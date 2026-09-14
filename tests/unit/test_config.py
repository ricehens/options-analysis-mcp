from pydantic import SecretStr, ValidationError

from options_analysis.config import AppSettings, EnvironmentName


def test_default_settings_are_offline_and_safe() -> None:
    settings = AppSettings(_env_file=None)

    assert settings.enabled_providers == ("fake",)
    assert settings.allow_live_smoke_tests is False
    assert settings.public_view().environment is EnvironmentName.DEVELOPMENT
    assert settings.schwab_client_id is None
    assert settings.schwab_client_secret is None


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


def test_schwab_secrets_are_redacted_and_not_in_public_settings() -> None:
    settings = AppSettings(
        _env_file=None,
        schwab_client_id=SecretStr("identifier-secret"),
        schwab_client_secret=SecretStr("application-secret"),
    )

    rendered = repr(settings) + settings.public_view().model_dump_json()
    assert "identifier-secret" not in rendered
    assert "application-secret" not in rendered
    assert "schwab" not in settings.public_view().model_dump()


def test_schwab_redirect_rejects_lookalike_loopback_host() -> None:
    try:
        AppSettings(
            _env_file=None,
            schwab_redirect_uri="http://localhost.example/callback",
        )
    except ValidationError as error:
        assert "HTTPS or loopback HTTP" in str(error)
    else:
        raise AssertionError("non-loopback HTTP redirect was accepted")
