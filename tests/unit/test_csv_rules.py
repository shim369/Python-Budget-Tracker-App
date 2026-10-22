"""UT-CSV: CSV encoding, header and row validation (CSV-01..05)."""

from datetime import date

import pytest

from app.domain.categories import build_resolver
from app.domain.csv_rules import (
    HeaderIssue,
    RowError,
    ValidRow,
    decode,
    duplicate_key,
    is_blank_row,
    parse_csv_date,
    parse_header,
    validate_row,
)
from app.repositories.models import DataFile

COLUMNS = {"date": 0, "amount": 1, "category": 2, "memo": 3}
RESOLVER = build_resolver(DataFile.initial().categories)


def test_ut_csv_01_utf8():
    result = decode("date,memo\n2026-10-01,ランチ\n".encode())
    assert result is not None and result.encoding == "utf-8"


def test_ut_csv_02_utf8_bom():
    result = decode(b"\xef\xbb\xbf" + "date\n食費\n".encode())
    assert result is not None and result.encoding == "utf-8-sig"
    assert result.text.startswith("date")


def test_ut_csv_03_shift_jis_with_vendor_chars():
    result = decode("category,memo\n食費,①髙島屋\n".encode("cp932"))
    assert result is not None and result.encoding == "shift_jis"
    assert "①髙島屋" in result.text


def test_ut_csv_04_ascii():
    result = decode(b"date,amount\n")
    assert result is not None and result.encoding == "utf-8"


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("date,金額\n".encode("utf-16"), id="utf16"),
        # BUG-001: these decoded "successfully" as utf-8 / shift_jis before the fix.
        pytest.param("date,amount,category\n".encode("utf-16"), id="BUG-001-utf16-bom-ascii"),
        pytest.param("date,amount,category\n".encode("utf-16-le"), id="BUG-001-utf16le-no-bom"),
        pytest.param("date,amount,category\n".encode("utf-16-be"), id="BUG-001-utf16be-no-bom"),
        pytest.param("date,金額\n".encode("utf-16-be"), id="BUG-001-utf16be-cjk"),
        pytest.param("date\n".encode("utf-32"), id="BUG-001-utf32"),
        pytest.param(b"date,amount\x00\n", id="BUG-001-nul-byte"),
        pytest.param(b"\xef\xbb\xbf\xff\xfe", id="bom-then-invalid"),
        pytest.param(b"\x81\x20\xff", id="invalid-both"),
    ],
)
def test_ut_csv_05_undecodable(raw):
    assert decode(raw) is None


def test_ut_csv_06_header_any_order_and_case():
    assert parse_header([" Amount", "DATE", "memo ", "Category"]) == {
        "amount": 0,
        "date": 1,
        "memo": 2,
        "category": 3,
    }


def test_ut_csv_07_memo_optional():
    assert parse_header(["date", "amount", "category"]) == {"date": 0, "amount": 1, "category": 2}


def test_ut_csv_08_header_problems():
    assert parse_header(["date", "amonut", "date"]) == [
        HeaderIssue("amonut", "UNKNOWN_COLUMN"),
        HeaderIssue("date", "DUPLICATE_COLUMN"),
        HeaderIssue("amount", "MISSING_COLUMN"),
        HeaderIssue("category", "MISSING_COLUMN"),
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [("2026-10-01", date(2026, 10, 1)), ("2026/10/1", date(2026, 10, 1)), ("2026/1/05", date(2026, 1, 5))],
)
def test_ut_csv_09_date_formats(text, expected):
    assert parse_csv_date(text) == expected


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("", "DATE_REQUIRED"),
        ("2026-02-30", "INVALID_DATE"),
        ("2026-10/01", "INVALID_DATE"),
        ("20261001", "INVALID_DATE"),
        ("26-10-01", "INVALID_DATE"),
        ("1999-12-31", "DATE_OUT_OF_RANGE"),
        ("2100-01-01", "DATE_OUT_OF_RANGE"),
    ],
)
def test_ut_csv_10_date_errors(text, code):
    assert parse_csv_date(text) == code


def test_ut_csv_11_valid_row():
    memo = "あ" * 100
    assert validate_row(["2026/10/2", "3,980", "日用品", memo], COLUMNS, RESOLVER) == ValidRow(
        date(2026, 10, 2), 3980, "cat-000002", memo
    )


def test_ut_csv_12_column_count():
    assert validate_row(["2026-10-01", "100", "food"], COLUMNS, RESOLVER) == RowError(
        "COLUMN_COUNT_MISMATCH", None, None
    )


def test_ut_csv_13_first_error_wins():
    result = validate_row(["bad", "abc", "food", ""], COLUMNS, RESOLVER)
    assert result == RowError("INVALID_DATE", "date", "bad")


@pytest.mark.parametrize(
    ("category", "expected"),
    [("", RowError("CATEGORY_REQUIRED", "category", None)), ("fodo", RowError("UNKNOWN_CATEGORY", "category", "fodo"))],
)
def test_ut_csv_14_category_errors(category, expected):
    assert validate_row(["2026-10-01", "100", category, ""], COLUMNS, RESOLVER) == expected


def test_ut_csv_15_memo_too_long():
    result = validate_row(["2026-10-01", "100", "food", "x" * 101], COLUMNS, RESOLVER)
    assert isinstance(result, RowError) and result.code == "MEMO_TOO_LONG"


def test_ut_csv_16_value_preview_truncated():
    result = validate_row(["2026-10-01", "9" * 80, "food", ""], COLUMNS, RESOLVER)
    assert isinstance(result, RowError) and result.code == "AMOUNT_OUT_OF_RANGE"
    assert len(result.value) == 50


def test_ut_csv_17_duplicate_key_is_normalized():
    a = validate_row(["2026/10/1", "1,200", "食費", "Lunch"], COLUMNS, RESOLVER)
    b = validate_row(["2026-10-01", "1200", "food", " Lunch "], COLUMNS, RESOLVER)
    assert duplicate_key(a) == duplicate_key(b)


@pytest.mark.parametrize(("cells", "expected"), [([], True), (["", " "], True), (["", "1"], False)])
def test_ut_csv_18_blank_row(cells, expected):
    assert is_blank_row(cells) is expected
