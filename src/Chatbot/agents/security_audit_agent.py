"""
安全审核智能体模块
实现内容过滤、敏感词检测、政治敏感等安全审核功能
"""

import re
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from config.settings import settings
from src.Chatbot.utils.logger import setup_logger

logger = setup_logger("security_audit_agent")


class SecurityAuditAgent:
    """安全审核智能体"""

    def __init__(self):
        """初始化安全审核智能体"""
        # 初始化敏感词库
        self._initialize_sensitive_words()
        # 初始化正则规则（覆盖变体与短语组合）
        self._initialize_regex_rules()
        # 审核日志
        self.audit_logs = []

    def _initialize_sensitive_words(self):
        """初始化敏感词库"""
        # 政治敏感词
        self.political_sensitive_words = [
            "政治敏感",
            "反政府",
            "颠覆",
            "分裂",
            "独立",
            "暴力",
            "恐怖",
            "极端",
            "仇恨",
            "歧视",
        ]

        # 违规内容词汇（违法、黄赌毒、诽谤等）
        self.violation_words = [
            "作弊",
            "代考",
            "买卖答案",
            "学术不端",
            "抄袭",
            "威胁",
            "恶意攻击",
            "人身攻击",
            "诽谤",
            "违法",
            "赌博",
            "毒品",
            "色情",
            "涉黄",
            "走私",
            "传销",
            "贩毒",
            "吸毒",
            "赌钱",
        ]

        # 不当言论（侮辱类）
        self.inappropriate_words = [
            "脏话",
            "侮辱",
            "谩骂",
            "辱骂",
            "羞辱",
            "嘲讽",
            "讥讽",
            "贬低",
            "诋毁",
            "挑衅",
            "恶意中伤",
            "冷嘲热讽",
            "侮蔑",
            "辱侮",
            "骂人",
        ]

        # 学术不端相关（高风险）
        self.academic_misconduct_words = [
            "代写",
            "代考",
            "买论文",
            "卖答案",
            "考试作弊",
            "抄袭",
            "剽窃",
            "学术造假",
            "数据造假",
            "买题",
            "泄题",
            "枪手",
        ]

        # 暴力行为（高风险，独立分类）
        self.violence_words = [
            "打他",
            "打人",
            "殴打",
            "伤害",
            "重伤",
            "斗殴",
            "揍",
            "动手打人",
            "施暴",
        ]

        # 暴力/人身威胁（高风险）
        self.threat_words = [
            "恐吓",
            "要杀",
            "杀了",
            "弄死",
            "干掉",
            "砍死",
            "捅他",
            "报复",
            "威胁",
        ]

    def _initialize_audit_prompts(self):
        """初始化审核提示词"""
        self.content_audit_prompt = ChatPromptTemplate.from_template(
            """
            你是一个严格且专业的内容安全审核助手，负责检测文本中的安全与合规风险。  
            请以中立、客观、可执行的方式完成以下任务。

            【待审核内容】
            {content}

            【审核目标】
            请从以下维度逐项分析，并生成结构化 JSON 审核报告：

            1. 政治敏感性  
            - 是否包含政治人物、政府机构、国家安全、分裂、煽动等内容。
            2. 违法违规  
            - 是否涉及违法犯罪、恐怖暴力、黄赌毒、欺诈等内容。
            3. 学术诚信  
            - 是否涉及抄袭、代写、作弊、伪造数据等学术不端行为。
            4. 言论规范  
            - 是否包含侮辱、歧视、攻击、恐吓、辱骂、冒犯或不当言论。
            5. 内容合规  
            - 是否与教育场景、校园文化、社会公德相冲突。
            6. 其他风险  
            - 是否存在误导、低俗、违规广告、隐私泄露等潜在风险。

            【输出要求】
            请输出以下 JSON 结构，确保字段齐全且格式正确：

            {{
                "is_safe": true/false,             // 内容是否总体安全
                "risk_level": "low/medium/high",   // 整体风险等级
                "violations": [                    // 如存在风险，列出具体项
                    {{
                        "type": "违规类型",
                        "description": "详细描述",
                        "severity": "low/medium/high"
                    }}
                ],
                "suggestions": "优化或整改建议",
                "filtered_content": "若需屏蔽的敏感部分，可输出过滤后内容；若安全则原样返回"
            }}

            【输出风格】
            - 仅返回合法 JSON 对象，不包含额外说明。  
            - 若无风险，violations 数组返回空列表 []。
        """
        )

        self.context_audit_prompt = ChatPromptTemplate.from_template(
        """
        你是一个专业的对话上下文安全审核助手。  
        请基于历史对话与当前输入，综合判断是否存在潜在风险。

        【历史对话】
        {context}

        【当前内容】
        {content}

        【分析目标】
        请重点检查以下方面：
        1. 上下文关联风险  
        - 是否与历史内容形成连贯的敏感语义（如诱导生成违规回答）。  
        2. 误导与诱导性  
        - 是否引导模型产生虚假、偏见、违法、低俗等输出。  
        3. 场景适配性  
        - 是否符合教育、科研、校园类场景的规范要求。  
        4. 语义延伸风险  
        - 是否可能在后续交互中被继续利用为违规线索。

        【输出要求】
        请返回严格的 JSON 结构：

        {{
            "is_safe": true/false,             // 是否安全
            "context_risk": "low/medium/high", // 上下文相关风险等级
            "analysis": "简要描述风险来源与上下文关联",
            "recommendations": "如何调整内容或上下文以确保安全"
        }}

        【输出风格】
        - 输出必须是可解析的 JSON。
        - 不得添加解释性前后缀。
        """
        )


    async def audit_content(
        self, content: str, context: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        对文本内容进行安全审核（纯文本关键词规则）。
        """
        try:
            logger.info(f"开始安全审核: {content[:50]}...")

            # 仅进行关键词规则审核
            keyword_result = self._check_sensitive_keywords(content)
            is_safe = keyword_result.get("is_safe", True)
            final_risk = keyword_result.get("risk_level", "low")
            filtered_content = self._filter_content_by_keywords(content) if not is_safe else content

            final_result = {
                "is_safe": is_safe,
                "risk_level": final_risk,
                "violations": keyword_result.get("violations", []),
                "audit_methods": {
                    "keyword_check": keyword_result,
                    "ai_audit": None,
                    "context_audit": None,
                },
                "filtered_content": filtered_content,
                "suggestions": "" if is_safe else "请遵守校纪校规，不请求不当内容。",
                "timestamp": datetime.now().isoformat(),
            }

            # 记录审核日志
            self._log_audit_result(content, final_result)
            return final_result

        except Exception as e:
            logger.error(f"安全审核失败: {e}")
            return {
                "is_safe": False,
                "risk_level": "high",
                "error": f"审核过程出错: {str(e)}",
                "filtered_content": content,
            }

    def _check_sensitive_keywords(self, content: str) -> Dict[str, Any]:
        """检查敏感关键词（包含列表匹配与正则匹配，带风险升级规则）"""
        violations = []

        # 规范化文本：移除空白、统一全角标点为半角
        normalized = re.sub(r"\s+", "", content)
        normalized = normalized.replace("，", ",").replace("。", ".").replace("！", "!").replace("？", "?")

        # 1) 列表匹配：政治敏感（默认高风险）
        for word in self.political_sensitive_words:
            if word and word in normalized:
                violations.append({"type": "政治敏感", "keyword": word, "severity": "high"})

        # 2) 列表匹配：违法违规（中-高混合，默认中风险）
        for word in self.violation_words:
            if word and word in normalized:
                # 违法、毒品、赌博归为高风险；其余默认中风险
                high_terms = {"违法", "毒品", "赌博", "贩毒", "吸毒", "走私", "传销"}
                severity = "high" if word in high_terms else "medium"
                violations.append({"type": "违规内容", "keyword": word, "severity": severity})

        # 3) 列表匹配：不当言论（默认中风险）
        for word in self.inappropriate_words:
            if word and word in normalized:
                violations.append({"type": "不当言论", "keyword": word, "severity": "medium"})

        # 4) 列表匹配：学术不端（高风险）
        for word in self.academic_misconduct_words:
            if word and word in normalized:
                violations.append({"type": "学术不端", "keyword": word, "severity": "high"})

        # 5) 列表匹配：暴力与威胁（高风险）
        for word in getattr(self, "violence_words", []):
            if word and word in normalized:
                violations.append({"type": "暴力行为", "keyword": word, "severity": "high"})
        for word in getattr(self, "threat_words", []):
            if word and word in normalized:
                violations.append({"type": "暴力威胁", "keyword": word, "severity": "high"})

        # 6) 正则匹配：覆盖变体与短语组合
        for rule in getattr(self, "regex_rules", []):
            for m in rule["pattern"].finditer(normalized):
                matched = m.group(0)
                violations.append({"type": rule["type"], "keyword": matched, "severity": rule["severity"]})

        # 7) 风险升级规则（组合与频次）
        types = [v["type"] for v in violations]
        severities = [v["severity"] for v in violations]
        type_set = set(types)
        insult_count = sum(1 for v in violations if v["type"] == "不当言论")
        threat_present = any(v["type"] in {"暴力威胁"} for v in violations)
        violence_present = any(v["type"] in {"暴力行为"} for v in violations)

        # 基础等级：有 high -> high；否则有 medium -> medium；否则 low
        if any(s == "high" for s in severities):
            risk_level = "high"
            is_safe = False
        elif any(s == "medium" for s in severities):
            risk_level = "medium"
            is_safe = False
        else:
            risk_level = "low"
            is_safe = True

        # 组合升级：侮辱+威胁 或 侮辱+暴力 -> 高风险
        if insult_count >= 1 and (threat_present or violence_present):
            risk_level = "high"
            is_safe = False
        # 频次升级：不当言论出现 >=3 次，提升为高风险；>=2 次维持中风险
        elif insult_count >= 3:
            risk_level = "high"
            is_safe = False
        elif insult_count >= 2 and risk_level == "low":
            risk_level = "medium"
            is_safe = False
        
        # 跨类叠加：不同类型命中 >=3 项，提升为高风险
        if len(type_set) >= 3:
            risk_level = "high"
            is_safe = False

        return {
            "method": "keyword_check",
            "is_safe": is_safe,
            "risk_level": risk_level,
            "violations": violations,
        }

    async def _ai_content_audit(self, content: str) -> Dict[str, Any]:
        """AI内容审核"""
        try:
            chain = self.content_audit_prompt | self.llm | JsonOutputParser()
            result = await chain.ainvoke({"content": content})
            result["method"] = "ai_audit"
            return result
        except Exception as e:
            logger.error(f"AI内容审核失败: {e}")
            return {
                "method": "ai_audit",
                "is_safe": False,
                "risk_level": "medium",
                "error": str(e),
            }

    async def _context_audit(self, content: str, context: List[str]) -> Dict[str, Any]:
        """上下文审核"""
        try:
            context_str = "\n".join(context[-5:])  # 取最近5条对话
            chain = self.context_audit_prompt | self.llm | JsonOutputParser()
            result = await chain.ainvoke({"content": content, "context": context_str})
            result["method"] = "context_audit"
            return result
        except Exception as e:
            logger.error(f"上下文审核失败: {e}")
            return {
                "method": "context_audit",
                "is_safe": True,
                "context_risk": "low",
                "error": str(e),
            }

    def _combine_audit_results(
        self,
        keyword_result: Dict,
        ai_result: Dict,
        context_result: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """综合审核结果"""
        # 收集所有违规信息
        all_violations = []

        if keyword_result.get("violations"):
            all_violations.extend(keyword_result["violations"])

        if ai_result.get("violations"):
            all_violations.extend(ai_result["violations"])

        # 确定最终安全状态
        is_safe = keyword_result.get("is_safe", True) and ai_result.get("is_safe", True)

        if context_result:
            is_safe = is_safe and context_result.get("is_safe", True)

        # 确定风险等级
        risk_levels = [
            keyword_result.get("risk_level", "low"),
            ai_result.get("risk_level", "low"),
        ]

        if context_result:
            risk_levels.append(context_result.get("context_risk", "low"))

        # 取最高风险等级
        if "high" in risk_levels:
            final_risk = "high"
        elif "medium" in risk_levels:
            final_risk = "medium"
        else:
            final_risk = "low"

        # 生成过滤后的内容
        filtered_content = ai_result.get("filtered_content", "")
        if not filtered_content:
            filtered_content = self._filter_content_by_keywords(
                ai_result.get("original_content", "")
            )

        return {
            "is_safe": is_safe,
            "risk_level": final_risk,
            "violations": all_violations,
            "audit_methods": {
                "keyword_check": keyword_result,
                "ai_audit": ai_result,
                "context_audit": context_result,
            },
            "filtered_content": filtered_content,
            "suggestions": ai_result.get("suggestions", ""),
            "timestamp": datetime.now().isoformat(),
        }

    def _filter_content_by_keywords(self, content: str) -> str:
        """基于关键词与正则过滤内容"""
        filtered = content

        # 替换敏感词（列表）
        all_sensitive_words = (
            self.political_sensitive_words
            + self.violation_words
            + self.inappropriate_words
            + self.academic_misconduct_words
            + getattr(self, "violence_words", [])
            + getattr(self, "threat_words", [])
        )

        for word in all_sensitive_words:
            if word and word in filtered:
                filtered = filtered.replace(word, "*" * len(word))

        # 替换正则命中的片段
        for rule in getattr(self, "regex_rules", []):
            def _mask(m: re.Match) -> str:
                return "*" * len(m.group(0))
            filtered = rule["pattern"].sub(_mask, filtered)

        return filtered

    def _log_audit_result(self, content: str, result: Dict[str, Any]):
        """记录审核日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "content_preview": content[:100],
            "is_safe": result["is_safe"],
            "risk_level": result["risk_level"],
            "violations_count": len(result.get("violations", [])),
            "audit_id": f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        }

        self.audit_logs.append(log_entry)
        logger.info(f"审核完成: {log_entry}")

        # 保持日志数量在合理范围内
        if len(self.audit_logs) > 1000:
            self.audit_logs = self.audit_logs[-500:]

    def get_audit_statistics(self) -> Dict[str, Any]:
        """获取审核统计信息"""
        if not self.audit_logs:
            return {"message": "暂无审核记录"}

        total_audits = len(self.audit_logs)
        safe_count = sum(1 for log in self.audit_logs if log["is_safe"])
        unsafe_count = total_audits - safe_count

        risk_distribution = {}
        for log in self.audit_logs:
            risk = log["risk_level"]
            risk_distribution[risk] = risk_distribution.get(risk, 0) + 1

        return {
            "total_audits": total_audits,
            "safe_count": safe_count,
            "unsafe_count": unsafe_count,
            "safety_rate": f"{(safe_count/total_audits)*100:.2f}%",
            "risk_distribution": risk_distribution,
            "recent_audits": self.audit_logs[-10:],  # 最近10条记录
        }

    async def batch_audit(self, contents: List[str]) -> List[Dict[str, Any]]:
        """批量审核"""
        results = []
        for content in contents:
            result = await self.audit_content(content)
            results.append(result)
        return results


    async def gate_for_school_agent(self, content: str) -> Dict[str, Any]:
        """
        审核并为学校智能体输出路由决策。
        - 无不当言论: 直接放行，返回 should_answer=True 与原始内容。
        - 存在不当言论: 拦截，返回 should_answer=False 与提示文案。
        """
        audit = await self.audit_content(content)
        if audit.get("is_safe", True):
            return {
                "should_answer": True,
                "agent_input": content,
                "message_to_user": "",
                "audit": audit,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            block_msg = self._build_block_message(audit)
            return {
                "should_answer": False,
                "agent_input": None,
                "message_to_user": block_msg,
                "audit": audit,
                "timestamp": datetime.now().isoformat(),
            }

    def _build_block_message(self, audit: Dict[str, Any]) -> str:
        """
        根据审核结果的风险级别生成拦截提示文案。
        """
        risk_level = audit.get("risk_level", "unknown")
        if risk_level == "high":
            message = "您的问题包含不当内容，无法处理。请确保问题内容符合校园规范。"
        elif risk_level == "medium":
            message = "您的问题可能包含敏感内容，建议重新表述后再次提问。"
        else:
            # 去掉“需要进一步审核”的文案，统一采用中风险提示
            message = "您的问题可能包含敏感内容，建议重新表述后再次提问。"

        # 不展示违规类型摘要，保护隐私与降低敏感信息暴露
        return message


    # 在敏感词初始化之后新增：
    def _initialize_regex_rules(self):
        """初始化基于正则的敏感规则，覆盖常见变体与短语组合"""
        self.regex_rules = [
            {
                "pattern": re.compile(r"(打|殴|揍|踢|砍|捅)[^，。,.！!？?]{0,4}(他|她|人)"),
                "type": "暴力行为",
                "severity": "high",
            },
            {
                "pattern": re.compile(r"(弄死|干掉|杀了|砍死|捅死|刀捅)"),
                "type": "暴力威胁",
                "severity": "high",
            },
            {
                "pattern": re.compile(r"(辱|骂|侮|嘲|贬|讥)[^，。,.！!？?]{0,3}(他|她|人)"),
                "type": "不当言论",
                "severity": "medium",
            },
            {
                "pattern": re.compile(r"(代写|代考|买论文|卖答案|泄题|枪手)"),
                "type": "学术不端",
                "severity": "high",
            },
        ]