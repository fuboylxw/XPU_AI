#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect, Response, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import asyncio
import time

from fastapi_app.database import get_db, engine, Base
from sqlalchemy import text
from fastapi_app.models import WorkSession, WorkTask, WorkSubTask
from fastapi_app.schemas import (
    WorkSessionCreate,
    WorkSessionUpdate,
    WorkSessionResponse,
    TaskSubmitRequest,
    TaskRunRequest,
    WorkSubTaskResponse,
    WorkSubTaskUpdate,
)
from src.Chatbot.agents.task_execution_agent import TaskExecutionAgent
from dataclasses import asdict

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logging.warning(f"创建工作任务相关表失败: {e}")

def _ensure_db_constraints():
    try:
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE work_task RENAME TO work_sessions"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE work_task_history RENAME TO work_tasks"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE work_sessions CHANGE conversation_id session_id VARCHAR(50) NOT NULL"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE work_sessions ADD UNIQUE INDEX uq_work_sessions_session_id (session_id)"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE work_tasks DROP COLUMN description"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE work_tasks ADD CONSTRAINT fk_work_tasks_session FOREIGN KEY (session_id) REFERENCES work_sessions(session_id)"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE work_sub_tasks ADD COLUMN sub_task_name VARCHAR(255)"))
            except Exception:
                pass
    except Exception as e:
        logging.warning(f"约束检查失败: {e}")

_ensure_db_constraints()

router = APIRouter()

# 延迟导入ChatbotAgent，避免循环依赖
_chatbot_agent = None
def _get_chatbot_agent():
    global _chatbot_agent
    if _chatbot_agent is None:
        try:
            from src.Chatbot.agents.chat_agent import ChatbotAgent
            _chatbot_agent = ChatbotAgent()
        except Exception as e:
            logging.error(f"初始化ChatbotAgent失败: {e}")
            _chatbot_agent = None
    return _chatbot_agent

async def _run_chat_agent_task(session_id: str, question: str, user_id: str):
    """后台运行 ChatbotAgent.answer_question_tools"""
    agent = _get_chatbot_agent()
    if not agent:
        logging.error("无法获取 ChatbotAgent 实例")
        return
    
    try:
        # 驱动异步生成器执行
        async for _ in agent.answer_question_tools(
            question=question,
            user_id=user_id,
            conversation_id=session_id
        ):
            pass
    except Exception as e:
        logging.error(f"后台任务执行失败: {e}")

def _get_session_by_id(session_id: str, db: Session):
    return db.query(WorkSession).filter(WorkSession.session_id == session_id).first()


 


@router.get("/tasks/", response_model=List[WorkSessionResponse])
async def list_tasks(
    user_id: Optional[str] = Query(None, description="用户ID，可选"),
    session_id: Optional[str] = Query(None, description="会话ID，可选"),
    db: Session = Depends(get_db),
):
    """获取工作任务列表"""
    try:
        q = db.query(WorkSession)
        if user_id:
            q = q.filter(WorkSession.user_id == user_id)
        if session_id:
            q = q.filter(WorkSession.session_id == session_id)
        q = q.order_by(WorkSession.updated_at.desc())
        return q.all()
    except Exception as e:
        logging.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务列表失败")


@router.post("/tasks/", response_model=WorkSessionResponse)
async def create_task(payload: WorkSessionCreate, db: Session = Depends(get_db)):
    """创建工作任务"""
    try:
        existing = _get_session_by_id(payload.session_id, db)
        if existing:
            return existing
        session = WorkSession(
            session_id=payload.session_id,
            user_id=payload.user_id,
            title=payload.title,
            status=(payload.status or "loading"),
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    except Exception as e:
        db.rollback()
        logging.error(f"创建任务失败: {e}")
        raise HTTPException(status_code=500, detail="创建任务失败")


@router.put("/tasks/subtasks/{subtask_id}", response_model=WorkSubTaskResponse)
async def update_subtask(subtask_id: int, payload: WorkSubTaskUpdate, db: Session = Depends(get_db)):
    """更新子任务"""
    try:
        subtask = db.query(WorkSubTask).filter(WorkSubTask.id == subtask_id).first()
        if not subtask:
            raise HTTPException(status_code=404, detail="子任务不存在")
        
        if payload.sub_task_name:
            subtask.sub_task_name = payload.sub_task_name
        if payload.status:
            subtask.status = payload.status
        if payload.result is not None:
            subtask.result = payload.result
            
        db.add(subtask)
        db.commit()
        db.refresh(subtask)
        return subtask
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"更新子任务失败: {e}")
        raise HTTPException(status_code=500, detail="更新子任务失败")


@router.put("/tasks/{task_id}/title/", response_model=WorkSessionResponse)
async def rename_task(task_id: int, payload: WorkSessionUpdate, db: Session = Depends(get_db)):
    """重命名任务标题"""
    try:
        session_obj = db.query(WorkSession).filter(WorkSession.id == task_id).first()
        if not session_obj:
            raise HTTPException(status_code=404, detail="任务不存在")
        if payload.title and payload.title.strip():
            session_obj.title = payload.title.strip()
        db.add(session_obj)
        db.commit()
        db.refresh(session_obj)
        return session_obj
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"重命名任务失败: {e}")
        raise HTTPException(status_code=500, detail="重命名任务失败")


@router.put("/tasks/{task_id}/status/", response_model=WorkSessionResponse)
async def update_task_status(task_id: int, payload: WorkSessionUpdate, db: Session = Depends(get_db)):
    """更新任务状态"""
    try:
        session_obj = db.query(WorkSession).filter(WorkSession.id == task_id).first()
        if not session_obj:
            raise HTTPException(status_code=404, detail="任务不存在")
        if payload.status and payload.status.strip():
            session_obj.status = payload.status.strip()
        db.add(session_obj)
        db.commit()
        db.refresh(session_obj)
        return session_obj
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"更新任务状态失败: {e}")
        raise HTTPException(status_code=500, detail="更新任务状态失败")


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """删除任务"""
    try:
        session_obj = db.query(WorkSession).filter(WorkSession.id == task_id).first()
        if not session_obj:
            raise HTTPException(status_code=404, detail="任务不存在")
            
        # Manually delete related records first
        # Delete subtasks
        db.query(WorkSubTask).filter(WorkSubTask.session_id == session_obj.session_id).delete()
        # Delete tasks (items)
        db.query(WorkTask).filter(WorkTask.session_id == session_obj.session_id).delete()
        
        db.delete(session_obj)
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"删除任务失败: {e}")
        raise HTTPException(status_code=500, detail="删除任务失败")



# --- 任务执行与进度 ---

@router.get("/tasks/{session_id}/progress")
async def stream_task_progress(session_id: str):
    """
    SSE流式输出任务执行进度
    前端通过 EventSource 连接此接口
    事件类型:
    - start: 任务开始
    - thinking: 思考过程
    - decision: 决策结果
    - tool_call: 工具调用
    - result: 任务结果
    - error: 错误信息
    """
    agent = TaskExecutionAgent.get_instance()
    
    async def event_generator():
        q = asyncio.Queue()
        if session_id not in agent.progress_listeners:
            agent.progress_listeners[session_id] = []
        agent.progress_listeners[session_id].append(q)
        
        try:
            while True:
                # 增加心跳机制，每10秒发送一次注释行，防止连接超时
                try:
                    data = await asyncio.wait_for(q.get(), timeout=10.0)
                    yield f"data: {json.dumps(asdict(data), ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        except Exception as e:
            logging.error(f"流式传输断开: {e}")
        finally:
            if session_id in agent.progress_listeners:
                try:
                    agent.progress_listeners[session_id].remove(q)
                except ValueError:
                    pass

    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲
        }
    )


@router.post("/tasks/{session_id}/execute")
async def execute_task_submit(
    session_id: str,
    payload: TaskSubmitRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """接受用户任务（问题与会话ID），后台调用 ChatbotAgent.answer_question_tools 执行"""
    try:
        session_obj = _get_session_by_id(session_id, db)
        if not session_obj:
            session_obj = WorkSession(
                session_id=session_id,
                user_id=payload.user_id,
                title=(payload.question[:50] if payload.question else None),
                status="loading",
            )
            db.add(session_obj)
            db.commit()
            db.refresh(session_obj)

        # 启动后台任务
        background_tasks.add_task(_run_chat_agent_task, session_id, payload.question, payload.user_id)

        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"任务提交失败: {e}")
        raise HTTPException(status_code=500, detail=f"任务提交失败: {str(e)}")

@router.get("/tasks/{session_id}/subtasks", response_model=List[WorkSubTaskResponse])
async def get_subtasks(session_id: str, db: Session = Depends(get_db)):
    """获取指定会话的所有子任务"""
    try:
        subtasks = db.query(WorkSubTask).filter(WorkSubTask.session_id == session_id).order_by(WorkSubTask.order).all()
        return subtasks
    except Exception as e:
        logging.error(f"获取子任务失败: {e}")
        raise HTTPException(status_code=500, detail="获取子任务失败")

@router.get("/tasks/subtasks/{subtask_id}/progress")
async def stream_subtask_progress(subtask_id: int, db: Session = Depends(get_db)):
    """获取特定子任务的流式进度"""
    subtask = db.query(WorkSubTask).filter(WorkSubTask.id == subtask_id).first()
    if not subtask:
        raise HTTPException(status_code=404, detail="子任务不存在")
    
    session_id = subtask.session_id
    agent = TaskExecutionAgent.get_instance()
    
    async def event_generator():
        q = asyncio.Queue()
        if session_id not in agent.progress_listeners:
            agent.progress_listeners[session_id] = []
        agent.progress_listeners[session_id].append(q)
        
        try:
            while True:
                try:
                    data = await asyncio.wait_for(q.get(), timeout=10.0)
                    if data.task_id == subtask_id:
                        yield f"data: {json.dumps(asdict(data), ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        except Exception as e:
            logging.error(f"流式传输断开: {e}")
        finally:
             if session_id in agent.progress_listeners:
                try:
                    agent.progress_listeners[session_id].remove(q)
                except ValueError:
                    pass

    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
