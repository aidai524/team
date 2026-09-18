"""Conversation/session listing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_gateway_key
from app.db.crud import list_conversations, list_history
from app.db.models import Conversation
from app.db.session import get_sessionmaker

router = APIRouter(tags=["sessions"])


def _conversation_payload(conversation: Conversation) -> dict:
    return {
        "id": conversation.id,
        "title": conversation.title,
        "workspace_slug": conversation.workspace_slug,
        "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
    }


@router.get("/sessions", dependencies=[Depends(require_gateway_key)])
async def sessions(workspace_slug: str | None = None) -> list[dict]:
    async with get_sessionmaker()() as db:
        conversations = await list_conversations(db, workspace_slug)
        return [_conversation_payload(c) for c in conversations]


@router.get("/sessions/{conversation_id}/messages", dependencies=[Depends(require_gateway_key)])
async def session_messages(conversation_id: str) -> list[dict]:
    async with get_sessionmaker()() as db:
        conversation = await db.get(Conversation, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        history = await list_history(db, conversation_id)
        return [{"role": m.role, "content": m.content} for m in history]
