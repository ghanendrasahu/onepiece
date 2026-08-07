"""Centralised service configuration backed by environment variables.

Secrets policy:
- ``JWT_SECRET`` has no committed default. In non-dev environments it is
  required (>= 32 chars); in dev it may be omitted and an ephemeral secret is
  generated per process (tokens do not survive restarts - intentional).
- SQLite is only allowed in dev; non-dev must use PostgreSQL.
"""

import logging
import secrets
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_EPHEMERAL_SECRET = "dev-only-change-me"  # nosec B105


class Settings(BaseSettings):
    """Runtime settings for a WorldView service.

    Every value can be overridden via environment variables or a ``.env`` file.
    Secrets must never be committed; use environment/KMS in production.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True
    )

    # --- global ---
    env: str = "dev"
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    region_key: str = Field(default="us-east-1", validation_alias="REGION_KEY")
    service_name: str = "service"
    cors_origins: list[str] = Field(default=["*"], validation_alias="CORS_ORIGINS")

    # --- database ---
    database_url: str = Field(
        default="sqlite:///./data/worldview.db", validation_alias="DATABASE_URL"
    )

    # --- redis (optional in dev, required for prod-grade rate limiting) ---
    redis_url: str | None = Field(default=None, validation_alias="REDIS_URL")

    # --- auth ---
    jwt_secret: str | None = Field(default=None, validation_alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_access_ttl_minutes: int = Field(default=15, validation_alias="JWT_ACCESS_TTL_MINUTES")
    jwt_refresh_ttl_days: int = Field(default=30, validation_alias="JWT_REFRESH_TTL_DAYS")
    jwt_refresh_ttl_days: int = Field(default=30, validation_alias="JWT_REFRESH_TTL_DAYS")

    # --- observability ---
    sentry_dsn: str | None = Field(default=None, validation_alias="SENTRY_DSN")
    metrics_enabled: bool = Field(default=True, validation_alias="METRICS_ENABLED")

    # --- external AI (used by ai-guide) ---
    ai_provider: str = Field(default="mock", validation_alias="AI_PROVIDER")
    model_gateway_url: str | None = Field(default=None, validation_alias="AI_MODEL_GATEWAY_URL")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def _enforce_secret_policy(self) -> "Settings":
        if self.env != "dev":
            if (
                not self.jwt_secret
                or self.jwt_secret == _EPHEMERAL_SECRET
                or len(self.jwt_secret) < 32
            ):
                raise ValueError(
                    "JWT_SECRET must be set and at least 32 chars in non-dev environments"
                )
            if self.database_url.startswith("sqlite"):
                raise ValueError(
                    "SQLite is not allowed in non-dev environments; set DATABASE_URL to PostgreSQL"
                )
            if self.jwt_algorithm not in {"HS256", "HS384", "HS512"}:
                raise ValueError("JWT_ALGORITHM must be an HMAC algorithm in non-dev environments")
        elif not self.jwt_secret:
            self.jwt_secret = secrets.token_urlsafe(48)
            logging.getLogger("worldview").warning(
                "JWT_SECRET not set in dev - generated ephemeral secret; "
                "tokens will not survive restarts"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (one per process)."""
    return Settings()


def reset_settings() -> None:
    """Clear the cached settings (used by tests between env changes)."""
    get_settings.cache_clear()
