"""Monthly summary and chart data. Design refs: API-21..23, BR-04..07."""

from __future__ import annotations

from app.clock import Clock
from app.domain import summary as rules
from app.domain.budget_rule import judge, usage_percent
from app.domain.categories import OTHERS_KEY
from app.domain.money import monthly_equivalent
from app.domain.period import month_of, next_month, previous_month
from app.repositories.json_store import JsonStore
from app.schemas.chart import BreakdownItem, CategoryBreakdownOut, MonthlyTrendOut, TrendItem
from app.schemas.summary import (
    AlertOut,
    BudgetStatusOut,
    CategorySummaryOut,
    MonthlySummaryOut,
    SubscriptionTotalsOut,
)
from app.services.views import categories_by_id, category_label


class SummaryService:
    def __init__(self, store: JsonStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    def _month(self, month: str | None) -> str:
        return month or month_of(self._clock.today())

    def summary(self, month: str | None) -> MonthlySummaryOut:
        """[API-21] Totals, change, budget judgement, subscriptions and alerts."""
        ym = self._month(month)
        prev_ym = previous_month(ym)
        data = self._store.read()
        cats = categories_by_id(data)

        total = rules.month_total(data.expenses, ym)
        previous_total = rules.month_total(data.expenses, prev_ym)
        overall = data.budgets.overall
        lines = rules.summarize_categories(data.expenses, ym, prev_ym, data.budgets.categories)

        categories = []
        for line in lines:
            key, name = category_label(cats.get(line.category_id))
            categories.append(
                CategorySummaryOut(
                    category_id=line.category_id,
                    key=key,
                    name=name,
                    total=line.total,
                    previous_total=line.previous_total,
                    change_amount=line.change_amount,
                    change_rate=line.change_rate,
                    budget=line.budget,
                    usage_percent=line.usage_percent,
                    status=line.status.value,
                )
            )

        alerts = []
        for alert in rules.build_alerts(total, overall, lines):
            key, name = category_label(cats.get(alert.category_id or ""))
            alerts.append(
                AlertOut(
                    scope=alert.scope,
                    category_id=alert.category_id,
                    key=key,
                    name=name,
                    status=alert.status.value,
                    usage_percent=alert.usage_percent,
                    budget=alert.budget,
                    spent=alert.spent,
                )
            )

        active = [s for s in data.subscriptions if s.status == "active"]
        return MonthlySummaryOut(
            month=ym,
            previous_month=prev_ym,
            next_month=next_month(ym),
            total=total,
            previous_total=previous_total,
            change_amount=total - previous_total,
            change_rate=rules.change_rate(total, previous_total),
            overall_budget=BudgetStatusOut(
                budget=overall,
                spent=total,
                usage_percent=usage_percent(total, overall),
                status=judge(total, overall).value,
            ),
            categories=categories,
            subscriptions=SubscriptionTotalsOut(
                monthly_total=sum(monthly_equivalent(s.amount, s.cycle) for s in active),
                active_count=len(active),
            ),
            alerts=alerts,
        )

    def breakdown(self, month: str | None) -> CategoryBreakdownOut:
        """[API-22][BR-07-2]"""
        ym = self._month(month)
        data = self._store.read()
        cats = categories_by_id(data)
        total, slices = rules.breakdown(data.expenses, ym)
        items = []
        for s in slices:
            if s.kind == "other":
                key, name = OTHERS_KEY, None
            else:
                key, name = category_label(cats.get(s.category_id or ""))
            items.append(
                BreakdownItem(
                    kind=s.kind,
                    category_id=s.category_id,
                    key=key,
                    name=name,
                    amount=s.amount,
                    ratio_percent=s.ratio_percent,
                )
            )
        return CategoryBreakdownOut(month=ym, total=total, items=items)

    def trend(self, month: str | None) -> MonthlyTrendOut:
        """[API-23][BR-07-3]"""
        ym = self._month(month)
        data = self._store.read()
        return MonthlyTrendOut(
            end_month=ym,
            items=[TrendItem(month=m, total=t) for m, t in rules.trend(data.expenses, ym)],
        )
