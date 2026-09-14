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
        assert names == {"options_list_providers", "options_server_info"}
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
            "options_list_providers",
            "options_server_info",
        }
        result = await client.call_tool("options_server_info", {})
        assert result.is_error is False
        assert result.structured_content is not None
        assert result.structured_content["read_only"] is True
