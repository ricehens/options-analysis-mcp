"""Read-only adapter over a validated local canonical replay bundle."""

from datetime import date
from pathlib import Path

from pydantic import ValidationError

from options_analysis.domain import Instrument, OptionChain, PriceBar, Quote
from options_analysis.providers.contracts import (
    AuthenticationType,
    Capability,
    FreshnessMode,
    OptionChainQuery,
    PriceHistoryQuery,
    ProviderDescriptor,
    ProviderStatus,
)
from options_analysis.providers.errors import (
    InstrumentNotFoundError,
    ProviderConfigurationError,
    ProviderValidationError,
)
from options_analysis.providers.replay.models import ReplayBundle, ReplaySymbolSnapshot

_PROVIDER_ID = "replay"


class ReplayProvider:
    """Serve immutable recorded snapshots without credentials or network access."""

    def __init__(self, bundle: ReplayBundle | None = None) -> None:
        self._bundle = bundle
        self._symbols = (
            {item.symbol: item for item in bundle.symbols} if bundle is not None else {}
        )
        self._options = {
            quote.instrument.provider_symbol.upper(): quote
            for item in self._symbols.values()
            for quote in item.option_chain.contracts
        }
        for item in self._symbols.values():
            for quote in item.option_chain.contracts:
                self._options.setdefault(quote.instrument.symbol.upper(), quote)

    @classmethod
    def from_path(cls, path: Path, *, max_bytes: int) -> "ReplayProvider":
        if not path.is_file():
            raise ProviderConfigurationError("replay bundle path is not a file")
        try:
            with path.open("rb") as source:
                encoded = source.read(max_bytes + 1)
            if len(encoded) > max_bytes:
                raise ProviderConfigurationError(
                    f"replay bundle exceeds configured {max_bytes}-byte limit"
                )
            bundle = ReplayBundle.model_validate_json(encoded)
        except ProviderConfigurationError:
            raise
        except (OSError, ValidationError, ValueError) as error:
            raise ProviderConfigurationError(
                "replay bundle is unreadable or fails schema validation"
            ) from error
        return cls(bundle)

    @property
    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=_PROVIDER_ID,
            display_name="Validated Snapshot Replay",
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
            freshness_modes=frozenset(
                {FreshnessMode.DETERMINISTIC, FreshnessMode.HISTORICAL}
            ),
        )

    def status(self) -> ProviderStatus:
        count = len(self._symbols)
        return ProviderStatus(
            descriptor=self.descriptor,
            configured=self._bundle is not None,
            ready=self._bundle is not None,
            message=(
                f"Loaded {count} symbol snapshot{'s' if count != 1 else ''}."
                if self._bundle is not None
                else "Set OPTIONS_ANALYSIS_REPLAY_BUNDLE_PATH to a validated bundle."
            ),
        )

    async def get_underlying_quote(self, symbol: str) -> Quote:
        snapshot = self._snapshot(symbol)
        return self._remap_quote(snapshot.underlying_quote)

    async def get_option_expirations(self, underlying_symbol: str) -> tuple[date, ...]:
        snapshot = self._snapshot(underlying_symbol)
        return tuple(
            sorted(
                {
                    quote.instrument.option.expiration_date
                    for quote in snapshot.option_chain.contracts
                    if quote.instrument.option is not None
                }
            )
        )

    async def get_option_chain(self, query: OptionChainQuery) -> OptionChain:
        snapshot = self._snapshot(query.underlying_symbol)
        contracts = tuple(
            self._remap_quote(quote)
            for quote in snapshot.option_chain.contracts
            if self._matches_chain_query(quote, query)
        )[: query.limit]
        source = snapshot.option_chain
        return OptionChain(
            provider_id=_PROVIDER_ID,
            underlying_symbol=snapshot.symbol,
            as_of=source.as_of,
            underlying_quote=self._remap_quote(snapshot.underlying_quote),
            contracts=contracts,
            warnings=source.warnings,
        )

    async def get_option_quotes(self, symbols: tuple[str, ...]) -> tuple[Quote, ...]:
        self._require_configured()
        results: list[Quote] = []
        for symbol in symbols:
            normalized = symbol.strip().upper()
            try:
                quote = self._options[normalized]
            except KeyError as error:
                raise InstrumentNotFoundError(_PROVIDER_ID, symbol) from error
            results.append(self._remap_quote(quote))
        return tuple(results)

    async def get_price_history(self, query: PriceHistoryQuery) -> tuple[PriceBar, ...]:
        snapshot = self._snapshot(query.symbol)
        resolution = query.resolution.strip().lower()
        series = next(
            (
                candidate
                for candidate in snapshot.price_history
                if candidate.resolution == resolution
            ),
            None,
        )
        if series is None:
            raise ProviderValidationError(
                f"replay bundle has no {resolution!r} history for {snapshot.symbol}"
            )
        return tuple(
            self._remap_bar(bar)
            for bar in series.bars
            if bar.end > query.start and bar.start < query.end
        )

    def _snapshot(self, symbol: str) -> ReplaySymbolSnapshot:
        self._require_configured()
        normalized = symbol.strip().upper()
        try:
            return self._symbols[normalized]
        except KeyError as error:
            raise InstrumentNotFoundError(_PROVIDER_ID, symbol) from error

    def _require_configured(self) -> None:
        if self._bundle is None:
            raise ProviderConfigurationError("replay provider is not configured")

    @staticmethod
    def _matches_chain_query(quote: Quote, query: OptionChainQuery) -> bool:
        option = quote.instrument.option
        if option is None:
            return False
        return not (
            (
                query.expiration_from is not None
                and option.expiration_date < query.expiration_from
            )
            or (
                query.expiration_to is not None
                and option.expiration_date > query.expiration_to
            )
            or (query.put_call is not None and option.put_call is not query.put_call)
            or (query.strike_from is not None and option.strike < query.strike_from)
            or (query.strike_to is not None and option.strike > query.strike_to)
        )

    @staticmethod
    def _remap_instrument(instrument: Instrument) -> Instrument:
        payload = instrument.model_dump(mode="python")
        payload["provider_id"] = _PROVIDER_ID
        return Instrument.model_validate(payload)

    @classmethod
    def _remap_quote(cls, quote: Quote) -> Quote:
        payload = quote.model_dump(mode="python")
        payload["provider_id"] = _PROVIDER_ID
        payload["instrument"] = cls._remap_instrument(quote.instrument).model_dump(
            mode="python"
        )
        extensions = dict(quote.provider_extensions)
        extensions["replay.original_provider_id"] = quote.provider_id
        payload["provider_extensions"] = extensions
        return Quote.model_validate(payload)

    @classmethod
    def _remap_bar(cls, bar: PriceBar) -> PriceBar:
        payload = bar.model_dump(mode="python")
        payload["provider_id"] = _PROVIDER_ID
        payload["instrument"] = cls._remap_instrument(bar.instrument).model_dump(
            mode="python"
        )
        return PriceBar.model_validate(payload)
