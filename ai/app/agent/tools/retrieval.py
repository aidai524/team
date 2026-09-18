"""Semantic/keyword retrieval tool over indexed workspace documents."""

import json
from typing import Any

from app.agent.tools.base import FunctionTool, ToolContext


async def _search_documents(context: ToolContext, query: str, top_k: int = 5) -> str:
    if context.retrieval is None:
        return json.dumps({"results": [], "sources": [], "note": "retrieval not configured"}, ensure_ascii=False)

    hits = await context.retrieval.search(context.workspace_slug, query, int(top_k))

    results = [
        {
            "content": hit.content,
            "entity_type": hit.entity_type,
            "metadata": hit.metadata,
            "score": round(hit.score, 3),
        }
        for hit in hits
    ]
    sources = [
        {
            "title": (hit.metadata.get("sequence_id") or hit.entity_type),
            "name": hit.metadata.get("name"),
            "link": hit.metadata.get("link"),
            "snippet": hit.content[:200],
        }
        for hit in hits
    ]
    return json.dumps({"results": results, "sources": sources}, ensure_ascii=False, default=str)


def search_documents_tool() -> FunctionTool:
    return FunctionTool(
        name="search_documents",
        description=(
            "Search indexed workspace documents (work items and comments) by meaning or keywords. "
            "Use this for fuzzy questions like 'any discussion about X?'. Returns snippets and "
            "clickable source links; cite the sources in your answer."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "top_k": {"type": "integer", "description": "Max results, default 5"},
            },
            "required": ["query"],
        },
        fn=_search_documents,
    )
