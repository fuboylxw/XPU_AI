"""
新生信息问答Agent主程序
基于LangChain、MCP和RAG技术
"""

import streamlit as st
import asyncio
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.agent.school_info_agent import SchoolInfoAgent
from src.rag.document_manager import DocumentManager
from src.config.settings import Settings
from src.utils.logger import setup_logger

# 异步函数包装器
def run_async(coro):
    """运行异步函数"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果事件循环已经在运行，创建一个任务
            task = asyncio.create_task(coro)
            return task
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

def main():
    st.set_page_config(
        page_title="新生信息问答助手",
        page_icon="🎓",
        layout="wide"
    )
    
    st.title("🎓 新生信息问答助手")
    st.markdown("欢迎使用智能问答系统！您可以上传学校相关文档，然后询问任何关于学校的问题。")
    
    # 初始化组件
    if 'settings' not in st.session_state:
        st.session_state.settings = Settings()
        st.session_state.logger = setup_logger(st.session_state.settings)
    
    if 'doc_manager' not in st.session_state:
        st.session_state.doc_manager = DocumentManager(st.session_state.settings)
    
    if 'agent' not in st.session_state:
        st.session_state.agent = SchoolInfoAgent(
            st.session_state.settings, 
            st.session_state.doc_manager
        )
    
    # 侧边栏 - 文档管理
    with st.sidebar:
        st.header("📄 文档管理")
        
        # 文档摘要
        if st.button("查看文档库"):
            summary = run_async(st.session_state.agent.get_document_summary())
            st.markdown(summary)
        
        st.divider()
        
        # 文档上传
        uploaded_files = st.file_uploader(
            "上传学校信息文档",
            type=['pdf', 'docx', 'txt', 'xlsx'],
            accept_multiple_files=True
        )
        
        # 文档类别选择
        category = st.selectbox(
            "文档类别",
            ["专业", "课程", "设施", "政策", "活动", "其他"]
        )
        
        if uploaded_files:
            if st.button("处理上传的文档"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, file in enumerate(uploaded_files):
                    status_text.text(f"正在处理: {file.name}")
                    
                    try:
                        # 读取文件内容
                        file_content = file.read()
                        
                        # 添加文档
                        result = run_async(
                            st.session_state.agent.add_document(
                                file_content, file.name, category
                            )
                        )
                        
                        progress_bar.progress((i + 1) / len(uploaded_files))
                        
                    except Exception as e:
                        st.error(f"处理文件 {file.name} 失败: {str(e)}")
                
                status_text.text("处理完成！")
                st.success(f"成功处理 {len(uploaded_files)} 个文档！")
                
                # 清空上传的文件
                st.rerun()
    
    # 主界面 - 问答
    st.header("💬 智能问答")
    
    # 聊天历史
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "您好！你是西安工程大学新生助手小橙汁，可以帮您解答关于学校的各种问题。请随时提问！"
            }
        ]
    
    # 显示聊天历史
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 用户输入
    if prompt := st.chat_input("请输入您的问题..."):
        # 检查是否是重复的问题（防止Streamlit重新运行导致的重复执行）
        if len(st.session_state.messages) > 0 and st.session_state.messages[-1].get("content") == prompt:
            return
            
        # 添加用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # 生成流式回答
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                # 构建对话历史（排除当前问题和初始欢迎消息）
                conversation_history = [
                    {"role": msg["role"], "content": msg["content"]} 
                    for msg in st.session_state.messages[1:-1]  # 跳过初始欢迎消息和当前用户消息
                    if msg["role"] in ["user", "assistant"]
                ]
                
                # 使用流式工具调用功能回答问题
                async def get_response():
                    nonlocal full_response
                    
                    try:
                        # 使用支持工具调用的流式回答方法
                        if len(conversation_history) > 1:
                            # 多轮对话模式
                            async for chunk in st.session_state.agent.answer_question_with_tools_stream(
                                question=prompt,
                                messages=conversation_history
                            ):
                                full_response += chunk
                                message_placeholder.markdown(full_response + "▌")
                        else:
                            # 单轮对话模式
                            async for chunk in st.session_state.agent.answer_question_with_tools_stream(
                                question=prompt
                            ):
                                full_response += chunk
                                message_placeholder.markdown(full_response + "▌")
                                
                    except Exception as e:
                        # 记录错误并显示错误消息
                        st.error(f"处理问题时出错: {str(e)}")
                        full_response = "抱歉，处理您的问题时遇到了技术问题。请稍后再试或换一种表达方式。"
                    
                    message_placeholder.markdown(full_response)
                
                # 使用asyncio.run来正确处理异步生成器
                try:
                    asyncio.run(get_response())
                except RuntimeError:
                    # 如果已经在事件循环中，使用run_async
                    run_async(get_response())
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                error_msg = f"抱歉，处理您的问题时出现错误: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

if __name__ == "__main__":
    main()