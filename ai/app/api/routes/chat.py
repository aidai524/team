"""Chat endpoint (SSE streaming) with the agent loop.

Modes:
- ``ask``       — read-only tools, streams an answer.
- ``build``     — plans write actions (read tools + submit_plan), returns a
  ``plan`` event; execution happens via ``POST /execute``.
- ``autopilot`` — read + write tools executed directly, streamed.

Events emitted to the client:
- ``token``        — a chunk of the final answer
- ``tool_call``    — the agent invoked a tool (name + arguments)
- ``tool_result``  — the tool's result
- ``plan``         — proposed write actions (build mode)
- ``done``         — stream finished (carries conversation_id)
- ``error``        — terminal error
"""

import json
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.agent import plan_agent, run_agent
from app.agent.tools.base import ToolContext
from app.agent.tools.plane import read_only_tools
from app.agent.tools.retrieval import search_documents_tool
from app.agent.tools.write import submit_plan_tool, write_actions
from app.api.ai_guard import ensure_ai_enabled
from app.api.deps import require_gateway_key
from app.core.config import Settings, get_settings
from app.db.crud import add_message, add_usage_log, get_or_create_conversation, list_history
from app.db.session import get_sessionmaker
from app.llm import get_llm_provider
from app.plane.client import PlaneClient
from app.retrieval.embeddings import get_embedding_provider
from app.retrieval.service import RetrievalService
from app.skills import resolve_slash_command

router = APIRouter(tags=["chat"])

BASE_SYSTEM_PROMPT = (
    "You are a helpful assistant for a self-hosted Plane workspace "
    "(workspace slug: {workspace_slug}). "
    "Always ground answers in actual tool results and never fabricate data. "
    "Answer concisely and reference work item identifiers (e.g. PROJ-123) when useful."
)

ASK_PROMPT = BASE_SYSTEM_PROMPT + (
    " You are strictly read-only: use the provided tools to answer questions, "
    "and never request or perform writes."
)

BUILD_PROMPT = BASE_SYSTEM_PROMPT + (
    " You are in planning mode. Use read tools to gather the IDs you need, then "
    "call submit_plan with the exact list of write actions required to fulfil the "
    "request. Do not perform writes yourself; propose them for human approval."
)

AUTOPILOT_PROMPT = BASE_SYSTEM_PROMPT + (
    " You may use read and write tools. Execute write operations directly and "
    "then summarise what you changed, including any identifiers."
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=32_000)
    workspace_slug: str = Field(min_length=1)
    conversation_id: str | None = None
    mode: Literal["ask", "build", "autopilot"] = "ask"


def _system_prompt(mode: str, workspace_slug: str) -> str:
    template = {"ask": ASK_PROMPT, "build": BUILD_PROMPT, "autopilot": AUTOPILOT_PROMPT}[mode]
    return template.format(workspace_slug=workspace_slug)


async def _stream(request: ChatRequest, settings: Settings):
    sessionmaker = get_sessionmaker()
    provider = get_llm_provider(settings)
    start = time.monotonic()

    async with sessionmaker() as db:
        # Resolve slash commands (/skill key=value) before persisting.
        effective_message = request.message
        if request.message.startswith("/"):
            resolved = await resolve_slash_command(db, request.workspace_slug, request.message)
            if resolved:
                effective_message = resolved
        conversation = await get_or_create_conversation(
            db, request.workspace_slug, request.conversation_id, request.message
        )
        await db.commit()
        history = await list_history(db, conversation.id)
        await add_message(db, conversation.id, "user", effective_message)
        await db.commit()

    system_prompt = _system_prompt(request.mode, request.workspace_slug)
    assistant_parts: list[str] = []
    read_tools = read_only_tools() + [search_documents_tool()]
    retrieval = RetrievalService(get_embedding_provider())

    async with PlaneClient.from_settings(settings) as client:
        context = ToolContext(plane=client, workspace_slug=request.workspace_slug, retrieval=retrieval)
        if request.mode == "build":
            plan_tool = submit_plan_tool([action.name for action in write_actions()])
            agent_stream = plan_agent(
                provider, read_tools, plan_tool, system_prompt, effective_message, context, history
            )
        else:
            tools = read_tools if request.mode == "ask" else read_tools + write_actions()
            agent_stream = run_agent(provider, tools, system_prompt, effective_message, context, history)

        try:
            async for event in agent_stream:
                if event.kind == "tool_call":
                    yield {
                        "event": "tool_call",
                        "data": json.dumps({"name": event.name, "arguments": event.arguments}, ensure_ascii=False),
                    }
                elif event.kind == "tool_result":
                    yield {
                        "event": "tool_result",
                        "data": json.dumps({"name": event.name, "result": event.result}, ensure_ascii=False),
                    }
                elif event.kind == "plan":
                    yield {"event": "plan", "data": json.dumps({"actions": event.actions}, ensure_ascii=False)}
                elif event.kind == "sources":
                    yield {"event": "sources", "data": json.dumps({"sources": event.sources}, ensure_ascii=False)}
                elif event.kind == "token":
                    assistant_parts.append(event.text or "")
                    yield {"event": "token", "data": event.text or ""}
                elif event.kind == "error":
                    yield {"event": "error", "data": event.error or "unknown error"}
        except Exception as exc:  # noqa: BLE001 - surface LLM/Plane errors to the client
            yield {"event": "error", "data": str(exc)}

    answer = "".join(assistant_parts)
    if answer:
        async with sessionmaker() as db:
            await add_message(db, conversation.id, "assistant", answer)
            await db.commit()

    # Record usage (tokens are unavailable for streamed completions; counted as None).
    latency_ms = int((time.monotonic() - start) * 1000)
    async with sessionmaker() as db:
        await add_usage_log(
            db,
            workspace_slug=request.workspace_slug,
            member_id=None,
            mode=request.mode,
            model=settings.llm_model,
            provider=settings.llm_provider,
            latency_ms=latency_ms,
            tokens_in=None,
            tokens_out=None,
        )
        await db.commit()

    yield {"event": "done", "data": json.dumps({"conversation_id": conversation.id})}


@router.post("/chat", dependencies=[Depends(require_gateway_key)])
async def chat(request: ChatRequest) -> EventSourceResponse:
    settings = get_settings()
    if not settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI gateway is not configured (missing plane/llm API keys)",
        )
    await ensure_ai_enabled(request.workspace_slug)
    return EventSourceResponse(_stream(request, settings), sep="\n")
