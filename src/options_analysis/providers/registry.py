"""Allow-listed provider registration, plug-in discovery, and routing."""

from collections.abc import Callable, Iterable
from importlib.metadata import EntryPoint, entry_points
from typing import cast

from options_analysis.providers.contracts import (
    Capability,
    MarketDataProvider,
    Provider,
    ProviderStatus,
)
from options_analysis.providers.errors import (
    ProviderRegistrationError,
    UnknownProviderError,
    UnsupportedCapabilityError,
)

ENTRY_POINT_GROUP = "options_analysis.providers"
ProviderFactory = Callable[[], Provider]


class ProviderRegistry:
    """Holds only explicitly allow-listed providers."""

    def __init__(self, allowed_provider_ids: Iterable[str]) -> None:
        self._allowed = frozenset(item.strip().lower() for item in allowed_provider_ids)
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        provider_id = provider.descriptor.provider_id
        if provider_id not in self._allowed:
            raise ProviderRegistrationError(
                f"provider {provider_id!r} is not in the configured allow-list"
            )
        if provider_id in self._providers:
            raise ProviderRegistrationError(
                f"provider {provider_id!r} is already registered"
            )
        self._providers[provider_id] = provider

    def load_entry_point_plugins(
        self, candidates: Iterable[EntryPoint] | None = None
    ) -> None:
        """Load allow-listed plug-ins without importing disabled candidates."""

        discovered = (
            entry_points(group=ENTRY_POINT_GROUP) if candidates is None else candidates
        )
        for candidate in discovered:
            if candidate.name not in self._allowed or candidate.name in self._providers:
                continue
            loaded = candidate.load()
            if not callable(loaded):
                raise ProviderRegistrationError(
                    f"provider entry point {candidate.name!r} is not a factory"
                )
            factory = cast(ProviderFactory, loaded)
            provider = factory()
            if not isinstance(provider, Provider):
                raise ProviderRegistrationError(
                    "provider entry point "
                    f"{candidate.name!r} returned an invalid object"
                )
            if provider.descriptor.provider_id != candidate.name:
                raise ProviderRegistrationError(
                    "provider entry-point name must match its descriptor id"
                )
            self.register(provider)

    def get(self, provider_id: str) -> Provider:
        normalized = provider_id.strip().lower()
        try:
            return self._providers[normalized]
        except KeyError as error:
            raise UnknownProviderError(normalized) from error

    def require_capability(self, provider_id: str, capability: Capability) -> Provider:
        provider = self.get(provider_id)
        if capability not in provider.descriptor.capabilities:
            raise UnsupportedCapabilityError(provider_id, capability)
        return provider

    def statuses(self) -> tuple[ProviderStatus, ...]:
        return tuple(
            self._providers[provider_id].status()
            for provider_id in sorted(self._providers)
        )


class ProviderRouter:
    """Select providers explicitly and reject unsupported capabilities."""

    def __init__(
        self, registry: ProviderRegistry, default_market_data_provider: str
    ) -> None:
        self._registry = registry
        self._default_market_data_provider = default_market_data_provider

    def market_data(self, provider_id: str | None = None) -> MarketDataProvider:
        selected = provider_id or self._default_market_data_provider
        provider = self._registry.require_capability(
            selected, Capability.UNDERLYING_QUOTES
        )
        if not isinstance(provider, MarketDataProvider):
            raise ProviderRegistrationError(
                f"provider {selected!r} advertises market data but "
                "violates its contract"
            )
        return provider
