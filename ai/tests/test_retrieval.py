import uuid

import pytest

from app.db.session import init_db
from app.retrieval.embeddings import NullEmbeddings
from app.retrieval.service import RetrievalService


class FakePlaneClient:
    async def list_projects(self, workspace_slug):
        return [{"id": "p1", "identifier": "PROJ", "name": "Project"}]

    async def list_work_items(self, workspace_slug, project_id, **kwargs):
        return [
            {
                "id": "i1",
                "sequence_id": "PROJ-1",
                "name": "Login flow stuck on MFA",
                "description_html": "<p>Users report getting stuck on the login flow at the MFA step.</p>",
            }
        ]

    async def list_comments(self, workspace_slug, project_id, work_item_id):
        return [
            {"id": "c1", "comment_html": "<p>We should try the new login flow endpoint.</p>"},
            {"id": "c2", "comment_html": "<p>Totally unrelated comment.</p>"},
        ]


@pytest.mark.asyncio
async def test_index_and_keyword_search():
    await init_db()
    service = RetrievalService(NullEmbeddings())
    client = FakePlaneClient()
    slug = f"ws-a-{uuid.uuid4().hex[:8]}"

    stats = await service.index_workspace(slug, client)
    assert stats["indexed"] == 3  # 1 work item + 2 comments

    hits = await service.search(slug, "login flow", top_k=5)
    contents = " ".join(h.content for h in hits)
    assert "login flow" in contents.lower()


@pytest.mark.asyncio
async def test_incremental_index_skips_unchanged():
    await init_db()
    service = RetrievalService(NullEmbeddings())
    client = FakePlaneClient()
    slug = f"ws-inc-{uuid.uuid4().hex[:8]}"

    first = await service.index_workspace(slug, client)
    second = await service.index_workspace(slug, client)
    assert first["indexed"] == 3
    assert second["indexed"] == 0
    assert second["skipped"] == 3


@pytest.mark.asyncio
async def test_search_scopes_by_workspace():
    await init_db()
    service = RetrievalService(NullEmbeddings())
    slug = f"ws-b-{uuid.uuid4().hex[:8]}"
    await service.index_workspace(slug, FakePlaneClient())

    # A different workspace should not leak this workspace's documents.
    hits = await service.search(f"ws-other-{uuid.uuid4().hex[:8]}", "MFA", top_k=3)
    assert hits == []
