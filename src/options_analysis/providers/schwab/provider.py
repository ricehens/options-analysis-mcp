"""Schwab provider identity and Milestone 2 gateway composition."""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

import httpx

from options_analysis.config import AppSettings
from options_analysis.domain import OptionChain, PriceBar, Quote
from options_analysis.providers import (
    AuthenticationType,
    Capability,
    FreshnessMode,
    OptionChainQuery,
    PriceHistoryQuery,
    ProviderAuthStatus,
    ProviderDescriptor,
    ProviderStatus,
)
from options_analysis.providers.schwab.config import SchwabConfig
from options_analysis.providers.schwab.gateway import SchwabGateway
from options_analysis.providers.schwab.manager import SchwabTokenManager
from options_analysis.providers.schwab.mapping import SchwabMapper
from options_analysis.providers.schwab.oauth import (
    AuthorizationRequest,
    SchwabOAuthClient,
)
from options_analysis.providers.schwab.tokens import OAuthToken, TokenStore


class SchwabProvider:
    def __init__(
        self,
        config: SchwabConfig,
        oauth: SchwabOAuthClient,
        tokens: SchwabTokenManager,
        gateway: SchwabGateway,
        mapper: SchwabMapper,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config
        self._oauth = oauth
        self._tokens = tokens
        self.gateway = gateway
        self._mapper = mapper
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id="schwab",
            display_name="Charles Schwab",
            version="1",
            authentication_type=AuthenticationType.OAUTH,
            capabilities=frozenset(
                {
                    Capability.UNDERLYING_QUOTES,
                    Capability.OPTION_EXPIRATIONS,
                    Capability.OPTION_CHAINS,
                    Capability.OPTION_QUOTES,
                    Capability.PROVIDER_GREEKS,
                    Capability.OPEN_INTEREST,
                    Capability.PRICE_HISTORY,
                }
            ),
            freshness_modes=frozenset({FreshnessMode.REALTIME, FreshnessMode.DELAYED}),
        )

    def status(self) -> ProviderStatus:
        auth = self.auth_status()
        return ProviderStatus(
            descriptor=self.descriptor,
            configured=auth.configured,
            ready=auth.authorized,
            message=(
                "Read-only Schwab market-data adapter is ready."
                if auth.authorized
                else auth.message
            ),
        )

    def auth_status(self) -> ProviderAuthStatus:
        return self._tokens.status()

    def authorization_request(self) -> AuthorizationRequest:
        return self._oauth.authorization_request()

    async def complete_authorization(
        self, callback_url: str, expected_state: str
    ) -> OAuthToken:
        return await self._tokens.store_callback(callback_url, expected_state)

    async def get_underlying_quote(self, symbol: str) -> Quote:
        normalized = self._symbol(symbol)
        payload = await self.gateway.get_json(
            "/quotes",
            params={"symbols": normalized, "fields": "quote,reference"},
        )
        return self._mapper.quote(payload, normalized)

    async def get_option_expirations(self, underlying_symbol: str) -> tuple[date, ...]:
        normalized = self._symbol(underlying_symbol)
        payload = await self.gateway.get_json(
            "/expirationchain", params={"symbol": normalized}
        )
        return self._mapper.expirations(payload)

    async def get_option_chain(self, query: OptionChainQuery) -> OptionChain:
        from_date, to_date = self._chain_date_range(query)
        strike_count = query.limit if query.put_call else max(1, (query.limit + 1) // 2)
        params = {
            "symbol": query.underlying_symbol,
            "contractType": (query.put_call.value.upper() if query.put_call else "ALL"),
            "strategy": "SINGLE",
            "includeUnderlyingQuote": "true",
            "strikeCount": str(min(strike_count, 50)),
            "fromDate": from_date.isoformat(),
            "toDate": to_date.isoformat(),
        }
        if query.strike_from is not None and query.strike_to == query.strike_from:
            params["strike"] = str(query.strike_from)
        payload = await self.gateway.get_json("/chains", params=params)
        return self._mapper.option_chain(payload, query)

    async def get_option_quotes(self, symbols: tuple[str, ...]) -> tuple[Quote, ...]:
        if not symbols or len(symbols) > 100:
            raise ValueError("between 1 and 100 option symbols are required")
        payload = await self.gateway.get_json(
            "/quotes",
            params={"symbols": ",".join(symbols), "fields": "quote,reference"},
        )
        return self._mapper.option_quotes(payload, symbols)

    async def get_price_history(self, query: PriceHistoryQuery) -> tuple[PriceBar, ...]:
        frequency_type, frequency = self._history_frequency(query.resolution)
        payload = await self.gateway.get_json(
            "/pricehistory",
            params={
                "symbol": query.symbol,
                "frequencyType": frequency_type,
                "frequency": str(frequency),
                "startDate": str(int(query.start.timestamp() * 1000)),
                "endDate": str(int(query.end.timestamp() * 1000)),
                "needExtendedHoursData": "false",
                "needPreviousClose": "false",
            },
        )
        return self._mapper.price_history(payload, query)

    async def smoke_read(self, symbol: str) -> dict[str, str | int | bool]:
        normalized = symbol.strip().upper()
        payload = await self.gateway.get_json(
            "/quotes", params={"symbols": normalized, "fields": "quote"}
        )
        return {
            "ok": True,
            "provider_id": "schwab",
            "symbol": normalized,
            "response_kind": "object" if isinstance(payload, dict) else "array",
            "top_level_items": len(payload),
        }

    @staticmethod
    def _symbol(value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol cannot be empty")
        return normalized

    @staticmethod
    def _history_frequency(resolution: str) -> tuple[str, int]:
        frequencies = {
            "1m": ("minute", 1),
            "5m": ("minute", 5),
            "10m": ("minute", 10),
            "15m": ("minute", 15),
            "30m": ("minute", 30),
            "1d": ("daily", 1),
            "1w": ("weekly", 1),
            "1mo": ("monthly", 1),
        }
        try:
            return frequencies[resolution.lower()]
        except KeyError as error:
            raise ValueError(
                "resolution must be one of 1m, 5m, 10m, 15m, 30m, 1d, 1w, 1mo"
            ) from error

    def _chain_date_range(self, query: OptionChainQuery) -> tuple[date, date]:
        today = self._clock().date()
        if query.expiration_from is None and query.expiration_to is None:
            return today, today + timedelta(days=45)
        if query.expiration_from is None:
            assert query.expiration_to is not None
            return query.expiration_to - timedelta(days=45), query.expiration_to
        if query.expiration_to is None:
            return query.expiration_from, query.expiration_from + timedelta(days=45)
        return query.expiration_from, query.expiration_to


def build_schwab_provider(
    settings: AppSettings,
    *,
    client: httpx.AsyncClient | None = None,
    clock: Callable[[], datetime] | None = None,
) -> SchwabProvider:
    config = SchwabConfig.from_settings(settings)
    http_client = client or httpx.AsyncClient(
        timeout=httpx.Timeout(config.http_timeout_seconds),
        follow_redirects=False,
    )
    oauth = SchwabOAuthClient(config, http_client, clock=clock)
    store = TokenStore(config.token_path)
    tokens = SchwabTokenManager(config, oauth, store, clock=clock)
    mapper = SchwabMapper(clock=clock)
    gateway = SchwabGateway(
        config.market_data_base_url,
        tokens,
        http_client,
        max_attempts=config.http_max_attempts,
        max_response_bytes=config.http_max_response_bytes,
    )
    return SchwabProvider(config, oauth, tokens, gateway, mapper, clock=clock)
