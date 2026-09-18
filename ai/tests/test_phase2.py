import json

import pytest

from app.agent import execute_actions, plan_agent
from app.agent.tools.base import Tool, ToolContext
from app.agent.tools.write import submit_plan_tool
from app.llm import ChatMessage, ChatResponse, LLMProvider, ToolCall
from app.plane.client import PlaneClient


class PlanProvider(LLMProvider):
    def __init__(self, actions):
        super().__init__(api_key="test", model="test-model")
        self.actions = actions

    async def chat(self, messages: list[ChatMessage], tools=None) -> ChatResponse:
        return ChatResponse(
            tool_calls=[ToolCall(id="call_1", name="submit_plan", arguments={"actions": self.actions})]
        )

    async def stream_chat(self, messages):
        yield "unexpected"


class RecordingWriteTool(Tool):
    name = "create_work_item"
    description = "create"
    parameters = {"type": "object", "properties": {}, "required": []}

    def __init__(self):
        self.calls = []

    async def execute(self, context: ToolContext, **kwargs):
        self.calls.append(kwargs)
        return json.dumps({"ok": True, "id": "i1", "name": kwargs.get("name")})


def make_context() -> ToolContext:
    return ToolContext(plane=PlaneClient(base_url="http://test", api_key="k"), workspace_slug="ws")


@pytest.mark.asyncio
async def test_plan_agent_emits_plan_without_executing():
    actions = [{"action": "create_work_item", "params": {"project_id": "p1", "name": "hi", "state_id": "s1"}}]
    provider = PlanProvider(actions)
    plan_tool = submit_plan_tool(["create_work_item"])

    events = []
    async for event in plan_agent(provider, [], plan_tool, "sys", "hi", make_context()):
        events.append(event)

    assert events[0].kind == "plan"
    assert events[0].actions == actions


@pytest.mark.asyncio
async def test_execute_actions_runs_confirmed_actions():
    tool = RecordingWriteTool()
    actions = [{"action": "create_work_item", "params": {"project_id": "p1", "name": "x", "state_id": "s1"}}]

    events = []
    async for event in execute_actions(make_context(), actions, {"create_work_item": tool}):
        events.append(event)

    assert events[0].kind == "action_result"
    payload = json.loads(events[0].result)
    assert payload["ok"] is True
    assert tool.calls == [{"project_id": "p1", "name": "x", "state_id": "s1"}]


@pytest.mark.asyncio
async def test_execute_actions_reports_unknown_action():
    actions = [{"action": "nope", "params": {}}]

    events = []
    async for event in execute_actions(make_context(), actions, {}):
        events.append(event)

    payload = json.loads(events[0].result)
    assert payload["ok"] is False
    assert "Unknown action" in payload["error"]
