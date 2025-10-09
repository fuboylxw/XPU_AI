"""
安全审核智能体模块
实现内容过滤、敏感词检测、政治敏感等安全审核功能
"""

import re
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from config.settings import settings
from src.chatbi.utils.logger import setup_logger

logger = setup_logger("security_audit_agent")

class SecurityAuditAgent:
    """安全审核智能体"""
    
    def __init__(self):
        """初始化安全审核智能体"""
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_MODEL_BASE_URL,
            temperature=0.1  # 使用较低温度确保一致性
        )
        
        # 初始化敏感词库
        self._initialize_sensitive_words()
        
        # 初始化审核提示词
        self._initialize_audit_prompts()
        
        # 审核日志
        self.audit_logs = []
    
    def _initialize_sensitive_words(self):
        """初始化敏感词库"""
        # 政治敏感词
        self.political_sensitive_words = [
            "政治敏感", "反政府", "颠覆", "分裂", "独立",
            "暴力", "恐怖", "极端", "仇恨", "歧视"
        ]
        
        # 违规内容词汇
        self.violation_words = [
            "作弊", "代考", "买卖答案", "学术不端", "抄袭",
            "暴力", "威胁", "恶意攻击", "人身攻击", "诽谤"
        ]
        
        # 不当言论
        self.inappropriate_words = [
            "脏话", "侮辱", "谩骂", "人身攻击", "恶意中伤",
            "色情", "赌博", "毒品", "违法"
        ]
        
        # 学术不端相关
        self.academic_misconduct_words = [
            "代写", "代考", "买论文", "卖答案", "考试作弊",
            "抄袭", "剽窃", "学术造假", "数据造假"
        ]
    
    def _initialize_audit_prompts(self):
        """初始化审核提示词"""
        self.content_audit_prompt = ChatPromptTemplate.from_template("""
你是一个专业的内容安全审核助手。请对以下内容进行全面的安全审核：

内容：{content}

请从以下维度进行审核：
1. 政治敏感性：是否包含政治敏感、反政府、分裂等内容
2. 违法违规：是否涉及违法犯罪、暴力恐怖等内容  
3. 学术诚信：是否涉及学术不端、作弊、代考等行为
4. 言论规范：是否包含不当言论、人身攻击、恶意中伤
5. 内容合规：是否符合教育环境和校园文化要求

请返回JSON格式的审核结果：
{{
    "is_safe": true/false,
    "risk_level": "low/medium/high",
    "violations": [
        {{
            "type": "违规类型",
            "description": "具体描述",
            "severity": "low/medium/high"
        }}
    ],
    "suggestions": "改进建议",
    "filtered_content": "过滤后的内容（如需要）"
}}
""")
        
        self.context_audit_prompt = ChatPromptTemplate.from_template("""
你是一个上下文安全审核助手。请结合对话上下文分析内容的安全性：

历史对话：{context}
当前内容：{content}

请分析：
1. 结合上下文，当前内容是否存在安全风险
2. 是否存在诱导性、误导性信息
3. 是否符合教育场景的对话规范

返回JSON格式结果：
{{
    "is_safe": true/false,
    "context_risk": "low/medium/high", 
    "analysis": "上下文分析结果",
    "recommendations": "建议"
}}
""")
    
    async def audit_content(self, content: str, context: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        对内容进行安全审核
        
        Args:
            content: 待审核的内容
            context: 对话上下文（可选）
            
        Returns:
            审核结果
        """
        try:
            logger.info(f"开始安全审核: {content[:50]}...")
            
            # 1. 基础敏感词检测
            keyword_result = self._check_sensitive_keywords(content)
            
            # 2. AI内容审核
            ai_result = await self._ai_content_audit(content)
            
            # 3. 上下文审核（如果有上下文）
            context_result = None
            if context:
                context_result = await self._context_audit(content, context)
            
            # 4. 综合审核结果
            final_result = self._combine_audit_results(
                keyword_result, ai_result, context_result
            )
            
            # 5. 记录审核日志
            self._log_audit_result(content, final_result)
            
            return final_result
            
        except Exception as e:
            logger.error(f"安全审核失败: {e}")
            return {
                "is_safe": False,
                "risk_level": "high",
                "error": f"审核过程出错: {str(e)}",
                "filtered_content": content
            }
    
    def _check_sensitive_keywords(self, content: str) -> Dict[str, Any]:
        """检查敏感关键词"""
        violations = []
        
        # 检查政治敏感词
        for word in self.political_sensitive_words:
            if word in content:
                violations.append({
                    "type": "政治敏感",
                    "keyword": word,
                    "severity": "high"
                })
        
        # 检查违规内容
        for word in self.violation_words:
            if word in content:
                violations.append({
                    "type": "违规内容", 
                    "keyword": word,
                    "severity": "medium"
                })
        
        # 检查不当言论
        for word in self.inappropriate_words:
            if word in content:
                violations.append({
                    "type": "不当言论",
                    "keyword": word, 
                    "severity": "medium"
                })
        
        # 检查学术不端
        for word in self.academic_misconduct_words:
            if word in content:
                violations.append({
                    "type": "学术不端",
                    "keyword": word,
                    "severity": "high"
                })
        
        # 判断风险等级
        if any(v["severity"] == "high" for v in violations):
            risk_level = "high"
            is_safe = False
        elif any(v["severity"] == "medium" for v in violations):
            risk_level = "medium" 
            is_safe = False
        else:
            risk_level = "low"
            is_safe = True
        
        return {
            "method": "keyword_check",
            "is_safe": is_safe,
            "risk_level": risk_level,
            "violations": violations
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
                "error": str(e)
            }
    
    async def _context_audit(self, content: str, context: List[str]) -> Dict[str, Any]:
        """上下文审核"""
        try:
            context_str = "\n".join(context[-5:])  # 取最近5条对话
            chain = self.context_audit_prompt | self.llm | JsonOutputParser()
            result = await chain.ainvoke({
                "content": content,
                "context": context_str
            })
            result["method"] = "context_audit"
            return result
        except Exception as e:
            logger.error(f"上下文审核失败: {e}")
            return {
                "method": "context_audit",
                "is_safe": True,
                "context_risk": "low",
                "error": str(e)
            }
    
    def _combine_audit_results(self, keyword_result: Dict, ai_result: Dict, 
                             context_result: Optional[Dict] = None) -> Dict[str, Any]:
        """综合审核结果"""
        # 收集所有违规信息
        all_violations = []
        
        if keyword_result.get("violations"):
            all_violations.extend(keyword_result["violations"])
        
        if ai_result.get("violations"):
            all_violations.extend(ai_result["violations"])
        
        # 确定最终安全状态
        is_safe = (keyword_result.get("is_safe", True) and 
                  ai_result.get("is_safe", True))
        
        if context_result:
            is_safe = is_safe and context_result.get("is_safe", True)
        
        # 确定风险等级
        risk_levels = [
            keyword_result.get("risk_level", "low"),
            ai_result.get("risk_level", "low")
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
                "context_audit": context_result
            },
            "filtered_content": filtered_content,
            "suggestions": ai_result.get("suggestions", ""),
            "timestamp": datetime.now().isoformat()
        }
    
    def _filter_content_by_keywords(self, content: str) -> str:
        """基于关键词过滤内容"""
        filtered = content
        
        # 替换敏感词
        all_sensitive_words = (self.political_sensitive_words + 
                             self.violation_words + 
                             self.inappropriate_words + 
                             self.academic_misconduct_words)
        
        for word in all_sensitive_words:
            if word in filtered:
                filtered = filtered.replace(word, "*" * len(word))
        
        return filtered
    
    def _log_audit_result(self, content: str, result: Dict[str, Any]):
        """记录审核日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "content_preview": content[:100],
            "is_safe": result["is_safe"],
            "risk_level": result["risk_level"],
            "violations_count": len(result.get("violations", [])),
            "audit_id": f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
            "recent_audits": self.audit_logs[-10:]  # 最近10条记录
        }
    
    async def batch_audit(self, contents: List[str]) -> List[Dict[str, Any]]:
        """批量审核"""
        results = []
        for content in contents:
            result = await self.audit_content(content)
            results.append(result)
        return results