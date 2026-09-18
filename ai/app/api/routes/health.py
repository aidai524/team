"""Health and readiness endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app import __version__
from app.core.config import get_settings
from app.core.logging import get_logger
from app.plane.client import PlaneClient

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health")
async def health() -> dict:
    """Liveness probe: always 200 if the process is up."""
    return {"status": "ok", "version": __version__}


@router.get("/ready")
async def ready() -> dict:
    """Readiness probe: verifies the gateway can reach Plane via API key."""
    settings = get_settings()
    if not settings.plane_api_key:
        return {"status": "degraded", "reason": "PLANE_API_KEY not configured"}

    try:
        async with PlaneClient.from_settings(settings) as client:
            me = await client.me()
        return {"status": "ready", "plane_user": me.get("email") or me.get("id")}
    except Exception as exc:  # noqa: BLE001 - readiness must not raise
        logger.warning("readiness check failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Plane API unreachable: {exc}",
        )
