"""
日志模块 - 提供统一的日志记录功能
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# 日志级别映射
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

# 默认日志格式
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logger(name, log_file=None, level="info", max_bytes=10485760, backup_count=5):
    """
    设置并返回一个日志记录器

    参数:
        name (str): 日志记录器名称
        log_file (str, optional): 日志文件路径，如果为None则只输出到控制台
        level (str, optional): 日志级别，默认为"info"
        max_bytes (int, optional): 单个日志文件最大字节数，默认为10MB
        backup_count (int, optional): 备份文件数量，默认为5

    返回:
        logging.Logger: 配置好的日志记录器
    """
    # 获取日志级别
    log_level = LOG_LEVELS.get(level.lower(), logging.INFO)

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # 如果已经有处理器，不再添加
    if logger.handlers:
        return logger

    # 创建格式化器
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 如果指定了日志文件，添加文件处理器
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 创建滚动文件处理器
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 创建默认日志记录器
default_logger = setup_logger("chatbi", log_file="logs/chatbi.log", level="info")


def get_logger(name=None):
    """
    获取一个日志记录器

    参数:
        name (str, optional): 日志记录器名称，如果为None则返回默认日志记录器

    返回:
        logging.Logger: 日志记录器
    """
    if name is None:
        return default_logger
    return setup_logger(name)
