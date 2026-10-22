"""IT-I18N, IT-CHT, IT-OFF, IT-ERR, IT-CRUD and IT-PERF."""

import json
import re
import time

import pytest

from app.config import PROJECT_ROOT
from app.dependencies import get_expense_service
from tests.integration.helpers import (
    FOOD,
    add_expense,
    add_subscription,
    assert_error,
    csv_rows,
    import_csv,
)

STATIC = PROJECT_ROOT / "static"


def flatten(node, prefix=""):
    out = {}
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else key
        out.update(flatten(value, path) if isinstance(value, dict) else {path: value})
    return out


# ---- IT-I18N -----------------------------------------------------------------


def test_it_i18n_01_responses_do_not_depend_on_language(client):
    bad = {"date": "2026-02-30", "amount": 0, "category_id": "x"}
    ja = client.post("/api/expenses", json=bad, headers={"Accept-Language": "ja"})
    en = client.post("/api/expenses", json=bad, headers={"Accept-Language": "en"})
    assert ja.status_code == en.status_code == 400
    assert ja.json() == en.json()
    assert not re.search(r"[぀-ヿ一-鿿]", ja.text)  # no Japanese text in the API


def test_it_i18n_02_codes_and_keys_are_translated(client):
    dicts = {lang: flatten(json.loads((STATIC / "i18n" / f"{lang}.json").read_text("utf-8"))) for lang in ("en", "ja")}
    keys = {c["key"] for c in client.get("/api/categories").json()["items"] if c["key"]} | {"category.others"}
    responses = [
        client.post("/api/expenses", json={}),
        client.post("/api/expenses", content="{", headers={"Content-Type": "application/json"}),
        client.delete(f"/api/categories/{FOOD}"),
        client.get("/api/expenses/exp-999999"),
        client.get("/api/nope"),
        import_csv(client, b""),
    ]
    codes = {r.json()["error"]["code"] for r in responses}
    field_codes = {d["code"] for r in responses for d in r.json()["error"]["details"] if d["field"]}
    for lang, entries in dicts.items():
        assert {f"errors.{c}" for c in codes} <= set(entries), lang
        assert {f"errors.field.{c}" for c in field_codes} <= set(entries), lang
        assert keys <= set(entries), lang


# ---- IT-CHT ------------------------------------------------------------------


def test_it_cht_01_no_data(client):
    breakdown = client.get("/api/charts/category-breakdown").json()
    assert (breakdown["total"], breakdown["items"]) == (0, [])
    trend = client.get("/api/charts/monthly-trend").json()
    assert [t["total"] for t in trend["items"]] == [0] * 6


def test_it_cht_02_single(client):
    add_expense(client, "2026-10-01", 500)
    items = client.get("/api/charts/category-breakdown").json()["items"]
    assert [(i["kind"], i["key"], i["ratio_percent"]) for i in items] == [("category", "category.food", "100.0")]


def test_it_cht_03_many_categories(client):
    user_ids = [client.post("/api/categories", json={"name": f"Hobby {i}"}).json()["id"] for i in range(2)]
    category_ids = [f"cat-{n:06d}" for n in range(1, 9)] + user_ids
    for rank, category_id in enumerate(category_ids):
        add_expense(client, "2026-10-01", (len(category_ids) - rank) * 1_000, category_id)
    items = client.get("/api/charts/category-breakdown").json()["items"]
    assert len(items) == 8
    # 10 categories: 10,000..4,000 are shown, the remaining three (3,000 + 2,000 + 1,000) are combined.
    assert items[-1] == {
        "kind": "other",
        "category_id": None,
        "key": "category.others",
        "name": None,
        "amount": 3_000 + 2_000 + 1_000,
        "ratio_percent": "10.9",  # 6,000 / 55,000
    }


def test_it_cht_04_extreme_amounts(client):
    add_expense(client, "2026-10-01", 1, FOOD)
    for day in (2, 3, 4):
        add_expense(client, f"2026-10-0{day}", 9_999_999, "cat-000003")
    breakdown = client.get("/api/charts/category-breakdown").json()
    assert breakdown["total"] == 29_999_998
    assert {i["key"]: i["ratio_percent"] for i in breakdown["items"]} == {
        "category.housing": "100.0",
        "category.food": "0.0",
    }
    assert client.get("/api/charts/monthly-trend").json()["items"][-1]["total"] == 29_999_998


# ---- IT-OFF ------------------------------------------------------------------


def _own_files():
    files = [STATIC / "index.html", *sorted((STATIC / "js").rglob("*.js")), STATIC / "css" / "custom.css"]
    return files + sorted((STATIC / "i18n").glob("*.json"))


def test_it_off_01_no_external_references():
    pattern = re.compile(r"""(?:src|href)\s*=\s*["'](?:https?:)?//|url\(\s*["']?(?:https?:)?//|import\s.*["']https?://""")
    offenders = [str(f) for f in _own_files() if pattern.search(f.read_text("utf-8"))]
    assert offenders == []
    vendor_css = (STATIC / "vendor" / "pico.min.css").read_text("utf-8")
    assert not re.search(r"@import|url\(\s*[\"']?https?://", vendor_css)


def test_it_off_02_all_local_assets_are_served(client):
    html = (STATIC / "index.html").read_text("utf-8")
    assets = set(re.findall(r"""(?:src|href)="(/static/[^"]+)\"""", html))
    for js in (STATIC / "js").rglob("*.js"):
        for target in re.findall(r"""from\s+['"](\.{1,2}/[^'"]+)['"]""", js.read_text("utf-8")):
            resolved = (js.parent / target).resolve().relative_to(STATIC.resolve())
            assets.add(f"/static/{resolved.as_posix()}")
    assets |= {"/static/i18n/en.json", "/static/i18n/ja.json", "/"}
    assert len(assets) >= 15
    failures = {path: client.get(path).status_code for path in assets}
    assert {p: s for p, s in failures.items() if s != 200} == {}


def test_it_off_03_ui_files_are_revalidated(client):
    """BUG-003 retest: page and static files must not be cached without revalidation."""
    for path in ["/", "/static/js/main.js", "/static/css/custom.css", "/static/i18n/ja.json"]:
        response = client.get(path)
        assert response.headers.get("cache-control") == "no-cache", path
        assert response.headers.get("etag") or path == "/", path
    etag = client.get("/static/css/custom.css").headers["etag"]
    assert client.get("/static/css/custom.css", headers={"If-None-Match": etag}).status_code == 304
    assert "cache-control" not in client.get("/api/status").headers


# ---- IT-ERR ------------------------------------------------------------------


def test_it_err_01_unknown_path_and_method(client):
    assert_error(client.get("/api/unknown"), 404, "NOT_FOUND")
    assert_error(client.patch("/api/expenses"), 405, "METHOD_NOT_ALLOWED")


def test_it_err_02_bad_requests(client):
    assert_error(
        client.post("/api/expenses", content='{"date": ', headers={"Content-Type": "application/json"}),
        400,
        "INVALID_JSON",
    )
    missing_body = assert_error(client.post("/api/expenses"), 400, "VALIDATION_ERROR")
    assert missing_body["details"][0]["code"] == "FIELD_REQUIRED"
    month = assert_error(client.get("/api/summary?month=2026-13"), 400, "VALIDATION_ERROR")
    assert month["details"] == [{"field": "month", "code": "INVALID_MONTH", "params": {}}]


def test_it_err_03_unexpected_exception(make_client):
    client = make_client(raise_server_exceptions=False)

    class Broken:
        def list(self, month):
            raise RuntimeError("secret internal detail")

    client.app.dependency_overrides[get_expense_service] = lambda: Broken()
    response = client.get("/api/expenses")
    error = assert_error(response, 500, "INTERNAL_ERROR")
    assert "secret" not in response.text and error["details"] == []


def test_it_err_04_no_422_anywhere(client):
    requests = [
        ("post", "/api/expenses", {"json": {"amount": "x"}}),
        ("put", "/api/expenses/exp-000001", {"json": {}}),
        ("post", "/api/subscriptions", {"json": {"cycle": 1}}),
        ("put", "/api/budgets", {"json": {"overall": -1}}),
        ("post", "/api/categories", {"json": {"name": ""}}),
        ("get", "/api/summary?month=x", {}),
        ("get", "/api/charts/category-breakdown?month=x", {}),
        ("get", "/api/charts/monthly-trend?month=1999-12", {}),
        ("get", "/api/expenses?month=2026-00", {}),
    ]
    for method, path, kwargs in requests:
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 400, (method, path, response.status_code)
        assert set(response.json()) == {"error"}


def test_it_err_05_openapi_matches_design(client):
    schema = client.get("/openapi.json").json()
    operations = [(m.upper(), p) for p, ops in schema["paths"].items() for m in ops]
    assert len(operations) == 24
    assert all("422" not in op["responses"] for ops in schema["paths"].values() for op in ops.values())
    assert "ErrorResponse" in schema["components"]["schemas"]
    assert "HTTPValidationError" not in schema["components"]["schemas"]
    assert ("POST", "/api/imports/expenses") in operations
    assert "text/csv" in schema["paths"]["/api/imports/expenses"]["post"]["requestBody"]["content"]


# ---- IT-CRUD -----------------------------------------------------------------


def test_it_crud_01_expense_lifecycle(client):
    created = add_expense(client, "2026-10-01", 1_200, FOOD, "Lunch")
    path = f"/api/expenses/{created['id']}"
    assert client.get(path).json() == created
    updated = client.put(path, json={"date": "2026-10-02", "amount": 1_500, "category_id": FOOD, "memo": ""})
    assert updated.status_code == 200 and updated.json()["amount"] == 1_500
    assert client.delete(path).status_code == 204
    assert_error(client.get(path), 404, "EXPENSE_NOT_FOUND")


def test_it_crud_02_subscription_lifecycle(client):
    a = add_subscription(client, "A", 100, "monthly", "2026-11-05")
    b = add_subscription(client, "B", 200, "monthly", "2026-11-01")
    client.post(f"/api/subscriptions/{b['id']}/pause")
    assert [s["id"] for s in client.get("/api/subscriptions").json()["items"]] == [a["id"], b["id"]]
    assert client.delete(f"/api/subscriptions/{a['id']}").status_code == 204
    assert_error(client.get(f"/api/subscriptions/{a['id']}"), 404, "SUBSCRIPTION_NOT_FOUND")


@pytest.mark.parametrize(
    ("method", "path", "kwargs", "code"),
    [
        ("put", "/api/expenses/exp-999999", {"json": {"date": "2026-10-01", "amount": 1, "category_id": FOOD}}, "EXPENSE_NOT_FOUND"),
        ("delete", "/api/expenses/exp-999999", {}, "EXPENSE_NOT_FOUND"),
        ("delete", "/api/subscriptions/sub-999999", {}, "SUBSCRIPTION_NOT_FOUND"),
        ("post", "/api/subscriptions/sub-999999/renew", {}, "SUBSCRIPTION_NOT_FOUND"),
        ("delete", "/api/categories/cat-999999", {}, "CATEGORY_NOT_FOUND"),
    ],
)
def test_it_crud_03_not_found(client, method, path, kwargs, code):
    assert_error(getattr(client, method)(path, **kwargs), 404, code)


# ---- IT-PERF -----------------------------------------------------------------


def test_it_perf_01_response_time_with_5000_expenses(client):
    assert import_csv(client, csv_rows(5_000).encode()).json()["imported_count"] == 5_000
    timings = {}
    for path in [
        "/api/summary",
        "/api/charts/category-breakdown",
        "/api/charts/monthly-trend",
        "/api/expenses?month=2026-10",
        "/api/subscriptions/upcoming",
    ]:
        started = time.perf_counter()
        assert client.get(path).status_code == 200
        timings[path] = (time.perf_counter() - started) * 1000
    print("IT-PERF-01 ms:", {k: round(v, 1) for k, v in timings.items()})
    assert max(timings.values()) < 500, timings
