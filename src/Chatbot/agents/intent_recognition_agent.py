"""
意图识别智能体模块
仅保留：基于大模型的文本意图识别
"""

from typing import Dict, Any, Optional
import time
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from config.settings import settings
from src.Chatbot.utils.logger import setup_logger

logger = setup_logger("intent_recognition_agent")


class IntentRecognitionAgent:
    """意图识别智能体"""

    def __init__(self):
        """初始化意图识别智能体（最小化实现：仅LLM与提示词）"""
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_MODEL_BASE_URL,
            temperature=0.0,
            max_tokens=128,
        )
        self._stats = {
            "calls": 0,
            "failures": 0,
            "avg_latency_ms": 0.0,
            "last_latency_ms": 0.0,
        }
        self._initialize_prompts()

    # 仅保留提示词初始化

    def _initialize_prompts(self):
        """初始化提示词模板"""
        self.text_intent_prompt = ChatPromptTemplate.from_template(
            """
            你是一名专业的“意图识别与任务分类助手”，负责根据用户提出的问题，精准识别其意图类别、意图目的，并说明推理依据。  
            你的目标是：让下游模块（如工具调用、知识库查询、回答生成）能够基于你的输出，准确决策“应做什么”和“不能做什么”。

            ---

            ### 【输入信息】
            用户问题（question）：{question}

            ---

            ### 【分析与推理步骤】

            #### 第 1 步：识别语境与领域归属
            1. 判断问题是否与“西安工程大学”或其相关校园场景（学院、课程、教务、学籍、住宿、奖学金、校园卡、就业等）有关。  
            2. 若与学校或校园场景相关，则标记为 `is_school_related = true`；否则为 `false`。

            #### 第 2 步：判定问题大类（意图主类）
            - 若 **不涉及学校** → 归类为 `general_answer`
            - 若 **涉及学校事务性或政策类问题** → 归类为 `knowledge_query`
            - 若 **涉及学校内部数据（成绩、选课、奖学金等）** → 归类为 `data_query`

            #### 第 3 步：细分子意图（具体主题分类）
            根据问题的核心内容匹配以下子类：

            1. **general_answer（通用知识问答）**
            - `GeneralQA`: 常识性、事实性问题（如时间、地点、概念解释）
            - `Technology`: 技术类问题（如代码、AI、计算机、系统问题）
            - `Life`: 生活类问题（如饮食、出行、健康、购物）
            - `Other`: 其他不属于上述分类的通用问题

            2. **knowledge_query（校园业务查询）**
            - `Policy`: 校规校纪、管理制度、文件政策
            - `MajorInfo`: 学院、专业、课程介绍及培养方案
            - `StudentStatus`: 学籍、请假、转专业、休复学等事务
            - `CampusLife`: 宿舍、饮食、校园卡、网络、活动等
            - `Admission`: 招生、报名、录取、入学相关
            - `Employment`: 实习、就业、招聘、访企拓岗
            - `OtherSchool`: 其他未明确定义的学校相关事务

            3. **data_query（校园数据查询）**
            - `Scholarship`: 奖学金、助学金、评优评奖等数据
            - `Course`: 课程表、选课安排、考试成绩、教务系统信息

            #### 第 4 步：分析用户真实意图（语义层分析）
            - 分析用户问题背后的 **目的、任务目标或信息需求类型**。  
            - 判断问题是否隐含“查询”“操作”“咨询”“解释”等动作意图。  
            - 例如：  
            - “我想知道奖学金什么时候发” → 意图是 **数据时间查询（Scholarship）**  
            - “请问学校的请假制度是什么” → 意图是 **制度政策咨询（StudentStatus）**

            #### 第 5 步：确定使用限制（Restriction）
            - 若问题涉及敏感信息、受限数据或不允许联网工具访问的内容，应标明限制条件。  
            - 举例：  
            - 若问题为“如何入侵教务系统”，则限制为 `"Restriction": "禁止任何非法工具或系统访问"`  
            - 若问题可回答但无需联网，应注明 `"Restriction": "无需联网查询"`

            ---
            规则：is_school_related 根据是否涉及学校场景判断。
            限制：当为 knowledge_query 或 data_query，Restriction 必须为 "禁止使用网络搜索"。
            输出字段：
            {{
              "intent_class": "...",
              "intent_name": "...",
              "sub_intent_class": "...",
              "sub_intent_name": "...",
              "is_school_related": true,
              "analysis": "不超过20字",
              "Restriction": "..."
            }}
            """
        )


    async def recognize_text_intent(self, text: str) -> Dict[str, Any]:
        """识别文本意图（直接调用大模型并返回规范JSON）"""
        try:
            t0 = time.perf_counter()
            chain = self.text_intent_prompt | self.llm | JsonOutputParser()
            ai_result = await chain.ainvoke({"question": text})
            t1 = time.perf_counter()
            self._stats["calls"] += 1
            self._stats["last_latency_ms"] = (t1 - t0) * 1000
            c = self._stats["calls"]
            prev_avg = self._stats["avg_latency_ms"]
            self._stats["avg_latency_ms"] = prev_avg + (self._stats["last_latency_ms"] - prev_avg) / c
            if isinstance(ai_result, dict):
                ic = ai_result.get("intent_class", "")
                if ic in ("knowledge_query", "data_query"):
                    ai_result["Restriction"] = "禁止使用网络搜索"
                analysis = ai_result.get("analysis", "")
                if isinstance(analysis, str):
                    ai_result["analysis"] = analysis[:20]
            return ai_result
        except Exception as e:
            logger.error(f"文本意图识别失败: {e}")
            self._stats["failures"] += 1
            # 回退：返回规范字段，说明失败原因
            return {
                "intent_class": "Other",
                "intent_name": "其他",
                "sub_intent_class": "Other",
                "sub_intent_name": "其他",
                "is_school_related": False,
                "analysis": "识别失败",
                "Restriction": "无需联网查询",
            }

    async def recognize_multimodal_intent(self, text: str, image_data: Optional[bytes]) -> Dict[str, Any]:
        return await self.recognize_text_intent(text)

    def get_recognition_statistics(self) -> Dict[str, Any]:
        return dict(self._stats)
