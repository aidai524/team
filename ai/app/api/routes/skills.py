"""AI Skills CRUD (Phase 5): reusable slash-command prompt templates."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import require_gateway_key
from app.db.crud import create_skill, delete_skill, list_skills
from app.db.session import get_sessionmaker

router = APIRouter(tags=["skills"])

Scope = Literal["personal", "workspace"]


class SkillCreate(BaseModel):
    workspace_slug: str | None = None
    scope: Scope = "workspace"
    name: str = Field(min_length=1, max_length=64)
    description: str | None = None
    prompt: str = Field(min_length=1)
    created_by: str | None = None


def _payload(skill) -> dict:
    return {
        "id": skill.id,
        "workspace_slug": skill.workspace_slug,
        "scope": skill.scope,
        "name": skill.name,
        "description": skill.description,
        "prompt": skill.prompt,
        "created_by": skill.created_by,
    }


@router.get("/skills", dependencies=[Depends(require_gateway_key)])
async def skills(workspace_slug: str | None = None, scope: str | None = None) -> list[dict]:
    async with get_sessionmaker()() as db:
        result = await list_skills(db, workspace_slug, scope)
        return [_payload(s) for s in result]


@router.post("/skills", dependencies=[Depends(require_gateway_key)])
async def create(request: SkillCreate) -> dict:
    async with get_sessionmaker()() as db:
        skill = await create_skill(
            db,
            workspace_slug=request.workspace_slug,
            scope=request.scope,
            name=request.name.strip(),
            description=request.description,
            prompt=request.prompt,
            created_by=request.created_by,
        )
        await db.commit()
        return _payload(skill)


@router.delete("/skills/{skill_id}", dependencies=[Depends(require_gateway_key)])
async def remove(skill_id: str, workspace_slug: str | None = None) -> dict:
    async with get_sessionmaker()() as db:
        deleted = await delete_skill(db, skill_id, workspace_slug)
        await db.commit()
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
        return {"ok": True}
