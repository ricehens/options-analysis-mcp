"""Deterministic offline provider used to prove the adapter boundary."""

import math
import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from options_analysis.domain import (
    AssetType,
    FieldProvenance,
    Instrument,
    OptionChain,
    OptionGreeks,
    OptionTerms,
    PriceBar,
    ProvenanceKind,
    PutCall,
    Quote,
)
from options_analysis.providers.contracts import (
    AuthenticationType,
    Capability,
    FreshnessMode,
    OptionChainQuery,
    PriceHistoryQuery,
    ProviderDescriptor,
    ProviderStatus,
)
from options_analysis.providers.errors import InstrumentNotFoundError

_AS_OF = datetime(2026, 9, 14, 20, 0, tzinfo=UTC)
_EXPIRATIONS = (date(2030, 1, 18), date(2030, 2, 15))
_OPTION_PATTERN = re.compile(
    r"^(?P<underlying>[A-Z.]+)(?P<expiry>\d{6})(?P<side>[CP])(?P<strike>\d{8})$"
)
_HISTORY_DURATIONS = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "10m": timedelta(minutes=10),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
    "1mo": timedelta(days=31),
}
_HISTORY_BAR_LIMITS = {
    "1m": 390,
    "5m": 390,
    "10m": 240,
    "15m": 240,
    "30m": 240,
    "1d": 252,
    "1w": 260,
    "1mo": 240,
}


class FakeProvider:
    """Repeatable data with no files, credentials, clocks, or network access."""

    @property
    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id="fake",
            display_name="Deterministic Fake Provider",
            version="1",
            authentication_type=AuthenticationType.NONE,
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
            freshness_modes=frozenset({FreshnessMode.DETERMINISTIC}),
        )

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            descriptor=self.descriptor,
            configured=True,
            ready=True,
            message="Offline deterministic data only.",
        )

    async def get_underlying_quote(self, symbol: str) -> Quote:
        normalized = self._normalize_symbol(symbol)
        instrument = Instrument(
            asset_type=AssetType.EQUITY,
            symbol=normalized,
            provider_id="fake",
            provider_symbol=normalized,
        )
        return Quote(
            instrument=instrument,
            provider_id="fake",
            as_of=_AS_OF,
            received_at=_AS_OF,
            bid=Decimal("99.95"),
            ask=Decimal("100.05"),
            bid_size=10,
            ask_size=12,
            last=Decimal("100.00"),
            last_size=2,
            mark=Decimal("100.00"),
            volume=1_000_000,
            field_provenance=self._provenance("bid", "ask", "last", "mark"),
        )

    async def get_option_expirations(self, underlying_symbol: str) -> tuple[date, ...]:
        self._normalize_symbol(underlying_symbol)
        return _EXPIRATIONS

    async def get_option_chain(self, query: OptionChainQuery) -> OptionChain:
        expirations = tuple(
            expiry
            for expiry in _EXPIRATIONS
            if (query.expiration_from is None or expiry >= query.expiration_from)
            and (query.expiration_to is None or expiry <= query.expiration_to)
        )
        strikes = tuple(
            strike
            for strike in (
                Decimal("90"),
                Decimal("95"),
                Decimal("100"),
                Decimal("105"),
                Decimal("110"),
            )
            if (query.strike_from is None or strike >= query.strike_from)
            and (query.strike_to is None or strike <= query.strike_to)
        )
        sides = (query.put_call,) if query.put_call is not None else tuple(PutCall)
        contracts = tuple(
            self._option_quote(query.underlying_symbol, expiry, side, strike)
            for expiry in expirations
            for strike in strikes
            for side in sides
        )[: query.limit]
        return OptionChain(
            provider_id="fake",
            underlying_symbol=query.underlying_symbol,
            as_of=_AS_OF,
            underlying_quote=await self.get_underlying_quote(query.underlying_symbol),
            contracts=contracts,
        )

    async def get_option_quotes(self, symbols: tuple[str, ...]) -> tuple[Quote, ...]:
        quotes: list[Quote] = []
        for symbol in symbols:
            match = _OPTION_PATTERN.fullmatch(symbol.strip().upper())
            if match is None:
                raise InstrumentNotFoundError("fake", symbol)
            expiration = datetime.strptime(match.group("expiry"), "%y%m%d").date()
            side = PutCall.CALL if match.group("side") == "C" else PutCall.PUT
            strike = Decimal(match.group("strike")) / Decimal("1000")
            quotes.append(
                self._option_quote(match.group("underlying"), expiration, side, strike)
            )
        return tuple(quotes)

    async def get_price_history(self, query: PriceHistoryQuery) -> tuple[PriceBar, ...]:
        quote = await self.get_underlying_quote(query.symbol)
        try:
            duration = _HISTORY_DURATIONS[query.resolution.lower()]
            maximum = _HISTORY_BAR_LIMITS[query.resolution.lower()]
        except KeyError as error:
            raise ValueError(
                "resolution must be one of 1m, 5m, 10m, 15m, 30m, 1d, 1w, 1mo"
            ) from error
        available = max(
            1,
            math.ceil(
                (query.end - query.start).total_seconds() / duration.total_seconds()
            ),
        )
        count = min(available, maximum)
        first_start = max(query.start, query.end - duration * count)
        last_phase = (count - 1) % 18
        bars: list[PriceBar] = []
        for index in range(count):
            bar_start = first_start + duration * index
            bar_end = min(query.end, bar_start + duration)
            trend = Decimal(index - (count - 1)) * Decimal("0.015")
            wave = Decimal(index % 18 - last_phase) * Decimal("0.03")
            close = Decimal("100") + trend + wave
            open_price = close + (Decimal("0.12") if index % 2 else Decimal("-0.12"))
            high = max(open_price, close) + Decimal("0.35")
            low = min(open_price, close) - Decimal("0.35")
            bars.append(
                PriceBar(
                    provider_id="fake",
                    instrument=quote.instrument,
                    start=bar_start,
                    end=bar_end,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=900_000 + index * 1_000,
                )
            )
        return tuple(bars)

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper()
        if not normalized:
            raise InstrumentNotFoundError("fake", symbol)
        return normalized

    @staticmethod
    def _provenance(*fields: str) -> dict[str, FieldProvenance]:
        source = FieldProvenance(
            kind=ProvenanceKind.PROVIDER,
            provider_id="fake",
            as_of=_AS_OF,
        )
        return dict.fromkeys(fields, source)

    def _option_quote(
        self,
        underlying: str,
        expiration: date,
        side: PutCall,
        strike: Decimal,
    ) -> Quote:
        side_code = "C" if side is PutCall.CALL else "P"
        strike_code = f"{int(strike * 1000):08d}"
        occ_symbol = f"{underlying}{expiration:%y%m%d}{side_code}{strike_code}"
        option = OptionTerms(
            underlying_symbol=underlying,
            option_root=underlying,
            expiration_date=expiration,
            put_call=side,
            strike=strike,
            is_adjusted=False,
        )
        instrument = Instrument(
            asset_type=AssetType.OPTION,
            symbol=occ_symbol,
            provider_id="fake",
            provider_symbol=occ_symbol,
            occ_symbol=occ_symbol,
            option=option,
        )
        distance = abs(strike - Decimal("100"))
        intrinsic = (
            max(Decimal("100") - strike, Decimal())
            if side is PutCall.CALL
            else max(strike - Decimal("100"), Decimal())
        )
        time_value = max(Decimal("4.00") - distance * Decimal("0.40"), Decimal("0.50"))
        mark = intrinsic + time_value
        return Quote(
            instrument=instrument,
            provider_id="fake",
            as_of=_AS_OF,
            received_at=_AS_OF,
            bid=mark - Decimal("0.05"),
            ask=mark + Decimal("0.05"),
            mark=mark,
            underlying_price=Decimal("100"),
            volume=100,
            open_interest=1_000,
            implied_volatility=Decimal("0.25"),
            greeks=OptionGreeks(
                delta=Decimal("0.50") if side is PutCall.CALL else Decimal("-0.50"),
                gamma=Decimal("0.04"),
                theta=Decimal("-0.03"),
                vega=Decimal("0.12"),
                rho=Decimal("0.05") if side is PutCall.CALL else Decimal("-0.05"),
            ),
            field_provenance=self._provenance(
                "bid", "ask", "mark", "open_interest", "implied_volatility", "greeks"
            ),
        )
