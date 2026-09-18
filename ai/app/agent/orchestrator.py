"""Agent orchestrator: LLM + tool calling loop.

Supports three modes:
- ``ask``       — read-only tools only (streams an answer).
- ``autopilot`` — read + write tools, executed directly during the loop.
- ``build``     — read tools for context, then a ``submit_plan`` call returns a
  proposed plan of write actions that the human must confirm before execution.

Tool results may carry a ``sources`` key; the orchestrator re-emits those as
``sources`` events so the UI can render citations.
"""

import json
from dataclasses import dataclass
from typing import Any, AsyncIterator

from app.agent.tools.base import Tool, ToolContext
from app.llm import ChatMessage, LLMProvider

MAX_TOOL_ROUNDS = 5


@dataclass
class AgentEvent:
    """A streamed event emitted while the agent runs."""

    kind: str  # tool_call | tool_result | token | done | error | plan | action_result | sources
    name: str | None = None
    arguments: dict[str, Any] | None = None
    result: str | None = None
    text: str | None = None
    error: str | None = None
    actions: list[dict[str, Any]] | None = None
    sources: list[dict[str, Any]] | None = None


def _error_json(message: str) -> str:
    return json.dumps({"ok": False, "error": message}, ensure_ascii=False)


def _extract_sources(result: str) -> list[dict[str, Any]] | None:
    try:
        payload = json.loads(result)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and isinstance(payload.get("sources"), list):
        return payload["sources"]
    return None


async def _run_tool(tool: Tool | None, context: ToolContext, name: str, arguments: dict[str, Any]) -> str:
    if tool is None:
        return f"Error: unknown tool '{name}'"
    try:
        return await tool.execute(context, **arguments)
    except Exception as exc:  # noqa: BLE001 - keep loop alive on tool errors
        return f"Error executing {name}: {exc}"


async def run_agent(
    provider: LLMProvider,
    tools: list[Tool],
    system_prompt: str,
    user_message: str,
    context: ToolContext,
    history: list[ChatMessage] | None = None,
) -> AsyncIterator[AgentEvent]:
    """Run the tool-calling loop, executing every tool the model requests.

    For ``ask`` pass only read tools; for ``autopilot`` pass read + write tools.
    """
    tool_map = {tool.name: tool for tool in tools}
    tool_schemas = [tool.to_openai_schema() for tool in tools]

    messages: list[ChatMessage] = [ChatMessage(role="system", content=system_prompt)]
    if history:
        messages.extend(history)
    messages.append(ChatMessage(role="user", content=user_message))

    for _ in range(MAX_TOOL_ROUNDS):
        response = await provider.chat(messages, tools=tool_schemas)

        if response.tool_calls:
            messages.append(
                ChatMessage(role="assistant", content=response.content or "", tool_calls=response.tool_calls)
            )
            for call in response.tool_calls:
                yield AgentEvent(kind="tool_call", name=call.name, arguments=call.arguments)
                result = await _run_tool(tool_map.get(call.name), context, call.name, call.arguments)
                sources = _extract_sources(result)
                yield AgentEvent(kind="tool_result", name=call.name, result=result)
                if sources is not None:
                    yield AgentEvent(kind="sources", sources=sources)
                messages.append(ChatMessage(role="tool", tool_call_id=call.id, content=result))
            continue

        async for delta in provider.stream_chat(messages):
            yield AgentEvent(kind="token", text=delta)
        yield AgentEvent(kind="done")
        return

    yield AgentEvent(kind="error", error="Reached the maximum tool-calling rounds without a final answer.")


async def plan_agent(
    provider: LLMProvider,
    read_tools: list[Tool],
    submit_plan: Tool,
    system_prompt: str,
    user_message: str,
    context: ToolContext,
    history: list[ChatMessage] | None = None,
) -> AsyncIterator[AgentEvent]:
    """Build-mode planning loop: gather context, then emit a proposed plan."""
    tool_map = {tool.name: tool for tool in read_tools}
    tool_map[submit_plan.name] = submit_plan
    tool_schemas = [tool.to_openai_schema() for tool in read_tools] + [submit_plan.to_openai_schema()]

    messages: list[ChatMessage] = [ChatMessage(role="system", content=system_prompt)]
    if history:
        messages.extend(history)
    messages.append(ChatMessage(role="user", content=user_message))

    for _ in range(MAX_TOOL_ROUNDS):
        response = await provider.chat(messages, tools=tool_schemas)

        if response.tool_calls:
            messages.append(
                ChatMessage(role="assistant", content=response.content or "", tool_calls=response.tool_calls)
            )
            for call in response.tool_calls:
                if call.name == submit_plan.name:
                    actions = call.arguments.get("actions", [])
                    yield AgentEvent(kind="plan", actions=actions if isinstance(actions, list) else [])
                    return
                yield AgentEvent(kind="tool_call", name=call.name, arguments=call.arguments)
                result = await _run_tool(tool_map.get(call.name), context, call.name, call.arguments)
                sources = _extract_sources(result)
                yield AgentEvent(kind="tool_result", name=call.name, result=result)
                if sources is not None:
                    yield AgentEvent(kind="sources", sources=sources)
                messages.append(ChatMessage(role="tool", tool_call_id=call.id, content=result))
            continue

        async for delta in provider.stream_chat(messages):
            yield AgentEvent(kind="token", text=delta)
        yield AgentEvent(kind="done")
        return

    yield AgentEvent(kind="error", error="Reached the maximum planning rounds without a plan.")


async def execute_actions(
    context: ToolContext,
    actions: list[dict[str, Any]],
    write_tool_map: dict[str, Tool],
) -> AsyncIterator[AgentEvent]:
    """Execute confirmed write actions one by one."""
    for action in actions:
        name = action.get("action") if isinstance(action, dict) else None
        params = action.get("params") if isinstance(action, dict) else {}
        if not isinstance(params, dict):
            params = {}

        tool = write_tool_map.get(name or "")
        if tool is None:
            yield AgentEvent(kind="action_result", name=name, arguments=params, result=_error_json(f"Unknown action: {name}"))
            continue

        try:
            result = await tool.execute(context, **params)
            yield AgentEvent(kind="action_result", name=name, arguments=params, result=result)
        except Exception as exc:  # noqa: BLE001 - continue with remaining actions
            yield AgentEvent(kind="action_result", name=name, arguments=params, result=_error_json(str(exc)))
