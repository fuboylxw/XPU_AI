from typing import List, Dict, Optional, Any, AsyncGenerator, Generator
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

# 在模块导入时应用nest_asyncio
nest_asyncio.apply()

from config.settings import settings
from src.chatbi.tools.query_tools import QueryTool
from src.chatbi.tools.web_search import WebSearchTool
from src.chatbi.tools.document_manager import DocumentManager
from src.chatbi.tools.llm_client import LLMClient
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from src.chatbi.utils.logger import setup_logger

logger = setup_logger("chat_agent")

class ChatBIAgent:
    """ChatBI对话智能体 - 支持问题改写、意图分析和流式响应"""
    
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


        # 会话存储
        self.conversations: Dict[str, List[BaseMessage]] = {}
        
        # 定义提示词模板
        self._initialize_prompts()
    

    def _initialize_prompts(self):
        """初始化各种提示词模板(系统提示词)"""

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

    
    def _get_current_time(self, _) -> str:
        """获取当前时间"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # def _get_conversation_context(self, conversation_id: str) -> str:
    #     """获取对话上下文"""
    #     if conversation_id not in self.conversations:
    #         return ""
        
    #     context = []
    #     for message in self.conversations[conversation_id][-4:]:  # 最近4条消息
    #         if isinstance(message, HumanMessage):
    #             context.append(f"用户: {message.content}")
    #         elif isinstance(message, AIMessage):
    #             context.append(f"助手: {message.content}")
        
    #     return "\n".join(context)


    def _get_conversation_context(self, conversation_id: str) -> list[BaseMessage]:
        """获取对话上下文（返回消息对象列表）"""
        if conversation_id not in self.conversations:
            # 如果会话ID不存在，创建一个空列表
            self.conversations[conversation_id] = []
            return []
        
        # 只取最近4条消息作为上下文
        context_messages = self.conversations[conversation_id][-4:]
        logger.info(f"获取对话上下文: {len(context_messages)} 条消息")
        return context_messages

    
    async def search_web(self, query: str, max_results: int = 3) -> str:
        """执行网络搜索
        
        Args:
            query: 搜索查询
            max_results: 最大结果数量
            
        Returns:
            搜索结果文本
        """
        try:
            # 使用百度AI搜索API
            async with self.web_search_tool as search_tool:
                search_results = await search_tool.search_baidu_ai(query, max_results=max_results)
                
                # 如果百度AI搜索失败，尝试普通百度搜索
                if not search_results:
                    self.logger.info("百度AI搜索未返回结果，尝试普通百度搜索")
                    search_results = await search_tool.search_baidu(query, max_results=max_results)
            
            if not search_results:
                self.logger.info(f"网络搜索未找到结果: {query}")
                return ""
            
            # 格式化搜索结果
            formatted_results = []
            for i, result in enumerate(search_results):
                title = result.get('title', '无标题')
                snippet = result.get('snippet', '无摘要')
                url = result.get('url', '无链接')
                formatted_results.append(f"[{i+1}] {title}\n摘要: {snippet}\n来源: {url}")
            
            web_search_text = "\n\n".join(formatted_results)
            self.logger.info(f"网络搜索找到 {len(search_results)} 条结果")
            
            return web_search_text
            
        except Exception as e:
            logger.error(f"网络搜索出错: {str(e)}")
            return ""

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
    
    async def search_web(self, query: str, max_results: int = 3) -> str:
        """执行网络搜索
        
        Args:
            query: 搜索查询
            max_results: 最大结果数量
            
        Returns:
            搜索结果文本
        """
        try:
            # 使用百度AI搜索API
            async with self.web_search_tool as search_tool:
                search_results = await search_tool.search_baidu_ai(query, max_results=max_results)
                
                # 如果百度AI搜索失败，尝试普通百度搜索
                if not search_results:
                    logger.info("百度AI搜索未返回结果，尝试普通百度搜索")
                    search_results = await search_tool.search_baidu(query, max_results=max_results)
            
            if not search_results:
                logger.info(f"网络搜索未找到结果: {query}")
                return ""
            
            # 格式化搜索结果
            formatted_results = []
            for i, result in enumerate(search_results):
                title = result.get('title', '无标题')
                snippet = result.get('snippet', '无摘要')
                url = result.get('url', '无链接')
                formatted_results.append(f"[{i+1}] {title}\n摘要: {snippet}\n来源: {url}")
            
            web_search_text = "\n\n".join(formatted_results)
            logger.info(f"网络搜索找到 {len(search_results)} 条结果")
            
            return web_search_text
            
        except Exception as e:
            logger.error(f"网络搜索出错: {str(e)}")
            return ""
            
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
    
    def clear_conversation(self, conversation_id: str = "default"):
        """清除指定会话的历史记录"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id] = []
            logger.info(f"清除了会话 {conversation_id} 的历史记录")
    
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