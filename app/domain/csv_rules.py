"""CSV import rules: encoding, header and row validation. Pure functions only.

Design refs: CSV-01 .. CSV-05.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from app.domain.categories import normalize_name
from app.domain.money import parse_csv_amount
from app.domain.period import is_date_in_range

REQUIRED_COLUMNS = ("date", "amount", "category")
OPTIONAL_COLUMNS = ("memo",)
KNOWN_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS
MEMO_MAX = 100
VALUE_PREVIEW_MAX = 50

_UTF8_BOM = b"\xef\xbb\xbf"
# Same separator on both sides: 2026-10-01 or 2026/10/1 (not 2026-10/01).
_DATE_RE = re.compile(r"^(\d{4})([-/])(\d{1,2})\2(\d{1,2})$")


@dataclass(frozen=True)
class Decoded:
    text: str
    encoding: str  # "utf-8" | "utf-8-sig" | "shift_jis"


def decode(raw: bytes) -> Decoded | None:
    """[CSV-02] BOM -> UTF-8 -> cp932 (reported as shift_jis). None if none fits."""
    if raw.startswith(_UTF8_BOM):
        try:
            return Decoded(raw[len(_UTF8_BOM) :].decode("utf-8"), "utf-8-sig")
        except UnicodeDecodeError:
            return None
    try:
        return Decoded(raw.decode("utf-8"), "utf-8")
    except UnicodeDecodeError:
        pass
    try:
        return Decoded(raw.decode("cp932"), "shift_jis")
    except UnicodeDecodeError:
        return None


@dataclass(frozen=True)
class HeaderIssue:
    column: str
    code: str  # MISSING_COLUMN | UNKNOWN_COLUMN | DUPLICATE_COLUMN


def parse_header(cells: Sequence[str]) -> dict[str, int] | list[HeaderIssue]:
    """[CSV-01][CSV-03] Column name -> index, or the list of header problems."""
    issues: list[HeaderIssue] = []
    columns: dict[str, int] = {}
    for index, cell in enumerate(cells):
        name = cell.strip().lower()
        if name not in KNOWN_COLUMNS:
            issues.append(HeaderIssue(cell.strip(), "UNKNOWN_COLUMN"))
        elif name in columns:
            issues.append(HeaderIssue(name, "DUPLICATE_COLUMN"))
        else:
            columns[name] = index
    issues.extend(HeaderIssue(name, "MISSING_COLUMN") for name in REQUIRED_COLUMNS if name not in columns)
    return issues if issues else columns


def is_blank_row(cells: Sequence[str]) -> bool:
    """[CSV-01] Empty lines (and rows of empty cells) are ignored."""
    return all(cell.strip() == "" for cell in cells)


def parse_csv_date(text: str) -> date | str:
    """[CSV-04] YYYY-MM-DD or YYYY/MM/DD (zero padding optional). Returns date or error code."""
    value = text.strip()
    if value == "":
        return "DATE_REQUIRED"
    match = _DATE_RE.match(value)
    if match is None:
        return "INVALID_DATE"
    try:
        parsed = date(int(match.group(1)), int(match.group(3)), int(match.group(4)))
    except ValueError:
        return "INVALID_DATE"
    if not is_date_in_range(parsed):
        return "DATE_OUT_OF_RANGE"
    return parsed


@dataclass(frozen=True)
class ValidRow:
    date: date
    amount: int
    category_id: str
    memo: str


@dataclass(frozen=True)
class RowError:
    code: str
    field: str | None
    value: str | None


def _preview(value: str) -> str:
    return value[:VALUE_PREVIEW_MAX]


def validate_row(
    cells: Sequence[str], columns: Mapping[str, int], resolver: Mapping[str, str]
) -> ValidRow | RowError:
    """[CSV-04] Validate one data row in the fixed order and report the first error only."""
    # The header has only known columns (CSV-03), so its width equals len(columns).
    if len(cells) != len(columns):
        return RowError("COLUMN_COUNT_MISMATCH", None, None)

    raw_date = cells[columns["date"]]
    parsed_date = parse_csv_date(raw_date)
    if isinstance(parsed_date, str):
        return RowError(parsed_date, "date", _preview(raw_date.strip()) or None)

    raw_amount = cells[columns["amount"]]
    parsed_amount = parse_csv_amount(raw_amount)
    if isinstance(parsed_amount, str):
        return RowError(parsed_amount, "amount", _preview(raw_amount.strip()) or None)

    raw_category = cells[columns["category"]].strip()
    if raw_category == "":
        return RowError("CATEGORY_REQUIRED", "category", None)
    category_id = resolver.get(normalize_name(raw_category))
    if category_id is None:
        return RowError("UNKNOWN_CATEGORY", "category", _preview(raw_category))

    memo = cells[columns["memo"]].strip() if "memo" in columns else ""
    if len(memo) > MEMO_MAX:
        return RowError("MEMO_TOO_LONG", "memo", _preview(memo))

    return ValidRow(parsed_date, parsed_amount, category_id, memo)


def duplicate_key(row: ValidRow) -> tuple[date, int, str, str]:
    """[CSV-05] Rows are duplicates when date, amount, category and memo all match."""
    return (row.date, row.amount, row.category_id, row.memo)
