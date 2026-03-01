"""
共享运行时 Provider（类 React Context Provider 思路）

统一管理重型单例实例，避免各 Router 重复维护局部全局变量。
"""
from __future__ import annotations

import inspect
import logging
from threading import Lock
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

_runtime_instances: Dict[str, Any] = {}
_runtime_lock = Lock()


def _get_or_create(name: str, factory: Callable[[], Any]) -> Optional[Any]:
    with _runtime_lock:
        existing = _runtime_instances.get(name)
        if existing is not None:
            return existing
        try:
            instance = factory()
        except Exception as e:
            logger.error("初始化 provider 失败 [%s]: %s", name, e)
            return None
        _runtime_instances[name] = instance
        return instance


def get_chatbot_agent():
    """获取共享 ChatbotAgent 实例（懒加载）"""
    from src.Chatbot.agents.chat_agent import ChatbotAgent

    return _get_or_create("chatbot_agent", ChatbotAgent)


def get_tts_agent():
    """获取共享 TextToSpeechAgent 实例（懒加载）"""
    from src.Chatbot.agents.text_to_speech_agent import TextToSpeechAgent

    return _get_or_create("tts_agent", TextToSpeechAgent)


def get_voice_recognition_agent():
    """获取共享 VoiceRecognitionAgent 实例（懒加载）"""
    from src.Chatbot.agents.voice_recognition_agent import VoiceRecognitionAgent

    return _get_or_create("voice_recognition_agent", VoiceRecognitionAgent)


def runtime_snapshot() -> Dict[str, bool]:
    """返回 provider 当前缓存状态（仅用于健康检查/调试）"""
    with _runtime_lock:
        keys = ("chatbot_agent", "tts_agent", "voice_recognition_agent")
        return {key: _runtime_instances.get(key) is not None for key in keys}


async def shutdown_runtime_instances() -> None:
    """关闭并清空 provider 缓存实例"""
    with _runtime_lock:
        items = list(_runtime_instances.items())
        _runtime_instances.clear()

    for name, instance in reversed(items):
        if instance is None:
            continue
        for method_name in ("shutdown", "cleanup"):
            method = getattr(instance, method_name, None)
            if not callable(method):
                continue
            try:
                result = method()
                if inspect.isawaitable(result):
                    await result
            except Exception as e:
                logger.warning("Provider 资源释放失败 [%s.%s]: %s", name, method_name, e)
