"""Shared schema pieces: error format, base input model and constrained types.

Design refs: ERR-01, MOD-10 (type aliases), BR-01 (amount ranges), BR-02 (date/month ranges).
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, StrictInt
from pydantic_core import PydanticCustomError

from app.domain.money import AMOUNT_MAX, AMOUNT_MIN, BUDGET_MAX, BUDGET_MIN
from app.domain.period import MAX_DATE, MIN_DATE, is_date_in_range, parse_month


class ErrorDetail(BaseModel):
    """[ERR-01] One field-level error."""

    field: str | None = Field(description="Dotted field path, or null")
    code: str = Field(description="Field error code (ERR-02)")
    params: dict[str, Any] = Field(default_factory=dict, description="Values for message placeholders")


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail]


class ErrorResponse(BaseModel):
    """[ERR-01] Every error response uses this shape."""

    error: ErrorBody


class InputModel(BaseModel):
    """[MOD-10] Request bodies reject unknown fields and trim strings."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _range_checker(minimum: int, maximum: int):
    def check(value: int) -> int:
        if not minimum <= value <= maximum:
            raise PydanticCustomError(
                "OUT_OF_RANGE",
                "Value must be between {min} and {max}",
                {"min": minimum, "max": maximum},
            )
        return value

    return check


_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _require_iso_date_string(value: Any) -> Any:
    """Accept only "YYYY-MM-DD" strings (no timestamps, no datetimes)."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise PydanticCustomError("INVALID_TYPE", "Date must be a string")
    if not _ISO_DATE_RE.match(value):
        raise PydanticCustomError("INVALID_DATE", "Date must be YYYY-MM-DD")
    return value


def _check_date(value: date) -> date:
    if not is_date_in_range(value):
        raise PydanticCustomError(
            "DATE_OUT_OF_RANGE",
            "Date must be between {min} and {max}",
            {"min": MIN_DATE.isoformat(), "max": MAX_DATE.isoformat()},
        )
    return value


def _check_month(value: str) -> str:
    if parse_month(value) is None:
        raise PydanticCustomError("INVALID_MONTH", "Month must be YYYY-MM between 2000-01 and 2099-12")
    return value


# [BR-01-1] Integers only. StrictInt rejects 1200.0, "1200" and true.
Amount = Annotated[
    StrictInt,
    AfterValidator(_range_checker(AMOUNT_MIN, AMOUNT_MAX)),
    Field(json_schema_extra={"minimum": AMOUNT_MIN, "maximum": AMOUNT_MAX}),
]
BudgetAmount = Annotated[
    StrictInt,
    AfterValidator(_range_checker(BUDGET_MIN, BUDGET_MAX)),
    Field(json_schema_extra={"minimum": BUDGET_MIN, "maximum": BUDGET_MAX}),
]
# [BR-02] Only "YYYY-MM-DD" strings, not timestamps.
AppDate = Annotated[
    date,
    BeforeValidator(_require_iso_date_string),
    AfterValidator(_check_date),
    Field(description=f"YYYY-MM-DD, {MIN_DATE.isoformat()} to {MAX_DATE.isoformat()}"),
]
MonthStr = Annotated[
    str,
    AfterValidator(_check_month),
    Field(json_schema_extra={"example": "2026-10", "format": "YYYY-MM"}),
]
# [BR-06] Serialized as a JSON string such as "12.5" (null when not computable).
RatePercent = Annotated[
    Decimal | None,
    Field(json_schema_extra={"example": "12.5"}),
]
