"""Stable errors exposed by provider registration and routing."""

from options_analysis.providers.contracts import Capability


class ProviderError(RuntimeError):
    """Base class for errors at the provider boundary."""


class ProviderRegistrationError(ProviderError):
    """A provider could not be admitted to the configured registry."""


class UnknownProviderError(ProviderError):
    def __init__(self, provider_id: str) -> None:
        super().__init__(f"unknown or disabled provider: {provider_id}")
        self.provider_id = provider_id


class UnsupportedCapabilityError(ProviderError):
    def __init__(self, provider_id: str, capability: Capability) -> None:
        super().__init__(
            f"provider {provider_id!r} does not support capability {capability.value!r}"
        )
        self.provider_id = provider_id
        self.capability = capability


class InstrumentNotFoundError(ProviderError):
    def __init__(self, provider_id: str, symbol: str) -> None:
        super().__init__(f"provider {provider_id!r} has no instrument {symbol!r}")
        self.provider_id = provider_id
        self.symbol = symbol
