"""Deterministic offline provider used to prove the adapter boundary."""

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

_AS_OF = datetime(2026, 1, 2, 15, 30, tzinfo=UTC)
_EXPIRATIONS = (date(2030, 1, 18), date(2030, 2, 15))
_OPTION_PATTERN = re.compile(
    r"^(?P<underlying>[A-Z.]+)(?P<expiry>\d{6})(?P<side>[CP])(?P<strike>\d{8})$"
)


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
            for strike in (Decimal("95"), Decimal("100"), Decimal("105"))
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
        bar_end = min(query.end, query.start + timedelta(days=1))
        return (
            PriceBar(
                provider_id="fake",
                instrument=quote.instrument,
                start=query.start,
                end=bar_end,
                open=Decimal("99"),
                high=Decimal("101"),
                low=Decimal("98"),
                close=Decimal("100"),
                volume=1_000_000,
            ),
        )

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
        mark = Decimal("5.00") - distance / Decimal("2")
        mark = max(mark, Decimal("0.50"))
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
