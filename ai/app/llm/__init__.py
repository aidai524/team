"""LLM provider factory."""

from app.core.config import Settings
from app.llm.base import ChatMessage, ChatResponse, LLMProvider, ToolCall
from app.llm.deepseek import DeepSeekProvider, OpenAICompatibleProvider

_PROVIDERS: dict[str, type[LLMProvider]] = {
    "deepseek": DeepSeekProvider,
    "openai": OpenAICompatibleProvider,
    "openai-compatible": OpenAICompatibleProvider,
}


def get_llm_provider(settings: Settings) -> LLMProvider:
    provider_cls = _PROVIDERS.get(settings.llm_provider.lower())
    if provider_cls is None:
        raise ValueError(
            f"Unsupported LLM provider: {settings.llm_provider}. "
            f"Supported: {', '.join(_PROVIDERS)}"
        )
    return provider_cls(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
    )


__all__ = ["LLMProvider", "ChatMessage", "ChatResponse", "ToolCall", "get_llm_provider"]
