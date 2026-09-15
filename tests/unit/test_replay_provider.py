from pathlib import Path

import pytest

from options_analysis.bootstrap import build_application
from options_analysis.config import AppSettings
from options_analysis.providers.errors import ProviderConfigurationError
from options_analysis.providers.replay import ReplayProvider
from options_analysis.providers.replay.sample import create_sample_bundle


def test_unconfigured_replay_provider_is_visible_but_not_ready() -> None:
    status = ReplayProvider().status()

    assert status.configured is False
    assert status.ready is False
    assert "REPLAY_BUNDLE_PATH" in (status.message or "")


@pytest.mark.asyncio
async def test_replay_provider_loads_valid_bundle_from_path(tmp_path: Path) -> None:
    bundle = await create_sample_bundle()
    bundle_path = tmp_path / "sample.json"
    bundle_path.write_text(bundle.model_dump_json(), encoding="utf-8")

    provider = ReplayProvider.from_path(bundle_path, max_bytes=2_000_000)

    assert provider.status().ready is True
    assert (await provider.get_underlying_quote("spy")).provider_id == "replay"


@pytest.mark.asyncio
async def test_replay_provider_runs_through_application_composition(
    tmp_path: Path,
) -> None:
    bundle = await create_sample_bundle()
    bundle_path = tmp_path / "sample.json"
    bundle_path.write_text(bundle.model_dump_json(), encoding="utf-8")
    settings = AppSettings(
        _env_file=None,
        enabled_providers=("replay",),
        default_market_data_provider="replay",
        replay_bundle_path=bundle_path,
        state_db_path=tmp_path / "state.sqlite3",
    )

    application = build_application(settings)
    quote = await application.market_data_service.get_underlying_quote("SPY")

    assert quote.provider_id == "replay"
    assert application.registry.statuses()[0].ready is True


def test_replay_provider_rejects_invalid_or_oversized_files(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")

    with pytest.raises(ProviderConfigurationError, match="schema validation"):
        ReplayProvider.from_path(invalid, max_bytes=1_024)
    with pytest.raises(ProviderConfigurationError, match="exceeds"):
        ReplayProvider.from_path(invalid, max_bytes=1)
