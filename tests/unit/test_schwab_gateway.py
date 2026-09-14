from collections.abc import Awaitable, Callable

import httpx
import pytest

from options_analysis.providers.errors import (
    ProviderEntitlementError,
    ProviderRateLimitError,
    ProviderResponseSchemaError,
    ProviderValidationError,
)
from options_analysis.providers.schwab.gateway import SchwabGateway


class StubTokens:
    def __init__(self) -> None:
        self.forced: list[bool] = []

    async def access_token(self, *, force_refresh: bool = False) -> str:
        self.forced.append(force_refresh)
        return "refreshed" if force_refresh else "initial"


def no_sleep(delays: list[float]) -> Callable[[float], Awaitable[None]]:
    async def sleep(delay: float) -> None:
        delays.append(delay)

    return sleep


@pytest.mark.asyncio
async def test_gateway_refreshes_once_after_401_and_returns_json() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            assert request.headers["Authorization"] == "Bearer initial"
            return httpx.Response(401)
        assert request.headers["Authorization"] == "Bearer refreshed"
        return httpx.Response(200, json={"SPY": {"quote": {}}})

    tokens = StubTokens()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = SchwabGateway("https://example.test/v1", tokens, client)
        result = await gateway.get_json("/quotes", params={"symbols": "SPY"})

    assert result == {"SPY": {"quote": {}}}
    assert tokens.forced == [False, True]


@pytest.mark.asyncio
async def test_gateway_bounds_rate_limit_retries() -> None:
    delays: list[float] = []
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(429, headers={"Retry-After": "99"})
        )
    )
    gateway = SchwabGateway(
        "https://example.test/v1",
        StubTokens(),
        client,
        max_attempts=2,
        sleeper=no_sleep(delays),
    )

    with pytest.raises(ProviderRateLimitError):
        await gateway.get_json("quotes")
    assert delays == [5.0]
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "error_type"),
    [
        (httpx.Response(403), ProviderEntitlementError),
        (httpx.Response(200, text="not-json"), ProviderResponseSchemaError),
    ],
)
async def test_gateway_maps_non_retryable_errors(
    response: httpx.Response, error_type: type[Exception]
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: response)
    ) as client:
        gateway = SchwabGateway("https://example.test/v1", StubTokens(), client)
        with pytest.raises(error_type):
            await gateway.get_json("quotes")


@pytest.mark.asyncio
async def test_gateway_rejects_absolute_and_traversing_paths() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={}))
    ) as client:
        gateway = SchwabGateway("https://example.test/v1", StubTokens(), client)
        with pytest.raises(ProviderValidationError):
            await gateway.get_json("https://other.test/private")
        with pytest.raises(ProviderValidationError):
            await gateway.get_json("../trader/accounts")
