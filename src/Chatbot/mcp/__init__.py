"""
MCP (Model Context Protocol) lightweight integration layer.

Provides:
- Tool registry and unified execution API
- Simple client class for model↔service interactions

Tools can be registered dynamically and invoked by name with parameters.
This module is intentionally minimal and self-contained for local use.
"""

from .registry import MCPRegistry, MCPToolSpec, MCPToolRunner
from .client import MCPClient, NetMCPClient
from .schema import ToolParam, ToolResult, RPCRequest, RPCResponse

__all__ = [
    "MCPRegistry",
    "MCPToolSpec",
    "MCPToolRunner",
    "MCPClient",
    "NetMCPClient",
    "ToolParam",
    "ToolResult",
    "RPCRequest",
    "RPCResponse",
]