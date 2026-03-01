"""工作会话/任务相关Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class WorkSubTaskUpdate(BaseModel):
    sub_task_name: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = None
    result: Optional[str] = None


class WorkSubTaskResponse(BaseModel):
    task_sub_id: int
    session_id: str
    task_id: int
    sub_task_name: Optional[str] = None
    order: Optional[int] = 0
    status: Optional[str] = "waiting"
    result: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkTaskBase(BaseModel):
    conversation_id: str = Field(..., max_length=50)
    user_id: str = Field(..., max_length=32)
    title: str = Field(..., max_length=255)
    status: Optional[str] = Field(default="loading", max_length=32)


class WorkTaskCreate(BaseModel):
    conversation_id: str = Field(..., max_length=50)
    user_id: str = Field(..., max_length=32)
    title: str = Field(..., max_length=255)
    status: Optional[str] = Field(default="loading", max_length=32)


class WorkTaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, max_length=32)


class WorkTaskResponse(WorkTaskBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkTaskHistoryBase(BaseModel):
    task_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    result: Optional[str] = None


class WorkTaskHistoryCreate(WorkTaskHistoryBase):
    pass


class WorkTaskHistoryResponse(WorkTaskHistoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkTaskHistoryUpdate(BaseModel):
    task_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    result: Optional[str] = None


class WorkSessionCreate(BaseModel):
    session_id: str = Field(..., max_length=50)
    user_id: str = Field(..., max_length=32)
    title: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(default="loading", max_length=32)


class WorkSessionUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, max_length=32)


class WorkSessionResponse(BaseModel):
    id: int
    session_id: str
    user_id: str
    title: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkTaskItemCreate(BaseModel):
    task_name: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = None
    result: Optional[str] = None


class WorkTaskItemUpdate(BaseModel):
    task_name: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = None
    result: Optional[str] = None


class WorkTaskItemResponse(BaseModel):
    task_id: int
    session_id: str
    task_name: Optional[str]
    status: Optional[str]
    result: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskRunRequest(BaseModel):
    task_id: int = Field(..., description="任务ID")
    user_id: str = Field(..., description="用户ID")


class TaskSubmitRequest(BaseModel):
    session_id: Optional[str] = None
    question: str
    user_id: str = "guest"
    user_role: str = "guest"
    session_token: Optional[str] = None

    class Config:
        from_attributes = True
