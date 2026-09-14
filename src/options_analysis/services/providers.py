"""Safe provider discovery exposed to user interfaces."""

from options_analysis.providers import ProviderRegistry, ProviderStatus


class ProviderService:
    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    def list_statuses(self) -> tuple[ProviderStatus, ...]:
        return self._registry.statuses()
