"""Application settings loaded from environment variables.

All values are read from the environment; the compose fragment in
``deployments/ai/`` passes them through from ``plane-ai.env``.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_GATEWAY_", env_file=".env", extra="ignore")

    # --- Service ---
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # Optional shared secret protecting the gateway's own endpoints.
    # The Plane frontend must send this as `X-AI-Gateway-Key`. When unset
    # (local dev only) the gateway is open; never leave it unset in prod.
    gateway_api_key: str | None = None

    # --- Plane ---
    plane_api_base_url: str = "http://api:8000"
    # Service-account API key used by the tool layer (scoped, read/write).
    plane_api_key: str | None = None

    # --- LLM ---
    llm_provider: str = "deepseek"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: float = 60.0

    # --- Retrieval (Phase 3) ---
    # Postgres DSN for the AI-specific database (pgvector). Optional for now.
    database_url: str | None = None
    # Embeddings (OpenAI-compatible endpoint; can point at BGE/TEI/infinity).
    embedding_provider: str = "openai-compatible"
    embedding_api_key: str | None = None
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    retrieval_top_k: int = 5

    @property
    def is_configured(self) -> bool:
        return bool(self.plane_api_key and self.llm_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
