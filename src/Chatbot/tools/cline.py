from __future__ import annotations

from typing import Any, Dict, Optional, List, Callable
import json
import asyncio
import time
import logging

import redis

from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from config.settings import settings
from src.Chatbot.mcp.registry import MCPToolRunner
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

    @staticmethod
    async def _emit_event(
        on_event: Optional[Callable[[Dict[str, Any]], Any]],
        payload: Dict[str, Any],
    ) -> None:
        if not on_event:
            return
        try:
            result = on_event(payload)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            # 事件回调失败不影响主流程
            pass

    @staticmethod
    def _normalize_state(state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        normalized = state.copy() if isinstance(state, dict) else {}
        tools = normalized.get("tools")
        if not isinstance(tools, list):
            normalized["tools"] = []
        react_steps = normalized.get("react_steps")
        if not isinstance(react_steps, list):
            normalized["react_steps"] = []
        return normalized

    async def _ensure_intent(self, question: str, intent: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(intent, dict):
            return intent
        if self.intent_agent and hasattr(self.intent_agent, "recognize_text_intent"):
            try:
                return await self.intent_agent.recognize_text_intent(question)
            except Exception as e:
                logging.warning("RUN_ASYNC: intent recognition failed: %s", e)
        return {"analysis": "", "Restriction": "", "intent_class": "general_answer"}

    @staticmethod
    def _tool_names(tools: List[Dict[str, Any]]) -> set[str]:
        return {str(t.get("name")) for t in tools if t.get("name")}

    @staticmethod
    def _coerce_tool_params(params: Dict[str, Any], input_schema: Any) -> Dict[str, Any]:
        if not isinstance(params, dict):
            return {}
        normalized = dict(params)

        # JSON-Schema 风格：{"properties": {"days": {"type": "integer"}}}
        if isinstance(input_schema, dict) and isinstance(input_schema.get("properties"), dict):
            for key, spec in input_schema["properties"].items():
                if key not in normalized:
                    continue
                value = normalized.get(key)
                if not isinstance(spec, dict):
                    continue
                if spec.get("type") == "integer" and isinstance(value, str) and value.strip().isdigit():
                    normalized[key] = int(value.strip())
            return normalized

        # 轻量风格：{"days": "int?", "city": "str"}
        if isinstance(input_schema, dict):
            for key, t in input_schema.items():
                if key not in normalized:
                    continue
                value = normalized.get(key)
                if isinstance(t, str) and "int" in t.lower() and isinstance(value, str) and value.strip().isdigit():
                    normalized[key] = int(value.strip())
        return normalized

    @staticmethod
    def _validate_required_params(params: Dict[str, Any], input_schema: Any) -> List[str]:
        if not isinstance(input_schema, dict):
            return []
        required = input_schema.get("required")
        if not isinstance(required, list):
            return []
        missing: List[str] = []
        for key in required:
            if not isinstance(key, str):
                continue
            value = params.get(key)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(key)
        return missing

    def _normalize_decision(
        self,
        decision: Dict[str, Any],
        tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not isinstance(decision, dict):
            return {
                "action": "invalid",
                "error": "Decision is not a JSON object",
                "raw_decision": decision,
            }

        action = str(decision.get("action") or "").strip().lower()
        if action == "final_answer":
            answer = str(decision.get("answer") or decision.get("final_answer") or "").strip()
            if not answer:
                return {"action": "invalid", "error": "Empty final answer", "raw_decision": decision}
            return {
                "action": "final_answer",
                "answer": answer,
                "reasoning": decision.get("reasoning", ""),
                "restriction_check": decision.get("restriction_check", ""),
            }

        if action == "tool_call":
            tool_name = str(decision.get("next_tool") or "").strip()
            if not tool_name:
                return {"action": "invalid", "error": "Missing next_tool", "raw_decision": decision}

            tool_map = {str(t.get("name")): t for t in tools if t.get("name")}
            if tool_name not in tool_map:
                return {
                    "action": "invalid",
                    "error": f"Unknown tool selected: {tool_name}",
                    "raw_decision": decision,
                }

            raw_params = decision.get("tool_params")
            tool_params = raw_params if isinstance(raw_params, dict) else {}
            input_schema = tool_map[tool_name].get("input_schema") or {}
            tool_params = self._coerce_tool_params(tool_params, input_schema)
            missing = self._validate_required_params(tool_params, input_schema)
            if missing:
                return {
                    "action": "invalid",
                    "error": f"Missing required params for {tool_name}: {', '.join(missing)}",
                    "raw_decision": decision,
                }

            return {
                "action": "tool_call",
                "next_tool": tool_name,
                "tool_params": tool_params,
                "reasoning": decision.get("reasoning", ""),
                "restriction_check": decision.get("restriction_check", ""),
            }

        return {
            "action": "invalid",
            "error": f"Unsupported action: {action or '<empty>'}",
            "raw_decision": decision,
        }

    @staticmethod
    def _tool_call_signature(tool_name: Optional[str], tool_params: Dict[str, Any]) -> str:
        safe_name = str(tool_name or "")
        try:
            safe_params = json.dumps(tool_params or {}, ensure_ascii=False, sort_keys=True)
        except Exception:
            safe_params = "{}"
        return f"{safe_name}::{safe_params}"

    @staticmethod
    def _attach_trace(
        payload: Dict[str, Any],
        state: Dict[str, Any],
        include_trace: bool,
    ) -> Dict[str, Any]:
        if not include_trace:
            return payload
        payload["trace"] = {
            "tools": state.get("tools", []),
            "react_steps": state.get("react_steps", []),
        }
        return payload

    async def _synthesize_answer_from_history(
        self,
        question: str,
        intent: Dict[str, Any],
        state: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> str:
        """当决策循环未返回最终答案时，基于观察结果进行一次兜底总结。"""
        if not history:
            return ""
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "你是 ReAct 执行后的总结器。"
                    "请根据工具执行观察结果，生成给用户的最终回答。"
                    "要求：简洁、准确、中文输出；若结果不足，明确说明不足与下一步建议。"
                ),
            ),
            (
                "human",
                (
                    "用户问题：{question}\n"
                    "意图：{intent}\n"
                    "工具观察历史：{history}\n"
                    "状态：{state}\n"
                    "请直接输出最终回答文本。"
                ),
            ),
        ])
        try:
            messages = prompt.format_messages(
                question=question,
                intent=json.dumps(intent, ensure_ascii=False),
                history=json.dumps(history, ensure_ascii=False),
                state=json.dumps(state, ensure_ascii=False),
            )
            resp = await self.llm.ainvoke(messages)
            content = getattr(resp, "content", "")
            if isinstance(content, str):
                return content.strip()
            return str(content).strip()
        except Exception as e:
            logging.warning("fallback synthesis failed: %s", e)
            return ""

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
        try:
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
        except Exception as e:
            logging.warning("run_decide failed: %s", e)
            return {}
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

        try:
            decision = await (prompt | self.llm | self.parser).ainvoke(inputs)
        except Exception as e:
            logging.warning("run_decide_stream parse failed: %s", e)
            return {}
        return decision if isinstance(decision, dict) else {}

    async def _discover_tools(
        self,
        host: Optional[str],
        port: int,
    ) -> tuple[List[Dict[str, Any]], Optional[NetMCPClient], set[str]]:
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
                if t.get("name")
            ]
            if not tools_full:
                tools_full = self._format_tools()
        except Exception:
            tools_full = self._format_tools()

        # 远程 MCP 工具（如提供 host/port）
        remote_tool_names: set[str] = set()
        net_client: Optional[NetMCPClient] = None
        if host and port:
            try:
                net_client = NetMCPClient(host, port)
                await net_client.handshake()
                remote_list = await net_client.list_tools()
                for t in remote_list:
                    name = t.get("name")
                    if not name:
                        continue
                    remote_tool_names.add(name)
                    tools_full.append(
                        {
                            "name": name,
                            "description": t.get("description"),
                            "input_schema": t.get("input_schema") or {},
                        }
                    )
            except Exception as e:
                logging.warning("RUN_ASYNC: 远程 MCP 工具发现失败: %s", e)
        return tools_full, net_client, remote_tool_names

    async def run_async(
        self,
        question: str,
        host: Optional[str] = None,
        port: int = 0,
        max_attempts: int = 3,
        intent: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None,
        on_event: Optional[Callable[[Dict[str, Any]], Any]] = None,
        on_thinking_chunk: Optional[Callable[[str], Any]] = None,
        use_stream_decide: bool = False,
        include_trace: bool = False,
        allow_fallback_synthesis: bool = True,
        max_consecutive_invalid: int = 2,
    ) -> Dict[str, Any]:
        """
        ReAct 多轮决策与工具调用流程（接口化）。

        - 支持 on_event 回调，输出结构化事件（decision/tool_call/tool_result/final/error）
        - 支持 on_thinking_chunk 回调，输出模型思考 token
        - 返回统一结构：{"type": str, "result": dict, "history": list}
        """
        state = self._normalize_state(state)
        intent = await self._ensure_intent(question, intent)
        if max_attempts <= 0:
            max_attempts = 1

        tools_full, net_client, remote_tool_names = await self._discover_tools(host, port)
        history: List[Dict[str, Any]] = []
        last_exec: Optional[Dict[str, Any]] = None
        consecutive_invalid = 0
        last_tool_sig: Optional[str] = None

        async def _forward_thinking(token: str) -> None:
            if on_thinking_chunk:
                result = on_thinking_chunk(token)
                if asyncio.iscoroutine(result):
                    await result

        for attempt in range(max_attempts):
            await self._emit_event(
                on_event,
                {
                    "type": "attempt_start",
                    "attempt": attempt + 1,
                    "max_attempts": max_attempts,
                    "question": question,
                },
            )

            if use_stream_decide or on_thinking_chunk:
                raw_decision = await self.run_decide_stream(
                    question=question,
                    intent=intent,
                    state=state,
                    tools=tools_full,
                    on_chunk=_forward_thinking if on_thinking_chunk else None,
                )
            else:
                raw_decision = await self.run_decide(
                    question=question,
                    intent=intent,
                    state=state,
                    tools=tools_full,
                )

            decision = self._normalize_decision(raw_decision, tools_full)
            await self._emit_event(
                on_event,
                {
                    "type": "decision",
                    "attempt": attempt + 1,
                    "decision": decision,
                },
            )

            action = decision.get("action")
            if action == "final_answer":
                answer = decision.get("answer", "")
                result = {"success": True, "answer": answer, "source": "llm"}
                await self._emit_event(
                    on_event,
                    {
                        "type": "final_answer",
                        "attempt": attempt + 1,
                        "result": result,
                    },
                )
                payload = {
                    "type": intent.get("intent_class") or "general_answer",
                    "result": result,
                    "history": history,
                }
                return self._attach_trace(payload, state, include_trace)

            if action == "tool_call":
                consecutive_invalid = 0
                tool_name = decision.get("next_tool")
                tool_params = decision.get("tool_params") or {}
                current_sig = self._tool_call_signature(tool_name, tool_params)
                if last_tool_sig == current_sig:
                    # 连续重复同一个工具调用，标记为无效决策并让模型重新思考下一步
                    duplicate_error = f"Repeated tool call detected: {tool_name}"
                    state["react_steps"].append(
                        {
                            "decision": decision,
                            "attempt": attempt + 1,
                            "error": duplicate_error,
                        }
                    )
                    await self._emit_event(
                        on_event,
                        {
                            "type": "error",
                            "attempt": attempt + 1,
                            "error": duplicate_error,
                        },
                    )
                    consecutive_invalid += 1
                    if consecutive_invalid >= max(1, max_consecutive_invalid):
                        break
                    continue

                await self._emit_event(
                    on_event,
                    {
                        "type": "tool_call",
                        "attempt": attempt + 1,
                        "tool": tool_name,
                        "params": tool_params,
                    },
                )

                if net_client and tool_name in remote_tool_names:
                    try:
                        exec_res = await net_client.call_tool(tool_name, tool_params)
                    except Exception as e:
                        exec_res = {"success": False, "error": f"Remote MCP call failed: {e}", "source": "mcp_remote"}
                else:
                    exec_res = await self.runner.registry.call(tool_name, tool_params)

                last_exec = {"tool": tool_name, "params": tool_params, "result": exec_res, "attempt": attempt + 1}
                history.append(last_exec)
                state["tools"].append({"name": tool_name, "result": exec_res})
                state["react_steps"].append({"decision": decision, "observation": exec_res, "attempt": attempt + 1})
                last_tool_sig = current_sig

                await self._emit_event(
                    on_event,
                    {
                        "type": "tool_result",
                        "attempt": attempt + 1,
                        "tool": tool_name,
                        "result": exec_res,
                    },
                )

                if self.intent_agent and hasattr(self.intent_agent, "assess_and_compose_answer"):
                    try:
                        composed = await self.intent_agent.assess_and_compose_answer(intent, exec_res, question)
                        if composed and composed.get("can_answer"):
                            final_result = {
                                "type": composed.get("type") or (intent.get("intent_class") or "general_answer"),
                                "result": composed.get("result") or {"success": True, "answer": ""},
                                "history": history,
                            }
                            await self._emit_event(
                                on_event,
                                {
                                    "type": "final_answer",
                                    "attempt": attempt + 1,
                                    "result": final_result["result"],
                                },
                            )
                            return self._attach_trace(final_result, state, include_trace)
                    except Exception:
                        pass
                continue

            error_message = decision.get("error") or "Invalid decision output"
            consecutive_invalid += 1
            state["react_steps"].append({"decision": decision, "attempt": attempt + 1})
            await self._emit_event(
                on_event,
                {
                    "type": "error",
                    "attempt": attempt + 1,
                    "error": error_message,
                },
            )
            if consecutive_invalid >= max(1, max_consecutive_invalid):
                break

        if allow_fallback_synthesis:
            fallback_answer = await self._synthesize_answer_from_history(
                question=question,
                intent=intent,
                state=state,
                history=history,
            )
            if fallback_answer:
                result = {"success": True, "answer": fallback_answer, "source": "react_fallback"}
                await self._emit_event(
                    on_event,
                    {
                        "type": "final_answer",
                        "attempt": max_attempts,
                        "result": result,
                    },
                )
                payload = {
                    "type": intent.get("intent_class") or "general_answer",
                    "result": result,
                    "history": history,
                }
                return self._attach_trace(payload, state, include_trace)

        if last_exec is not None:
            result = last_exec.get("result") or {"success": False, "error": "Max attempts reached"}
            payload = {
                "type": intent.get("intent_class") or "general_answer",
                "result": result,
                "history": history,
            }
            return self._attach_trace(payload, state, include_trace)

        payload = {
            "type": intent.get("intent_class") or "general_answer",
            "result": {"success": False, "error": "No attempts executed"},
            "history": history,
        }
        return self._attach_trace(payload, state, include_trace)

    async def run_react(
        self,
        question: str,
        host: Optional[str] = None,
        port: int = 0,
        max_attempts: int = 3,
        intent: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None,
        on_event: Optional[Callable[[Dict[str, Any]], Any]] = None,
        on_thinking_chunk: Optional[Callable[[str], Any]] = None,
        use_stream_decide: bool = False,
        include_trace: bool = False,
        allow_fallback_synthesis: bool = True,
        max_consecutive_invalid: int = 2,
    ) -> Dict[str, Any]:
        """显式 ReAct 接口别名（与 run_async 等价）。"""
        return await self.run_async(
            question=question,
            host=host,
            port=port,
            max_attempts=max_attempts,
            intent=intent,
            state=state,
            on_event=on_event,
            on_thinking_chunk=on_thinking_chunk,
            use_stream_decide=use_stream_decide,
            include_trace=include_trace,
            allow_fallback_synthesis=allow_fallback_synthesis,
            max_consecutive_invalid=max_consecutive_invalid,
        )



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
    on_event: Optional[Callable[[Dict[str, Any]], Any]] = None,
    on_thinking_chunk: Optional[Callable[[str], Any]] = None,
    use_stream_decide: bool = False,
    include_trace: bool = False,
    allow_fallback_synthesis: bool = True,
    max_consecutive_invalid: int = 2,
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
        on_event=on_event,
        on_thinking_chunk=on_thinking_chunk,
        use_stream_decide=use_stream_decide,
        include_trace=include_trace,
        allow_fallback_synthesis=allow_fallback_synthesis,
        max_consecutive_invalid=max_consecutive_invalid,
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
