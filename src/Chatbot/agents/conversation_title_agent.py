"""
对话标题自动生成智能体
自动监听数据库中历史对话的更新，并在一定时间内没有新会话时，调用大模型总结所有对话并更新该对话的标题
"""

import os
import sys
import time
import threading
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 添加项目根路径与src路径
current_file_dir = os.path.dirname(os.path.abspath(__file__))
chatbot_dir = os.path.dirname(current_file_dir)              # .../src/Chatbot
src_dir = os.path.dirname(chatbot_dir)                       # .../src
project_root = os.path.dirname(src_dir)                      # project root
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from config.settings import settings
from src.Chatbot.utils.logger import setup_logger

# 使用FastAPI的SQLAlchemy模型而非Django
from sqlalchemy.orm import Session
from fastapi_app.database import SessionLocal
from fastapi_app.models import Conversation, ConversationHistory


class ConversationTitleAgent:
    """对话标题自动生成智能体"""
    
    def __init__(self, check_interval: int = 120, idle_threshold: int = 300):
        """
        初始化对话标题生成智能体
        
        Args:
            check_interval: 检查间隔时间（秒），默认2分钟
            idle_threshold: 空闲阈值时间（秒），默认5分钟  
        """
        self.logger = setup_logger("conversation_title_agent")
        self.check_interval = check_interval
        self.idle_threshold = idle_threshold
        self.is_running = False
        self.monitor_thread = None
        
        # 初始化LLM客户端（使用与chat_agent.py相同的配置）
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_MODEL_BASE_URL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
        )
        
        # 初始化提示模板
        self._initialize_prompts()
        
        self.logger.info("对话标题生成智能体初始化完成")
    
    def _initialize_prompts(self):
        """初始化提示模板"""
        self.title_generation_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""
            你是一个专业的对话标题生成助手。你的任务是根据用户与AI助手的完整对话内容，生成一个简洁、准确、有意义的对话标题。
            要求：
            1. 标题应该简洁明了，不超过10个字符
            2. 标题应该准确反映对话的主要内容和主题，让人一眼明白讨论的是什么。
            3. 标题应该具有可读性和识别性
            4. 如果对话涉及多个主题，选择最主要或最重要的主题
            5. 避免使用过于技术性或复杂的词汇
            6. 标题应该是中文
            7.用自然语言表达，而非说明句。

            示例：
            - 对话内容关于Python编程问题 → "Python编程咨询"
            - 对话内容关于数据库设计 → "数据库设计讨论"
            - 对话内容关于机器学习算法 → "机器学习算法"
            - 对话内容关于项目管理 → "项目管理建议"

            请直接返回标题，不要包含任何其他内容。
            """),
            HumanMessage(content="请根据以下对话内容生成一个合适的标题：\n\n{conversation_content}")
        ])
    
    def start_monitoring(self):
        """开始监听数据库更新"""
        if self.is_running:
            self.logger.warning("监听已经在运行中")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info(f"开始监听数据库更新，检查间隔：{self.check_interval}秒，空闲阈值：{self.idle_threshold}秒")
    
    def stop_monitoring(self):
        """停止监听数据库更新"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("停止监听数据库更新")
    
    def _monitor_loop(self):
        """监听循环"""
        while self.is_running:
            try:
                # 每次循环创建独立的数据库会话
                db = SessionLocal()
                try:
                    # 检查需要更新标题的对话
                    conversations_to_update = self._find_conversations_needing_title_update(db)
                    
                    for conversation in conversations_to_update:
                        try:
                            self._update_conversation_title(db, conversation)
                        except Exception as e:
                            self.logger.error(f"更新对话 {conversation.conversation_id} 标题失败: {e}")
                finally:
                    db.close()
                
                # 等待下一次检查
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"监听循环出错: {e}")
                time.sleep(self.check_interval)
    
    def _find_conversations_needing_title_update(self, db: Session) -> List[Conversation]:
        """查找需要更新标题的对话"""
        try:
            current_time = datetime.now()
            idle_time_threshold = current_time - timedelta(seconds=self.idle_threshold)
            
            # 查找满足条件的对话：
            # 1. 有历史记录
            # 2. 最后一条历史记录的时间早于空闲阈值
            # 3. 标题为空或者对话最后修改时间早于最后一条历史记录
            conversations = []
            
            all_conversations = db.query(Conversation).all()
            for conversation in all_conversations:
                # 获取该对话的最新历史记录
                latest_history = db.query(ConversationHistory).filter(
                    ConversationHistory.conversation_id == conversation.conversation_id
                ).order_by(ConversationHistory.created_at.desc()).first()
                
                if not latest_history:
                    continue
                
                # 检查是否超过空闲阈值
                if latest_history.created_at > idle_time_threshold:
                    continue
                
                # 检查是否需要更新标题
                needs_update = False
                
                # 如果没有标题，需要更新
                if not conversation.title or conversation.title.strip() == "":
                    needs_update = True
                
                # 如果对话的修改时间早于最新历史记录，需要更新
                elif ((conversation.modified or conversation.created) < latest_history.created_at):
                    needs_update = True
                
                if needs_update:
                    conversations.append(conversation)
                    self.logger.info(f"发现需要更新标题的对话: {conversation.conversation_id}")
            
            return conversations
            
        except Exception as e:
            self.logger.error(f"查找需要更新标题的对话时出错: {e}")
            return []
    
    def _update_conversation_title(self, db: Session, conversation: Conversation):
        """更新对话标题"""
        try:
            # 获取对话的所有历史记录
            history_records = db.query(ConversationHistory).filter(
                ConversationHistory.conversation_id == conversation.conversation_id
            ).order_by(ConversationHistory.created_at.asc()).all()
            
            if not history_records:
                self.logger.warning(f"对话 {conversation.conversation_id} 没有历史记录")
                return
            
            # 构建对话内容
            conversation_content = self._build_conversation_content(history_records)
            
            # 生成标题
            new_title = self._generate_title(conversation_content)
            
            if new_title:
                # 更新数据库
                conversation.title = new_title
                # modified 字段在onupdate时会自动更新
                db.add(conversation)
                db.commit()
                db.refresh(conversation)
                
                self.logger.info(f"成功更新对话 {conversation.conversation_id} 的标题: {new_title}")
            else:
                self.logger.warning(f"为对话 {conversation.conversation_id} 生成标题失败")
                
        except Exception as e:
            self.logger.error(f"更新对话 {conversation.conversation_id} 标题时出错: {e}")
    
    def _build_conversation_content(self, history_records) -> str:
        """构建对话内容字符串"""
        content_parts = []
        
        for record in history_records:
            content_parts.append(f"用户: {record.question}")
            content_parts.append(f"助手: {record.answer}")
        
        return "\n\n".join(content_parts)
    
    def _generate_title(self, conversation_content: str) -> Optional[str]:
        """使用LLM生成对话标题"""
        try:
            if not settings.OPENAI_API_KEY:
                return self._generate_title_fallback(conversation_content)
            # 限制对话内容长度，避免超过模型限制
            max_content_length = 3000
            if len(conversation_content) > max_content_length:
                conversation_content = conversation_content[:max_content_length] + "..."
            
            # 使用提示模板生成标题
            chain = self.title_generation_prompt | self.llm | StrOutputParser()
            
            title = chain.invoke({
                "conversation_content": conversation_content
            })
            
            # 清理标题
            title = title.strip().strip('"').strip("'")
            
            # 占位符与无效标题修正
            invalid_tokens = {"{generated_title}", "generated_title", "{title}", "title", "<generated_title>", "新对话", "对话标题"}
            if (not title) or (title.lower() in invalid_tokens) or ("generated_title" in title.lower()) or (title.startswith("{") and title.endswith("}")):
                return self._generate_title_fallback(conversation_content)
            
            # 限制标题长度
            if len(title) > 50:
                title = title[:50]
            
            return title
            
        except Exception as e:
            self.logger.error(f"生成标题时出错: {e}")
            return self._generate_title_fallback(conversation_content)

    def _generate_title_fallback(self, conversation_content: str) -> Optional[str]:
        try:
            parts = [p.strip() for p in conversation_content.split("\n\n") if p.strip()]
            for p in reversed(parts):
                if p.startswith("用户:"):
                    t = p.replace("用户:", "").strip().strip('"').strip("'")
                    if len(t) > 50:
                        t = t[:50]
                    return t or "会话摘要"
            if parts:
                t = parts[0].strip().strip('"').strip("'")
                if len(t) > 50:
                    t = t[:50]
                return t or "会话摘要"
            return "会话摘要"
        except Exception:
            return "会话摘要"
    
    def generate_title_for_conversation(self, conversation_id: str) -> Optional[str]:
        """为指定对话生成标题（手动调用）"""
        try:
            db = SessionLocal()
            try:
                conversation = db.query(Conversation).filter(
                    Conversation.conversation_id == conversation_id
                ).first()
                if not conversation:
                    self.logger.error(f"对话 {conversation_id} 不存在")
                    return None
                self._update_conversation_title(db, conversation)
                return conversation.title
            finally:
                db.close()
        except Exception as e:
            self.logger.error(f"为对话 {conversation_id} 生成标题时出错: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """获取智能体状态"""
        return {
            "is_running": self.is_running,
            "check_interval": self.check_interval,
            "idle_threshold": self.idle_threshold,
            "monitor_thread_alive": self.monitor_thread.is_alive() if self.monitor_thread else False
        }


# 全局实例，使用settings中的配置项
title_agent = ConversationTitleAgent(
    check_interval=settings.TITLE_CHECK_INTERVAL,
    idle_threshold=settings.TITLE_IDLE_THRESHOLD
)


def start_title_monitoring():
    """启动标题监听服务"""
    title_agent.start_monitoring()


def stop_title_monitoring():
    """停止标题监听服务"""
    title_agent.stop_monitoring()
