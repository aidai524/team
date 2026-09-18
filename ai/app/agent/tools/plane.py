"""Read-only tools over Plane's public REST API.

Phase 1 exposes list/get operations for projects, work items, cycles,
modules, states, and members. Write actions live in ``write.py``.
"""

import json
from typing import Any

from app.agent.tools.base import FunctionTool, ToolContext

MAX_RESULTS = 20


def _display(value: Any) -> Any:
    """Reduce nested API objects to a readable scalar where possible."""
    if isinstance(value, dict):
        return value.get("name") or value.get("display_name") or value.get("identifier") or value.get("id")
    if isinstance(value, list):
        return [_display(v) for v in value]
    return value


def _compact_issue(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "sequence_id": item.get("sequence_id"),
        "name": item.get("name"),
        "priority": item.get("priority"),
        "state": _display(item.get("state")),
        "assignees": _display(item.get("assignees")),
        "labels": _display(item.get("labels")),
        "target_date": item.get("target_date"),
        "updated_at": item.get("updated_at"),
    }


def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


async def _list_projects(context: ToolContext) -> str:
    projects = await context.plane.list_projects(context.workspace_slug)
    compact = [
        {"id": p.get("id"), "identifier": p.get("identifier"), "name": p.get("name")}
        for p in projects[:MAX_RESULTS]
    ]
    return _dump(compact)


async def _list_work_items(
    context: ToolContext,
    project_id: str,
    order_by: str = "-updated_at",
    limit: int = 20,
) -> str:
    items = await context.plane.list_work_items(
        context.workspace_slug, project_id, order_by=order_by, per_page=min(int(limit), 50)
    )
    return _dump([_compact_issue(i) for i in items[:MAX_RESULTS]])


async def _get_work_item(context: ToolContext, project_id: str, work_item_id: str) -> str:
    item = await context.plane.get_work_item(context.workspace_slug, project_id, work_item_id)
    return _dump(_compact_issue(item))


async def _search_work_items(
    context: ToolContext,
    query: str,
    project_id: str | None = None,
) -> str:
    results = await context.plane.search_work_items(context.workspace_slug, query, project_id)
    issues = results.get("issues", []) if isinstance(results, dict) else []
    return _dump([_compact_issue(i) for i in issues[:MAX_RESULTS]])


async def _list_cycles(context: ToolContext, project_id: str) -> str:
    cycles = await context.plane.list_cycles(context.workspace_slug, project_id)
    compact = [
        {
            "id": c.get("id"),
            "name": c.get("name"),
            "start_date": c.get("start_date"),
            "end_date": c.get("end_date"),
            "status": c.get("status"),
        }
        for c in cycles[:MAX_RESULTS]
    ]
    return _dump(compact)


async def _list_modules(context: ToolContext, project_id: str) -> str:
    modules = await context.plane.list_modules(context.workspace_slug, project_id)
    compact = [
        {"id": m.get("id"), "name": m.get("name"), "status": m.get("status")}
        for m in modules[:MAX_RESULTS]
    ]
    return _dump(compact)


async def _list_states(context: ToolContext, project_id: str) -> str:
    states = await context.plane.list_states(context.workspace_slug, project_id)
    compact = [
        {"id": s.get("id"), "name": s.get("name"), "group": s.get("group"), "color": s.get("color")}
        for s in states[:MAX_RESULTS]
    ]
    return _dump(compact)


async def _list_members(context: ToolContext) -> str:
    members = await context.plane.list_members(context.workspace_slug)
    compact = [
        {
            "id": m.get("id") or m.get("member"),
            "display_name": m.get("display_name") or m.get("member__display_name"),
            "email": m.get("email"),
            "role": m.get("role"),
        }
        for m in members[:MAX_RESULTS]
    ]
    return _dump(compact)


def _id_param(name: str = "id", description: str = "UUID identifier") -> dict[str, Any]:
    return {"type": "string", "description": description}


def read_only_tools() -> list[FunctionTool]:
    return [
        FunctionTool(
            name="list_projects",
            description="List projects in a Plane workspace.",
            parameters={"type": "object", "properties": {}, "required": []},
            fn=_list_projects,
        ),
        FunctionTool(
            name="list_work_items",
            description=(
                "List work items (issues) in a project. Community Edition has no server-side "
                "filtering, so filter client-side after fetching. Use order_by for recent items."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "project_id": _id_param("project_id", "Project UUID"),
                    "order_by": {"type": "string", "enum": ["-updated_at", "-created_at", "priority", "state__name"]},
                    "limit": {"type": "integer", "description": "Max results, default 20"},
                },
                "required": ["project_id"],
            },
            fn=_list_work_items,
        ),
        FunctionTool(
            name="get_work_item",
            description="Get a single work item by id.",
            parameters={
                "type": "object",
                "properties": {
                    "project_id": _id_param("project_id", "Project UUID"),
                    "work_item_id": _id_param("work_item_id", "Work item UUID"),
                },
                "required": ["project_id", "work_item_id"],
            },
            fn=_get_work_item,
        ),
        FunctionTool(
            name="search_work_items",
            description="Search work items across a workspace by name, sequence id, or project identifier.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search text"},
                    "project_id": _id_param("project_id", "Optional project UUID to scope search"),
                },
                "required": ["query"],
            },
            fn=_search_work_items,
        ),
        FunctionTool(
            name="list_cycles",
            description="List cycles (sprints) in a project.",
            parameters={
                "type": "object",
                "properties": {"project_id": _id_param("project_id", "Project UUID")},
                "required": ["project_id"],
            },
            fn=_list_cycles,
        ),
        FunctionTool(
            name="list_modules",
            description="List modules in a project.",
            parameters={
                "type": "object",
                "properties": {"project_id": _id_param("project_id", "Project UUID")},
                "required": ["project_id"],
            },
            fn=_list_modules,
        ),
        FunctionTool(
            name="list_states",
            description="List work item states in a project.",
            parameters={
                "type": "object",
                "properties": {"project_id": _id_param("project_id", "Project UUID")},
                "required": ["project_id"],
            },
            fn=_list_states,
        ),
        FunctionTool(
            name="list_members",
            description="List workspace members.",
            parameters={"type": "object", "properties": {}, "required": []},
            fn=_list_members,
        ),
    ]
