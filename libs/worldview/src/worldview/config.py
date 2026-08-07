"""Centralised service configuration backed by environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for a WorldView service.

    Every value can be overridden via environment variables or a ``.env`` file.
    Secrets must never be committed; use environment/KMS in production.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- global ---
    env: str = "dev"
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    region_key: str = Field(default="us-east-1", validation_alias="REGION_KEY")
    service_name: str = "service"

    # --- database ---
    database_url: str = Field(
        default="sqlite:///./data/worldview.db", validation_alias="DATABASE_URL"
    )

    # --- redis (optional in dev) ---
    redis_url: str | None = Field(default=None, validation_alias="REDIS_URL")

    # --- auth ---
    jwt_secret: str = Field(default="dev-only-change-me", validation_alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_access_ttl_minutes: int = Field(default=15, validation_alias="JWT_ACCESS_TTL_MINUTES")

    # --- external AI (used by ai-guide) ---
    ai_provider: str = Field(default="mock", validation_alias="AI_PROVIDER")
    model_gateway_url: str | None = Field(default=None, validation_alias="AI_MODEL_GATEWAY_URL")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (one per process)."""
    return Settings()


def reset_settings() -> None:
    """Clear the cached settings (used by tests between env changes)."""
    get_settings.cache_clear()
