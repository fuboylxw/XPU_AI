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
from dataclasses import dataclass, field
import uuid

# 在模块导入时应用nest_asyncio
nest_asyncio.apply()

from config.settings import settings
from src.Chatbot.tools.MCP.web_search import WebSearchTool
from src.Chatbot.tools.llm_client import LLMClient

# 导入其他智能体
from src.Chatbot.agents.security_audit_agent import SecurityAuditAgent
from src.Chatbot.agents.intent_recognition_agent import IntentRecognitionAgent
from src.Chatbot.agents.knowledge_query_agent import hybrid_retrieval
from src.Chatbot.agents.data_query_agent import DataQueryAgent, UserRole

from src.Chatbot.utils.logger import setup_logger
from src.Chatbot.utils.memory_storage import memory_storage
from src.Chatbot.core.container import get_container
from src.Chatbot.agents.task_execution_agent import TaskExecutionAgent
from src.Chatbot.services.question_rewrite import QuestionRewriteService
from src.Chatbot.services.security_audit import SecurityAuditService as SecurityAuditSvc
from src.Chatbot.services.intent_recognition import IntentRecognitionService
from src.Chatbot.services.answer_generation import AnswerGenerationService
from src.Chatbot.services.conversation_context import ConversationContextService
from src.Chatbot.services.response_cache import ResponseCacheService
from fastapi_app.database import SessionLocal
from fastapi_app.models import WorkTask, WorkSession, WorkSubTask
from src.Chatbot.tools.cline import ClineOrchestrator
from src.Chatbot.tools.task_planner import TaskPlanner
from src.Chatbot.core.prompts import (
    REWRITE_PROMPT, INTENT_PROMPT, SCHOOL_ANSWER_PROMPT, WEB_ANSWER_PROMPT,
    NO_WEB_ANSWER_PROMPT, DATA_QUERY_PROMPT, PHONE_PROMPT, ERROR_HANDLING_PROMPT,
)

logger = setup_logger("chat_agent")


class ChatbotAgent:
    """Chatbot对话智能体 - 支持问题改写、意图分析、统一问答和流式响应"""

    def __init__(self):
        # 初始化日志记录器
        self.logger = setup_logger("chat_agent")

        # 从容器获取预加载组件
        container = get_container()
        if container.is_initialized:
            self.logger.info("使用容器预加载的组件")
            self.llm = container.llm
            self.llm_stream = container.llm_stream
            self.web_search_tool = container.web_search_tool
            self.security_agent = container.security_agent
            self.intent_agent = container.intent_agent
            self.data_agent = container.data_agent
            self.website_knowledge_agent = None
            self.task_planner = TaskPlanner()

        else:
            # 回退到传统初始化方式
            self.logger.warning("容器未就绪，使用传统初始化方式")

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
                callbacks=[streaming_handler],
            )
            # 初始化工具
            self.web_search_tool = WebSearchTool(settings)

            # 初始化统一问答子智能体
            self.security_agent = SecurityAuditAgent()
            self.intent_agent = IntentRecognitionAgent()
            self.data_agent = DataQueryAgent()
            self.cline_orchestrator = ClineOrchestrator()
            self.task_planner = TaskPlanner()

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

        # 初始化提取的服务
        self.question_rewrite_svc = QuestionRewriteService(self.llm)
        self.security_audit_svc = SecurityAuditSvc(self.security_agent, self.llm, self.response_cache)
        self.intent_recognition_svc = IntentRecognitionService(self.intent_agent, self.llm, self.response_cache)
        self.conversation_context_svc = ConversationContextService()
        self.conversation_context_svc.qa_conversations = self.qa_conversations
        self.cache_svc = ResponseCacheService(cache_ttl=self.cache_ttl, max_cache_size=self.max_cache_size)
        self.cache_svc.response_cache = self.response_cache
        self.answer_generation_svc = AnswerGenerationService(
            self.llm, self.llm_stream,
            {
                "school_answer_prompt": self.school_answer_prompt,
                "web_answer_prompt": self.web_answer_prompt,
                "no_web_answer_prompt": self.no_web_answer_prompt,
                "data_query_prompt": getattr(self, "data_query_prompt", ""),
                "phone_prompt": getattr(self, "phone_prompt", ""),
            }
        )

        # 启动缓存预热任务
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._warmup_cache())
        except RuntimeError:
            self.logger.warning("事件循环未运行，跳过缓存预热启动")
        if not hasattr(self, 'cline_orchestrator') or self.cline_orchestrator is None:
            self.cline_orchestrator = ClineOrchestrator()
        self.task_queue = asyncio.Queue()
        self.task_history: List[Dict[str, Any]] = []
        self.task_exec_agent = TaskExecutionAgent.get_instance()
        
    async def _warmup_cache(self):
        """缓存预热，提前加载常用数据"""
        try:
            logger.info("开始缓存预热...")
            
            # 预热常用意图识别模型
            test_question = "你好"
            _ = await self.intent_agent.recognize_text_intent(test_question)
            logger.info("意图识别模型预热完成")
            
            # 预热安全审核模型
            _ = await self.security_agent.audit_content(test_question, "")
            logger.info("安全审核模型预热完成")
            
            logger.info("缓存预热完成")
            
        except Exception as e:
            logger.error(f"缓存预热失败: {e}")

    def _initialize_retrieval_systems(self):
        """预初始化检索系统，避免在查询时重复初始化"""
        try:
            logger.info("开始预初始化检索系统...")

            # 使用容器中已预热的检索引擎，避免旧 GlobalInitializer 依赖
            container = get_container()
            if container.is_initialized:
                self.dense_engine = container.dense_engine
                self.sparse_engine = container.sparse_engine
                logger.info("使用容器预加载的检索引擎")
            else:
                self.dense_engine = None
                self.sparse_engine = None
                logger.info("容器未初始化，检索引擎将在首次查询时按需初始化")
            
            logger.info("检索系统预初始化完成")
        except Exception as e:
            logger.warning(f"检索系统预初始化失败: {e}")
            # 不抛出异常，允许系统继续运行，在查询时再初始化

    def _initialize_prompts(self):
        """初始化提示词模板 - 从 core.prompts 常量加载"""
        self.rewrite_prompt = REWRITE_PROMPT
        self.intent_prompt = INTENT_PROMPT
        self.school_answer_prompt = SCHOOL_ANSWER_PROMPT
        self.web_answer_prompt = WEB_ANSWER_PROMPT
        self.no_web_answer_prompt = NO_WEB_ANSWER_PROMPT
        self.data_query_prompt = DATA_QUERY_PROMPT
        self.phone_prompt = PHONE_PROMPT
        self.error_handling_prompt = ERROR_HANDLING_PROMPT



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
            phone_conversation_history = []
            if phone_mode:
                phone_conversation_history = await self._get_phone_conversation_history(user_id)
                logger.info(f"电话模式：获取到 {len(phone_conversation_history)} 条历史对话")

            conversation_context = await self._get_conversation_context_async(conversation_id)
            rewritten_question = self._rewrite_question_sync(question, conversation_context)

            uploaded_context = ""
            try:
                relevant_uploads = memory_storage.search_relevant_content(
                    conversation_id, rewritten_question, max_results=3
                )
                if relevant_uploads:
                    upload_texts = []
                    for upload in relevant_uploads:
                        info = f"[{upload.content_type.upper()}]"
                        if upload.original_filename:
                            info += f" {upload.original_filename}:"
                        info += f" {upload.content}"
                        upload_texts.append(info)
                    uploaded_context = "\n".join(upload_texts)
            except Exception:
                uploaded_context = ""

            hybrid_results = await hybrid_retrieval(
                query_text=rewritten_question,
                top_k=5,
                keywords=None
            )
            formatted_content = self._format_hybrid_results(hybrid_results)
            query_result = formatted_content if not uploaded_context else uploaded_context + "\n" + formatted_content

            intent_result = await self._perform_intent_recognition_redis_cached(
                rewritten_question, image_data
            )
            intent = intent_result.get("analysis", "无分析信息")
            logger.info(f"查询到的结果: {query_result}")

            final_answer = await self._generate_answer_with_langchain(
                rewritten_question, intent, query_result, phone_mode, phone_conversation_history, conversation_context
            )
            logger.info(f"生成的回答: {final_answer}")

            # 构建响应
            response = {
                "success": True,
                "question": rewritten_question,
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
        use_web_search: bool = False,
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
            use_web_search: 是否在知识库检索基础上启用联网搜索补充

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

            # 并发执行安全审核、上下文获取
            security_task = asyncio.create_task(
                self._perform_security_audit_strict(question, conversation_id)
            )
            context_task = asyncio.create_task(
                self._get_conversation_context_async(conversation_id)
            )
            
            # 等待安全审核和上下文获取完成
            security_result, conversation_context = await asyncio.gather(
                security_task, context_task
            )
            
            logger.info(f"安全审核通过")
            
            if not security_result.get("is_safe", False):
                self.system_stats["blocked_queries"] += 1
                block_message = await self._handle_security_block(
                    question, security_result
                )
                yield block_message["answer"]
                return
            
            # 改写问题
            rewritten_question = self._rewrite_question_sync(
                question, conversation_context
            )
            logger.info(f"改写后的问题: {rewritten_question}")


            kb_task = asyncio.create_task(
                hybrid_retrieval(query_text=rewritten_question, top_k=5, keywords=[rewritten_question])
            )
            web_results = []
            if use_web_search:
                web_task = asyncio.create_task(
                    self.web_search_tool.search_baidu_ai(rewritten_question, max_results=5)
                )
                kb_results, web_results = await asyncio.gather(kb_task, web_task)
            else:
                kb_results = await kb_task

            kb_text = ""
            try:
                kb_text = self._format_hybrid_results(kb_results)
            except Exception:
                kb_text = json.dumps(kb_results, ensure_ascii=False)

            web_summary = ""
            if web_results:
                parts = []
                for i, r in enumerate(web_results[:5]):
                    title = r.get("title", "")
                    url = r.get("url", "")
                    snippet = r.get("snippet", "")
                    parts.append(f"{i+1}. {title}\n{url}\n{snippet}")
                web_summary = "\n".join(parts)

            processing_result = {
                "type": "knowledge_query",
                "result": {
                    "answer": kb_text,
                    "web_search": web_results
                }
            }

            # 检索上传的文本信息
            uploaded_context = ""
            try:
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
            intent_type = processing_result.get("type", "general_answer")
            # 统一使用知识库详答模板，结合上传内容与可选网络搜索
            prompt_template = None
            try:
                kb_result = processing_result.get("result", {}) if isinstance(processing_result, dict) else {}
                kb_answer = kb_result.get("answer", "")
                kb_sources = kb_result.get("sources", [])
            except Exception:
                kb_answer, kb_sources = "", []

            content_parts = [
                f"改写后的用户问题：{rewritten_question}",
                f"知识库检索结果: {kb_answer}",
            ]
            if uploaded_context:
                content_parts.insert(1, f"用户上传的相关内容：\n{uploaded_context}")
            if use_web_search and web_summary:
                content_parts.append(f"网络搜索结果：\n{web_summary}")
            if kb_sources:
                try:
                    titles = [src.get("title", "") for src in kb_sources if isinstance(src, dict)]
                    titles = [t for t in titles if t]
                    if titles:
                        content_parts.append(f"参考来源：{'; '.join(titles)}")
                except Exception:
                    pass

            content_parts.append(
                "请依据上述资料生成详细、结构化的回答，包含：关键结论、依据与引用、分步解释；若信息不确定或缺失请明确说明，并避免臆断。"
            )

            prompt_template = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=self.school_answer_prompt),
                    HumanMessage(content="\n".join(content_parts)),
                ]
            )
            logger.info("使用统一知识库详答提示词模板（可含网络搜索）")
            
            if prompt_template is None:
                logger.warning(f"未识别的意图类型: {intent_type}，使用默认提示词模板")
                content_parts = [
                    f"改写后的用户问题：{rewritten_question}",
                ]
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
            
            # 实现真正的流式输出
            async for chunk in self.llm_stream.astream(prompt_template.messages):
                if hasattr(chunk, "content") and chunk.content:
                    token = chunk.content
                    if token:
                        yield token
                        final_answer += token
                        self._update_answer_in_db(conversation_record_id, final_answer)
                        await asyncio.sleep(0.001)

            # 7. 最终更新会话历史（内存中的记录）
            self._update_qa_conversation_memory(conversation_id, question, final_answer)

            # 记录上传内容的使用情况
            if uploaded_context:
                logger.info(f"会话 {conversation_id} 使用了上传内容进行回答，内容将保留供后续问题使用")

            # 8. 更新统计
            self.system_stats["successful_queries"] += 1

        except Exception as e:
            logger.error(f"流式问答处理失败: {e}")
            error_response = await self._handle_error(question, str(e), "STREAM_ERROR")
            yield error_response

    async def answer_question_tools(
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

            # 并发执行安全审核、上下文获取和意图识别
            # 创建异步任务
            security_task = asyncio.create_task(
                self._perform_security_audit_strict(question, conversation_id)
            )
            context_task = asyncio.create_task(
                self._get_conversation_context_async(conversation_id)
            )
            
            # 等待安全审核和上下文获取完成
            security_result, conversation_context = await asyncio.gather(
                security_task, context_task
            )
            
            logger.info(f"安全审核通过")
            
            if not security_result.get("is_safe", False):
                self.system_stats["blocked_queries"] += 1
                block_message = await self._handle_security_block(
                    question, security_result
                )
                yield block_message["answer"]
                return
            
            # 改写问题
            rewritten_question = self._rewrite_question_sync(
                question, conversation_context
            )
            logger.info(f"改写后的问题: {rewritten_question}")
            
            # 执行意图识别（使用Redis缓存版本）
            intent_result = await self._perform_intent_recognition_redis_cached(
                rewritten_question, image_data
            )
            logger.info(f"意图识别结果: {intent_result}")
            intent_analysis = intent_result.get("intent_analysis", {})
            _plan_res = await self.task_planner.plan(rewritten_question)
            planned_tasks = _plan_res.get("results") if isinstance(_plan_res, dict) else []
            db = SessionLocal()
            logger.info(f"计划任务: {planned_tasks}")
            persisted_tasks: List[Dict[str, Any]] = []
            main_task_id: Optional[int] = None
            try:
                ws = db.query(WorkSession).filter(WorkSession.session_id == conversation_id).first()
                if ws is None:
                    ws = WorkSession(session_id=conversation_id, user_id=user_id, title=rewritten_question, status="pending")
                    db.add(ws)
                    db.flush()
                
                # Create main task
                main_task = WorkTask(
                    session_id=conversation_id,
                    task_name=rewritten_question,
                    status="waiting",
                    result="",
                )
                db.add(main_task)
                db.flush()
                main_task_id = int(main_task.task_id)

                for i, t in enumerate(planned_tasks):
                    sub_task_name = str(t.get("query") or t.get("title") or "子任务")
                    sub_task = WorkSubTask(
                        session_id=conversation_id,
                        task_id=main_task.task_id,
                        sub_task_name=sub_task_name,
                        order=i,
                        status="waiting",
                        result="",
                    )
                    db.add(sub_task)
                    db.flush()
                    persisted_tasks.append({
                        "id": sub_task.task_sub_id,
                        "conversation_id": conversation_id,
                        "title": sub_task_name,
                        "query": str(t.get("query") or sub_task_name),
                        "intent_analysis": intent_analysis,
                        "is_subtask": True
                    })

                # 规划器无子任务时，至少执行主任务，避免结果流无限等待
                if not persisted_tasks and main_task_id is not None:
                    persisted_tasks.append({
                        "id": main_task_id,
                        "conversation_id": conversation_id,
                        "title": rewritten_question,
                        "query": rewritten_question,
                        "intent_analysis": intent_analysis,
                        "is_subtask": False,
                    })
                db.commit()
            except Exception as e:
                logger.error(f"保存任务到数据库失败: {e}")
                db.rollback()
            finally:
                db.close()

            # 数据库不可用时，降级为内存任务，仍可执行 ReAct
            if not persisted_tasks:
                fallback_task_id = -int(time.time() * 1000)
                persisted_tasks.append({
                    "id": fallback_task_id,
                    "conversation_id": conversation_id,
                    "title": rewritten_question,
                    "query": rewritten_question,
                    "intent_analysis": intent_analysis,
                    "is_subtask": False,
                })

            logger.info(f"计划任务: {planned_tasks}")
            await self.task_exec_agent.add_tasks(persisted_tasks)
            tasks_preview = "\n".join([f"[{i+1}] {x['title']}" for i, x in enumerate(persisted_tasks)])
            if tasks_preview:
                yield tasks_preview
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

            final_answer = ""
            conversation_record_id = self._save_question_to_db(conversation_id, question)
            logger.info(f"问题已保存到数据库，记录ID: {conversation_record_id}")
            expected_results = max(1, len(persisted_tasks))
            async for r in self.task_exec_agent.stream_results(conversation_id, limit=expected_results):
                seg = r.get("result") or r.get("error") or ""
                if seg:
                    yield seg
                    final_answer += seg
                    self._update_answer_in_db(conversation_record_id, final_answer)
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
        context = self._get_qa_conversation_context(conversation_id)
        return await self.security_audit_svc.perform_audit(question, context)

    async def _perform_security_audit_strict(
        self, question: str, conversation_id: str
    ) -> Dict[str, Any]:
        """严格安全审核 - 委托给服务"""
        context_list = self._get_qa_conversation_context(conversation_id)
        return await self.security_audit_svc.perform_audit_strict(question, context_list)

    async def _perform_intent_recognition(
        self, question: str, image_data: Optional[Union[str, bytes, Image.Image]]
    ) -> Dict[str, Any]:
        """执行意图识别 - 委托给服务"""
        return await self.intent_recognition_svc.recognize(question, image_data)

    async def _handle_security_block(
        self, question: str, security_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理安全阻止 - 委托给服务"""
        return await SecurityAuditSvc.handle_security_block(question, security_result)

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
        """获取对话上下文 - 委托给服务"""
        return self.conversation_context_svc.get_qa_context(conversation_id)

    def _update_qa_conversation(self, conversation_id: str, question: str, answer: str):
        """更新对话历史并存储到数据库 - 委托给服务"""
        self.conversation_context_svc.update_qa_conversation(conversation_id, question, answer)

    def _save_question_to_db(self, conversation_id: str, question: str) -> Optional[int]:
        """保存问题到数据库 - 委托给服务"""
        return self.conversation_context_svc.save_question_to_db(conversation_id, question)

    def _update_answer_in_db(self, record_id: Optional[int], answer: str):
        """更新答案到数据库 - 委托给服务"""
        self.conversation_context_svc.update_answer_in_db(record_id, answer)

    def _update_qa_conversation_memory(self, conversation_id: str, question: str, answer: str):
        """更新内存中的对话历史 - 委托给服务"""
        self.conversation_context_svc.update_qa_conversation_memory(conversation_id, question, answer)

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
        """获取对话上下文 - 委托给服务"""
        return self.conversation_context_svc.get_conversation_context(conversation_id)

    async def _get_conversation_context_async(self, conversation_id: str) -> str:
        """异步获取对话上下文 - 委托给服务"""
        return await self.conversation_context_svc.get_conversation_context_async(conversation_id)



    def get_knowledge_for_Intent_class_sync(self, Intent_class: str, query: str) -> str:
        """根据意图类别获取知识库信息 - 同步版本

        Args:
            Intent_class: 意图类别
            query: 用户查询

        Returns:
            知识库检索结果
        """
        try:
            if not Intent_class or not isinstance(Intent_class, str):
                logger.warning(f"无效的意图类别: {Intent_class}")
                return "无法识别的意图类别"

            Intent_class_dir = Intent_class.lower().replace(" ", "_")
            knowledge_dir = os.path.join(self.document_manager.knowledge_dir, Intent_class_dir)
            if not os.path.exists(knowledge_dir) or not os.path.isdir(knowledge_dir):
                logger.info(f"意图类别 {Intent_class_dir} 的知识库目录不存在，跳过检索")
                return ""

            search_results = self.KnowledgeBase.search(query, Intent_class=Intent_class_dir)
            if not search_results:
                logger.info(f"未找到意图类别 {Intent_class_dir} 的知识库信息")
                return ""

            knowledge_text = "\n\n".join([result["content"] for result in search_results])
            logger.info(f"找到意图类别 {Intent_class_dir} 的知识库信息: {len(search_results)} 条")
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
        """问题改写 - 委托给服务"""
        return self.question_rewrite_svc.rewrite_sync(question, chat_history)

    async def _rewrite_question(
        self, question: str, conversation_context: str = ""
    ) -> str:
        """异步问题改写 - 委托给服务"""
        return await self.question_rewrite_svc.rewrite(question, conversation_context)

    def _analyze_intent_sync(self, question: str) -> str:
        """意图分析 - 委托给服务"""
        return self.intent_recognition_svc.analyze_sync(question)





    async def _generate_final_answer(
        self,
        search_results: str,
        Intent_description: str,
        rewritten_question: str,
        is_school_related: bool,
    ) -> AsyncGenerator[str, None]:
        """生成最终回答（流式） - 委托给服务"""
        async for chunk in self.answer_generation_svc.generate_final_answer(
            search_results, Intent_description, rewritten_question, is_school_related
        ):
            yield chunk

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
        """生成缓存键 - 委托给服务"""
        return self.cache_svc.generate_cache_key(question, user_role, phone_mode)

    async def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存响应 - 委托给服务"""
        return await self.cache_svc.get_cached_response(cache_key)

    async def _cache_response_async(self, cache_key: str, response: Dict[str, Any]):
        """异步缓存响应 - 委托给服务"""
        await self.cache_svc.cache_response(cache_key, response)

    async def _cleanup_cache(self):
        """清理过期缓存 - 委托给服务"""
        await self.cache_svc.cleanup()

 

    async def _perform_security_audit_cached(
        self, question: str, conversation_id: str
    ) -> Dict[str, Any]:
        """带缓存的安全审核 - 委托给服务"""
        context = self._get_qa_conversation_context(conversation_id)
        return await self.security_audit_svc.perform_audit_cached(question, context)

    async def _perform_security_audit_redis_cached(
        self, question: str, conversation_id: str
    ) -> Dict[str, Any]:
        """Redis缓存安全审核 - 委托给服务"""
        context = self._get_qa_conversation_context(conversation_id)
        return await self.security_audit_svc.perform_audit_redis_cached(question, context)

    async def _perform_intent_recognition_cached(
        self, question: str, image_data: Optional[Union[str, bytes, Image.Image]]
    ) -> Dict[str, Any]:
        """带缓存的意图识别 - 委托给服务"""
        return await self.intent_recognition_svc.recognize_cached(question, image_data)

    async def _perform_intent_recognition_redis_cached(
        self, question: str, image_data: Optional[Union[str, bytes, Image.Image]]
    ) -> Dict[str, Any]:
        """Redis缓存意图识别 - 委托给服务"""
        return await self.intent_recognition_svc.recognize_redis_cached(question, image_data)

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
        """优化的最终回答生成 - 委托给服务"""
        return await self.answer_generation_svc.synthesize_optimized(
            question, intent_result, processing_result, security_result,
            phone_mode, self.phone_mode_config.get("max_response_length", 200)
        )

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
        """简化意图识别 - 委托给服务"""
        return await self.intent_recognition_svc.simple_recognition(question)

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

    

    async def _generate_answer_with_langchain(
        self,
        question: str,
        intent: str,
        query_result: Any,
        phone_mode: bool = False,
        phone_conversation_history: List[Dict[str, Any]] = None,
        conversation_context: str = ""
    ) -> str:
        """LangChain生成回答 - 委托给服务"""
        return await self.answer_generation_svc.generate_with_langchain(
            question, intent, query_result, phone_mode,
            phone_conversation_history, conversation_context
        )

    def _format_intent_info(self, intent_result: Dict[str, Any]) -> str:
        """格式化意图信息 - 委托给服务"""
        return self.intent_recognition_svc.format_intent_info(intent_result)

    async def _get_phone_conversation_history(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取电话对话历史 - 委托给服务"""
        return await self.conversation_context_svc.get_phone_conversation_history(user_id, limit)

    def _format_phone_conversation_context(self, conversation_history: List[Dict[str, Any]]) -> str:
        """格式化电话对话上下文 - 委托给服务"""
        return self.conversation_context_svc.format_phone_conversation_context(conversation_history)

    def _format_hybrid_results(self, hybrid_results: List[Dict[str, Any]]) -> str:
        """格式化混合检索结果 - 委托给服务"""
        return self.answer_generation_svc.format_hybrid_results(hybrid_results)
