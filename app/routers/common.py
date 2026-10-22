"""OpenAPI error response declarations shared by routers. Design ref: ERR-01."""

from __future__ import annotations

from typing import Any

from app.schemas.common import ErrorResponse

_DESCRIPTIONS = {
    400: "Validation error (VALIDATION_ERROR / INVALID_JSON / CSV_*)",
    404: "Resource not found",
    409: "State conflict",
    413: "CSV too large",
    415: "Unsupported media type",
}


def error_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    """Declare the unified error schema for the given status codes in /docs."""
    return {code: {"model": ErrorResponse, "description": _DESCRIPTIONS[code]} for code in codes}
