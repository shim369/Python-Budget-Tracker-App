"""Subscription schemas. Design refs: API-10..18, BR-03, BR-04, DATA-04."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.common import Amount, AppDate, InputModel


class SubscriptionIn(InputModel):
    """[API-11][API-13] Status is changed only via pause/resume (DATA-04)."""

    name: Annotated[str, Field(min_length=1, max_length=50)]
    amount: Amount
    cycle: Literal["monthly", "yearly"]
    next_renewal_date: AppDate


class SubscriptionOut(BaseModel):
    id: str
    name: str
    amount: int
    cycle: Literal["monthly", "yearly"]
    next_renewal_date: date
    anchor_day: int
    anchor_month: int | None
    status: Literal["active", "paused"]
    monthly_equivalent: int = Field(description="BR-04-1: yearly amount // 12")


class SubscriptionListOut(BaseModel):
    items: list[SubscriptionOut]


class UpcomingItem(BaseModel):
    """[API-18] days_until is negative when overdue."""

    id: str
    name: str
    amount: int
    cycle: Literal["monthly", "yearly"]
    next_renewal_date: date
    days_until: int
    is_overdue: bool


class UpcomingListOut(BaseModel):
    today: date
    window_days: int
    items: list[UpcomingItem]
