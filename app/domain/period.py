"""Month boundaries and date ranges. Pure functions only.

Design ref: BR-02.
"""

from __future__ import annotations

import calendar
import re
from datetime import date

MIN_DATE = date(2000, 1, 1)
MAX_DATE = date(2099, 12, 31)
MIN_MONTH = "2000-01"
MAX_MONTH = "2099-12"

_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")


def is_date_in_range(d: date) -> bool:
    """[BR-02] Dates are accepted only between 2000-01-01 and 2099-12-31."""
    return MIN_DATE <= d <= MAX_DATE


def parse_month(text: str) -> tuple[int, int] | None:
    """[BR-02] Parse "YYYY-MM". Returns None when the format or range is invalid."""
    match = _MONTH_RE.match(text)
    if match is None:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12 or not MIN_DATE.year <= year <= MAX_DATE.year:
        return None
    return year, month


def format_month(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def month_of(d: date) -> str:
    """[BR-02] An expense belongs to the month of its calendar date."""
    return format_month(d.year, d.month)


def last_day(year: int, month: int) -> int:
    """Last day of the month (leap years included)."""
    return calendar.monthrange(year, month)[1]


def month_range(ym: str) -> tuple[date, date]:
    """[BR-02] First and last day (inclusive) of the month."""
    parsed = parse_month(ym)
    if parsed is None:
        raise ValueError(f"invalid month: {ym!r}")
    year, month = parsed
    return date(year, month, 1), date(year, month, last_day(year, month))


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """Move by `delta` months without range checks."""
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def _shift_checked(ym: str, delta: int) -> str | None:
    parsed = parse_month(ym)
    if parsed is None:
        raise ValueError(f"invalid month: {ym!r}")
    shifted = format_month(*shift_month(*parsed, delta))
    return shifted if parse_month(shifted) is not None else None


def previous_month(ym: str) -> str | None:
    """[BR-02] January -> previous December. None before 2000-01."""
    return _shift_checked(ym, -1)


def next_month(ym: str) -> str | None:
    """[BR-02] December -> next January. None after 2099-12."""
    return _shift_checked(ym, 1)


def last_n_months(ym: str, n: int) -> list[str]:
    """[BR-07-3] The n months ending with `ym`, oldest first.

    Months before 2000-01 may appear; they simply have no expenses.
    """
    parsed = parse_month(ym)
    if parsed is None:
        raise ValueError(f"invalid month: {ym!r}")
    return [format_month(*shift_month(*parsed, -offset)) for offset in range(n - 1, -1, -1)]
