from pydantic import ValidationError

from options_analysis.config import AppSettings, EnvironmentName


def test_default_settings_are_offline_and_safe() -> None:
    settings = AppSettings(_env_file=None)

    assert settings.enabled_providers == ("fake",)
    assert settings.allow_live_smoke_tests is False
    assert settings.public_view().environment is EnvironmentName.DEVELOPMENT
    assert "secret" not in repr(settings).lower()


def test_provider_names_are_normalized_and_deduplicated() -> None:
    settings = AppSettings(
        _env_file=None,
        enabled_providers=(" Fake ", "fake", "SECOND"),
        default_market_data_provider=" FAKE ",
    )

    assert settings.enabled_providers == ("fake", "second")
    assert settings.default_market_data_provider == "fake"


def test_default_provider_must_be_enabled() -> None:
    try:
        AppSettings(
            _env_file=None,
            enabled_providers=("fake",),
            default_market_data_provider="other",
        )
    except ValidationError as error:
        assert "default market-data provider must be enabled" in str(error)
    else:
        raise AssertionError("invalid settings were accepted")
