"""IT-FLOW (expense -> summary -> budget alerts) and IT-SUB (subscription renewal)."""

from datetime import date

from tests.integration.helpers import DAILY, FOOD, add_expense, add_subscription, set_budgets


def test_it_flow_01_to_04_expense_summary_budget(client):
    set_budgets(client, 10_000, {FOOD: 5_000})

    # IT-FLOW-01: 3,900 -> 78% ok
    add_expense(client, "2026-10-01", 3_900)
    s = client.get("/api/summary").json()
    food = next(c for c in s["categories"] if c["category_id"] == FOOD)
    assert (food["usage_percent"], food["status"]) == (78, "ok")
    assert (s["overall_budget"]["usage_percent"], s["overall_budget"]["status"]) == (39, "ok")
    assert s["alerts"] == []

    # IT-FLOW-02: 4,000 -> 80% caution
    add_expense(client, "2026-10-02", 100)
    s = client.get("/api/summary").json()
    assert [(a["scope"], a["status"], a["usage_percent"]) for a in s["alerts"]] == [("category", "caution", 80)]
    assert s["alerts"][0]["key"] == "category.food"

    # IT-FLOW-03: exactly 100% stays caution
    add_expense(client, "2026-10-03", 1_000)
    s = client.get("/api/summary").json()
    assert [(a["status"], a["usage_percent"], a["spent"]) for a in s["alerts"]] == [("caution", 100, 5_000)]

    # IT-FLOW-04: 5,001 -> over; overall 9,001 / 10,000 -> caution; order over -> overall
    add_expense(client, "2026-10-04", 1)
    add_expense(client, "2026-10-05", 4_000, DAILY)
    s = client.get("/api/summary").json()
    assert [(a["scope"], a["status"]) for a in s["alerts"]] == [("category", "over"), ("overall", "caution")]
    assert s["overall_budget"] == {"budget": 10_000, "spent": 9_001, "usage_percent": 90, "status": "caution"}
    assert (s["total"], s["previous_total"], s["change_amount"], s["change_rate"]) == (9_001, 0, 9_001, None)


def test_it_sub_01_02_upcoming_window(client):
    sub = add_subscription(client, "Video", 1_490, "monthly", "2026-10-31")
    assert client.get("/api/subscriptions/upcoming").json()["items"] == []  # 8 days ahead

    updated = client.put(
        f"/api/subscriptions/{sub['id']}",
        json={"name": "Video", "amount": 1_490, "cycle": "monthly", "next_renewal_date": "2026-10-30"},
    ).json()
    assert updated["anchor_day"] == 30
    items = client.get("/api/subscriptions/upcoming").json()["items"]
    assert [(i["id"], i["days_until"], i["is_overdue"]) for i in items] == [(sub["id"], 7, False)]


def test_it_sub_03_04_month_end_renewal(client, movable_clock):
    movable_clock.set(date(2027, 1, 30))
    sub = add_subscription(client, "Gym", 7_700, "monthly", "2027-01-31")

    renewed = client.post(f"/api/subscriptions/{sub['id']}/renew").json()
    assert (renewed["next_renewal_date"], renewed["anchor_day"]) == ("2027-02-28", 31)
    assert client.get("/api/summary").json()["subscriptions"] == {"monthly_total": 7_700, "active_count": 1}

    movable_clock.set(date(2027, 2, 25))
    renewed = client.post(f"/api/subscriptions/{sub['id']}/renew").json()
    assert renewed["next_renewal_date"] == "2027-03-31"
    assert client.get(f"/api/subscriptions/{sub['id']}").json()["next_renewal_date"] == "2027-03-31"


def test_it_sub_05_yearly_leap_day(client, movable_clock):
    movable_clock.set(date(2028, 2, 25))
    sub = add_subscription(client, "Cloud", 13_000, "yearly", "2028-02-29")
    assert sub["monthly_equivalent"] == 1_083
    renewed = client.post(f"/api/subscriptions/{sub['id']}/renew").json()
    assert (renewed["next_renewal_date"], renewed["anchor_month"]) == ("2029-02-28", 2)


def test_it_sub_06_pause_and_resume(client, movable_clock):
    sub = add_subscription(client, "Music", 1_080, "monthly", "2026-10-25")
    assert client.post(f"/api/subscriptions/{sub['id']}/pause").json()["status"] == "paused"
    assert client.get("/api/subscriptions/upcoming").json()["items"] == []
    assert client.get("/api/summary").json()["subscriptions"] == {"monthly_total": 0, "active_count": 0}

    movable_clock.set(date(2026, 12, 28))
    resumed = client.post(f"/api/subscriptions/{sub['id']}/resume").json()
    assert (resumed["status"], resumed["next_renewal_date"]) == ("active", "2027-01-25")
    assert [i["days_until"] for i in client.get("/api/subscriptions/upcoming").json()["items"]] == []
