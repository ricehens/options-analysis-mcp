"""Provider-neutral HTTP response models."""

from datetime import date

from pydantic import BaseModel, ConfigDict

from options_analysis.config import EnvironmentName
from options_analysis.domain import OptionChain, Quote
from options_analysis.errors import ErrorDetail


class WebModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ServerInfo(WebModel):
    name: str
    version: str
    environment: EnvironmentName
    read_only: bool
    default_market_data_provider: str


class ServerInfoResult(WebModel):
    info: ServerInfo | None = None
    error: ErrorDetail | None = None


class ProviderSummary(WebModel):
    provider_id: str
    display_name: str
    capabilities: tuple[str, ...]
    freshness_modes: tuple[str, ...]
    configured: bool
    ready: bool
    message: str | None


class ProviderListResult(WebModel):
    providers: tuple[ProviderSummary, ...] = ()
    default_market_data_provider: str | None = None
    error: ErrorDetail | None = None


class WorkspaceSnapshot(WebModel):
    provider_id: str
    symbol: str
    quote: Quote
    expirations: tuple[date, ...]
    chain: OptionChain


class WorkspaceResult(WebModel):
    workspace: WorkspaceSnapshot | None = None
    error: ErrorDetail | None = None
