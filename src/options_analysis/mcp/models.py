"""Structured, secret-safe MCP foundation-tool results."""

from pydantic import BaseModel, ConfigDict

from options_analysis.config import EnvironmentName


class MCPResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ServerInfoResult(MCPResult):
    server_name: str
    version: str
    environment: EnvironmentName
    transport: str
    read_only: bool
    allow_live_smoke_tests: bool
    feature_groups: tuple[str, ...]


class ProviderSummary(MCPResult):
    provider_id: str
    display_name: str
    version: str
    authentication_type: str
    capabilities: tuple[str, ...]
    freshness_modes: tuple[str, ...]
    configured: bool
    ready: bool
    message: str | None


class ProviderListResult(MCPResult):
    providers: tuple[ProviderSummary, ...]
    defaults: dict[str, str]


class ProviderAuthStatusResult(MCPResult):
    provider_id: str
    authentication_type: str
    state: str
    configured: bool
    authorized: bool
    expires_at: str | None
    reauthorization_required: bool
    message: str | None
