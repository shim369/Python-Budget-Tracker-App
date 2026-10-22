"""UT-CLK: "today" is the JST calendar date (BR-02)."""

from datetime import UTC, date, datetime

import pytest

from app.clock import APP_TZ, FixedClock, SystemClock, get_clock


def clock_at(utc: datetime) -> SystemClock:
    return SystemClock(now_fn=lambda: utc)


def test_ut_clk_01_month_end_2359_jst():
    assert clock_at(datetime(2026, 10, 31, 14, 59, 59, tzinfo=UTC)).today() == date(2026, 10, 31)


def test_ut_clk_02_next_month_0000_jst():
    assert clock_at(datetime(2026, 10, 31, 15, 0, 0, tzinfo=UTC)).today() == date(2026, 11, 1)


def test_ut_clk_03_naive_datetime_rejected():
    with pytest.raises(ValueError):
        clock_at(datetime(2026, 10, 31, 15, 0, 0)).today()


def test_ut_clk_04_fixed_clock():
    clock = FixedClock(date(2026, 10, 23))
    assert clock.today() == date(2026, 10, 23)
    assert clock.now() == datetime(2026, 10, 23, tzinfo=APP_TZ)


def test_default_clock_is_system_clock():
    assert isinstance(get_clock(), SystemClock)
    assert isinstance(SystemClock().today(), date)
