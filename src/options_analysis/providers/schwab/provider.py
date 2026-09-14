"""Schwab provider identity and Milestone 2 gateway composition."""

from collections.abc import Callable
from datetime import datetime

import httpx

from options_analysis.config import AppSettings
from options_analysis.providers import (
    AuthenticationType,
    FreshnessMode,
    ProviderAuthStatus,
    ProviderDescriptor,
    ProviderStatus,
)
from options_analysis.providers.schwab.config import SchwabConfig
from options_analysis.providers.schwab.gateway import SchwabGateway
from options_analysis.providers.schwab.manager import SchwabTokenManager
from options_analysis.providers.schwab.oauth import (
    AuthorizationRequest,
    SchwabOAuthClient,
)
from options_analysis.providers.schwab.tokens import OAuthToken, TokenStore


class SchwabProvider:
    def __init__(
        self,
        config: SchwabConfig,
        oauth: SchwabOAuthClient,
        tokens: SchwabTokenManager,
        gateway: SchwabGateway,
    ) -> None:
        self.config = config
        self._oauth = oauth
        self._tokens = tokens
        self.gateway = gateway

    @property
    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id="schwab",
            display_name="Charles Schwab",
            version="1",
            authentication_type=AuthenticationType.OAUTH,
            capabilities=frozenset(),
            freshness_modes=frozenset({FreshnessMode.REALTIME, FreshnessMode.DELAYED}),
        )

    def status(self) -> ProviderStatus:
        auth = self.auth_status()
        return ProviderStatus(
            descriptor=self.descriptor,
            configured=auth.configured,
            ready=auth.authorized,
            message=(
                "OAuth gateway ready; market-data capabilities arrive in Milestone 3."
                if auth.authorized
                else auth.message
            ),
        )

    def auth_status(self) -> ProviderAuthStatus:
        return self._tokens.status()

    def authorization_request(self) -> AuthorizationRequest:
        return self._oauth.authorization_request()

    async def complete_authorization(
        self, callback_url: str, expected_state: str
    ) -> OAuthToken:
        return await self._tokens.store_callback(callback_url, expected_state)

    async def smoke_read(self, symbol: str) -> dict[str, str | int | bool]:
        normalized = symbol.strip().upper()
        payload = await self.gateway.get_json(
            "/quotes", params={"symbols": normalized, "fields": "quote"}
        )
        return {
            "ok": True,
            "provider_id": "schwab",
            "symbol": normalized,
            "response_kind": "object" if isinstance(payload, dict) else "array",
            "top_level_items": len(payload),
        }


def build_schwab_provider(
    settings: AppSettings,
    *,
    client: httpx.AsyncClient | None = None,
    clock: Callable[[], datetime] | None = None,
) -> SchwabProvider:
    config = SchwabConfig.from_settings(settings)
    http_client = client or httpx.AsyncClient(
        timeout=httpx.Timeout(config.http_timeout_seconds),
        follow_redirects=False,
    )
    oauth = SchwabOAuthClient(config, http_client, clock=clock)
    store = TokenStore(config.token_path)
    tokens = SchwabTokenManager(config, oauth, store, clock=clock)
    gateway = SchwabGateway(
        config.market_data_base_url,
        tokens,
        http_client,
        max_attempts=config.http_max_attempts,
    )
    return SchwabProvider(config, oauth, tokens, gateway)
