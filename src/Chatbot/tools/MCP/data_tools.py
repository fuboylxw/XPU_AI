from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional
import asyncio


# 描述与输入模式供注册使用
DB_QUERY_DESCRIPTION = "Permission-based user data query (grades/schedule) via MySQL/Redis."
DB_QUERY_INPUT_SCHEMA = {
    "engine": "str",
    "resource": "str",  # student_grades | student_schedule | teacher_schedule
    "subject_user_id": "str",
    "request_user_id": "str",
    "request_role": "str",  # student | teacher | admin
    "term": "str?",
    "week": "int?",
    "limit": "int?",
    "key": "str?",
}


def build_db_query_runner():
    from src.Chatbot.utils.db_utils_updated import get_db_manager0

    def _authorize(resource: str, subject_user_id: str, request_user_id: str, request_role: str) -> bool:
        role = (request_role or "").lower()
        if role == "admin":
            return True
        if role == "student":
            return subject_user_id == request_user_id and resource in {"student_grades", "student_schedule"}
        if role == "teacher":
            return subject_user_id == request_user_id and resource in {"teacher_schedule"}
        return False

    def _build_sql(resource: str, subject_user_id: str, params: Dict[str, Any], role: str) -> Tuple[str, Tuple[Any, ...]]:
        limit = int(params.get("limit", 100))
        term = params.get("term")
        week = params.get("week")
        admin = (role or "").lower() == "admin"
        if resource == "student_grades":
            cols = "term, course_code, course_name, score, gpa" if not admin else "term, course_name, score"
            sql = f"SELECT {cols} FROM grades WHERE student_id = %s"
            args: Tuple[Any, ...] = (subject_user_id,)
            if term:
                sql += " AND term = %s"
                args = args + (term,)
            sql += " ORDER BY term DESC LIMIT %s"
            args = args + (limit,)
            return sql, args
        if resource == "student_schedule":
            cols = "day_of_week, start_time, end_time, course_name, classroom"
            sql = f"SELECT {cols} FROM schedule WHERE student_id = %s"
            args = (subject_user_id,)
            if week:
                sql += " AND week = %s"
                args = args + (week,)
            sql += " ORDER BY day_of_week, start_time LIMIT %s"
            args = args + (limit,)
            return sql, args
        if resource == "teacher_schedule":
            cols = "day_of_week, start_time, end_time, course_name, classroom"
            sql = f"SELECT {cols} FROM teacher_schedule WHERE teacher_id = %s"
            args = (subject_user_id,)
            if week:
                sql += " AND week = %s"
                args = args + (week,)
            sql += " ORDER BY day_of_week, start_time LIMIT %s"
            args = args + (limit,)
            return sql, args
        raise ValueError("Unsupported resource")

    async def db_query(params: Dict[str, Any]) -> Dict[str, Any]:
        engine = (params.get("engine") or "mysql").lower()
        resource = (params.get("resource") or "").strip()
        subject_user_id = (params.get("subject_user_id") or "").strip()
        request_user_id = (params.get("request_user_id") or "").strip()
        request_role = (params.get("request_role") or "").strip()
        if not resource or not subject_user_id or not request_user_id or not request_role:
            return {"success": False, "error": "Missing required params: resource/subject_user_id/request_user_id/request_role", "source": "db"}
        if not _authorize(resource, subject_user_id, request_user_id, request_role):
            return {"success": False, "error": "Unauthorized", "source": "db"}
        mgr = get_db_manager0()
        if engine == "mysql":
            try:
                sql, sql_args = _build_sql(resource, subject_user_id, params, request_role)
            except ValueError:
                return {"success": False, "error": "Unsupported resource", "source": "db_mysql"}
            try:
                conn = mgr.get_mysql_connection()
                def run_query() -> Tuple[bool, List[Dict[str, Any]], str]:
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute(sql, sql_args)
                            res = cursor.fetchall() or []
                            return True, res, ""
                    except Exception as qe:
                        return False, [], str(qe)
                loop = asyncio.get_event_loop()
                ok, res, err = await loop.run_in_executor(None, run_query)
                if not ok:
                    return {"success": False, "error": err, "source": "db_mysql"}
                return {"success": True, "results": res, "source": "db_mysql", "resource": resource}
            except Exception as e:
                return {"success": False, "error": str(e), "source": "db_mysql"}
        elif engine == "redis":
            key = params.get("key") or f"user:{subject_user_id}:{resource}"
            try:
                r = mgr.get_redis_connection()
                val = await asyncio.get_event_loop().run_in_executor(None, lambda: r.get(key))
                return {"success": True, "results": [{"key": key, "value": val}], "source": "db_redis", "resource": resource}
            except Exception as e:
                return {"success": False, "error": str(e), "source": "db_redis"}
        else:
            return {"success": False, "error": f"Unsupported engine: {engine}", "source": "db"}

    return db_query
