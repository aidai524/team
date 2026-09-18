"""Minimal MCP (Model Context Protocol) client over stdio.

Supports ``initialize``, ``tools/list`` and ``tools/call`` via newline-delimited
JSON-RPC. Experimental — token encryption and SSE transport are follow-ups.
"""

import asyncio
import json
import os
from typing import Any


class MCPStdioClient:
    def __init__(self, command: str, args: list[str] | None = None, env: dict[str, str] | None = None) -> None:
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.proc: asyncio.subprocess.Process | None = None
        self._id = 0

    async def start(self) -> None:
        self.proc = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **self.env},
        )
        await self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "plane-ai-gateway", "version": "0.1.0"},
            },
        )

    async def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if self.proc is None or self.proc.stdin is None or self.proc.stdout is None:
            raise RuntimeError("MCP client not started")
        self._id += 1
        request_id = self._id
        message = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        self.proc.stdin.write((json.dumps(message) + "\n").encode())
        await self.proc.stdin.drain()

        while True:
            line = await self.proc.stdout.readline()
            if not line:
                raise RuntimeError("MCP server closed the stream")
            data = json.loads(line)
            if data.get("id") == request_id:
                if "error" in data:
                    raise RuntimeError(str(data["error"]))
                return data.get("result", {}) or {}

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self._request("tools/list", {})
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self._request("tools/call", {"name": name, "arguments": arguments})

    async def close(self) -> None:
        if self.proc is not None:
            try:
                self.proc.terminate()
                await asyncio.wait_for(self.proc.wait(), timeout=5)
            except (ProcessLookupError, TimeoutError):
                self.proc.kill()
