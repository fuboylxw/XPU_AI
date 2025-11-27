"""
数据库监听服务
监听数据库中历史对话表的更新，并触发相应的处理逻辑
"""

import os
import sys
import time
import threading
import pymysql
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.Chatbot.utils.logger import setup_logger


@dataclass
class ConversationUpdate:
    """对话更新事件"""
    conversation_id: str
    last_update_time: datetime
    record_count: int


class DatabaseMonitor:
    """数据库监听器"""
    
    def __init__(self, 
                 mysql_host: str = None,
                 mysql_port: int = None,
                 mysql_user: str = None,
                 mysql_password: str = None,
                 mysql_db: str = None,
                 check_interval: int = 60):
        """
        初始化数据库监听器
        
        Args:
            mysql_host: MySQL主机地址
            mysql_port: MySQL端口
            mysql_user: MySQL用户名
            mysql_password: MySQL密码
            mysql_db: MySQL数据库名
            check_interval: 检查间隔（秒）
        """
        self.logger = setup_logger("database_monitor")
        self.check_interval = check_interval
        self.is_running = False
        self.monitor_thread = None
        
        # 数据库配置，从环境变量读取
        self.mysql_config = {
            "host": mysql_host or os.getenv("MYSQL_HOST", "localhost"),
            "port": mysql_port or int(os.getenv("MYSQL_PORT", "3306")),
            "user": mysql_user or os.getenv("MYSQL_USER", "root"),
            "password": mysql_password or os.getenv("MYSQL_PASSWORD", ""),
            "db": mysql_db or os.getenv("MYSQL_DB", "chatbot"),
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor,
        }
        
        # 存储上次检查的状态
        self.last_check_time = datetime.now()
        self.conversation_states: Dict[str, ConversationUpdate] = {}
        
        # 回调函数列表
        self.update_callbacks: List[Callable[[List[ConversationUpdate]], None]] = []
        
        self.logger.info("数据库监听器初始化完成")
    
    def add_update_callback(self, callback: Callable[[List[ConversationUpdate]], None]):
        """添加更新回调函数"""
        self.update_callbacks.append(callback)
        self.logger.info(f"添加更新回调函数: {callback.__name__}")
    
    def start_monitoring(self):
        """开始监听数据库"""
        if self.is_running:
            self.logger.warning("数据库监听已经在运行中")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info(f"开始监听数据库，检查间隔：{self.check_interval}秒")
    
    def stop_monitoring(self):
        """停止监听数据库"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("停止监听数据库")
    
    def _monitor_loop(self):
        """监听循环"""
        # 初始化状态
        self._initialize_conversation_states()
        
        while self.is_running:
            try:
                # 检查数据库更新
                updates = self._check_for_updates()
                
                if updates:
                    self.logger.info(f"检测到 {len(updates)} 个对话更新")
                    
                    # 调用所有回调函数
                    for callback in self.update_callbacks:
                        try:
                            callback(updates)
                        except Exception as e:
                            self.logger.error(f"回调函数 {callback.__name__} 执行失败: {e}")
                
                # 更新检查时间
                self.last_check_time = datetime.now()
                
                # 等待下一次检查
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"监听循环出错: {e}")
                time.sleep(self.check_interval)
    
    def _initialize_conversation_states(self):
        """初始化对话状态"""
        try:
            with pymysql.connect(**self.mysql_config) as conn:
                with conn.cursor() as cursor:
                    # 获取所有对话的最新状态
                    sql = """
                    SELECT 
                        conversation_id,
                        MAX(created_at) as last_update_time,
                        COUNT(*) as record_count
                    FROM chat_conversation_history 
                    GROUP BY conversation_id
                    """
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    
                    for row in results:
                        conversation_id = row['conversation_id']
                        self.conversation_states[conversation_id] = ConversationUpdate(
                            conversation_id=conversation_id,
                            last_update_time=row['last_update_time'],
                            record_count=row['record_count']
                        )
                    
                    self.logger.info(f"初始化了 {len(self.conversation_states)} 个对话状态")
                    
        except Exception as e:
            self.logger.error(f"初始化对话状态失败: {e}")
    
    def _check_for_updates(self) -> List[ConversationUpdate]:
        """检查数据库更新"""
        updates = []
        
        try:
            with pymysql.connect(**self.mysql_config) as conn:
                with conn.cursor() as cursor:
                    # 获取自上次检查以来的更新
                    sql = """
                    SELECT 
                        conversation_id,
                        MAX(created_at) as last_update_time,
                        COUNT(*) as record_count
                    FROM chat_conversation_history 
                    WHERE created_at >= %s
                    GROUP BY conversation_id
                    """
                    cursor.execute(sql, (self.last_check_time,))
                    recent_updates = cursor.fetchall()
                    
                    # 检查每个对话的变化
                    for row in recent_updates:
                        conversation_id = row['conversation_id']
                        current_update = ConversationUpdate(
                            conversation_id=conversation_id,
                            last_update_time=row['last_update_time'],
                            record_count=row['record_count']
                        )
                        
                        # 检查是否有新的更新
                        if conversation_id in self.conversation_states:
                            previous_state = self.conversation_states[conversation_id]
                            if (current_update.last_update_time > previous_state.last_update_time or
                                current_update.record_count != previous_state.record_count):
                                updates.append(current_update)
                                self.conversation_states[conversation_id] = current_update
                        else:
                            # 新对话
                            updates.append(current_update)
                            self.conversation_states[conversation_id] = current_update
                    
                    # 获取所有对话的完整状态（用于更新记录数）
                    if updates:
                        sql_all = """
                        SELECT 
                            conversation_id,
                            MAX(created_at) as last_update_time,
                            COUNT(*) as record_count
                        FROM chat_conversation_history 
                        GROUP BY conversation_id
                        """
                        cursor.execute(sql_all)
                        all_states = cursor.fetchall()
                        
                        for row in all_states:
                            conversation_id = row['conversation_id']
                            if conversation_id in [u.conversation_id for u in updates]:
                                # 更新完整的记录数
                                for update in updates:
                                    if update.conversation_id == conversation_id:
                                        update.record_count = row['record_count']
                                        self.conversation_states[conversation_id] = update
                                        break
                    
        except Exception as e:
            self.logger.error(f"检查数据库更新失败: {e}")
        
        return updates
    
    def get_conversation_state(self, conversation_id: str) -> Optional[ConversationUpdate]:
        """获取指定对话的状态"""
        return self.conversation_states.get(conversation_id)
    
    def get_all_conversation_states(self) -> Dict[str, ConversationUpdate]:
        """获取所有对话状态"""
        return self.conversation_states.copy()
    
    def force_check(self) -> List[ConversationUpdate]:
        """强制检查更新"""
        return self._check_for_updates()
    
    def get_status(self) -> Dict[str, Any]:
        """获取监听器状态"""
        return {
            "is_running": self.is_running,
            "check_interval": self.check_interval,
            "last_check_time": self.last_check_time.isoformat(),
            "monitored_conversations": len(self.conversation_states),
            "monitor_thread_alive": self.monitor_thread.is_alive() if self.monitor_thread else False
        }


# 全局实例
db_monitor = DatabaseMonitor()


def start_database_monitoring():
    """启动数据库监听服务"""
    db_monitor.start_monitoring()


def stop_database_monitoring():
    """停止数据库监听服务"""
    db_monitor.stop_monitoring()


if __name__ == "__main__":
    # 测试代码
    def on_conversation_update(updates: List[ConversationUpdate]):
        print(f"检测到对话更新: {len(updates)} 个")
        for update in updates:
            print(f"  - 对话ID: {update.conversation_id}")
            print(f"    最后更新: {update.last_update_time}")
            print(f"    记录数: {update.record_count}")
    
    monitor = DatabaseMonitor(check_interval=30)
    monitor.add_update_callback(on_conversation_update)
    
    try:
        print("启动数据库监听服务...")
        monitor.start_monitoring()
        
        # 保持运行
        while True:
            time.sleep(10)
            status = monitor.get_status()
            print(f"监听器状态: {status}")
            
    except KeyboardInterrupt:
        print("停止服务...")
        monitor.stop_monitoring()