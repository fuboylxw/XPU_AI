"""
学校信息问答Agent
集成MCP、DeepSeek和RAG功能
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from src.config.settings import Settings
from src.llm.deepseek_client import DeepSeekClient
from src.rag.document_manager import DocumentManager
from src.mcp.client import MCPClient
from src.utils.logger import setup_logger
from src.utils.web_search import WebSearchTool
from src.utils.time_tool import TimeQueryTool
from src.utils.calculator_tool import CalculatorTool

# LangChain imports
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema import SystemMessage, HumanMessage

class SchoolInfoAgent:
    """学校信息问答Agent"""
    

    
    TOOL_SYSTEM_PROMPT = (
        "你是西安工程大学新生助手纺芽。你可以使用以下工具来帮助回答问题：\n"
        "1. search_web: 搜索网络信息\n"
        "2. get_time_info: 获取当前时间\n"
        "3. calculate: 进行数学计算\n\n"
        "严格遵循来源优先级：\n"
        "- 始终先利用本地知识库上下文作答；\n"
        "- 当知识库信息不足或需要补充时，再使用网络搜索；\n"
        "- 当知识库与网络搜索信息冲突时，必须以知识库为准，并在回答中说明差异。\n\n"
        "回答要求：\n"
        "- 除非用户明确要求简洁回答，否则请提供详细、全面、丰富的内容\n"
        "- 尽可能多地提供相关信息，包括背景知识、具体细节、实用建议等\n"
        "- 回答要有条理性，使用标题、列表、分段等方式组织内容\n"
        "- 不限制回答长度，优先保证信息的完整性和实用性\n\n"
        "请根据用户问题选择合适的工具，并提供准确、详细、有帮助的回答。"
    )
    
    # Token限制设置
    MAX_TOKENS = 4096  # DeepSeek API的最大token限制
    
    def __init__(self, settings: Settings, doc_manager: DocumentManager = None):
        self.settings = settings
        self.logger = setup_logger(settings)
        
        # 初始化组件
        self.llm_client = DeepSeekClient(settings)
        self.doc_manager = doc_manager or DocumentManager(settings)
        self.mcp_client = MCPClient(settings)
        self.web_search_tool = WebSearchTool(settings)  # 添加网络搜索工具
        self.time_tool = TimeQueryTool(settings)  # 添加时间查询工具
        self.calculator_tool = CalculatorTool(settings)  # 添加计算器工具
        
        # 搜索缓存机制
        self.search_cache = {}
        self.cache_timeout = 300  # 5分钟缓存
        
        # 系统提示词
        self.system_prompt = """
你是西安工程大学智能助手"纺芽"，专门为学生提供全方位的信息服务。

你的核心职责：
1. 专业回答西安工程大学的基本信息（专业设置、课程安排、校园设施、学校政策等）
2. 提供实时时间查询服务（当前时间、日期、星期等）
3. 提供数学计算服务（基本运算、科学计算、三角函数等）
4. 通过网络搜索获取学生关心的各种信息，包括但不限于：
   - 实时信息（天气、新闻等）
   - 学校最新动态和政策
   - 网络上的相关学习资源
   - 生活服务信息
5. 提供准确、实用、友好的信息服务
6. 绝不回答"不知道"或"无法回答"，而是主动搜索和查找相关信息
7. 保持专业和耐心的态度，全力帮助每一位学生

【重要】时间敏感性处理：
- 当用户询问任何与时间相关的问题时，必须首先调用时间工具获取当前准确时间
- 在进行网络搜索时，必须考虑当前时间背景，确保搜索结果的时效性
- 对于"今天"、"现在"、"当前"、"最新"等时间相关词汇，要特别注意时间上下文
- 回答问题时要明确时间基准点，避免信息过时

【重要】搜索结果处理规则：
当你收到工具调用结果（特别是search_web的结果）时，你必须：
1. 仔细阅读和分析所有搜索结果内容
2. 从搜索结果中提取关键信息来回答用户问题
3. 绝对不能忽略搜索结果，也不能让用户"再搜索一下"
4. 必须基于搜索结果给出具体、详细的回答
5. 如果搜索结果包含了用户问题的答案，必须直接使用这些信息
6. 整合多个搜索结果，提供全面的回答

信息获取和使用策略（严格按优先级执行）：
【第一优先级】本地知识库信息：
- 首先检查并使用本地知识库中的权威信息
- 知识库信息是最可靠的官方资料，必须优先采用
- 如果知识库中有相关信息，必须以此为主要依据

【第二优先级】百度AI搜索信息：
- 当知识库信息不足或需要补充时，使用百度AI搜索结果
- 百度搜索结果用于补充、验证或更新知识库信息
- 对于实时信息、时效性问题，必须结合搜索结果
- 搜索结果必须被充分利用，不能被忽略

【信息整合原则】：
- 必须明确区分知识库信息和搜索信息的来源
- 当两个信息源有冲突时，优先采用知识库信息，但要说明差异
- 整合多个信息源时，要保持逻辑一致性
- 明确标注每部分信息的来源，提高透明度

回答原则：
- 永远不说"不知道"、"无法回答"或"这不在我的职责范围内"
- 必须充分利用已获取的知识库信息和搜索结果
- 当有搜索结果时，必须基于搜索结果内容回答，不能要求用户重新搜索
- 回答时要体现信息的优先级和来源
- 使用友好、易懂的语言
- 提供具体、可操作的建议
- 必要时提供相关链接或联系方式
- 对不确定的信息明确标注来源和可靠性
- 主动提供相关的延伸信息

特别注意：
- 时间查询：直接调用时间工具获取当前准确时间、日期、星期等信息
- 数学计算：直接调用计算器工具进行各种数学运算和科学计算
- 天气查询：搜索当地实时天气信息
- 新闻资讯：搜索最新相关新闻
- 学习资源：搜索网络上的学习材料和资源
- 生活服务：搜索校园周边的生活服务信息

回答格式要求：
- 当使用知识库信息时，可以标注"根据学校官方资料"
- 当使用搜索信息时，可以标注"根据网络搜索结果"
- 当整合两种信息时，要清楚说明各部分的来源
"""
    

    

    

    

    
    async def _retrieve_context_and_tools(self, question: str) -> Dict[str, Any]:
        """检索相关上下文并执行工具调用（智能决策本地+网络搜索+工具调用）"""
        try:
            print(f"🔍 开始检索问题: {question}")
            
            tool_results = {}
            
            # 首先检查是否为时间查询
            time_keywords = ['时间', '几点', '现在', '当前', '日期', '今天', '几号', '星期', '周几', '礼拜']
            if any(keyword in question for keyword in time_keywords):
                print("⏰ 检测到时间查询，调用时间工具")
                time_result = self.time_tool.parse_time_query(question)
                if time_result.get('success'):
                    tool_results['time'] = {
                        'type': 'time_query',
                        'content': f"⏰ 时间信息：\n\n{time_result.get('formatted', time_result.get('message', str(time_result)))}",
                        'raw_result': time_result
                    }
            
            # 检查是否为计算查询
            calc_keywords = ['计算', '算', '等于', '+', '-', '*', '/', '(', ')', '^', 'sin', 'cos', 'tan', 'log', 'sqrt']
            if any(keyword in question for keyword in calc_keywords) or self.calculator_tool._is_valid_expression(question):
                print("🧮 检测到计算查询，调用计算器工具")
                calc_result = self.calculator_tool.parse_calculation_query(question)
                if calc_result.get('success'):
                    tool_results['calculation'] = {
                        'type': 'calculation',
                        'content': f"🧮 计算结果：\n\n{calc_result.get('expression', '')} = {calc_result.get('formatted_result', calc_result.get('result', ''))}",
                        'raw_result': calc_result
                    }
            
            # 使用RAG检索本地文档
            search_results = await self.doc_manager.search_documents(question)
            print(f"📚 本地搜索结果数量: {len(search_results)}")
            
            kb_context = ""
            if search_results:
                kb_context = "📚 本地知识库信息：\n\n"
                for i, result in enumerate(search_results[:3], 1):
                    kb_context += f"{i}. {result['content']}\n"
                    kb_context += f"   📄 来源: {result['source']}\n\n"
                
                avg_score = sum(result.get('score', 0) for result in search_results) / len(search_results)
                print(f"📊 本地搜索平均相关性: {avg_score:.3f}")
            
            # 进行网络搜索以获取最新信息
            web_context = ""
            if self.settings.web_search_enabled:
                print(f"🌐 开始网络搜索: {question}")
                web_results = await self._search_web(question)
                print(f"🌐 网络搜索结果数量: {len(web_results)}")
                
                if web_results:
                    web_context = "🌐 网络搜索信息：\n\n"
                    for i, result in enumerate(web_results, 1):
                        web_context += f"{i}. {result.get('snippet', result.get('content', '无内容'))}\n"
                        web_context += f"   📰 标题: {result.get('title', '无标题')}\n"
                        web_context += f"   🔗 来源: {result.get('source', '未知来源')} - {result.get('url', '无链接')}\n\n"
                    print("✅ 网络搜索结果已添加到上下文")
                else:
                    print("❌ 网络搜索未返回结果")
            else:
                print("❌ 网络搜索功能已禁用")
            
            return {
                'tool_results': tool_results,
                'kb_context': kb_context,
                'web_context': web_context,
                'kb_results': search_results,
                'web_results': web_results if self.settings.web_search_enabled else []
            }
            
        except Exception as e:
            self.logger.error(f"检索上下文失败: {e}")
            print(f"❌ 检索过程出错: {e}")
            return {
                'tool_results': {},
                'kb_context': "⚠️ 检索信息时出现错误，请稍后重试或联系技术支持。",
                'web_context': "",
                'kb_results': [],
                'web_results': []
            }
    
    async def _search_web(self, query: str) -> List[Dict[str, Any]]:
        """执行智能网络搜索（带缓存机制）"""
        import time
        from datetime import datetime
        
        # 检查缓存
        cache_key = query.lower().strip()
        current_time = time.time()
        
        if cache_key in self.search_cache:
            cached_result, timestamp = self.search_cache[cache_key]
            if current_time - timestamp < self.cache_timeout:
                print(f"📋 使用缓存的搜索结果: {query}")
                self.logger.info(f"使用缓存的搜索结果: {query}")
                return cached_result
        
        try:
            # 获取当前时间信息
            current_datetime = datetime.now()
            current_date = current_datetime.strftime("%Y年%m月%d日")
            current_year = current_datetime.year
            
            # 智能构建搜索查询
            # 对于时间、天气等通用查询，直接搜索原始问题
            general_keywords = ['时间', '几点', '天气', '温度', '新闻', '股价', '汇率', '疫情', '今天', '现在', '当前']
            time_related_keywords = ['最新', '近期', '今年', '2024', '2025', '新', '现在', '目前', '当前']
            
            # 检查是否需要添加时间信息
            needs_time_context = any(keyword in query for keyword in time_related_keywords + general_keywords)
            
            if any(keyword in query for keyword in general_keywords):
                # 通用查询，添加当前时间信息以获取最新结果
                enhanced_query = f"{query} {current_date}"
                print(f"🔍 通用查询，添加时间信息: {enhanced_query}")
            else:
                # 学校相关查询
                if needs_time_context:
                    # 如果查询包含时间相关关键词，添加当前年份和日期
                    enhanced_query = f"西安工程大学 {query} {current_year}年 最新"
                    print(f"🔍 学校时间相关查询: {enhanced_query}")
                else:
                    enhanced_query = f"西安工程大学 {query}"
                    print(f"🔍 学校相关查询: {enhanced_query}")
            
            # 只使用百度AI搜索API
            print("🌐 调用百度AI搜索...")
            try:
                results = await self.web_search_tool.search_baidu_ai(
                    enhanced_query, 
                    max_results=self.settings.web_search_max_results
                )
                if not results:
                    print("🌐 百度AI搜索无结果")
                    results = []
                # 暂时注释传统搜索回退
                # if not results:
                #     print("🌐 百度AI搜索无结果，回退到普通搜索...")
                #     results = await self.web_search_tool.search_with_fallback(
                #         enhanced_query, 
                #         max_results=self.settings.web_search_max_results
                #     )
            except Exception as e:
                print(f"🌐 百度AI搜索失败: {e}")
                results = []
                # 暂时注释传统搜索回退
                # print(f"🌐 百度AI搜索失败: {e}，回退到普通搜索...")
                # results = await self.web_search_tool.search_with_fallback(
                #     enhanced_query, 
                #     max_results=self.settings.web_search_max_results
                # )
            
            print(f"📊 原始搜索结果: {len(results)} 个")
            for i, result in enumerate(results):
                print(f"  {i+1}. {result.get('title', '无标题')[:50]}...")
            
            # 过滤和排序结果
            filtered_results = []
            for result in results:
                # 优先选择官方网站和权威来源
                if any(domain in result.get('url', '') for domain in 
                      ['xpu.edu.cn', 'edu.cn', 'gov.cn']):
                    result['priority'] = 1
                    print(f"⭐ 官方来源: {result.get('url', '')}")
                else:
                    result['priority'] = 2
                filtered_results.append(result)
            
            # 按优先级排序
            filtered_results.sort(key=lambda x: x.get('priority', 2))
            
            final_results = filtered_results[:self.settings.web_search_max_results]
            
            # 缓存结果
            self.search_cache[cache_key] = (final_results, current_time)
            
            print(f"✅ 网络搜索完成，返回 {len(final_results)} 个结果")
            
            self.logger.info(f"网络搜索完成，找到 {len(final_results)} 个结果")
            return final_results
            
        except Exception as e:
            self.logger.error(f"网络搜索失败: {e}")
            print(f"❌ 网络搜索失败: {e}")
            return []
    
    async def add_document(self, file_content, filename: str, category: str = "其他") -> str:
        """添加文档"""
        try:
            doc_id = await self.doc_manager.add_document(file_content, filename, category)
            return f"成功添加文档: {filename}"
        except Exception as e:
            self.logger.error(f"添加文档失败: {e}")
            return f"添加文档失败: {str(e)}"
    
    async def get_document_summary(self) -> str:
        """获取文档摘要"""
        return await self.doc_manager.get_documents_summary()
    

    
    async def close(self):
        """关闭Agent"""
        await self.llm_client.close()
        await self.mcp_client.disconnect()
    
    def _get_search_tool_schema(self) -> Dict[str, Any]:
        """获取网络搜索工具的schema定义"""
        return {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "当本地知识库信息不足时，搜索网络获取最新信息。适用于时效性强的问题、最新政策、当前活动等。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索查询词，应该包含关键信息和'西安工程大学'"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "最大搜索结果数量，默认5",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    

    
    async def answer_question_with_tools_stream(self, question: str, context: Optional[str] = None, messages: Optional[List[Dict[str, str]]] = None):
        """统一的智能对话接口，支持工具调用、知识库查询、联网搜索、流式输出、多轮对话
        
        参数:
            question: 用户问题
            context: 可选的上下文信息，如果不提供则自动检索
            messages: 可选的历史消息列表，用于多轮对话
            
        返回:
            异步生成器，流式输出回答内容
        """
        
        try:
            # 第一步：根据问题判断是否需要调用工具，并进行RAG查询和网络搜索
            retrieval_data = await self._retrieve_context_and_tools(question)
            
            # 第二步：处理工具调用结果并显示给用户
            tool_context = ""
            for tool_type, tool_data in retrieval_data['tool_results'].items():
                if tool_type == 'time':
                    yield "🕒 正在查询时间信息...\n\n"
                    yield f"{tool_data['content']}\n\n"
                    tool_context += f"{tool_data['content']}\n\n"
                elif tool_type == 'calculation':
                    yield "🧮 正在进行计算...\n\n"
                    yield f"{tool_data['content']}\n\n"
                    tool_context += f"{tool_data['content']}\n\n"
            
            # 第三步：显示搜索进度
            if retrieval_data['kb_context'] or retrieval_data['web_context']:
                if retrieval_data['kb_context']:
                    yield f"📚 已从知识库找到 {len(retrieval_data['kb_results'])} 条相关信息\n"
                if retrieval_data['web_context']:
                    yield f"🌐 已从网络搜索找到 {len(retrieval_data['web_results'])} 条最新信息\n"
                yield "✅ 信息整理完毕，正在生成回答...\n\n"
            
            # 第四步：构建完整上下文（按优先级：工具结果 > 知识库 > 网络搜索）
            final_context = ""
            
            # 添加工具调用结果（最高优先级）
            if tool_context:
                final_context += f"🔧 工具调用结果：\n{tool_context}\n"
            
            # 添加知识库信息（第二优先级，作为基准）
            if retrieval_data['kb_context']:
                final_context += retrieval_data['kb_context']
                if retrieval_data['web_context']:
                    final_context += "\n" + "="*50 + "\n\n"
            
            # 添加网络搜索信息（第三优先级，补充最新信息）
            if retrieval_data['web_context']:
                final_context += retrieval_data['web_context']
            
            # 如果没有找到任何信息
            if not final_context:
                final_context = """❌ 暂时无法找到相关信息。
建议您：
1. 📞 联系学校相关部门咨询
2. 📧 发送邮件到学校官方邮箱
3. 🌐 访问学校官方网站查看最新信息
4. 📱 关注学校官方微信公众号
5. 📋 上传相关文档以丰富知识库"""
            
            # 第五步：处理历史会话信息（使用时间权重）
            weighted_messages = []
            if messages and len(messages) > 0:
                import time
                current_time = time.time()
                
                # 为历史消息添加时间权重（越接近当前时间权重越大）
                for i, msg in enumerate(messages):
                    # 假设消息按时间顺序排列，越靠后的消息时间权重越大
                    time_weight = (i + 1) / len(messages)  # 权重从 1/n 到 1
                    content_weight = min(len(msg.get('content', '')), 500) / 500  # 内容丰富度权重
                    final_weight = (time_weight * 0.7) + (content_weight * 0.3)
                    
                    weighted_msg = msg.copy()
                    weighted_msg['weight'] = final_weight
                    weighted_messages.append(weighted_msg)
                
                # 按权重排序，但保持所有对话内容
                weighted_messages.sort(key=lambda x: x.get('weight', 0), reverse=True)
            
            # 第六步：构建最终对话消息
            conversation_messages = [
                {"role": "system", "content": self.TOOL_SYSTEM_PROMPT}
            ]
            
            # 添加加权的历史消息（保持所有内容但调整顺序）
            if weighted_messages:
                # 重要的历史消息优先添加
                for msg in weighted_messages[:10]:  # 限制历史消息数量
                    if msg.get('role') and msg.get('content'):
                        conversation_messages.append({
                            "role": msg['role'],
                            "content": msg['content']
                        })
            
            # 添加当前问题和完整上下文
            conversation_messages.append({
                "role": "user",
                "content": f"问题：{question}\n\n可用上下文：{final_context}"
            })
            
            # 第七步：添加信息来源说明
            has_tool_results = bool(tool_context)
            has_knowledge_base = bool(retrieval_data['kb_context'])
            has_web_results = bool(retrieval_data['web_context'])
            
            if has_tool_results:
                yield "ℹ️ *本回答包含工具调用结果*\n\n"
            elif has_knowledge_base and has_web_results:
                yield "ℹ️ 本回答优先采用学校官方知识库信息，网络搜索仅作补充；若有冲突以知识库为准。\n\n"
            elif has_knowledge_base:
                yield "ℹ️ *本回答基于学校官方知识库资料*\n\n"
            elif has_web_results:
                yield "ℹ️ *本回答基于网络搜索结果*\n\n"
            else:
                yield "ℹ️ *本回答基于AI知识*\n\n"
            
            # 第八步：流式输出AI回答
            response_generated = False
            try:
                async for chunk in self.llm_client.chat_completion_stream(
                    messages=conversation_messages,
                    max_tokens=self.MAX_TOKENS
                ):
                    if chunk and isinstance(chunk, str) and chunk.strip():
                        yield chunk
                        response_generated = True
                
                # 如果没有生成任何回答，提供备用回答
                if not response_generated:
                    if has_tool_results or has_knowledge_base or has_web_results:
                        yield "基于以上信息，我已经为您找到了相关内容。如需更详细的解答，请重新描述您的问题。\n\n"
                    else:
                        yield "抱歉，暂时无法获取到相关信息，请稍后再试或换个问题。\n\n"
                
            except Exception as stream_error:
                self.logger.error(f"流式输出失败: {stream_error}")
                # 如果流式输出失败，使用非流式方式生成回答
                try:
                    response = await self.llm_client.chat_completion(
                        messages=conversation_messages,
                        max_tokens=self.MAX_TOKENS
                    )
                    if response and "choices" in response:
                        content = response["choices"][0]["message"]["content"]
                        if content and isinstance(content, str) and content.strip():
                            # 模拟流式输出
                            for i in range(0, len(content), 20):
                                chunk = content[i:i+20]
                                if chunk.strip():
                                    yield chunk
                                await asyncio.sleep(0.02)
                        else:
                            yield "基于以上信息，我已经为您找到了相关内容。\n\n"
                    else:
                        yield "基于以上信息，我已经为您找到了相关内容。\n\n"
                except Exception as fallback_error:
                    self.logger.error(f"回退方案也失败: {fallback_error}")
                    yield "✅ 我已经为您整理了相关信息，请查看上面的内容。如需更详细的解答，请重新描述您的问题。\n\n"
                    
        except Exception as e:
            self.logger.error(f"智能问答失败: {e}")
            # 提供错误信息给用户
            yield "❌ 抱歉，处理您的问题时遇到了技术问题。\n\n"
            yield "💡 请尝试重新提问，或者换一种表达方式。\n\n"
            yield "如果问题持续存在，请联系技术支持。\n"