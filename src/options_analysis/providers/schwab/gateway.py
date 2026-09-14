"""Read-only Schwab HTTP gateway with bounded retry and typed failures."""

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol
from urllib.parse import urljoin

import httpx

from options_analysis.providers.errors import (
    ProviderAuthorizationError,
    ProviderEntitlementError,
    ProviderRateLimitError,
    ProviderResponseSchemaError,
    ProviderUpstreamUnavailableError,
    ProviderValidationError,
)

Sleeper = Callable[[float], Awaitable[None]]


class AccessTokenSource(Protocol):
    async def access_token(self, *, force_refresh: bool = False) -> str: ...


class SchwabGateway:
    """Only exposes GET, making the adapter's read-only boundary mechanical."""

    def __init__(
        self,
        base_url: str,
        token_source: AccessTokenSource,
        client: httpx.AsyncClient,
        *,
        max_attempts: int = 3,
        sleeper: Sleeper = asyncio.sleep,
    ) -> None:
        self._base_url = base_url.rstrip("/") + "/"
        self._token_source = token_source
        self._client = client
        self._max_attempts = max_attempts
        self._sleeper = sleeper

    async def get_json(
        self, path: str, *, params: Mapping[str, str] | None = None
    ) -> dict[str, Any] | list[Any]:
        if "://" in path or "?" in path or "#" in path or ".." in path.split("/"):
            raise ProviderValidationError("Gateway paths must be provider-relative.")
        url = urljoin(self._base_url, path.lstrip("/"))
        force_refresh = False
        refresh_attempted = False
        last_transport_error: httpx.HTTPError | None = None

        for attempt in range(self._max_attempts):
            token = await self._token_source.access_token(force_refresh=force_refresh)
            force_refresh = False
            try:
                response = await self._client.get(
                    url,
                    params=params,
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {token}",
                    },
                )
            except (httpx.TimeoutException, httpx.TransportError) as error:
                last_transport_error = error
                if attempt + 1 < self._max_attempts:
                    await self._sleeper(self._backoff(attempt))
                    continue
                break

            if response.status_code == 401:
                if not refresh_attempted and attempt + 1 < self._max_attempts:
                    refresh_attempted = True
                    force_refresh = True
                    continue
                raise ProviderAuthorizationError(
                    "Schwab rejected authorization; authorize again.",
                    reauthorization_required=True,
                )
            if response.status_code == 403:
                raise ProviderEntitlementError(
                    "Schwab authorization lacks the required API entitlement."
                )
            if response.status_code == 429:
                if attempt + 1 < self._max_attempts:
                    await self._sleeper(self._retry_delay(response, attempt))
                    continue
                raise ProviderRateLimitError(
                    "Schwab rate limit persisted after bounded retries."
                )
            if response.status_code >= 500:
                if attempt + 1 < self._max_attempts:
                    await self._sleeper(self._backoff(attempt))
                    continue
                raise ProviderUpstreamUnavailableError(
                    "Schwab remained unavailable after bounded retries."
                )
            if response.status_code >= 400:
                raise ProviderValidationError(
                    f"Schwab rejected the read request (HTTP {response.status_code})."
                )
            try:
                payload: Any = response.json()
            except ValueError as error:
                raise ProviderResponseSchemaError(
                    "Schwab returned a non-JSON response."
                ) from error
            if not isinstance(payload, (dict, list)):
                raise ProviderResponseSchemaError(
                    "Schwab JSON response must be an object or array."
                )
            return payload

        raise ProviderUpstreamUnavailableError(
            "Schwab could not be reached after bounded retries."
        ) from last_transport_error

    @staticmethod
    def _backoff(attempt: int) -> float:
        delay: float = 0.25 * pow(2.0, attempt)
        return min(delay, 2.0)

    @classmethod
    def _retry_delay(cls, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                parsed_delay: float = float(retry_after)
                return min(max(parsed_delay, 0.0), 5.0)
            except ValueError:
                pass
        return cls._backoff(attempt)
