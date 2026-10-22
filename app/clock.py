"""Injectable clock so that "today" can be fixed in tests.

Design refs: BR-02 (today is the JST calendar date), MOD-20 (dependency injection).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from app.config import TIMEZONE

APP_TZ = ZoneInfo(TIMEZONE)


class Clock(Protocol):
    """Source of the current date and time (JST)."""

    def today(self) -> date: ...

    def now(self) -> datetime: ...


class SystemClock:
    """[BR-02] Real clock. `now_fn` lets tests reproduce 23:59 / 00:00 boundaries."""

    def __init__(self, now_fn: Callable[[], datetime] | None = None) -> None:
        self._now_fn = now_fn or (lambda: datetime.now(UTC))

    def now(self) -> datetime:
        current = self._now_fn()
        if current.tzinfo is None:
            raise ValueError("now_fn must return an aware datetime")
        return current.astimezone(APP_TZ)

    def today(self) -> date:
        return self.now().date()


class FixedClock:
    """Clock that always returns the given date (midnight JST)."""

    def __init__(self, fixed: date) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return datetime(self._fixed.year, self._fixed.month, self._fixed.day, tzinfo=APP_TZ)

    def today(self) -> date:
        return self._fixed


def get_clock() -> Clock:
    """FastAPI dependency. Overridden in tests via app.dependency_overrides."""
    return SystemClock()
