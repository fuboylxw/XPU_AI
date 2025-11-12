import streamlit as st
import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from src.Chatbot.agents.chat_agent import ChatBIAgent
from src.Chatbot.utils.logger import setup_logger
from config.settings import settings

# 设置日志
logger = setup_logger("main")


def initialize_session_state():
    """初始化会话状态"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        st.session_state.agent = ChatBIAgent()
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = "default"


def display_chat_history():
    """显示聊天历史"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def main():
    """主应用函数"""
    st.set_page_config(
        page_title="ChatBI - 智能对话助手",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 初始化会话状态
    initialize_session_state()

    # 页面标题
    st.title("🤖 ChatBI - 智能对话助手")
    st.markdown("---")

    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 配置")

        # 模型选择
        model_name = st.selectbox("选择模型", ["gpt-3.5-turbo", "gpt-4"], index=0)

        # 温度设置
        temperature = st.slider(
            "创造力 (Temperature)", min_value=0.0, max_value=1.0, value=0.7, step=0.1
        )

        # 清除对话按钮
        if st.button("🗑️ 清除对话"):
            st.session_state.messages = []
            st.rerun()

        st.markdown("---")
        st.info("💡 提示：ChatBI可以帮助您回答各种问题，进行数据分析和对话交互。")

    # 显示聊天历史
    display_chat_history()

    # 用户输入
    if prompt := st.chat_input("请输入您的问题..."):
        # 添加用户消息到聊天历史
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)

        # 获取AI回复
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            try:
                # 调用AI代理
                response = st.session_state.agent.chat(
                    message=prompt,
                    conversation_id=st.session_state.conversation_id,
                    model_name=model_name,
                    temperature=temperature,
                )

                # 显示回复
                full_response = response
                message_placeholder.markdown(full_response)

                # 添加到聊天历史
                st.session_state.messages.append(
                    {"role": "assistant", "content": full_response}
                )

                logger.info(f"用户提问: {prompt}")
                logger.info(f"AI回复: {full_response[:100]}...")

            except Exception as e:
                error_msg = f"抱歉，处理您的问题时出现错误: {str(e)}"
                message_placeholder.markdown(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )
                logger.error(f"处理用户问题时出错: {e}")


if __name__ == "__main__":
    main()
