"""
SQLAlchemy数据库模型
"""
from sqlalchemy import Column, String, Text, DateTime, SmallInteger, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from fastapi_app.database import Base
import json


class AppConfig(Base):
    """应用配置模型"""
    __tablename__ = "app_config"
    
    key = Column(String(100), primary_key=True, unique=True)
    value = Column(Text)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def get_value(self):
        """获取配置值，自动解析JSON"""
        try:
            return json.loads(self.value)
        except (json.JSONDecodeError, TypeError):
            return self.value

    def set_value(self, value):
        """设置配置值，自动转换为JSON"""
        if isinstance(value, (dict, list)):
            self.value = json.dumps(value, ensure_ascii=False)
        else:
            self.value = str(value)


class Conversation(Base):
    __tablename__ = "chat_conversation"
    
    id = Column(String(32), primary_key=True)
    conversation_id = Column(String(50), unique=True, index=True)
    user_id = Column(String(32), index=True)
    title = Column(String(255), nullable=True)
    created = Column(DateTime, default=func.now())
    modified = Column(DateTime, default=func.now(), onupdate=func.now())
    status = Column(SmallInteger, default=1)


class ConversationHistory(Base):
    __tablename__ = "chat_conversation_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(50), index=True)
    question = Column(Text)
    answer = Column(Text)
    created_at = Column(DateTime, default=func.now())


class PhoneSession(Base):
    """电话会话模型"""
    __tablename__ = "phone_session"
    
    id = Column(String(32), primary_key=True)  # 电话会话ID
    user_id = Column(String(32), index=True)  # 用户ID
    session_start = Column(DateTime, default=func.now())  # 会话开始时间
    session_end = Column(DateTime, nullable=True)  # 会话结束时间
    status = Column(SmallInteger, default=1)  # 1:进行中, 0:已结束
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class PhoneConversationHistory(Base):
    """电话对话历史记录模型"""
    __tablename__ = "phone_conversation_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(32), index=True)  # 关联电话会话ID
    user_id = Column(String(32), index=True)  # 用户ID
    question = Column(Text)  # 用户问题
    answer = Column(Text)  # AI回答
    question_audio_path = Column(String(255), nullable=True)  # 问题音频文件路径
    answer_audio_path = Column(String(255), nullable=True)  # 回答音频文件路径
    created_at = Column(DateTime, default=func.now())


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(String(32), primary_key=True)  # 用户ID
    username = Column(String(50), unique=True, index=True, nullable=True)  # 用户名
    email = Column(String(100), unique=True, index=True, nullable=False)  # 邮箱（必填）
    password_hash = Column(String(255))  # 密码哈希
    nickname = Column(String(50), nullable=True)  # 昵称
    avatar_url = Column(String(255), nullable=True)  # 头像URL
    is_active = Column(SmallInteger, default=1)  # 是否激活 1:激活 0:禁用
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)  # 最后登录时间


class WorkSession(Base):
    __tablename__ = "work_sessions"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_work_sessions_session_id"),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), index=True, nullable=False)
    user_id = Column(String(32), index=True)
    title = Column(String(255))
    status = Column(String(32), default="loading")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class WorkTask(Base):
    __tablename__ = "work_tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("work_sessions.session_id"), index=True)
    task_name = Column(String(255), nullable=True)
    status = Column(String(32), nullable=True)
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class WorkSubTask(Base):
    __tablename__ = "work_sub_tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), index=True)
    task_id = Column(Integer, ForeignKey("work_tasks.id"), index=True)
    sub_task_name = Column(String(255), nullable=True)
    order = Column(Integer)
    status = Column(String(32), nullable=True)
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
