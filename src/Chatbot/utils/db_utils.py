import pymysql
import redis
import json
import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理类，用于处理MySQL和Redis连接"""

    def __init__(
        self,
        mysql_host: str = None,
        mysql_port: int = None,
        mysql_user: str = None,
        mysql_password: str = None,
        mysql_db: str = None,
        redis_host: str = None,
        redis_port: int = None,
        redis_password: str = None,
        redis_db: int = None,
    ):
        """初始化数据库连接"""
        # 从环境变量读取配置，如果没有提供参数的话
        self.mysql_config = {
            "host": mysql_host or os.getenv("MYSQL_HOST", "localhost"),
            "port": mysql_port or int(os.getenv("MYSQL_PORT", "3306")),
            "user": mysql_user or os.getenv("MYSQL_USER", "root"),
            "password": mysql_password or os.getenv("MYSQL_PASSWORD", ""),
            "db": mysql_db or os.getenv("MYSQL_DB", "chatbot"),
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor,
        }

        self.redis_config = {
            "host": redis_host or os.getenv("REDIS_HOST", "localhost"),
            "port": redis_port or int(os.getenv("REDIS_PORT", "6379")),
            "password": redis_password or os.getenv("REDIS_PASSWORD", ""),
            "db": redis_db or int(os.getenv("REDIS_DB", "0")),
            "decode_responses": True,
        }

        # 初始化连接
        self._mysql_conn = None
        self._redis_conn = None

    def get_mysql_connection(self):
        """获取MySQL连接"""
        try:
            if self._mysql_conn is None or not self._mysql_conn.open:
                self._mysql_conn = pymysql.connect(**self.mysql_config)
            return self._mysql_conn
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            raise

    def get_redis_connection(self):
        """获取Redis连接"""
        try:
            if self._redis_conn is None:
                self._redis_conn = redis.Redis(**self.redis_config)
            return self._redis_conn
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise

    def close_connections(self):
        """关闭所有数据库连接"""
        if self._mysql_conn and self._mysql_conn.open:
            self._mysql_conn.close()

        if self._redis_conn:
            self._redis_conn.close()

    def ensure_conversation_exists(
        self, conversation_id: str, user_id: str = "default_user", title: str = None
    ) -> bool:
        """
        确保conversation表中存在指定会话ID的记录

        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            title: 会话标题

        Returns:
            是否成功
        """
        try:
            conn = self.get_mysql_connection()
            with conn.cursor() as cursor:
                # 检查是否存在
                sql = "SELECT id FROM conversation WHERE conversation_id = %s"
                cursor.execute(sql, (conversation_id,))
                if not cursor.fetchone():
                    # 不存在则创建
                    if not title:
                        title = f"会话 {conversation_id[:8]}"

                    # 使用UUID作为id字段值，而不是使用conversation_id
                    import uuid

                    unique_id = uuid.uuid4().hex

                    sql = """
                    INSERT INTO conversation 
                    (id, conversation_id, user_id, title, created, modified, status) 
                    VALUES (%s, %s, %s, %s, NOW(), NOW(), 1)
                    """
                    cursor.execute(sql, (unique_id, conversation_id, user_id, title))
                    conn.commit()
                    logger.info(f"创建新会话记录: {conversation_id}, id: {unique_id}")
                return True
        except Exception as e:
            logger.error(f"确保会话存在失败: {e}")
            return False

    def get_conversation_history(
        self, conversation_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取对话历史记录，通过关联conversation和conversation_history表

        Args:
            conversation_id: 对话ID
            limit: 获取最近的几条记录

        Returns:
            对话历史记录列表
        """
        # 先尝试从Redis缓存获取
        redis_key = f"conversation:{conversation_id}"
        redis_conn = self.get_redis_connection()

        cached_data = redis_conn.get(redis_key)
        if cached_data:
            try:
                return json.loads(cached_data)[-limit:]
            except Exception as e:
                logger.warning(f"Redis缓存数据解析失败: {e}")

        # 从MySQL数据库获取，使用JOIN关联两个表
        try:
            conn = self.get_mysql_connection()
            with conn.cursor() as cursor:
                # 确保conversation表中存在该会话
                self.ensure_conversation_exists(conversation_id)

                # 使用JOIN查询
                sql = """
                SELECT c.title, ch.question, ch.answer, ch.created_at 
                FROM conversation c
                JOIN conversation_history ch ON c.conversation_id = ch.conversation_id
                WHERE c.conversation_id = %s 
                ORDER BY ch.created_at DESC 
                LIMIT %s
                """
                cursor.execute(sql, (conversation_id, limit))
                results = cursor.fetchall()

                # 如果JOIN查询没有结果，回退到直接查询conversation_history表
                if not results:
                    sql = """
                    SELECT question, answer, created_at 
                    FROM conversation_history 
                    WHERE conversation_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                    """
                    cursor.execute(sql, (conversation_id, limit))
                    results = cursor.fetchall()

                # 转换结果格式
                conversation_history = []
                for row in reversed(results):  # 反转结果以按时间正序排列
                    history_item = {
                        "question": row["question"],
                        "answer": row["answer"],
                        "timestamp": row["created_at"].isoformat()
                        if hasattr(row["created_at"], "isoformat")
                        else str(row["created_at"]),
                    }
                    # 如果有title字段，添加到结果中
                    if "title" in row and row["title"]:
                        history_item["title"] = row["title"]

                    conversation_history.append(history_item)

                # 更新Redis缓存
                redis_conn.setex(
                    redis_key, 3600, json.dumps(conversation_history)  # 缓存1小时
                )

                return conversation_history

        except Exception as e:
            logger.error(f"获取对话历史记录失败: {e}")
            return []

    def save_conversation(
        self,
        conversation_id: str,
        question: str,
        answer: str,
        user_id: str = "default_user",
        title: str = None,
    ) -> bool:
        """
        保存对话记录到数据库，并更新conversation表的最后会话时间

        Args:
            conversation_id: 对话ID
            question: 用户问题
            answer: 系统回答
            user_id: 用户ID
            title: 会话标题

        Returns:
            是否保存成功
        """
        try:
            # 确保conversation表中存在该会话
            self.ensure_conversation_exists(conversation_id, user_id, title)

            # 保存到MySQL
            conn = self.get_mysql_connection()
            with conn.cursor() as cursor:
                # 插入对话历史
                sql = """
                INSERT INTO conversation_history 
                (conversation_id, question, answer) 
                VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (conversation_id, question, answer))

                # 更新conversation表的modified字段（最后会话时间）
                sql = """
                UPDATE conversation 
                SET modified = NOW() 
                WHERE conversation_id = %s
                """
                cursor.execute(sql, (conversation_id,))

            conn.commit()

            # 更新Redis缓存
            redis_key = f"conversation:{conversation_id}"
            redis_conn = self.get_redis_connection()

            # 获取现有缓存
            cached_data = redis_conn.get(redis_key)
            if cached_data:
                try:
                    conversation_history = json.loads(cached_data)
                    conversation_history.append(
                        {
                            "question": question,
                            "answer": answer,
                            "timestamp": None,  # 数据库会自动添加时间戳
                        }
                    )

                    # 更新缓存
                    redis_conn.setex(
                        redis_key, 3600, json.dumps(conversation_history)  # 缓存1小时
                    )
                except Exception as e:
                    logger.warning(f"更新Redis缓存失败: {e}")

            return True

        except Exception as e:
            logger.error(f"保存对话记录失败: {e}")
            return False

    def save_conversation_with_id(
        self,
        conversation_id: str,
        question: str,
        user_id: str = "default_user",
        title: str = None,
    ) -> Optional[int]:
        """
        保存问题到数据库并返回记录ID，用于后续更新答案

        Args:
            conversation_id: 对话ID
            question: 用户问题
            user_id: 用户ID
            title: 会话标题

        Returns:
            对话历史记录的ID，失败返回None
        """
        try:
            # 确保conversation表中存在该会话
            self.ensure_conversation_exists(conversation_id, user_id, title)

            # 保存到MySQL
            conn = self.get_mysql_connection()
            with conn.cursor() as cursor:
                # 插入对话历史，答案先为空
                sql = """
                INSERT INTO conversation_history 
                (conversation_id, question, answer) 
                VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (conversation_id, question, ""))
                
                # 获取插入的记录ID
                record_id = cursor.lastrowid

                # 更新conversation表的modified字段（最后会话时间）
                sql = """
                UPDATE conversation 
                SET modified = NOW() 
                WHERE conversation_id = %s
                """
                cursor.execute(sql, (conversation_id,))

            conn.commit()
            return record_id

        except Exception as e:
            logger.error(f"保存问题到数据库失败: {e}")
            return None

    def update_conversation_answer(
        self,
        record_id: int,
        answer: str,
        conversation_id: str = None,
    ) -> bool:
        """
        更新对话记录的答案

        Args:
            record_id: 对话历史记录ID
            answer: 系统回答
            conversation_id: 对话ID（可选，用于更新Redis缓存）

        Returns:
            是否更新成功
        """
        try:
            # 更新MySQL
            conn = self.get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                UPDATE conversation_history 
                SET answer = %s 
                WHERE id = %s
                """
                cursor.execute(sql, (answer, record_id))

            conn.commit()

            # 如果提供了conversation_id，更新Redis缓存
            if conversation_id:
                try:
                    redis_key = f"conversation:{conversation_id}"
                    redis_conn = self.get_redis_connection()
                    
                    # 获取现有缓存
                    cached_data = redis_conn.get(redis_key)
                    if cached_data:
                        conversation_history = json.loads(cached_data)
                        # 更新最后一条记录的答案
                        if conversation_history:
                            conversation_history[-1]["answer"] = answer
                            
                            # 更新缓存
                            redis_conn.setex(
                                redis_key, 3600, json.dumps(conversation_history)  # 缓存1小时
                            )
                except Exception as e:
                    logger.warning(f"更新Redis缓存失败: {e}")

            return True

        except Exception as e:
            logger.error(f"更新对话答案失败: {e}")
            return False


# 单例模式
_db_manager = None


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器单例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager