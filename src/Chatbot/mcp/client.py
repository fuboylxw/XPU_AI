from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
import asyncio
import json

from .registry import MCPRegistry


class MCPClient:
    """Minimal MCP client that interacts with a local MCPRegistry.

    This simulates the MCP protocol flow:
    - handshake()
    - list_tools()
    - call_tool(name, params)

    In production, this would speak over a transport (e.g., JSON-RPC/WebSocket).
    Here we keep it embedded for simplicity.
    """

    def __init__(self, registry: MCPRegistry) -> None:
        self._registry = registry
        self._ready = False

    async def handshake(self) -> Dict[str, Any]:
        self._ready = True
        return {
            "protocol": "mcp-lite",
            "version": "0.1",
            "status": "ready",
        }

    async def list_tools(self) -> List[Dict[str, Any]]:
        if not self._ready:
            await self.handshake()
        return self._registry.list_tools()

    async def call_tool(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._ready:
            await self.handshake()
        return await self._registry.call(name, params)


class NetMCPClient:
    """Network MCP JSON-RPC client over TCP sockets."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._id = 0

    async def connect(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)

    async def _rpc(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self._id += 1
        req = {"jsonrpc": "2.0", "method": method, "params": params, "id": self._id}
        self._writer.write((json.dumps(req) + "\n").encode())
        await self._writer.drain()
        line = await self._reader.readline()
        if not line:
            raise RuntimeError("Connection closed")
        resp = json.loads(line.decode())
        if resp.get("error"):
            raise RuntimeError(resp["error"].get("message"))
        return resp.get("result", {})

    async def handshake(self) -> Dict[str, Any]:
        if not self._reader:
            await self.connect()
        return await self._rpc("handshake", {})

    async def list_tools(self) -> List[Dict[str, Any]]:
        result = await self._rpc("list_tools", {})
        return result.get("tools", [])

    async def call_tool(self, name: str, params: Dict[str, Any], *, timeout_ms: int = 30000, retries: int = 0) -> Dict[str, Any]:
        return await self._rpc("call_tool", {"name": name, "params": params, "timeout_ms": timeout_ms, "retries": retries})