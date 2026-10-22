"""IT-REC (corrupted / missing data file) and IT-CON (concurrent writes)."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor

from app.repositories.json_store import JsonStore
from app.repositories.models import DataFile, StoredExpense
from tests.integration.helpers import DAILY, FOOD, add_expense


def backups(data_file):
    return sorted(data_file.parent.glob("budget.json.corrupt-*"))


def test_it_rec_01_missing_file(make_client, data_file):
    assert not data_file.exists()
    client = make_client()
    assert data_file.exists()
    status = client.get("/api/status").json()
    assert (status["data_recovered"], status["backup_file"]) == (False, None)
    assert len(client.get("/api/categories").json()["items"]) == 8


def test_it_rec_02_broken_json(make_client, data_file):
    data_file.write_text('{"schema_version": 1, "expenses": [', encoding="utf-8")
    client = make_client()
    status = client.get("/api/status").json()
    assert status["data_recovered"] is True
    [backup] = backups(data_file)
    assert status["backup_file"] == backup.name
    assert backup.read_text(encoding="utf-8") == '{"schema_version": 1, "expenses": ['
    add_expense(client, "2026-10-01", 100)
    assert client.get("/api/expenses?month=2026-10").json()["count"] == 1


def test_it_rec_03_integrity_violation(make_client, data_file):
    payload = json.loads(DataFile.initial().model_dump_json())
    payload["budgets"]["categories"] = {"cat-999999": 100}
    data_file.write_text(json.dumps(payload), encoding="utf-8")
    client = make_client()
    assert client.get("/api/status").json()["data_recovered"] is True
    assert len(backups(data_file)) == 1


def test_it_rec_04_leftover_tmp(make_client, data_file):
    data = DataFile.initial()
    data.budgets.overall = 1234
    data_file.write_text(data.model_dump_json(), encoding="utf-8")
    tmp = data_file.with_name("budget.json.tmp")
    tmp.write_text("{ half written", encoding="utf-8")
    client = make_client()
    assert not tmp.exists()
    assert client.get("/api/budgets").json()["overall"] == 1234
    assert client.get("/api/status").json()["data_recovered"] is False


def test_it_rec_05_corrupted_while_running(client, data_file):
    add_expense(client, "2026-10-01", 100)
    data_file.write_text("garbage", encoding="utf-8")
    response = client.get("/api/expenses?month=2026-10")
    assert (response.status_code, response.json()["count"]) == (200, 0)
    assert client.get("/api/status").json()["data_recovered"] is True


def test_it_con_01_parallel_posts(client, data_file):
    def post(i: int) -> int:
        response = client.post(
            "/api/expenses", json={"date": "2026-10-01", "amount": i + 1, "category_id": FOOD, "memo": f"m{i}"}
        )
        return response.status_code

    with ThreadPoolExecutor(max_workers=16) as pool:
        statuses = list(pool.map(post, range(50)))
    assert statuses == [201] * 50
    data = DataFile.model_validate_json(data_file.read_bytes())
    assert len(data.expenses) == 50
    assert len({e.id for e in data.expenses}) == 50
    assert sorted(e.amount for e in data.expenses) == list(range(1, 51))


def test_it_con_02_mixed_operations(client, data_file):
    def worker(i: int) -> None:
        kind = i % 3
        if kind == 0:
            assert client.post(
                "/api/expenses", json={"date": "2026-10-02", "amount": 10, "category_id": DAILY}
            ).status_code == 201
        elif kind == 1:
            assert client.post("/api/categories", json={"name": f"User {i}"}).status_code == 201
        else:
            assert client.get("/api/summary").status_code == 200

    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(worker, range(60)))
    data = DataFile.model_validate_json(data_file.read_bytes())
    assert len(data.expenses) == 20
    assert len([c for c in data.categories if not c.is_fixed]) == 20
    assert data.sequences.category == 8 + 20


def test_it_con_03_store_threads_without_http(data_file):
    store = JsonStore(data_file)
    store.initialize()
    barrier = threading.Barrier(8)

    def worker() -> None:
        barrier.wait()
        for _ in range(100):
            with store.transaction() as tx:
                n = tx.data.sequences.expense + 1
                tx.data.sequences.expense = n
                tx.data.expenses.append(
                    StoredExpense(id=f"exp-{n:06d}", date="2026-10-01", amount=1, category_id=FOOD)
                )

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    data = store.read()
    assert data.sequences.expense == 800
    assert len(data.expenses) == 800
