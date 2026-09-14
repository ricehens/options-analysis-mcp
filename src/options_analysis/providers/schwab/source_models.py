"""Tolerant source models for the Schwab fields used by canonical mapping."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, RootModel


class SourceModel(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class SchwabQuoteFields(SourceModel):
    bid: Decimal | None = Field(default=None, alias="bidPrice")
    ask: Decimal | None = Field(default=None, alias="askPrice")
    bid_size: int | None = Field(default=None, alias="bidSize")
    ask_size: int | None = Field(default=None, alias="askSize")
    last: Decimal | None = Field(default=None, alias="lastPrice")
    last_size: int | None = Field(default=None, alias="lastSize")
    mark: Decimal | None = None
    underlying_price: Decimal | None = Field(default=None, alias="underlyingPrice")
    volume: int | None = Field(default=None, alias="totalVolume")
    open_interest: int | None = Field(default=None, alias="openInterest")
    implied_volatility: Decimal | None = Field(default=None, alias="volatility")
    delta: Decimal | None = None
    gamma: Decimal | None = None
    theta: Decimal | None = None
    vega: Decimal | None = None
    rho: Decimal | None = None
    theoretical_value: Decimal | None = Field(
        default=None, alias="theoreticalOptionValue"
    )
    quote_time: int | None = Field(default=None, alias="quoteTime")
    trade_time: int | None = Field(default=None, alias="tradeTime")
    exchange: str | None = Field(default=None, alias="lastMICId")
    security_status: str | None = Field(default=None, alias="securityStatus")


class SchwabReference(SourceModel):
    contract_type: str | None = Field(default=None, alias="contractType")
    strike_price: Decimal | None = Field(default=None, alias="strikePrice")
    expiration_year: int | None = Field(default=None, alias="expirationYear")
    expiration_month: int | None = Field(default=None, alias="expirationMonth")
    expiration_day: int | None = Field(default=None, alias="expirationDay")
    last_trading_day: int | None = Field(default=None, alias="lastTradingDay")
    multiplier: Decimal | None = None
    settlement_type: str | None = Field(default=None, alias="settlementType")
    exercise_type: str | None = Field(default=None, alias="exerciseType")
    is_non_standard: bool | None = Field(default=None, alias="isNonStandard")
    underlying: str | None = None


class SchwabQuoteEntry(SourceModel):
    symbol: str
    asset_main_type: str = Field(alias="assetMainType")
    asset_sub_type: str | None = Field(default=None, alias="assetSubType")
    quote_type: str | None = Field(default=None, alias="quoteType")
    realtime: bool | None = None
    quote: SchwabQuoteFields = Field(default_factory=SchwabQuoteFields)
    reference: SchwabReference = Field(default_factory=SchwabReference)


class SchwabQuoteResponse(RootModel[dict[str, SchwabQuoteEntry]]):
    pass


class SchwabExpiration(SourceModel):
    expiration_date: str = Field(alias="expirationDate")
    days_to_expiration: int | None = Field(default=None, alias="daysToExpiration")
    expiration_type: str | None = Field(default=None, alias="expirationType")
    settlement_type: str | None = Field(default=None, alias="settlementType")
    option_roots: str | None = Field(default=None, alias="optionRoots")
    standard: bool | None = None


class SchwabExpirationResponse(SourceModel):
    status: str | None = None
    expiration_list: tuple[SchwabExpiration, ...] = Field(
        default=(), alias="expirationList"
    )


class SchwabChainContract(SourceModel):
    symbol: str | None = None
    put_call: str | None = Field(default=None, alias="putCall")
    strike_price: Decimal | None = Field(default=None, alias="strikePrice")
    expiration_date: int | None = Field(default=None, alias="expirationDate")
    last_trading_day: int | None = Field(default=None, alias="lastTradingDay")
    multiplier: Decimal | None = None
    settlement_type: str | None = Field(default=None, alias="settlementType")
    expiration_type: str | None = Field(default=None, alias="expirationType")
    non_standard: bool | None = Field(default=None, alias="nonStandard")
    bid: Decimal | None = None
    ask: Decimal | None = None
    bid_size: int | None = Field(default=None, alias="bidSize")
    ask_size: int | None = Field(default=None, alias="askSize")
    last: Decimal | None = None
    last_size: int | None = Field(default=None, alias="lastSize")
    mark: Decimal | None = None
    underlying_price: Decimal | None = Field(default=None, alias="underlyingPrice")
    total_volume: int | None = Field(default=None, alias="totalVolume")
    open_interest: int | None = Field(default=None, alias="openInterest")
    volatility: Decimal | None = None
    delta: Decimal | None = None
    gamma: Decimal | None = None
    theta: Decimal | None = None
    vega: Decimal | None = None
    rho: Decimal | None = None
    theoretical_value: Decimal | None = Field(
        default=None, alias="theoreticalOptionValue"
    )
    quote_time: int | None = Field(default=None, alias="quoteTime")
    trade_time: int | None = Field(default=None, alias="tradeTime")
    exchange: str | None = Field(default=None, alias="exchangeName")


ExpirationMap = dict[str, dict[str, list[SchwabChainContract]]]


class SchwabChainResponse(SourceModel):
    symbol: str
    status: str | None = None
    is_delayed: bool | None = Field(default=None, alias="isDelayed")
    underlying_price: Decimal | None = Field(default=None, alias="underlyingPrice")
    number_of_contracts: int | None = Field(default=None, alias="numberOfContracts")
    call_map: ExpirationMap = Field(default_factory=dict, alias="callExpDateMap")
    put_map: ExpirationMap = Field(default_factory=dict, alias="putExpDateMap")


class SchwabCandle(SourceModel):
    start_ms: int = Field(alias="datetime")
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int | None = None


class SchwabPriceHistoryResponse(SourceModel):
    symbol: str
    empty: bool = False
    candles: tuple[SchwabCandle, ...] = ()
