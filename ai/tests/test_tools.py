import json

from app.agent.tools.base import ToolContext
from app.agent.tools.plane import read_only_tools
from app.plane.client import PlaneClient


def test_tools_have_valid_schema():
    tools = read_only_tools()
    assert len(tools) == 8
    names = {t.name for t in tools}
    assert {"list_projects", "list_work_items", "get_work_item", "list_cycles", "list_modules", "list_states", "list_members", "search_work_items"} <= names

    for tool in tools:
        schema = tool.to_openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == tool.name
        assert schema["function"]["parameters"]["type"] == "object"


def test_list_projects_tool_executes():
    class FakeClient:
        async def list_projects(self, workspace_slug):
            return [{"id": "p1", "identifier": "PROJ", "name": "Project One"}]

    tool = next(t for t in read_only_tools() if t.name == "list_projects")
    import asyncio

    context = ToolContext(plane=FakeClient(), workspace_slug="ws")
    result = asyncio.run(tool.execute(context))
    data = json.loads(result)
    assert data[0]["identifier"] == "PROJ"
