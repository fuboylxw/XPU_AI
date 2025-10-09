"""
数据查询智能体模块
实现权限控制的数据查询、多层级权限管理、数据安全等功能
"""

import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

from config.settings import settings
from src.chatbi.tools.query_tools import QueryTool
from src.chatbi.utils.logger import setup_logger

logger = setup_logger("data_query_agent")

class UserRole(Enum):
    """用户角色枚举"""
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"
    GUEST = "guest"

class DataSensitivity(Enum):
    """数据敏感级别"""
    PUBLIC = "public"          # 公开数据
    INTERNAL = "internal"      # 内部数据
    CONFIDENTIAL = "confidential"  # 机密数据
    RESTRICTED = "restricted"  # 限制数据

class DataQueryAgent:
    """数据查询智能体"""
    
    def __init__(self):
        """初始化数据查询智能体"""
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_MODEL_BASE_URL,
            temperature=0.1  # 数据查询需要较低的随机性
        )
        
        # 初始化查询工具
        self.query_tool = QueryTool()
        
        # 初始化权限系统
        self._initialize_permission_system()
        
        # 初始化数据分类
        self._initialize_data_classification()
        
        # 初始化提示词模板
        self._initialize_prompts()
        
        # 查询历史和审计日志
        self.query_history = []
        self.audit_logs = []
        
        # 用户会话管理
        self.user_sessions = {}
    
    def _initialize_permission_system(self):
        """初始化权限系统"""
        # 角色权限映射
        self.role_permissions = {
            UserRole.GUEST: {
                "allowed_data_types": [DataSensitivity.PUBLIC],
                "max_records": 10,
                "allowed_operations": ["SELECT"],
                "time_restrictions": {"daily_queries": 20}
            },
            UserRole.STUDENT: {
                "allowed_data_types": [DataSensitivity.PUBLIC, DataSensitivity.INTERNAL],
                "max_records": 50,
                "allowed_operations": ["SELECT"],
                "time_restrictions": {"daily_queries": 100},
                "personal_data_access": True  # 可以访问自己的数据
            },
            UserRole.TEACHER: {
                "allowed_data_types": [DataSensitivity.PUBLIC, DataSensitivity.INTERNAL, DataSensitivity.CONFIDENTIAL],
                "max_records": 200,
                "allowed_operations": ["SELECT", "INSERT", "UPDATE"],
                "time_restrictions": {"daily_queries": 500},
                "personal_data_access": True,
                "class_data_access": True  # 可以访问所教班级的数据
            },
            UserRole.ADMIN: {
                "allowed_data_types": list(DataSensitivity),
                "max_records": 1000,
                "allowed_operations": ["SELECT", "INSERT", "UPDATE", "DELETE"],
                "time_restrictions": {"daily_queries": 2000},
                "full_access": True
            }
        }
        
        # 数据表权限配置
        self.table_permissions = {
            "students": {
                "sensitivity": DataSensitivity.CONFIDENTIAL,
                "personal_fields": ["student_id", "name", "phone", "email"],
                "public_fields": ["major", "grade", "class"],
                "restricted_fields": ["id_card", "family_info", "financial_status"]
            },
            "teachers": {
                "sensitivity": DataSensitivity.CONFIDENTIAL,
                "personal_fields": ["teacher_id", "name", "department"],
                "public_fields": ["title", "research_area"],
                "restricted_fields": ["salary", "personal_info"]
            },
            "courses": {
                "sensitivity": DataSensitivity.INTERNAL,
                "public_fields": ["course_name", "credits", "description"],
                "internal_fields": ["enrollment_count", "pass_rate"]
            },
            "grades": {
                "sensitivity": DataSensitivity.CONFIDENTIAL,
                "personal_fields": ["student_id", "course_id", "score"],
                "restricted_fields": ["detailed_scores", "comments"]
            },
            "scholarships": {
                "sensitivity": DataSensitivity.INTERNAL,
                "public_fields": ["scholarship_name", "amount", "criteria"],
                "internal_fields": ["recipients", "selection_process"]
            }
        }
    
    def _initialize_data_classification(self):
        """初始化数据分类"""
        self.data_categories = {
            "学生信息": {
                "tables": ["students", "student_status", "student_records"],
                "sensitivity": DataSensitivity.CONFIDENTIAL,
                "description": "学生个人信息、学籍状态等"
            },
            "教师信息": {
                "tables": ["teachers", "teacher_profiles", "staff_info"],
                "sensitivity": DataSensitivity.CONFIDENTIAL,
                "description": "教师个人信息、职务等"
            },
            "课程信息": {
                "tables": ["courses", "course_schedules", "syllabi"],
                "sensitivity": DataSensitivity.INTERNAL,
                "description": "课程设置、课程表、教学大纲"
            },
            "成绩信息": {
                "tables": ["grades", "exam_results", "assessments"],
                "sensitivity": DataSensitivity.CONFIDENTIAL,
                "description": "学生成绩、考试结果、评估记录"
            },
            "财务信息": {
                "tables": ["tuition", "scholarships", "financial_aid"],
                "sensitivity": DataSensitivity.RESTRICTED,
                "description": "学费、奖学金、助学金等财务数据"
            },
            "统计数据": {
                "tables": ["enrollment_stats", "graduation_stats", "employment_stats"],
                "sensitivity": DataSensitivity.INTERNAL,
                "description": "招生、毕业、就业等统计数据"
            }
        }
    
    def _initialize_prompts(self):
        """初始化提示词模板"""
        self.query_analysis_prompt = ChatPromptTemplate.from_template("""
你是一个数据查询分析助手。请分析用户的查询需求并评估安全性。

用户查询：{query}
用户角色：{user_role}
用户ID：{user_id}

请分析：
1. 查询意图和目标数据
2. 涉及的数据表和字段
3. 数据敏感级别
4. 是否存在安全风险
5. 建议的查询策略

返回JSON格式：
{{
    "query_intent": "查询意图描述",
    "target_tables": ["涉及的数据表"],
    "target_fields": ["涉及的字段"],
    "data_sensitivity": "数据敏感级别",
    "security_risks": ["安全风险列表"],
    "recommended_strategy": "建议的查询策略",
    "requires_approval": true/false
}}
""")
        
        self.sql_generation_prompt = ChatPromptTemplate.from_template("""
你是一个SQL生成助手。请根据用户需求和权限限制生成安全的SQL查询。

用户需求：{user_query}
用户角色：{user_role}
权限限制：{permissions}
可用表结构：{table_schema}

生成要求：
1. 确保SQL语句安全，防止注入攻击
2. 遵守用户权限限制
3. 只查询允许的字段
4. 添加适当的数据过滤
5. 限制返回记录数

返回JSON格式：
{{
    "sql_query": "生成的SQL查询语句",
    "explanation": "查询说明",
    "security_measures": ["安全措施"],
    "estimated_records": "预估返回记录数",
    "execution_safe": true/false
}}
""")
        
        self.result_formatting_prompt = ChatPromptTemplate.from_template("""
请将数据查询结果格式化为用户友好的形式。

原始查询：{original_query}
查询结果：{query_results}
用户角色：{user_role}

格式化要求：
1. 隐藏敏感信息
2. 使用清晰的表格或列表格式
3. 添加必要的说明
4. 确保数据准确性

格式化结果：
""")
    
    async def query_data(self, query: str, user_id: str, user_role: UserRole, 
                        session_token: Optional[str] = None) -> Dict[str, Any]:
        """执行数据查询"""
        try:
            logger.info(f"用户 {user_id}({user_role.value}) 发起数据查询: {query[:50]}...")
            
            # 1. 验证用户会话
            if not self._validate_session(user_id, session_token):
                return {
                    "success": False,
                    "error": "会话无效或已过期，请重新登录",
                    "error_code": "INVALID_SESSION"
                }
            
            # 2. 检查查询频率限制
            if not self._check_rate_limit(user_id, user_role):
                return {
                    "success": False,
                    "error": "查询频率超限，请稍后再试",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                }
            
            # 3. 分析查询需求
            query_analysis = await self._analyze_query(query, user_role, user_id)
            
            # 4. 权限检查
            permission_check = self._check_permissions(query_analysis, user_role, user_id)
            if not permission_check["allowed"]:
                return {
                    "success": False,
                    "error": permission_check["reason"],
                    "error_code": "PERMISSION_DENIED",
                    "query_analysis": query_analysis
                }
            
            # 5. 生成安全的SQL查询
            sql_result = await self._generate_safe_sql(query, user_role, query_analysis)
            if not sql_result.get("execution_safe", False):
                return {
                    "success": False,
                    "error": "查询存在安全风险，无法执行",
                    "error_code": "SECURITY_RISK",
                    "sql_analysis": sql_result
                }
            
            # 6. 执行查询
            execution_result = await self._execute_query(sql_result["sql_query"], user_role)
            
            # 7. 格式化结果
            formatted_result = await self._format_results(
                query, execution_result, user_role
            )
            
            # 8. 记录审计日志
            self._log_query_audit(user_id, user_role, query, sql_result, execution_result)
            
            return {
                "success": True,
                "query": query,
                "results": formatted_result,
                "metadata": {
                    "query_analysis": query_analysis,
                    "sql_generated": sql_result["sql_query"],
                    "records_returned": len(execution_result.get("data", [])),
                    "execution_time": execution_result.get("execution_time", 0)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"数据查询失败: {e}")
            # 记录错误日志
            self._log_query_error(user_id, user_role, query, str(e))
            
            return {
                "success": False,
                "error": f"查询执行失败: {str(e)}",
                "error_code": "EXECUTION_ERROR",
                "timestamp": datetime.now().isoformat()
            }
    
    def _validate_session(self, user_id: str, session_token: Optional[str]) -> bool:
        """验证用户会话"""
        if not session_token:
            return False
        
        session_info = self.user_sessions.get(user_id)
        if not session_info:
            return False
        
        # 检查会话令牌
        if session_info["token"] != session_token:
            return False
        
        # 检查会话是否过期
        if datetime.now() > session_info["expires_at"]:
            del self.user_sessions[user_id]
            return False
        
        # 更新最后活动时间
        session_info["last_activity"] = datetime.now()
        return True
    
    def _check_rate_limit(self, user_id: str, user_role: UserRole) -> bool:
        """检查查询频率限制"""
        permissions = self.role_permissions[user_role]
        daily_limit = permissions["time_restrictions"]["daily_queries"]
        
        # 统计今日查询次数
        today = datetime.now().date()
        today_queries = [
            log for log in self.query_history
            if log["user_id"] == user_id and 
            datetime.fromisoformat(log["timestamp"]).date() == today
        ]
        
        return len(today_queries) < daily_limit
    
    async def _analyze_query(self, query: str, user_role: UserRole, user_id: str) -> Dict[str, Any]:
        """分析查询需求"""
        try:
            chain = self.query_analysis_prompt | self.llm | JsonOutputParser()
            analysis = await chain.ainvoke({
                "query": query,
                "user_role": user_role.value,
                "user_id": user_id
            })
            return analysis
        except Exception as e:
            logger.error(f"查询分析失败: {e}")
            return {
                "query_intent": "未知查询意图",
                "target_tables": [],
                "target_fields": [],
                "data_sensitivity": "unknown",
                "security_risks": ["分析失败"],
                "requires_approval": True
            }
    
    def _check_permissions(self, query_analysis: Dict[str, Any], 
                          user_role: UserRole, user_id: str) -> Dict[str, bool]:
        """检查用户权限"""
        permissions = self.role_permissions[user_role]
        
        # 检查数据敏感级别权限
        data_sensitivity = query_analysis.get("data_sensitivity", "restricted")
        try:
            sensitivity_enum = DataSensitivity(data_sensitivity.lower())
        except ValueError:
            sensitivity_enum = DataSensitivity.RESTRICTED
        
        if sensitivity_enum not in permissions["allowed_data_types"]:
            return {
                "allowed": False,
                "reason": f"用户角色 {user_role.value} 无权访问 {sensitivity_enum.value} 级别的数据"
            }
        
        # 检查表权限
        target_tables = query_analysis.get("target_tables", [])
        for table in target_tables:
            if table in self.table_permissions:
                table_sensitivity = self.table_permissions[table]["sensitivity"]
                if table_sensitivity not in permissions["allowed_data_types"]:
                    return {
                        "allowed": False,
                        "reason": f"无权访问表 {table}（敏感级别：{table_sensitivity.value}）"
                    }
        
        # 检查是否需要特殊审批
        if query_analysis.get("requires_approval", False) and user_role != UserRole.ADMIN:
            return {
                "allowed": False,
                "reason": "该查询需要管理员审批"
            }
        
        return {"allowed": True, "reason": "权限检查通过"}
    
    async def _generate_safe_sql(self, query: str, user_role: UserRole, 
                               query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成安全的SQL查询"""
        try:
            permissions = self.role_permissions[user_role]
            
            # 构建表结构信息（简化版）
            table_schema = {}
            for table in query_analysis.get("target_tables", []):
                if table in self.table_permissions:
                    table_schema[table] = self.table_permissions[table]
            
            chain = self.sql_generation_prompt | self.llm | JsonOutputParser()
            sql_result = await chain.ainvoke({
                "user_query": query,
                "user_role": user_role.value,
                "permissions": json.dumps(permissions, default=str),
                "table_schema": json.dumps(table_schema, default=str)
            })
            
            # 添加记录数限制
            sql_query = sql_result.get("sql_query", "")
            max_records = permissions["max_records"]
            
            if "LIMIT" not in sql_query.upper():
                sql_query += f" LIMIT {max_records}"
                sql_result["sql_query"] = sql_query
            
            return sql_result
            
        except Exception as e:
            logger.error(f"SQL生成失败: {e}")
            return {
                "sql_query": "",
                "explanation": "SQL生成失败",
                "execution_safe": False,
                "error": str(e)
            }
    
    async def _execute_query(self, sql_query: str, user_role: UserRole) -> Dict[str, Any]:
        """执行查询"""
        try:
            start_time = datetime.now()
            
            # 使用查询工具执行SQL
            result = self.query_tool._execute_sql_query(sql_query)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                "success": True,
                "data": result if isinstance(result, list) else [result],
                "execution_time": execution_time,
                "sql_query": sql_query
            }
            
        except Exception as e:
            logger.error(f"SQL执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "execution_time": 0
            }
    
    async def _format_results(self, original_query: str, query_results: Dict[str, Any], 
                            user_role: UserRole) -> str:
        """格式化查询结果"""
        try:
            if not query_results.get("success", False):
                return f"查询执行失败: {query_results.get('error', '未知错误')}"
            
            data = query_results.get("data", [])
            if not data:
                return "查询未返回任何结果"
            
            # 使用AI格式化结果
            chain = self.result_formatting_prompt | self.llm | StrOutputParser()
            formatted_result = await chain.ainvoke({
                "original_query": original_query,
                "query_results": json.dumps(data[:10], ensure_ascii=False),  # 只格式化前10条
                "user_role": user_role.value
            })
            
            # 添加记录数信息
            total_records = len(data)
            if total_records > 10:
                formatted_result += f"\n\n注：共返回 {total_records} 条记录，以上显示前10条。"
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"结果格式化失败: {e}")
            return f"结果格式化失败，原始数据：{str(query_results)[:500]}..."
    
    def _log_query_audit(self, user_id: str, user_role: UserRole, query: str, 
                        sql_result: Dict[str, Any], execution_result: Dict[str, Any]):
        """记录查询审计日志"""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "user_role": user_role.value,
            "original_query": query,
            "generated_sql": sql_result.get("sql_query", ""),
            "execution_success": execution_result.get("success", False),
            "records_returned": len(execution_result.get("data", [])),
            "execution_time": execution_result.get("execution_time", 0),
            "audit_id": f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}"
        }
        
        self.audit_logs.append(audit_entry)
        self.query_history.append(audit_entry)
        
        logger.info(f"查询审计记录: {audit_entry['audit_id']}")
        
        # 保持日志数量在合理范围内
        if len(self.audit_logs) > 5000:
            self.audit_logs = self.audit_logs[-2500:]
        if len(self.query_history) > 2000:
            self.query_history = self.query_history[-1000:]
    
    def _log_query_error(self, user_id: str, user_role: UserRole, query: str, error: str):
        """记录查询错误日志"""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "user_role": user_role.value,
            "query": query,
            "error": error,
            "type": "query_error"
        }
        
        self.audit_logs.append(error_entry)
        logger.error(f"查询错误记录: {error_entry}")
    
    def create_user_session(self, user_id: str, user_role: UserRole, 
                           session_duration_hours: int = 8) -> str:
        """创建用户会话"""
        session_token = hashlib.sha256(
            f"{user_id}_{datetime.now().isoformat()}_{user_role.value}".encode()
        ).hexdigest()
        
        expires_at = datetime.now() + timedelta(hours=session_duration_hours)
        
        self.user_sessions[user_id] = {
            "token": session_token,
            "user_role": user_role,
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "last_activity": datetime.now()
        }
        
        logger.info(f"为用户 {user_id} 创建会话，过期时间: {expires_at}")
        return session_token
    
    def revoke_user_session(self, user_id: str):
        """撤销用户会话"""
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            logger.info(f"用户 {user_id} 的会话已撤销")
    
    def get_query_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取查询统计信息"""
        if user_id:
            # 用户个人统计
            user_queries = [log for log in self.query_history if log["user_id"] == user_id]
            if not user_queries:
                return {"message": f"用户 {user_id} 暂无查询记录"}
            
            total_queries = len(user_queries)
            successful_queries = sum(1 for log in user_queries if log.get("execution_success", False))
            
            return {
                "user_id": user_id,
                "total_queries": total_queries,
                "successful_queries": successful_queries,
                "success_rate": f"{(successful_queries/total_queries)*100:.2f}%",
                "recent_queries": user_queries[-10:]
            }
        else:
            # 系统整体统计
            if not self.query_history:
                return {"message": "暂无查询记录"}
            
            total_queries = len(self.query_history)
            successful_queries = sum(1 for log in self.query_history if log.get("execution_success", False))
            
            # 按角色统计
            role_stats = {}
            for log in self.query_history:
                role = log["user_role"]
                role_stats[role] = role_stats.get(role, 0) + 1
            
            # 按日期统计
            today = datetime.now().date()
            today_queries = sum(1 for log in self.query_history 
                              if datetime.fromisoformat(log["timestamp"]).date() == today)
            
            return {
                "total_queries": total_queries,
                "successful_queries": successful_queries,
                "success_rate": f"{(successful_queries/total_queries)*100:.2f}%",
                "queries_today": today_queries,
                "role_distribution": role_stats,
                "active_sessions": len(self.user_sessions),
                "recent_queries": self.query_history[-10:]
            }