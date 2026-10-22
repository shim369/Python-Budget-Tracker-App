"""UT-BGT: budget judgement boundaries (BR-05)."""

import pytest

from app.domain.budget_rule import BudgetStatus, judge, usage_percent


@pytest.mark.parametrize(
    ("spent", "budget", "status", "usage"),
    [
        pytest.param(0, 10_000, BudgetStatus.OK, 0, id="UT-BGT-01-zero"),
        pytest.param(7_900, 10_000, BudgetStatus.OK, 79, id="UT-BGT-02-79"),
        pytest.param(7_999, 10_000, BudgetStatus.OK, 79, id="UT-BGT-03-79.99"),
        pytest.param(8_000, 10_000, BudgetStatus.CAUTION, 80, id="UT-BGT-04-80"),
        pytest.param(9_900, 10_000, BudgetStatus.CAUTION, 99, id="UT-BGT-05-99"),
        pytest.param(10_000, 10_000, BudgetStatus.CAUTION, 100, id="UT-BGT-06-exactly-100"),
        pytest.param(10_001, 10_000, BudgetStatus.OVER, 100, id="UT-BGT-07-100.01"),
        pytest.param(10_100, 10_000, BudgetStatus.OVER, 101, id="UT-BGT-08-101"),
    ],
)
def test_judge_boundaries(spent, budget, status, usage):
    assert judge(spent, budget) is status
    assert usage_percent(spent, budget) == usage


@pytest.mark.parametrize("budget", [None, 0])
def test_ut_bgt_09_no_budget(budget):
    assert judge(5_000, budget) is BudgetStatus.NONE
    assert usage_percent(5_000, budget) is None


@pytest.mark.parametrize(
    ("spent", "budget", "status"),
    [
        pytest.param(2, 3, BudgetStatus.OK, id="66.7pct"),
        pytest.param(8, 10, BudgetStatus.CAUTION, id="80pct-small"),
        pytest.param(12, 15, BudgetStatus.CAUTION, id="80pct-non-round-budget"),
    ],
)
def test_ut_bgt_10_integer_comparison(spent, budget, status):
    assert judge(spent, budget) is status
