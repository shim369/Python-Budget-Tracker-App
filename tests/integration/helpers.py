"""Small helpers shared by the integration tests."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

FOOD = "cat-000001"
DAILY = "cat-000002"
HOUSING = "cat-000003"
CSV_HEADERS = {"Content-Type": "text/csv"}


def add_expense(client: TestClient, d: str, amount: int, category_id: str = FOOD, memo: str = "") -> dict:
    response = client.post(
        "/api/expenses", json={"date": d, "amount": amount, "category_id": category_id, "memo": memo}
    )
    assert response.status_code == 201, response.text
    return response.json()


def add_subscription(client: TestClient, name: str, amount: int, cycle: str, next_date: str) -> dict:
    response = client.post(
        "/api/subscriptions",
        json={"name": name, "amount": amount, "cycle": cycle, "next_renewal_date": next_date},
    )
    assert response.status_code == 201, response.text
    return response.json()


def set_budgets(client: TestClient, overall: int | None, categories: dict[str, int | None]) -> dict:
    payload = {
        "overall": overall,
        "categories": [{"category_id": cid, "amount": amount} for cid, amount in categories.items()],
    }
    response = client.put("/api/budgets", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def import_csv(client: TestClient, raw: bytes, headers: dict[str, str] | None = None):
    return client.post("/api/imports/expenses", content=raw, headers=headers or CSV_HEADERS)


def csv_rows(n: int, start_amount: int = 1) -> str:
    """n distinct valid rows (no duplicates)."""
    return "date,amount,category,memo\n" + "".join(
        f"2026-10-01,{start_amount + i},food,row{i}\n" for i in range(n)
    )


def assert_error(response, status: int, code: str) -> dict[str, Any]:
    """[ERR-01] Status, unified shape and code."""
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["details"], list)
    return body["error"]
