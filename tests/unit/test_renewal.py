"""UT-RNW: subscription renewal rules (BR-03, BR-04-2)."""

from dataclasses import dataclass
from datetime import date, timedelta

import pytest

from app.domain.renewal import (
    advance,
    anchors_after_edit,
    anchors_for,
    can_renew,
    roll_forward,
    select_upcoming,
)

TODAY = date(2026, 10, 23)


# BR-03 table No.1..11
@pytest.mark.parametrize(
    ("cycle", "anchor_day", "anchor_month", "current", "expected"),
    [
        pytest.param("monthly", 15, None, date(2026, 10, 15), date(2026, 11, 15), id="UT-RNW-01-normal"),
        pytest.param("monthly", 31, None, date(2026, 12, 31), date(2027, 1, 31), id="UT-RNW-02-year-end"),
        pytest.param("monthly", 31, None, date(2027, 1, 31), date(2027, 2, 28), id="UT-RNW-03-31-to-feb"),
        pytest.param("monthly", 31, None, date(2027, 2, 28), date(2027, 3, 31), id="UT-RNW-04-back-to-31"),
        pytest.param("monthly", 31, None, date(2028, 1, 31), date(2028, 2, 29), id="UT-RNW-05-leap-feb"),
        pytest.param("monthly", 31, None, date(2026, 3, 31), date(2026, 4, 30), id="UT-RNW-06-31-to-30"),
        pytest.param("monthly", 30, None, date(2027, 1, 30), date(2027, 2, 28), id="UT-RNW-07-30-to-feb"),
        pytest.param("monthly", 29, None, date(2028, 1, 29), date(2028, 2, 29), id="UT-RNW-08-29-leap"),
        pytest.param("yearly", 29, 2, date(2028, 2, 29), date(2029, 2, 28), id="UT-RNW-09-leap-day-to-common"),
        pytest.param("yearly", 29, 2, date(2031, 2, 28), date(2032, 2, 29), id="UT-RNW-10-back-to-leap-day"),
        pytest.param("yearly", 23, 10, date(2026, 10, 23), date(2027, 10, 23), id="UT-RNW-11-yearly-normal"),
    ],
)
def test_advance(cycle, anchor_day, anchor_month, current, expected):
    assert advance(current, cycle, anchor_day, anchor_month) == expected


def test_ut_rnw_12_anchors_for():
    assert anchors_for(date(2026, 10, 31), "monthly") == (31, None)
    assert anchors_for(date(2028, 2, 29), "yearly") == (29, 2)


def _edit(old_date, old_cycle, old_day, old_month, new_date, new_cycle):
    return anchors_after_edit(
        old_date=old_date,
        old_cycle=old_cycle,
        old_anchor_day=old_day,
        old_anchor_month=old_month,
        new_date=new_date,
        new_cycle=new_cycle,
    )


def test_ut_rnw_13_edit_date_changed():
    assert _edit(date(2027, 2, 28), "monthly", 31, None, date(2026, 11, 15), "monthly") == (15, None)


def test_ut_rnw_14_edit_same_date_keeps_anchor_day():
    assert _edit(date(2027, 2, 28), "monthly", 31, None, date(2027, 2, 28), "monthly") == (31, None)


def test_ut_rnw_15_edit_monthly_to_yearly():
    assert _edit(date(2027, 2, 28), "monthly", 31, None, date(2027, 2, 28), "yearly") == (31, 2)


def test_ut_rnw_16_edit_yearly_to_monthly():
    assert _edit(date(2029, 2, 28), "yearly", 29, 2, date(2029, 2, 28), "monthly") == (29, None)


def test_ut_rnw_17_edit_yearly_unchanged():
    assert _edit(date(2029, 2, 28), "yearly", 29, 2, date(2029, 2, 28), "yearly") == (29, 2)


def test_ut_rnw_18_yearly_without_anchor_month():
    with pytest.raises(ValueError):
        advance(date(2026, 10, 23), "yearly", 23, None)


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        pytest.param(date(2026, 8, 31), date(2026, 10, 31), id="a-past"),
        pytest.param(date(2026, 10, 23), date(2026, 10, 23), id="b-today"),
        pytest.param(date(2026, 12, 1), date(2026, 12, 1), id="c-future"),
    ],
)
def test_ut_rnw_19_roll_forward(current, expected):
    assert roll_forward(current, TODAY, "monthly", current.day, None) == expected


def test_ut_rnw_20_roll_forward_many_cycles_month_end():
    assert roll_forward(date(2026, 1, 31), date(2026, 4, 15), "monthly", 31, None) == date(2026, 4, 30)


@pytest.mark.parametrize(
    ("offset", "expected"),
    [(7, True), (8, False), (0, True), (-30, True)],
)
def test_ut_rnw_21_can_renew(offset, expected):
    assert can_renew(TODAY + timedelta(days=offset), TODAY, 7) is expected


@dataclass
class Sub:
    id: str
    status: str
    next_renewal_date: date


def test_ut_rnw_22_upcoming_boundaries():
    subs = [Sub(f"sub-{d + 10:06d}", "active", TODAY + timedelta(days=d)) for d in (-3, 0, 7, 8)]
    result = select_upcoming(subs, TODAY, 7)
    assert [(e.days_until, e.is_overdue) for e in result] == [(-3, True), (0, False), (7, False)]


def test_ut_rnw_23_upcoming_excludes_paused():
    assert select_upcoming([Sub("sub-000001", "paused", TODAY)], TODAY, 7) == []


def test_ut_rnw_24_upcoming_order():
    subs = [
        Sub("sub-000003", "active", TODAY + timedelta(days=2)),
        Sub("sub-000002", "active", TODAY + timedelta(days=1)),
        Sub("sub-000001", "active", TODAY + timedelta(days=2)),
    ]
    assert [e.subscription_id for e in select_upcoming(subs, TODAY, 7)] == [
        "sub-000002",
        "sub-000001",
        "sub-000003",
    ]
