"""Retrieval service: indexing and hybrid search over workspace documents."""

import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select, text

from app.db.models import Document
from app.db.session import get_engine, get_sessionmaker
from app.plane.client import PlaneClient
from app.retrieval.embeddings import EmbeddingProvider

_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class SearchHit:
    entity_type: str
    entity_id: str
    content: str
    metadata: dict[str, Any]
    score: float


class RetrievalService:
    def __init__(self, embeddings: EmbeddingProvider) -> None:
        self.embeddings = embeddings

    @staticmethod
    def _strip_html(value: str | None) -> str:
        if not value:
            return ""
        return re.sub(r"\s+", " ", _TAG_RE.sub(" ", value)).strip()

    @staticmethod
    def _work_item_content(item: dict[str, Any]) -> str:
        parts = [str(item.get("name") or ""), RetrievalService._strip_html(item.get("description_html"))]
        return " ".join(p for p in parts if p).strip()

    @staticmethod
    def _link(workspace_slug: str, project_id: Any, sequence_id: Any) -> str:
        return f"/{workspace_slug}/projects/{project_id}/issues/{sequence_id}"

    async def index_workspace(self, workspace_slug: str, plane_client: PlaneClient) -> dict[str, Any]:
        """Incremental index of work items and comments for a workspace.

        Documents whose ``source_updated_at`` is unchanged are skipped (no
        re-embedding), so re-running this is cheap.
        """
        projects = await plane_client.list_projects(workspace_slug)
        docs: list[dict[str, Any]] = []

        for project in projects[:50]:
            project_id = project.get("id")
            if not project_id:
                continue
            items = await plane_client.list_work_items(workspace_slug, project_id, per_page=50)
            for item in items:
                sequence_id = item.get("sequence_id")
                content = self._work_item_content(item)
                if content:
                    docs.append(
                        {
                            "entity_type": "work_item",
                            "entity_id": str(item.get("id")),
                            "content": content[:4000],
                            "metadata": {
                                "sequence_id": sequence_id,
                                "name": item.get("name"),
                                "project_id": project_id,
                                "link": self._link(workspace_slug, project_id, sequence_id),
                                "source_updated_at": item.get("updated_at"),
                            },
                        }
                    )
                for comment in await plane_client.list_comments(workspace_slug, project_id, item.get("id")):
                    body = self._strip_html(comment.get("comment_html"))
                    if body:
                        docs.append(
                            {
                                "entity_type": "comment",
                                "entity_id": str(comment.get("id")),
                                "content": body[:4000],
                                "metadata": {
                                    "work_item_id": str(item.get("id")),
                                    "sequence_id": sequence_id,
                                    "link": self._link(workspace_slug, project_id, sequence_id),
                                    "source_updated_at": comment.get("updated_at"),
                                },
                            }
                        )

        indexed, skipped = await self._upsert(workspace_slug, docs)
        return {"indexed": indexed, "skipped": skipped, "projects": len(projects)}

    async def _upsert(self, workspace_slug: str, docs: list[dict[str, Any]]) -> tuple[int, int]:
        """Upsert documents, skipping unchanged ones. Returns (indexed, skipped)."""
        if not docs:
            return 0, 0

        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            existing_rows = (
                await session.execute(
                    select(Document.entity_type, Document.entity_id, Document.metadata_json).where(
                        Document.workspace_slug == workspace_slug
                    )
                )
            ).all()
            existing_map = {}
            for entity_type, entity_id, metadata_json in existing_rows:
                try:
                    existing_map[(entity_type, entity_id)] = json.loads(metadata_json or "{}")
                except json.JSONDecodeError:
                    existing_map[(entity_type, entity_id)] = {}

            changed: list[dict[str, Any]] = []
            skipped = 0
            for doc in docs:
                key = (doc["entity_type"], doc["entity_id"])
                if key in existing_map and existing_map[key].get("source_updated_at") == doc["metadata"].get("source_updated_at"):
                    skipped += 1
                else:
                    changed.append(doc)

            if not changed:
                return 0, skipped

            vectors = await self.embeddings.embed([d["content"] for d in changed])
            is_postgres = get_engine().dialect.name == "postgresql"
            for doc, vector in zip(changed, vectors):
                existing_doc = (
                    await session.execute(
                        select(Document).where(
                            Document.workspace_slug == workspace_slug,
                            Document.entity_type == doc["entity_type"],
                            Document.entity_id == doc["entity_id"],
                        )
                    )
                ).scalar_one_or_none()

                embedding_value = vector if is_postgres else json.dumps(vector)
                if existing_doc is not None:
                    existing_doc.content = doc["content"]
                    existing_doc.metadata_json = json.dumps(doc["metadata"], ensure_ascii=False)
                    existing_doc.embedding = embedding_value
                else:
                    session.add(
                        Document(
                            workspace_slug=workspace_slug,
                            entity_type=doc["entity_type"],
                            entity_id=doc["entity_id"],
                            content=doc["content"],
                            metadata_json=json.dumps(doc["metadata"], ensure_ascii=False),
                            embedding=embedding_value,
                        )
                    )
            await session.commit()
            return len(changed), skipped

    async def search(self, workspace_slug: str, query: str, top_k: int = 5) -> list[SearchHit]:
        keyword_hits = await self._keyword_search(workspace_slug, query, top_k)
        vector_hits = await self._vector_search(workspace_slug, query, top_k)

        # Merge and dedupe by (entity_type, entity_id), keeping the best score.
        merged: dict[tuple[str, str], SearchHit] = {}
        for hit in keyword_hits + vector_hits:
            key = (hit.entity_type, hit.entity_id)
            if key not in merged or hit.score > merged[key].score:
                merged[key] = hit
        return sorted(merged.values(), key=lambda h: h.score, reverse=True)[:top_k]

    async def _keyword_search(self, workspace_slug: str, query: str, top_k: int) -> list[SearchHit]:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            result = await session.execute(
                select(Document)
                .where(
                    Document.workspace_slug == workspace_slug,
                    func.lower(Document.content).contains(query.lower()),
                )
                .limit(top_k)
            )
            return [self._to_hit(d, 0.5) for d in result.scalars()]

    async def _vector_search(self, workspace_slug: str, query: str, top_k: int) -> list[SearchHit]:
        if not self.embeddings.supports_vectors:
            return []
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            if get_engine().dialect.name != "postgresql":
                return []
            vector = (await self.embeddings.embed([query]))[0]
            vector_literal = "[" + ",".join(str(v) for v in vector) + "]"
            result = await session.execute(
                text(
                    "SELECT id, 1 - (embedding <=> :vec::vector) AS score "
                    "FROM documents "
                    "WHERE workspace_slug = :slug AND embedding IS NOT NULL "
                    "ORDER BY embedding <=> :vec::vector "
                    "LIMIT :k"
                ),
                {"vec": vector_literal, "slug": workspace_slug, "k": top_k},
            )
            hits: list[SearchHit] = []
            for doc_id, score in result.all():
                doc = await session.get(Document, doc_id)
                if doc is not None:
                    hits.append(self._to_hit(doc, float(score)))
            return hits

    @staticmethod
    def _to_hit(doc: Document, score: float) -> SearchHit:
        try:
            metadata = json.loads(doc.metadata_json or "{}")
        except json.JSONDecodeError:
            metadata = {}
        return SearchHit(
            entity_type=doc.entity_type,
            entity_id=doc.entity_id,
            content=doc.content,
            metadata=metadata,
            score=score,
        )
