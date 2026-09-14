import pytest
from httpx import ASGITransport, AsyncClient

from options_analysis.config import AppSettings
from options_analysis.web import create_app


@pytest.fixture
def app():  # type: ignore[no-untyped-def]
    return create_app(AppSettings(_env_file=None))


@pytest.mark.asyncio
async def test_info_and_provider_endpoints_are_read_only(app) -> None:  # type: ignore[no-untyped-def]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        info = await client.get("/api/v1/info")
        providers = await client.get("/api/v1/providers")

    assert info.status_code == 200
    assert info.json()["info"] == {
        "name": "options-analysis",
        "version": "0.6.0",
        "environment": "development",
        "read_only": True,
        "default_market_data_provider": "fake",
    }
    assert info.json()["error"] is None
    assert providers.status_code == 200
    assert providers.json()["providers"][0]["provider_id"] == "fake"


@pytest.mark.asyncio
async def test_workspace_combines_quote_expirations_and_filtered_chain(app) -> None:  # type: ignore[no-untyped-def]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/workspaces/spy",
            params={"put_call": "call", "expiration": "2030-01-18", "limit": 2},
        )

    assert response.status_code == 200
    result = response.json()
    assert result["error"] is None
    assert result["workspace"]["symbol"] == "SPY"
    assert result["workspace"]["quote"]["mark"] == "100.00"
    assert result["workspace"]["expirations"] == ["2030-01-18", "2030-02-15"]
    contracts = result["workspace"]["chain"]["contracts"]
    assert len(contracts) == 2
    assert {item["instrument"]["option"]["put_call"] for item in contracts} == {"call"}


@pytest.mark.asyncio
async def test_workspace_errors_are_stable_and_secret_safe(app) -> None:  # type: ignore[no-untyped-def]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        unknown = await client.get(
            "/api/v1/workspaces/SPY", params={"provider": "disabled"}
        )
        invalid = await client.get("/api/v1/workspaces/SPY", params={"limit": 1000})

    assert unknown.status_code == 400
    assert unknown.json()["error"]["category"] == "configuration"
    assert unknown.json()["error"]["retryable"] is False
    assert invalid.status_code == 422
    assert invalid.json()["error"]["category"] == "validation"
    assert invalid.json()["error"]["field_paths"] == ["limit"]


@pytest.mark.asyncio
async def test_local_vite_origin_is_allowed(app) -> None:  # type: ignore[no-untyped-def]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.options(
            "/api/v1/workspaces/SPY",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
