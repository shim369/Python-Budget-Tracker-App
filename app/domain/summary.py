"""Monthly aggregation, month-over-month change and chart data. Pure functions only.

Design refs: BR-05 (alerts order), BR-06 (change rate), BR-07 (aggregation, charts).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, Protocol

from app.domain.budget_rule import BudgetStatus, judge, usage_percent
from app.domain.period import last_n_months, month_of

_ONE_DECIMAL = Decimal("0.1")
MAX_SLICES = 8
TREND_MONTHS = 6


class ExpenseLike(Protocol):
    date: date
    amount: int
    category_id: str


def round_percent(value: Decimal) -> Decimal:
    """[BR-06] One decimal place, ROUND_HALF_UP (away from zero on .5)."""
    return value.quantize(_ONE_DECIMAL, rounding=ROUND_HALF_UP)


def change_rate(current: int, previous: int) -> Decimal | None:
    """[BR-06] Percentage change; None when the previous month is 0 yen."""
    if previous == 0:
        return None
    return round_percent(Decimal(current - previous) * 100 / Decimal(previous))


def ratio_percent(part: int, total: int) -> Decimal:
    """[BR-07-2] Share of `part` in `total` (total must be > 0)."""
    return round_percent(Decimal(part) * 100 / Decimal(total))


def month_total(expenses: Iterable[ExpenseLike], ym: str | None) -> int:
    if ym is None:
        return 0
    return sum(e.amount for e in expenses if month_of(e.date) == ym)


def totals_by_category(expenses: Iterable[ExpenseLike], ym: str | None) -> dict[str, int]:
    """[BR-07-1] Sum of amounts per category for the month."""
    totals: dict[str, int] = defaultdict(int)
    if ym is None:
        return {}
    for e in expenses:
        if month_of(e.date) == ym:
            totals[e.category_id] += e.amount
    return dict(totals)


@dataclass(frozen=True)
class CategoryLine:
    category_id: str
    total: int
    previous_total: int
    change_amount: int
    change_rate: Decimal | None
    budget: int | None
    usage_percent: int | None
    status: BudgetStatus


def summarize_categories(
    expenses: Iterable[ExpenseLike],
    ym: str,
    previous_ym: str | None,
    category_budgets: Mapping[str, int],
) -> list[CategoryLine]:
    """[BR-07-1] One line per category that has spending (this or last month) or a budget."""
    items = list(expenses)
    current = totals_by_category(items, ym)
    previous = totals_by_category(items, previous_ym)
    targets = set(current) | set(previous) | set(category_budgets)
    lines = []
    for category_id in targets:
        total = current.get(category_id, 0)
        prev = previous.get(category_id, 0)
        budget = category_budgets.get(category_id)
        lines.append(
            CategoryLine(
                category_id=category_id,
                total=total,
                previous_total=prev,
                change_amount=total - prev,
                change_rate=change_rate(total, prev),
                budget=budget,
                usage_percent=usage_percent(total, budget),
                status=judge(total, budget),
            )
        )
    lines.sort(key=lambda line: (-line.total, line.category_id))
    return lines


@dataclass(frozen=True)
class Alert:
    scope: Literal["overall", "category"]
    category_id: str | None
    status: BudgetStatus
    usage_percent: int
    budget: int
    spent: int


def build_alerts(
    overall_spent: int, overall_budget: int | None, lines: Iterable[CategoryLine]
) -> list[Alert]:
    """[BR-05] caution/over only; over first, then overall, then categories by usage desc."""
    alerts: list[Alert] = []
    overall_status = judge(overall_spent, overall_budget)
    if overall_status in (BudgetStatus.CAUTION, BudgetStatus.OVER) and overall_budget:
        alerts.append(
            Alert(
                scope="overall",
                category_id=None,
                status=overall_status,
                usage_percent=overall_spent * 100 // overall_budget,
                budget=overall_budget,
                spent=overall_spent,
            )
        )
    for line in lines:
        if line.status in (BudgetStatus.CAUTION, BudgetStatus.OVER) and line.budget:
            alerts.append(
                Alert(
                    scope="category",
                    category_id=line.category_id,
                    status=line.status,
                    usage_percent=line.usage_percent or 0,
                    budget=line.budget,
                    spent=line.total,
                )
            )

    def sort_key(alert: Alert) -> tuple[int, int, int, str]:
        status_rank = 0 if alert.status == BudgetStatus.OVER else 1
        scope_rank = 0 if alert.scope == "overall" else 1
        return (status_rank, scope_rank, -alert.usage_percent, alert.category_id or "")

    alerts.sort(key=sort_key)
    return alerts


@dataclass(frozen=True)
class BreakdownSlice:
    kind: Literal["category", "other"]
    category_id: str | None
    amount: int
    ratio_percent: Decimal


def breakdown(
    expenses: Iterable[ExpenseLike], ym: str, max_slices: int = MAX_SLICES
) -> tuple[int, list[BreakdownSlice]]:
    """[BR-07-2] Pie data: top (max_slices - 1) categories + "other" when there are more."""
    totals = totals_by_category(expenses, ym)
    total = sum(totals.values())
    ranked = sorted(
        ((cid, amount) for cid, amount in totals.items() if amount > 0),
        key=lambda pair: (-pair[1], pair[0]),
    )
    if total == 0:
        return 0, []
    if len(ranked) > max_slices:
        head, tail = ranked[: max_slices - 1], ranked[max_slices - 1 :]
        other_amount = sum(amount for _, amount in tail)
    else:
        head, other_amount = ranked, 0
    slices = [
        BreakdownSlice("category", cid, amount, ratio_percent(amount, total)) for cid, amount in head
    ]
    if other_amount > 0:
        slices.append(BreakdownSlice("other", None, other_amount, ratio_percent(other_amount, total)))
    return total, slices


def trend(
    expenses: Iterable[ExpenseLike], end_ym: str, months: int = TREND_MONTHS
) -> list[tuple[str, int]]:
    """[BR-07-3] Monthly totals for the last `months` months, oldest first, zeros included."""
    window = last_n_months(end_ym, months)
    totals = dict.fromkeys(window, 0)
    for e in expenses:
        ym = month_of(e.date)
        if ym in totals:
            totals[ym] += e.amount
    return [(ym, totals[ym]) for ym in window]
