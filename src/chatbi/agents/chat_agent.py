from typing import List, Dict, Optional, Any, AsyncGenerator, Generator, Union
from langchain_community.chat_models import ChatOpenAI
import os
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain.chains import LLMChain
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
from src.chatbi.tools.query_tools import QueryTool
from src.chatbi.tools.web_search import WebSearchTool
from src.chatbi.tools.document_manager import DocumentManager
from src.chatbi.tools.llm_client import LLMClient
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from src.chatbi.agents.security_audit_agent import SecurityAuditAgent
from src.chatbi.agents.intent_recognition_agent import IntentRecognitionAgent
from src.chatbi.agents.knowledge_query_agent import KnowledgeQueryAgent
from src.chatbi.agents.data_query_agent import DataQueryAgent, UserRole
from src.chatbi.agents.website_knowledge_agent import WebsiteKnowledgeAgent

from src.chatbi.utils.logger import setup_logger

logger = setup_logger("chat_agent")

class ChatBIAgent:
    """ChatBI对话智能体 - 支持问题改写、意图分析、统一问答和流式响应"""
    
    def __init__(self):
        # 初始化LLM客户端
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_MODEL_BASE_URL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS
        )
        streaming_handler = StreamingStdOutCallbackHandler()
        self.llm_stream = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_MODEL_BASE_URL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            streaming=True,
            callbacks=[streaming_handler]  # 绑定回调处理器（核心参数）
        )
        # 初始化工具
        self.query_tool = QueryTool()
        self.web_search_tool = WebSearchTool(settings)
        self.document_manager = DocumentManager()
        
        # 初始化记忆
        self.memory = None

        # 初始化统一问答子智能体
        self.security_agent = SecurityAuditAgent()
        self.intent_agent = IntentRecognitionAgent()
        self.knowledge_agent = KnowledgeQueryAgent()
        self.data_agent = DataQueryAgent()
        
        # 初始化网站知识库智能体（用于学校信息查询）
        self.website_knowledge_agent = WebsiteKnowledgeAgent(
            base_url="https://www.xpu.edu.cn/",
            output_dir=str(settings.project_root / "knowledge_base" / "xpu"),
            max_pages=200,
            delay=0.5
        )

        # 会话存储
        self.conversations: Dict[str, List[BaseMessage]] = {}
        self.qa_conversations: Dict[str, List[Dict[str, Any]]] = {}
        
        # 系统状态
        self.system_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "blocked_queries": 0,
            "start_time": datetime.now()
        }
        
        # 定义提示词模板
        self._initialize_prompts()
    

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
            """
            
        # 提示词3: 最终回答生成（网络搜索）
        self.web_answer_prompt = """
                你是一个西安工程大学回答助手小丫，你必须基于提供的网络搜索结果回答问题。  

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
            """
            
        # 提示词4: 最终回答生成（数据查询）
        self.data_query_prompt = """
                你是一个西安工程大学回答助手小丫，你必须基于提供的数据查询结果回答问题。  

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
            """
        
        # 提示词5: 错误处理
        self.error_handling_prompt = ChatPromptTemplate.from_template("""
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
            """)

    async def answer_question(self, 
                            question: str,
                            user_id: str = "guest",
                            user_role: str = "guest",
                            session_token: Optional[str] = None,
                            image_data: Optional[Union[str, bytes, Image.Image]] = None,
                            conversation_id: str = "default") -> Dict[str, Any]:
        """
        统一问答接口
        
        Args:
            question: 用户问题
            user_id: 用户ID
            user_role: 用户角色 (guest/student/teacher/admin)
            session_token: 会话令牌
            image_data: 图像数据（可选）
            conversation_id: 会话ID
            
        Returns:
            问答结果
        """
        try:
            logger.info(f"收到问答请求 - 用户: {user_id}, 角色: {user_role}, 问题: {question[:50]}...")
            
            # 更新系统统计
            self.system_stats["total_queries"] += 1
            
            # 转换用户角色
            try:
                user_role_enum = UserRole(user_role.lower())
            except ValueError:
                user_role_enum = UserRole.GUEST
            
            # 1. 安全审核
            logger.info("执行安全审核...")
            security_result = await self._perform_security_audit(question, conversation_id)
            
            if not security_result.get("is_safe", False):
                self.system_stats["blocked_queries"] += 1
                return await self._handle_security_block(question, security_result)
            
            # 2. 意图识别
            logger.info("执行意图识别...")
            intent_result = await self._perform_intent_recognition(question, image_data)
            
            # 3. 根据意图路由到相应的处理模块
            logger.info(f"根据意图路由: {intent_result.get('final_intent', intent_result.get('intent_class'))}")
            processing_result = await self._route_by_intent(
                question, intent_result, user_id, user_role_enum, session_token
            )
            
            # 4. 综合生成最终回答
            logger.info("生成最终回答...")
            final_answer = await self._synthesize_final_answer(
                question, intent_result, processing_result, security_result
            )
            
            # 5. 更新会话历史
            self._update_qa_conversation(conversation_id, question, final_answer)
            
            # 6. 更新统计
            self.system_stats["successful_queries"] += 1
            
            return {
                "success": True,
                "question": question,
                "answer": final_answer,
                "metadata": {
                    "intent_result": intent_result,
                    "processing_result": processing_result,
                    "security_result": security_result,
                    "user_id": user_id,
                    "user_role": user_role,
                    "conversation_id": conversation_id,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"问答处理失败: {e}")
            error_response = await self._handle_error(question, str(e), "SYSTEM_ERROR")
            
            return {
                "success": False,
                "question": question,
                "answer": error_response,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def answer_question_stream(self, 
                                  question: str,
                                  user_id: str = "guest",
                                  user_role: str = "guest",
                                  session_token: Optional[str] = None,
                                  image_data: Optional[Union[str, bytes, Image.Image]] = None,
                                  conversation_id: str = "default") -> AsyncGenerator[str, None]:
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
            security_result = await self._perform_security_audit(question, conversation_id)
            
            if not security_result.get("is_safe", False):
                self.system_stats["blocked_queries"] += 1
                block_message = await self._handle_security_block(question, security_result)
                yield block_message["answer"]
                return
            
            # 2. 获取对话上下文并改写问题
            conversation_context = self._get_conversation_context(conversation_id)
            rewritten_question = await self._rewrite_question_sync(question, conversation_context)
            logger.info(f"改写后的问题: {rewritten_question}")
            
            # 3. 使用改写后的问题进行意图识别
            intent_result = await self.intent_agent.recognize_text_intent(rewritten_question)
            
            # 4. 根据意图路由到相应的处理模块
            processing_result = await self._route_by_intent(
                rewritten_question, intent_result, user_id, user_role_enum, session_token
            )
            
            # 5. 准备流式输出的提示词
            # 根据意图类型选择对应的提示词模板
            intent_type = processing_result.get("type", "general_answer")
            
            if intent_type == "knowledge_query":
                prompt_template = ChatPromptTemplate.from_messages([
                    SystemMessage(content=self.school_answer_prompt),
                    HumanMessage(content=f"""
                    改写后的用户问题：{rewritten_question}
                    意图分析: {json.dumps(intent_result, ensure_ascii=False)}                
                    知识库检索结果: {processing_result.get("result", {}).get("answer", "")}
                    """)
                ])
                logger.info("使用知识库查询提示词模板")
            elif intent_type == "data_query":
                prompt_template = ChatPromptTemplate.from_messages([
                    SystemMessage(content=self.data_query_prompt),
                    HumanMessage(content=f"""
                    改写后的用户问题：{rewritten_question}
                    意图分析: {json.dumps(intent_result, ensure_ascii=False)}                
                    数据查询结果: {str(processing_result.get("result", {}))}
                    """)
                ])
                logger.info("使用数据查询提示词模板")
            elif intent_type == "general_answer":
                # 对于通用回答，使用网络搜索提示词模板
                prompt_template = ChatPromptTemplate.from_messages([
                    SystemMessage(content=self.web_answer_prompt),
                    HumanMessage(content=f"""
                    改写后的用户问题：{rewritten_question}
                    意图分析: {json.dumps(intent_result, ensure_ascii=False)}                
                    网络搜索结果: {processing_result.get("result", {}).get("answer", "")}
                    """)
                ])
                logger.info("使用网络搜索提示词模板")
            
            # 6. 使用流式LLM生成回答
            final_answer = ""
            
            # 使用chain链式进行流式输出
            async for chunk in self.llm_stream.astream(prompt_template.messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
                    final_answer += chunk.content

            # 7. 更新会话历史
            self._update_qa_conversation(conversation_id, question, final_answer)
            
            # 8. 更新统计
            self.system_stats["successful_queries"] += 1
            
        except Exception as e:
            logger.error(f"流式问答处理失败: {e}")
            error_response = await self._handle_error(question, str(e), "STREAM_ERROR")
            yield error_response
    
    async def _generate_streaming_response(self, messages: List[BaseMessage]) -> AsyncGenerator[str, None]:
        """生成流式响应"""
        response = await self.llm_stream.agenerate([messages])
        for chunk in response.generations[0][0].text:
            yield chunk
            await asyncio.sleep(0.01)  # 控制输出速度
    
    async def _perform_security_audit(self, question: str, conversation_id: str) -> Dict[str, Any]:
        """执行安全审核"""
        try:
            # 获取对话上下文
            context = self._get_qa_conversation_context(conversation_id)
            
            # 执行安全审核
            audit_result = await self.security_agent.audit_content(question, context)
            
            return audit_result
            
        except Exception as e:
            logger.error(f"安全审核失败: {e}")
            return {
                "is_safe": False,
                "risk_level": "high",
                "error": str(e)
            }
    
    async def _perform_intent_recognition(self, question: str, 
                                        image_data: Optional[Union[str, bytes, Image.Image]]) -> Dict[str, Any]:
        """执行意图识别"""
        try:
            if image_data:
                # 多模态意图识别
                intent_result = await self.intent_agent.recognize_multimodal_intent(question, image_data)
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
                "error": str(e)
            }
    
    async def _route_by_intent(self, question: str, intent_result: Dict[str, Any],
                             user_id: str, user_role: UserRole, session_token: Optional[str]) -> Dict[str, Any]:
        """根据意图路由到相应的处理模块"""
        intent_class = intent_result.get("intent_class", "Other")
        is_school_related = intent_result.get("is_school_related", False)
        
        try:
            if not is_school_related and intent_class is "general_answer":
                # 非校园相关问题，使用网络搜索
                search_result = await self.web_search_tool.search(question)
                return {
                    "type": "general_answer",
                    "result": search_result
                }
            
            # 校园相关问题，根据具体意图分类处理
            elif is_school_related and intent_class is "knowledge_query":
                # 知识库查询
                knowledge_result = await self.knowledge_agent.query_knowledge(question)
                return {
                    "type": "knowledge_query",
                    "result": knowledge_result
                }
            
            elif is_school_related and intent_class is "data_query":
                # 数据查询
                if user_role == UserRole.GUEST:
                    return {
                        "type": "data_query",
                        "result": {
                            "success": False,
                            "error": "数据查询需要登录，游客用户无法访问数据功能",
                            "suggestion": "请联系相关部门或登录后重试"
                        }
                    }
                
                data_result = await self.data_agent.query_data(
                    question, user_id, user_role, session_token
                )
                return {
                    "type": "data_query", 
                    "result": data_result
                }
            
            else:
                # 默认使用知识库查询
                knowledge_result = await self.knowledge_agent.query_knowledge(question)
                return {
                    "type": "knowledge_query",
                    "result": knowledge_result
                }
                
        except Exception as e:
            logger.error(f"意图路由处理失败: {e}")
            return {
                "type": "error",
                "result": {
                    "success": False,
                    "error": str(e)
                }
            }
    


    async def _handle_security_block(self, question: str, security_result: Dict[str, Any]) -> Dict[str, Any]:
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
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_error(self, question: str, error_info: str, error_type: str) -> str:
        """处理错误情况"""
        try:
            chain = self.error_handling_prompt | self.llm | StrOutputParser()
            error_response = await chain.ainvoke({
                "question": question,
                "error_info": error_info,
                "error_type": error_type
            })
            
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
        """更新对话历史"""
        if conversation_id not in self.qa_conversations:
            self.qa_conversations[conversation_id] = []
        
        self.qa_conversations[conversation_id].append({
            "question": question,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        })
        
        # 保持对话历史在合理长度
        if len(self.qa_conversations[conversation_id]) > 50:
            self.qa_conversations[conversation_id] = self.qa_conversations[conversation_id][-25:]
    
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
                "data_agent": "active"
            },
            "statistics": {
                "security_audit": self.security_agent.get_audit_statistics(),
                "intent_recognition": self.intent_agent.get_recognition_statistics(),
                "knowledge_query": self.knowledge_agent.get_query_statistics(),
                "data_query": self.data_agent.get_query_statistics()
            }
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
        """获取对话上下文"""
        conversation = self.qa_conversations.get(conversation_id, [])
        if not conversation:
            return ""
            
        # 构建上下文字符串，包含最近5轮对话
        context_parts = []
        for i, item in enumerate(conversation[-5:]):
            context_parts.append(f"用户: {item['question']}")
            context_parts.append(f"助手: {item['answer']}")
            
        return "\n".join(context_parts)
    

    
    def _get_current_time(self, _) -> str:
        """获取当前时间"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    


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
                
            # 使用同步方式检索
            results = self.document_manager.search_documents(query)
            
            if not results:
                logger.info(f"未找到意图类别 {Intent_class} 的知识库信息")
                return ""
            
            # 格式化结果
            formatted_results = []
            for doc in results:
                formatted_results.append(f"文档: {doc.metadata.get('source', '未知')}\n内容: {doc.page_content}")
                
            knowledge_text = "\n\n".join(formatted_results)
            logger.info(f"找到意图类别 {Intent_class} 的知识库信息: {len(results)} 条")
            
            return knowledge_text
        except Exception as e:
            logger.error(f"知识库检索失败: {e}")
            return f"知识库检索出错: {str(e)}"
            
    async def get_knowledge_for_Intent_class(self, Intent_class: str, query: str) -> str:
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
        knowledge_dir = os.path.join(self.document_manager.knowledge_dir, Intent_class_dir)
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
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=self.rewrite_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessage(content=f"用户问题: {question}")
            ])
            chain = LLMChain(
                llm=self.llm,
                prompt=prompt
            )
            response = chain.invoke({"chat_history": chat_history, "question": question})
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
            
    async def _rewrite_question(self, question: str, conversation_context: str = "") -> str:
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
            rewritten_question = self._rewrite_question_sync(question, conversation_context)
            return rewritten_question
        except Exception as e:
            logger.error(f"问题改写失败: {e}")
            # 出错时返回原问题
            return question

    def _analyze_intent_sync(self, question: str) -> str:
        """意图分析 - 同步版本"""

        try:
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(self.intent_prompt),
                HumanMessage(content=f"用户问题: {question}")
            ])
            chain = LLMChain(
                llm=self.llm,
                prompt=prompt,
                output_parser=JsonOutputParser()
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
                return {"is_school_related": False, "Intent_class": "其他", "Intent_description": "意图分析失败"}
        except Exception as e:
            logger.error(f"意图分析失败: {e}")
            return {
                "is_school_related": False,
                "Intent_class": "其他",
                "Intent_description": "意图分析失败"
            }
    
    async def _analyze_intent(self, rewritten_question: str) -> Dict[str, Any]:
        """分析意图"""
        try:
            intent_chain = self.intent_prompt | self.llm
            result = await intent_chain.ainvoke({
                "rewritten_question": rewritten_question
            })
            
            # 解析意图分析结果
            content = result.content.strip()
            lines = content.split('\n')
            
            intent_info = {
                "is_school_related": False,
                "category": "其他",
                "explanation": ""
            }
            
            for line in lines:
                line = line.strip()
                if "学校相关:" in line:
                    intent_info["is_school_related"] = "是" in line
                elif "信息类别:" in line:
                    intent_info["category"] = line.split("信息类别:")[1].strip()
                elif "简要说明:" in line:
                    intent_info["explanation"] = line.split("简要说明:")[1].strip()
            
            return intent_info
            
        except Exception as e:
            logger.error(f"意图分析失败: {e}")
            return {
                "is_school_related": False,
                "Intent_class": "其他",
                "Intent_description": "意图分析失败"
            }
    


    
    def _search_web_sync(self, question: str) -> str:
        """网络搜索 - 同步版本"""
        try:
            # 使用网络搜索工具
            results = self.web_search_tool.search(question)
            
            if not results or results.strip() in ["未找到相关信息", "", "未找到匹配的信息"]:
                # 如果网络搜索没有找到，使用LLM直接回答
                fallback_prompt = f"请简要回答关于'{question}'的问题，如果无法回答，请说'抱歉，我没有找到相关信息'。"
                response = self.llm_client.invoke(fallback_prompt)
                return response.content.strip()
            
            return results
            
        except Exception as e:
            logger.error(f"网络搜索失败: {e}")
            # 如果网络搜索失败，使用LLM直接回答
            try:
                fallback_prompt = f"请简要回答关于'{question}'的问题："
                response = self.llm.invoke(fallback_prompt)
                return response.content.strip()
            except Exception as fallback_error:
                logger.error(f"LLM回退失败: {fallback_error}")
                return "抱歉，网络搜索时出现问题"
    

    
    
    
    async def _generate_final_answer(self, search_results: str, Intent_description: str, 
                                   rewritten_question: str, is_school_related: bool) -> AsyncGenerator[str, None]:
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
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            chain = LLMChain(
                llm=self.llm_stream,
                prompt=prompt
            )

            # 传入所有变量：历史对话、网络搜索信息、知识库信息、当前问题
            logger.info(f"开始生成回答，搜索结果长度: {len(search_results)}")
            
            # 实现与大模型同步的真正流式输出，优化延迟时间
            previous_text = ""
            
            async for chunk in chain.astream({
                "rewritten_question": rewritten_question,
                "Intent_description": Intent_description,
                "search_results": search_results
            }):
                if chunk["event"] == "on_llm_new_token":
                    current_text = chunk["data"]
                    # 只输出新增的部分
                    new_text = current_text[len(previous_text):]
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
    
    async def chat_stream(self, message: str, conversation_id: str = "default", 
                         model_name: str = None, temperature: float = None) -> AsyncGenerator[str, None]:
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
            logger.info(f"解析后的意图: {intent['Intent_class'] if 'Intent_class' in intent else '未知'}")
            
            # 4. 根据意图选择检索方式
            is_school_related = intent.get("is_school_related", False)
            intent_class = intent.get("Intent_class", None)
            Intent_description = intent.get("Intent_description", None)
            
            if is_school_related:
                search_results = self.get_knowledge_for_Intent_class_sync(intent_class, rewritten_question)
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
                search_results, Intent_description, rewritten_question, is_school_related
            )
            
            # 用于存储完整回复的变量
            full_response = ""
            
            # 流式输出并同时收集完整回复
            async for chunk in response_generator:
                # 确保chunk是字符串
                if isinstance(chunk, str):
                    chunk_str = chunk
                elif hasattr(chunk, 'content'):
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
            self.conversations[conversation_id].append({"role": "user", "content": message})
            self.conversations[conversation_id].append({"role": "assistant", "content": full_response})
            
            # 限制历史记录长度
            if len(self.conversations[conversation_id]) > settings.MAX_CONVERSATION_HISTORY * 2:
                self.conversations[conversation_id] = self.conversations[conversation_id][-settings.MAX_CONVERSATION_HISTORY * 2:]
            
        except Exception as e:
            logger.error(f"流式对话处理失败: {e}")
            yield f"抱歉，处理您的请求时出现错误: {str(e)}"
    
    def chat(self, message: str, conversation_id: str = "default", 
             model_name: str = None, temperature: float = None) -> str:
        """
        处理用户消息 - 使用新的完整流程
        
        Args:
            message: 用户输入消息
            conversation_id: 会话ID
            model_name: 模型名称
            temperature: 温度参数
            
        Returns:
            AI回复消息
        """
        try:
            logger.info(f"收到用户消息: {message}")
            
            # # 更新模型配置（如果提供）
            # if model_name or temperature is not None:
            #     self._update_model_config(model_name, temperature)
            
            # 1. 获取对话上下文
            context = self._get_conversation_context(conversation_id)
            logger.info(f"获取对话上下文: {context[:100]}...")
            
            # 2. 问题改写 - 直接调用同步方法
            rewritten_question = self._rewrite_question_sync(message, context)
            logger.info(f"改写后的问题: {rewritten_question}")
            
            # 3. 意图分析 - 直接调用同步方法
            intent = self._analyze_intent_sync(rewritten_question)
            logger.info(f"意图分析结果: {intent}")
            
            # 4. 根据意图选择检索方式 - 直接调用同步方法
            # 确保intent是字典类型
            is_school_related = False
            if isinstance(intent, dict):
                is_school_related = intent.get("is_school_related", False)
            
            if is_school_related:
                # 使用文档管理器检索知识库
                search_results = self.document_manager.search_documents(rewritten_question)
                logger.info("使用知识库检索")
            else:
                search_results = self._search_web_sync(rewritten_question)
                logger.info("使用网络搜索")
            
            # 确保search_results是字符串
            if not isinstance(search_results, str):
                search_results = str(search_results)
                
            logger.info(f"检索结果: {search_results[:200] if len(search_results) > 200 else search_results}...")
            
            # 5. 生成最终回答 - 直接调用同步方法
            final_response = self._generate_final_answer(
                search_results, intent, rewritten_question, is_school_related
            )
            
            # 确保final_response是字符串
            if not isinstance(final_response, str):
                if hasattr(final_response, 'content'):
                    final_response = final_response.content
                else:
                    final_response = str(final_response)
            
            # 更新会话历史
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []
            
            self.conversations[conversation_id].extend([
                HumanMessage(content=message),
                AIMessage(content=final_response)
            ])
            
            # 限制历史记录长度
            if len(self.conversations[conversation_id]) > settings.MAX_CONVERSATION_HISTORY * 2:
                self.conversations[conversation_id] = self.conversations[conversation_id][-settings.MAX_CONVERSATION_HISTORY * 2:]
            
            # 保存对话历史到日志
            logger.info(f"保存对话历史，会话ID: {conversation_id}, 历史长度: {len(self.conversations[conversation_id])}")
            
            logger.info(f"AI回复: {final_response[:100] if len(final_response) > 100 else final_response}...")
            return final_response
            
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            return f"抱歉，处理您的请求时出现错误: {str(e)}"
    
    def _update_model_config(self, model_name: str = None, temperature: float = None):
        """更新模型配置"""
        if model_name:
            self.llm_client = LLMClient(
                api_key=settings.OPENAI_API_KEY,
                model=model_name,
                base_url=settings.OPENAI_MODEL_BASE_URL,
                temperature=temperature if temperature is not None else settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS
            )
        elif temperature is not None:
            self.llm_client = LLMClient(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
                base_url=settings.OPENAI_MODEL_BASE_URL,
                temperature=temperature,
                max_tokens=settings.OPENAI_MAX_TOKENS
            )
    

    
    def get_conversation_history(self, conversation_id: str = "default") -> List[Dict[str, str]]:
        """获取会话历史"""
        if conversation_id not in self.conversations:
            return []
        
        history = []
        for message in self.conversations[conversation_id]:
            if isinstance(message, HumanMessage):
                history.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                history.append({"role": "assistant", "content": message.content})
        
        return history