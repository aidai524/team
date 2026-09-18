from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Settings with deterministic values for unit tests."""
    monkeypatch.setenv("AI_GATEWAY_PLANE_API_KEY", "test-plane-key")
    monkeypatch.setenv("AI_GATEWAY_LLM_API_KEY", "test-llm-key")
    monkeypatch.setenv("AI_GATEWAY_GATEWAY_API_KEY", "test-gateway-key")
    # Import after env is set; get_settings is lru_cached so reset it.
    from app.core.config import get_settings

    get_settings.cache_clear()
    return get_settings()
