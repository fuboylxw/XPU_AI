"""
意图识别智能体模块
实现图像识别、意图分类、多模态理解等功能
"""

import base64
import io
import json
import re
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from PIL import Image
import requests
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage

from config.settings import settings
from src.Chatbot.utils.logger import setup_logger

logger = setup_logger("intent_recognition_agent")


class IntentRecognitionAgent:
    """意图识别智能体"""

    def __init__(self):
        """初始化意图识别智能体"""
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_MODEL_BASE_URL,
            temperature=0.3,
        )

        # 初始化意图分类体系
        self._initialize_intent_categories()

        # 初始化提示词模板
        self._initialize_prompts()

        # 识别历史记录
        self.recognition_history = []

    def _initialize_intent_categories(self):
        """初始化意图分类体系"""
        self.intent_categories = {
            # 三大类意图分类
            "general_answer": {
                "name": "通用知识问答",
                "description": "非学校相关的通用知识问答",
                "subcategories": {
                    "GeneralQA": {
                        "name": "通用问答",
                        "keywords": ["什么", "怎么", "为什么", "如何"],
                        "description": "通用知识问答",
                    },
                    "Technology": {
                        "name": "技术咨询",
                        "keywords": ["编程", "技术", "软件", "开发", "算法"],
                        "description": "技术相关咨询",
                    },
                    "Life": {
                        "name": "生活咨询",
                        "keywords": ["生活", "健康", "娱乐", "旅游"],
                        "description": "生活相关咨询",
                    },
                    "Other": {"name": "其他", "keywords": [], "description": "其他类型问题"},
                },
            },
            "knowledge_query": {
                "name": "校园业务查询",
                "description": "学校相关的校园业务查询",
                "subcategories": {
                    "Policy": {
                        "name": "校规校纪",
                        "keywords": ["校规", "校纪", "管理办法", "规章制度", "文件", "政策"],
                        "description": "校规校纪、管理办法、制度文件相关",
                    },
                    "MajorInfo": {
                        "name": "专业信息",
                        "keywords": ["学院", "专业", "介绍", "课程设置", "培养方案"],
                        "description": "学院专业介绍、课程信息",
                    },
                    "StudentStatus": {
                        "name": "学籍管理",
                        "keywords": ["学籍", "请假", "转专业", "休学", "处分", "毕业"],
                        "description": "学籍管理、请假、转专业等事务",
                    },
                    "CampusLife": {
                        "name": "校园生活",
                        "keywords": ["宿舍", "饮食", "校园卡", "网络", "活动", "社团"],
                        "description": "宿舍、饮食、校园卡、网络等校园生活",
                    },
                    "Admission": {
                        "name": "招生入学",
                        "keywords": ["招生", "报名", "入学", "录取", "分数线"],
                        "description": "招生、报名、入学相关信息",
                    },
                    "Employment": {
                        "name": "实习就业",
                        "keywords": ["实习", "就业", "招聘", "求职", "职业规划"],
                        "description": "实习、就业、招聘相关信息",
                    },
                    "OtherSchool": {
                        "name": "其他校园",
                        "keywords": ["校园", "学校", "教务", "学工"],
                        "description": "其他学校相关事务",
                    },
                },
            },
            "data_query": {
                "name": "校园数据查询",
                "description": "学校相关的数据查询",
                "subcategories": {
                    "Scholarship": {
                        "name": "奖学金助学金",
                        "keywords": ["奖学金", "助学金", "评优", "评奖", "资助", "补助"],
                        "description": "奖学金、助学金、评优评奖相关查询",
                    },
                    "Course": {
                        "name": "课程考试",
                        "keywords": ["课程", "选课", "考试", "成绩", "学分", "课表"],
                        "description": "课程安排、选课、考试成绩相关",
                    },
                },
            },
        }

    def _initialize_prompts(self):
        """初始化提示词模板"""
        self.text_intent_prompt = ChatPromptTemplate.from_template(
            """
        你是一个专业的意图识别助手。请根据以下步骤分析用户问题并判断其意图，同时决定是否需要联网搜索。

        用户问题：{question}

        请按照以下步骤进行分析：

        1. **判断问题是否与西安工程大学相关**  
        - 如果问题与学校相关，继续执行步骤 2。
        - 如果问题不涉及学校，直接归类为通用知识问答（general_answer）。

        2. **判断问题类型：校园业务查询 vs 校园数据查询**  
        - 校园业务查询（knowledge_query）：涉及学校相关的具体业务或事务（如学籍管理、课程信息等）。
        - 校园数据查询（data_query）：涉及学校的具体数据（如课程安排、选课、成绩等）。

        3. **判断是否需要联网搜索**  
        - **不需要联网搜索**：
            - 学校相关信息（knowledge_query、data_query）— 这些信息可以通过内部知识库、数据库或预加载数据进行回答。
            - 项目自身介绍类问题（如“你是谁？”“你能做什么？”等）— 系统自带的基本信息，无需联网。
            - 简单问候语（如“你好”，“谢谢”等）— 无需联网处理。
        - **需要联网搜索**：
            - 通用知识问答（general_answer）— 这类问题通常涉及普适的知识，且不特定于学校，通常需要从外部知识库、搜索引擎获取。
            - 实时信息查询（如天气、新闻、股价等）— 需要获取最新的外部数据，通常需要联网。
            - 如果问题涉及 **无法在现有数据源中找到答案**，则需要联网进行搜索。

        三大类意图分类：
        1. **general_answer** (通用知识问答)：非学校相关的通用知识问答  
        - GeneralQA: 普通的常识性问题  
        - Technology: 技术相关问题  
        - Life: 生活相关问题  
        - Other: 其他问题

        2. **knowledge_query** (校园业务查询)：学校相关的校园业务查询  
        - Policy: 校规校纪、管理制度、文件  
        - MajorInfo: 学院专业介绍、课程信息  
        - StudentStatus: 学籍管理、请假、转专业等  
        - CampusLife: 宿舍、饮食、校园卡、网络等  
        - Admission: 招生、报名、入学相关  
        - Employment: 实习、就业、招聘相关  
        - OtherSchool: 其他学校相关事务

        3. **data_query** (校园数据查询)：学校相关的数据查询  
        - Scholarship: 奖学金、助学金、评优评奖  
        - Course: 课程安排、选课、考试成绩

        ### JSON 返回格式：
        {{
            "intent_class": "三大类之一: general_answer/knowledge_query/data_query",
            "intent_name": "意图大类名称",
            "sub_intent_class": "子意图类别代码",
            "sub_intent_name": "子意图类别名称",
            "is_school_related": True/False,
            "need_web_search": True/False,
            "confidence": 0.0-1.0,
            "keywords_matched": ["匹配的关键词"],
            "analysis": "分析过程说明",
            "web_search_reason": "需要或不需要联网搜索的原因"
        }}

        ### 优化的要点：
        1. **更细化的判断标准**：在“需要联网搜索”的判断中，增加了对“实时信息”和“无法找到答案”情况的明确划分，避免错误地判定联网搜索。
        2. **更清晰的分类**：重新梳理了“通用知识问答”和“校园数据查询”两者的区别，强调校园业务查询不需要联网搜索。
        3. **关键词匹配与分析**：增强了对关键词的匹配，确保关键词能准确指示出问题类型和搜索需求。

        ---

        ### 示例：

        **用户问题：** "今天的天气怎么样？"

        **返回的 JSON：**
        ```json
        {{
            "intent_class": "general_answer",
            "intent_name": "GeneralQA",
            "sub_intent_class": "Technology",
            "sub_intent_name": "Weather",
            "is_school_related": False,
            "need_web_search": True,
            "confidence": 0.95,
            "keywords_matched": ["天气", "今天"],
            "analysis": "识别为天气查询，属于通用知识问答，且属于实时信息查询，需要联网获取最新的天气信息。",
            "web_search_reason": "天气问题需要联网搜索，获取实时数据。"
        }}

        """
        )

        self.image_analysis_prompt = ChatPromptTemplate.from_template(
            """
你是一个专业的图像分析助手。请分析这张图片的内容并识别用户的意图。

请从以下角度分析图片：
1. 图片内容描述
2. 是否包含文字信息
3. 是否与校园、学习、教育相关
4. 用户可能的查询意图

请返回JSON格式结果：
{{
    "image_description": "图片内容描述",
    "contains_text": true/false,
    "extracted_text": "提取的文字内容",
    "is_school_related": true/false,
    "possible_intents": ["可能的意图列表"],
    "suggested_questions": ["建议的问题"],
    "analysis": "分析说明"
}}
"""
        )

        self.image_intent_prompt = ChatPromptTemplate.from_template(
            """
你是一个专业的图像意图识别助手。请分析用户上传的图像并识别其意图。

图像描述：{image_description}

请按照以下步骤分析：
1. 判断图像是否与西安工程大学相关
2. 如果是校园相关，进一步判断是属于校园业务查询还是校园数据查询
3. 如果不是校园相关，归类为通用知识问答

三大类意图分类：
1. general_answer (通用知识问答): 非学校相关的通用知识问答
   - GeneralQA: 通用知识问答
   - Technology: 技术相关咨询
   - Life: 生活相关咨询
   - Other: 其他类型问题

2. knowledge_query (校园业务查询): 学校相关的校园业务查询
   - Policy: 校规校纪、管理办法、制度文件
   - MajorInfo: 学院专业介绍、课程信息
   - StudentStatus: 学籍管理、请假、转专业等
   - CampusLife: 宿舍、饮食、校园卡、网络等
   - Admission: 招生、报名、入学相关
   - Employment: 实习、就业、招聘相关
   - OtherSchool: 其他学校相关事务

3. data_query (校园数据查询): 学校相关的数据查询
   - Scholarship: 奖学金、助学金、评优评奖
   - Course: 课程安排、选课、考试成绩

请返回JSON格式结果：
{{
    "intent_class": "三大类之一: general_answer/knowledge_query/data_query",
    "intent_name": "意图大类名称",
    "sub_intent_class": "子意图类别代码",
    "sub_intent_name": "子意图类别名称",
    "is_school_related": true/false,
    "confidence": 0.0-1.0,
    "keywords_matched": ["匹配的关键词"],
    "analysis": "分析过程说明"
}}"""
        )

        self.multimodal_intent_prompt = ChatPromptTemplate.from_template(
            """
你是一个多模态意图识别助手。请结合文字和图片信息，识别用户的真实意图，同时判断是否需要联网搜索。

文字内容：{text}
图片分析结果：{image_analysis}

请按照以下步骤分析：
1. 分别分析文本和图像内容
2. 判断整体是否与西安工程大学相关
3. 如果是校园相关，进一步判断是属于校园业务查询还是校园数据查询
4. 如果不是校园相关，归类为通用知识问答
5. 判断是否需要联网搜索

三大类意图分类：
1. general_answer (通用知识问答): 非学校相关的通用知识问答
   - GeneralQA: 通用知识问答
   - Technology: 技术相关咨询
   - Life: 生活相关咨询
   - Other: 其他类型问题

2. knowledge_query (校园业务查询): 学校相关的校园业务查询
   - Policy: 校规校纪、管理办法、制度文件
   - MajorInfo: 学院专业介绍、课程信息
   - StudentStatus: 学籍管理、请假、转专业等
   - CampusLife: 宿舍、饮食、校园卡、网络等
   - Admission: 招生、报名、入学相关
   - Employment: 实习、就业、招聘相关
   - OtherSchool: 其他学校相关事务

3. data_query (校园数据查询): 学校相关的数据查询
   - Scholarship: 奖学金、助学金、评优评奖
   - Course: 课程安排、选课、考试成绩

联网搜索判断规则：
- 学校相关信息（knowledge_query、data_query）：不需要联网搜索
- 项目自身介绍（询问"你是谁"、"你的功能"等）：不需要联网搜索
- 简单问候语（"你好"、"谢谢"等短语）：不需要联网搜索
- 通用知识问答（general_answer）：需要联网搜索
- 实时信息查询（天气、新闻、股价等）：需要联网搜索

请返回JSON格式结果：
{{
    "intent_class": "三大类之一: general_answer/knowledge_query/data_query",
    "intent_name": "意图大类名称",
    "sub_intent_class": "子意图类别代码",
    "sub_intent_name": "子意图类别名称",
    "is_school_related": true/false,
    "need_web_search": true/false,
    "confidence": 0.0-1.0,
    "keywords_matched": ["匹配的关键词"],
    "analysis": "分析过程说明",
    "web_search_reason": "需要或不需要联网搜索的原因"
}}
"""
        )

    async def recognize_text_intent(self, text: str) -> Dict[str, Any]:
        """识别文本意图"""
        try:
            logger.info(f"开始文本意图识别: {text[:50]}...")

            # 1. 关键词匹配预分析
            keyword_result = self._keyword_based_classification(text)

            # 2. AI意图识别
            chain = self.text_intent_prompt | self.llm | JsonOutputParser()
            ai_result = await chain.ainvoke({"question": text})

            # 3. 结合关键词和AI结果
            final_result = self._combine_text_results(keyword_result, ai_result, text)
            final_result["timestamp"] = datetime.now().isoformat()

            # 记录识别历史
            self._log_recognition(text, final_result, "text")

            return final_result

        except Exception as e:
            logger.error(f"文本意图识别失败: {e}")
            return {
                "is_school_related": False,
                "intent_class": "Other",
                "intent_name": "其他",
                "confidence": 0.0,
                "error": str(e),
                "input_text": text,
            }

    async def recognize_image_intent(
        self, image_data: Union[str, bytes, Image.Image]
    ) -> Dict[str, Any]:
        """识别图像意图"""
        try:
            logger.info("开始图像意图识别...")

            # 1. 图像预处理
            processed_image = self._preprocess_image(image_data)

            # 2. 图像内容分析（如果支持视觉模型）
            if self._supports_vision():
                image_analysis = await self._analyze_image_with_vision(processed_image)
            else:
                image_analysis = self._basic_image_analysis(processed_image)

            # 3. 基于图像分析结果推断意图
            intent_result = self._infer_intent_from_image(image_analysis)

            intent_result["timestamp"] = datetime.now().isoformat()

            # 记录识别历史
            self._log_recognition("图像输入", intent_result, "image")

            return intent_result

        except Exception as e:
            logger.error(f"图像意图识别失败: {e}")
            return {
                "is_school_related": False,
                "intent_class": "Other",
                "confidence": 0.0,
                "error": str(e),
                "image_description": "图像处理失败",
            }

    async def recognize_multimodal_intent(
        self, text: str, image_data: Union[str, bytes, Image.Image]
    ) -> Dict[str, Any]:
        """识别多模态意图"""
        try:
            logger.info(f"开始多模态意图识别: {text[:30]}... + 图像")

            # 1. 分别识别文本和图像
            text_result = await self.recognize_text_intent(text)
            image_result = await self.recognize_image_intent(image_data)

            # 2. 多模态融合分析
            if self._supports_vision():
                chain = self.multimodal_intent_prompt | self.llm | JsonOutputParser()
                multimodal_result = await chain.ainvoke(
                    {
                        "text": text,
                        "image_analysis": json.dumps(image_result, ensure_ascii=False),
                    }
                )
            else:
                multimodal_result = self._basic_multimodal_fusion(
                    text_result, image_result
                )

            # 3. 整合结果
            final_result = {
                "text_analysis": text_result,
                "image_analysis": image_result,
                "multimodal_result": multimodal_result,
                "intent_class": multimodal_result.get(
                    "intent_class", text_result.get("intent_class")
                ),
                "intent_name": multimodal_result.get(
                    "intent_name", text_result.get("intent_name")
                ),
                "sub_intent_class": multimodal_result.get(
                    "sub_intent_class", text_result.get("sub_intent_class")
                ),
                "sub_intent_name": multimodal_result.get(
                    "sub_intent_name", text_result.get("sub_intent_name")
                ),
                "confidence": multimodal_result.get("confidence", 0.5),
                "is_school_related": multimodal_result.get(
                    "is_school_related", text_result.get("is_school_related")
                ),
                "need_web_search": multimodal_result.get(
                    "need_web_search", text_result.get("need_web_search", True)
                ),
                "input_text": text,
                "timestamp": datetime.now().isoformat(),
            }

            # 如果AI结果没有联网搜索判断，使用我们的判断逻辑
            if "need_web_search" not in multimodal_result:
                final_result["need_web_search"] = self._determine_web_search_need(
                    final_result
                )

            # 记录识别历史
            self._log_recognition(f"{text} + 图像", final_result, "multimodal")

            return final_result

        except Exception as e:
            logger.error(f"多模态意图识别失败: {e}")
            return {
                "is_school_related": False,
                "intent_class": "general_answer",
                "intent_name": "通用知识问答",
                "sub_intent_class": "Other",
                "sub_intent_name": "其他",
                "confidence": 0.0,
                "error": str(e),
            }

    def _keyword_based_classification(self, text: str) -> Dict[str, Any]:
        """基于关键词的分类"""
        matched_subcategories = []

        # 遍历三大类意图
        for category_type, category_info in self.intent_categories.items():
            subcategories = category_info.get("subcategories", {})

            # 遍历子类别
            for intent_code, intent_info in subcategories.items():
                keywords = intent_info.get("keywords", [])
                matched_keywords = [kw for kw in keywords if kw in text]

                if matched_keywords:
                    matched_subcategories.append(
                        {
                            "category_type": category_type,  # general_answer, knowledge_query, data_query
                            "category_name": category_info.get("name", ""),
                            "intent_code": intent_code,
                            "intent_name": intent_info.get("name", ""),
                            "matched_keywords": matched_keywords,
                            "match_score": len(matched_keywords) / len(keywords)
                            if keywords
                            else 0,
                        }
                    )

        # 选择匹配度最高的类别
        if matched_subcategories:
            best_match = max(matched_subcategories, key=lambda x: x["match_score"])
            return {
                "intent_class": best_match["category_type"],  # 返回三大类之一
                "intent_name": best_match["category_name"],
                "sub_intent_class": best_match["intent_code"],
                "sub_intent_name": best_match["intent_name"],
                "is_school_related": best_match["category_type"] != "general_answer",
                "confidence": best_match["match_score"],
                "matched_keywords": best_match["matched_keywords"],
                "method": "keyword_matching",
            }
        else:
            # 默认返回general_answer
            return {
                "intent_class": "general_answer",
                "intent_name": "通用知识问答",
                "sub_intent_class": "Other",
                "sub_intent_name": "其他",
                "is_school_related": False,
                "confidence": 0.0,
                "matched_keywords": [],
                "method": "keyword_matching",
            }

    def _combine_text_results(
        self, keyword_result: Dict, ai_result: Dict, input_text: str = ""
    ) -> Dict[str, Any]:
        """结合关键词和AI识别结果"""
        # 如果AI识别置信度高，优先使用AI结果
        if ai_result.get("confidence", 0) > 0.7:
            final_result = ai_result.copy()
            final_result["keyword_analysis"] = keyword_result
        # 如果关键词匹配度高，结合两者结果
        elif keyword_result.get("confidence", 0) > 0.5:
            final_result = keyword_result.copy()
            final_result["ai_analysis"] = ai_result
            # 调整置信度
            final_result["confidence"] = (
                keyword_result.get("confidence", 0) + ai_result.get("confidence", 0)
            ) / 2
        else:
            # 默认使用AI结果
            final_result = ai_result.copy()
            final_result["keyword_analysis"] = keyword_result

        final_result["recognition_method"] = "combined"
        final_result["input_text"] = input_text

        # 特殊处理：项目自身介绍（即使包含学校名称也不应被识别为学校相关）
        user_text = input_text.lower()
        if ("西安工程大学回答助手" in user_text or "小丫" in user_text) and any(
            word in user_text for word in ["用途", "功能", "作用", "是什么", "介绍"]
        ):
            logger.info("检测到项目自身介绍问题（包含学校名称），修正为非学校相关")
            final_result["is_school_related"] = False
            final_result["intent_class"] = "general_answer"
            final_result["intent_name"] = "通用知识问答"
            final_result["sub_intent_class"] = "SystemInfo"
            final_result["sub_intent_name"] = "系统功能介绍"

        # 添加联网搜索判断
        final_result["need_web_search"] = self._determine_web_search_need(final_result)

        return final_result

    def _determine_web_search_need(self, intent_result: Dict[str, Any]) -> bool:
        """判断是否需要联网搜索"""
        try:
            # 获取用户输入文本
            user_text = intent_result.get("input_text", "").lower()

            # 1. 学校相关信息一律不用联网搜索
            if intent_result.get("is_school_related", False):
                logger.info("学校相关问题，不需要联网搜索")
                return False

            # 1.5 快速检查常见问候语和自我介绍请求
            if any(phrase in user_text for phrase in ["你好", "请介绍", "自我介绍", "介绍一下自己"]):
                logger.info(f"检测到问候或自我介绍请求: {user_text}，不需要联网搜索")
                return False

            # 2. 针对本项目的问题不需要联网搜索（更全面的关键词检测）
            project_keywords = [
                "你是谁",
                "你的功能",
                "你能做什么",
                "介绍一下你",
                "你的用途",
                "chatbi",
                "聊天助手",
                "智能助手",
                "回答助手",
                "小丫",
                "你的作用",
                "你的能力",
                "你是什么",
                "你叫什么",
                "你的名字",
                "你是哪个",
                "你来自",
                "你属于",
                "打个招呼",
                "问候",
                "认识一下",
            ]

            # 特殊处理：包含"西安工程大学回答助手"或"小丫"的项目相关问题
            if ("西安工程大学回答助手" in user_text or "小丫" in user_text) and any(
                word in user_text for word in ["用途", "功能", "作用", "是什么", "介绍"]
            ):
                logger.info("检测到项目自身介绍问题（包含学校名称），不需要联网搜索")
                return False

            # 检测项目相关问题的模式
            project_patterns = ["你是", "你的", "你能", "你会", "你有", "你叫", "你来自", "你属于"]

            # 先检查直接关键词匹配
            for keyword in project_keywords:
                if keyword in user_text:
                    logger.info(f"检测到项目相关问题关键词: {keyword}，不需要联网搜索")
                    return False

            # 再检查模式匹配（针对"你是谁？"这类问题）
            for pattern in project_patterns:
                if pattern in user_text and len(user_text.strip()) <= 20:
                    logger.info(f"检测到项目相关问题模式: {pattern}，不需要联网搜索")
                    return False

            # 3. 简单问候语不需要联网搜索（但要排除复合问题）
            greeting_keywords = [
                "你好",
                "hello",
                "hi",
                "早上好",
                "下午好",
                "晚上好",
                "再见",
                "谢谢",
                "不客气",
                "没关系",
                "拜拜",
                "bye",
            ]

            # 检查是否是纯问候语（不包含其他实质性问题）
            for keyword in greeting_keywords:
                if keyword in user_text:
                    # 如果问候语后面还有实质性问题，不算纯问候语
                    remaining_text = user_text.replace(keyword, "").strip("，。！？,!?")
                    if len(remaining_text) <= 5:  # 只有很少的其他字符，算作纯问候语
                        logger.info(f"检测到简单问候语: {keyword}，不需要联网搜索")
                        return False

            # 4. 通用知识问答需要联网搜索
            intent_class = intent_result.get("intent_class", "")
            if intent_class == "general_answer":
                # 检查是否是需要实时信息的问题
                realtime_keywords = [
                    "最新",
                    "今天",
                    "现在",
                    "当前",
                    "最近",
                    "新闻",
                    "股价",
                    "天气",
                    "时间",
                    "日期",
                    "什么时候",
                    "几点",
                    "价格",
                ]

                knowledge_keywords = [
                    "什么是",
                    "怎么",
                    "为什么",
                    "如何",
                    "原理",
                    "定义",
                    "介绍",
                    "解释",
                    "方法",
                    "步骤",
                    "技术",
                    "算法",
                ]

                # 包含实时信息关键词或知识性关键词的问题需要联网搜索
                has_realtime = any(
                    keyword in user_text for keyword in realtime_keywords
                )
                has_knowledge = any(
                    keyword in user_text for keyword in knowledge_keywords
                )

                if has_realtime or has_knowledge:
                    logger.info("通用知识问答且包含需要搜索的关键词，需要联网搜索")
                    return True

                # 其他通用问题也默认需要联网搜索以获取更准确信息
                logger.info("通用知识问答，默认需要联网搜索")
                return True

            # 5. 默认情况下不需要联网搜索
            logger.info("默认不需要联网搜索")
            return False

        except Exception as e:
            logger.error(f"判断联网搜索需求时出错: {e}")
            # 出错时默认不需要联网搜索
            return False

    def _preprocess_image(
        self, image_data: Union[str, bytes, Image.Image]
    ) -> Image.Image:
        """图像预处理"""
        if isinstance(image_data, str):
            # Base64字符串
            if image_data.startswith("data:image"):
                image_data = image_data.split(",")[1]
            image_bytes = base64.b64decode(image_data)
            return Image.open(io.BytesIO(image_bytes))
        elif isinstance(image_data, bytes):
            return Image.open(io.BytesIO(image_data))
        elif isinstance(image_data, Image.Image):
            return image_data
        else:
            raise ValueError("不支持的图像数据格式")

    def _supports_vision(self) -> bool:
        """检查是否支持视觉模型"""
        # 检查模型是否支持视觉功能
        vision_models = ["gpt-4-vision", "gpt-4o", "claude-3"]
        return any(model in settings.OPENAI_MODEL.lower() for model in vision_models)

    async def _analyze_image_with_vision(self, image: Image.Image) -> Dict[str, Any]:
        """使用视觉模型分析图像"""
        try:
            # 将图像转换为base64
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()

            # 构建视觉消息
            message = HumanMessage(
                content=[
                    {"type": "text", "text": self.image_analysis_prompt.format()},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_base64}"},
                    },
                ]
            )

            response = await self.llm.ainvoke([message])

            # 解析JSON响应
            try:
                return JsonOutputParser().parse(response.content)
            except:
                return {
                    "image_description": response.content,
                    "contains_text": False,
                    "is_school_related": False,
                    "analysis": "视觉分析完成，但结果解析失败",
                }

        except Exception as e:
            logger.error(f"视觉模型分析失败: {e}")
            return self._basic_image_analysis(image)

    def _basic_image_analysis(self, image: Image.Image) -> Dict[str, Any]:
        """基础图像分析（无视觉模型时的备选方案）"""
        # 获取图像基本信息
        width, height = image.size
        mode = image.mode

        # 简单的图像特征分析
        analysis = {
            "image_description": f"图像尺寸: {width}x{height}, 模式: {mode}",
            "contains_text": False,  # 无法检测文字
            "extracted_text": "",
            "is_school_related": False,  # 无法判断
            "possible_intents": ["图像查询", "视觉问答"],
            "suggested_questions": ["这张图片是什么？", "请描述图片内容"],
            "analysis": "基础图像分析（无视觉模型支持）",
        }

        return analysis

    def _infer_intent_from_image(
        self, image_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """从图像分析结果推断意图"""
        is_school_related = image_analysis.get("is_school_related", False)

        if is_school_related:
            # 根据图像内容推断具体的校园意图
            description = image_analysis.get("image_description", "").lower()
            extracted_text = image_analysis.get("extracted_text", "").lower()

            combined_text = f"{description} {extracted_text}"

            # 使用关键词匹配推断意图
            keyword_result = self._keyword_based_classification(combined_text)

            return {
                "is_school_related": True,
                "intent_class": keyword_result.get("intent_class", "OtherSchool"),
                "intent_name": keyword_result.get("intent_name", "其他校园"),
                "confidence": 0.6,  # 图像推断的置信度相对较低
                "image_analysis": image_analysis,
                "inference_method": "image_content_analysis",
            }
        else:
            return {
                "is_school_related": False,
                "intent_class": "Other",
                "intent_name": "其他",
                "confidence": 0.5,
                "image_analysis": image_analysis,
                "inference_method": "image_content_analysis",
            }

    def _basic_multimodal_fusion(
        self, text_result: Dict, image_result: Dict
    ) -> Dict[str, Any]:
        """基础多模态融合（无多模态模型时的备选方案）"""
        # 简单的融合策略：优先考虑文本结果，图像作为补充
        text_confidence = text_result.get("confidence", 0)
        image_confidence = image_result.get("confidence", 0)

        if text_confidence > image_confidence:
            final_intent = text_result.get("intent_class", "Other")
            is_school_related = text_result.get("is_school_related", False)
            confidence = text_confidence
        else:
            final_intent = image_result.get("intent_class", "Other")
            is_school_related = image_result.get("is_school_related", False)
            confidence = image_confidence

        return {
            "final_intent": final_intent,
            "confidence": confidence,
            "is_school_related": is_school_related,
            "multimodal_analysis": "基础融合策略：优先文本，图像补充",
            "recommended_action": "建议使用支持多模态的模型以获得更好的效果",
        }

    def _log_recognition(
        self, input_data: str, result: Dict[str, Any], input_type: str
    ):
        """记录识别历史"""
        import uuid

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "input_type": input_type,
            "input_preview": input_data[:100]
            if isinstance(input_data, str)
            else "图像数据",
            "intent_class": result.get("intent_class") or result.get("final_intent"),
            "intent_name": result.get("intent_name", ""),
            "sub_intent_class": result.get("sub_intent_class", "GeneralQA"),
            "sub_intent_name": result.get("sub_intent_name", "通用知识问答"),
            "is_school_related": result.get("is_school_related", False),
            "confidence": result.get("confidence", 0.0),
            "recognition_id": str(uuid.uuid4()),
        }

        self.recognition_history.append(log_entry)
        logger.info(f"意图识别完成: {log_entry}")

        # 保持历史记录在合理范围内
        if len(self.recognition_history) > 1000:
            self.recognition_history = self.recognition_history[-500:]

    def get_recognition_statistics(self) -> Dict[str, Any]:
        """获取识别统计信息"""
        if not self.recognition_history:
            return {"total_recognitions": 0, "intents": []}

        total = len(self.recognition_history)
        intent_counts = {}
        school_related_count = 0

        # 统计三大类意图
        for entry in self.recognition_history:
            intent_class = entry.get("intent_class", "general_answer")
            intent_name = entry.get("intent_name", "通用知识问答")
            sub_intent_class = entry.get("sub_intent_class", "GeneralQA")
            sub_intent_name = entry.get("sub_intent_name", "通用知识问答")

            if intent_class not in intent_counts:
                intent_counts[intent_class] = {
                    "count": 0,
                    "name": intent_name,
                    "percentage": 0,
                    "sub_intents": {},
                }

            intent_counts[intent_class]["count"] += 1

            # 统计子意图
            if sub_intent_class not in intent_counts[intent_class]["sub_intents"]:
                intent_counts[intent_class]["sub_intents"][sub_intent_class] = {
                    "count": 0,
                    "name": sub_intent_name,
                    "percentage": 0,
                }

            intent_counts[intent_class]["sub_intents"][sub_intent_class]["count"] += 1

            if entry.get("is_school_related", False):
                school_related_count += 1

        # 计算百分比
        for intent_class in intent_counts:
            intent_counts[intent_class]["percentage"] = round(
                (intent_counts[intent_class]["count"] / total) * 100, 2
            )

            # 计算子意图百分比
            for sub_intent in intent_counts[intent_class]["sub_intents"]:
                sub_count = intent_counts[intent_class]["sub_intents"][sub_intent][
                    "count"
                ]
                intent_counts[intent_class]["sub_intents"][sub_intent][
                    "percentage"
                ] = round((sub_count / intent_counts[intent_class]["count"]) * 100, 2)

        # 转换为列表格式
        intents_list = []
        for intent_class, data in intent_counts.items():
            # 转换子意图为列表
            sub_intents_list = []
            for sub_intent, sub_data in data["sub_intents"].items():
                sub_intents_list.append(
                    {
                        "sub_intent_class": sub_intent,
                        "sub_intent_name": sub_data["name"],
                        "count": sub_data["count"],
                        "percentage": sub_data["percentage"],
                    }
                )

            # 按计数降序排序子意图
            sub_intents_list.sort(key=lambda x: x["count"], reverse=True)

            intents_list.append(
                {
                    "intent_class": intent_class,
                    "intent_name": data["name"],
                    "count": data["count"],
                    "percentage": data["percentage"],
                    "sub_intents": sub_intents_list,
                }
            )

        # 按计数降序排序主意图
        intents_list.sort(key=lambda x: x["count"], reverse=True)

        return {
            "total_recognitions": total,
            "school_related_percentage": round((school_related_count / total) * 100, 2),
            "intents": intents_list,
        }
