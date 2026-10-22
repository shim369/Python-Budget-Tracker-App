"""Chart data schemas, ready to display without client-side aggregation.

Design refs: API-22, API-23, BR-07-2, BR-07-3.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.schemas.common import RatePercent


class BreakdownItem(BaseModel):
    kind: Literal["category", "other"]
    category_id: str | None
    key: str | None
    name: str | None
    amount: int
    ratio_percent: RatePercent


class CategoryBreakdownOut(BaseModel):
    month: str
    total: int
    items: list[BreakdownItem]


class TrendItem(BaseModel):
    month: str
    total: int


class MonthlyTrendOut(BaseModel):
    end_month: str
    items: list[TrendItem]
