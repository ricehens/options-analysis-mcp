"""Concurrency-safe token lifecycle and safe authentication status."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import SecretStr

from options_analysis.providers import (
    AuthenticationState,
    AuthenticationType,
    ProviderAuthStatus,
)
from options_analysis.providers.errors import ProviderAuthorizationError
from options_analysis.providers.schwab.config import SchwabConfig
from options_analysis.providers.schwab.oauth import SchwabOAuthClient
from options_analysis.providers.schwab.tokens import OAuthToken, TokenStore

Clock = Callable[[], datetime]


class SchwabTokenManager:
    def __init__(
        self,
        config: SchwabConfig,
        oauth: SchwabOAuthClient,
        store: TokenStore,
        *,
        clock: Clock | None = None,
    ) -> None:
        self._config = config
        self._oauth = oauth
        self._store = store
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = asyncio.Lock()

    def status(self) -> ProviderAuthStatus:
        if not self._config.configured:
            return self._status(
                AuthenticationState.NOT_CONFIGURED,
                authorized=False,
                message="Configure Schwab application credentials locally.",
            )
        try:
            token = self._store.load()
        except ProviderAuthorizationError:
            return self._status(
                AuthenticationState.REAUTHORIZATION_REQUIRED,
                authorized=False,
                reauthorization_required=True,
                message="Stored authorization is invalid; run the Schwab auth helper.",
            )
        if token is None:
            return self._status(
                AuthenticationState.NOT_AUTHORIZED,
                authorized=False,
                message="Run options-analysis-schwab-auth locally.",
            )
        now = self._clock()
        if token.refresh_is_expired(now):
            return self._status(
                AuthenticationState.REAUTHORIZATION_REQUIRED,
                authorized=False,
                expires_at=token.expires_at,
                reauthorization_required=True,
                message="Schwab authorization must be renewed interactively.",
            )
        if token.access_is_expiring(now):
            return self._status(
                AuthenticationState.REFRESH_NEEDED,
                authorized=True,
                expires_at=token.expires_at,
                message="Access token will refresh on the next provider request.",
            )
        return self._status(
            AuthenticationState.AUTHORIZED,
            authorized=True,
            expires_at=token.expires_at,
            message="Schwab authorization is available.",
        )

    async def store_callback(
        self, callback_url: str, expected_state: str
    ) -> OAuthToken:
        code = self._oauth.validate_callback(callback_url, expected_state)
        token = await self._oauth.exchange_code(code)
        self._store.save(token)
        return token

    async def access_token(self, *, force_refresh: bool = False) -> str:
        async with self._lock:
            token = self._store.load()
            if token is None:
                raise ProviderAuthorizationError(
                    "Schwab authorization is missing; run the auth helper.",
                    reauthorization_required=True,
                )
            now = self._clock()
            if force_refresh or token.access_is_expiring(now):
                if token.refresh_is_expired(now) or token.refresh_token is None:
                    raise ProviderAuthorizationError(
                        "Schwab refresh authorization has expired; authorize again.",
                        reauthorization_required=True,
                    )
                refreshed = await self._oauth.refresh(
                    token.refresh_token.get_secret_value()
                )
                if refreshed.refresh_token is None:
                    refreshed = refreshed.model_copy(
                        update={
                            "refresh_token": SecretStr(
                                token.refresh_token.get_secret_value()
                            ),
                            "refresh_token_expires_at": (
                                token.refresh_token_expires_at
                            ),
                        }
                    )
                self._store.save(refreshed)
                token = refreshed
            return token.access_token.get_secret_value()

    @staticmethod
    def _status(
        state: AuthenticationState,
        *,
        authorized: bool,
        expires_at: datetime | None = None,
        reauthorization_required: bool = False,
        message: str,
    ) -> ProviderAuthStatus:
        return ProviderAuthStatus(
            provider_id="schwab",
            authentication_type=AuthenticationType.OAUTH,
            state=state,
            configured=state is not AuthenticationState.NOT_CONFIGURED,
            authorized=authorized,
            expires_at=expires_at,
            reauthorization_required=reauthorization_required,
            message=message,
        )
