"""OpenAI-compatible provider (covers DeepSeek and OpenAI).

DeepSeek exposes an OpenAI-compatible API at ``https://api.deepseek.com``;
the same adapter is used for OpenAI with ``OPENAI_BASE_URL`` support.
"""

import json
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from app.llm.base import ChatMessage, ChatResponse, LLMProvider, ToolCall


class OpenAICompatibleProvider(LLMProvider):
    name = "openai-compatible"

    def __init__(
        self,
        api_key: str | None,
        model: str,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(api_key, model, base_url, timeout)
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    def _openai_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        return [m.to_openai() for m in messages]

    async def chat(self, messages: list[ChatMessage], tools: list[dict[str, Any]] | None = None) -> ChatResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": self._openai_messages(messages),
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        completion = await self._client.chat.completions.create(**kwargs)
        choice = completion.choices[0]
        message = choice.message

        tool_calls = []
        for call in message.tool_calls or []:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {"_raw": call.function.arguments}
            tool_calls.append(ToolCall(id=call.id, name=call.function.name, arguments=arguments))

        return ChatResponse(content=message.content, tool_calls=tool_calls)

    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=self._openai_messages(messages),
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and (delta := chunk.choices[0].delta.content):
                yield delta


class DeepSeekProvider(OpenAICompatibleProvider):
    name = "deepseek"
