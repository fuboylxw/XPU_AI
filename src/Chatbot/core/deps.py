"""
FastAPI 依赖注入函数
提供从容器获取组件的 Depends 函数
"""
from fastapi import Request
from src.Chatbot.core.container import Container, get_container


def get_app_container() -> Container:
    """FastAPI 依赖函数：获取应用容器"""
    return get_container()
