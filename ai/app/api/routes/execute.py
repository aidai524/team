"""Execute confirmed write actions (Build mode) and record an audit trail."""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.agent import execute_actions
from app.agent.tools.base import ToolContext
from app.agent.tools.write import write_actions
from app.api.ai_guard import ensure_ai_enabled
from app.api.deps import require_gateway_key
from app.core.config import get_settings
from app.db.crud import add_audit_log
from app.db.session import get_sessionmaker
from app.plane.client import PlaneClient

router = APIRouter(tags=["execute"])


class ExecuteRequest(BaseModel):
    workspace_slug: str = Field(min_length=1)
    conversation_id: str | None = None
    actions: list[dict] = Field(min_length=1)


@router.post("/execute", dependencies=[Depends(require_gateway_key)])
async def execute(request: ExecuteRequest) -> dict:
    settings = get_settings()
    if not settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI gateway is not configured (missing plane/llm API keys)",
        )
    await ensure_ai_enabled(request.workspace_slug)

    write_map = {action.name: action for action in write_actions()}
    results: list[dict] = []

    async with PlaneClient.from_settings(settings) as client:
        context = ToolContext(plane=client, workspace_slug=request.workspace_slug)
        async for event in execute_actions(context, request.actions, write_map):
            try:
                payload = json.loads(event.result or "{}")
            except json.JSONDecodeError:
                payload = {}

            ok = bool(payload.get("ok"))
            results.append(
                {
                    "action": event.name,
                    "ok": ok,
                    "id": payload.get("id"),
                    "sequence_id": payload.get("sequence_id"),
                    "name": payload.get("name"),
                    "link": payload.get("link"),
                    "error": payload.get("error"),
                }
            )

            async with get_sessionmaker()() as db:
                await add_audit_log(
                    db,
                    workspace_slug=request.workspace_slug,
                    conversation_id=request.conversation_id,
                    action=event.name or "unknown",
                    params=json.dumps(event.arguments, ensure_ascii=False, default=str),
                    status="success" if ok else "error",
                    result=event.result,
                )
                await db.commit()

    return {"results": results}
