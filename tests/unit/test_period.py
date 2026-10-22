"""UT-PER: month boundaries (BR-02)."""

from datetime import date

import pytest

from app.domain.period import (
    is_date_in_range,
    last_n_months,
    month_of,
    month_range,
    next_month,
    parse_month,
    previous_month,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [("2026-10", (2026, 10)), ("2000-01", (2000, 1)), ("2099-12", (2099, 12))],
)
def test_ut_per_01_parse_month_valid(text, expected):
    assert parse_month(text) == expected


@pytest.mark.parametrize(
    "text", ["2026-1", "2026-13", "2026-00", "1999-12", "2100-01", "2026/10", "abcd-ef", ""]
)
def test_ut_per_02_parse_month_invalid(text):
    assert parse_month(text) is None


def test_ut_per_03_month_of():
    assert month_of(date(2026, 10, 31)) == "2026-10"
    assert month_of(date(2026, 11, 1)) == "2026-11"


@pytest.mark.parametrize(
    ("ym", "last"),
    [("2027-02", 28), ("2028-02", 29), ("2026-04", 30), ("2026-12", 31)],
)
def test_ut_per_04_month_range(ym, last):
    first, end = month_range(ym)
    year, month = parse_month(ym)
    assert first == date(year, month, 1)
    assert end == date(year, month, last)


def test_ut_per_05_previous_month():
    assert previous_month("2026-01") == "2025-12"
    assert previous_month("2026-10") == "2026-09"
    assert previous_month("2000-01") is None


def test_ut_per_06_next_month():
    assert next_month("2026-12") == "2027-01"
    assert next_month("2099-12") is None


def test_ut_per_07_last_n_months():
    assert last_n_months("2026-03", 6) == [
        "2025-10",
        "2025-11",
        "2025-12",
        "2026-01",
        "2026-02",
        "2026-03",
    ]


@pytest.mark.parametrize(
    ("d", "expected"),
    [
        (date(1999, 12, 31), False),
        (date(2000, 1, 1), True),
        (date(2099, 12, 31), True),
        (date(2100, 1, 1), False),
    ],
)
def test_ut_per_08_date_range(d, expected):
    assert is_date_in_range(d) is expected


@pytest.mark.parametrize(
    "call",
    [
        lambda: month_range("2026-13"),
        lambda: previous_month("bad"),
        lambda: last_n_months("bad", 6),
    ],
)
def test_ut_per_09_invalid_month_raises(call):
    with pytest.raises(ValueError):
        call()
