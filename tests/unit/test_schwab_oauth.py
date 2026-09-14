from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from pydantic import SecretStr

from options_analysis.providers.errors import ProviderAuthorizationError
from options_analysis.providers.schwab.config import SchwabConfig
from options_analysis.providers.schwab.manager import SchwabTokenManager
from options_analysis.providers.schwab.oauth import SchwabOAuthClient
from options_analysis.providers.schwab.tokens import OAuthToken, TokenStore

NOW = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)


def config(token_path: Path) -> SchwabConfig:
    return SchwabConfig(
        client_id=SecretStr("client-id"),
        client_secret=SecretStr("client-secret"),
        redirect_uri="https://127.0.0.1/callback",
        authorization_url="https://example.test/oauth/authorize",
        token_url="https://example.test/oauth/token",
        market_data_base_url="https://example.test/marketdata/v1",
        token_path=token_path,
        http_timeout_seconds=1,
        http_max_attempts=3,
    )


@pytest.mark.asyncio
async def test_authorization_url_callback_and_code_exchange(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "access_token": "access-value",
                "refresh_token": "refresh-value",
                "token_type": "Bearer",
                "expires_in": 1800,
                "scope": "market-data",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        oauth = SchwabOAuthClient(
            config(tmp_path / "token.json"), client, clock=lambda: NOW
        )
        request = oauth.authorization_request()
        query = parse_qs(urlsplit(request.url).query)
        assert query["client_id"] == ["client-id"]
        assert query["redirect_uri"] == ["https://127.0.0.1/callback"]
        assert query["state"] == [request.state]

        callback = (
            "https://127.0.0.1/callback?code=one-time-code&state=" + request.state
        )
        code = oauth.validate_callback(callback, request.state)
        token = await oauth.exchange_code(code)

    assert token.expires_at == NOW + timedelta(minutes=30)
    assert "access-value" not in repr(token)
    assert requests[0].url == "https://example.test/oauth/token"
    assert requests[0].headers["Authorization"].startswith("Basic ")
    assert b"one-time-code" in requests[0].content


def test_callback_rejects_changed_redirect_and_state(tmp_path: Path) -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(500))
    )
    oauth = SchwabOAuthClient(config(tmp_path / "token.json"), client)

    with pytest.raises(ProviderAuthorizationError, match="exactly match"):
        oauth.validate_callback(
            "https://localhost/callback?code=code&state=expected", "expected"
        )
    with pytest.raises(ProviderAuthorizationError, match="state validation"):
        oauth.validate_callback(
            "https://127.0.0.1/callback?code=code&state=wrong", "expected"
        )

    root_config = config(tmp_path / "root-token.json").model_copy(
        update={"redirect_uri": "https://127.0.0.1"}
    )
    root_oauth = SchwabOAuthClient(root_config, client)
    assert (
        root_oauth.validate_callback(
            "https://127.0.0.1/?code=code&state=expected", "expected"
        )
        == "code"
    )


@pytest.mark.asyncio
async def test_expired_access_token_refreshes_and_preserves_refresh_token(
    tmp_path: Path,
) -> None:
    token_path = tmp_path / "token.json"
    store = TokenStore(token_path)
    store.save(
        OAuthToken(
            access_token="old-access",
            refresh_token="long-lived-refresh",
            expires_at=NOW - timedelta(seconds=1),
        )
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert b"long-lived-refresh" in request.content
        return httpx.Response(
            200,
            json={"access_token": "new-access", "expires_in": 1800},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider_config = config(token_path)
        oauth = SchwabOAuthClient(provider_config, client, clock=lambda: NOW)
        manager = SchwabTokenManager(provider_config, oauth, store, clock=lambda: NOW)
        assert await manager.access_token() == "new-access"

    stored = store.load()
    assert stored is not None
    assert stored.refresh_token is not None
    assert stored.refresh_token.get_secret_value() == "long-lived-refresh"
