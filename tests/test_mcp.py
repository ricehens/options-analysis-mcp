import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters

from options_analysis.config import AppSettings
from options_analysis.mcp.server import create_server


@pytest.mark.asyncio
async def test_foundation_tools_over_real_in_memory_mcp_protocol() -> None:
    server = create_server(AppSettings(_env_file=None))

    async with Client(server) as client:
        listed = await client.list_tools()
        names = {tool.name for tool in listed.tools}
        assert names == {
            "options_analyze_positions",
            "options_get_option_chain",
            "options_get_option_expirations",
            "options_get_option_quotes",
            "options_get_price_history",
            "options_get_underlying_quote",
            "options_list_providers",
            "options_provider_auth_status",
            "options_server_info",
        }
        assert all(tool.output_schema is not None for tool in listed.tools)

        info = await client.call_tool("options_server_info", {})
        assert info.is_error is False
        assert info.structured_content is not None
        assert info.structured_content["read_only"] is True
        assert info.structured_content["transport"] == "stdio"

        providers = await client.call_tool("options_list_providers", {})
        assert providers.is_error is False
        assert providers.structured_content is not None
        assert providers.structured_content["providers"][0]["provider_id"] == "fake"
        assert providers.structured_content["defaults"]["market_data"] == "fake"

        auth = await client.call_tool(
            "options_provider_auth_status", {"provider": "fake"}
        )
        assert auth.is_error is False
        assert auth.structured_content is not None
        assert auth.structured_content["state"] == "not_required"
        assert auth.structured_content["authorized"] is True

        quote = await client.call_tool(
            "options_get_underlying_quote", {"symbol": "SPY"}
        )
        assert quote.is_error is False
        assert quote.structured_content is not None
        assert quote.structured_content["quote"]["instrument"]["symbol"] == "SPY"

        expirations = await client.call_tool(
            "options_get_option_expirations", {"underlying_symbol": "SPY"}
        )
        assert expirations.is_error is False
        assert expirations.structured_content is not None
        assert len(expirations.structured_content["expirations"]) == 2

        chain = await client.call_tool(
            "options_get_option_chain",
            {"underlying_symbol": "SPY", "put_call": "call", "limit": 2},
        )
        assert chain.is_error is False
        assert chain.structured_content is not None
        assert len(chain.structured_content["chain"]["contracts"]) == 2

        option_quotes = await client.call_tool(
            "options_get_option_quotes",
            {"symbols": ["SPY300118C00095000", "SPY300118P00095000"]},
        )
        assert option_quotes.is_error is False
        assert option_quotes.structured_content is not None
        assert len(option_quotes.structured_content["quotes"]) == 2

        history = await client.call_tool(
            "options_get_price_history",
            {
                "symbol": "SPY",
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-01-03T00:00:00Z",
            },
        )
        assert history.is_error is False
        assert history.structured_content is not None
        assert len(history.structured_content["bars"]) == 1

        analysis = await client.call_tool(
            "options_analyze_positions",
            {
                "legs": [
                    {
                        "symbol": "SPY300118C00095000",
                        "asset_type": "option",
                        "quantity": "1",
                        "average_open_price": "6",
                    },
                    {
                        "symbol": "SPY300118C00100000",
                        "asset_type": "option",
                        "quantity": "-1",
                        "average_open_price": "3",
                    },
                ]
            },
        )
        assert analysis.is_error is False
        assert analysis.structured_content is not None
        assert analysis.structured_content["analysis"]["max_profit"] == "200"
        assert analysis.structured_content["analysis"]["break_even_prices"] == ["98"]

        error = await client.call_tool(
            "options_get_underlying_quote",
            {"symbol": "SPY", "provider": "disabled"},
        )
        assert error.is_error is False
        assert error.structured_content is not None
        assert error.structured_content["error"] == {
            "category": "configuration",
            "message": "unknown or disabled provider: disabled",
            "retryable": False,
            "reauthorization_required": False,
            "field_paths": [],
        }


@pytest.mark.asyncio
async def test_foundation_tools_over_stdio_subprocess() -> None:
    project_root = Path(__file__).parent.parent
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "options_analysis.mcp"],
        cwd=project_root,
    )

    async with Client(parameters, read_timeout_seconds=10) as client:
        listed = await client.list_tools()
        assert {tool.name for tool in listed.tools} == {
            "options_analyze_positions",
            "options_get_option_chain",
            "options_get_option_expirations",
            "options_get_option_quotes",
            "options_get_price_history",
            "options_get_underlying_quote",
            "options_list_providers",
            "options_provider_auth_status",
            "options_server_info",
        }
        result = await client.call_tool("options_server_info", {})
        assert result.is_error is False
        assert result.structured_content is not None
        assert result.structured_content["read_only"] is True
