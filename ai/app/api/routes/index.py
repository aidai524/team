"""Indexing endpoint: sync workspace documents into the retrieval store."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.ai_guard import ensure_ai_enabled
from app.api.deps import require_gateway_key
from app.core.config import get_settings
from app.plane.client import PlaneClient
from app.retrieval.embeddings import get_embedding_provider
from app.retrieval.service import RetrievalService

router = APIRouter(tags=["retrieval"])


class IndexRequest(BaseModel):
    workspace_slug: str = Field(min_length=1)


@router.post("/retrieval/index", dependencies=[Depends(require_gateway_key)])
async def index_workspace(request: IndexRequest) -> dict:
    settings = get_settings()
    if not settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI gateway is not configured (missing plane/llm API keys)",
        )
    await ensure_ai_enabled(request.workspace_slug)

    service = RetrievalService(get_embedding_provider())
    async with PlaneClient.from_settings(settings) as client:
        return await service.index_workspace(request.workspace_slug, client)
