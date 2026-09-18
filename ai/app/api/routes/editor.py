"""Editor AI endpoints (Phase 4): text transforms for selection rewrite.

``/editor/task`` and ``/editor/ask`` return a single result; ``/editor/stream``
streams tokens for the top-input writing flow.
"""

from typing import AsyncIterator, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.api.deps import require_gateway_key
from app.core.config import get_settings
from app.llm import ChatMessage, get_llm_provider

router = APIRouter(tags=["editor"])

Task = Literal["paraphrase", "simplify", "elaborate", "summarize", "title"]
Tone = Literal["default", "formal", "casual", "professional"]

TASK_INSTRUCTIONS: dict[str, str] = {
    "paraphrase": "Rewrite the following text in different words while preserving its exact meaning.",
    "simplify": "Simplify the following text to make it clearer and more concise.",
    "elaborate": "Expand the following text with more detail and explanation.",
    "summarize": "Summarize the following text.",
    "title": "Generate a short, descriptive title for the following text. Return only the title.",
}

TONE_INSTRUCTIONS: dict[str, str] = {
    "default": "",
    "formal": " Use a formal tone.",
    "casual": " Use a casual, friendly tone.",
    "professional": " Use a professional tone.",
}


class EditorTaskRequest(BaseModel):
    task: Task
    text: str = Field(min_length=1, max_length=50_000)
    tone: Tone = "default"


class EditorAskRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=10_000)
    text: str = Field(min_length=1, max_length=50_000)
    tone: Tone = "default"


class EditorStreamRequest(BaseModel):
    task: Task | None = None
    instruction: str | None = None
    text: str = Field(min_length=1, max_length=50_000)
    tone: Tone = "default"


@router.post("/editor/task", dependencies=[Depends(require_gateway_key)])
async def editor_task(request: EditorTaskRequest) -> dict:
    settings = get_settings()
    if not settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI gateway is not configured (missing plane/llm API keys)",
        )

    provider = get_llm_provider(settings)
    instruction = TASK_INSTRUCTIONS[request.task] + TONE_INSTRUCTIONS[request.tone]

    response = await provider.chat(
        [
            ChatMessage(role="system", content="You are a precise writing assistant. Return only the requested text."),
            ChatMessage(role="user", content=f"{instruction}\n\nText:\n{request.text}"),
        ]
    )
    return {"response": response.content or ""}


@router.post("/editor/ask", dependencies=[Depends(require_gateway_key)])
async def editor_ask(request: EditorAskRequest) -> dict:
    settings = get_settings()
    if not settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI gateway is not configured (missing plane/llm API keys)",
        )

    provider = get_llm_provider(settings)
    instruction = (
        f"Apply the following instruction to the provided text. "
        f"Return only the resulting text.\n\nInstruction: {request.instruction}"
        + TONE_INSTRUCTIONS[request.tone]
    )

    response = await provider.chat(
        [
            ChatMessage(role="system", content="You are a precise writing assistant. Return only the requested text."),
            ChatMessage(role="user", content=f"{instruction}\n\nText:\n{request.text}"),
        ]
    )
    return {"response": response.content or ""}


def _stream_instruction(request: EditorStreamRequest) -> str:
    if request.task:
        return TASK_INSTRUCTIONS[request.task] + TONE_INSTRUCTIONS[request.tone]
    instruction = request.instruction or "Improve the provided text."
    return (
        f"Apply the following instruction to the provided text. "
        f"Return only the resulting text.\n\nInstruction: {instruction}"
        + TONE_INSTRUCTIONS[request.tone]
    )


async def _editor_stream(request: EditorStreamRequest) -> AsyncIterator[dict]:
    provider = get_llm_provider(get_settings())
    instruction = _stream_instruction(request)
    messages = [
        ChatMessage(role="system", content="You are a precise writing assistant. Return only the requested text."),
        ChatMessage(role="user", content=f"{instruction}\n\nText:\n{request.text}"),
    ]
    async for delta in provider.stream_chat(messages):
        yield {"event": "token", "data": delta}
    yield {"event": "done", "data": ""}


@router.post("/editor/stream", dependencies=[Depends(require_gateway_key)])
async def editor_stream(request: EditorStreamRequest) -> EventSourceResponse:
    settings = get_settings()
    if not settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI gateway is not configured (missing plane/llm API keys)",
        )
    return EventSourceResponse(_editor_stream(request))
