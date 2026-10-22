"""Consistent JSON error handling for the Nexus-Intel API.

Every error response uses the same envelope::

    {"error": {"code": "not_found", "message": "...", "details": [...]}}

Stack traces, database connection strings, API keys and other internals are
never sent to clients; they are logged server-side (sanitised) instead.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("nexus_intel.api")

ERROR_ENVELOPE_MEDIA_TYPE = "application/json"


class ApiException(Exception):
    """Base class for errors that map cleanly onto an HTTP status code."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: list | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []


class DatabaseUnavailableError(ApiException):
    """MongoDB could not be reached for a required operation."""

    def __init__(self, message: str = "The database is unavailable right now. Please retry shortly.") -> None:
        super().__init__("database_unavailable", message, status.HTTP_503_SERVICE_UNAVAILABLE)


class PipelineExecutionError(ApiException):
    """The orchestrator pipeline failed (upstream search/fetch/extraction)."""

    def __init__(self, message: str = "The analysis pipeline failed while fetching competitor data.") -> None:
        super().__init__("pipeline_failed", message, status.HTTP_502_BAD_GATEWAY)


class AnalysisTimeoutError(ApiException):
    """The pipeline did not finish within ``ANALYSIS_TIMEOUT_SECONDS``."""

    def __init__(self, message: str = "The analysis timed out before completing.") -> None:
        super().__init__("analysis_timeout", message, status.HTTP_504_GATEWAY_TIMEOUT)


def error_payload(code: str, message: str, details: list | None = None) -> dict:
    body: dict = {"code": code, "message": message}
    if details:
        body["details"] = details
    return {"error": body}


def error_response(code: str, message: str, status_code: int, details: list | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code, message, details),
        media_type=ERROR_ENVELOPE_MEDIA_TYPE,
    )


def _validation_details(exc: RequestValidationError) -> list[dict]:
    """Reduce pydantic errors to JSON-safe fields (loc/msg/type only)."""
    details: list[dict] = []
    for err in exc.errors():
        details.append(
            {
                "loc": [str(part) for part in err.get("loc", [])],
                "message": err.get("msg", "Invalid value."),
                "type": err.get("type", "value_error"),
            }
        )
    return details


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the shared error handlers to the application instance."""

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(
            "validation_error",
            "The request payload failed validation.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            _validation_details(exc),
        )

    @app.exception_handler(HTTPException)
    async def _http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        code = "http_error"
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            code = "not_found"
        elif exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            code = "method_not_allowed"
        return error_response(code, message, exc.status_code)

    @app.exception_handler(ApiException)
    async def _api_error_handler(request: Request, exc: ApiException) -> JSONResponse:
        return error_response(exc.code, exc.message, exc.status_code, exc.details)

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log server-side only; never echo internals (stack traces, DSNs, keys).
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return error_response(
            "internal_error",
            "An unexpected server error occurred.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
