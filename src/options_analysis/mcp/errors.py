"""Convert internal provider failures to stable, secret-safe MCP results."""

from options_analysis.mcp.models import (
    ErrorCategory,
    ToolErrorDetail,
)
from options_analysis.providers.errors import (
    InstrumentNotFoundError,
    ProviderAuthorizationError,
    ProviderConfigurationError,
    ProviderEntitlementError,
    ProviderError,
    ProviderRateLimitError,
    ProviderRegistrationError,
    ProviderResponseSchemaError,
    ProviderUpstreamUnavailableError,
    ProviderValidationError,
    UnknownProviderError,
    UnsupportedCapabilityError,
)


def tool_error(error: ProviderError | ValueError) -> ToolErrorDetail:
    category = ErrorCategory.VALIDATION
    retryable = False
    reauthorization_required = False
    field_paths: tuple[str, ...] = ()

    if isinstance(
        error,
        (ProviderConfigurationError, ProviderRegistrationError, UnknownProviderError),
    ):
        category = ErrorCategory.CONFIGURATION
    elif isinstance(error, UnsupportedCapabilityError):
        category = ErrorCategory.UNSUPPORTED_CAPABILITY
    elif isinstance(error, ProviderAuthorizationError):
        category = ErrorCategory.AUTHORIZATION
        reauthorization_required = error.reauthorization_required
    elif isinstance(error, ProviderEntitlementError):
        category = ErrorCategory.ENTITLEMENT
    elif isinstance(error, InstrumentNotFoundError):
        category = ErrorCategory.NOT_FOUND
    elif isinstance(error, ProviderRateLimitError):
        category = ErrorCategory.RATE_LIMIT
        retryable = True
    elif isinstance(error, ProviderUpstreamUnavailableError):
        category = ErrorCategory.UPSTREAM_UNAVAILABLE
        retryable = True
    elif isinstance(error, ProviderResponseSchemaError):
        category = ErrorCategory.UPSTREAM_SCHEMA
        field_paths = error.field_paths
    elif isinstance(error, ProviderValidationError | ValueError):
        category = ErrorCategory.VALIDATION

    return ToolErrorDetail(
        category=category,
        message=str(error),
        retryable=retryable,
        reauthorization_required=reauthorization_required,
        field_paths=field_paths,
    )
