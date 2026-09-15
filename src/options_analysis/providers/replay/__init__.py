"""Validated local replay-bundle provider."""

from options_analysis.config import AppSettings
from options_analysis.providers.replay.models import (
    ReplayBundle,
    ReplayHistorySeries,
    ReplaySource,
    ReplaySymbolSnapshot,
)
from options_analysis.providers.replay.provider import ReplayProvider


def build_replay_provider(settings: AppSettings) -> ReplayProvider:
    """Build a replay provider without making network requests."""

    if settings.replay_bundle_path is None:
        return ReplayProvider()
    return ReplayProvider.from_path(
        settings.replay_bundle_path,
        max_bytes=settings.replay_max_bundle_bytes,
    )


__all__ = [
    "ReplayBundle",
    "ReplayHistorySeries",
    "ReplayProvider",
    "ReplaySource",
    "ReplaySymbolSnapshot",
    "build_replay_provider",
]
