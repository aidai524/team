"""FastAPI dependencies: auth and shared clients."""

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def require_gateway_key(
    x_ai_gateway_key: str | None = Header(default=None),
) -> None:
    """Protect gateway endpoints with a shared secret when configured."""
    expected = get_settings().gateway_api_key
    if expected and x_ai_gateway_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid AI gateway key",
        )
