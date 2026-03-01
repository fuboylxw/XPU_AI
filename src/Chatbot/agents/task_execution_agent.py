from typing import Any, Dict, List, Optional, AsyncGenerator
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime

from src.Chatbot.tools.cline import ClineOrchestrator
from fastapi_app.database import SessionLocal
from fastapi_app.models import WorkTask, WorkSubTask
from src.Chatbot.utils.logger import setup_logger
from config.settings import settings

logger = setup_logger("task_exec_agent")

@dataclass
class TaskItem:
    id: int
    conversation_id: str
    title: str
    query: str
    intent_analysis: Dict[str, Any] | None = None
    is_subtask: bool = False

@dataclass
class TaskProgress:
    """任务进度数据"""
    task_id: int
    conversation_id: str
    title: str
    status: str  # waiting, executing, done, failure
    progress_type: str  # decision, tool_call, result, error
    data: Dict[str, Any]
    timestamp: str

class TaskExecutionAgent:
    _instance: Optional["TaskExecutionAgent"] = None

    def __init__(self) -> None:
        self.queue: asyncio.Queue[TaskItem] = asyncio.Queue()
        self.result_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self.progress_listeners: Dict[str, List[asyncio.Queue]] = {}  # 按会话ID分发的进度监听队列
        self._runner_started = False
        self.orchestrator = ClineOrchestrator()
        self.session_queues: Dict[str, asyncio.Queue[TaskItem]] = {}
        self.session_workers: Dict[str, asyncio.Task] = {}

    @classmethod
    def get_instance(cls) -> "TaskExecutionAgent":
        if cls._instance is None:
            cls._instance = TaskExecutionAgent()
        return cls._instance

    async def add_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        for t in tasks:
            item = TaskItem(
                id=int(t["id"]),
                conversation_id=str(t["conversation_id"]),
                title=str(t.get("title") or "任务"),
                query=str(t.get("query") or ""),
                intent_analysis=t.get("intent_analysis") or {},
                is_subtask=t.get("is_subtask", False)
            )
            await self._enqueue_session(item)

    async def _enqueue_session(self, item: TaskItem) -> None:
        cid = item.conversation_id
        if cid not in self.session_queues:
            self.session_queues[cid] = asyncio.Queue()
        await self.session_queues[cid].put(item)
        if cid not in self.session_workers:
            try:
                loop = asyncio.get_running_loop()
                self.session_workers[cid] = loop.create_task(self._session_run_loop(cid))
            except RuntimeError:
                pass

    async def _update_status(self, task_id: int, status: str, result_text: Optional[str] = None, is_subtask: bool = False) -> None:
        db = SessionLocal()
        try:
            if is_subtask:
                obj = db.query(WorkSubTask).filter(WorkSubTask.task_sub_id == task_id).first()
            else:
                obj = db.query(WorkTask).filter(WorkTask.task_id == task_id).first()
            
            if obj:
                obj.status = status
                if result_text is not None:
                    obj.result = result_text
                db.add(obj)
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    async def _emit_progress(self, task: TaskItem, progress_type: str, status: str, data: Dict[str, Any]) -> None:
        """发送进度更新"""
        payload = dict(data or {})
        payload.setdefault("schema_version", "react.v1")
        payload.setdefault("react_event", progress_type)
        payload.setdefault("conversation_id", task.conversation_id)
        payload.setdefault("task_id", task.id)
        payload.setdefault("task_title", task.title)

        progress = TaskProgress(
            task_id=task.id,
            conversation_id=task.conversation_id,
            title=task.title,
            status=status,
            progress_type=progress_type,
            data=payload,
            timestamp=datetime.now().isoformat()
        )
        
        # 分发给该会话的所有监听者
        cid = task.conversation_id
        if cid in self.progress_listeners:
            for q in self.progress_listeners[cid]:
                await q.put(progress)

    async def _run_loop(self) -> None:
        while True:
            task: TaskItem = await self.queue.get()
            await self._update_status(task.id, "executing", is_subtask=task.is_subtask)
            
            # 发送任务开始进度
            await self._emit_progress(
                task, "start", "executing",
                {"message": f"开始执行任务: {task.query}"}
            )
            
            final_seg = ""
            try:
                logger.info(f"执行任务: {task.query}")
                
                # 使用带进度回调的执行方法
                proc = await self._run_with_progress(task)
                
                result_data = proc.get("result", {})
                ans = result_data.get("answer") or ""
                if not ans:
                    ans = json.dumps(result_data, ensure_ascii=False)
                final_seg = ans
                
                await self._update_status(task.id, "done", final_seg, is_subtask=task.is_subtask)
                
                # 发送最终结果进度
                await self._emit_progress(
                    task, "result", "done",
                    {"result": final_seg, "history": proc.get("history", [])}
                )
                
                await self.result_queue.put({
                    "task_id": task.id,
                    "conversation_id": task.conversation_id,
                    "title": task.title,
                    "result": final_seg,
                })
            except Exception as e:
                err = str(e)
                await self._update_status(task.id, "failure", err, is_subtask=task.is_subtask)
                
                # 发送错误进度
                await self._emit_progress(
                    task, "error", "failure",
                    {"error": err}
                )
                
                await self.result_queue.put({
                    "task_id": task.id,
                    "conversation_id": task.conversation_id,
                    "title": task.title,
                    "error": err,
                })
            await asyncio.sleep(0.001)

    async def _session_run_loop(self, conversation_id: str) -> None:
        q = self.session_queues.get(conversation_id)
        if q is None:
            self.session_queues[conversation_id] = asyncio.Queue()
            q = self.session_queues[conversation_id]
        while True:
            task: TaskItem = await q.get()
            await self._update_status(task.id, "executing", is_subtask=task.is_subtask)
            await self._emit_progress(
                task, "start", "executing",
                {"message": f"开始执行任务: {task.query}"}
            )
            final_seg = ""
            try:
                logger.info(f"执行任务: {task.query}")
                proc = await self._run_with_progress(task)
                result_data = proc.get("result", {})
                ans = result_data.get("answer") or ""
                if not ans:
                    ans = json.dumps(result_data, ensure_ascii=False)
                final_seg = ans
                await self._update_status(task.id, "done", final_seg, is_subtask=task.is_subtask)
                await self._emit_progress(
                    task, "result", "done",
                    {"result": final_seg, "history": proc.get("history", [])}
                )
                await self.result_queue.put({
                    "task_id": task.id,
                    "conversation_id": task.conversation_id,
                    "title": task.title,
                    "result": final_seg,
                })
            except Exception as e:
                err = str(e)
                await self._update_status(task.id, "failure", err, is_subtask=task.is_subtask)
                await self._emit_progress(
                    task, "error", "failure",
                    {"error": err}
                )
                await self.result_queue.put({
                    "task_id": task.id,
                    "conversation_id": task.conversation_id,
                    "title": task.title,
                    "error": err,
                })
            await asyncio.sleep(0.001)

    async def _run_with_progress(self, task: TaskItem) -> Dict[str, Any]:
        """执行任务并发送进度更新（基于统一 ReAct 接口）"""
        state = {"tools": [], "react_steps": []}
        intent = task.intent_analysis or {}
        max_attempts = max(1, int(getattr(settings, "REACT_MAX_ATTEMPTS", 6)))

        thinking_enabled = settings.STREAM_THINKING_ENABLED and not settings.STREAM_DECISION_ONLY
        throttle_ms = max(50, int(settings.STREAM_THINKING_THROTTLE_MS))
        max_buffer = max(50, int(settings.STREAM_THINKING_MAX_BUFFER))
        thinking_buffer = ""
        last_emit_ts = datetime.now().timestamp()
        current_attempt = 1

        async def _on_thinking_chunk(token: str):
            if not thinking_enabled or not token:
                return
            nonlocal thinking_buffer, last_emit_ts, current_attempt
            thinking_buffer += token
            now_ts = datetime.now().timestamp()
            elapsed_ms = int((now_ts - last_emit_ts) * 1000)
            if elapsed_ms >= throttle_ms or len(thinking_buffer) >= max_buffer:
                await self._emit_progress(
                    task,
                    "thinking",
                    "executing",
                    {"attempt": current_attempt, "detail": thinking_buffer},
                )
                thinking_buffer = ""
                last_emit_ts = now_ts

        async def _on_event(event: Dict[str, Any]):
            nonlocal current_attempt, thinking_buffer
            event_type = event.get("type")
            attempt = int(event.get("attempt") or current_attempt)
            current_attempt = attempt

            if event_type == "attempt_start":
                await self._emit_progress(
                    task,
                    "thinking",
                    "executing",
                    {"attempt": attempt, "message": "AI正在思考决策..."},
                )
                return

            if event_type == "decision":
                decision = event.get("decision") or {}
                await self._emit_progress(
                    task,
                    "decision",
                    "executing",
                    {
                        "attempt": attempt,
                        "action": decision.get("action"),
                        "reasoning": decision.get("reasoning", ""),
                        "decision": decision,
                    },
                )
                return

            if event_type == "tool_call":
                tool_name = event.get("tool")
                tool_params = event.get("params") or {}
                await self._emit_progress(
                    task,
                    "tool_call",
                    "executing",
                    {
                        "attempt": attempt,
                        "tool": tool_name,
                        "params": tool_params,
                        "message": f"正在调用工具: {tool_name}",
                    },
                )
                return

            if event_type == "tool_result":
                tool_name = event.get("tool")
                tool_result = event.get("result") or {}
                await self._emit_progress(
                    task,
                    "tool_result",
                    "executing",
                    {
                        "attempt": attempt,
                        "tool": tool_name,
                        "result": tool_result,
                        "message": f"工具 {tool_name} 执行完成",
                    },
                )
                return

            if event_type == "error":
                await self._emit_progress(
                    task,
                    "error",
                    "executing",
                    {"attempt": attempt, "error": event.get("error")},
                )
                return

            if event_type == "final_answer" and thinking_buffer:
                await self._emit_progress(
                    task,
                    "thinking",
                    "executing",
                    {"attempt": attempt, "detail": thinking_buffer},
                )
                thinking_buffer = ""

        result = await self.orchestrator.run_react(
            question=task.query,
            max_attempts=max_attempts,
            intent=intent,
            state=state,
            on_event=_on_event,
            on_thinking_chunk=_on_thinking_chunk if thinking_enabled else None,
            use_stream_decide=thinking_enabled,
            include_trace=bool(getattr(settings, "REACT_INCLUDE_TRACE", False)),
            allow_fallback_synthesis=bool(getattr(settings, "REACT_ALLOW_FALLBACK_SYNTHESIS", True)),
            max_consecutive_invalid=max(
                1, int(getattr(settings, "REACT_MAX_CONSECUTIVE_INVALID", 2))
            ),
        )

        # flush 残余思考 token
        if thinking_enabled and thinking_buffer:
            await self._emit_progress(
                task,
                "thinking",
                "executing",
                {"attempt": current_attempt, "detail": thinking_buffer},
            )

        return result

    async def stream_results(self, conversation_id: Optional[str] = None, limit: Optional[int] = None):
        """流式返回任务最终结果"""
        delivered = 0
        while True:
            data = await self.result_queue.get()
            if not conversation_id or data.get("conversation_id") == conversation_id:
                yield data
                delivered += 1
                if limit is not None and delivered >= limit:
                    break
            await asyncio.sleep(0.001)

    async def stream_progress(self, conversation_id: Optional[str] = None, task_id: Optional[int] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """流式返回任务执行进度
        
        Args:
            conversation_id: 会话ID，用于过滤特定会话的进度
            task_id: 任务ID，用于过滤特定任务的进度
            
        Yields:
            进度数据字典
        """
        # 创建新的监听队列
        q = asyncio.Queue()
        
        # 注册监听
        if conversation_id:
            if conversation_id not in self.progress_listeners:
                self.progress_listeners[conversation_id] = []
            self.progress_listeners[conversation_id].append(q)
            
        try:
            while True:
                progress: TaskProgress = await q.get()
                
                # task_id filter
                if task_id and progress.task_id != task_id:
                    continue
                
                # 转换为字典格式
                yield {
                    "task_id": progress.task_id,
                    "conversation_id": progress.conversation_id,
                    "title": progress.title,
                    "status": progress.status,
                    "progress_type": progress.progress_type,
                    "data": progress.data,
                    "timestamp": progress.timestamp
                }
        finally:
            # 清理监听
            if conversation_id and conversation_id in self.progress_listeners:
                if q in self.progress_listeners[conversation_id]:
                    self.progress_listeners[conversation_id].remove(q)
                if not self.progress_listeners[conversation_id]:
                    del self.progress_listeners[conversation_id]
