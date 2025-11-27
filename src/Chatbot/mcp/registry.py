from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from pydantic import ValidationError
import time
from .schema import ToolParam, ToolResult
from typing import Tuple


@dataclass
class MCPToolSpec:
    """Specification of an MCP tool.

    Attributes:
        name: Unique tool name
        description: Human-friendly description
        input_schema: Minimal schema description for params (informational)
        runner: Async callable that takes params dict and returns result dict
    """

    name: str
    description: str
    input_schema: Dict[str, Any]
    runner: Callable[[Dict[str, Any]], Any]


class MCPRegistry:
    """A simple registry for MCP tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, MCPToolSpec] = {}

    def register(self, spec: MCPToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "input_schema": spec.input_schema,
            }
            for spec in self._tools.values()
        ]

    async def call(self, name: str, params: Dict[str, Any], *, timeout_ms: int = 30000, retries: int = 0) -> Dict[str, Any]:
        if name not in self._tools:
            raise ValueError(f"Unknown tool: {name}")
        runner = self._tools[name].runner

        # Validate input
        try:
            validated = ToolParam(**params)
        except ValidationError as ve:
            return {"tool": name, "success": False, "error": f"Invalid params: {ve}"}

        attempts = retries + 1
        last_error: Optional[str] = None

        for attempt in range(attempts):
            start = time.time()
            try:
                # Support both async and sync runners
                if asyncio.iscoroutinefunction(runner):
                    # Enforce timeout
                    result = await asyncio.wait_for(runner(validated.model_dump()), timeout=timeout_ms / 1000)
                else:
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(loop.run_in_executor(None, lambda: runner(validated.model_dump())), timeout=timeout_ms / 1000)

                if not isinstance(result, dict):
                    result = {"result": result}

                # Validate output
                try:
                    ToolResult(**{**result, "success": result.get("success", True)})
                except ValidationError as ve:
                    return {"tool": name, "success": False, "error": f"Invalid tool result: {ve}"}

                return {"tool": name, **result}
            except asyncio.TimeoutError:
                last_error = f"Tool '{name}' timed out after {timeout_ms} ms"
            except Exception as e:
                last_error = str(e)
            finally:
                _elapsed = (time.time() - start) * 1000

        return {"tool": name, "success": False, "error": last_error or "Unknown error"}


class MCPToolRunner:
    """Convenience wrapper around MCPRegistry with pre-registered tools.

    Can be instantiated with existing services like WebSearchTool, hybrid_retrieval, etc.
    """

    def __init__(
        self,
        web_search_tool: Optional[Any] = None,
        hybrid_retrieval_fn: Optional[Callable[..., Any]] = None,
        db_enabled: bool = False,
        weather_tool: Optional[Any] = None,
        time_tool: Optional[Any] = None,
        city_code_tool: Optional[Any] = None,
        wechat_available: bool = True,
    ) -> None:
        self.registry = MCPRegistry()
        if web_search_tool:
            # 仅保留一个“AI搜索”工具，且不回退至百度网页抓取
            async def ai_search(params: Dict[str, Any]) -> Dict[str, Any]:
                query = params.get("query", "")
                max_results = int(params.get("max_results", 5))
                try:
                    # 直接调用百度AI搜索API（若未配置将返回空结果），不使用普通百度网页搜索
                    results = await web_search_tool.search_baidu_ai(query, max_results=max_results)
                    # 生成简要 answer 预览，便于上层直接展示
                    preview = []
                    for i, item in enumerate(results[: min(5, len(results))]):
                        title = item.get("title", "").strip() or "无标题"
                        url = item.get("url", "")
                        snippet = (item.get("snippet", "") or item.get("content", "")).strip()
                        snippet = snippet[:160]
                        preview.append(f"[{i+1}] {title}\n摘要: {snippet}\n链接: {url}")
                    answer = "\n\n".join(preview) if preview else ""
                    return {"success": True, "results": results, "answer": answer, "source": "ai_search"}
                except Exception as e:
                    return {"success": False, "error": str(e), "source": "ai_search"}

            self.registry.register(
                MCPToolSpec(
                    name="ai_search",
                    description="整合全网资源，快速搜索网络上的实时信息，满足用户对实时事件、新闻、数据等的查询需求。（不能保证信息的准确性，若查询如学校信息等结果，不建议使用此工具）",
                    input_schema={"query": "str", "max_results": "int?"},
                    runner=ai_search,
                )
            )

        # Weather tools (optional, no API key required)
        if weather_tool:
            async def get_forecast(params: Dict[str, Any]) -> Dict[str, Any]:
                city = (params.get("city") or "Xi'an").strip()
                days = int(params.get("days", 1))
                try:
                    items = await weather_tool.get_forecast(city, days)
                    # 生成可读的 answer，避免上层按工具专门处理
                    answer = ""
                    try:
                        now_item = next((r for r in items if str(r.get("date")).lower() == "now"), None)
                        today_item = next((r for r in items if str(r.get("date")).lower() in ("today", "day1")), None)
                        base = (now_item or today_item or (items[0] if items else {}))
                        city_name = base.get("city") or ""
                        lines = []
                        if now_item:
                            t = now_item.get("time")
                            temp_c = now_item.get("temperature") or now_item.get("max_temp_C") or now_item.get("min_temp_C")
                            wind = now_item.get("summary") or ""
                            hum = now_item.get("humidity") or ""
                            seg = []
                            if city_name:
                                seg.append(city_name)
                            if t:
                                seg.append(f"当前{t}")
                            if temp_c:
                                seg.append(f"气温{temp_c}°C")
                            if wind:
                                seg.append(wind)
                            if hum:
                                seg.append(f"湿度{hum}")
                            if seg:
                                lines.append("，".join(seg) + "。")
                        if today_item:
                            hi = today_item.get("max_temp_C") or today_item.get("max_temp") or today_item.get("max")
                            lo = today_item.get("min_temp_C") or today_item.get("min_temp") or today_item.get("min")
                            overview = today_item.get("summary") or today_item.get("overview") or ""
                            parts = ["今日"]
                            if overview:
                                parts.append(overview)
                            hi_lo = []
                            if hi:
                                hi_lo.append(f"最高{hi}°C")
                            if lo:
                                hi_lo.append(f"最低{lo}°C")
                            if hi_lo:
                                parts.append("，".join(hi_lo))
                            if len(parts) > 1:
                                lines.append("：".join([parts[0], "，".join(parts[1:])]) + "。")
                        if not lines and items:
                            first = items[0]
                            temp_c = first.get("temperature") or first.get("max_temp_C") or first.get("min_temp_C")
                            wind = first.get("summary") or ""
                            hum = first.get("humidity") or ""
                            seg = []
                            if city_name:
                                seg.append(city_name)
                            if temp_c:
                                seg.append(f"气温{temp_c}°C")
                            if wind:
                                seg.append(wind)
                            if hum:
                                seg.append(f"湿度{hum}")
                            if seg:
                                lines.append("，".join(seg) + "。")
                        if lines:
                            answer = " ".join(lines) + " 数据来源：中国气象局/中国天气网。"
                    except Exception:
                        answer = ""
                    return {"success": True, "results": items, "answer": answer, "source": "get_forecast"}
                except Exception as e:
                    return {"success": False, "error": str(e), "source": "get_forecast"}

            self.registry.register(
                MCPToolSpec(
                    name="get_forecast",
                    description="通过CMA/Weather.com.cn官方界面查询天气。",
                    input_schema={"city": "str", "days": "int?"},
                    runner=get_forecast,
                )
            )

        # City code (network-only) tool: 独立注册，删除原本基于 WeatherTool 的城市查询工具
        if city_code_tool:
            async def resolve_city_code_network(params: Dict[str, Any]) -> Dict[str, Any]:
                city = (params.get("city") or "").strip()
                try:
                    data = await city_code_tool.resolve_city_code(city)
                    if data.get("success"):
                        code = data.get("code")
                        cname = data.get("city") or city
                        data["answer"] = f"{cname} 的城市代码为 {code}（网络查询）。"
                    return data
                except Exception as e:
                    return {"success": False, "error": str(e), "source": "resolve_city_code_network"}

            self.registry.register(
                MCPToolSpec(
                    name="resolve_city_code_network",
                    description="查询城市代码（基于中国天气网城市3级数据）。用于天气查询时需要输入的城市代码的查询。",
                    input_schema={"city": "str"},
                    runner=resolve_city_code_network,
                )
            )

        # Time tool (optional)
        if time_tool:
            def get_time(params: Dict[str, Any]) -> Dict[str, Any]:
                tz = params.get("timezone")
                fmt = params.get("format")
                data = time_tool.get_time(tz, fmt)
                # 统一生成 answer，避免上层按工具专门处理
                try:
                    if data.get("success"):
                        t = data.get("time")
                        tzname = data.get("timezone")
                        src = data.get("source")
                        data["answer"] = f"当前{tzname}时间：{t}（来源：{src}）。" if t else ""
                except Exception:
                    pass
                return data

            self.registry.register(
                MCPToolSpec(
                    name="get_time",
                    description="使用NTP/system fallback通过NTSC time.ac.cn （web）查询官方时间；时区转换。",
                    input_schema={"timezone": "str?", "format": "str?"},
                    runner=get_time,
                )
            )

        if hybrid_retrieval_fn:
            async def knowledge_search(params: Dict[str, Any]) -> Dict[str, Any]:
                query = params.get("query", "")
                top_k = int(params.get("top_k", 10))
                keywords = params.get("keywords") or [query]
                merged = await hybrid_retrieval_fn(query_text=query, top_k=top_k, keywords=keywords)
                # 简要摘要，便于上层直接展示
                try:
                    preview_items = merged[: min(5, len(merged))]
                    summary = "\n".join([
                        f"{i+1}. {item.get('title','').strip()} - {str(item.get('content',''))[:120]}"
                        for i, item in enumerate(preview_items)
                    ])
                except Exception:
                    summary = ""
                return {
                    "success": True,
                    "results": merged,
                    "answer": summary,
                    "source": "hybrid_retrieval",
                }

            self.registry.register(
                MCPToolSpec(
                    name="knowledge_search",
                    description="用于查询学校相关信息的混合检索工具。",
                    input_schema={"query": "str", "top_k": "int?", "keywords": "List[str]?"},
                    runner=knowledge_search,
                )
            )

        if wechat_available:
            try:
                from config.settings import settings as _settings
                from src.Chatbot.tools.MCP.wechat import (
                    build_wechat_send_runner,
                    build_wechat_fetch_runner,
                    WECHAT_SEND_INPUT_SCHEMA,
                    WECHAT_FETCH_INPUT_SCHEMA,
                )
                self.registry.register(
                    MCPToolSpec(
                        name="wechat_send",
                        description="向指定企业微信用户发送文本消息。",
                        input_schema=WECHAT_SEND_INPUT_SCHEMA,
                        runner=build_wechat_send_runner(_settings),
                    )
                )
                self.registry.register(
                    MCPToolSpec(
                        name="wechat_fetch",
                        description="获取企业微信消息（占位，不支持接收）。",
                        input_schema=WECHAT_FETCH_INPUT_SCHEMA,
                        runner=build_wechat_fetch_runner(_settings),
                    )
                )
            except Exception:
                pass
        # Database query tool (permission-based, optional) — only registration here
        if db_enabled:
            try:
                from src.Chatbot.tools.MCP.data_tools import build_db_query_runner, DB_QUERY_INPUT_SCHEMA, DB_QUERY_DESCRIPTION
                runner = build_db_query_runner()
                self.registry.register(
                    MCPToolSpec(
                        name="db_query",
                        description=DB_QUERY_DESCRIPTION,
                        input_schema=DB_QUERY_INPUT_SCHEMA,
                        runner=runner,
                    )
                )
            except Exception:
                # 如果数据库依赖不可用，跳过注册
                pass

    def add_tool(self, spec: MCPToolSpec) -> None:
        self.registry.register(spec)

    @classmethod
    def from_settings(cls, settings: Any) -> "MCPToolRunner":
        """Create a tool runner using dynamic availability from settings/env.

        - Registers WebSearch if SEARCH_ENGINE configured
        - Registers Knowledge Search if dependencies available
        - Registers DB Query if MySQL/Redis configured
        """
        web = None
        try:
            from src.Chatbot.tools.MCP.web_search import WebSearchTool
            web = WebSearchTool(settings)
        except Exception:
            web = None

        # Weather tool (no special settings required)
        weather = None
        try:
            from src.Chatbot.tools.MCP.weather import WeatherTool as _WeatherTool
            weather = _WeatherTool(settings)
        except Exception:
            weather = None

        # City code (network-only) tool
        city_code_tool = None
        try:
            from src.Chatbot.tools.MCP.city_code_network import CityCodeNetworkTool as _CityCodeTool
            city_code_tool = _CityCodeTool(settings)
        except Exception:
            city_code_tool = None

        # Time tool
        time_tool = None
        try:
            from src.Chatbot.tools.MCP.time_tools import TimeTool as _TimeTool
            time_tool = _TimeTool()
        except Exception:
            time_tool = None

        # 尝试加载知识检索（可能依赖 asyncpg / 词向量等）
        hybrid = None
        try:
            from src.Chatbot.agents.knowledge_query_agent import hybrid_retrieval as _hybrid
            hybrid = _hybrid
        except Exception:
            hybrid = None

        # 根据配置判断是否启用数据库查询
        db_enabled = bool(settings.MYSQL_HOST or settings.REDIS_HOST)
        return cls(
            web_search_tool=web,
            hybrid_retrieval_fn=hybrid,
            db_enabled=db_enabled,
            weather_tool=weather,
            time_tool=time_tool,
            city_code_tool=city_code_tool,
        )
