"""Async client for Plane's public REST API (``/api/v1/``).

Authenticates with a service-account API key via the ``X-Api-Key`` header.
Read operations are used from Phase 1; write operations are added in
Phase 2 behind the confirmation flow.
"""

from typing import Any

import httpx

from app.core.config import Settings

API_KEY_HEADER = "X-Api-Key"


class PlaneAPIError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"Plane API error {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class PlaneClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("Plane API key is required")
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={API_KEY_HEADER: api_key},
            timeout=timeout,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "PlaneClient":
        return cls(
            base_url=settings.plane_api_base_url,
            api_key=settings.plane_api_key or "",
            timeout=30.0,
        )

    async def __aenter__(self) -> "PlaneClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = await self._client.request(method, path, **kwargs)
        if response.is_error:
            raise PlaneAPIError(response.status_code, response.text[:500])
        return response.json()

    async def get(self, path: str, **params: Any) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        return await self._request("POST", path, json=json)

    async def patch(self, path: str, json: dict[str, Any] | None = None) -> Any:
        return await self._request("PATCH", path, json=json)

    # --- Identity ---
    async def me(self) -> dict[str, Any]:
        return await self.get("/api/v1/users/me/")

    # --- Read-only workspace data (Phase 1) ---
    async def list_projects(self, workspace_slug: str) -> list[dict[str, Any]]:
        data = await self.get(f"/api/v1/workspaces/{workspace_slug}/projects/")
        return data.get("results", data) if isinstance(data, dict) else data

    async def list_work_items(self, workspace_slug: str, project_id: str, **filters: Any) -> list[dict[str, Any]]:
        data = await self.get(
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/",
            **filters,
        )
        return data.get("results", data) if isinstance(data, dict) else data

    async def get_work_item(self, workspace_slug: str, project_id: str, work_item_id: str) -> dict[str, Any]:
        return await self.get(
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/"
        )

    async def search_work_items(
        self, workspace_slug: str, query: str, project_id: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"search": query, "workspace_search": "false"}
        if project_id:
            params["project_id"] = project_id
        return await self.get(f"/api/v1/workspaces/{workspace_slug}/work-items/search/", **params)

    async def list_cycles(self, workspace_slug: str, project_id: str) -> list[dict[str, Any]]:
        data = await self.get(f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/")
        return data.get("results", data) if isinstance(data, dict) else data

    async def list_modules(self, workspace_slug: str, project_id: str) -> list[dict[str, Any]]:
        data = await self.get(f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/")
        return data.get("results", data) if isinstance(data, dict) else data

    async def list_states(self, workspace_slug: str, project_id: str) -> list[dict[str, Any]]:
        data = await self.get(f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/states/")
        return data.get("results", data) if isinstance(data, dict) else data

    async def list_members(self, workspace_slug: str) -> list[dict[str, Any]]:
        data = await self.get(f"/api/v1/workspaces/{workspace_slug}/members/")
        return data.get("results", data) if isinstance(data, dict) else data

    async def list_comments(self, workspace_slug: str, project_id: str, work_item_id: str) -> list[dict[str, Any]]:
        data = await self.get(
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/comments/"
        )
        return data.get("results", data) if isinstance(data, dict) else data

    # --- Write operations (Phase 2) ---
    async def create_work_item(self, workspace_slug: str, project_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return await self.post(
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/", json=data
        )

    async def update_work_item(
        self, workspace_slug: str, project_id: str, work_item_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        return await self.patch(
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/", json=data
        )

    async def add_comment(
        self, workspace_slug: str, project_id: str, work_item_id: str, comment_html: str
    ) -> dict[str, Any]:
        return await self.post(
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/comments/",
            json={"comment_html": comment_html},
        )
