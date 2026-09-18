"""Embedding providers (OpenAI-compatible, pluggable)."""

from abc import ABC, abstractmethod

from openai import AsyncOpenAI

from app.core.config import get_settings


class EmbeddingProvider(ABC):
    supports_vectors: bool = False

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a dense vector for each input text."""
        raise NotImplementedError


class OpenAICompatibleEmbeddings(EmbeddingProvider):
    """Uses any OpenAI-compatible /embeddings endpoint (OpenAI, BGE via TEI/infinity, ...)."""

    supports_vectors = True

    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 60.0) -> None:
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(model=self.model, input=texts)
        # OpenAI returns items in input order.
        items = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in items]


class NullEmbeddings(EmbeddingProvider):
    """Fallback when no embeddings are configured: keyword-only retrieval."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] for _ in texts]


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if settings.embedding_api_key:
        return OpenAICompatibleEmbeddings(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
            model=settings.embedding_model,
        )
    return NullEmbeddings()
