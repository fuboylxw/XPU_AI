# OpenCode ReAct 智能体接口优化说明

本次优化聚焦 **ReAct（Reason + Act）接口智能体**，不是前端框架改造。目标是让决策-调用-观察流程更可控、更可追踪。

## 1) ReAct 决策标准化

- 文件：`src/Chatbot/tools/cline.py`
- 新增能力：
  - 统一 `decision` 归一化（`final_answer` / `tool_call` / `invalid`）
  - 校验 `next_tool` 是否存在于可用工具列表
  - 校验并补齐 `tool_params` 的结构（含 required 缺失检查）
  - 对整数参数做轻量类型纠正（例如 `"3"` -> `3`）

## 2) ReAct 接口化事件流

- 文件：`src/Chatbot/tools/cline.py`
- `run_async()/run_react()` 新增接口能力：
  - `on_event`：结构化事件回调（attempt_start / decision / tool_call / tool_result / final_answer / error）
  - `on_thinking_chunk`：思考 token 回调
  - `use_stream_decide`：启用流式决策
  - `include_trace`：返回 ReAct trace（react_steps/tools）
  - `allow_fallback_synthesis`：迭代结束后基于观察结果兜底总结最终答案
- 返回结果仍保持兼容：
  - `{"type": ..., "result": ..., "history": ...}`

## 3) 工具发现与执行分层

- 文件：`src/Chatbot/tools/cline.py`
- 新增 `_discover_tools()`：
  - 本地工具优先走缓存 bootstrap
  - 可选合并远程 MCP 工具
  - 远程/本地执行路径统一在 ReAct 主循环中处理

## 4) TaskExecutionAgent 接入统一 ReAct 接口

- 文件：`src/Chatbot/agents/task_execution_agent.py`
- `_run_with_progress()` 改为直接调用 `ClineOrchestrator.run_react()` 并使用回调分发进度：
  - 思考中（节流）
  - 决策结果
  - 工具调用
  - 工具执行结果
  - 错误

这样避免了任务执行层重复实现一套 ReAct 循环逻辑。

## 5) 兼容性与降级

- 决策解析失败或动作无效时，不会直接崩溃，而是返回 `invalid` 并进入可控降级路径
- 连续重复相同工具调用会被识别为异常决策，避免死循环
- 保留历史结构与现有上层调用方式，尽量减少对现有接口影响

## 6) 任务流与SSE对齐

- 文件：`src/Chatbot/agents/chat_agent.py`
  - 修复任务结果流可能无限等待的问题：按期望任务数消费 `stream_results(limit=...)`
  - 规划器无子任务或数据库失败时，自动降级为可执行的内存任务，保证 ReAct 仍可运行
- 文件：`src/Chatbot/agents/task_execution_agent.py`
  - 统一进度数据为 `react.v1` 结构（`schema_version/react_event`）
  - 修复任务状态更新字段映射（`task_id/task_sub_id`）
- 文件：`fastapi_app/routers/tasks.py`
  - SSE 接口新增 `include_thinking` 参数，支持按需返回思考过程

## 7) ReAct 运行参数配置化

- 文件：`config/settings.py`
- 新增配置：
  - `REACT_MAX_ATTEMPTS`
  - `REACT_INCLUDE_TRACE`
  - `REACT_ALLOW_FALLBACK_SYNTHESIS`
  - `REACT_MAX_CONSECUTIVE_INVALID`
  - `REACT_PROGRESS_INCLUDE_THINKING_DEFAULT`

## 8) 端到端冒烟脚本

- 文件：`scripts/react_task_sse_smoke.py`
- 用途：验证 “提交任务 -> ReAct 执行 -> SSE 进度/结果” 链路是否可用
- 示例：
  - `python3 scripts/react_task_sse_smoke.py --base-url http://127.0.0.1:8000`
