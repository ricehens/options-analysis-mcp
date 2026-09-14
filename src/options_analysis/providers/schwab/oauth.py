"""Schwab authorization-code flow with exact callback and state validation."""

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import httpx
from pydantic import SecretStr

from options_analysis.providers.errors import (
    ProviderAuthorizationError,
    ProviderConfigurationError,
    ProviderResponseSchemaError,
)
from options_analysis.providers.schwab.config import SchwabConfig
from options_analysis.providers.schwab.tokens import OAuthToken

Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    url: str
    state: str


class SchwabOAuthClient:
    def __init__(
        self,
        config: SchwabConfig,
        client: httpx.AsyncClient,
        *,
        clock: Clock | None = None,
    ) -> None:
        self._config = config
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))

    def authorization_request(self) -> AuthorizationRequest:
        client_id, _ = self._credentials()
        state = secrets.token_urlsafe(32)
        query = urlencode(
            {
                "client_id": client_id,
                "redirect_uri": self._config.redirect_uri,
                "response_type": "code",
                "state": state,
            }
        )
        separator = "&" if "?" in self._config.authorization_url else "?"
        return AuthorizationRequest(
            url=f"{self._config.authorization_url}{separator}{query}",
            state=state,
        )

    def validate_callback(self, callback_url: str, expected_state: str) -> str:
        callback = urlsplit(callback_url.strip())
        configured = urlsplit(self._config.redirect_uri)
        callback_base = urlunsplit(
            (callback.scheme, callback.netloc, callback.path, "", "")
        )
        configured_base = urlunsplit(
            (configured.scheme, configured.netloc, configured.path, "", "")
        )
        if callback_base != configured_base or callback.fragment:
            raise ProviderAuthorizationError(
                "OAuth callback URL does not exactly match the configured redirect URI."
            )

        parameters = parse_qs(callback.query, keep_blank_values=True)
        states = parameters.get("state", [])
        if len(states) != 1 or not secrets.compare_digest(states[0], expected_state):
            raise ProviderAuthorizationError("OAuth callback state validation failed.")
        if "error" in parameters:
            raise ProviderAuthorizationError(
                "Schwab rejected the authorization request."
            )
        codes = parameters.get("code", [])
        if len(codes) != 1 or not codes[0]:
            raise ProviderAuthorizationError(
                "OAuth callback did not contain one authorization code."
            )
        return codes[0]

    async def exchange_code(self, code: str) -> OAuthToken:
        return await self._request_token(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._config.redirect_uri,
            }
        )

    async def refresh(self, refresh_token: str) -> OAuthToken:
        return await self._request_token(
            {"grant_type": "refresh_token", "refresh_token": refresh_token}
        )

    async def _request_token(self, data: dict[str, str]) -> OAuthToken:
        client_id, client_secret = self._credentials()
        try:
            response = await self._client.post(
                self._config.token_url,
                data=data,
                auth=(client_id, client_secret),
                headers={"Accept": "application/json"},
            )
        except httpx.HTTPError as error:
            raise ProviderAuthorizationError(
                "Schwab token service could not be reached."
            ) from error
        if response.status_code not in range(200, 300):
            raise ProviderAuthorizationError(
                "Schwab rejected the token request; authorization may be required.",
                reauthorization_required=response.status_code in {400, 401, 403},
            )
        try:
            payload: Any = response.json()
            if not isinstance(payload, dict):
                raise TypeError
            access_token = payload["access_token"]
            expires_in = int(payload["expires_in"])
            if not isinstance(access_token, str) or expires_in <= 0:
                raise TypeError
            refresh_token = payload.get("refresh_token")
            if refresh_token is not None and not isinstance(refresh_token, str):
                raise TypeError
            refresh_expires_in = payload.get("refresh_token_expires_in")
            now = self._clock()
            return OAuthToken(
                access_token=SecretStr(access_token),
                refresh_token=(SecretStr(refresh_token) if refresh_token else None),
                token_type=str(payload.get("token_type", "Bearer")),
                scope=(str(payload["scope"]) if payload.get("scope") else None),
                expires_at=now + timedelta(seconds=expires_in),
                refresh_token_expires_at=(
                    now + timedelta(seconds=int(refresh_expires_in))
                    if refresh_expires_in is not None
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ProviderResponseSchemaError(
                "Schwab token response did not match the expected schema."
            ) from error

    def _credentials(self) -> tuple[str, str]:
        if self._config.client_id is None or self._config.client_secret is None:
            raise ProviderConfigurationError(
                "Set OPTIONS_ANALYSIS_SCHWAB_CLIENT_ID and "
                "OPTIONS_ANALYSIS_SCHWAB_CLIENT_SECRET locally."
            )
        return (
            self._config.client_id.get_secret_value(),
            self._config.client_secret.get_secret_value(),
        )
