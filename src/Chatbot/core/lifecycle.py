"""
组件生命周期协议与管理器
参考 opencode 的 onMount/onCleanup 模式：
1. service lifecycle：startup/shutdown
2. effect lifecycle：注册 setup，并在 cleanup 阶段逆序释放
"""
from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional, Protocol, Union, runtime_checkable

logger = logging.getLogger(__name__)

CleanupHandler = Callable[[], Union[Awaitable[None], None]]
SetupHandler = Callable[[], Union[Awaitable[Optional[CleanupHandler]], Optional[CleanupHandler]]]


@runtime_checkable
class Lifecycle(Protocol):
    """组件生命周期协议：所有需要启动/关闭管理的组件应实现此协议"""

    async def startup(self) -> None:
        """组件启动时调用"""
        ...

    async def shutdown(self) -> None:
        """组件关闭时调用"""
        ...


@dataclass
class EffectRegistration:
    """一次 effect 注册（setup + 可选 cleanup）"""

    name: str
    setup: SetupHandler
    cleanup: Optional[CleanupHandler] = None


class LifecycleManager:
    """
    轻量生命周期管理器，行为类似 React useEffect：
    - startup 时执行 setup
    - shutdown 时按逆序执行 cleanup
    """

    def __init__(self) -> None:
        self._effects: list[EffectRegistration] = []
        self._started = False

    @staticmethod
    async def _run_maybe_awaitable(result):
        if inspect.isawaitable(result):
            return await result
        return result

    def register_effect(self, name: str, setup: SetupHandler) -> None:
        """注册一个 effect setup；setup 可返回 cleanup 回调"""
        self._effects.append(EffectRegistration(name=name, setup=setup))

    async def startup(self) -> None:
        """按注册顺序执行 setup，并保存 cleanup"""
        if self._started:
            return

        for effect in self._effects:
            try:
                cleanup = await self._run_maybe_awaitable(effect.setup())
                if cleanup is not None and not callable(cleanup):
                    logger.warning("effect cleanup 不是可调用对象: %s", effect.name)
                    cleanup = None
                effect.cleanup = cleanup
            except Exception as e:
                logger.error("effect setup 失败 [%s]: %s", effect.name, e)
        self._started = True

    async def shutdown(self) -> None:
        """按逆序执行 cleanup"""
        if not self._started:
            return

        for effect in reversed(self._effects):
            if effect.cleanup is None:
                continue
            try:
                await self._run_maybe_awaitable(effect.cleanup())
            except Exception as e:
                logger.warning("effect cleanup 失败 [%s]: %s", effect.name, e)
            finally:
                effect.cleanup = None
        self._started = False
