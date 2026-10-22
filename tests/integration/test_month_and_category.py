"""IT-MON (month boundaries) and IT-CAT (category deletion integrity)."""

from datetime import UTC, datetime

from app.clock import APP_TZ, SystemClock
from tests.integration.helpers import FOOD, HOUSING, add_expense, assert_error, set_budgets


def clock_at_jst(*args) -> SystemClock:
    moment = datetime(*args, tzinfo=APP_TZ)
    return SystemClock(now_fn=lambda: moment)


def register_today(client, amount: int) -> str:
    """What the UI does: take today from /api/status as the default date and register."""
    today = client.get("/api/status").json()["today"]
    add_expense(client, today, amount)
    return today


def test_it_mon_01_02_2359_and_0000(client, movable_clock):
    movable_clock.set(clock_at_jst(2026, 10, 31, 23, 59, 59))
    assert register_today(client, 1_000) == "2026-10-31"
    october = client.get("/api/summary").json()
    assert (october["month"], october["total"]) == ("2026-10", 1_000)

    movable_clock.set(clock_at_jst(2026, 11, 1, 0, 0, 0))
    assert register_today(client, 2_000) == "2026-11-01"
    november = client.get("/api/summary").json()
    assert (november["month"], november["total"], november["previous_total"]) == ("2026-11", 2_000, 1_000)
    assert client.get("/api/summary?month=2026-10").json()["total"] == 1_000


def test_it_mon_03_utc_server_time(client, movable_clock):
    utc_moment = datetime(2026, 10, 31, 15, 0, 0, tzinfo=UTC)
    movable_clock.set(SystemClock(now_fn=lambda: utc_moment))
    status = client.get("/api/status").json()
    assert (status["today"], status["current_month"], status["timezone"]) == ("2026-11-01", "2026-11", "Asia/Tokyo")


def test_it_mon_04_year_boundary(client):
    add_expense(client, "2026-12-31", 10_000)
    add_expense(client, "2027-01-01", 12_500)
    summary = client.get("/api/summary?month=2027-01").json()
    assert (summary["previous_month"], summary["next_month"]) == ("2026-12", "2027-02")
    assert (summary["total"], summary["previous_total"], summary["change_rate"]) == (12_500, 10_000, "25.0")
    trend = client.get("/api/charts/monthly-trend?month=2027-01").json()["items"]
    assert [t["month"] for t in trend] == ["2026-08", "2026-09", "2026-10", "2026-11", "2026-12", "2027-01"]
    assert [t["total"] for t in trend][-2:] == [10_000, 12_500]


def test_it_cat_01_02_in_use_then_deleted(client):
    pets = client.post("/api/categories", json={"name": "Pets"}).json()
    a = add_expense(client, "2026-10-01", 100, pets["id"])
    b = add_expense(client, "2026-10-02", 200, pets["id"])
    set_budgets(client, None, {pets["id"]: 3_000, FOOD: 1_000})

    error = assert_error(client.delete(f"/api/categories/{pets['id']}"), 409, "CATEGORY_IN_USE")
    assert error["details"][0]["params"] == {"count": 2}
    assert client.get("/api/expenses?month=2026-10").json()["count"] == 2

    for expense in (a, b):
        payload = {k: expense[k] for k in ("date", "amount", "memo")} | {"category_id": HOUSING}
        assert client.put(f"/api/expenses/{expense['id']}", json=payload).status_code == 200
    assert client.delete(f"/api/categories/{pets['id']}").status_code == 204
    assert pets["id"] not in {c["id"] for c in client.get("/api/categories").json()["items"]}
    assert client.get("/api/budgets").json()["categories"] == [{"category_id": FOOD, "amount": 1_000}]


def test_it_cat_03_deleted_category_cannot_be_used(client):
    pets = client.post("/api/categories", json={"name": "Pets"}).json()
    assert client.delete(f"/api/categories/{pets['id']}").status_code == 204
    error = assert_error(
        client.post("/api/expenses", json={"date": "2026-10-01", "amount": 1, "category_id": pets["id"]}),
        400,
        "VALIDATION_ERROR",
    )
    assert error["details"][0]["code"] == "UNKNOWN_CATEGORY"
    response = client.put("/api/budgets", json={"overall": None, "categories": [{"category_id": pets["id"], "amount": 1}]})
    assert assert_error(response, 400, "VALIDATION_ERROR")["details"][0]["code"] == "UNKNOWN_CATEGORY"


def test_it_cat_04_fixed_category_rules(client):
    assert_error(client.delete(f"/api/categories/{FOOD}"), 409, "CATEGORY_FIXED")
    assert_error(client.post("/api/categories", json={"name": "食費"}), 409, "CATEGORY_NAME_DUPLICATED")
    assert_error(client.delete("/api/categories/cat-999999"), 404, "CATEGORY_NOT_FOUND")
