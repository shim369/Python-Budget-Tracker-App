"""CSV import use case. Design refs: API-24, CSV-02..07, MOD-30 UC-3."""

from __future__ import annotations

import csv
import io
import logging

from app.config import CSV_MAX_ROWS
from app.domain.categories import build_resolver
from app.domain.csv_rules import (
    RowError,
    decode,
    duplicate_key,
    is_blank_row,
    parse_header,
)
from app.domain.csv_rules import validate_row as validate_csv_row
from app.errors import AppError, ErrorCode
from app.repositories.json_store import JsonStore
from app.repositories.models import StoredExpense, next_id
from app.schemas.common import ErrorDetail
from app.schemas.csv_import import ImportReportOut, ImportRowErrorOut

logger = logging.getLogger("budget_tracker")

DUPLICATE_CODES = {"DUPLICATE_IN_FILE", "DUPLICATE_EXISTING"}


def _read_rows(text: str) -> list[tuple[int, list[str]]]:
    """Non-blank rows with the line number where each record ends (CSV-07)."""
    reader = csv.reader(io.StringIO(text, newline=""))
    rows: list[tuple[int, list[str]]] = []
    try:
        for cells in reader:
            if not is_blank_row(cells):
                rows.append((reader.line_num, cells))
    except csv.Error as exc:
        # e.g. a field larger than csv.field_size_limit()
        raise AppError(
            ErrorCode.CSV_PARSE_ERROR,
            400,
            f"CSV could not be parsed near line {reader.line_num}.",
            [ErrorDetail(field=None, code=ErrorCode.CSV_PARSE_ERROR, params={"line": reader.line_num})],
        ) from exc
    return rows


class ImportService:
    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def import_csv(self, raw: bytes) -> ImportReportOut:
        """[CSV-03..06] Whole-file checks first, then row-by-row with partial commit."""
        if len(raw) == 0:
            raise AppError(ErrorCode.CSV_EMPTY, 400, "The file is empty.")
        decoded = decode(raw)
        if decoded is None:
            raise AppError(ErrorCode.CSV_ENCODING_UNSUPPORTED, 400, "Unsupported encoding.")
        if decoded.text.strip() == "":
            raise AppError(ErrorCode.CSV_EMPTY, 400, "The file has no content.")

        rows = _read_rows(decoded.text)
        (_, header_cells), data_rows = rows[0], rows[1:]
        columns = parse_header(header_cells)
        if isinstance(columns, list):
            raise AppError(
                ErrorCode.CSV_HEADER_INVALID,
                400,
                "Invalid header row.",
                [ErrorDetail(field=issue.column, code=issue.code) for issue in columns],
            )
        if not data_rows:
            raise AppError(ErrorCode.CSV_EMPTY, 400, "The file has no data rows.")
        if len(data_rows) > CSV_MAX_ROWS:
            raise AppError(
                ErrorCode.CSV_TOO_MANY_ROWS,
                413,
                f"Too many rows: {len(data_rows)}",
                [ErrorDetail(field=None, code=ErrorCode.CSV_TOO_MANY_ROWS, params={"max": CSV_MAX_ROWS})],
            )

        errors: list[ImportRowErrorOut] = []
        imported = 0
        with self._store.transaction() as tx:
            resolver = build_resolver(tx.data.categories)
            existing = {
                (e.date, e.amount, e.category_id, e.memo) for e in tx.data.expenses
            }
            seen_in_file: set[tuple] = set()
            for line, cells in data_rows:
                result = validate_csv_row(cells, columns, resolver)
                if isinstance(result, RowError):
                    errors.append(
                        ImportRowErrorOut(line=line, field=result.field, code=result.code, value=result.value)
                    )
                    continue
                key = duplicate_key(result)
                if key in existing:  # [CSV-05] existing wins over in-file
                    errors.append(ImportRowErrorOut(line=line, field=None, code="DUPLICATE_EXISTING", value=None))
                    continue
                if key in seen_in_file:
                    errors.append(ImportRowErrorOut(line=line, field=None, code="DUPLICATE_IN_FILE", value=None))
                    continue
                seen_in_file.add(key)
                tx.data.expenses.append(
                    StoredExpense(
                        id=next_id(tx.data, "expense"),
                        date=result.date,
                        amount=result.amount,
                        category_id=result.category_id,
                        memo=result.memo,
                    )
                )
                imported += 1
            if imported == 0:
                tx.discard()  # [CSV-06] nothing valid: leave the file untouched

        duplicates = sum(1 for e in errors if e.code in DUPLICATE_CODES)
        logger.info("CSV import: %d imported, %d skipped", imported, len(errors))
        return ImportReportOut(
            encoding=decoded.encoding,  # type: ignore[arg-type]
            total_rows=len(data_rows),
            imported_count=imported,
            error_count=len(errors) - duplicates,
            duplicate_count=duplicates,
            errors=errors,
        )
