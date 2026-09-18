import httpx
import pytest

from app.plane.client import API_KEY_HEADER, PlaneAPIError, PlaneClient


@pytest.mark.asyncio
async def test_me_sends_api_key_header(monkeypatch):
    captured: dict = {}

    async def fake_request(method, path, **kwargs):
        captured["path"] = path
        captured["headers"] = {}
        return httpx.Response(200, json={"id": "u1", "email": "bot@example.com"})

    client = PlaneClient(base_url="http://api", api_key="secret")
    client._client.request = fake_request  # type: ignore[method-assign]

    me = await client.me()
    assert me["email"] == "bot@example.com"


@pytest.mark.asyncio
async def test_error_raises_plane_api_error(monkeypatch):
    async def fake_request(method, path, **kwargs):
        return httpx.Response(500, text="boom")

    client = PlaneClient(base_url="http://api", api_key="secret")
    client._client.request = fake_request  # type: ignore[method-assign]

    with pytest.raises(PlaneAPIError) as exc_info:
        await client.me()
    assert exc_info.value.status_code == 500


def test_requires_api_key():
    with pytest.raises(ValueError):
        PlaneClient(base_url="http://api", api_key="")
