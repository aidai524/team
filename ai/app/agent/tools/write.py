"""Write actions over Plane's public REST API (Phase 2).

These are executed only after human confirmation (Build mode) or directly
(Autopilot mode). Each action returns a JSON string with ``ok`` plus either a
created/updated resource summary or an error.
"""

import html
import json
from typing import Any

from app.agent.tools.base import FunctionTool, ToolContext

PRIORITIES = ["urgent", "high", "medium", "low", "none"]


def _link(workspace_slug: str, project_id: str, sequence_id: Any) -> str:
    return f"/{workspace_slug}/projects/{project_id}/issues/{sequence_id}"


def _ok(payload: dict[str, Any]) -> str:
    return json.dumps({"ok": True, **payload}, ensure_ascii=False, default=str)


def _error(message: str) -> str:
    return json.dumps({"ok": False, "error": message}, ensure_ascii=False)


async def _create_work_item(context: ToolContext, **params: Any) -> str:
    payload: dict[str, Any] = {"name": params["name"], "state": params["state_id"]}
    if params.get("description"):
        payload["description"] = params["description"]
    if params.get("priority"):
        payload["priority"] = params["priority"]
    if params.get("assignee_ids"):
        payload["assignees"] = params["assignee_ids"]
    if params.get("label_ids"):
        payload["labels"] = params["label_ids"]
    if params.get("target_date"):
        payload["target_date"] = params["target_date"]

    item = await context.plane.create_work_item(context.workspace_slug, params["project_id"], payload)
    return _ok(
        {
            "id": item.get("id"),
            "sequence_id": item.get("sequence_id"),
            "name": item.get("name"),
            "link": _link(context.workspace_slug, params["project_id"], item.get("sequence_id")),
        }
    )


async def _update_work_item(context: ToolContext, **params: Any) -> str:
    payload: dict[str, Any] = {}
    mapping = {
        "name": "name",
        "state_id": "state",
        "priority": "priority",
        "description": "description",
        "assignee_ids": "assignees",
        "label_ids": "labels",
        "target_date": "target_date",
    }
    for param_key, api_key in mapping.items():
        if params.get(param_key) is not None:
            payload[api_key] = params[param_key]
    if not payload:
        return _error("No fields provided to update")

    item = await context.plane.update_work_item(context.workspace_slug, params["project_id"], params["work_item_id"], payload)
    return _ok(
        {
            "id": item.get("id"),
            "sequence_id": item.get("sequence_id"),
            "name": item.get("name"),
            "link": _link(context.workspace_slug, params["project_id"], item.get("sequence_id")),
        }
    )


async def _add_comment(context: ToolContext, **params: Any) -> str:
    body = html.escape(params["body"])
    comment = await context.plane.add_comment(
        context.workspace_slug, params["project_id"], params["work_item_id"], f"<p>{body}</p>"
    )
    return _ok({"id": comment.get("id"), "comment": params["body"][:200]})


def _id_param(name: str, description: str) -> dict[str, Any]:
    return {"type": "string", "description": description}


def write_actions() -> list[FunctionTool]:
    return [
        FunctionTool(
            name="create_work_item",
            description="Create a new work item in a project.",
            parameters={
                "type": "object",
                "properties": {
                    "project_id": _id_param("project_id", "Project UUID"),
                    "name": {"type": "string", "description": "Work item title"},
                    "state_id": _id_param("state_id", "State UUID (from list_states)"),
                    "description": {"type": "string", "description": "Optional description"},
                    "priority": {"type": "string", "enum": PRIORITIES},
                    "assignee_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Member UUIDs to assign",
                    },
                    "label_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Label UUIDs to attach",
                    },
                    "target_date": {"type": "string", "description": "Due date (YYYY-MM-DD)"},
                },
                "required": ["project_id", "name", "state_id"],
            },
            fn=_create_work_item,
        ),
        FunctionTool(
            name="update_work_item",
            description="Update an existing work item (name, state, priority, assignees, labels, due date).",
            parameters={
                "type": "object",
                "properties": {
                    "project_id": _id_param("project_id", "Project UUID"),
                    "work_item_id": _id_param("work_item_id", "Work item UUID"),
                    "name": {"type": "string"},
                    "state_id": _id_param("state_id", "New state UUID"),
                    "priority": {"type": "string", "enum": PRIORITIES},
                    "description": {"type": "string"},
                    "assignee_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Full list of member UUIDs to assign",
                    },
                    "label_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Full list of label UUIDs to attach",
                    },
                    "target_date": {"type": "string"},
                },
                "required": ["project_id", "work_item_id"],
            },
            fn=_update_work_item,
        ),
        FunctionTool(
            name="add_comment",
            description="Add a comment to a work item.",
            parameters={
                "type": "object",
                "properties": {
                    "project_id": _id_param("project_id", "Project UUID"),
                    "work_item_id": _id_param("work_item_id", "Work item UUID"),
                    "body": {"type": "string", "description": "Comment text"},
                },
                "required": ["project_id", "work_item_id", "body"],
            },
            fn=_add_comment,
        ),
    ]


def submit_plan_tool(action_names: list[str]) -> FunctionTool:
    """A pseudo-tool the model calls to hand back a plan without executing it."""

    async def _noop(*args: Any, **kwargs: Any) -> str:
        return ""

    return FunctionTool(
        name="submit_plan",
        description=(
            "Submit a proposed plan of write actions for human approval. "
            "Do NOT perform the actions yourself; just list them here. "
            f"Available actions: {', '.join(action_names)}."
        ),
        parameters={
            "type": "object",
            "properties": {
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "description": "Action name"},
                            "params": {"type": "object", "description": "Action parameters"},
                        },
                        "required": ["action", "params"],
                    },
                }
            },
            "required": ["actions"],
        },
        fn=_noop,
    )
