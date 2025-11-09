"""
数据查询智能体模块
实现权限控制的数据查询、多层级权限管理、数据安全等功能
"""

import json
import hashlib
import pymysql
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

from config.settings import settings
from src.Chatbot.tools.document_manager import DocumentManager
from src.Chatbot.utils.logger import setup_logger

logger = setup_logger("data_query_agent")


class UserRole(Enum):
    """用户角色枚举"""

    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"
    GUEST = "guest"


class DataSensitivity(Enum):
    """数据敏感级别"""

    PUBLIC = "public"  # 公开数据
    INTERNAL = "internal"  # 内部数据
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
            temperature=0.1,  # 数据查询需要较低的随机性
        )

        # 初始化文档管理器（包含数据库查询功能）
        self.document_manager = DocumentManager()

        # 初始化权限信息数据库连接
        self._initialize_permission_db()

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

    def _initialize_permission_db(self):
        """初始化权限信息数据库连接"""
        try:
            # 直接使用配置值，确保连接成功
            self.permission_db_config = {
                'host': '172.26.52.198',
                'port': 3306,
                'user': 'root',
                'password': '83169142',
                'database': 'personal_information',
                'charset': 'utf8mb4',
                'autocommit': True
            }
            
            # 测试数据库连接
            connection = pymysql.connect(**self.permission_db_config)
            connection.close()
            logger.info("权限信息数据库连接初始化成功")
            
        except Exception as e:
            logger.error(f"权限信息数据库连接初始化失败: {e}")
            raise e

    def _initialize_permission_system(self):
        """初始化权限系统"""
        # 角色权限映射
        self.role_permissions = {
            UserRole.GUEST: {
                "allowed_data_types": [DataSensitivity.PUBLIC],
                "max_records": 10,
                "allowed_operations": ["SELECT"],
                "time_restrictions": {"daily_queries": 20},
            },
            UserRole.STUDENT: {
                "allowed_data_types": [
                    DataSensitivity.PUBLIC,
                    DataSensitivity.INTERNAL,
                ],
                "max_records": 50,
                "allowed_operations": ["SELECT"],
                "time_restrictions": {"daily_queries": 100},
                "personal_data_access": True,  # 可以访问自己的数据
            },
            UserRole.TEACHER: {
                "allowed_data_types": [
                    DataSensitivity.PUBLIC,
                    DataSensitivity.INTERNAL,
                    DataSensitivity.CONFIDENTIAL,
                ],
                "max_records": 200,
                "allowed_operations": ["SELECT", "INSERT", "UPDATE"],
                "time_restrictions": {"daily_queries": 500},
                "personal_data_access": True,
                "class_data_access": True,  # 可以访问所教班级的数据
            },
            UserRole.ADMIN: {
                "allowed_data_types": list(DataSensitivity),
                "max_records": 1000,
                "allowed_operations": ["SELECT", "INSERT", "UPDATE", "DELETE"],
                "time_restrictions": {"daily_queries": 2000},
                "full_access": True,
            },
        }

        # 数据表权限配置
        self.table_permissions = {
            "students": {
                "sensitivity": DataSensitivity.CONFIDENTIAL,
                "personal_fields": ["student_id", "name", "phone", "email"],
                "public_fields": ["major", "grade", "class"],
                "restricted_fields": ["id_card", "family_info", "financial_status"],
            },
            "teachers": {
                "sensitivity": DataSensitivity.CONFIDENTIAL,
                "personal_fields": ["teacher_id", "name", "department"],
                "public_fields": ["title", "research_area"],
                "restricted_fields": ["salary", "personal_info"],
            },
            "courses": {
                "sensitivity": DataSensitivity.INTERNAL,
                "public_fields": ["course_name", "credits", "description"],
                "internal_fields": ["enrollment_count", "pass_rate"],
            },
            "grades": {
                "sensitivity": DataSensitivity.CONFIDENTIAL,
                "personal_fields": ["student_id", "course_id", "score"],
                "restricted_fields": ["detailed_scores", "comments"],
            },
            "scholarships": {
                "sensitivity": DataSensitivity.INTERNAL,
                "public_fields": ["scholarship_name", "amount", "criteria"],
                "internal_fields": ["recipients", "selection_process"],
            },
        }

    def _initialize_data_classification(self):
        """初始化数据分类"""
        # 表权限配置 - 更新为实际的个人信息表
        self.table_permissions = {
            "students": {
                "sensitivity": DataSensitivity.CONFIDENTIAL,
                "allowed_roles": [UserRole.TEACHER, UserRole.ADMIN],
                "fields": {
                    "student_id": DataSensitivity.INTERNAL,
                    "name": DataSensitivity.CONFIDENTIAL,
                    "gender": DataSensitivity.INTERNAL,
                    "birth_date": DataSensitivity.CONFIDENTIAL,
                    "phone": DataSensitivity.CONFIDENTIAL,
                    "email": DataSensitivity.CONFIDENTIAL,
                    "address": DataSensitivity.CONFIDENTIAL,
                    "enrollment_date": DataSensitivity.INTERNAL,
                    "major": DataSensitivity.INTERNAL,
                    "class_name": DataSensitivity.INTERNAL,
                    "status": DataSensitivity.INTERNAL,
                },
                "personal_field": "student_id",  # 学生可以查看自己的信息
            },
            "teachers": {
                "sensitivity": DataSensitivity.CONFIDENTIAL,
                "allowed_roles": [UserRole.ADMIN],
                "fields": {
                    "teacher_id": DataSensitivity.INTERNAL,
                    "name": DataSensitivity.CONFIDENTIAL,
                    "gender": DataSensitivity.INTERNAL,
                    "birth_date": DataSensitivity.CONFIDENTIAL,
                    "phone": DataSensitivity.CONFIDENTIAL,
                    "email": DataSensitivity.CONFIDENTIAL,
                    "department": DataSensitivity.INTERNAL,
                    "position": DataSensitivity.INTERNAL,
                    "hire_date": DataSensitivity.INTERNAL,
                    "salary": DataSensitivity.RESTRICTED,
                },
                "personal_field": "teacher_id",  # 教师可以查看自己的信息
            },
            "courses": {
                "sensitivity": DataSensitivity.INTERNAL,
                "allowed_roles": [UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN],
                "fields": {
                    "course_id": DataSensitivity.PUBLIC,
                    "course_name": DataSensitivity.PUBLIC,
                    "teacher_id": DataSensitivity.INTERNAL,
                    "credits": DataSensitivity.PUBLIC,
                    "semester": DataSensitivity.PUBLIC,
                    "max_students": DataSensitivity.INTERNAL,
                    "current_students": DataSensitivity.INTERNAL,
                },
            },
            "grades": {
                "sensitivity": DataSensitivity.CONFIDENTIAL,
                "allowed_roles": [UserRole.TEACHER, UserRole.ADMIN],
                "fields": {
                    "grade_id": DataSensitivity.INTERNAL,
                    "student_id": DataSensitivity.CONFIDENTIAL,
                    "course_id": DataSensitivity.INTERNAL,
                    "score": DataSensitivity.CONFIDENTIAL,
                    "grade_letter": DataSensitivity.CONFIDENTIAL,
                    "exam_date": DataSensitivity.INTERNAL,
                },
                "personal_field": "student_id",  # 学生可以查看自己的成绩
            },
            "scholarships": {
                "sensitivity": DataSensitivity.CONFIDENTIAL,
                "allowed_roles": [UserRole.TEACHER, UserRole.ADMIN],
                "fields": {
                    "scholarship_id": DataSensitivity.INTERNAL,
                    "student_id": DataSensitivity.CONFIDENTIAL,
                    "scholarship_name": DataSensitivity.INTERNAL,
                    "amount": DataSensitivity.CONFIDENTIAL,
                    "award_date": DataSensitivity.INTERNAL,
                },
                "personal_field": "student_id",  # 学生可以查看自己的奖学金
            },
            "enrollment_stats": {
                "sensitivity": DataSensitivity.INTERNAL,
                "allowed_roles": [UserRole.TEACHER, UserRole.ADMIN],
                "fields": {
                    "stat_id": DataSensitivity.INTERNAL,
                    "year": DataSensitivity.PUBLIC,
                    "semester": DataSensitivity.PUBLIC,
                    "total_students": DataSensitivity.INTERNAL,
                    "new_enrollments": DataSensitivity.INTERNAL,
                    "graduations": DataSensitivity.INTERNAL,
                },
            },
        }

    def _initialize_prompts(self):
        """初始化提示词模板"""
        self.query_analysis_prompt = ChatPromptTemplate.from_template(
            """
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
"""
        )

        self.sql_generation_prompt = ChatPromptTemplate.from_template(
            """
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
"""
        )

        self.result_formatting_prompt = ChatPromptTemplate.from_template(
            """
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
"""
        )

    async def query_data(
        self,
        query: str,
        user_id: str,
        user_role: UserRole,
        session_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行数据查询"""
        try:
            logger.info(f"用户 {user_id}({user_role.value}) 发起数据查询: {query[:50]}...")

            # 0. 输入验证
            if not query or not query.strip():
                return {
                    "success": False,
                    "query": query,
                    "results": None,
                    "metadata": None,
                    "error": "查询内容不能为空",
                    "error_code": "EMPTY_QUERY",
                    "timestamp": datetime.now().isoformat(),
                }

            # 1. 验证用户会话
            if not self._validate_session(user_id, session_token):
                return {
                    "success": False,
                    "query": query,
                    "results": None,
                    "metadata": None,
                    "error": "会话无效或已过期，请重新登录",
                    "error_code": "INVALID_SESSION",
                    "timestamp": datetime.now().isoformat(),
                }

            # 2. 检查查询频率限制
            if not self._check_rate_limit(user_id, user_role):
                return {
                    "success": False,
                    "query": query,
                    "results": None,
                    "metadata": None,
                    "error": "查询频率超限，请稍后再试",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "timestamp": datetime.now().isoformat(),
                }

            # 3. 分析查询需求
            query_analysis = await self._analyze_query(query, user_role, user_id)

            # 4. 权限检查
            permission_check = self._check_permissions(
                query_analysis, user_role, user_id
            )
            if not permission_check["allowed"]:
                # 从query_analysis中移除requires_approval字段，避免Pydantic验证失败
                clean_query_analysis = {k: v for k, v in query_analysis.items() if k != "requires_approval"}
                return {
                    "success": False,
                    "query": query,
                    "results": None,
                    "error": permission_check["reason"],
                    "error_code": "PERMISSION_DENIED",
                    "metadata": {"query_analysis": clean_query_analysis},
                    "timestamp": datetime.now().isoformat(),
                }

            # 5. 生成安全的SQL查询
            sql_result = await self._generate_safe_sql(query, user_role, query_analysis)
            if not sql_result.get("execution_safe", False):
                return {
                    "success": False,
                    "query": query,
                    "results": None,
                    "error": "查询存在安全风险，无法执行",
                    "error_code": "SECURITY_RISK",
                    "metadata": {"sql_analysis": sql_result},
                    "timestamp": datetime.now().isoformat(),
                }

            # 6. 执行查询
            execution_result = await self._execute_query(
                sql_result["sql_query"], user_role
            )

            # 7. 格式化结果
            formatted_result = await self._format_results(
                query, execution_result, user_role
            )

            # 8. 记录审计日志
            self._log_query_audit(
                user_id, user_role, query, sql_result, execution_result
            )

            return {
                "success": True,
                "query": query,
                "results": formatted_result,
                "metadata": {
                    "query_analysis": {k: v for k, v in query_analysis.items() if k != "requires_approval"},
                    "sql_generated": sql_result["sql_query"],
                    "records_returned": len(execution_result.get("data", [])),
                    "execution_time": execution_result.get("execution_time", 0),
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"数据查询失败: {e}")
            # 记录错误日志
            self._log_query_error(user_id, user_role, query, str(e))

            return {
                "success": False,
                "query": query,
                "results": None,
                "metadata": None,
                "error": f"查询执行失败: {str(e)}",
                "error_code": "EXECUTION_ERROR",
                "timestamp": datetime.now().isoformat(),
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
            log
            for log in self.query_history
            if log["user_id"] == user_id
            and datetime.fromisoformat(log["timestamp"]).date() == today
        ]

        return len(today_queries) < daily_limit

    async def _analyze_query(
        self, query: str, user_role: UserRole, user_id: str
    ) -> Dict[str, Any]:
        """分析查询需求"""
        try:
            chain = self.query_analysis_prompt | self.llm | JsonOutputParser()
            analysis = await chain.ainvoke(
                {"query": query, "user_role": user_role.value, "user_id": user_id}
            )
            # 确保返回的分析结果包含requires_approval字段，用于后续权限检查
            if "requires_approval" not in analysis:
                analysis["requires_approval"] = False
            return analysis
        except Exception as e:
            logger.error(f"查询分析失败: {e}")
            return {
                "query_intent": "未知查询意图",
                "target_tables": [],
                "target_fields": [],
                "data_sensitivity": "public",
                "security_risks": ["分析失败"],
                "requires_approval": False,
            }

    def _check_permissions(
        self, query_analysis: Dict[str, Any], user_role: UserRole, user_id: str
    ) -> Dict[str, bool]:
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
                "reason": f"用户角色 {user_role.value} 无权访问 {sensitivity_enum.value} 级别的数据",
            }

        # 检查表权限
        target_tables = query_analysis.get("target_tables", [])
        for table in target_tables:
            if table in self.table_permissions:
                table_sensitivity = self.table_permissions[table]["sensitivity"]
                if table_sensitivity not in permissions["allowed_data_types"]:
                    return {
                        "allowed": False,
                        "reason": f"无权访问表 {table}（敏感级别：{table_sensitivity.value}）",
                    }

        # 检查是否需要特殊审批
        if (
            query_analysis.get("requires_approval", False)
            and user_role != UserRole.ADMIN
        ):
            return {"allowed": False, "reason": "该查询需要管理员审批"}

        return {"allowed": True, "reason": "权限检查通过"}

    async def _generate_safe_sql(
        self, query: str, user_role: UserRole, query_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成安全的SQL查询"""
        try:
            permissions = self.role_permissions[user_role]

            # 构建表结构信息（简化版）
            table_schema = {}
            for table in query_analysis.get("target_tables", []):
                if table in self.table_permissions:
                    table_schema[table] = self.table_permissions[table]

            chain = self.sql_generation_prompt | self.llm | JsonOutputParser()
            sql_result = await chain.ainvoke(
                {
                    "user_query": query,
                    "user_role": user_role.value,
                    "permissions": json.dumps(permissions, default=str),
                    "table_schema": json.dumps(table_schema, default=str),
                }
            )

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
                "error": str(e),
            }

    async def _execute_query(
        self, sql_query: str, user_role: UserRole
    ) -> Dict[str, Any]:
        """执行查询 - 使用权限信息数据库"""
        try:
            start_time = datetime.now()

            # 使用权限信息数据库执行SQL
            result = self._execute_permission_db_query(sql_query)

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            return {
                "success": True,
                "data": result if isinstance(result, list) else [result],
                "execution_time": execution_time,
                "sql_query": sql_query,
            }

        except Exception as e:
            logger.error(f"SQL执行失败: {e}")
            return {"success": False, "error": str(e), "data": [], "execution_time": 0}

    def _execute_permission_db_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        执行权限信息数据库查询
        
        Args:
            sql_query: SQL查询语句
            
        Returns:
            查询结果列表
        """
        try:
            logger.info(f"执行权限信息数据库查询: {sql_query}")
            
            # 连接权限信息数据库
            connection = pymysql.connect(**self.permission_db_config)
            cursor = connection.cursor(pymysql.cursors.DictCursor)
            
            # 执行查询
            cursor.execute(sql_query)
            results = cursor.fetchall()
            
            # 关闭连接
            cursor.close()
            connection.close()
            
            logger.info(f"权限信息数据库查询完成，返回 {len(results)} 条记录")
            return results
            
        except Exception as e:
            logger.error(f"权限信息数据库查询执行失败: {e}")
            raise e

    def get_user_personal_id(self, user_id: str, user_role: UserRole) -> Optional[str]:
        """
        获取用户的个人ID（用于个人数据访问控制）
        
        Args:
            user_id: 用户ID
            user_role: 用户角色
            
        Returns:
            个人ID或None
        """
        try:
            if user_role == UserRole.STUDENT:
                # 假设用户ID就是学生ID，实际应用中可能需要查询用户表
                return user_id
            elif user_role == UserRole.TEACHER:
                # 假设用户ID就是教师ID，实际应用中可能需要查询用户表
                return user_id
            else:
                return None
                
        except Exception as e:
            logger.error(f"获取用户个人ID失败: {e}")
            return None

    async def _format_results(
        self, original_query: str, query_results: Dict[str, Any], user_role: UserRole
    ) -> str:
        """格式化查询结果"""
        try:
            if not query_results.get("success", False):
                return f"查询执行失败: {query_results.get('error', '未知错误')}"

            data = query_results.get("data", [])
            if not data:
                return "查询未返回任何结果"

            # 使用AI格式化结果
            chain = self.result_formatting_prompt | self.llm | StrOutputParser()
            formatted_result = await chain.ainvoke(
                {
                    "original_query": original_query,
                    "query_results": json.dumps(
                        data[:10], ensure_ascii=False
                    ),  # 只格式化前10条
                    "user_role": user_role.value,
                }
            )

            # 添加记录数信息
            total_records = len(data)
            if total_records > 10:
                formatted_result += f"\n\n注：共返回 {total_records} 条记录，以上显示前10条。"

            return formatted_result

        except Exception as e:
            logger.error(f"结果格式化失败: {e}")
            return f"结果格式化失败，原始数据：{str(query_results)[:500]}..."

    def _log_query_audit(
        self,
        user_id: str,
        user_role: UserRole,
        query: str,
        sql_result: Dict[str, Any],
        execution_result: Dict[str, Any],
    ):
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
            "audit_id": f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}",
        }

        self.audit_logs.append(audit_entry)
        self.query_history.append(audit_entry)

        logger.info(f"查询审计记录: {audit_entry['audit_id']}")

        # 保持日志数量在合理范围内
        if len(self.audit_logs) > 5000:
            self.audit_logs = self.audit_logs[-2500:]
        if len(self.query_history) > 2000:
            self.query_history = self.query_history[-1000:]

    def _log_query_error(
        self, user_id: str, user_role: UserRole, query: str, error: str
    ):
        """记录查询错误日志"""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "user_role": user_role.value,
            "query": query,
            "error": error,
            "type": "query_error",
        }

        self.audit_logs.append(error_entry)
        logger.error(f"查询错误记录: {error_entry}")

    def create_user_session(
        self, user_id: str, user_role: UserRole, session_duration_hours: int = 8
    ) -> str:
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
            "last_activity": datetime.now(),
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
            user_queries = [
                log for log in self.query_history if log["user_id"] == user_id
            ]
            if not user_queries:
                return {"message": f"用户 {user_id} 暂无查询记录"}

            total_queries = len(user_queries)
            successful_queries = sum(
                1 for log in user_queries if log.get("execution_success", False)
            )

            return {
                "user_id": user_id,
                "total_queries": total_queries,
                "successful_queries": successful_queries,
                "success_rate": f"{(successful_queries/total_queries)*100:.2f}%",
                "recent_queries": user_queries[-10:],
            }
        else:
            # 系统整体统计
            if not self.query_history:
                return {"message": "暂无查询记录"}

            total_queries = len(self.query_history)
            successful_queries = sum(
                1 for log in self.query_history if log.get("execution_success", False)
            )

            # 按角色统计
            role_stats = {}
            for log in self.query_history:
                role = log["user_role"]
                role_stats[role] = role_stats.get(role, 0) + 1

            # 按日期统计
            today = datetime.now().date()
            today_queries = sum(
                1
                for log in self.query_history
                if datetime.fromisoformat(log["timestamp"]).date() == today
            )

            return {
                "total_queries": total_queries,
                "successful_queries": successful_queries,
                "success_rate": f"{(successful_queries/total_queries)*100:.2f}%",
                "queries_today": today_queries,
                "role_distribution": role_stats,
                "active_sessions": len(self.user_sessions),
                "recent_queries": self.query_history[-10:],
            }