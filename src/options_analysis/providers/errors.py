"""Stable errors exposed by provider registration and routing."""

from options_analysis.providers.contracts import Capability


class ProviderError(RuntimeError):
    """Base class for errors at the provider boundary."""


class ProviderConfigurationError(ProviderError):
    """Required local provider configuration is absent or invalid."""


class ProviderAuthorizationError(ProviderError):
    """Authorization is absent, expired, rejected, or requires user action."""

    def __init__(self, message: str, *, reauthorization_required: bool = False) -> None:
        super().__init__(message)
        self.reauthorization_required = reauthorization_required


class ProviderEntitlementError(ProviderError):
    """The authorized account or application lacks an API entitlement."""


class ProviderRateLimitError(ProviderError):
    """The upstream provider continued to rate-limit after bounded retries."""


class ProviderUpstreamUnavailableError(ProviderError):
    """The upstream provider remained unavailable after bounded retries."""


class ProviderResponseSchemaError(ProviderError):
    """The upstream response could not be safely interpreted."""


class ProviderValidationError(ProviderError):
    """The provider rejected request parameters."""


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
