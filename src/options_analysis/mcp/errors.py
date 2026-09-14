"""Convert internal provider failures to stable, secret-safe MCP results."""

from options_analysis.errors import ErrorDetail, error_detail
from options_analysis.providers.errors import ProviderError


def tool_error(error: ProviderError | ValueError) -> ErrorDetail:
    return error_detail(error)
