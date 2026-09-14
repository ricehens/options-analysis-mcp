"""Environment-backed application configuration with safe public output."""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
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
    """Local process settings; future secrets use SecretStr fields."""

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

    def public_view(self) -> PublicSettings:
        return PublicSettings(
            environment=self.environment,
            enabled_providers=self.enabled_providers,
            default_market_data_provider=self.default_market_data_provider,
            allow_live_smoke_tests=self.allow_live_smoke_tests,
        )
