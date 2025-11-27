from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

from config.settings import settings
from src.Chatbot.mcp.registry import MCPToolRunner
from .schema import RPCRequest, RPCResponse


class MCPServer:
    """JSON-RPC 2.0 MCP TCP server.

    Methods:
      - handshake: returns protocol and status
      - list_tools: returns available tools metadata
      - call_tool: executes a tool by name
    """

    def __init__(self) -> None:
        # 动态注册：按配置和依赖可用性注册工具（web/knowledge/db）
        self.runner = MCPToolRunner.from_settings(settings)

    async def handle_conn(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                text = data.decode().strip()
                if not text:
                    continue

                try:
                    req = RPCRequest.model_validate_json(text)
                except Exception:
                    resp = RPCResponse(result=None, error={"code": -32700, "message": "Parse error"}, id=None)
                    writer.write((resp.model_dump_json() + "\n").encode())
                    await writer.drain()
                    continue

                response = await self.dispatch(req)
                writer.write((response.model_dump_json() + "\n").encode())
                await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    async def dispatch(self, req: RPCRequest) -> RPCResponse:
        try:
            if req.method == "handshake":
                return RPCResponse(result={"protocol": "mcp", "version": "1.0", "status": "ready"}, id=req.id)

            elif req.method == "list_tools":
                tools = self.runner.registry.list_tools()
                return RPCResponse(result={"tools": tools}, id=req.id)

            elif req.method == "call_tool":
                name = req.params.get("name")
                params = req.params.get("params", {})
                timeout_ms = int(req.params.get("timeout_ms", 30000))
                retries = int(req.params.get("retries", 0))
                result = await self.runner.execute(name, params, timeout_ms=timeout_ms, retries=retries)
                return RPCResponse(result=result, id=req.id)

            else:
                return RPCResponse(error={"code": -32601, "message": "Method not found"}, id=req.id)
        except Exception as e:
            return RPCResponse(error={"code": -32603, "message": str(e)}, id=req.id)


async def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = MCPServer()
    srv = await asyncio.start_server(server.handle_conn, host, port)
    addrs = ", ".join(str(sock.getsockname()) for sock in srv.sockets)
    print(f"MCP server listening on {addrs}")
    async with srv:
        await srv.serve_forever()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run MCP JSON-RPC server")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    asyncio.run(run_server(args.host, args.port))