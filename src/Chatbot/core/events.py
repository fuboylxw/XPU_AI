"""
异步事件总线
参考 opencode 的 createGlobalEmitter 事件流模式：
- on/once/off
- 订阅返回 unsubscribe
- 支持 * 通配符监听
"""
from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# 事件常量
CONVERSATION_MESSAGE_ADDED = "conversation.message.added"
CONVERSATION_CREATED = "conversation.created"
SYSTEM_STARTUP = "system.startup"
SYSTEM_SHUTDOWN = "system.shutdown"

Handler = Union[Callable[[Any], Awaitable[None]], Callable[[Any], None]]
Unsubscribe = Callable[[], None]


class EventBus:
    """异步事件总线（轻量、容错、可卸载）"""

    def __init__(self):
        self._handlers: Dict[str, List[Handler]] = {}

    def _resolve_handlers(self, event_name: str) -> List[Handler]:
        handlers: List[Handler] = []
        handlers.extend(self._handlers.get(event_name, []))
        # * 监听所有事件，行为类似全局订阅
        handlers.extend(self._handlers.get("*", []))
        return handlers

    async def _run_handler(self, event_name: str, handler: Handler, data: Any) -> None:
        try:
            result = handler(data)
            if inspect.isawaitable(result):
                await result
        except Exception as e:
            logger.error("事件处理器执行失败 [%s]: %s", event_name, e)

    def on(self, event_name: str, handler: Handler) -> Unsubscribe:
        """注册事件处理器，并返回可调用的 unsubscribe"""
        handlers = self._handlers.setdefault(event_name, [])
        handlers.append(handler)

        def _unsubscribe() -> None:
            self.off(event_name, handler)

        return _unsubscribe

    def once(self, event_name: str, handler: Handler) -> Unsubscribe:
        """注册一次性处理器，触发一次后自动移除"""
        unsubscribe_ref: Dict[str, Optional[Unsubscribe]] = {"fn": None}

        async def _once(data: Any) -> None:
            fn = unsubscribe_ref["fn"]
            if fn is not None:
                fn()
            result = handler(data)
            if inspect.isawaitable(result):
                await result

        unsubscribe_ref["fn"] = self.on(event_name, _once)
        return unsubscribe_ref["fn"]  # type: ignore[return-value]

    def off(self, event_name: str, handler: Handler) -> None:
        """移除事件处理器"""
        if event_name not in self._handlers:
            return
        try:
            self._handlers[event_name].remove(handler)
        except ValueError:
            return
        if not self._handlers[event_name]:
            del self._handlers[event_name]

    async def emit(self, event_name: str, data: Any = None, concurrent: bool = False) -> None:
        """触发事件；默认顺序执行，可选并发执行"""
        handlers = list(self._resolve_handlers(event_name))
        if not handlers:
            return

        if concurrent:
            await asyncio.gather(
                *(self._run_handler(event_name, handler, data) for handler in handlers),
                return_exceptions=True,
            )
            return

        for handler in handlers:
            await self._run_handler(event_name, handler, data)

    def emit_nowait(self, event_name: str, data: Any = None, concurrent: bool = True) -> None:
        """非阻塞触发事件（在后台任务中执行）"""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.emit(event_name, data, concurrent=concurrent))
        except RuntimeError:
            logger.warning("无法触发事件 %s：事件循环未运行", event_name)

    def clear(self, event_name: Optional[str] = None) -> None:
        """清空某个事件（或全部事件）处理器"""
        if event_name is None:
            self._handlers.clear()
            return
        self._handlers.pop(event_name, None)

    def listener_count(self, event_name: Optional[str] = None) -> int:
        """获取监听器数量"""
        if event_name is None:
            return sum(len(v) for v in self._handlers.values())
        return len(self._handlers.get(event_name, []))


# 全局事件总线实例
event_bus = EventBus()
