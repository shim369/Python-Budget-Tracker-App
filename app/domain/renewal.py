"""Subscription renewal date rules. Pure functions only.

Design refs: BR-03 (next renewal date, anchors, renew/resume), BR-04-2 (upcoming list).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Protocol

from app.domain.money import Cycle
from app.domain.period import last_day, shift_month


def anchors_for(d: date, cycle: Cycle) -> tuple[int, int | None]:
    """[BR-03] Anchor (day, month) taken from a user-entered renewal date."""
    return d.day, (d.month if cycle == "yearly" else None)


def anchors_after_edit(
    *,
    old_date: date,
    old_cycle: Cycle,
    old_anchor_day: int,
    old_anchor_month: int | None,
    new_date: date,
    new_cycle: Cycle,
) -> tuple[int, int | None]:
    """[BR-03] Anchors after an edit.

    - Date changed: reset anchors from the new date.
    - Date unchanged: keep anchor_day so that e.g. "31st" survives an edit
      made while the date is Feb 28; adjust anchor_month only for cycle changes.
    """
    if new_date != old_date:
        return anchors_for(new_date, new_cycle)
    if new_cycle == "monthly":
        return old_anchor_day, None
    if old_cycle != "yearly" or old_anchor_month is None:
        return old_anchor_day, new_date.month
    return old_anchor_day, old_anchor_month


def advance(current: date, cycle: Cycle, anchor_day: int, anchor_month: int | None) -> date:
    """[BR-03] Next renewal date, one cycle after `current`.

    The day is clamped to the month end (31 -> 30 / 28 / 29) and restored
    from `anchor_day` in later months, so dates never drift.
    """
    if cycle == "monthly":
        year, month = shift_month(current.year, current.month, 1)
    else:
        if anchor_month is None:
            raise ValueError("yearly subscription requires anchor_month")
        year, month = current.year + 1, anchor_month
    return date(year, month, min(anchor_day, last_day(year, month)))


def roll_forward(
    current: date, today: date, cycle: Cycle, anchor_day: int, anchor_month: int | None
) -> date:
    """[BR-03] On resume, skip cycles that passed while paused (today stays as is)."""
    result = current
    while result < today:
        result = advance(result, cycle, anchor_day, anchor_month)
    return result


def can_renew(next_renewal_date: date, today: date, window_days: int) -> bool:
    """[BR-03] "Renewed" is allowed within the notice window or when overdue."""
    return next_renewal_date <= today + timedelta(days=window_days)


class RenewalTarget(Protocol):
    id: str
    status: str
    next_renewal_date: date


@dataclass(frozen=True)
class UpcomingEntry:
    subscription_id: str
    next_renewal_date: date
    days_until: int
    is_overdue: bool


def select_upcoming(
    subscriptions: Iterable[RenewalTarget], today: date, window_days: int
) -> list[UpcomingEntry]:
    """[BR-04-2] Active subscriptions due within the window, including overdue ones."""
    limit = today + timedelta(days=window_days)
    entries = [
        UpcomingEntry(
            subscription_id=sub.id,
            next_renewal_date=sub.next_renewal_date,
            days_until=(sub.next_renewal_date - today).days,
            is_overdue=sub.next_renewal_date < today,
        )
        for sub in subscriptions
        if sub.status == "active" and sub.next_renewal_date <= limit
    ]
    entries.sort(key=lambda e: (e.next_renewal_date, e.subscription_id))
    return entries
