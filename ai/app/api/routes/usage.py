"""Usage metrics (Phase 6)."""

from fastapi import APIRouter, Depends

from app.api.deps import require_gateway_key
from app.db.crud import aggregate_usage
from app.db.session import get_sessionmaker

router = APIRouter(tags=["usage"])


@router.get("/usage", dependencies=[Depends(require_gateway_key)])
async def usage(workspace_slug: str) -> dict:
    async with get_sessionmaker()() as db:
        data = await aggregate_usage(db, workspace_slug)
        total_requests = sum(m["requests"] for m in data["by_model"])
        total_latency = sum(m["total_latency_ms"] for m in data["by_model"])
        return {
            "workspace_slug": workspace_slug,
            "total_requests": total_requests,
            "total_latency_ms": total_latency,
            "avg_latency_ms": round(total_latency / total_requests, 1) if total_requests else 0,
            **data,
        }
