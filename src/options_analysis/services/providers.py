"""Safe provider discovery and authentication state for user interfaces."""

from options_analysis.providers import (
    AuthenticatingProvider,
    AuthenticationState,
    AuthenticationType,
    ProviderAuthStatus,
    ProviderRegistry,
    ProviderStatus,
)


class ProviderService:
    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    def list_statuses(self) -> tuple[ProviderStatus, ...]:
        return self._registry.statuses()

    def auth_status(self, provider_id: str) -> ProviderAuthStatus:
        provider = self._registry.get(provider_id)
        if isinstance(provider, AuthenticatingProvider):
            return provider.auth_status()
        return ProviderAuthStatus(
            provider_id=provider.descriptor.provider_id,
            authentication_type=AuthenticationType.NONE,
            state=AuthenticationState.NOT_REQUIRED,
            configured=True,
            authorized=True,
            message="This provider does not require authentication.",
        )
