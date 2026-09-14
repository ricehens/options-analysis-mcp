"""Transport-neutral, secret-safe application error details."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

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


class ErrorCategory(StrEnum):
    CONFIGURATION = "configuration"
    AUTHORIZATION = "authorization"
    ENTITLEMENT = "entitlement"
    NOT_FOUND = "not_found"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    VALIDATION = "validation"
    RATE_LIMIT = "rate_limit"
    UPSTREAM_UNAVAILABLE = "upstream_unavailable"
    UPSTREAM_SCHEMA = "upstream_schema"


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    category: ErrorCategory
    message: str
    retryable: bool
    reauthorization_required: bool = False
    field_paths: tuple[str, ...] = ()


def error_detail(error: ProviderError | ValueError) -> ErrorDetail:
    """Map internal errors without exposing credentials or upstream bodies."""

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

    return ErrorDetail(
        category=category,
        message=str(error),
        retryable=retryable,
        reauthorization_required=reauthorization_required,
        field_paths=field_paths,
    )
