from __future__ import annotations

# 为直接运行该模块时的导入做兼容处理（添加项目根与 src 到路径）
import os
import sys
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, os.pardir, os.pardir, os.pardir))
_src = os.path.join(_root, "src")
for _p in (_root, _src):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from typing import Any, Dict, Optional, List, Tuple
import json
import asyncio
import time
import logging
from datetime import timedelta

import redis

from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from config.settings import settings
from src.Chatbot.mcp.registry import MCPToolRunner
from src.Chatbot.agents.intent_recognition_agent import IntentRecognitionAgent
from src.Chatbot.mcp.client import NetMCPClient


class ClineOrchestrator:
    """基于类的 cline 工具编排实现。

    - 输入：问题、意图（可选）、已有状态（可选）
    - 决策：能否直接回答；若不能，选择工具与参数
    - 执行：调用 MCP 工具并返回统一结构结果
    """

    def __init__(
        self,
        runner: Optional[MCPToolRunner] = None,
        intent_agent: Optional[Any] = None,
        llm: Optional[ChatOpenAI] = None,
    ) -> None:
        self.runner = runner or MCPToolRunner.from_settings(settings)
        self.intent_agent = intent_agent
        self.llm = llm or ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_MODEL_BASE_URL,
            temperature=0.2,
        )
        self.llm_stream = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_MODEL_BASE_URL,
            temperature=0.2,
            streaming=True,
        )
        self.parser = JsonOutputParser()

    

    def _build_prompt(self) -> ChatPromptTemplate:
        # 使用用户提供的系统提示词（含占位变量）
        system_text = (
        """
        你是一个专业的意图识别与任务决策助手，精通 ReAct（Reason + Act）流程。你的职责是：基于当前上下文（state）、用户问题（question）、意图识别结果（intent_result）、可用工具清单（tools）与工具参数结构（tool_schema），进行严谨的逐步推理与决策，最终选择 **直接回答** 或 **调用工具**，并以严格规定的 JSON 结构输出决策结果。整个过程必须首先验证并遵守 `Restriction` 中的限制（法律、隐私、安全、资源或其它约束），任何违反限制的动作均不可执行，需在输出中明确说明并回退到安全替代方案。

        ---

        ### 输入（必读）
        - 用户问题（question）：{question}  
        - 当前状态 / 已知上下文（state）：{state}  — 可能为空或不完整  
        - 可用工具（tools）：{tools}  — 列表格式，包含工具名与功能描述  
        - 工具参数结构（tool_schema）：{tool_schema}  — 每个工具的入参、必选/可选项、返回格式  
        - 意图识别结果（intent_result）：{intent_result}  — 已识别的用户意图与置信度（若有）  
        - 工具调用限制（Restriction）：{Restriction}  — 必须严格遵守的限制说明

        ---

        ### 思考与行动规范（必须遵守）

        #### 一、前置检查（Header checks）
        1. **读取并理解 `Restriction`**：任何步骤前首先读取 `Restriction` 并将其作为优先约束。  
        2. **核对 `tools` 与 `tool_schema`**：确认哪些工具可用、哪些参数必传、是否存在调用频率或权限限制。  
        3. **审查 `intent_result` 置信度**：若置信度低（例如 <0.6），在推理时应考虑多种意图可能性并说明。

        #### 二、Reason（思考 — 结构化推理）
        按下列小节结构化输出内部推理结果（**仅用于内部推理，最终只输出 JSON**）：

        A. **信息充足性评估**
        - 判断当前 `state` 是否已包含完整回答所需的信息。  
        - 若充足：列出支持回答的关键数据点（至少 2 个佐证项）。  

        B. **缺口与风险识别**
        - 明确列出缺失的信息项（格式：字段名 + 需要的具体值或类型）。  
        - 识别潜在风险（隐私/合规/超出权限/违反 Restriction 等）。  

        C. **工具选择与理由**
        - 基于缺口列出候选工具（按优先级排序），并对每个候选工具说明：“为什么选它（能力）”与“是否与 Restriction 冲突”。  
        - 对每个选中工具，推演至少一组合理的 `tool_params` 值，并说明参数来源（从 state 提取/假设/需要用户填补）。

        D. **不可调用时的替代方案**
        - 若所有工具都被 Restriction 阻止，给出可行的降级策略（例如：返回部分信息、请求用户提供额外数据、提供安全/通用建议等）。

        #### 三、Act（行动 — 输出决策）
        根据上面的推理只做两种动作之一：`final_answer` 或 `tool_call`。**必须严格输出 JSON 且仅输出 JSON，不得包含额外文本。**

        - 若选择 **final_answer**（state 已足够且不违反 Restriction）：
        ```json
        {{
            "action": "final_answer",
            "reasoning": "<一句话概述为何无需调用工具>",
            "restriction_check": "<对 Restriction 的检查结论，若有关切说明如何满足>",
            "answer": "<面向用户的最终答案文本>",
            "evidence": ["<state 中支持答案的关键证据项1>", "<证据项2>"]  // 最少一项，若无则置空数组
        }}

        - 若选择 **tool_call**（需要调用某个工具以补充信息或完成任务）：
        ```json
        {{
            "action": "tool_call",
            "reasoning": "<一句话概述为何需要调用工具>",
            "restriction_check": "<对 Restriction 的检查结论，若有关切说明如何满足>",
            "next_tool": "<必须为 tools 列表中的工具名>",
            "tool_params": {{"<参数名>": "<参数值>"}}
        }}
        ```

        - 严格要求：
          1) 当输出为 `tool_call` 时，`next_tool` 必须准确来自输入的 `tools` 列表；
          2) `tool_params` 必须符合 `tool_schema` 中该工具的参数结构，包含所有必填参数；
          3) 输出必须是严格的 JSON（无额外文本、解释或 Markdown 注释）。

        """
        )

        return ChatPromptTemplate.from_messages([
            ("system", system_text),
            ("human", "请按上述 JSON 模式输出，且不要包含任何非 JSON 文本。")
        ])


    def _format_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.get("name"),
                "description": t.get("description"),
                "input_schema": t.get("input_schema"),
            }
            for t in self.runner.registry.list_tools()
        ]

    async def run_decide(
        self,
        question: str,
        intent: Dict[str, Any],
        state: Dict[str, Any],
        tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt = self._build_prompt()
        decision = await (prompt | self.llm | self.parser).ainvoke(
            {
                "question": question,
                "state": json.dumps(state, ensure_ascii=False),
                "tools": json.dumps(
                    [
                        {"name": t.get("name"), "description": t.get("description")}
                        for t in tools
                    ],
                    ensure_ascii=False,
                ),
                "tool_schema": json.dumps(
                    {t.get("name"): t.get("input_schema") for t in tools},
                    ensure_ascii=False,
                ),
                "intent_result": intent.get("analysis", ""),
                "Restriction": intent.get("Restriction", ""),
            }
        )
        logging.info(f"Decision: {decision}")
        print(f"Decision: {decision}")
        logging.info(f"state: {state}")
        return decision if isinstance(decision, dict) else {}

    async def run_decide_stream(
        self,
        question: str,
        intent: Dict[str, Any],
        state: Dict[str, Any],
        tools: List[Dict[str, Any]],
        on_chunk: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """流式决策：在生成决策前，实时输出模型思考 token。

        - on_chunk: 可选的异步回调，形如 `await on_chunk(token_str)`。
        返回最终决策字典。
        """
        prompt = self._build_prompt()
        inputs = {
            "question": question,
            "state": json.dumps(state, ensure_ascii=False),
            "tools": json.dumps(
                [
                    {"name": t.get("name"), "description": t.get("description")}
                    for t in tools
                ],
                ensure_ascii=False,
            ),
            "tool_schema": json.dumps(
                {t.get("name"): t.get("input_schema") for t in tools},
                ensure_ascii=False,
            ),
            "intent_result": intent.get("analysis", ""),
            "Restriction": intent.get("Restriction", ""),
        }
        try:
            messages = prompt.format_messages(**inputs)
            async for chunk in self.llm_stream.astream(messages):
                token = getattr(chunk, "content", None)
                if token and on_chunk and callable(on_chunk):
                    try:
                        await on_chunk(token)
                    except Exception:
                        pass
        except Exception as e:
            logging.warning(f"run_decide_stream: streaming unavailable: {e}")

        decision = await (prompt | self.llm | self.parser).ainvoke(inputs)
        return decision if isinstance(decision, dict) else {}

    async def run_async(
        self,
        question: str,
        host: Optional[str] = None,
        port: int = 0,
        max_attempts: int = 3,
        intent: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        多轮决策与工具调用的异步流程：
        - 若无显式 intent，则尝试使用 intent_agent 识别。
        - 使用 ReAct 决策（run_decide）判断直接回答或调用工具。
        - 工具调用后将结果合并到 state，并继续迭代，直至产生最终答案或达到最大次数。
        返回统一结构：{"type": str, "result": dict, "history": list}
        """
        state = state or {"tools": []}

        # 规范化 intent，避免 None 触发属性访问错误
        if intent is None:
            if self.intent_agent and hasattr(self.intent_agent, "recognize_text_intent"):
                try:
                    intent = await self.intent_agent.recognize_text_intent(question)
                except Exception as e:
                    logging.warning("RUN_ASYNC: intent recognition failed: %s", e)
                    intent = {"analysis": "", "Restriction": "", "intent_class": "general_answer"}
            else:
                intent = {"analysis": "", "Restriction": "", "intent_class": "general_answer"}

        # 至少保证一次决策
        if max_attempts <= 0:
            max_attempts = 1

        # 本地工具：优先使用缓存启动信息以减少注册表查询
        try:
            bootstrap = start_mcp_tools_bootstrap()
            cached_tools = bootstrap.get("tools", [])
            cached_schema = bootstrap.get("tool_schema", {})
            tools_full = [
                {
                    "name": t.get("name"),
                    "description": t.get("description"),
                    "input_schema": cached_schema.get(t.get("name"), {}),
                }
                for t in cached_tools
            ]
            if not tools_full:
                tools_full = self._format_tools()
        except Exception:
            tools_full = self._format_tools()

        # 远程 MCP 工具（如提供 host/port）
        remote_tools: List[Dict[str, Any]] = []
        remote_schema: Dict[str, Any] = {}
        remote_tool_names: set = set()
        net_client: Optional[NetMCPClient] = None
        if host and port:
            try:
                net_client = NetMCPClient(host, port)
                await net_client.handshake()
                remote_list = await net_client.list_tools()
                # 统一结构：仅传递 name/description 给决策，schema 另存
                for t in remote_list:
                    name = t.get("name")
                    desc = t.get("description")
                    sch = t.get("input_schema")
                    if name:
                        remote_tools.append({"name": name, "description": desc})
                        remote_schema[name] = sch
                        remote_tool_names.add(name)
                # 合并到 tools_full
                tools_full.extend(
                    [
                        {
                            "name": t.get("name"),
                            "description": t.get("description"),
                            "input_schema": remote_schema.get(t.get("name"), {}),
                        }
                        for t in remote_list
                    ]
                )
            except Exception as e:
                logging.warning("RUN_ASYNC: 远程 MCP 工具发现失败: %s", e)
        history: List[Dict[str, Any]] = []
        last_exec: Optional[Dict[str, Any]] = None

        for attempt in range(max_attempts):
            decision = await self.run_decide(
                question=question,
                intent=intent,
                state=state,
                tools=tools_full,
            )

            action = decision.get("action")
            if action == "final_answer":
                answer = decision.get("answer") or decision.get("final_answer", "")
                result = {"success": True, "answer": answer, "source": "llm"}
                return {"type": intent.get("intent_class") or "general_answer", "result": result, "history": history}

            if action == "tool_call":
                tool_name = decision.get("next_tool")
                tool_params = decision.get("tool_params") or {}
                # 判断是否远程工具
                if net_client and tool_name in remote_tool_names:
                    try:
                        exec_res = await net_client.call_tool(tool_name, tool_params)
                    except Exception as e:
                        exec_res = {"success": False, "error": f"Remote MCP call failed: {e}", "source": "mcp_remote"}
                else:
                    exec_res = await self.runner.registry.call(tool_name, tool_params)
                last_exec = {"tool": tool_name, "params": tool_params, "result": exec_res}
                history.append(last_exec)
                state['tools'].append({"name": tool_name, "result": exec_res})

                if self.intent_agent and hasattr(self.intent_agent, "assess_and_compose_answer"):
                    try:
                        composed = await self.intent_agent.assess_and_compose_answer(intent, exec_res, question)
                        if composed and composed.get("can_answer"):
                            return {
                                "type": composed.get("type") or (intent.get("intent_class") or "general_answer"),
                                "result": composed.get("result") or {"success": True, "answer": ""},
                                "history": history,
                            }
                    except Exception:
                        pass
                continue

            return {
                "type": "general_answer",
                "result": {"success": False, "error": "Invalid decision output"},
                "history": history,
            }

        if last_exec is not None:
            return {
                "type": intent.get("intent_class") or "general_answer",
                "result": last_exec.get("result") or {"success": False, "error": "Max attempts reached"},
                "history": history,
            }
        return {
            "type": intent.get("intent_class") or "general_answer",
            "result": {"success": False, "error": "No attempts executed"},
            "history": history,
        }



_LOGGER = logging.getLogger(__name__)

_CACHE_KEY_TOOLS = "mcp:tools:list"
_CACHE_KEY_SCHEMA = "mcp:tools:schema"
_CACHE_TTL_SECONDS = 600  # 10 分钟刷新缓存


def _get_redis_client() -> Optional[redis.Redis]:
    """按 settings 获取 Redis 客户端；失败时返回 None。"""
    try:
        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )
        # 简单 ping 测试，避免懒连接导致首次使用报错不明确
        client.ping()
        return client
    except Exception as e:
        _LOGGER.warning(f"Redis 不可用或连接失败：{e}")
        return None


def _load_mcp_tools_from_cache(r: redis.Redis) -> Optional[Dict[str, Any]]:
    """从 Redis 读取工具与 schema，若不存在或解析失败返回 None。"""
    try:
        tools_json = r.get(_CACHE_KEY_TOOLS)
        schema_json = r.get(_CACHE_KEY_SCHEMA)
        if not tools_json or not schema_json:
            return None
        tools = json.loads(tools_json)
        schema = json.loads(schema_json)
        if not isinstance(tools, list) or not isinstance(schema, dict):
            return None
        return {"source": "cache", "tools": tools, "tool_schema": schema}
    except Exception as e:
        _LOGGER.warning(f"读取 Redis 缓存失败：{e}")
        return None


def _store_mcp_tools_to_cache(r: redis.Redis, tools: List[Dict[str, Any]], schema: Dict[str, Any]) -> None:
    """将工具与 schema 写入 Redis，设置合理 TTL。"""
    try:
        r.setex(_CACHE_KEY_TOOLS, _CACHE_TTL_SECONDS, json.dumps(tools, ensure_ascii=False))
        r.setex(_CACHE_KEY_SCHEMA, _CACHE_TTL_SECONDS, json.dumps(schema, ensure_ascii=False))
    except Exception as e:
        _LOGGER.warning(f"写入 Redis 缓存失败：{e}")


def _query_mcp_tools_from_registry() -> Dict[str, Any]:
    """从 MCP 注册表查询工具列表与参数结构。"""
    runner = MCPToolRunner.from_settings(settings)
    tools_raw = runner.registry.list_tools()
    tools: List[Dict[str, Any]] = [
        {"name": t.get("name"), "description": t.get("description")}
        for t in tools_raw
    ]
    schema: Dict[str, Any] = {
        t.get("name"): t.get("input_schema") for t in tools_raw
    }
    return {"source": "registry", "tools": tools, "tool_schema": schema}


def start_mcp_tools_bootstrap(force_refresh: bool = False) -> Dict[str, Any]:
    """
    启动函数：获取 MCP 工具信息（工具列表与参数结构）。

    - 优先从 Redis 缓存读取；若不存在或强制刷新，则从 MCP 注册表查询并回写缓存。
    - 返回统一结构：{"source": "cache|registry", "tools": [...], "tool_schema": {name: schema}}
    """
    t0 = time.time()
    redis_client = _get_redis_client()

    # 优先尝试缓存
    if redis_client and not force_refresh:
        cached = _load_mcp_tools_from_cache(redis_client)
        if cached:
            cached["elapsed_ms"] = int((time.time() - t0) * 1000)
            return cached

    # 回退至注册表查询
    data = _query_mcp_tools_from_registry()
    data["elapsed_ms"] = int((time.time() - t0) * 1000)

    # 写回缓存（若 Redis 可用）
    if redis_client:
        _store_mcp_tools_to_cache(redis_client, data["tools"], data["tool_schema"])

    return data


async def run_cline_flow(
    question: str,
    host: Optional[str] = None,
    port: int = 0,
    max_attempts: int = 3,
    intent: Optional[Dict[str, Any]] = None,
    state: Optional[Dict[str, Any]] = None,
    intent_agent: Optional[Any] = None,
) -> Dict[str, Any]:
    """模块级异步入口：执行 cline 多轮决策与工具调用。"""
    orchestrator = ClineOrchestrator(intent_agent=intent_agent)
    return await orchestrator.run_async(
        question=question,
        host=host,
        port=port,
        max_attempts=max_attempts,
        intent=intent,
        state=state,
    )


if __name__ == "__main__":
    # 自检：打印工具与 schema 来源与数量，并展示部分参数结构
    info = start_mcp_tools_bootstrap()
    src = info.get("source")
    tools = info.get("tools", [])
    schema = info.get("tool_schema", {})
    print(f"[Bootstrap] source={src}, tools={len(tools)}, schema={len(schema)}, elapsed={info.get('elapsed_ms')}ms")
    for t in tools:
        name = t.get("name")
        desc = t.get("description")
        print(f" - {name}: {desc}")
        sch = schema.get(name) or {}
        if isinstance(sch, dict):
            props = sch.get("properties") or {}
            reqs = sch.get("required") or []
            keys = list(props.keys())[:6]
            print(f"   params: {keys} required: {reqs[:6]}")
