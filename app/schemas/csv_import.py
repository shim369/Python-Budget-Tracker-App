"""CSV import report schema. Design refs: API-24, CSV-07."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ImportRowErrorOut(BaseModel):
    line: int
    field: str | None
    code: str
    value: str | None


class ImportReportOut(BaseModel):
    """total_rows == imported_count + error_count + duplicate_count."""

    encoding: Literal["utf-8", "utf-8-sig", "shift_jis"]
    total_rows: int
    imported_count: int
    error_count: int
    duplicate_count: int
    errors: list[ImportRowErrorOut]
