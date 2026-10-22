"""Monthly summary schema. Design refs: API-21, BR-05, BR-06, BR-07-1."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.schemas.common import RatePercent

BudgetStatusLiteral = Literal["none", "ok", "caution", "over"]


class BudgetStatusOut(BaseModel):
    budget: int | None
    spent: int
    usage_percent: int | None
    status: BudgetStatusLiteral


class CategorySummaryOut(BaseModel):
    category_id: str
    key: str | None
    name: str | None
    total: int
    previous_total: int
    change_amount: int
    change_rate: RatePercent
    budget: int | None
    usage_percent: int | None
    status: BudgetStatusLiteral


class SubscriptionTotalsOut(BaseModel):
    monthly_total: int
    active_count: int


class AlertOut(BaseModel):
    scope: Literal["overall", "category"]
    category_id: str | None
    key: str | None
    name: str | None
    status: Literal["caution", "over"]
    usage_percent: int
    budget: int
    spent: int


class MonthlySummaryOut(BaseModel):
    month: str
    previous_month: str | None
    next_month: str | None
    total: int
    previous_total: int
    change_amount: int
    change_rate: RatePercent
    overall_budget: BudgetStatusOut
    categories: list[CategorySummaryOut]
    subscriptions: SubscriptionTotalsOut
    alerts: list[AlertOut]
