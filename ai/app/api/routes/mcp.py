"""MCP connection management (Phase 5).

Provides CRUD for external tool connections plus a best-effort ``tools/list``
probe. Wiring MCP tools into the agent loop (autopilot/build) is a follow-up.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import require_gateway_key
from app.db.crud import create_mcp_connection, delete_mcp_connection, list_mcp_connections
from app.db.models import MCPConnection
from app.db.session import get_sessionmaker
from app.mcp.client import MCPStdioClient

router = APIRouter(tags=["mcp"])


class MCPCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    transport: str = "stdio"
    command: str = Field(min_length=1)
    args: list[str] = []
    env: dict[str, str] = {}
    enabled: bool = True


def _payload(conn) -> dict:
    return {"id": conn.id, "name": conn.name, "transport": conn.transport, "enabled": conn.enabled}


@router.get("/mcp", dependencies=[Depends(require_gateway_key)])
async def connections() -> list[dict]:
    async with get_sessionmaker()() as db:
        return [_payload(c) for c in await list_mcp_connections(db)]


@router.post("/mcp", dependencies=[Depends(require_gateway_key)])
async def create(request: MCPCreate) -> dict:
    config = json.dumps({"command": request.command, "args": request.args, "env": request.env})
    async with get_sessionmaker()() as db:
        conn = await create_mcp_connection(
            db, name=request.name, transport=request.transport, config_json=config, enabled=request.enabled
        )
        await db.commit()
        return _payload(conn)


@router.delete("/mcp/{conn_id}", dependencies=[Depends(require_gateway_key)])
async def remove(conn_id: str) -> dict:
    async with get_sessionmaker()() as db:
        deleted = await delete_mcp_connection(db, conn_id)
        await db.commit()
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP connection not found")
        return {"ok": True}


@router.post("/mcp/{conn_id}/tools", dependencies=[Depends(require_gateway_key)])
async def probe_tools(conn_id: str) -> dict:
    async with get_sessionmaker()() as db:
        conn = await db.get(MCPConnection, conn_id)
        if conn is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP connection not found")
        config = json.loads(conn.config_json or "{}")

    client = MCPStdioClient(config.get("command", ""), config.get("args", []), config.get("env", {}))
    try:
        await client.start()
        tools = await client.list_tools()
        return {"tools": [{"name": t.get("name"), "description": t.get("description")} for t in tools]}
    finally:
        await client.close()
