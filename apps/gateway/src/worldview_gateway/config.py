"""Gateway configuration: upstream addresses, rate limit, optional TLS."""

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

UPSTREAM_SERVICES = (
    "identity",
    "catalog",
    "streaming",
    "ai-guide",
    "payments",
    "creators",
    "moderation",
    "notifications",
)


class GatewaySettings(BaseSettings):
    """Gateway settings. Init kwargs take precedence over environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True
    )

    env: str = "dev"
    port: int = Field(default=8000, validation_alias="GATEWAY_PORT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    region_key: str = Field(default="us-east-1", validation_alias="REGION_KEY")

    # CORS: allowed origins (comma-separated). "*" permits any (dev only).
    cors_origins: list[str] = Field(default=["*"], validation_alias="CORS_ORIGINS")

    redis_url: str | None = Field(default=None, validation_alias="REDIS_URL")
    rate_limit_rpm: int = Field(default=600, validation_alias="GATEWAY_RATE_LIMIT_RPM")
    auth_rate_limit_rpm: int = Field(default=30, validation_alias="GATEWAY_AUTH_RATE_LIMIT_RPM")

    # Optional direct TLS termination at the gateway (dev). In production TLS is
    # terminated at the load balancer/ingress; set these to run self-signed locally.
    tls_cert_file: str | None = Field(default=None, validation_alias="GATEWAY_TLS_CERT_FILE")
    tls_key_file: str | None = Field(default=None, validation_alias="GATEWAY_TLS_KEY_FILE")

    identity_upstream: str = Field(
        default="http://localhost:8001", validation_alias="IDENTITY_UPSTREAM"
    )
    catalog_upstream: str = Field(
        default="http://localhost:8002", validation_alias="CATALOG_UPSTREAM"
    )
    streaming_upstream: str = Field(
        default="http://localhost:8003", validation_alias="STREAMING_UPSTREAM"
    )
    ai_guide_upstream: str = Field(
        default="http://localhost:8004", validation_alias="AI_GUIDE_UPSTREAM"
    )
    payments_upstream: str = Field(
        default="http://localhost:8005", validation_alias="PAYMENTS_UPSTREAM"
    )
    creators_upstream: str = Field(
        default="http://localhost:8007", validation_alias="CREATORS_UPSTREAM"
    )
    moderation_upstream: str = Field(
        default="http://localhost:8006", validation_alias="MODERATION_UPSTREAM"
    )
    notifications_upstream: str = Field(
        default="http://localhost:8008", validation_alias="NOTIFICATIONS_UPSTREAM"
    )
    gateway_upstream: str = Field(
        default="http://localhost:8000", validation_alias="GATEWAY_UPSTREAM"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def upstreams(self) -> dict[str, str]:
        return {
            "identity": self.identity_upstream,
            "catalog": self.catalog_upstream,
            "streaming": self.streaming_upstream,
            "ai-guide": self.ai_guide_upstream,
            "payments": self.payments_upstream,
            "creators": self.creators_upstream,
            "moderation": self.moderation_upstream,
            "notifications": self.notifications_upstream,
        }


@lru_cache
def get_gateway_settings() -> GatewaySettings:
    return GatewaySettings()
