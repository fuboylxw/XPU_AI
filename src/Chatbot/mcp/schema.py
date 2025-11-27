from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolParam(BaseModel):
    """Generic tool parameter container."""

    query: Optional[str] = Field(default=None, description="User query text")
    max_results: Optional[int] = Field(default=5, ge=1, le=50)
    top_k: Optional[int] = Field(default=10, ge=1, le=50)
    keywords: Optional[List[str]] = Field(default=None, description="Optional keywords")
    # Weather related (optional)
    city: Optional[str] = Field(default=None, description="City name for weather queries")
    days: Optional[int] = Field(default=1, ge=1, le=7, description="Forecast days")
    # Time related (optional)
    timezone: Optional[str] = Field(default=None, description="Timezone identifier for time tool")
    format: Optional[str] = Field(default=None, description="Optional time format string")
    # Database query related (optional, used by db_query tool)
    engine: Optional[str] = Field(default=None, description="Database engine, e.g., 'mysql' or 'redis'")
    sql: Optional[str] = Field(default=None, description="SQL query for MySQL engine (SELECT only)")
    limit: Optional[int] = Field(default=100, ge=1, le=1000, description="Max rows to return for DB query")
    command: Optional[str] = Field(default=None, description="Redis command, e.g., 'GET'")
    key: Optional[str] = Field(default=None, description="Redis key for GET")
    args: Optional[List[str]] = Field(default=None, description="Optional args for commands")
    # Permission and identity fields for db_query
    resource: Optional[str] = Field(default=None, description="Protected resource type for DB query")
    subject_user_id: Optional[str] = Field(default=None, description="Subject user ID")
    request_user_id: Optional[str] = Field(default=None, description="Requesting user ID")
    request_role: Optional[str] = Field(default=None, description="Role of requesting user")
    term: Optional[str] = Field(default=None, description="Academic term filter")
    week: Optional[int] = Field(default=None, description="Week filter")


class ToolResult(BaseModel):
    """Unified tool result schema."""

    success: bool = True
    source: Optional[str] = None
    answer: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class RPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)
    id: Optional[int] = None


class RPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[int] = None
