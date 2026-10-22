"""Subscription use cases. Design refs: API-10..18, BR-03, BR-04, DATA-04."""

from __future__ import annotations

from datetime import date

from app.clock import Clock
from app.config import UPCOMING_WINDOW_DAYS
from app.domain.period import is_date_in_range
from app.domain.renewal import (
    advance,
    anchors_after_edit,
    anchors_for,
    can_renew,
    roll_forward,
    select_upcoming,
)
from app.errors import ErrorCode, conflict, not_found
from app.repositories.json_store import JsonStore
from app.repositories.models import DataFile, StoredSubscription, next_id
from app.schemas.subscription import (
    SubscriptionIn,
    SubscriptionListOut,
    SubscriptionOut,
    UpcomingItem,
    UpcomingListOut,
)
from app.services.views import subscription_out


def _find(data: DataFile, subscription_id: str) -> StoredSubscription:
    sub = next((s for s in data.subscriptions if s.id == subscription_id), None)
    if sub is None:
        raise not_found(ErrorCode.SUBSCRIPTION_NOT_FOUND, subscription_id)
    return sub


def _ensure_storable(new_date: date) -> date:
    """Guard: a computed date past 2099-12-31 would break the data file constraints."""
    if not is_date_in_range(new_date):
        raise conflict(ErrorCode.SUBSCRIPTION_DATE_LIMIT, "Next renewal date exceeds 2099-12-31.")
    return new_date


class SubscriptionService:
    def __init__(self, store: JsonStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    def list(self) -> SubscriptionListOut:
        """[API-10] Active first, then by next renewal date and id."""
        subs = sorted(
            self._store.read().subscriptions,
            key=lambda s: (s.status != "active", s.next_renewal_date, s.id),
        )
        return SubscriptionListOut(items=[subscription_out(s) for s in subs])

    def get(self, subscription_id: str) -> SubscriptionOut:
        return subscription_out(_find(self._store.read(), subscription_id))

    def create(self, payload: SubscriptionIn) -> SubscriptionOut:
        """[API-11] Always created as active; anchors come from the entered date (BR-03)."""
        anchor_day, anchor_month = anchors_for(payload.next_renewal_date, payload.cycle)
        with self._store.transaction() as tx:
            sub = StoredSubscription(
                id=next_id(tx.data, "subscription"),
                name=payload.name,
                amount=payload.amount,
                cycle=payload.cycle,
                next_renewal_date=payload.next_renewal_date,
                anchor_day=anchor_day,
                anchor_month=anchor_month,
                status="active",
            )
            tx.data.subscriptions.append(sub)
        return subscription_out(sub)

    def update(self, subscription_id: str, payload: SubscriptionIn) -> SubscriptionOut:
        """[API-13] Status is kept; anchors follow the BR-03 edit table."""
        with self._store.transaction() as tx:
            sub = _find(tx.data, subscription_id)
            anchor_day, anchor_month = anchors_after_edit(
                old_date=sub.next_renewal_date,
                old_cycle=sub.cycle,
                old_anchor_day=sub.anchor_day,
                old_anchor_month=sub.anchor_month,
                new_date=payload.next_renewal_date,
                new_cycle=payload.cycle,
            )
            updated = sub.model_copy(
                update={
                    "name": payload.name,
                    "amount": payload.amount,
                    "cycle": payload.cycle,
                    "next_renewal_date": payload.next_renewal_date,
                    "anchor_day": anchor_day,
                    "anchor_month": anchor_month,
                }
            )
            tx.data.subscriptions[tx.data.subscriptions.index(sub)] = updated
        return subscription_out(updated)

    def delete(self, subscription_id: str) -> None:
        """[API-14] Allowed in any state."""
        with self._store.transaction() as tx:
            tx.data.subscriptions.remove(_find(tx.data, subscription_id))

    def pause(self, subscription_id: str) -> SubscriptionOut:
        """[API-15][DATA-04] active -> paused."""
        with self._store.transaction() as tx:
            sub = _find(tx.data, subscription_id)
            if sub.status != "active":
                raise conflict(ErrorCode.SUBSCRIPTION_STATE_CONFLICT, "Already paused.")
            sub.status = "paused"
        return subscription_out(sub)

    def resume(self, subscription_id: str) -> SubscriptionOut:
        """[API-16][BR-03] paused -> active, skipping cycles that passed while paused."""
        today = self._clock.today()
        with self._store.transaction() as tx:
            sub = _find(tx.data, subscription_id)
            if sub.status != "paused":
                raise conflict(ErrorCode.SUBSCRIPTION_STATE_CONFLICT, "Already active.")
            sub.next_renewal_date = _ensure_storable(
                roll_forward(sub.next_renewal_date, today, sub.cycle, sub.anchor_day, sub.anchor_month)
            )
            sub.status = "active"
        return subscription_out(sub)

    def renew(self, subscription_id: str) -> SubscriptionOut:
        """[API-17][BR-03] Advance one cycle; only for active ones within the window."""
        today = self._clock.today()
        with self._store.transaction() as tx:
            sub = _find(tx.data, subscription_id)
            if sub.status != "active":
                raise conflict(ErrorCode.SUBSCRIPTION_INACTIVE, "Subscription is paused.")
            if not can_renew(sub.next_renewal_date, today, UPCOMING_WINDOW_DAYS):
                raise conflict(
                    ErrorCode.SUBSCRIPTION_RENEW_TOO_EARLY,
                    "Renewal is allowed only within the notice window.",
                    {"days": UPCOMING_WINDOW_DAYS},
                )
            sub.next_renewal_date = _ensure_storable(
                advance(sub.next_renewal_date, sub.cycle, sub.anchor_day, sub.anchor_month)
            )
        return subscription_out(sub)

    def upcoming(self) -> UpcomingListOut:
        """[API-18][BR-04-2]"""
        today = self._clock.today()
        data = self._store.read()
        by_id = {s.id: s for s in data.subscriptions}
        items = []
        for entry in select_upcoming(data.subscriptions, today, UPCOMING_WINDOW_DAYS):
            sub = by_id[entry.subscription_id]
            items.append(
                UpcomingItem(
                    id=sub.id,
                    name=sub.name,
                    amount=sub.amount,
                    cycle=sub.cycle,
                    next_renewal_date=entry.next_renewal_date,
                    days_until=entry.days_until,
                    is_overdue=entry.is_overdue,
                )
            )
        return UpcomingListOut(today=today, window_days=UPCOMING_WINDOW_DAYS, items=items)
