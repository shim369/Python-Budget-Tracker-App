"""Unified error response, business exception and exception handlers.

Design refs: ERR-01 (format), ERR-02 (codes), ERR-03 (handlers), ERR-10 (AppError).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ErrorDetail

logger = logging.getLogger("budget_tracker")


class ErrorCode:
    """[ERR-02] Top-level error codes (error.code)."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_JSON = "INVALID_JSON"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    HTTP_ERROR = "HTTP_ERROR"
    EXPENSE_NOT_FOUND = "EXPENSE_NOT_FOUND"
    CATEGORY_NOT_FOUND = "CATEGORY_NOT_FOUND"
    SUBSCRIPTION_NOT_FOUND = "SUBSCRIPTION_NOT_FOUND"
    CATEGORY_FIXED = "CATEGORY_FIXED"
    CATEGORY_IN_USE = "CATEGORY_IN_USE"
    CATEGORY_NAME_DUPLICATED = "CATEGORY_NAME_DUPLICATED"
    SUBSCRIPTION_STATE_CONFLICT = "SUBSCRIPTION_STATE_CONFLICT"
    SUBSCRIPTION_INACTIVE = "SUBSCRIPTION_INACTIVE"
    SUBSCRIPTION_RENEW_TOO_EARLY = "SUBSCRIPTION_RENEW_TOO_EARLY"
    SUBSCRIPTION_DATE_LIMIT = "SUBSCRIPTION_DATE_LIMIT"
    CSV_UNSUPPORTED_MEDIA_TYPE = "CSV_UNSUPPORTED_MEDIA_TYPE"
    CSV_TOO_LARGE = "CSV_TOO_LARGE"
    CSV_TOO_MANY_ROWS = "CSV_TOO_MANY_ROWS"
    CSV_EMPTY = "CSV_EMPTY"
    CSV_ENCODING_UNSUPPORTED = "CSV_ENCODING_UNSUPPORTED"
    CSV_HEADER_INVALID = "CSV_HEADER_INVALID"
    CSV_PARSE_ERROR = "CSV_PARSE_ERROR"
    STORAGE_WRITE_FAILED = "STORAGE_WRITE_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """[ERR-10] Business error converted to the unified error response."""

    def __init__(
        self,
        code: str,
        status: int,
        message: str,
        details: Sequence[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.message = message
        self.details = list(details or [])


def not_found(code: str, resource_id: str) -> AppError:
    return AppError(code, 404, f"Resource not found: {resource_id}")


def conflict(code: str, message: str, params: dict[str, Any] | None = None) -> AppError:
    details = [ErrorDetail(field=None, code=code, params=params)] if params is not None else []
    return AppError(code, 409, message, details)


def field_error(field: str, code: str, params: dict[str, Any] | None = None) -> AppError:
    """400 VALIDATION_ERROR for checks done in the service layer (e.g. UNKNOWN_CATEGORY)."""
    return validation_error([ErrorDetail(field=field, code=code, params=params or {})])


def validation_error(details: Sequence[ErrorDetail]) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, 400, "Request validation failed.", details)


def error_body(code: str, message: str, details: Sequence[ErrorDetail] = ()) -> dict[str, Any]:
    """[ERR-01] {"error": {"code", "message", "details"}}."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": [d.model_dump(mode="json") for d in details],
        }
    }


# [ERR-03] Pydantic error type -> field error code.
_TYPE_MAP: dict[str, str] = {
    "missing": "FIELD_REQUIRED",
    "int_type": "INVALID_TYPE",
    "int_parsing": "INVALID_TYPE",
    "int_from_float": "INVALID_TYPE",
    "string_type": "INVALID_TYPE",
    "bool_type": "INVALID_TYPE",
    "date_type": "INVALID_TYPE",
    "dict_type": "INVALID_TYPE",
    "list_type": "INVALID_TYPE",
    "model_type": "INVALID_TYPE",
    "model_attributes_type": "INVALID_TYPE",
    "greater_than_equal": "OUT_OF_RANGE",
    "less_than_equal": "OUT_OF_RANGE",
    "greater_than": "OUT_OF_RANGE",
    "less_than": "OUT_OF_RANGE",
    "string_too_short": "TOO_SHORT",
    "string_too_long": "TOO_LONG",
    "date_parsing": "INVALID_DATE",
    "date_from_datetime_parsing": "INVALID_DATE",
    "date_from_datetime_inexact": "INVALID_DATE",
    "literal_error": "INVALID_CHOICE",
    "enum": "INVALID_CHOICE",
    "extra_forbidden": "UNKNOWN_FIELD",
}
_LOCATION_PREFIXES = {"body", "query", "path", "header", "cookie"}
_CUSTOM_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")


def _field_path(loc: Sequence[Any]) -> str | None:
    parts = list(loc)
    if parts and parts[0] in _LOCATION_PREFIXES:
        parts = parts[1:]
    return ".".join(str(p) for p in parts) or None


def _params(error_type: str, ctx: dict[str, Any]) -> dict[str, Any]:
    if error_type in ("greater_than_equal", "greater_than"):
        return {"min": ctx.get("ge", ctx.get("gt"))}
    if error_type in ("less_than_equal", "less_than"):
        return {"max": ctx.get("le", ctx.get("lt"))}
    if error_type == "string_too_short":
        return {"min": ctx.get("min_length")}
    if error_type == "string_too_long":
        return {"max": ctx.get("max_length")}
    if error_type in ("literal_error", "enum"):
        return {"choices": re.findall(r"'([^']*)'", str(ctx.get("expected", "")))}
    return {}


def pydantic_errors_to_details(errors: Sequence[dict[str, Any]]) -> list[ErrorDetail]:
    """[ERR-03] Convert Pydantic errors to ErrorDetail using the mapping table."""
    details = []
    for err in errors:
        error_type = str(err.get("type", ""))
        ctx = dict(err.get("ctx") or {})
        if _CUSTOM_CODE_RE.match(error_type):
            # PydanticCustomError raised by our own validators carries its code and params.
            code, params = error_type, {k: v for k, v in ctx.items() if k != "reason"}
        else:
            code, params = _TYPE_MAP.get(error_type, "INVALID_VALUE"), _params(error_type, ctx)
        details.append(ErrorDetail(field=_field_path(err.get("loc", ())), code=code, params=params))
    return details


async def _handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = list(exc.errors())
    if any(err.get("type") == "json_invalid" for err in errors):
        return JSONResponse(error_body(ErrorCode.INVALID_JSON, "Malformed JSON body."), status_code=400)
    details = pydantic_errors_to_details(errors)
    return JSONResponse(
        error_body(ErrorCode.VALIDATION_ERROR, "Request validation failed.", details),
        status_code=400,
    )


async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    if exc.status >= 500:
        logger.error("%s: %s", exc.code, exc.message)
    elif exc.status in (409, 413, 415):
        logger.warning("%s: %s", exc.code, exc.message)
    return JSONResponse(error_body(exc.code, exc.message, exc.details), status_code=exc.status)


async def _handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {404: ErrorCode.NOT_FOUND, 405: ErrorCode.METHOD_NOT_ALLOWED}.get(
        exc.status_code, ErrorCode.HTTP_ERROR
    )
    return JSONResponse(
        error_body(code, str(exc.detail)),
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
    )


async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    return JSONResponse(
        error_body(ErrorCode.INTERNAL_ERROR, "Unexpected error occurred."), status_code=500
    )


def register_exception_handlers(app: FastAPI) -> None:
    """[ERR-03] Replace FastAPI's default 422 format with the unified format."""
    app.add_exception_handler(RequestValidationError, _handle_request_validation)  # type: ignore[arg-type]
    app.add_exception_handler(AppError, _handle_app_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unexpected)
