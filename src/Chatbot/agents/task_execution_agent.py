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
                obj = db.query(WorkSubTask).filter(WorkSubTask.id == task_id).first()
            else:
                obj = db.query(WorkTask).filter(WorkTask.id == task_id).first()
            
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
        progress = TaskProgress(
            task_id=task.id,
            conversation_id=task.conversation_id,
            title=task.title,
            status=status,
            progress_type=progress_type,
            data=data,
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
        """执行任务并发送进度更新"""
        state = {"tools": []}
        intent = task.intent_analysis or {}
        max_attempts = 6
        history = []
        thinking_enabled = settings.STREAM_THINKING_ENABLED and not settings.STREAM_DECISION_ONLY
        throttle_ms = max(50, int(settings.STREAM_THINKING_THROTTLE_MS))
        max_buffer = max(50, int(settings.STREAM_THINKING_MAX_BUFFER))
        thinking_buffer = ""
        last_emit_ts = datetime.now().timestamp()
        
        for attempt in range(max_attempts):
            # 发送决策进度
            await self._emit_progress(
                task, "thinking", "executing",
                {"attempt": attempt + 1, "message": "AI正在思考决策..."}
            )
            
            # 执行决策（带流式思考回调，节流与合并）
            async def _on_thinking_chunk(token: str):
                if not thinking_enabled:
                    return
                nonlocal thinking_buffer, last_emit_ts
                if not token:
                    return
                thinking_buffer += token
                now_ts = datetime.now().timestamp()
                elapsed_ms = int((now_ts - last_emit_ts) * 1000)
                if elapsed_ms >= throttle_ms or len(thinking_buffer) >= max_buffer:
                    await self._emit_progress(
                        task, "thinking", "executing",
                        {"attempt": attempt + 1, "detail": thinking_buffer}
                    )
                    thinking_buffer = ""
                    last_emit_ts = now_ts

            decision = await self.orchestrator.run_decide_stream(
                question=task.query,
                intent=intent,
                state=state,
                tools=self.orchestrator._format_tools(),
                on_chunk=_on_thinking_chunk,
            )
            # 决策生成后，flush残余思考缓冲
            if thinking_enabled and thinking_buffer:
                await self._emit_progress(
                    task, "thinking", "executing",
                    {"attempt": attempt + 1, "detail": thinking_buffer}
                )
                thinking_buffer = ""
            
            # 发送决策结果进度
            await self._emit_progress(
                task, "decision", "executing",
                {
                    "attempt": attempt + 1,
                    "action": decision.get("action"),
                    "reasoning": decision.get("reasoning", ""),
                    "decision": decision
                }
            )
            
            action = decision.get("action")
            
            if action == "final_answer":
                answer = decision.get("answer") or decision.get("final_answer", "")
                return {
                    "type": intent.get("intent_class") or "general_answer",
                    "result": {"success": True, "answer": answer, "source": "llm"},
                    "history": history
                }
            
            if action == "tool_call":
                tool_name = decision.get("next_tool")
                tool_params = decision.get("tool_params") or {}
                
                # 发送工具调用进度
                await self._emit_progress(
                    task, "tool_call", "executing",
                    {
                        "attempt": attempt + 1,
                        "tool": tool_name,
                        "params": tool_params,
                        "message": f"正在调用工具: {tool_name}"
                    }
                )
                
                # 执行工具调用
                exec_res = await self.orchestrator.runner.registry.call(tool_name, tool_params)
                
                # 发送工具结果进度
                await self._emit_progress(
                    task, "tool_result", "executing",
                    {
                        "attempt": attempt + 1,
                        "tool": tool_name,
                        "result": exec_res,
                        "message": f"工具 {tool_name} 执行完成"
                    }
                )
                
                last_exec = {"tool": tool_name, "params": tool_params, "result": exec_res}
                history.append(last_exec)
                state['tools'].append({"name": tool_name, "result": exec_res})
                continue
        
        # 达到最大尝试次数
        if history:
            return {
                "type": intent.get("intent_class") or "general_answer",
                "result": history[-1].get("result") or {"success": False, "error": "Max attempts reached"},
                "history": history
            }
        
        return {
            "type": intent.get("intent_class") or "general_answer",
            "result": {"success": False, "error": "No attempts executed"},
            "history": history
        }

    async def stream_results(self, conversation_id: Optional[str] = None):
        """流式返回任务最终结果"""
        while True:
            data = await self.result_queue.get()
            if not conversation_id or data.get("conversation_id") == conversation_id:
                yield data
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
