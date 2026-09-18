"""Workspace AI settings (Phase 6): per-workspace AI enable/disable."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require_gateway_key
from app.db.crud import get_workspace_setting, set_ai_enabled
from app.db.session import get_sessionmaker

router = APIRouter(tags=["settings"])


class AISettingBody(BaseModel):
    workspace_slug: str
    ai_enabled: bool


@router.get("/settings/ai", dependencies=[Depends(require_gateway_key)])
async def get_ai_setting(workspace_slug: str) -> dict:
    async with get_sessionmaker()() as db:
        setting = await get_workspace_setting(db, workspace_slug)
        return {"workspace_slug": workspace_slug, "ai_enabled": setting.ai_enabled if setting else True}


@router.put("/settings/ai", dependencies=[Depends(require_gateway_key)])
async def update_ai_setting(body: AISettingBody) -> dict:
    async with get_sessionmaker()() as db:
        setting = await set_ai_enabled(db, body.workspace_slug, body.ai_enabled)
        await db.commit()
        return {"workspace_slug": setting.workspace_slug, "ai_enabled": setting.ai_enabled}
