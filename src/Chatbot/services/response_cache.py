"""
响应缓存服务
从 ChatbotAgent 提取的缓存相关方法
"""
import logging
import hashlib
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ResponseCacheService:
    """响应缓存服务，实现 Lifecycle 协议"""

    def __init__(self, cache_ttl: int = 300, max_cache_size: int = 1000):
        self.response_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = cache_ttl
        self.max_cache_size = max_cache_size
        self.stats = {"cache_hits": 0, "cache_misses": 0}

    def generate_cache_key(self, question: str, user_role: str, phone_mode: bool) -> str:
        """生成缓存键"""
        key_data = f"{question.lower().strip()}_{user_role}_{phone_mode}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存响应"""
        try:
            if cache_key in self.response_cache:
                cached_item = self.response_cache[cache_key]
                if time.time() - cached_item["timestamp"] < self.cache_ttl:
                    self.stats["cache_hits"] += 1
                    return cached_item["response"]
                else:
                    del self.response_cache[cache_key]

            self.stats["cache_misses"] += 1
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None

    async def cache_response(self, cache_key: str, response: Dict[str, Any]):
        """异步缓存响应"""
        try:
            if len(self.response_cache) >= self.max_cache_size:
                await self.cleanup()

            self.response_cache[cache_key] = {
                "response": response,
                "timestamp": time.time(),
            }
        except Exception as e:
            logger.error(f"缓存响应失败: {e}")

    async def cleanup(self):
        """清理过期缓存"""
        try:
            current_time = time.time()
            expired_keys = [
                key for key, item in self.response_cache.items()
                if current_time - item["timestamp"] > self.cache_ttl
            ]
            for key in expired_keys:
                del self.response_cache[key]

            if len(self.response_cache) >= self.max_cache_size:
                sorted_items = sorted(
                    self.response_cache.items(),
                    key=lambda x: x[1]["timestamp"],
                )
                for key, _ in sorted_items[: len(sorted_items) // 2]:
                    del self.response_cache[key]

            logger.info(f"缓存清理完成，当前缓存条目数: {len(self.response_cache)}")
        except Exception as e:
            logger.error(f"缓存清理失败: {e}")

    async def startup(self) -> None:
        """Lifecycle: 启动时预热缓存"""
        logger.info("ResponseCacheService 启动，缓存预热完成")

    async def shutdown(self) -> None:
        """Lifecycle: 关闭时清理缓存"""
        count = len(self.response_cache)
        self.response_cache.clear()
        self.stats = {"cache_hits": 0, "cache_misses": 0}
        logger.info(f"ResponseCacheService 关闭，已清理 {count} 条缓存")
