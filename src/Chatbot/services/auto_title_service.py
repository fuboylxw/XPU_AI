"""
自动标题生成服务
集成数据库监听、定时任务和标题生成功能，提供完整的自动标题生成解决方案
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from src.Chatbot.utils.logger import setup_logger
from src.Chatbot.agents.conversation_title_agent import ConversationTitleAgent
from src.Chatbot.utils.database_monitor import DatabaseMonitor, ConversationUpdate


@dataclass
class ConversationTracker:
    """对话跟踪器"""
    conversation_id: str
    last_activity_time: datetime
    last_title_update_time: Optional[datetime] = None
    pending_title_update: bool = False
    activity_count: int = 0


class AutoTitleService:
    """自动标题生成服务"""
    
    def __init__(self, 
                 idle_threshold: int = 600,  # 10分钟无活动后生成标题
                 check_interval: int = 300,  # 5分钟检查一次
                 db_monitor_interval: int = 60):  # 1分钟检查数据库更新
        """
        初始化自动标题生成服务
        
        Args:
            idle_threshold: 空闲阈值（秒），超过此时间无新消息则生成标题
            check_interval: 检查间隔（秒）
            db_monitor_interval: 数据库监听间隔（秒）
        """
        self.logger = setup_logger("auto_title_service")
        self.idle_threshold = idle_threshold
        self.check_interval = check_interval
        self.is_running = False
        self.service_thread = None
        
        # 初始化组件
        self.title_agent = ConversationTitleAgent()
        self.db_monitor = DatabaseMonitor(check_interval=db_monitor_interval)
        
        # 对话跟踪器
        self.conversation_trackers: Dict[str, ConversationTracker] = {}
        self.tracker_lock = threading.Lock()
        
        # 注册数据库更新回调
        self.db_monitor.add_update_callback(self._on_conversation_update)
        
        self.logger.info("自动标题生成服务初始化完成")
    
    def start_service(self):
        """启动服务"""
        if self.is_running:
            self.logger.warning("自动标题生成服务已经在运行中")
            return
        
        self.is_running = True
        
        # 启动数据库监听
        self.db_monitor.start_monitoring()
        
        # 启动服务主循环
        self.service_thread = threading.Thread(target=self._service_loop, daemon=True)
        self.service_thread.start()
        
        self.logger.info(f"自动标题生成服务已启动，空闲阈值：{self.idle_threshold}秒，检查间隔：{self.check_interval}秒")
    
    def stop_service(self):
        """停止服务"""
        self.is_running = False
        
        # 停止数据库监听
        self.db_monitor.stop_monitoring()
        
        # 等待服务线程结束
        if self.service_thread:
            self.service_thread.join(timeout=5)
        
        self.logger.info("自动标题生成服务已停止")
    
    def _service_loop(self):
        """服务主循环"""
        # 初始化现有对话的跟踪器
        self._initialize_conversation_trackers()
        
        while self.is_running:
            try:
                # 检查需要生成标题的对话
                self._check_and_generate_titles()
                
                # 等待下一次检查
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"服务循环出错: {e}")
                time.sleep(self.check_interval)
    
    def _initialize_conversation_trackers(self):
        """初始化对话跟踪器"""
        try:
            # 获取所有对话状态
            conversation_states = self.db_monitor.get_all_conversation_states()
            
            with self.tracker_lock:
                for conversation_id, state in conversation_states.items():
                    if conversation_id not in self.conversation_trackers:
                        self.conversation_trackers[conversation_id] = ConversationTracker(
                            conversation_id=conversation_id,
                            last_activity_time=state.last_update_time,
                            activity_count=state.record_count
                        )
            
            self.logger.info(f"初始化了 {len(self.conversation_trackers)} 个对话跟踪器")
            
        except Exception as e:
            self.logger.error(f"初始化对话跟踪器失败: {e}")
    
    def _on_conversation_update(self, updates: List[ConversationUpdate]):
        """处理对话更新事件"""
        with self.tracker_lock:
            for update in updates:
                conversation_id = update.conversation_id
                
                if conversation_id in self.conversation_trackers:
                    tracker = self.conversation_trackers[conversation_id]
                    tracker.last_activity_time = update.last_update_time
                    tracker.activity_count = update.record_count
                    tracker.pending_title_update = True
                else:
                    # 新对话
                    self.conversation_trackers[conversation_id] = ConversationTracker(
                        conversation_id=conversation_id,
                        last_activity_time=update.last_update_time,
                        activity_count=update.record_count,
                        pending_title_update=True
                    )
                
                self.logger.debug(f"更新对话跟踪器: {conversation_id}")
    
    def _check_and_generate_titles(self):
        """检查并生成标题"""
        current_time = datetime.now()
        idle_threshold_time = current_time - timedelta(seconds=self.idle_threshold)
        
        conversations_to_process = []
        
        with self.tracker_lock:
            for conversation_id, tracker in self.conversation_trackers.items():
                # 检查是否满足生成标题的条件
                if (tracker.pending_title_update and 
                    tracker.last_activity_time <= idle_threshold_time and
                    tracker.activity_count > 0):
                    
                    conversations_to_process.append(conversation_id)
                    tracker.pending_title_update = False
        
        # 处理需要生成标题的对话
        for conversation_id in conversations_to_process:
            try:
                self._generate_title_for_conversation(conversation_id)
            except Exception as e:
                self.logger.error(f"为对话 {conversation_id} 生成标题失败: {e}")
    
    def _generate_title_for_conversation(self, conversation_id: str):
        """为指定对话生成标题"""
        self.logger.info(f"开始为对话 {conversation_id} 生成标题")
        
        # 调用标题生成智能体
        title = self.title_agent.generate_title_for_conversation(conversation_id)
        
        if title:
            # 更新跟踪器
            with self.tracker_lock:
                if conversation_id in self.conversation_trackers:
                    self.conversation_trackers[conversation_id].last_title_update_time = datetime.now()
            
            self.logger.info(f"成功为对话 {conversation_id} 生成标题: {title}")
        else:
            self.logger.warning(f"为对话 {conversation_id} 生成标题失败")
    
    def force_generate_title(self, conversation_id: str) -> Optional[str]:
        """强制为指定对话生成标题"""
        try:
            title = self.title_agent.generate_title_for_conversation(conversation_id)
            
            if title:
                # 更新跟踪器
                with self.tracker_lock:
                    if conversation_id in self.conversation_trackers:
                        self.conversation_trackers[conversation_id].last_title_update_time = datetime.now()
                        self.conversation_trackers[conversation_id].pending_title_update = False
            
            return title
            
        except Exception as e:
            self.logger.error(f"强制生成标题失败: {e}")
            return None
    
    def get_conversation_status(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取对话状态"""
        with self.tracker_lock:
            tracker = self.conversation_trackers.get(conversation_id)
            if tracker:
                return {
                    "conversation_id": tracker.conversation_id,
                    "last_activity_time": tracker.last_activity_time.isoformat(),
                    "last_title_update_time": tracker.last_title_update_time.isoformat() if tracker.last_title_update_time else None,
                    "pending_title_update": tracker.pending_title_update,
                    "activity_count": tracker.activity_count,
                    "idle_time_seconds": (datetime.now() - tracker.last_activity_time).total_seconds()
                }
        return None
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        with self.tracker_lock:
            tracked_conversations = len(self.conversation_trackers)
            pending_updates = sum(1 for t in self.conversation_trackers.values() if t.pending_title_update)
        
        return {
            "is_running": self.is_running,
            "idle_threshold": self.idle_threshold,
            "check_interval": self.check_interval,
            "tracked_conversations": tracked_conversations,
            "pending_title_updates": pending_updates,
            "service_thread_alive": self.service_thread.is_alive() if self.service_thread else False,
            "db_monitor_status": self.db_monitor.get_status(),
            "title_agent_status": self.title_agent.get_status()
        }
    
    def get_all_conversation_statuses(self) -> List[Dict[str, Any]]:
        """获取所有对话状态"""
        statuses = []
        with self.tracker_lock:
            for conversation_id in self.conversation_trackers:
                status = self.get_conversation_status(conversation_id)
                if status:
                    statuses.append(status)
        return statuses


# 全局服务实例
auto_title_service = AutoTitleService()


def start_auto_title_service():
    """启动自动标题生成服务"""
    auto_title_service.start_service()


def stop_auto_title_service():
    """停止自动标题生成服务"""
    auto_title_service.stop_service()


def force_generate_title(conversation_id: str) -> Optional[str]:
    """强制生成标题"""
    return auto_title_service.force_generate_title(conversation_id)


def get_service_status() -> Dict[str, Any]:
    """获取服务状态"""
    return auto_title_service.get_service_status()


if __name__ == "__main__":
    # 测试代码
    service = AutoTitleService(idle_threshold=300, check_interval=60)
    
    try:
        print("启动自动标题生成服务...")
        service.start_service()
        
        # 保持运行并定期显示状态
        while True:
            time.sleep(30)
            status = service.get_service_status()
            print(f"服务状态: {status}")
            
            # 显示对话状态
            conversation_statuses = service.get_all_conversation_statuses()
            if conversation_statuses:
                print(f"跟踪的对话数量: {len(conversation_statuses)}")
                for conv_status in conversation_statuses[:5]:  # 只显示前5个
                    print(f"  - {conv_status['conversation_id']}: "
                          f"空闲时间 {conv_status['idle_time_seconds']:.0f}秒, "
                          f"待更新: {conv_status['pending_title_update']}")
            
    except KeyboardInterrupt:
        print("停止服务...")
        service.stop_service()