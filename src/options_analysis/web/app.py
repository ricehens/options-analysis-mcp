"""FastAPI facade over the reusable application services."""

import asyncio
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import FastAPI, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from options_analysis import __version__
from options_analysis.bootstrap import Application, build_application
from options_analysis.config import AppSettings
from options_analysis.domain import PutCall
from options_analysis.errors import ErrorCategory, ErrorDetail, error_detail
from options_analysis.providers import OptionChainQuery
from options_analysis.providers.errors import ProviderError
from options_analysis.web.models import (
    ProviderListResult,
    ProviderSummary,
    ServerInfo,
    ServerInfoResult,
    WorkspaceResult,
    WorkspaceSnapshot,
)

_LOCAL_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)


def _error_status(detail: ErrorDetail) -> int:
    return {
        ErrorCategory.AUTHORIZATION: 401,
        ErrorCategory.ENTITLEMENT: 403,
        ErrorCategory.NOT_FOUND: 404,
        ErrorCategory.RATE_LIMIT: 429,
        ErrorCategory.UPSTREAM_UNAVAILABLE: 503,
        ErrorCategory.UPSTREAM_SCHEMA: 502,
    }.get(detail.category, 400)


def _error_response(
    detail: ErrorDetail, status_code: int | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code or _error_status(detail),
        content=jsonable_encoder({"error": detail}),
    )


def create_app(
    settings: AppSettings | None = None,
    *,
    application: Application | None = None,
) -> FastAPI:
    """Build an isolated HTTP application for serving or tests."""

    resolved_application = application or build_application(settings)
    app = FastAPI(
        title="Options Analysis API",
        summary="Read-only provider-neutral market-data API for the browser UI",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(_LOCAL_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type"],
    )

    async def handled_error(_: Request, error: Exception) -> JSONResponse:
        assert isinstance(error, ProviderError)
        return _error_response(error_detail(error))

    async def invalid_value(_: Request, error: Exception) -> JSONResponse:
        assert isinstance(error, ValueError)
        return _error_response(error_detail(error))

    async def invalid_request(_: Request, error: Exception) -> JSONResponse:
        assert isinstance(error, RequestValidationError)
        field_paths = tuple(
            ".".join(str(part) for part in item["loc"] if part != "query")
            for item in error.errors()[:5]
        )
        return _error_response(
            ErrorDetail(
                category=ErrorCategory.VALIDATION,
                message="request validation failed",
                retryable=False,
                field_paths=field_paths,
            ),
            422,
        )

    app.add_exception_handler(ProviderError, handled_error)
    app.add_exception_handler(ValueError, invalid_value)
    app.add_exception_handler(RequestValidationError, invalid_request)

    @app.get("/api/v1/info", response_model=ServerInfoResult)
    async def info() -> ServerInfoResult:
        public = resolved_application.settings.public_view()
        return ServerInfoResult(
            info=ServerInfo(
                name="options-analysis",
                version=__version__,
                environment=public.environment,
                read_only=True,
                default_market_data_provider=public.default_market_data_provider,
            )
        )

    @app.get("/api/v1/providers", response_model=ProviderListResult)
    async def providers() -> ProviderListResult:
        public = resolved_application.settings.public_view()
        return ProviderListResult(
            providers=tuple(
                ProviderSummary(
                    provider_id=status.descriptor.provider_id,
                    display_name=status.descriptor.display_name,
                    capabilities=tuple(
                        sorted(item.value for item in status.descriptor.capabilities)
                    ),
                    freshness_modes=tuple(
                        sorted(item.value for item in status.descriptor.freshness_modes)
                    ),
                    configured=status.configured,
                    ready=status.ready,
                    message=status.message,
                )
                for status in resolved_application.provider_service.list_statuses()
            ),
            default_market_data_provider=public.default_market_data_provider,
        )

    @app.get("/api/v1/workspaces/{symbol}", response_model=WorkspaceResult)
    async def workspace(
        symbol: str,
        provider: str | None = None,
        expiration: date | None = None,
        put_call: PutCall | None = None,
        strike_from: Annotated[Decimal | None, Query(gt=0)] = None,
        strike_to: Annotated[Decimal | None, Query(gt=0)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 40,
    ) -> WorkspaceResult:
        normalized = symbol.strip().upper()
        if not normalized:
            raise ValueError("symbol must not be empty")
        query = OptionChainQuery(
            underlying_symbol=normalized,
            expiration_from=expiration,
            expiration_to=expiration,
            put_call=put_call,
            strike_from=strike_from,
            strike_to=strike_to,
            limit=limit,
        )
        quote, expirations, chain = await asyncio.gather(
            resolved_application.market_data_service.get_underlying_quote(
                normalized, provider
            ),
            resolved_application.market_data_service.get_option_expirations(
                normalized, provider
            ),
            resolved_application.market_data_service.get_option_chain(query, provider),
        )
        return WorkspaceResult(
            workspace=WorkspaceSnapshot(
                provider_id=quote.provider_id,
                symbol=normalized,
                quote=quote,
                expirations=expirations,
                chain=chain,
            )
        )

    return app


app = create_app()
