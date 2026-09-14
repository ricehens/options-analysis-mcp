from collections.abc import Callable
from typing import Any, cast

import pytest

from options_analysis.providers import (
    AuthenticationType,
    Capability,
    FreshnessMode,
    Provider,
    ProviderDescriptor,
    ProviderRegistry,
    ProviderStatus,
)
from options_analysis.providers.errors import (
    ProviderRegistrationError,
    UnknownProviderError,
    UnsupportedCapabilityError,
)
from options_analysis.providers.fake import FakeProvider


class EmptyProvider:
    @property
    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id="empty",
            display_name="Empty",
            version="1",
            authentication_type=AuthenticationType.NONE,
            capabilities=frozenset(),
            freshness_modes=frozenset({FreshnessMode.DETERMINISTIC}),
        )

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            descriptor=self.descriptor,
            configured=True,
            ready=True,
        )


class StubEntryPoint:
    def __init__(self, name: str, loader: Callable[[], Any]) -> None:
        self.name = name
        self._loader = loader
        self.was_loaded = False

    def load(self) -> Any:
        self.was_loaded = True
        return self._loader()


def test_registry_only_admits_allowlisted_unique_providers() -> None:
    registry = ProviderRegistry(("fake",))
    registry.register(FakeProvider())

    assert registry.get(" FAKE ").descriptor.provider_id == "fake"
    assert registry.statuses()[0].ready is True
    with pytest.raises(ProviderRegistrationError, match="already registered"):
        registry.register(FakeProvider())
    with pytest.raises(ProviderRegistrationError, match="allow-list"):
        ProviderRegistry(()).register(FakeProvider())


def test_unknown_and_unsupported_capabilities_are_explicit() -> None:
    registry = ProviderRegistry(("empty",))
    registry.register(EmptyProvider())

    with pytest.raises(UnknownProviderError, match="unknown or disabled"):
        registry.get("missing")
    with pytest.raises(UnsupportedCapabilityError, match="option_chains"):
        registry.require_capability("empty", Capability.OPTION_CHAINS)


def test_disabled_entry_point_is_not_imported() -> None:
    candidate = StubEntryPoint("disabled", lambda: FakeProvider)
    registry = ProviderRegistry(("fake",))

    registry.load_entry_point_plugins([cast(Any, candidate)])

    assert candidate.was_loaded is False


def test_enabled_entry_point_factory_is_registered() -> None:
    candidate = StubEntryPoint("fake", lambda: FakeProvider)
    registry = ProviderRegistry(("fake",))

    registry.load_entry_point_plugins([cast(Any, candidate)])

    assert candidate.was_loaded is True
    assert isinstance(registry.get("fake"), Provider)
