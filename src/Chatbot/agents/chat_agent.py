from typing import List, Dict, Optional, Any, AsyncGenerator, Generator, Union
from langchain_community.chat_models import ChatOpenAI
import os
import hashlib
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain.chains import LLMChain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import os
import json
import time
from datetime import datetime
import asyncio
import nest_asyncio
from PIL import Image

# 在模块导入时应用nest_asyncio
nest_asyncio.apply()

from config.settings import settings
from src.Chatbot.tools.web_search import WebSearchTool
from src.Chatbot.tools.llm_client import LLMClient

# 导入其他智能体
from src.Chatbot.agents.security_audit_agent import SecurityAuditAgent
from src.Chatbot.agents.intent_recognition_agent import IntentRecognitionAgent
from src.Chatbot.agents.knowledge_query_agent import hybrid_retrieval
from src.Chatbot.agents.data_query_agent import DataQueryAgent, UserRole
from src.Chatbot.agents.website_knowledge_agent import WebsiteKnowledgeAgent

from src.Chatbot.utils.logger import setup_logger
from src.Chatbot.utils.memory_storage import memory_storage
from src.Chatbot.utils.global_initializer import is_system_initialized, get_global_component

logger = setup_logger("chat_agent")


class ChatbotAgent:
    """Chatbot对话智能体 - 支持问题改写、意图分析、统一问答和流式响应"""

    def __init__(self):
        # 初始化日志记录器
        self.logger = setup_logger("chat_agent")
        
        # 使用全局初始化器的预加载组件
        if is_system_initialized():
            self.logger.info("使用全局预加载的组件")
            # 使用预加载的LLM
            self.llm = get_global_component('llm')
            self.llm_stream = get_global_component('llm_stream')
            
            # 使用预加载的工具
            self.web_search_tool = get_global_component('web_search_tool')
            
            # 使用预加载的智能体
            self.security_agent = get_global_component('security_agent')
            self.intent_agent = get_global_component('intent_agent')
            self.data_agent = get_global_component('data_agent')
            self.website_knowledge_agent = get_global_component('website_agent')
            
        else:
            # 回退到传统初始化方式
            self.logger.warning("全局初始化器未就绪，使用传统初始化方式")
            
            # 初始化LLM客户端
            self.llm = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
                base_url=settings.OPENAI_MODEL_BASE_URL,
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
            )
            streaming_handler = StreamingStdOutCallbackHandler()
            self.llm_stream = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
                base_url=settings.OPENAI_MODEL_BASE_URL,
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                streaming=True,
                callbacks=[streaming_handler],  # 绑定回调处理器（核心参数）
            )
            # 初始化工具
            self.web_search_tool = WebSearchTool(settings)

            # 初始化统一问答子智能体
            self.security_agent = SecurityAuditAgent()
            self.intent_agent = IntentRecognitionAgent()
            # 移除knowledge_agent，现在直接使用hybrid_retrieval函数
            self.data_agent = DataQueryAgent()

            # 初始化网站知识库智能体（用于学校信息查询）
            self.website_knowledge_agent = WebsiteKnowledgeAgent(
                base_url="https://www.xpu.edu.cn/",
                output_dir=str(settings.project_root / "knowledge_base" / "xpu"),
                max_pages=200,
                delay=0.5,
            )

        # 初始化记忆
        self.memory = None
        
        # 预初始化检索系统（避免在查询时重复初始化）
        self._initialize_retrieval_systems()

        # 会话存储
        self.conversations: Dict[str, List[BaseMessage]] = {}
        self.qa_conversations: Dict[str, List[Dict[str, Any]]] = {}

        # 系统状态
        self.system_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "blocked_queries": 0,
            "start_time": datetime.now(),
        }

        # 初始化缓存系统（用于电话智能体优化）
        self.response_cache = {}
        self.cache_ttl = 300  # 缓存5分钟
        self.max_cache_size = 1000
        self.cache_max_size = 1000  # 添加cache_max_size属性以保持兼容性
        
        # 电话模式配置
        self.phone_mode_config = {
            "max_response_length": 200,  # 电话模式最大响应长度
            "enable_quick_knowledge": True,  # 启用快速知识查询
            "enable_simple_intent": True,  # 启用简化意图识别
            "cache_duration": 600,  # 电话模式缓存10分钟
        }
        
        # 性能统计
        self.performance_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "phone_mode_queries": 0,
            "fast_response_queries": 0,
            "avg_response_time": 0.0,
            "total_response_time": 0.0,
            "response_count": 0,
        }

        # 定义提示词模板
        self._initialize_prompts()

    def _initialize_retrieval_systems(self):
        """预初始化检索系统，避免在查询时重复初始化"""
        try:
            logger.info("开始预初始化检索系统...")
            
            # 如果全局系统已初始化，则使用预加载的检索引擎
            if is_system_initialized():
                self.dense_engine = get_global_component('dense_engine')
                self.sparse_engine = get_global_component('sparse_engine')
                logger.info("使用全局预加载的检索引擎")
            else:
                # 混合检索系统无需预初始化，在调用时动态初始化
                logger.info("混合检索系统将在首次调用时初始化")
            
            logger.info("检索系统预初始化完成")
        except Exception as e:
            logger.warning(f"检索系统预初始化失败: {e}")
            # 不抛出异常，允许系统继续运行，在查询时再初始化

    def _initialize_prompts(self):
        """初始化各种提示词模板(系统提示词和统一问答提示词)"""

        # 提示词1: 问题改写
        self.rewrite_prompt = """
                你是一个问题改写助手。  
                你会收到用户的原始问题和对话上下文。  
                你的任务是：  
                    1. 在保持语义不变的前提下，将用户的问题改写为更清晰、简洁、完整的形式。  
                    2. 衔接上下文，补全必要的省略信息。  
                    3. 不要改变问题意图，不要加入额外解释或答案。  
                    4. 输出时只给出改写后的问题，不要包含其他多余文字。  
                    5. 保持问题的简洁性，不要添加不必要的前缀或修饰词。
                    6. 保持问题的语言风格与用户原始问题一致（如中文或英文）。
                    7. 只修改问题，不做回复
                示例：
                    输入：网信处处长是谁
                    输出：西安工程大学网络与信息化管理处处长是谁
                    输入：近期国家有什么大事
                    输出：在近期我国（中国）有什么重大事件或新闻发生
                # 输出格式
                请直接输出最终改写后的问题，不要添加解释或标签等其他任何内容。
            """

        # 提示词2: 意图分析
        self.intent_prompt = """            
                你是一个意图识别助手。  
                你会收到一个用户问题。你的任务是：  
                1. 判断该问题是否与西安工程大学相关（如校规校纪、奖学金、课程安排、学籍管理、校园生活、招生就业等）。  
                2. 如果是学校相关问题，识别具体意图类别，例如：  
                    - "Scholarship" (奖学金 / 助学金 / 评优评奖)  
                    - "Policy" (校规校纪 / 管理办法 / 文件制度)  
                    - "MajorInfo" (学院 / 专业介绍)  
                    - "Course" (课程安排 / 选课 / 考试 / 成绩)  
                    - "StudentStatus" (学籍管理 / 请假 / 转专业 / 处分)  
                    - "CampusLife" (宿舍 / 饮食 / 校园卡 / 网络 / 校园生活)  
                    - "Admission" (招生 / 报名 / 入学)  
                    - "Employment" (实习 / 就业 / 招聘)  
                    - "OtherSchool" (其他学校相关)  
                3. 如果不是学校相关问题，则 `is_school_related` 返回 False，`Intent_class` 填写 “非学校问题”，`Intent description` 简要描述用户的真实意图。  
                4. 输出必须是严格的 JSON 格式，不能有任何额外说明或文字。  

                输出格式示例：  
                {
                "is_school_related": true,
                "Intent_class": "Scholarship",
                "Intent_description": "用户询问学校奖学金的相关信息"
                }
            """

        # 提示词3: 最终回答生成（学校相关）
        self.school_answer_prompt = """
                你是一个西安工程大学回答助手小丫，你必须基于提供的校园知识库检索结果回答问题。  

                你会收到以下内容：  
                - 改写后的用户问题  
                - 意图分类  
                - 知识库检索结果  

                你的任务是：  
                1. 答案必须完全基于知识库检索结果，提供尽可能详细和全面的回答。  
                2. 如果知识库中包含相关信息：  
                    - 给出详细、清晰、准确的回答，包含所有相关细节和具体信息。  
                    - 回答后附加信息来源，格式为：[来源名称](链接地址)，如果有官方链接请使用超链接格式。  
                    - 如果有多个相关文档，请分别引用并详细说明每个来源的内容。  
                3. 如果知识库中没有相关资料：  
                    - 明确回答："未在知识库中找到相关信息，请参考[学校官网](https://www.xpu.edu.cn)或相关部门公告。"  
                    - 不要编造答案。  
                4. 保持语言自然流畅，适合学生和老师阅读。  
                5. 尽可能提供完整的信息，包括具体的时间、地点、条件、流程等细节，不要因为篇幅限制而省略重要内容。  
                6. 输出时只输出最终的回答，不要包含其他多余文字。 
                7. 语气柔和、友好、礼貌，避免使用正式或严格的语言。
            """

        # 提示词3: 最终回答生成（网络搜索）
        self.web_answer_prompt = """
                你是一个西安工程大学回答助手织语，你必须基于提供的网络搜索结果回答问题。  

                你会收到以下内容：  
                - 改写后的用户问题  
                - 意图分类（非学校问题）  
                - 网络搜索结果  

                你的任务是：  
                1. 根据搜索结果生成一个详细、全面的事实性总结，确保答案客观准确。  
                2. 如果搜索结果中包含多个观点或数据：  
                - 用详细语言概括所有重要结论和细节。  
                - 避免过度推测或主观评价，但要提供完整的信息。  
                3. 如果搜索结果不足以回答：  
                - 明确回答："未找到足够的信息来回答该问题。"  
                - 不要编造答案。  
                4. 回答时保持自然流畅，必须在合适位置引用信息来源，格式为：[来源名称](链接地址)。  
                5. 尽可能提供完整的信息，包括具体的数据、时间、背景等细节，不要因为篇幅限制而省略重要内容。  
                6. 输出时只输出最终的回答，不要包含其他多余文字。 
                7. 语气柔和、友好、礼貌，避免使用正式或严格的语言。
            """

        # 提示词3: 最终回答生成（学校相关）
        self.no_web_answer_prompt = """
                你是一个西安工程大学回答助手织语，请回答问题。  

                你会收到以下内容：  
                - 改写后的用户问题  
                - 意图分类  

                你的任务是：  
                1. 提供尽可能详细和全面的回答。  
                2. 保持语言自然流畅，适合学生和老师阅读。  
                3. 尽可能提供完整的信息，包括具体的时间、地点、条件、流程等细节，不要因为篇幅限制而省略重要内容。  
                4. 输出时只输出最终的回答，不要包含其他多余文字。 
                5. 语气柔和、友好、礼貌，避免使用正式或严格的语言。
            """

        # 提示词4: 最终回答生成（数据查询）
        self.data_query_prompt = """
                你是一个西安工程大学回答助手织语，你必须基于提供的数据查询结果回答问题。  

                你会收到以下内容：  
                - 改写后的用户问题  
                - 意图分类  
                - 数据查询结果  

                你的任务是：  
                1. 答案必须完全基于数据查询结果，提供准确、清晰的数据分析和解读。  
                2. 如果数据查询结果包含有效信息：  
                   - 以结构化方式呈现数据，必要时使用表格或列表格式。  
                   - 提供数据的关键趋势、特点和洞察。  
                   - 确保数据解读准确无误，不要过度推断。  
                3. 如果数据查询结果不完整或有限：  
                   - 明确说明数据的局限性。  
                   - 建议用户如何获取更完整的数据。  
                4. 如果数据查询失败：  
                   - 明确回答："未能获取相关数据，请联系相关部门获取准确信息。"  
                   - 不要编造数据或结果。  
                5. 保持语言专业、清晰，适合学术和管理场景使用。  
                6. 在回答中引用数据来源和时间范围，确保信息可追溯。  
                7. 输出时只输出最终的回答，不要包含其他多余文字。  
                8. 语气柔和、友好、礼貌，避免使用正式或严格的语言。
            """

        # 提示词5: 最终回答生成（电话）
        self.phone_prompt = """
            # 角色设定
            你是一名专业的电话沟通智能体助手织语，负责根据用户的上下文对话、问题、意图描述和查询到的结果，生成自然、礼貌、逻辑清晰的电话回复内容。  
            你的目标是帮助用户通过电话高效、得体地表达信息或获取答案。  
            回答应符合中文口语习惯，语气友好、简洁明确(100字以内)。

            # 输入信息
            - 上下文对话
            - 当前问题
            - 意图描述
            - 查询结果

            # 回复要求
            1. 优先结合“上下文对话”保持语义连贯；
            2. 若“检索结果”中包含明确答案，请基于其内容回答；
            3. 若“检索结果”信息不足，请用自然的电话口语回复；
            4. 保持语气柔和、友好、礼貌；
            5. 输出内容为最终可直接在电话中说出的一句话，不要解释你的思考过程或显示系统信息。

            # 输出格式
            请直接输出最终可朗读的电话回复文本，不要添加解释或标签。

            """

        # 提示词6: 错误处理
        self.error_handling_prompt = ChatPromptTemplate.from_template(
            """
            用户遇到了问题，请生成一个友好的错误回复。

            用户问题：{question}
            错误信息：{error_info}
            错误类型：{error_type}

            请生成一个友好、有帮助的回复，包括：
            1. 对问题的理解
            2. 错误的简单说明
            3. 可能的解决建议
            4. 替代方案

            回复：
            """
        )


    async def answer_question(
        self,
        question: str,
        user_id: str = "guest",
        user_role: str = "guest",
        session_token: Optional[str] = None,
        image_data: Optional[Union[str, bytes, Image.Image]] = None,
        conversation_id: str = "default",
        phone_mode: bool = False,  # 电话模式标识
        fast_response: bool = False,  # 快速响应模式
    ) -> Dict[str, Any]:
        """
        简化的统一问答接口
        流程：意图分析 → 信息查询 → 大模型生成回答

        Args:
            question: 用户问题
            user_id: 用户ID
            user_role: 用户角色 (guest/student/teacher/admin)
            session_token: 会话令牌
            image_data: 图像数据（可选）
            conversation_id: 会话ID
            phone_mode: 电话模式，启用语音优化
            fast_response: 快速响应模式，跳过部分检查

        Returns:
            问答结果
        """
        start_time = time.time()
        
        try:
            logger.info(f"收到问答请求 - 用户: {user_id}, 问题: {question[:50]}...")

            # 电话模式下获取对话历史上下文
            phone_conversation_history = []
            if phone_mode:
                phone_conversation_history = await self._get_phone_conversation_history(user_id)
                logger.info(f"电话模式：获取到 {len(phone_conversation_history)} 条历史对话")

            # 1.题进行意图识别
            intent_result = await self.intent_agent.recognize_text_intent(
                question
            )
            logger.info(f"意图识别结果: {intent_result}")
            
            # 转换user_role为枚举类型
            try:
                user_role_enum = UserRole(user_role.lower())
            except ValueError:
                user_role_enum = UserRole.GUEST

            # 4. 根据意图路由到相应的处理模块
            processing_result = await self._route_by_intent(
                question,
                intent_result,
                user_id,
                user_role_enum,
                session_token,
            )

            # 根据意图类型选择对应的提示词模板
            query_result = processing_result.get("result", {}).get("answer", "")

            intent = intent_result.get("analysis", "无分析信息")
            logger.info(f"查询到的结果: {query_result}")

            
            # 步骤3: 使用LangChain调用大模型生成最终回答
            final_answer = await self._generate_answer_with_langchain(
                question, intent, query_result, phone_mode, phone_conversation_history
            )

            # 构建响应
            response = {
                "success": True,
                "question": question,
                "answer": final_answer,
                "metadata": {
                    "intent_result": intent_result,
                    "query_result": query_result,
                    "user_id": user_id,
                    "user_role": user_role,
                    "conversation_id": conversation_id,
                    "timestamp": datetime.now().isoformat(),
                    "response_time": time.time() - start_time,
                    "phone_mode": phone_mode,
                },
            }

            logger.info(f"问答完成，总耗时: {time.time() - start_time:.2f}s")
            return response

        except Exception as e:
            logger.error(f"问答处理失败: {e}")
            return {
                "success": False,
                "question": question,
                "answer": f"抱歉，处理您的问题时出现了错误：{str(e)}",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "response_time": time.time() - start_time,
            }

    async def answer_question_stream(
        self,
        question: str,
        user_id: str = "guest",
        user_role: str = "guest",
        session_token: Optional[str] = None,
        image_data: Optional[Union[str, bytes, Image.Image]] = None,
        conversation_id: str = "default",
    ) -> AsyncGenerator[str, None]:
        """
        统一问答接口（流式输出版本）

        Args:
            question: 用户问题
            user_id: 用户ID
            user_role: 用户角色
            session_token: 会话令牌
            image_data: 图像数据
            conversation_id: 会话ID

        Yields:
            流式输出的回答片段
        """
        try:
            logger.info(f"收到流式问答请求 - 用户: {user_id}, 问题: {question[:50]}...")

            # 更新系统统计
            self.system_stats["total_queries"] += 1

            # 转换用户角色
            try:
                user_role_enum = UserRole(user_role.lower())
            except ValueError:
                user_role_enum = UserRole.GUEST

            # 1. 安全审核
            security_result = await self._perform_security_audit(
                question, conversation_id
            )
            logger.info(f"安全审核通过")

            if not security_result.get("is_safe", False):
                self.system_stats["blocked_queries"] += 1
                block_message = await self._handle_security_block(
                    question, security_result
                )
                yield block_message["answer"]
                return

            # 2. 获取对话上下文并改写问题
            conversation_context = self._get_conversation_context(conversation_id)
            rewritten_question = self._rewrite_question_sync(
                question, conversation_context
            )
            logger.info(f"改写后的问题: {rewritten_question}")

            # 3. 使用改写后的问题进行意图识别
            intent_result = await self.intent_agent.recognize_text_intent(
                rewritten_question
            )

            # 4. 根据意图路由到相应的处理模块
            processing_result = await self._route_by_intent(
                rewritten_question,
                intent_result,
                user_id,
                user_role_enum,
                session_token,
            )

            # 4.5. 检索上传的文本信息
            uploaded_context = ""
            try:
                # 从内存存储中检索相关的上传内容
                relevant_uploads = memory_storage.search_relevant_content(
                    conversation_id, rewritten_question, max_results=3
                )
                
                if relevant_uploads:
                    upload_texts = []
                    for upload in relevant_uploads:
                        upload_info = f"[{upload.content_type.upper()}]"
                        if upload.original_filename:
                            upload_info += f" {upload.original_filename}:"
                        upload_info += f" {upload.content}"
                        upload_texts.append(upload_info)
                    
                    uploaded_context = "\n".join(upload_texts)
                    logger.info(f"找到 {len(relevant_uploads)} 个相关上传内容")
                else:
                    logger.info("未找到相关的上传内容")
            except Exception as e:
                logger.error(f"检索上传内容时出错: {str(e)}")
                uploaded_context = ""

            # 5. 准备流式输出的提示词
            # 根据意图类型选择对应的提示词模板
            intent_type = processing_result.get("type", "general_answer")

            # 保底初始化，避免未赋值异常
            prompt_template = None

            if intent_type == "knowledge_query":
                # 构建知识查询的内容，包含上传信息
                content_parts = [
                    f"改写后的用户问题：{rewritten_question}",
                    f"意图分析: {intent_result.get('analysis', '无分析信息')}",
                    f"知识库检索结果: {processing_result.get('result', {}).get('answer', '')}"
                ]
                
                # 如果有上传内容，添加到提示词中
                if uploaded_context:
                    content_parts.insert(-1, f"用户上传的相关内容：\n{uploaded_context}")
                
                prompt_template = ChatPromptTemplate.from_messages(
                    [
                        SystemMessage(content=self.school_answer_prompt),
                        HumanMessage(content="\n".join(content_parts)),
                    ]
                )
                logger.info("使用知识库查询提示词模板")
            elif intent_type == "data_query":
                # 构建数据查询的内容，包含上传信息
                content_parts = [
                    f"改写后的用户问题：{rewritten_question}",
                    f"意图分析: {intent_result.get('analysis', '无分析信息')}",
                    f"数据查询结果: {str(processing_result.get('result', {}))}"
                ]
                
                # 如果有上传内容，添加到提示词中
                if uploaded_context:
                    content_parts.insert(-1, f"用户上传的相关内容：\n{uploaded_context}")
                
                prompt_template = ChatPromptTemplate.from_messages(
                    [
                        SystemMessage(content=self.data_query_prompt),
                        HumanMessage(content="\n".join(content_parts)),
                    ]
                )
                logger.info("使用数据查询提示词模板")
            elif intent_type == "general_answer":
                # 对于通用回答，根据意图识别结果判断是否使用网络搜索
                need_web_search = intent_result.get("need_web_search", True)  # 默认为True

                if need_web_search:
                    # 构建网络搜索的内容，包含上传信息
                    content_parts = [
                        f"改写后的用户问题：{rewritten_question}",
                        f"意图分析: {intent_result.get('analysis', '无分析信息')}",
                        f"网络搜索结果: {processing_result.get('result', {}).get('answer', '')}"
                    ]
                    
                    # 如果有上传内容，添加到提示词中
                    if uploaded_context:
                        content_parts.insert(-1, f"用户上传的相关内容：\n{uploaded_context}")
                    
                    # 使用网络搜索提示词模板
                    prompt_template = ChatPromptTemplate.from_messages(
                        [
                            SystemMessage(content=self.web_answer_prompt),
                            HumanMessage(content="\n".join(content_parts)),
                        ]
                    )
                    logger.info("使用网络搜索提示词模板")
                else:
                    # 构建基础回答的内容，包含上传信息
                    content_parts = [
                        f"改写后的用户问题：{rewritten_question}",
                        f"意图分析: {intent_result.get('analysis', '无分析信息')}"
                    ]
                    
                    # 如果有上传内容，添加到提示词中
                    if uploaded_context:
                        content_parts.append(f"用户上传的相关内容：\n{uploaded_context}")
                    
                    # 不需要网络搜索，使用基础提示词模板
                    prompt_template = ChatPromptTemplate.from_messages(
                        [
                            SystemMessage(content=self.no_web_answer_prompt),
                            HumanMessage(content="\n".join(content_parts)),
                        ]
                    )
                    logger.info("使用基础提示词模板（无需网络搜索）")
            
            # 确保 prompt_template 不为 None，提供默认模板
            if prompt_template is None:
                logger.warning(f"未识别的意图类型: {intent_type}，使用默认提示词模板")
                
                # 构建默认回答的内容，包含上传信息
                content_parts = [
                    f"改写后的用户问题：{rewritten_question}",
                    f"意图分析: {intent_result.get('analysis', '无分析信息')}"
                ]
                
                # 如果有上传内容，添加到提示词中
                if uploaded_context:
                    content_parts.append(f"用户上传的相关内容：\n{uploaded_context}")
                
                prompt_template = ChatPromptTemplate.from_messages(
                    [
                        SystemMessage(content=self.no_web_answer_prompt),
                        HumanMessage(content="\n".join(content_parts)),
                    ]
                )

            # 6. 使用流式LLM生成回答
            final_answer = ""

            # 6.1 在流式输出开始前，先保存问题到数据库
            conversation_record_id = self._save_question_to_db(conversation_id, question)
            logger.info(f"问题已保存到数据库，记录ID: {conversation_record_id}")

            # 确保 prompt_template 和其 messages 属性都不为 None
            if prompt_template is None or not hasattr(prompt_template, 'messages') or prompt_template.messages is None:
                logger.error("prompt_template 或其 messages 属性为 None，无法进行流式输出")
                yield "抱歉，系统遇到了问题，无法处理您的请求。"
                return

            logger.info(f"使用提示词模板: {prompt_template.messages}")
            # 直接使用llm_stream进行流式输出，不使用LLMChain
            
            # 实现真正的流式输出
            async for chunk in self.llm_stream.astream(prompt_template.messages):
                if hasattr(chunk, "content") and chunk.content:
                    token = chunk.content
                    if token:
                        yield token
                        final_answer += token
                        # 6.2 在流式输出过程中实时更新答案到数据库
                        self._update_answer_in_db(conversation_record_id, final_answer)
                        # 添加小延迟确保真正的流式输出
                        await asyncio.sleep(0.001)

            # 7. 最终更新会话历史（内存中的记录）
            self._update_qa_conversation_memory(conversation_id, question, final_answer)

            # 7.5. 保留上传内容内存供后续问题使用
            # 注释掉自动清理逻辑，让用户可以在同一会话中多次询问上传内容相关问题
            # try:
            #     if uploaded_context:  # 只有在使用了上传内容时才清理
            #         memory_storage.clear_conversation(conversation_id)
            #         logger.info(f"已自动清理会话 {conversation_id} 的上传内容内存")
            # except Exception as e:
            #     logger.error(f"清理上传内容内存时出错: {str(e)}")
            
            # 记录上传内容的使用情况
            if uploaded_context:
                logger.info(f"会话 {conversation_id} 使用了上传内容进行回答，内容将保留供后续问题使用")

            # 8. 更新统计
            self.system_stats["successful_queries"] += 1

        except Exception as e:
            logger.error(f"流式问答处理失败: {e}")
            error_response = await self._handle_error(question, str(e), "STREAM_ERROR")
            yield error_response

    async def _generate_streaming_response(
        self, messages: List[BaseMessage]
    ) -> AsyncGenerator[str, None]:
        """生成流式响应"""
        response = await self.llm_stream.agenerate([messages])
        for chunk in response.generations[0][0].text:
            yield chunk
            await asyncio.sleep(0.01)  # 控制输出速度

    async def _perform_security_audit(
        self, question: str, conversation_id: str
    ) -> Dict[str, Any]:
        """执行安全审核"""
        try:
            # 获取对话上下文
            context = self._get_qa_conversation_context(conversation_id)

            # 执行安全审核
            audit_result = await self.security_agent.audit_content(question, context)

            return audit_result

        except Exception as e:
            logger.error(f"安全审核失败: {e}")
            return {"is_safe": False, "risk_level": "high", "error": str(e)}

    async def _perform_intent_recognition(
        self, question: str, image_data: Optional[Union[str, bytes, Image.Image]]
    ) -> Dict[str, Any]:
        """执行意图识别"""
        try:
            if image_data:
                # 多模态意图识别
                intent_result = await self.intent_agent.recognize_multimodal_intent(
                    question, image_data
                )
            else:
                # 纯文本意图识别
                intent_result = await self.intent_agent.recognize_text_intent(question)

            return intent_result

        except Exception as e:
            logger.error(f"意图识别失败: {e}")
            return {
                "is_school_related": False,
                "intent_class": "Other",
                "confidence": 0.0,
                "error": str(e),
            }

    async def _route_by_intent(
        self,
        question: str,
        intent_result: Dict[str, Any],
        user_id: str,
        user_role: UserRole,
        session_token: Optional[str],
    ) -> Dict[str, Any]:
        """根据意图路由到相应的处理模块"""
        intent_class = intent_result.get("intent_class", "Other")
        is_school_related = intent_result.get("is_school_related", False)
        need_web_search = intent_result.get("need_web_search", True)

        try:
            if not is_school_related and intent_class == "general_answer":
                # 非校园相关问题，使用网络搜索
                # search 为同步方法，返回字符串；不要使用 await
                if need_web_search:
                    search_text = self.web_search_tool.search(question)
                else:
                    search_text = ""
                # 统一返回结构：包装为包含 answer 的字典，便于下游使用
                return {"type": "general_answer", "result": {"answer": search_text}}

            # 校园相关问题，根据具体意图分类处理
            elif is_school_related and intent_class == "knowledge_query":
                # 使用混合检索进行知识查询
                try:
                    # 从意图识别结果中获取关键词
                    keywords = intent_result.get("keywords_matched", [])
                    if not keywords:
                        # 如果没有关键词，使用问题本身作为关键词
                        keywords = [question]
                    
                    # 调用混合检索函数
                    hybrid_results = await hybrid_retrieval(
                        query_text=question,
                        top_k=5,  # 默认返回5个结果
                        keywords=keywords
                    )
                    
                    if hybrid_results:
                        logger.info(f"混合检索成功，找到 {len(hybrid_results)} 个相关结果")
                        # 格式化混合检索结果
                        formatted_content = self._format_hybrid_results(hybrid_results)
                        knowledge_result = {
                            "success": True,
                            "answer": formatted_content,
                            "source": "hybrid_retrieval",
                            "results_count": len(hybrid_results)
                        }
                    else:
                        logger.warning("混合检索未找到相关结果")
                        knowledge_result = {
                            "success": False,
                            "error": "未找到相关信息",
                            "source": "hybrid_retrieval",
                            "results_count": 0
                        }
                        
                except Exception as e:
                    logger.error(f"混合检索失败: {e}")
                    knowledge_result = {
                        "success": False,
                        "error": f"检索失败: {str(e)}",
                        "source": "hybrid_retrieval",
                        "results_count": 0
                    }
                
                # 记录知识库查询结果
                if knowledge_result and knowledge_result.get("success", False):
                    answer_preview = knowledge_result.get("answer", "")[:200] + "..." if len(knowledge_result.get("answer", "")) > 200 else knowledge_result.get("answer", "")
                    logger.info(f"知识库查询成功 - 问题: {question[:50]}... | 结果预览: {answer_preview}")
                else:
                    logger.warning(f"知识库查询失败 - 问题: {question[:50]}... | 错误: {knowledge_result.get('error', '未知错误') if knowledge_result else '返回结果为空'}")
                return {"type": "knowledge_query", "result": knowledge_result}

            elif is_school_related and intent_class == "data_query":
                # 数据查询
                if user_role == UserRole.GUEST:
                    return {
                        "type": "data_query",
                        "result": {
                            "success": False,
                            "error": "数据查询需要登录，游客用户无法访问数据功能",
                            "suggestion": "请联系相关部门或登录后重试",
                        },
                    }

                data_result = await self.data_agent.query_data(
                    question, user_id, user_role, session_token
                )
                return {"type": "data_query", "result": data_result}


        except Exception as e:
            logger.error(f"意图路由处理失败: {e}")
            return {"type": "error", "result": {"success": False, "error": str(e)}}

    async def _handle_security_block(
        self, question: str, security_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理安全阻止的情况"""
        violations = security_result.get("violations", [])
        risk_level = security_result.get("risk_level", "unknown")

        if risk_level == "high":
            message = "您的问题包含不当内容，无法处理。请确保问题内容符合校园规范。"
        elif risk_level == "medium":
            message = "您的问题可能包含敏感内容，建议重新表述后再次提问。"
        else:
            message = "您的问题需要进一步审核，请稍后重试或联系相关部门。"

        if violations:
            violation_types = [v.get("type", "未知") for v in violations]
            message += f"\n检测到的问题类型：{', '.join(set(violation_types))}"

        return {
            "success": False,
            "question": question,
            "answer": message,
            "blocked": True,
            "security_result": security_result,
            "timestamp": datetime.now().isoformat(),
        }

    async def _handle_error(
        self, question: str, error_info: str, error_type: str
    ) -> str:
        """处理错误情况"""
        try:
            chain = self.error_handling_prompt | self.llm | StrOutputParser()
            error_response = await chain.ainvoke(
                {
                    "question": question,
                    "error_info": error_info,
                    "error_type": error_type,
                }
            )

            return error_response

        except Exception as e:
            logger.error(f"错误处理失败: {e}")
            return f"抱歉，系统遇到错误无法处理您的问题。请稍后重试或联系技术支持。"

    def _get_qa_conversation_context(self, conversation_id: str) -> List[str]:
        """获取对话上下文"""
        conversation = self.qa_conversations.get(conversation_id, [])
        # 返回最近5轮对话的问题部分
        return [item["question"] for item in conversation[-5:]]

    def _update_qa_conversation(self, conversation_id: str, question: str, answer: str):
        """更新对话历史并存储到数据库"""
        # 内存中更新
        if conversation_id not in self.qa_conversations:
            self.qa_conversations[conversation_id] = []

        current_time = datetime.now().isoformat()
        self.qa_conversations[conversation_id].append(
            {"question": question, "answer": answer, "timestamp": current_time}
        )

        # 保持对话历史在合理长度
        if len(self.qa_conversations[conversation_id]) > 50:
            self.qa_conversations[conversation_id] = self.qa_conversations[
                conversation_id
            ][-25:]

        # 存储到数据库
        try:
            from src.Chatbot.utils.db_utils import get_db_manager

            db_manager = get_db_manager()
            db_manager.save_conversation(
                conversation_id, question, answer, current_time
            )
            logger.info(f"对话记录已存储到数据库，会话ID: {conversation_id}")
        except Exception as e:
            logger.error(f"存储对话记录到数据库失败: {e}")
            # 数据库存储失败不影响内存中的对话历史

    def _save_question_to_db(self, conversation_id: str, question: str) -> Optional[int]:
        """
        在流式输出开始前，先保存问题到数据库
        
        Args:
            conversation_id: 会话ID
            question: 用户问题
            
        Returns:
            数据库记录ID，如果保存失败返回None
        """
        try:
            from src.Chatbot.utils.db_utils import get_db_manager
            
            db_manager = get_db_manager()
            # 先保存问题，答案为空
            record_id = db_manager.save_conversation_with_id(
                conversation_id, question, "", "default_user"
            )
            logger.info(f"问题已保存到数据库，会话ID: {conversation_id}, 记录ID: {record_id}")
            return record_id
        except Exception as e:
            logger.error(f"保存问题到数据库失败: {e}")
            return None

    def _update_answer_in_db(self, record_id: Optional[int], answer: str):
        """
        在流式输出过程中实时更新答案到数据库
        
        Args:
            record_id: 数据库记录ID
            answer: 当前累积的答案内容
        """
        if record_id is None:
            return
            
        try:
            from src.Chatbot.utils.db_utils import get_db_manager
            
            db_manager = get_db_manager()
            db_manager.update_conversation_answer(record_id, answer)
            # 只在答案较短时记录日志，避免日志过多
            if len(answer) % 100 == 0:  # 每100个字符记录一次
                logger.debug(f"答案已更新到数据库，记录ID: {record_id}, 答案长度: {len(answer)}")
        except Exception as e:
            logger.error(f"更新答案到数据库失败: {e}")

    def _update_qa_conversation_memory(self, conversation_id: str, question: str, answer: str):
        """
        更新内存中的对话历史（不涉及数据库操作）
        
        Args:
            conversation_id: 会话ID
            question: 用户问题
            answer: AI回答
        """
        # 内存中更新
        if conversation_id not in self.qa_conversations:
            self.qa_conversations[conversation_id] = []

        current_time = datetime.now().isoformat()
        self.qa_conversations[conversation_id].append(
            {"question": question, "answer": answer, "timestamp": current_time}
        )

        # 保持对话历史在合理长度
        if len(self.qa_conversations[conversation_id]) > 50:
            self.qa_conversations[conversation_id] = self.qa_conversations[
                conversation_id
            ][-25:]
            
        logger.info(f"内存中的对话历史已更新，会话ID: {conversation_id}")

    def create_user_session(self, user_id: str, user_role: str) -> str:
        """创建用户会话"""
        try:
            user_role_enum = UserRole(user_role.lower())
            session_token = self.data_agent.create_user_session(user_id, user_role_enum)
            logger.info(f"为用户 {user_id} 创建会话")
            return session_token
        except ValueError:
            logger.error(f"无效的用户角色: {user_role}")
            return ""

    def revoke_user_session(self, user_id: str):
        """撤销用户会话"""
        self.data_agent.revoke_user_session(user_id)
        logger.info(f"撤销用户 {user_id} 的会话")

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        uptime = datetime.now() - self.system_stats["start_time"]

        return {
            "system_uptime": str(uptime),
            "total_queries": self.system_stats["total_queries"],
            "successful_queries": self.system_stats["successful_queries"],
            "blocked_queries": self.system_stats["blocked_queries"],
            "success_rate": f"{(self.system_stats['successful_queries']/max(self.system_stats['total_queries'], 1))*100:.2f}%",
            "active_conversations": len(self.qa_conversations),
            "components_status": {
                "security_agent": "active",
                "intent_agent": "active",
                "knowledge_agent": "active",
                "data_agent": "active",
            },
            "statistics": {
                "security_audit": self.security_agent.get_audit_statistics(),
                "intent_recognition": self.intent_agent.get_recognition_statistics(),
                "knowledge_query": {"status": "hybrid_retrieval_active"},  # 混合检索无统计信息
                "data_query": self.data_agent.get_query_statistics(),
            },
        }

    def clear_conversation(self, conversation_id: str):
        """清空指定对话"""
        if conversation_id in self.qa_conversations:
            del self.qa_conversations[conversation_id]
            logger.info(f"清空对话: {conversation_id}")

    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return self.qa_conversations.get(conversation_id, [])

    def _get_conversation_context(self, conversation_id: str) -> str:
        """
        获取对话上下文
        先判断缓存(Redis)中是否有对应信息，若没有则查询数据库信息并将信息保存到缓存中，设置30分钟过期时间
        """
        try:
            # 导入数据库工具
            from ..utils.db_utils import get_db_manager

            # 获取数据库管理器
            db_manager = get_db_manager()
            redis_conn = db_manager.get_redis_connection()

            # 缓存键名
            cache_key = f"conversation_context:{conversation_id}"

            # 先检查Redis缓存
            cached_context = redis_conn.get(cache_key)
            if cached_context:
                self.logger.info(f"从Redis缓存获取对话上下文，会话ID: {conversation_id}")
                return (
                    cached_context.decode("utf-8")
                    if isinstance(cached_context, bytes)
                    else cached_context
                )

            # 缓存中没有，从数据库获取对话历史
            conversation = db_manager.get_conversation_history(conversation_id, limit=5)

            if not conversation:
                # 如果数据库中没有记录，尝试从内存中获取
                memory_conversation = self.qa_conversations.get(conversation_id, [])
                if not memory_conversation:
                    return ""
                conversation = memory_conversation[-5:]

            # 构建上下文字符串
            context_parts = []
            for item in conversation:
                context_parts.append(f"用户: {item['question']}")
                context_parts.append(f"助手: {item['answer']}")

            context_str = "\n".join(context_parts)

            # 将结果保存到Redis缓存，设置30分钟过期时间
            redis_conn.setex(cache_key, 1800, context_str)  # 1800秒 = 30分钟
            self.logger.info(f"对话上下文已保存到Redis缓存，会话ID: {conversation_id}，过期时间: 30分钟")

            return context_str

        except Exception as e:
            # 如果数据库操作失败，回退到原来的内存方式
            self.logger.error(f"从数据库/缓存获取对话上下文失败: {e}")

            # 使用内存中的对话记录
            memory_conversation = self.qa_conversations.get(conversation_id, [])
            if not memory_conversation:
                return ""

            # 构建上下文字符串
            context_parts = []
            for item in memory_conversation[-5:]:
                context_parts.append(f"用户: {item['question']}")
                context_parts.append(f"助手: {item['answer']}")

            return "\n".join(context_parts)



    def get_knowledge_for_Intent_class_sync(self, Intent_class: str, query: str) -> str:
        """根据意图类别获取知识库信息 - 同步版本

        Args:
            Intent_class: 意图类别
            query: 用户查询

        Returns:
            知识库检索结果
        """
        try:
            # 使用文档管理器检索相关文档
            if not Intent_class or not isinstance(Intent_class, str):
                logger.warning(f"无效的意图类别: {Intent_class}")
                return "无法识别的意图类别"

            if not results:
                logger.info(f"未找到意图类别 {Intent_class} 的知识库信息")
                return ""

            # 格式化结果
            formatted_results = []
            for doc in results:
                formatted_results.append(
                    f"文档: {doc.metadata.get('source', '未知')}\n内容: {doc.page_content}"
                )

            knowledge_text = "\n\n".join(formatted_results)
            logger.info(f"找到意图类别 {Intent_class} 的知识库信息: {len(results)} 条")

            return knowledge_text
        except Exception as e:
            logger.error(f"知识库检索失败: {e}")
            return f"知识库检索出错: {str(e)}"

    async def get_knowledge_for_Intent_class(
        self, Intent_class: str, query: str
    ) -> str:
        """根据意图类别获取知识库信息

        Args:
            Intent_class: 意图类别
            query: 用户查询

        Returns:
            知识库检索结果
        """
        # 将意图类别转换为目录名格式
        Intent_class_dir = Intent_class.lower().replace(" ", "_")

        # 检查知识库目录是否存在
        knowledge_dir = os.path.join(
            self.document_manager.knowledge_dir, Intent_class_dir
        )
        if not os.path.exists(knowledge_dir) or not os.path.isdir(knowledge_dir):
            self.logger.info(f"意图类别 {Intent_class_dir} 的知识库目录不存在，跳过检索")
            return ""

        # 搜索知识库
        search_results = self.KnowledgeBase.search(query, Intent_class=Intent_class_dir)

        if not search_results:
            self.logger.info(f"未找到意图类别 {Intent_class_dir} 的知识库信息")
            return ""

        # 合并搜索结果
        knowledge_text = "\n\n".join([result["content"] for result in search_results])
        self.logger.info(f"找到意图类别 {Intent_class_dir} 的知识库信息: {len(search_results)} 条")

        return knowledge_text

    def _rewrite_question_sync(self, question: str, chat_history: str = "") -> str:
        """问题改写 - 同步版本"""

        try:
            # 将对话上下文作为普通文本内联到提示词，避免 MessagesPlaceholder 期望 BaseMessage 列表
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.rewrite_prompt),
                    HumanMessage(content=f"对话上下文：\n{chat_history}\n\n用户问题：{question}"),
                ]
            )
            chain = LLMChain(llm=self.llm, prompt=prompt)
            # 直接调用，无需提供 chat_history 变量
            response = chain.invoke({"question": question})
            # 处理返回值
            if isinstance(response, dict) and "text" in response:
                response_text = response["text"]
            elif isinstance(response, str):
                response_text = response
            else:
                response_text = str(response)
            return response_text.strip()
        except Exception as e:
            logger.error(f"问题改写失败: {e}")
            return question  # 如果改写失败，返回原问题

    async def _rewrite_question(
        self, question: str, conversation_context: str = ""
    ) -> str:
        """
        异步方法：结合上下文对问题进行改写

        Args:
            question: 原始问题
            conversation_context: 对话上下文

        Returns:
            改写后的问题
        """
        try:
            # 如果没有上下文，直接返回原问题
            if not conversation_context:
                return question

            # 使用同步方法进行问题改写 - 不需要await，因为是同步方法
            rewritten_question = self._rewrite_question_sync(
                question, conversation_context
            )
            return rewritten_question
        except Exception as e:
            logger.error(f"问题改写失败: {e}")
            # 出错时返回原问题
            return question

    def _analyze_intent_sync(self, question: str) -> str:
        """意图分析 - 同步版本"""

        try:
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(self.intent_prompt),
                    HumanMessage(content=f"用户问题: {question}"),
                ]
            )
            chain = LLMChain(
                llm=self.llm, prompt=prompt, output_parser=JsonOutputParser()
            )
            response = chain.invoke({"question": question})
            # 处理返回值
            if isinstance(response, dict) and "text" in response:
                response_text = response["text"]
            elif isinstance(response, str):
                response_text = response
            else:
                response_text = str(response)

            # 尝试解析JSON
            try:
                return json.loads(response_text.strip())
            except:
                # 如果解析失败，返回默认意图
                return {
                    "is_school_related": False,
                    "Intent_class": "其他",
                    "Intent_description": "意图分析失败",
                }
        except Exception as e:
            logger.error(f"意图分析失败: {e}")
            return {
                "is_school_related": False,
                "Intent_class": "其他",
                "Intent_description": "意图分析失败",
            }





    async def _generate_final_answer(
        self,
        search_results: str,
        Intent_description: str,
        rewritten_question: str,
        is_school_related: bool,
    ) -> AsyncGenerator[str, None]:
        """生成最终回答（流式）"""
        try:
            # 选择适当的提示词模板
            if is_school_related:
                system_prompt = self.school_answer_prompt
                user_prompt = f"""
                改写后的用户问题：{rewritten_question}
                意图分析: {Intent_description}                
                知识库检索结果: {search_results}
                """
                logger.info("使用学校相关提示词模板")
            else:
                system_prompt = self.web_answer_prompt
                user_prompt = f"""
                改写后的用户问题：{rewritten_question}
                意图分析: {Intent_description}              
                网络搜索结果: {search_results}
                """
                logger.info("使用网络搜索提示词模板")

            # 提示词生成
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            chain = LLMChain(llm=self.llm_stream, prompt=prompt)

            # 传入所有变量：历史对话、网络搜索信息、知识库信息、当前问题
            logger.info(f"开始生成回答，搜索结果长度: {len(search_results)}")

            # 实现与大模型同步的真正流式输出，优化延迟时间
            previous_text = ""

            async for chunk in chain.astream(
                {
                    "rewritten_question": rewritten_question,
                    "Intent_description": Intent_description,
                    "search_results": search_results,
                }
            ):
                if chunk["event"] == "on_llm_new_token":
                    current_text = chunk["data"]
                    # 只输出新增的部分
                    new_text = current_text[len(previous_text) :]
                    # 立即返回每个新增的字符
                    if new_text:
                        yield new_text
                    previous_text = current_text

        except Exception as e:
            error_msg = f"生成最终回答时出错: {str(e)}"
            logger.error(error_msg)
            import traceback

            logger.error(f"错误详情: {traceback.format_exc()}")
            yield f"抱歉，处理您的请求时出现错误: {str(e)}"

    async def chat_stream(
        self,
        message: str,
        conversation_id: str = "default",
        model_name: str = None,
        temperature: float = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式对话处理 - 实现完整的处理流程

        Args:
            message: 用户输入消息
            conversation_id: 会话ID
            model_name: 模型名称
            temperature: 温度参数

        Yields:
            流式回答内容
        """
        try:
            logger.info(f"收到用户消息: {message}")

            # 更新模型配置（如果提供）
            if model_name or temperature is not None:
                self._update_model_config(model_name, temperature)

            # 1. 获取对话上下文
            context = self._get_conversation_context(conversation_id)

            # 2. 问题改写
            rewritten_question = self._rewrite_question_sync(message, context)
            logger.info(f"改写后的问题: {rewritten_question}")

            # 3. 意图分析
            intent_string = self._analyze_intent_sync(rewritten_question)
            logger.info(f"意图分析结果: {intent_string}")

            # 解析意图
            intent = intent_string  # 已经是字典类型
            logger.info(
                f"解析后的意图: {intent['Intent_class'] if 'Intent_class' in intent else '未知'}"
            )

            # 4. 根据意图选择检索方式
            is_school_related = intent.get("is_school_related", False)
            intent_class = intent.get("Intent_class", None)
            Intent_description = intent.get("Intent_description", None)

            if is_school_related:
                search_results = self.get_knowledge_for_Intent_class_sync(
                    intent_class, rewritten_question
                )
                logger.info("使用知识库检索")
            else:
                search_results = self.web_search_tool.search(rewritten_question)
                logger.info("使用网络搜索")

                # 确保search_results不是协程
                if asyncio.iscoroutine(search_results):
                    search_results = await search_results

            logger.info(f"检索结果: {search_results}")

            # 5. 生成流式回答
            response_generator = self._generate_final_answer(
                search_results,
                Intent_description,
                rewritten_question,
                is_school_related,
            )

            # 用于存储完整回复的变量
            full_response = ""

            # 流式输出并同时收集完整回复
            async for chunk in response_generator:
                # 确保chunk是字符串
                if isinstance(chunk, str):
                    chunk_str = chunk
                elif hasattr(chunk, "content"):
                    chunk_str = chunk.content
                else:
                    chunk_str = str(chunk)

                # 先返回再存储，确保立即响应
                yield chunk_str
                full_response += chunk_str

            # 更新会话历史
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []

            # 存储用户消息和AI完整回复
            self.conversations[conversation_id].append(
                {"role": "user", "content": message}
            )
            self.conversations[conversation_id].append(
                {"role": "assistant", "content": full_response}
            )

            # 限制历史记录长度
            if (
                len(self.conversations[conversation_id])
                > settings.MAX_CONVERSATION_HISTORY * 2
            ):
                self.conversations[conversation_id] = self.conversations[
                    conversation_id
                ][-settings.MAX_CONVERSATION_HISTORY * 2 :]

        except Exception as e:
            logger.error(f"流式对话处理失败: {e}")
            yield f"抱歉，处理您的请求时出现错误: {str(e)}"

    def _update_model_config(self, model_name: str = None, temperature: float = None):
        """更新模型配置"""
        if model_name:
            self.llm_client = LLMClient(
                api_key=settings.OPENAI_API_KEY,
                model=model_name,
                base_url=settings.OPENAI_MODEL_BASE_URL,
                temperature=temperature
                if temperature is not None
                else settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
            )
        elif temperature is not None:
            self.llm_client = LLMClient(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
                base_url=settings.OPENAI_MODEL_BASE_URL,
                temperature=temperature,
                max_tokens=settings.OPENAI_MAX_TOKENS,
            )





    # ==================== 优化功能辅助方法 ====================

    def _generate_cache_key(self, question: str, user_role: str, phone_mode: bool) -> str:
        """生成缓存键"""
        import hashlib
        key_data = f"{question.lower().strip()}_{user_role}_{phone_mode}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存响应"""
        try:
            if cache_key in self.response_cache:
                cached_item = self.response_cache[cache_key]
                # 检查缓存是否过期
                if time.time() - cached_item["timestamp"] < self.cache_ttl:
                    self.performance_stats["cache_hits"] += 1
                    logger.info(f"缓存命中: {cache_key[:16]}...")
                    return cached_item["response"]
                else:
                    # 删除过期缓存
                    del self.response_cache[cache_key]
            
            self.performance_stats["cache_misses"] += 1
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None

    async def _cache_response_async(self, cache_key: str, response: Dict[str, Any]):
        """异步缓存响应"""
        try:
            # 清理过期缓存
            if len(self.response_cache) >= self.cache_max_size:
                await self._cleanup_cache()
            
            self.response_cache[cache_key] = {
                "response": response,
                "timestamp": time.time()
            }
            logger.debug(f"响应已缓存: {cache_key[:16]}...")
        except Exception as e:
            logger.error(f"缓存响应失败: {e}")

    async def _cleanup_cache(self):
        """清理过期缓存"""
        try:
            current_time = time.time()
            expired_keys = [
                key for key, item in self.response_cache.items()
                if current_time - item["timestamp"] > self.cache_ttl
            ]
            
            for key in expired_keys:
                del self.response_cache[key]
            
            # 如果仍然超过限制，删除最旧的条目
            if len(self.response_cache) >= self.cache_max_size:
                sorted_items = sorted(
                    self.response_cache.items(),
                    key=lambda x: x[1]["timestamp"]
                )
                for key, _ in sorted_items[:len(sorted_items) // 2]:
                    del self.response_cache[key]
            
            logger.info(f"缓存清理完成，当前缓存条目数: {len(self.response_cache)}")
        except Exception as e:
            logger.error(f"缓存清理失败: {e}")

 

    async def _perform_security_audit_cached(
        self, question: str, conversation_id: str
    ) -> Dict[str, Any]:
        """带缓存的安全审核"""
        # 为安全审核添加简单缓存
        audit_cache_key = f"security_{hashlib.md5(question.encode()).hexdigest()}"
        
        if audit_cache_key in self.response_cache:
            cached_item = self.response_cache[audit_cache_key]
            if time.time() - cached_item["timestamp"] < 60:  # 安全审核缓存1分钟
                return cached_item["response"]
        
        result = await self._perform_security_audit(question, conversation_id)
        
        # 缓存安全审核结果
        self.response_cache[audit_cache_key] = {
            "response": result,
            "timestamp": time.time()
        }
        
        return result

    async def _perform_intent_recognition_cached(
        self, question: str, image_data: Optional[Union[str, bytes, Image.Image]]
    ) -> Dict[str, Any]:
        """带缓存的意图识别"""
        # 为意图识别添加缓存
        intent_cache_key = f"intent_{hashlib.md5(question.encode()).hexdigest()}"
        
        if intent_cache_key in self.response_cache:
            cached_item = self.response_cache[intent_cache_key]
            if time.time() - cached_item["timestamp"] < 120:  # 意图识别缓存2分钟
                return cached_item["response"]
        
        result = await self._perform_intent_recognition(question, image_data)
        
        # 缓存意图识别结果
        self.response_cache[intent_cache_key] = {
            "response": result,
            "timestamp": time.time()
        }
        
        return result

    async def _route_by_intent_optimized(
        self,
        question: str,
        intent_result: Dict[str, Any],
        user_id: str,
        user_role: UserRole,
        session_token: Optional[str],
        phone_mode: bool = False,
    ) -> Dict[str, Any]:
        """优化的意图路由处理"""
        try:
            # 电话模式使用更快的处理路径
            if phone_mode:
                return await self._route_by_intent_phone_mode(
                    question, intent_result, user_id, user_role, session_token
                )
            else:
                return await self._route_by_intent(
                    question, intent_result, user_id, user_role, session_token
                )
        except Exception as e:
            logger.error(f"优化意图路由失败: {e}")
            return {"type": "error", "result": {"success": False, "error": str(e)}}

    async def _route_by_intent_phone_mode(
        self,
        question: str,
        intent_result: Dict[str, Any],
        user_id: str,
        user_role: UserRole,
        session_token: Optional[str],
    ) -> Dict[str, Any]:
        """电话模式的意图路由处理"""
        intent_class = intent_result.get("intent_class", "Other")
        is_school_related = intent_result.get("is_school_related", False)

        try:
            if is_school_related and intent_class == "knowledge_query":
                # 混合检索查询（电话模式优化）
                keywords = intent_result.get("keywords_matched", [])
                if not keywords:
                    keywords = [question]  # 如果没有关键词，使用问题本身
                
                # 调用混合检索函数
                hybrid_results = await hybrid_retrieval(
                    query_text=question,
                    top_k=5,
                    keywords=keywords
                )
                
                # 格式化结果
                formatted_content = self._format_hybrid_results(hybrid_results)
                
                return {
                    "type": "knowledge_query", 
                    "result": {
                        "success": True,
                        "content": formatted_content,
                        "source": "hybrid_retrieval",
                        "results_count": len(hybrid_results)
                    }
                }
            
            elif is_school_related and intent_class == "data_query":
                # 数据查询（电话模式简化）
                if user_role == UserRole.GUEST:
                    return {
                        "type": "data_query",
                        "result": {
                            "success": False,
                            "error": "数据查询需要身份验证",
                            "suggestion": "请联系相关部门",
                        },
                    }
                # 简化的数据查询
                data_result = await self.data_agent.query_data(
                    question, user_id, user_role, session_token
                )
                return {"type": "data_query", "result": data_result}
            
            else:
                # 非校园相关或其他类型，返回简化回答
                return {
                    "type": "general_answer", 
                    "result": {
                        "answer": "如需了解校园信息，请详细描述您的问题。其他问题建议联系相关部门。"
                    }
                }

        except Exception as e:
            logger.error(f"电话模式意图路由处理失败: {e}")
            return {"type": "error", "result": {"success": False, "error": str(e)}}

    async def _synthesize_final_answer_optimized(
        self,
        question: str,
        intent_result: Dict[str, Any],
        processing_result: Dict[str, Any],
        security_result: Dict[str, Any],
        phone_mode: bool = False,
    ) -> str:
        """优化的最终回答生成"""
        try:
            result_type = processing_result.get("type", "unknown")
            result_data = processing_result.get("result", {})

            if result_type == "knowledge_query":
                answer = result_data.get("answer", "")
                if answer and answer != "无结果":
                    # 电话模式截断长回答
                    if phone_mode and len(answer) > self.phone_mode_config["max_response_length"]:
                        answer = answer[:self.phone_mode_config["max_response_length"]] + "..."
                    return answer
                else:
                    return "抱歉，我没有找到相关信息。" + ("请联系相关部门。" if phone_mode else "您可以尝试换个方式提问，或者联系相关部门获取帮助。")

            elif result_type == "data_query":
                if result_data.get("success", False):
                    answer = result_data.get("answer", "数据查询完成。")
                    if phone_mode and len(answer) > self.phone_mode_config["max_response_length"]:
                        answer = answer[:self.phone_mode_config["max_response_length"]] + "..."
                    return answer
                else:
                    error_msg = result_data.get("error", "数据查询失败")
                    suggestion = result_data.get("suggestion", "")
                    if phone_mode:
                        return f"{error_msg}。{suggestion}" if suggestion else error_msg
                    else:
                        return f"{error_msg}。{suggestion}" if suggestion else error_msg

            elif result_type == "general_answer":
                answer = result_data.get("answer", "抱歉，我无法回答这个问题。")
                if phone_mode and len(answer) > self.phone_mode_config["max_response_length"]:
                    answer = answer[:self.phone_mode_config["max_response_length"]] + "..."
                return answer

            else:
                return "抱歉，我无法理解您的问题。" if phone_mode else "抱歉，我无法理解您的问题，请尝试重新表述。"

        except Exception as e:
            logger.error(f"优化最终回答生成失败: {e}")
            return "抱歉，系统暂时繁忙，请稍后重试。"

    async def _handle_phone_fast_response(
        self,
        question: str,
        user_id: str,
        user_role: UserRole,
        conversation_id: str,
        cache_key: str,
        start_time: float,
    ) -> Dict[str, Any]:
        """处理电话模式快速响应"""
        try:
            logger.info("使用电话模式快速响应路径")
            
            # 更新统计
            asyncio.create_task(self._update_stats_async("phone_mode_queries"))
            asyncio.create_task(self._update_stats_async("fast_response_queries"))
            
            # 简化的意图识别（仅基于关键词）
            intent_result = await self._simple_intent_recognition(question)
            
            # 快速路由处理
            processing_result = await self._route_by_intent_phone_mode(
                question, intent_result, user_id, user_role, None
            )
            
            # 生成简化回答
            final_answer = await self._synthesize_final_answer_optimized(
                question, intent_result, processing_result, {"is_safe": True}, phone_mode=True
            )
            
            # 构建响应
            response = {
                "success": True,
                "question": question,
                "answer": final_answer,
                "metadata": {
                    "intent_result": intent_result,
                    "processing_result": processing_result,
                    "user_id": user_id,
                    "user_role": user_role.value if hasattr(user_role, 'value') else str(user_role),
                    "conversation_id": conversation_id,
                    "timestamp": datetime.now().isoformat(),
                    "response_time": time.time() - start_time,
                    "phone_mode": True,
                    "fast_response": True,
                },
            }
            
            # 异步更新会话历史和缓存
            asyncio.create_task(self._update_conversation_async(conversation_id, question, final_answer))
            asyncio.create_task(self._cache_response_async(cache_key, response))
            asyncio.create_task(self._update_stats_async("successful_queries"))
            
            logger.info(f"电话模式快速响应完成，耗时: {time.time() - start_time:.2f}s")
            return response
            
        except Exception as e:
            logger.error(f"电话模式快速响应失败: {e}")
            error_response = await self._handle_error(question, str(e), "PHONE_FAST_RESPONSE_ERROR")
            
            return {
                "success": False,
                "question": question,
                "answer": error_response,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "response_time": time.time() - start_time,
                "phone_mode": True,
                "fast_response": True,
            }
    
    async def _simple_intent_recognition(self, question: str) -> Dict[str, Any]:
        """简化的意图识别，用于电话模式快速响应"""
        try:
            # 基于关键词的简单意图识别
            question_lower = question.lower()
            
            # 校园信息相关关键词
            campus_keywords = ["学校", "校园", "教学楼", "图书馆", "食堂", "宿舍", "课程", "专业", "老师", "教授"]
            # 数据查询相关关键词
            data_keywords = ["成绩", "学分", "课表", "选课", "考试", "分数"]
            # 一般问答关键词
            general_keywords = ["什么", "怎么", "如何", "为什么", "哪里", "谁"]
            
            if any(keyword in question_lower for keyword in campus_keywords):
                return {
                    "intent_class": "knowledge_query",
                    "is_school_related": True,
                    "confidence": 0.8,
                    "final_intent": "knowledge_query"
                }
            elif any(keyword in question_lower for keyword in data_keywords):
                return {
                    "intent_class": "data_query",
                    "is_school_related": True,
                    "confidence": 0.8,
                    "final_intent": "data_query"
                }
            else:
                return {
                    "intent_class": "general_answer",
                    "is_school_related": False,
                    "confidence": 0.6,
                    "final_intent": "general_answer"
                }
                
        except Exception as e:
            logger.error(f"简化意图识别失败: {e}")
            return {
                "intent_class": "general_answer",
                "is_school_related": False,
                "confidence": 0.5,
                "final_intent": "general_answer"
            }

    async def _update_stats_async(self, stat_name: str):
        """异步更新统计信息"""
        try:
            if stat_name in self.system_stats:
                self.system_stats[stat_name] += 1
        except Exception as e:
            logger.error(f"更新统计失败: {e}")

    async def _update_conversation_async(self, conversation_id: str, question: str, answer: str):
        """异步更新会话历史"""
        try:
            self._update_qa_conversation(conversation_id, question, answer)
        except Exception as e:
            logger.error(f"异步更新会话失败: {e}")

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        cache_hit_rate = 0.0
        total_cache_requests = self.performance_stats["cache_hits"] + self.performance_stats["cache_misses"]
        if total_cache_requests > 0:
            cache_hit_rate = self.performance_stats["cache_hits"] / total_cache_requests
        
        return {
            "cache_stats": {
                "cache_size": len(self.response_cache),
                "cache_hits": self.performance_stats["cache_hits"],
                "cache_misses": self.performance_stats["cache_misses"],
                "cache_hit_rate": cache_hit_rate,
            },
            "phone_mode_stats": {
                "phone_mode_queries": self.performance_stats.get("phone_mode_queries", 0),
                "fast_response_queries": self.performance_stats.get("fast_response_queries", 0),
            },
            "response_stats": {
                "avg_response_time": self.performance_stats.get("avg_response_time", 0.0),
                "total_response_time": self.performance_stats.get("total_response_time", 0.0),
                "response_count": self.performance_stats.get("response_count", 0),
            },
            "system_stats": self.system_stats,
        }

    async def _query_information_by_intent(
        self, 
        question: str, 
        intent_result: Dict[str, Any], 
        user_id: str, 
        user_role: str
    ) -> Dict[str, Any]:
        """
        步骤2: 根据意图查询相关信息
        根据意图分析结果，调用相应的查询服务获取信息
        """
        try:
            intent_class = intent_result.get("intent_class", "general_answer")
            is_school_related = intent_result.get("is_school_related", False)
            
            # 转换用户角色
            try:
                user_role_enum = UserRole(user_role.lower())
            except ValueError:
                user_role_enum = UserRole.GUEST
            
            query_result = {"type": "none", "data": None, "source": "none"}
            
            # 根据意图类型查询相关信息
            if intent_class == "contact_info":
                # 联系方式查询
                result = await self.data_agent.query_contact_info(question, user_role_enum)
                query_result = {"type": "contact", "data": result, "source": "database"}
                
            elif intent_class == "knowledge_query" or is_school_related:
                # 混合检索查询
                keywords = intent_result.get("keywords_matched", [])
                if not keywords:
                    keywords = [question]  # 如果没有关键词，使用问题本身
                
                # 调用混合检索函数
                result = await hybrid_retrieval(
                    query_text=question,
                    top_k=5,
                    keywords=keywords
                )
                
                # 格式化结果
                formatted_content = self._format_hybrid_results(result)
                
                query_result = {
                    "type": "knowledge", 
                    "data": {
                        "success": True,
                        "content": formatted_content,
                        "source": "hybrid_retrieval",
                        "results_count": len(result)
                    }, 
                    "source": "knowledge_base"
                }
                
            elif intent_class == "data_query":
                # 数据库查询
                result = await self.data_agent.query_data(question, user_id, user_role_enum)
                query_result = {"type": "data", "data": result, "source": "database"}
                
            elif intent_class == "web_search":
                # 网络搜索
                result = await self.web_search_tool.search(question)
                query_result = {"type": "web", "data": result, "source": "web_search"}
                
            else:
                # 通用查询，尝试知识库 - 注意：query_knowledge是同步方法
                try:
                    result = self.knowledge_agent.query_knowledge(question)
                    query_result = {"type": "knowledge", "data": result, "source": "knowledge_base"}
                except Exception:
                    query_result = {"type": "general", "data": None, "source": "none"}
            
            logger.info(f"查询信息完成，类型: {query_result['type']}, 来源: {query_result['source']}")
            return query_result
            
        except Exception as e:
            logger.error(f"信息查询失败: {e}")
            return {"type": "error", "data": None, "source": "error", "error": str(e)}

    async def _generate_answer_with_langchain(
        self, 
        question: str, 
        intent: str, 
        query_result: Any, 
        phone_mode: bool = False,
        phone_conversation_history: List[Dict[str, Any]] = None
    ) -> str:
        """
        步骤3: 使用LangChain调用大模型生成最终回答
        """
        try:
            # 构建上下文对话
            context = ""
            if phone_mode and phone_conversation_history:
                context_parts = []
                for conv in phone_conversation_history[-5:]:  # 只取最近5条对话
                    if conv.get('question'):
                        context_parts.append(f"用户：{conv['question']}")
                    if conv.get('answer'):
                        context_parts.append(f"助手：{conv['answer']}")
                context = "\n".join(context_parts)
                logger.info(f"电话模式：添加了 {len(phone_conversation_history)} 条历史对话作为上下文")
            
            content_parts = [
                    f'上下文对话: {context}',
                    f"当前问题: {question}",
                    f"意图分析: {intent}",
                    f"查询结果: {query_result}",

                ]
                
                
            prompt_template = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.phone_prompt),
                    HumanMessage(content="\n".join(content_parts)),
                ]
            )
            
            # 创建LLM链
            chain = prompt_template | self.llm | StrOutputParser()
            
            # 调用大模型生成回答
            response = await chain.ainvoke({})
            
            return response
            
        except Exception as e:
            logger.error(f"大模型生成回答失败: {e}")
            return f"抱歉，我无法处理您的问题。请稍后再试。错误信息：{str(e)}"


    def _format_intent_info(self, intent_result: Dict[str, Any]) -> str:
        """格式化意图信息"""
        intent_class = intent_result.get("intent_class", "unknown")
        is_school_related = intent_result.get("is_school_related", False)
        confidence = intent_result.get("confidence", 0.0)
        
        return f"意图类型：{intent_class}，学校相关：{is_school_related}，置信度：{confidence:.2f}"

    async def _get_phone_conversation_history(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取用户的电话对话历史上下文
        
        Args:
            user_id: 用户ID
            limit: 获取的历史记录数量限制
            
        Returns:
            电话对话历史列表
        """
        try:
            # 导入数据库相关模块
            from fastapi_app.database import SessionLocal
            from fastapi_app.models import PhoneSession, PhoneConversationHistory
            from sqlalchemy.orm import Session
            
            # 创建数据库会话
            db: Session = SessionLocal()
            
            try:
                # 查找用户当前活跃的电话会话
                active_session = db.query(PhoneSession).filter(
                    PhoneSession.user_id == user_id,
                    PhoneSession.status == 1
                ).first()
                
                if not active_session:
                    logger.info(f"用户 {user_id} 没有活跃的电话会话")
                    return []
                
                # 获取该会话的对话历史
                history = db.query(PhoneConversationHistory).filter(
                    PhoneConversationHistory.session_id == active_session.id
                ).order_by(PhoneConversationHistory.created_at.desc()).limit(limit).all()
                
                # 按时间正序返回，并转换为字典格式
                conversation_history = []
                for record in reversed(history):
                    conversation_history.append({
                        "question": record.question,
                        "answer": record.answer,
                        "timestamp": record.created_at.isoformat() if record.created_at else None
                    })
                
                logger.info(f"获取到用户 {user_id} 的 {len(conversation_history)} 条电话对话历史")
                return conversation_history
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取电话对话历史失败: {e}")
            return []

    def _format_phone_conversation_context(self, conversation_history: List[Dict[str, Any]]) -> str:
        """
        格式化电话对话历史为上下文字符串
        
        Args:
            conversation_history: 电话对话历史列表
            
        Returns:
            格式化的上下文字符串
        """
        if not conversation_history:
            return ""
        
        context_parts = ["=== 电话对话历史上下文 ==="]
        
        for i, record in enumerate(conversation_history, 1):
            context_parts.append(f"第{i}轮对话:")
            context_parts.append(f"用户问题: {record['question']}")
            context_parts.append(f"AI回答: {record['answer']}")
            context_parts.append("---")
        
        context_parts.append("=== 当前问题 ===")
        
        return "\n".join(context_parts)
    
    def _format_postgres_results(self, postgres_results: List[Dict[str, Any]]) -> str:
        """
        格式化PostgreSQL检索结果为回答内容
        """
        if not postgres_results:
            return "抱歉，没有找到相关信息。"
        
        # 按相关性分数排序
        sorted_results = sorted(postgres_results, key=lambda x: x.get('score', 0), reverse=True)
        
        formatted_content = []
        
        # 如果只有一个结果且分数很高，直接返回其内容
        if len(sorted_results) == 1 and sorted_results[0].get('score', 0) > 0.8:
            result = sorted_results[0]
            content = result.get('content', '')
            if result.get('title'):
                formatted_content.append(f"**{result['title']}**\n")
            formatted_content.append(content)
        else:
            # 多个结果时，整合信息
            formatted_content.append("根据相关信息，为您整理如下内容：\n")
            
            for i, result in enumerate(sorted_results[:3], 1):  # 最多显示前3个结果
                title = result.get('title', f'相关信息 {i}')
                content = result.get('content', '')
                score = result.get('score', 0)
                
                # 只显示相关性较高的结果
                if score > 0.3:
                    formatted_content.append(f"**{i}. {title}**")
                    
                    # 如果有高亮信息，优先使用
                    highlights = result.get('highlights', [])
                    if highlights:
                        for highlight in highlights[:2]:  # 最多显示2个高亮片段
                            formatted_content.append(f"• {highlight}")
                    else:
                        # 截取内容的前200个字符
                        truncated_content = content[:200] + "..." if len(content) > 200 else content
                        formatted_content.append(f"• {truncated_content}")
                    
                    formatted_content.append("")  # 添加空行分隔
        
        result_text = "\n".join(formatted_content)
        
        # 添加数据来源说明
        result_text += f"\n\n*以上信息来源于知识库检索，共找到 {len(postgres_results)} 条相关记录。*"
        
        return result_text
    
    def _format_hybrid_results(self, hybrid_results: List[Dict[str, Any]]) -> str:
        """
        格式化混合检索结果为回答内容
        """
        if not hybrid_results:
            return "抱歉，没有找到相关信息。"
        
        # 按置信度分数排序
        sorted_results = sorted(hybrid_results, key=lambda x: x.get('confidence', 0), reverse=True)
        
        formatted_content = []
        
        # 如果只有一个结果且置信度很高，直接返回其内容
        if len(sorted_results) == 1 and sorted_results[0].get('confidence', 0) > 0.8:
            result = sorted_results[0]
            content = result.get('content', '')
            if result.get('title'):
                formatted_content.append(f"**{result['title']}**\n")
            formatted_content.append(content)
        else:
            # 多个结果时，整合信息
            formatted_content.append("根据混合检索结果，为您整理如下内容：\n")
            
            for i, result in enumerate(sorted_results[:3], 1):  # 最多显示前3个结果
                title = result.get('title', f'相关信息 {i}')
                content = result.get('content', '')
                confidence = result.get('confidence', 0)
                source = result.get('source', 'unknown')
                
                # 只显示置信度较高的结果
                if confidence > 0.3:
                    formatted_content.append(f"**{i}. {title}** (来源: {source})")
                    
                    # 如果有高亮信息，优先使用
                    highlights = result.get('highlights', [])
                    if highlights:
                        for highlight in highlights[:2]:  # 最多显示2个高亮片段
                            formatted_content.append(f"• {highlight}")
                    else:
                        # 截取内容的前200个字符
                        truncated_content = content[:200] + "..." if len(content) > 200 else content
                        formatted_content.append(f"• {truncated_content}")
                    
                    formatted_content.append("")  # 添加空行分隔
        
        result_text = "\n".join(formatted_content)
        
        # 添加数据来源说明
        result_text += f"\n\n*以上信息来源于混合检索（密集检索+稀疏检索），共找到 {len(hybrid_results)} 条相关记录。*"
        
        return result_text
