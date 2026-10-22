"""UT-MNY: money rules (BR-01, BR-04-1)."""

import pytest

from app.domain.money import monthly_equivalent, parse_csv_amount


@pytest.mark.parametrize(
    ("amount", "cycle", "expected"),
    [
        pytest.param(1490, "monthly", 1490, id="UT-MNY-01"),
        pytest.param(12000, "yearly", 1000, id="UT-MNY-02"),
        pytest.param(1490, "yearly", 124, id="UT-MNY-03"),
        pytest.param(11, "yearly", 0, id="UT-MNY-04"),
        pytest.param(9_999_999, "yearly", 833_333, id="UT-MNY-05"),
    ],
)
def test_monthly_equivalent(amount, cycle, expected):
    assert monthly_equivalent(amount, cycle) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("1200", 1200, id="UT-MNY-06-plain"),
        pytest.param("1,200", 1200, id="UT-MNY-06-grouped"),
        pytest.param(" 3,980 ", 3980, id="UT-MNY-06-spaces"),
        pytest.param("9,999,999", 9_999_999, id="UT-MNY-06-max-grouped"),
        pytest.param("", "AMOUNT_REQUIRED", id="UT-MNY-07-empty"),
        pytest.param("  ", "AMOUNT_REQUIRED", id="UT-MNY-07-blank"),
        pytest.param("1.5", "INVALID_AMOUNT", id="UT-MNY-08-decimal"),
        pytest.param("-100", "INVALID_AMOUNT", id="UT-MNY-08-negative"),
        pytest.param("¥1200", "INVALID_AMOUNT", id="UT-MNY-08-yen-sign"),
        pytest.param("1200円", "INVALID_AMOUNT", id="UT-MNY-08-yen-suffix"),
        pytest.param("1,20", "INVALID_AMOUNT", id="UT-MNY-08-bad-group"),
        pytest.param("12,0000", "INVALID_AMOUNT", id="UT-MNY-08-bad-group2"),
        pytest.param("abc", "INVALID_AMOUNT", id="UT-MNY-08-text"),
        pytest.param("１２００", "INVALID_AMOUNT", id="UT-MNY-08-fullwidth"),
        pytest.param("0", "AMOUNT_OUT_OF_RANGE", id="UT-MNY-09-zero"),
        pytest.param("1", 1, id="UT-MNY-09-min"),
        pytest.param("9999999", 9_999_999, id="UT-MNY-09-max"),
        pytest.param("10000000", "AMOUNT_OUT_OF_RANGE", id="UT-MNY-09-over"),
    ],
)
def test_parse_csv_amount(text, expected):
    assert parse_csv_amount(text) == expected
