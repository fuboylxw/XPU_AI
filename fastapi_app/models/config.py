"""应用配置模型"""
import json
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from fastapi_app.models.base import Base


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
