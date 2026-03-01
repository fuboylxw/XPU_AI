"""
工作会话/任务数据访问层
封装所有 WorkSession / WorkTask / WorkSubTask 的数据库操作
"""
import logging
from typing import List, Optional
from sqlalchemy.orm import Session

from fastapi_app.models import WorkSession, WorkTask, WorkSubTask


class WorkSessionRepository:
    """工作会话 Repository"""

    def __init__(self, db: Session):
        self.db = db

    # ── WorkSession ──

    def get_by_session_id(self, session_id: str) -> Optional[WorkSession]:
        return self.db.query(WorkSession).filter(
            WorkSession.session_id == session_id
        ).first()

    def get_by_id(self, task_id: int) -> Optional[WorkSession]:
        return self.db.query(WorkSession).filter(
            WorkSession.id == task_id
        ).first()

    def list_sessions(self, user_id: str = None,
                      session_id: str = None) -> List[WorkSession]:
        q = self.db.query(WorkSession)
        if user_id:
            q = q.filter(WorkSession.user_id == user_id)
        if session_id:
            q = q.filter(WorkSession.session_id == session_id)
        return q.order_by(WorkSession.updated_at.desc()).all()

    def create_session(self, session_id: str, user_id: str,
                       title: str = None, status: str = "loading") -> WorkSession:
        session = WorkSession(
            session_id=session_id,
            user_id=user_id,
            title=title,
            status=status,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def update_title(self, task_id: int, title: str) -> WorkSession:
        obj = self.get_by_id(task_id)
        if obj is None:
            raise ValueError("任务不存在")
        obj.title = title
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update_status(self, task_id: int, status: str) -> WorkSession:
        obj = self.get_by_id(task_id)
        if obj is None:
            raise ValueError("任务不存在")
        obj.status = status
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete_session(self, task_id: int) -> None:
        obj = self.get_by_id(task_id)
        if obj is None:
            raise ValueError("任务不存在")
        self.db.query(WorkSubTask).filter(
            WorkSubTask.session_id == obj.session_id
        ).delete(synchronize_session=False)
        self.db.query(WorkTask).filter(
            WorkTask.session_id == obj.session_id
        ).delete(synchronize_session=False)
        self.db.delete(obj)
        self.db.commit()

    # ── WorkTask ──

    def get_tasks_for_session(self, session_id: str) -> List[WorkTask]:
        return self.db.query(WorkTask).filter(
            WorkTask.session_id == session_id
        ).all()

    # ── WorkSubTask ──

    def get_subtasks_for_session(self, session_id: str) -> List[WorkSubTask]:
        return self.db.query(WorkSubTask).filter(
            WorkSubTask.session_id == session_id
        ).order_by(WorkSubTask.order).all()

    def get_subtask_by_id(self, subtask_id: int) -> Optional[WorkSubTask]:
        return self.db.query(WorkSubTask).filter(
            WorkSubTask.task_sub_id == subtask_id
        ).first()

    def update_subtask(self, subtask_id: int, sub_task_name: str = None,
                       status: str = None, result: str = None) -> WorkSubTask:
        subtask = self.get_subtask_by_id(subtask_id)
        if subtask is None:
            raise ValueError("子任务不存在")
        if sub_task_name:
            subtask.sub_task_name = sub_task_name
        if status:
            subtask.status = status
        if result is not None:
            subtask.result = result
        self.db.add(subtask)
        self.db.commit()
        self.db.refresh(subtask)
        return subtask
