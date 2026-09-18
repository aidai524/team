import pytest

from app.agent import run_agent
from app.agent.tools.base import Tool, ToolContext
from app.llm import ChatMessage, ChatResponse, LLMProvider, ToolCall
from app.plane.client import PlaneClient


class FakeProvider(LLMProvider):
    def __init__(self):
        super().__init__(api_key="test", model="test-model")
        self.chat_calls = 0

    async def chat(self, messages: list[ChatMessage], tools=None) -> ChatResponse:
        self.chat_calls += 1
        if self.chat_calls == 1:
            return ChatResponse(tool_calls=[ToolCall(id="call_1", name="list_projects", arguments={})])
        return ChatResponse(content="Here is the answer")

    async def stream_chat(self, messages):
        yield "Here is the answer"


class FakeTool(Tool):
    name = "list_projects"
    description = "List projects"
    parameters = {"type": "object", "properties": {}, "required": []}

    def __init__(self):
        self.executed = False

    async def execute(self, context: ToolContext, **kwargs):
        self.executed = True
        return '["project-1"]'


def make_context() -> ToolContext:
    return ToolContext(plane=PlaneClient(base_url="http://test", api_key="k"), workspace_slug="ws")


@pytest.mark.asyncio
async def test_run_agent_invokes_tools_then_streams_answer():
    provider = FakeProvider()
    tool = FakeTool()
    context = make_context()

    events = []
    async for event in run_agent(provider, [tool], "system", "hi", context):
        events.append(event)

    kinds = [e.kind for e in events]
    assert kinds == ["tool_call", "tool_result", "token", "done"]
    assert tool.executed is True
    answer = "".join(e.text or "" for e in events if e.kind == "token")
    assert answer == "Here is the answer"


@pytest.mark.asyncio
async def test_run_agent_reports_unknown_tool():
    provider = FakeProvider()

    async def chat(messages, tools=None):
        provider.chat_calls += 1
        if provider.chat_calls == 1:
            return ChatResponse(tool_calls=[ToolCall(id="c", name="nope", arguments={})])
        return ChatResponse(content="ok")

    provider.chat = chat

    events = []
    async for event in run_agent(provider, [], "system", "hi", make_context()):
        events.append(event)

    result = next(e for e in events if e.kind == "tool_result")
    assert "unknown tool" in result.result
