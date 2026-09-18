"""LLM provider abstraction.

Each provider exposes a uniform interface:
- ``chat`` returns a single completion (optionally with tool calls).
- ``stream_chat`` yields text deltas for streaming.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass
class ToolCall:
    """A single tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatMessage:
    """A message in the conversation, mapped to the OpenAI wire format."""

    role: str  # system | user | assistant | tool
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None

    def to_openai(self) -> dict[str, Any]:
        message: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            message["content"] = self.content
        if self.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": json.dumps(call.arguments, ensure_ascii=False)},
                }
                for call in self.tool_calls
            ]
        if self.tool_call_id is not None:
            message["tool_call_id"] = self.tool_call_id
        return message


@dataclass
class ChatResponse:
    """A single completion result."""

    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMProvider(ABC):
    """Base class for LLM provider adapters."""

    name: str = ""

    def __init__(self, api_key: str | None, model: str, base_url: str | None = None, timeout: float = 60.0) -> None:
        if not api_key:
            raise ValueError(f"{self.name} API key is required")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    @abstractmethod
    async def chat(self, messages: list[ChatMessage], tools: list[dict[str, Any]] | None = None) -> ChatResponse:
        """Return a single completion, including any requested tool calls."""
        raise NotImplementedError

    @abstractmethod
    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """Yield text deltas for a chat completion."""
        raise NotImplementedError
