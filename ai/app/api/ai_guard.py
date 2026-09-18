"""Access guards shared across AI routes (Phase 6)."""

from fastapi import HTTPException, status

from app.db.crud import get_workspace_setting
from app.db.session import get_sessionmaker


async def ensure_ai_enabled(workspace_slug: str) -> None:
    """Raise 403 when the workspace admin has disabled AI."""
    async with get_sessionmaker()() as db:
        setting = await get_workspace_setting(db, workspace_slug)
        if setting is not None and not setting.ai_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="AI is disabled for this workspace",
            )
