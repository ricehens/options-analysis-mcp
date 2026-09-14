"""Map Schwab response models into provider-neutral domain objects."""

import re
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from options_analysis.analytics import quote_quality_warnings
from options_analysis.domain import (
    AssetType,
    DataQualityWarning,
    ExerciseStyle,
    FieldProvenance,
    Instrument,
    OptionChain,
    OptionGreeks,
    OptionTerms,
    PriceBar,
    ProvenanceKind,
    PutCall,
    Quote,
    SettlementType,
)
from options_analysis.providers import OptionChainQuery, PriceHistoryQuery
from options_analysis.providers.errors import (
    InstrumentNotFoundError,
    ProviderResponseSchemaError,
)
from options_analysis.providers.schwab.source_models import (
    SchwabChainContract,
    SchwabChainResponse,
    SchwabExpirationResponse,
    SchwabPriceHistoryResponse,
    SchwabQuoteEntry,
    SchwabQuoteFields,
    SchwabQuoteResponse,
    SchwabReference,
)

_OCC_PATTERN = re.compile(
    r"^(?P<root>[A-Z0-9.$]{1,8})(?P<expiry>\d{6})"
    r"(?P<side>[CP])(?P<strike>\d{8})$"
)


class SchwabMapper:
    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))

    def quote(self, payload: object, requested_symbol: str) -> Quote:
        entries = self._parse_quotes(payload)
        normalized = requested_symbol.strip().upper()
        source = entries.get(normalized)
        if source is None:
            source = next(
                (
                    entry
                    for symbol, entry in entries.items()
                    if symbol.replace(" ", "").upper() == normalized.replace(" ", "")
                ),
                None,
            )
        if source is None:
            raise InstrumentNotFoundError("schwab", normalized)
        try:
            return self._map_quote_entry(source)
        except (ValidationError, ValueError) as error:
            raise _schema_error(
                "Schwab quote fields could not be normalized.", error
            ) from error

    def option_quotes(
        self, payload: object, requested_symbols: tuple[str, ...]
    ) -> tuple[Quote, ...]:
        entries = self._parse_quotes(payload)
        by_compact_symbol = {
            symbol.replace(" ", "").upper(): entry for symbol, entry in entries.items()
        }
        results: list[Quote] = []
        for requested in requested_symbols:
            source = by_compact_symbol.get(requested.replace(" ", "").upper())
            if source is None:
                raise InstrumentNotFoundError("schwab", requested)
            try:
                quote = self._map_quote_entry(source)
            except (ValidationError, ValueError) as error:
                raise _schema_error(
                    f"Schwab quote fields could not be normalized for {requested!r}.",
                    error,
                ) from error
            if quote.instrument.asset_type is not AssetType.OPTION:
                raise ProviderResponseSchemaError(
                    f"Schwab returned a non-option instrument for {requested!r}."
                )
            results.append(quote)
        return tuple(results)

    def expirations(self, payload: object) -> tuple[date, ...]:
        try:
            response = SchwabExpirationResponse.model_validate(payload)
            self._require_success(response.status, "expiration")
            return tuple(
                sorted(
                    {
                        date.fromisoformat(item.expiration_date)
                        for item in response.expiration_list
                    }
                )
            )
        except (ValidationError, ValueError) as error:
            raise _schema_error(
                "Schwab expiration response did not match the expected schema.",
                error,
            ) from error

    def option_chain(self, payload: object, query: OptionChainQuery) -> OptionChain:
        try:
            response = SchwabChainResponse.model_validate(payload)
            self._require_success(response.status, "option-chain", allow_partial=True)
        except ValidationError as error:
            raise _schema_error(
                "Schwab option-chain response did not match the expected schema.",
                error,
            ) from error

        received = self._clock()
        contracts: list[Quote] = []
        skipped = 0
        maps = (response.call_map, response.put_map)
        for source in self._chain_contracts(maps):
            try:
                quote = self._map_chain_contract(
                    source, response.symbol.strip().upper(), received
                )
            except (ProviderResponseSchemaError, ValidationError, ValueError):
                skipped += 1
                continue
            option = quote.instrument.option
            if option is None or not self._matches_query(option, query):
                continue
            contracts.append(quote)

        contracts.sort(key=self._contract_sort_key)
        contracts = contracts[: query.limit]
        warnings: list[DataQualityWarning] = []
        provider_reported_partial = (
            response.status is not None and response.status.upper() == "PARTIAL"
        )
        if skipped or provider_reported_partial:
            warnings.append(
                DataQualityWarning(
                    code="partial_response",
                    message=(
                        f"Skipped {skipped} contract(s) with missing identity fields."
                        if skipped
                        else "Schwab marked the option-chain response as partial."
                    ),
                    fields=("contracts",),
                )
            )
        if not contracts:
            warnings.append(
                DataQualityWarning(
                    code="empty_chain",
                    message="No option contracts matched the request.",
                    fields=("contracts",),
                )
            )

        as_of = max((item.as_of for item in contracts), default=received)
        underlying_quote = self._underlying_quote(
            response.symbol, response.underlying_price, received
        )
        return OptionChain(
            provider_id="schwab",
            underlying_symbol=response.symbol,
            as_of=as_of,
            underlying_quote=underlying_quote,
            contracts=tuple(contracts),
            warnings=tuple(warnings),
        )

    def price_history(
        self, payload: object, query: PriceHistoryQuery
    ) -> tuple[PriceBar, ...]:
        try:
            response = SchwabPriceHistoryResponse.model_validate(payload)
            if response.empty:
                return ()
            instrument = self._equity_instrument(response.symbol)
            duration = self._resolution_duration(query.resolution)
            return tuple(
                PriceBar(
                    provider_id="schwab",
                    instrument=instrument,
                    start=self._from_epoch_millis(candle.start_ms),
                    end=self._from_epoch_millis(candle.start_ms) + duration,
                    open=candle.open,
                    high=candle.high,
                    low=candle.low,
                    close=candle.close,
                    volume=candle.volume,
                )
                for candle in response.candles
            )
        except (ValidationError, ValueError) as error:
            raise _schema_error(
                "Schwab price-history response did not match the expected schema.",
                error,
            ) from error

    def _parse_quotes(self, payload: object) -> dict[str, SchwabQuoteEntry]:
        try:
            return SchwabQuoteResponse.model_validate(payload).root
        except ValidationError as error:
            raise _schema_error(
                "Schwab quote response did not match the expected schema.", error
            ) from error

    def _map_quote_entry(self, source: SchwabQuoteEntry) -> Quote:
        received = self._clock()
        asset_type = self._asset_type(source.asset_main_type, source.asset_sub_type)
        if asset_type is AssetType.OPTION:
            instrument = self._option_instrument(source.symbol, source.reference)
        else:
            instrument = Instrument(
                asset_type=asset_type,
                symbol=source.symbol,
                provider_id="schwab",
                provider_symbol=source.symbol,
            )
        return self._quote_from_fields(
            instrument,
            source.quote,
            received,
            extensions=self._extensions(
                **{
                    "asset_main_type": source.asset_main_type,
                    "asset_sub_type": source.asset_sub_type,
                    "quote_type": source.quote_type,
                    "realtime": source.realtime,
                }
            ),
        )

    def _quote_from_fields(
        self,
        instrument: Instrument,
        fields: SchwabQuoteFields,
        received: datetime,
        *,
        extensions: dict[str, Any] | None = None,
    ) -> Quote:
        timestamp = fields.quote_time or fields.trade_time
        as_of = self._from_epoch_millis(timestamp) if timestamp else received
        greeks = self._greeks(
            fields.delta, fields.gamma, fields.theta, fields.vega, fields.rho
        )
        implied_volatility = self._implied_volatility(fields.implied_volatility)
        warnings = list(
            quote_quality_warnings(
                bid=fields.bid,
                ask=fields.ask,
                mark=fields.mark,
                age=max(received - as_of, timedelta()),
                is_option=instrument.asset_type is AssetType.OPTION,
                open_interest=fields.open_interest,
                implied_volatility=implied_volatility,
                has_greeks=greeks is not None,
                timestamp_missing=timestamp is None,
            )
        )
        warnings.extend(self._partial_greek_warnings(greeks))
        values = {
            "bid": fields.bid,
            "ask": fields.ask,
            "last": fields.last,
            "mark": fields.mark,
            "underlying_price": fields.underlying_price,
            "volume": fields.volume,
            "open_interest": fields.open_interest,
            "implied_volatility": implied_volatility,
            "greeks": greeks,
            "theoretical_value": fields.theoretical_value,
        }
        return Quote(
            instrument=instrument,
            provider_id="schwab",
            as_of=as_of,
            received_at=received,
            bid=fields.bid,
            ask=fields.ask,
            bid_size=fields.bid_size,
            ask_size=fields.ask_size,
            last=fields.last,
            last_size=fields.last_size,
            mark=fields.mark,
            underlying_price=fields.underlying_price,
            volume=fields.volume,
            open_interest=fields.open_interest,
            implied_volatility=implied_volatility,
            greeks=greeks,
            theoretical_value=fields.theoretical_value,
            exchange=fields.exchange,
            security_status=fields.security_status,
            field_provenance=self._provenance(as_of, values),
            provider_extensions=extensions or {},
            warnings=tuple(warnings),
        )

    def _map_chain_contract(
        self, source: SchwabChainContract, underlying: str, received: datetime
    ) -> Quote:
        if (
            source.symbol is None
            or source.put_call is None
            or source.strike_price is None
            or source.expiration_date is None
        ):
            raise ProviderResponseSchemaError(
                "Schwab chain contract is missing identity fields."
            )
        side = self._put_call(source.put_call)
        expiration = self._from_epoch_millis(source.expiration_date).date()
        terms = OptionTerms(
            underlying_symbol=underlying,
            option_root=underlying,
            expiration_date=expiration,
            last_trading_datetime=(
                self._from_epoch_millis(source.last_trading_day)
                if source.last_trading_day
                else None
            ),
            put_call=side,
            strike=source.strike_price,
            multiplier=source.multiplier or Decimal("100"),
            settlement_type=self._settlement(source.settlement_type),
            is_adjusted=source.non_standard,
        )
        compact_symbol = source.symbol.replace(" ", "").upper()
        instrument = Instrument(
            asset_type=AssetType.OPTION,
            symbol=compact_symbol,
            provider_id="schwab",
            provider_symbol=source.symbol,
            occ_symbol=compact_symbol,
            option=terms,
        )
        fields = SchwabQuoteFields.model_construct(
            bid=source.bid,
            ask=source.ask,
            bid_size=source.bid_size,
            ask_size=source.ask_size,
            last=source.last,
            last_size=source.last_size,
            mark=source.mark,
            underlying_price=source.underlying_price,
            volume=source.total_volume,
            open_interest=source.open_interest,
            implied_volatility=source.volatility,
            delta=source.delta,
            gamma=source.gamma,
            theta=source.theta,
            vega=source.vega,
            rho=source.rho,
            theoretical_value=source.theoretical_value,
            quote_time=source.quote_time,
            trade_time=source.trade_time,
            exchange=source.exchange,
            security_status=None,
        )
        return self._quote_from_fields(
            instrument,
            fields,
            received,
            extensions=self._extensions(
                expiration_type=source.expiration_type,
                non_standard=source.non_standard,
            ),
        )

    def _option_instrument(
        self, provider_symbol: str, reference: SchwabReference
    ) -> Instrument:
        compact = provider_symbol.replace(" ", "").upper()
        parsed = _OCC_PATTERN.fullmatch(compact)
        side_text = reference.contract_type or (
            parsed.group("side") if parsed else None
        )
        strike = reference.strike_price
        expiration: date | None = None
        if (
            reference.expiration_year is not None
            and reference.expiration_month is not None
            and reference.expiration_day is not None
        ):
            expiration = date(
                reference.expiration_year,
                reference.expiration_month,
                reference.expiration_day,
            )
        elif parsed is not None:
            expiration = datetime.strptime(parsed.group("expiry"), "%y%m%d").date()
        if strike is None and parsed is not None:
            strike = Decimal(parsed.group("strike")) / Decimal("1000")
        if side_text is None or strike is None or expiration is None:
            raise ProviderResponseSchemaError(
                f"Schwab option identity is incomplete for {provider_symbol!r}."
            )
        root = reference.underlying or (parsed.group("root") if parsed else None)
        if root is None:
            raise ProviderResponseSchemaError(
                f"Schwab option underlying is missing for {provider_symbol!r}."
            )
        terms = OptionTerms(
            underlying_symbol=root,
            option_root=root,
            expiration_date=expiration,
            last_trading_datetime=(
                self._from_epoch_millis(reference.last_trading_day)
                if reference.last_trading_day
                else None
            ),
            put_call=self._put_call(side_text),
            strike=strike,
            multiplier=reference.multiplier or Decimal("100"),
            exercise_style=self._exercise_style(reference.exercise_type),
            settlement_type=self._settlement(reference.settlement_type),
            is_adjusted=(
                reference.is_non_standard
                if reference.is_non_standard is not None
                else None
            ),
        )
        return Instrument(
            asset_type=AssetType.OPTION,
            symbol=compact,
            provider_id="schwab",
            provider_symbol=provider_symbol,
            occ_symbol=compact,
            option=terms,
        )

    def _underlying_quote(
        self, symbol: str, price: Decimal | None, received: datetime
    ) -> Quote | None:
        if price is None:
            return None
        instrument = self._equity_instrument(symbol)
        provenance = self._provenance(received, {"mark": price})
        return Quote(
            instrument=instrument,
            provider_id="schwab",
            as_of=received,
            received_at=received,
            mark=price,
            field_provenance=provenance,
            warnings=quote_quality_warnings(
                bid=None,
                ask=None,
                mark=price,
                age=timedelta(),
                is_option=False,
                timestamp_missing=True,
            ),
        )

    @staticmethod
    def _chain_contracts(
        maps: Iterable[dict[str, dict[str, list[SchwabChainContract]]]],
    ) -> Iterable[SchwabChainContract]:
        for expiration_map in maps:
            for strike_map in expiration_map.values():
                for contracts in strike_map.values():
                    yield from contracts

    @staticmethod
    def _matches_query(option: OptionTerms, query: OptionChainQuery) -> bool:
        return not (
            (query.put_call is not None and option.put_call is not query.put_call)
            or (
                query.expiration_from is not None
                and option.expiration_date < query.expiration_from
            )
            or (
                query.expiration_to is not None
                and option.expiration_date > query.expiration_to
            )
            or (query.strike_from is not None and option.strike < query.strike_from)
            or (query.strike_to is not None and option.strike > query.strike_to)
        )

    @staticmethod
    def _contract_sort_key(quote: Quote) -> tuple[date, Decimal, str]:
        option = quote.instrument.option
        if option is None:
            raise ValueError("option quote has no terms")
        return (option.expiration_date, option.strike, option.put_call.value)

    @staticmethod
    def _provenance(
        as_of: datetime, values: Mapping[str, object | None]
    ) -> dict[str, FieldProvenance]:
        source = FieldProvenance(
            kind=ProvenanceKind.PROVIDER, provider_id="schwab", as_of=as_of
        )
        return {name: source for name, value in values.items() if value is not None}

    @staticmethod
    def _greeks(
        delta: Decimal | None,
        gamma: Decimal | None,
        theta: Decimal | None,
        vega: Decimal | None,
        rho: Decimal | None,
    ) -> OptionGreeks | None:
        if all(value is None for value in (delta, gamma, theta, vega, rho)):
            return None
        return OptionGreeks(delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho)

    @staticmethod
    def _partial_greek_warnings(
        greeks: OptionGreeks | None,
    ) -> tuple[DataQualityWarning, ...]:
        if greeks is None:
            return ()
        missing = tuple(
            name
            for name in ("delta", "gamma", "theta", "vega", "rho")
            if getattr(greeks, name) is None
        )
        if not missing:
            return ()
        return (
            DataQualityWarning(
                code="partial_greeks",
                message="One or more provider Greeks are unavailable.",
                fields=missing,
            ),
        )

    @staticmethod
    def _extensions(**values: object) -> dict[str, Any]:
        return {
            f"schwab.{name}": value
            for name, value in values.items()
            if value is not None
        }

    @staticmethod
    def _implied_volatility(value: Decimal | None) -> Decimal | None:
        """Schwab exposes volatility as percentage points; canonical uses a ratio."""

        return None if value is None else value / Decimal("100")

    @staticmethod
    def _require_success(
        status: str | None, response_name: str, *, allow_partial: bool = False
    ) -> None:
        if status is None:
            return
        allowed = {"SUCCESS"}
        if allow_partial:
            allowed.add("PARTIAL")
        if status.upper() not in allowed:
            raise ProviderResponseSchemaError(
                f"Schwab {response_name} response reported status {status!r}."
            )

    @staticmethod
    def _asset_type(main_type: str, sub_type: str | None) -> AssetType:
        normalized = main_type.upper()
        if normalized == "OPTION":
            return AssetType.OPTION
        if normalized in {"INDEX", "INDEX_OPTION"}:
            return AssetType.INDEX
        if sub_type and sub_type.upper() == "ETF":
            return AssetType.ETF
        return AssetType.EQUITY

    @staticmethod
    def _put_call(value: str) -> PutCall:
        normalized = value.upper()
        if normalized in {"C", "CALL"}:
            return PutCall.CALL
        if normalized in {"P", "PUT"}:
            return PutCall.PUT
        raise ProviderResponseSchemaError(f"Unknown Schwab option side {value!r}.")

    @staticmethod
    def _settlement(value: str | None) -> SettlementType | None:
        if value is None:
            return None
        normalized = value.upper()
        if normalized in {"P", "PHYSICAL"}:
            return SettlementType.PHYSICAL
        if normalized in {"C", "CASH"}:
            return SettlementType.CASH
        return None

    @staticmethod
    def _exercise_style(value: str | None) -> ExerciseStyle | None:
        if value is None:
            return None
        normalized = value.upper()
        if normalized in {"A", "AMERICAN"}:
            return ExerciseStyle.AMERICAN
        if normalized in {"E", "EUROPEAN"}:
            return ExerciseStyle.EUROPEAN
        return None

    @staticmethod
    def _equity_instrument(symbol: str) -> Instrument:
        normalized = symbol.strip().upper()
        return Instrument(
            asset_type=AssetType.EQUITY,
            symbol=normalized,
            provider_id="schwab",
            provider_symbol=normalized,
        )

    @staticmethod
    def _from_epoch_millis(value: int) -> datetime:
        return datetime.fromtimestamp(value / 1000, tz=UTC)

    @staticmethod
    def _resolution_duration(resolution: str) -> timedelta:
        durations = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "10m": timedelta(minutes=10),
            "15m": timedelta(minutes=15),
            "30m": timedelta(minutes=30),
            "1d": timedelta(days=1),
            "1w": timedelta(weeks=1),
            "1mo": timedelta(days=31),
        }
        try:
            return durations[resolution.lower()]
        except KeyError as error:
            raise ValueError(
                f"unsupported price-history resolution: {resolution}"
            ) from error


def _schema_error(
    message: str, error: ValidationError | ValueError
) -> ProviderResponseSchemaError:
    field_paths: tuple[str, ...] = ()
    if isinstance(error, ValidationError):
        field_paths = tuple(
            ".".join(str(part) for part in item["loc"])
            for item in error.errors(include_url=False)[:5]
        )
    return ProviderResponseSchemaError(message, field_paths=field_paths)
