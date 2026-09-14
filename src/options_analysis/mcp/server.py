"""Local stdio MCP server exposing provider-neutral foundation tools."""

from mcp.server import MCPServer

from options_analysis import __version__
from options_analysis.bootstrap import Application, build_application
from options_analysis.config import AppSettings
from options_analysis.mcp.models import (
    ProviderAuthStatusResult,
    ProviderListResult,
    ProviderSummary,
    ServerInfoResult,
)

SERVER_NAME = "options-analysis"


def create_server(settings: AppSettings | None = None) -> MCPServer:
    """Build an isolated server instance for stdio, embedding, or tests."""

    application = build_application(settings)
    server = MCPServer(
        SERVER_NAME,
        title="Provider-Pluggable Options Analysis",
        description="Read-only option position data and analysis foundation",
        instructions=(
            "Use provider-neutral options tools. This server is read-only and "
            "does not expose order or account-mutation capabilities."
        ),
        version=__version__,
    )
    _register_foundation_tools(server, application)
    return server


def _register_foundation_tools(server: MCPServer, application: Application) -> None:
    @server.tool(name="options_server_info")
    def options_server_info() -> ServerInfoResult:
        """Return safe server capabilities and runtime mode; never secrets."""

        public = application.settings.public_view()
        return ServerInfoResult(
            server_name=SERVER_NAME,
            version=__version__,
            environment=public.environment,
            transport="stdio",
            read_only=True,
            allow_live_smoke_tests=public.allow_live_smoke_tests,
            feature_groups=("foundation",),
        )

    @server.tool(name="options_list_providers")
    def options_list_providers() -> ProviderListResult:
        """List enabled provider capabilities and safe readiness information."""

        summaries = tuple(
            ProviderSummary(
                provider_id=status.descriptor.provider_id,
                display_name=status.descriptor.display_name,
                version=status.descriptor.version,
                authentication_type=status.descriptor.authentication_type.value,
                capabilities=tuple(
                    sorted(
                        capability.value
                        for capability in status.descriptor.capabilities
                    )
                ),
                freshness_modes=tuple(
                    sorted(mode.value for mode in status.descriptor.freshness_modes)
                ),
                configured=status.configured,
                ready=status.ready,
                message=status.message,
            )
            for status in application.provider_service.list_statuses()
        )
        return ProviderListResult(
            providers=summaries,
            defaults={
                "market_data": application.settings.default_market_data_provider,
            },
        )

    @server.tool(name="options_provider_auth_status")
    def options_provider_auth_status(provider: str) -> ProviderAuthStatusResult:
        """Return safe authentication state; never credentials or tokens."""

        status = application.provider_service.auth_status(provider)
        return ProviderAuthStatusResult(
            provider_id=status.provider_id,
            authentication_type=status.authentication_type.value,
            state=status.state.value,
            configured=status.configured,
            authorized=status.authorized,
            expires_at=(status.expires_at.isoformat() if status.expires_at else None),
            reauthorization_required=status.reauthorization_required,
            message=status.message,
        )


mcp = create_server()


def main() -> None:
    """Run the local stdio transport."""

    mcp.run()


if __name__ == "__main__":
    main()
