"""Environment-backed application configuration with safe public output."""

from enum import StrEnum
from pathlib import Path
from typing import Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentName(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class PublicSettings(BaseModel):
    """Configuration fields that are safe to return through MCP."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    environment: EnvironmentName
    enabled_providers: tuple[str, ...]
    default_market_data_provider: str
    allow_live_smoke_tests: bool


class AppSettings(BaseSettings):
    """Local process settings. Secret values stay out of public views."""

    model_config = SettingsConfigDict(
        env_prefix="OPTIONS_ANALYSIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    environment: EnvironmentName = EnvironmentName.DEVELOPMENT
    enabled_providers: tuple[str, ...] = ("fake",)
    default_market_data_provider: str = "fake"
    allow_live_smoke_tests: bool = False
    snapshot_cache_ttl_seconds: float = 1.0
    snapshot_cache_max_entries: int = 512
    replay_bundle_path: Path | None = None
    replay_max_bundle_bytes: int = 25_000_000
    state_db_path: Path | None = None
    schwab_client_id: SecretStr | None = None
    schwab_client_secret: SecretStr | None = None
    schwab_redirect_uri: str = "https://127.0.0.1"
    schwab_token_path: Path | None = None
    schwab_authorization_url: str = "https://api.schwabapi.com/v1/oauth/authorize"
    schwab_token_url: str = "https://api.schwabapi.com/v1/oauth/token"
    schwab_market_data_base_url: str = "https://api.schwabapi.com/marketdata/v1"
    schwab_http_timeout_seconds: float = 10.0
    schwab_http_max_attempts: int = 3
    schwab_http_max_response_bytes: int = 5_000_000

    @field_validator("snapshot_cache_ttl_seconds")
    @classmethod
    def validate_cache_ttl(cls, value: float) -> float:
        if not 0 <= value <= 60:
            raise ValueError("snapshot cache TTL must be between 0 and 60 seconds")
        return value

    @field_validator("snapshot_cache_max_entries")
    @classmethod
    def validate_cache_size(cls, value: int) -> int:
        if not 1 <= value <= 10_000:
            raise ValueError("snapshot cache size must be between 1 and 10000")
        return value

    @field_validator("state_db_path")
    @classmethod
    def validate_state_db_path(cls, value: Path | None) -> Path | None:
        if value is None:
            return None
        expanded = value.expanduser()
        if not expanded.is_absolute():
            raise ValueError("state database path must be absolute")
        return expanded

    @field_validator("replay_bundle_path")
    @classmethod
    def validate_replay_bundle_path(cls, value: Path | None) -> Path | None:
        if value is None:
            return None
        expanded = value.expanduser()
        if not expanded.is_absolute():
            raise ValueError("replay bundle path must be absolute")
        return expanded

    @field_validator("replay_max_bundle_bytes")
    @classmethod
    def validate_replay_bundle_limit(cls, value: int) -> int:
        if not 1_024 <= value <= 100_000_000:
            raise ValueError("replay bundle limit must be between 1 KiB and 100 MB")
        return value

    @field_validator("enabled_providers")
    @classmethod
    def normalize_enabled_providers(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(item.strip().lower() for item in value))
        if not normalized or any(not item for item in normalized):
            raise ValueError("at least one non-empty provider must be enabled")
        return normalized

    @field_validator("default_market_data_provider")
    @classmethod
    def normalize_default_provider(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def default_provider_is_enabled(self) -> Self:
        if self.default_market_data_provider not in self.enabled_providers:
            raise ValueError("default market-data provider must be enabled")
        return self

    @field_validator("schwab_redirect_uri")
    @classmethod
    def validate_redirect_uri(cls, value: str) -> str:
        normalized = value.strip()
        parsed = urlsplit(normalized)
        secure = parsed.scheme == "https"
        loopback_http = parsed.scheme == "http" and parsed.hostname in {
            "127.0.0.1",
            "::1",
            "localhost",
        }
        if not secure and not loopback_http:
            raise ValueError("Schwab redirect URI must use HTTPS or loopback HTTP")
        if not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("Schwab redirect URI cannot contain a query or fragment")
        return normalized

    @field_validator("schwab_http_timeout_seconds")
    @classmethod
    def validate_timeout(cls, value: float) -> float:
        if not 0 < value <= 120:
            raise ValueError("Schwab HTTP timeout must be between 0 and 120 seconds")
        return value

    @field_validator("schwab_http_max_attempts")
    @classmethod
    def validate_attempts(cls, value: int) -> int:
        if not 1 <= value <= 5:
            raise ValueError("Schwab HTTP attempts must be between 1 and 5")
        return value

    @field_validator("schwab_http_max_response_bytes")
    @classmethod
    def validate_response_limit(cls, value: int) -> int:
        if not 1_024 <= value <= 50_000_000:
            raise ValueError("Schwab response limit must be between 1 KiB and 50 MB")
        return value

    def public_view(self) -> PublicSettings:
        return PublicSettings(
            environment=self.environment,
            enabled_providers=self.enabled_providers,
            default_market_data_provider=self.default_market_data_provider,
            allow_live_smoke_tests=self.allow_live_smoke_tests,
        )
