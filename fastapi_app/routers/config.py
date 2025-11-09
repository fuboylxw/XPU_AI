"""
应用配置相关的API路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from fastapi_app.database import get_db
from fastapi_app.models import AppConfig
from fastapi_app.schemas import AppConfigFullResponse, SystemStatusResponse

router = APIRouter()

# 延迟导入ChatbotAgent，避免循环导入问题
chatbot_agent = None

def get_chatbot_agent():
    """获取ChatbotAgent实例，延迟初始化"""
    global chatbot_agent
    if chatbot_agent is None:
        try:
            print("🔍 开始初始化ChatbotAgent...")
            from src.Chatbot.agents.chat_agent import ChatbotAgent
            print("✅ ChatbotAgent导入成功")
            chatbot_agent = ChatbotAgent()
            print("✅ ChatbotAgent初始化成功")
        except Exception as e:
            print(f"❌ 初始化ChatbotAgent失败: {str(e)}")
            logging.error(f"初始化ChatbotAgent失败: {str(e)}")
            import traceback
            traceback.print_exc()
            chatbot_agent = None
    return chatbot_agent


@router.get("/config/", response_model=Dict[str, Any])
async def get_app_config(db: Session = Depends(get_db)):
    """获取应用配置信息"""
    try:
        logger = logging.getLogger(__name__)
        
        # 从数据库获取基本配置
        config = {}
        
        # 获取所有配置项
        try:
            app_configs = db.query(AppConfig).all()
            for app_config in app_configs:
                config[app_config.key] = app_config.get_value()
        except Exception as db_error:
            logger.warning(f"从数据库获取配置失败: {str(db_error)}")
        
        # 返回基础配置，不包含UI默认配置
        ui_config = {
            'app_name': config.get('app_name'),
            'page_title': config.get('page_title'),
            'user_name': config.get('user_name')
        }
        
        # 从ChatbotAgent获取系统状态和动态信息
        try:
            chat_agent = get_chatbot_agent()
            if chat_agent:
                system_status = chat_agent.get_system_status()
                
                # 添加系统状态信息到配置中
                ui_config['system_status'] = {
                    'llm_status': system_status.get('llm_status', 'unknown'),
                    'memory_status': system_status.get('memory_status', 'unknown'),
                    'tools_status': system_status.get('tools_status', {}),
                    'agents_status': system_status.get('agents_status', {}),
                    'last_update': system_status.get('last_update', ''),
                    'uptime': system_status.get('uptime', 0)
                }
                
                # 从chat_agent获取模型配置
                if hasattr(chat_agent, 'llm_client') and chat_agent.llm_client:
                    ui_config['current_model'] = getattr(chat_agent.llm_client.llm, 'model_name', config.get('ai_model', 'unknown'))
                    ui_config['current_temperature'] = getattr(chat_agent.llm_client.llm, 'temperature', config.get('temperature', 0.7))
                    ui_config['current_max_tokens'] = getattr(chat_agent.llm_client.llm, 'max_tokens', config.get('max_tokens', 2000))
            else:
                # ChatbotAgent初始化失败
                ui_config['system_status'] = {
                    'llm_status': 'error',
                    'memory_status': 'error',
                    'tools_status': {},
                    'agents_status': {},
                    'last_update': '',
                    'uptime': 0
                }
            
        except Exception as agent_error:
            logger.warning(f"获取ChatbotAgent状态失败: {str(agent_error)}")
            # 如果无法获取agent状态，使用默认值
            ui_config['system_status'] = {
                'llm_status': 'unknown',
                'memory_status': 'unknown',
                'tools_status': {},
                'agents_status': {},
                'last_update': '',
                'uptime': 0
            }
        
        return ui_config
        
    except Exception as e:
        logger.error(f"获取应用配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取应用配置失败: {str(e)}")