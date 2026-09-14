"""Provider-neutral HTTP response models."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from options_analysis.config import EnvironmentName
from options_analysis.domain import (
    OptionChain,
    PositionAnalysis,
    PositionRequestLeg,
    Quote,
    StrategyDraft,
    StrategyTemplate,
    ValuationMode,
    WatchlistItem,
)
from options_analysis.errors import ErrorDetail


class WebModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ServerInfo(WebModel):
    name: str
    version: str
    environment: EnvironmentName
    read_only: bool
    default_market_data_provider: str
    frontend_available: bool


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


class AddWatchlistItemRequest(WebModel):
    symbol: str


class WatchlistResult(WebModel):
    items: tuple[WatchlistItem, ...] = ()
    error: ErrorDetail | None = None


class StrategyCatalogResult(WebModel):
    strategies: tuple[StrategyTemplate, ...] = ()
    error: ErrorDetail | None = None


class StrategyDraftResult(WebModel):
    draft: StrategyDraft | None = None
    error: ErrorDetail | None = None


class StrategyDraftListResult(WebModel):
    drafts: tuple[StrategyDraft, ...] = ()
    error: ErrorDetail | None = None


class AnalyzePositionsRequest(WebModel):
    legs: tuple[PositionRequestLeg, ...] = Field(min_length=1, max_length=100)
    provider: str | None = None
    valuation_mode: ValuationMode = ValuationMode.MARK
    scenario_moves: tuple[Decimal, ...] = (
        Decimal("-0.20"),
        Decimal("-0.10"),
        Decimal("0"),
        Decimal("0.10"),
        Decimal("0.20"),
    )


class PositionAnalysisResult(WebModel):
    analysis: PositionAnalysis | None = None
    error: ErrorDetail | None = None
