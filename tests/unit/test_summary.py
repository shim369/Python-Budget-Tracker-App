"""UT-SUM: aggregation, month-over-month change and chart data (BR-05..07)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest

from app.domain.budget_rule import BudgetStatus
from app.domain.summary import (
    breakdown,
    build_alerts,
    change_rate,
    month_total,
    ratio_percent,
    summarize_categories,
    totals_by_category,
    trend,
)


@dataclass
class Exp:
    date: date
    amount: int
    category_id: str


# BR-06 table
@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [
        pytest.param(10_000, 11_250, "12.5", id="UT-SUM-01-increase"),
        pytest.param(10_000, 10_000, "0.0", id="UT-SUM-02-same"),
        pytest.param(10_000, 0, "-100.0", id="UT-SUM-03-to-zero"),
        pytest.param(0, 5_000, None, id="UT-SUM-04-prev-zero"),
        pytest.param(0, 0, None, id="UT-SUM-05-both-zero"),
        pytest.param(3, 4, "33.3", id="UT-SUM-06-round-down"),
        pytest.param(3, 5, "66.7", id="UT-SUM-07-round-up"),
        pytest.param(8, 9, "12.5", id="UT-SUM-08-exact-half-digit"),
        pytest.param(16, 17, "6.3", id="UT-SUM-09-half-up"),
        pytest.param(16, 15, "-6.3", id="UT-SUM-10-half-up-negative"),
    ],
)
def test_change_rate(previous, current, expected):
    result = change_rate(current, previous)
    assert result == (None if expected is None else Decimal(expected))
    if expected is not None:
        assert str(result) == expected


def test_ut_sum_11_ratio_percent():
    assert str(ratio_percent(42_000, 112_500)) == "37.3"
    assert str(ratio_percent(1, 3)) == "33.3"
    assert str(ratio_percent(2, 3)) == "66.7"


def test_ut_sum_12_month_boundary():
    expenses = [
        Exp(date(2026, 9, 30), 1, "cat-000001"),
        Exp(date(2026, 10, 1), 10, "cat-000001"),
        Exp(date(2026, 10, 31), 100, "cat-000001"),
        Exp(date(2026, 11, 1), 1000, "cat-000001"),
    ]
    assert month_total(expenses, "2026-10") == 110
    assert totals_by_category(expenses, "2026-10") == {"cat-000001": 110}


def test_ut_sum_13_month_none():
    assert month_total([Exp(date(2026, 10, 1), 10, "c")], None) == 0
    assert totals_by_category([Exp(date(2026, 10, 1), 10, "c")], None) == {}


def test_ut_sum_14_category_targets():
    expenses = [
        Exp(date(2026, 10, 5), 500, "cat-a"),  # this month only
        Exp(date(2026, 9, 5), 300, "cat-b"),  # previous month only
        Exp(date(2026, 8, 5), 999, "cat-d"),  # two months ago: not a target
    ]
    lines = summarize_categories(expenses, "2026-10", "2026-09", {"cat-c": 1000})
    by_id = {line.category_id: line for line in lines}
    assert set(by_id) == {"cat-a", "cat-b", "cat-c"}
    assert by_id["cat-b"].total == 0 and by_id["cat-b"].change_rate == Decimal("-100.0")
    assert by_id["cat-a"].change_rate is None and by_id["cat-a"].status is BudgetStatus.NONE
    assert by_id["cat-c"].status is BudgetStatus.OK and by_id["cat-c"].usage_percent == 0


def test_ut_sum_15_category_order():
    expenses = [
        Exp(date(2026, 10, 1), 100, "cat-b"),
        Exp(date(2026, 10, 1), 100, "cat-a"),
        Exp(date(2026, 10, 1), 500, "cat-z"),
    ]
    lines = summarize_categories(expenses, "2026-10", None, {})
    assert [line.category_id for line in lines] == ["cat-z", "cat-a", "cat-b"]


def test_ut_sum_16_alert_order():
    expenses = [
        Exp(date(2026, 10, 1), 850, "cat-a"),  # 85% caution
        Exp(date(2026, 10, 1), 950, "cat-b"),  # 95% caution
        Exp(date(2026, 10, 1), 1100, "cat-c"),  # 110% over
    ]
    lines = summarize_categories(expenses, "2026-10", None, {"cat-a": 1000, "cat-b": 1000, "cat-c": 1000})
    alerts = build_alerts(2900, 3000, lines)  # overall 96% caution
    assert [(a.scope, a.category_id, a.status.value) for a in alerts] == [
        ("category", "cat-c", "over"),
        ("overall", None, "caution"),
        ("category", "cat-b", "caution"),
        ("category", "cat-a", "caution"),
    ]


def test_ut_sum_17_alert_excludes_ok_and_none():
    expenses = [Exp(date(2026, 10, 1), 100, "cat-a"), Exp(date(2026, 10, 1), 100, "cat-b")]
    lines = summarize_categories(expenses, "2026-10", None, {"cat-a": 1000})
    assert build_alerts(200, None, lines) == []


def _expenses_for(count: int) -> list[Exp]:
    # cat-01 has the largest amount, cat-<count> the smallest.
    return [Exp(date(2026, 10, 1), (count - i) * 100, f"cat-{i + 1:02d}") for i in range(count)]


def test_ut_sum_18_breakdown_empty():
    assert breakdown([], "2026-10") == (0, [])


def test_ut_sum_19_breakdown_single():
    total, slices = breakdown(_expenses_for(1), "2026-10")
    assert total == 100
    assert [(s.kind, str(s.ratio_percent)) for s in slices] == [("category", "100.0")]


def test_ut_sum_20_breakdown_eight_no_other():
    _, slices = breakdown(_expenses_for(8), "2026-10")
    assert len(slices) == 8
    assert all(s.kind == "category" for s in slices)


def test_ut_sum_21_breakdown_nine_with_other():
    _, slices = breakdown(_expenses_for(9), "2026-10")
    assert len(slices) == 8
    assert [s.category_id for s in slices[:7]] == [f"cat-{i:02d}" for i in range(1, 8)]
    assert slices[-1].kind == "other"
    assert slices[-1].category_id is None
    assert slices[-1].amount == 200 + 100  # cat-08 + cat-09


def test_ut_sum_22_breakdown_tie_order():
    expenses = [Exp(date(2026, 10, 1), 100, "cat-b"), Exp(date(2026, 10, 1), 100, "cat-a")]
    _, slices = breakdown(expenses, "2026-10")
    assert [s.category_id for s in slices] == ["cat-a", "cat-b"]


def test_ut_sum_23_trend_zero_months_and_year_boundary():
    expenses = [Exp(date(2025, 12, 31), 10, "c"), Exp(date(2026, 2, 1), 20, "c"), Exp(date(2026, 3, 1), 99, "c")]
    assert trend(expenses, "2026-02") == [
        ("2025-09", 0),
        ("2025-10", 0),
        ("2025-11", 0),
        ("2025-12", 10),
        ("2026-01", 0),
        ("2026-02", 20),
    ]
