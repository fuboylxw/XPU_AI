import pymysql
import redis
import json
import logging
import os
from config.settings import settings
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
            "host": mysql_host or settings.MYSQL_HOST,
            "port": mysql_port or settings.MYSQL_PORT,
            "user": mysql_user or settings.MYSQL_USER,
            "password": mysql_password or settings.MYSQL_PASSWORD,
            "db": mysql_db or settings.MYSQL_DATABASE,
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor,
        }

        self.redis_config = {
            "host": redis_host or settings.REDIS_HOST,
            "port": redis_port or settings.REDIS_PORT,
            "password": redis_password or settings.REDIS_PASSWORD,
            "db": redis_db or settings.REDIS_DB,
            "decode_responses": True,
        }

        # 初始化连接
        self._mysql_conn = None
        self._redis_conn = None

        # 确保conversation表存在
        self._ensure_conversation_table()

    def _ensure_conversation_table(self):
        """确保conversation表存在"""
        try:
            conn = self.get_mysql_connection()
            with conn.cursor() as cursor:
                # 检查表是否存在
                cursor.execute("SHOW TABLES LIKE 'conversation'")
                if not cursor.fetchone():
                    # 创建conversation表
                    create_table_sql = """
                    CREATE TABLE IF NOT EXISTS conversation (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        conversation_id VARCHAR(50) NOT NULL UNIQUE,
                        user_id VARCHAR(50),
                        title VARCHAR(255) DEFAULT '新对话',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_conversation_id (conversation_id),
                        INDEX idx_user_id (user_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                    cursor.execute(create_table_sql)

                    # 从现有conversation_history表提取唯一的conversation_id并插入到conversation表
                    migrate_data_sql = """
                    INSERT IGNORE INTO conversation (conversation_id, created_at)
                    SELECT DISTINCT conversation_id, MIN(created_at) 
                    FROM conversation_history
                    GROUP BY conversation_id;
                    """
                    cursor.execute(migrate_data_sql)
                    conn.commit()
                    logger.info("已创建conversation表并迁移数据")
        except Exception as e:
            logger.error(f"确保conversation表存在时出错: {e}")

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

    def get_conversation_history(
        self, conversation_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取对话历史记录

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

        # 从MySQL数据库获取
        try:
            conn = self.get_mysql_connection()
            with conn.cursor() as cursor:
                # 先确保conversation表中有此会话ID
                self._ensure_conversation_exists(cursor, conversation_id)

                # 关联查询
                sql = """
                SELECT ch.question, ch.answer, ch.created_at, c.title, c.user_id
                FROM conversation_history ch
                JOIN conversation c ON ch.conversation_id = c.conversation_id
                WHERE ch.conversation_id = %s
                ORDER BY ch.created_at DESC
                LIMIT %s
                """
                cursor.execute(sql, (conversation_id, limit))
                results = cursor.fetchall()

                # 转换结果格式
                conversation_history = []
                for row in reversed(results):  # 反转结果以按时间正序排列
                    conversation_history.append(
                        {
                            "question": row["question"],
                            "answer": row["answer"],
                            "timestamp": row["created_at"].isoformat()
                            if hasattr(row["created_at"], "isoformat")
                            else str(row["created_at"]),
                            "title": row["title"],
                            "user_id": row["user_id"],
                        }
                    )

                # 更新Redis缓存
                redis_conn.setex(
                    redis_key, 3600, json.dumps(conversation_history)  # 缓存1小时
                )

                return conversation_history

        except Exception as e:
            logger.error(f"获取对话历史记录失败: {e}")
            # 如果关联查询失败，回退到原始查询
            return self._get_conversation_history_fallback(conversation_id, limit)

    def _get_conversation_history_fallback(
        self, conversation_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """获取对话历史记录的回退方法（不使用关联查询）"""
        try:
            conn = self.get_mysql_connection()
            with conn.cursor() as cursor:
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
                    conversation_history.append(
                        {
                            "question": row["question"],
                            "answer": row["answer"],
                            "timestamp": row["created_at"].isoformat()
                            if hasattr(row["created_at"], "isoformat")
                            else str(row["created_at"]),
                        }
                    )

                return conversation_history

        except Exception as e:
            logger.error(f"回退获取对话历史记录失败: {e}")
            return []

    def _ensure_conversation_exists(self, cursor, conversation_id: str):
        """确保conversation表中存在指定的会话ID"""
        cursor.execute(
            "SELECT 1 FROM conversation WHERE conversation_id = %s", (conversation_id,)
        )
        if not cursor.fetchone():
            # 如果不存在，则插入
            cursor.execute(
                "INSERT IGNORE INTO conversation (conversation_id) VALUES (%s)",
                (conversation_id,),
            )

    def save_conversation(
        self,
        conversation_id: str,
        question: str,
        answer: str,
        user_id: str = None,
        title: str = None,
    ) -> bool:
        """
        保存对话记录到数据库

        Args:
            conversation_id: 对话ID
            question: 用户问题
            answer: 系统回答
            user_id: 用户ID
            title: 对话标题

        Returns:
            是否保存成功
        """
        try:
            # 保存到MySQL
            conn = self.get_mysql_connection()
            with conn.cursor() as cursor:
                # 确保conversation表中有此会话ID
                cursor.execute(
                    "SELECT 1 FROM conversation WHERE conversation_id = %s",
                    (conversation_id,),
                )
                if not cursor.fetchone():
                    # 如果不存在，则插入
                    insert_conv_sql = """
                    INSERT INTO conversation (conversation_id, user_id, title)
                    VALUES (%s, %s, %s)
                    """
                    # 如果没有提供标题，使用问题的前30个字符作为标题
                    if not title and question:
                        title = question[:30] + ("..." if len(question) > 30 else "")

                    cursor.execute(insert_conv_sql, (conversation_id, user_id, title))
                elif user_id or title:
                    # 如果提供了用户ID或标题，则更新
                    update_fields = []
                    params = []

                    if user_id:
                        update_fields.append("user_id = %s")
                        params.append(user_id)

                    if title:
                        update_fields.append("title = %s")
                        params.append(title)

                    if update_fields:
                        update_sql = f"""
                        UPDATE conversation
                        SET {', '.join(update_fields)}
                        WHERE conversation_id = %s
                        """
                        params.append(conversation_id)
                        cursor.execute(update_sql, params)

                # 保存对话历史
                sql = """
                INSERT INTO conversation_history 
                (conversation_id, question, answer) 
                VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (conversation_id, question, answer))
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
                            "title": title,
                            "user_id": user_id,
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

    def get_all_conversations(
        self, user_id: str = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取所有对话列表

        Args:
            user_id: 用户ID，如果提供则只返回该用户的对话
            limit: 返回的最大记录数

        Returns:
            对话列表
        """
        try:
            conn = self.get_mysql_connection()
            with conn.cursor() as cursor:
                if user_id:
                    sql = """
                    SELECT c.conversation_id, c.title, c.user_id, c.created_at, c.updated_at,
                           COUNT(ch.id) as message_count
                    FROM conversation c
                    LEFT JOIN conversation_history ch ON c.conversation_id = ch.conversation_id
                    WHERE c.user_id = %s
                    GROUP BY c.conversation_id
                    ORDER BY c.updated_at DESC
                    LIMIT %s
                    """
                    cursor.execute(sql, (user_id, limit))
                else:
                    sql = """
                    SELECT c.conversation_id, c.title, c.user_id, c.created_at, c.updated_at,
                           COUNT(ch.id) as message_count
                    FROM conversation c
                    LEFT JOIN conversation_history ch ON c.conversation_id = ch.conversation_id
                    GROUP BY c.conversation_id
                    ORDER BY c.updated_at DESC
                    LIMIT %s
                    """
                    cursor.execute(sql, (limit,))

                results = cursor.fetchall()

                conversations = []
                for row in results:
                    conversations.append(
                        {
                            "conversation_id": row["conversation_id"],
                            "title": row["title"],
                            "user_id": row["user_id"],
                            "created_at": row["created_at"].isoformat()
                            if hasattr(row["created_at"], "isoformat")
                            else str(row["created_at"]),
                            "updated_at": row["updated_at"].isoformat()
                            if hasattr(row["updated_at"], "isoformat")
                            else str(row["updated_at"]),
                            "message_count": row["message_count"],
                        }
                    )

                return conversations

        except Exception as e:
            logger.error(f"获取对话列表失败: {e}")
            return []

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        删除对话及其历史记录

        Args:
            conversation_id: 对话ID

        Returns:
            是否删除成功
        """
        try:
            conn = self.get_mysql_connection()
            with conn.cursor() as cursor:
                # 先删除历史记录
                cursor.execute(
                    "DELETE FROM conversation_history WHERE conversation_id = %s",
                    (conversation_id,),
                )

                # 再删除对话
                cursor.execute(
                    "DELETE FROM conversation WHERE conversation_id = %s",
                    (conversation_id,),
                )

            conn.commit()

            # 删除Redis缓存
            redis_key = f"conversation:{conversation_id}"
            redis_conn = self.get_redis_connection()
            redis_conn.delete(redis_key)

            return True

        except Exception as e:
            logger.error(f"删除对话失败: {e}")
            return False


# 单例模式
_db_manager = None


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器单例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
