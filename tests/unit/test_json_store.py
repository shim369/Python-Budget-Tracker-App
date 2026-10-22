"""UT-STO: JSON store, data file model and id numbering (DATA-01..03, ERR-30, ERR-31)."""

import json
import os
from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import PROJECT_ROOT
from app.errors import AppError
from app.repositories.json_store import JsonStore
from app.repositories.models import DataFile, StoredExpense, StoredSubscription, next_id

FIXED_NOW = datetime(2026, 10, 23, 12, 34, 56)


def make_store(path: Path) -> JsonStore:
    return JsonStore(path, now_fn=lambda: FIXED_NOW)


def test_ut_sto_01_missing_file_creates_initial(data_file):
    store = make_store(data_file)
    store.initialize()
    data = DataFile.model_validate_json(data_file.read_bytes())
    assert len(data.categories) == 8
    assert store.recovery is None


def test_ut_sto_02_broken_json_is_moved_aside(data_file):
    data_file.write_text("{ broken", encoding="utf-8")
    store = make_store(data_file)
    store.initialize()
    backup = data_file.with_name("budget.json.corrupt-20261023123456")
    assert backup.read_text(encoding="utf-8") == "{ broken"
    assert store.recovery is not None and store.recovery.backup_file == backup.name
    assert len(store.read().categories) == 8


def test_ut_sto_03_integrity_violation_is_corruption(data_file):
    payload = json.loads(DataFile.initial().model_dump_json())
    payload["expenses"] = [
        {"id": "exp-000001", "date": "2026-10-01", "amount": 100, "category_id": "cat-999999", "memo": ""}
    ]
    payload["sequences"]["expense"] = 1
    data_file.write_text(json.dumps(payload), encoding="utf-8")
    store = make_store(data_file)
    store.initialize()
    assert store.recovery is not None
    assert store.read().expenses == []


def _initial_dict() -> dict:
    return json.loads(DataFile.initial().model_dump_json())


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda d: d["categories"].pop(0), id="fixed-category-missing"),
        pytest.param(lambda d: d["categories"].append(dict(d["categories"][0])), id="duplicate-id"),
        pytest.param(lambda d: d["sequences"].update(category=1), id="sequence-behind"),
        pytest.param(lambda d: d["budgets"]["categories"].update({"cat-999999": 100}), id="budget-unknown-category"),
        pytest.param(
            lambda d: d["subscriptions"].append(
                {
                    "id": "sub-000001",
                    "name": "x",
                    "amount": 1,
                    "cycle": "yearly",
                    "next_renewal_date": "2026-10-01",
                    "anchor_day": 1,
                    "anchor_month": None,
                    "status": "active",
                }
            )
            or d["sequences"].update(subscription=1),
            id="yearly-without-anchor-month",
        ),
        pytest.param(lambda d: d["categories"].append(
            {"id": "cat-000009", "code": None, "name": None, "is_fixed": False}
        ) or d["sequences"].update(category=9), id="user-category-without-name"),
        pytest.param(lambda d: d.update(schema_version=2), id="unknown-schema-version"),
    ],
)
def test_ut_sto_04_integrity_rules(mutate):
    payload = _initial_dict()
    mutate(payload)
    with pytest.raises(ValidationError):
        DataFile.model_validate_json(json.dumps(payload))


def test_ut_sto_05_backup_name_collision(data_file):
    data_file.with_name("budget.json.corrupt-20261023123456").write_text("old", encoding="utf-8")
    data_file.write_text("not json", encoding="utf-8")
    store = make_store(data_file)
    store.initialize()
    assert store.recovery.backup_file == "budget.json.corrupt-20261023123456-1"


def test_ut_sto_06_leftover_tmp_removed(data_file):
    tmp = data_file.with_name("budget.json.tmp")
    tmp.write_text("partial", encoding="utf-8")
    make_store(data_file).initialize()
    assert not tmp.exists()


def test_ut_sto_07_transaction_saves(store, data_file):
    with store.transaction() as tx:
        tx.data.budgets.overall = 1000
    assert DataFile.model_validate_json(data_file.read_bytes()).budgets.overall == 1000


def test_ut_sto_08_exception_or_discard_skips_save(store, data_file):
    before = data_file.read_bytes()
    with pytest.raises(RuntimeError), store.transaction() as tx:
        tx.data.budgets.overall = 1000
        raise RuntimeError("boom")
    with store.transaction() as tx:
        tx.data.budgets.overall = 2000
        tx.discard()
    assert data_file.read_bytes() == before


def test_ut_sto_09_write_failure_keeps_original(store, data_file, monkeypatch):
    before = data_file.read_bytes()

    def failing_replace(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", failing_replace)
    with pytest.raises(AppError) as exc_info, store.transaction() as tx:
        tx.data.budgets.overall = 1000
    assert (exc_info.value.code, exc_info.value.status) == ("STORAGE_WRITE_FAILED", 500)
    assert data_file.read_bytes() == before
    assert not data_file.with_name("budget.json.tmp").exists()


def test_ut_sto_10_next_id():
    data = DataFile.initial()
    assert next_id(data, "expense") == "exp-000001"
    assert next_id(data, "expense") == "exp-000002"
    assert next_id(data, "subscription") == "sub-000001"
    assert next_id(data, "category") == "cat-000009"


def test_ut_sto_11_backup_rename_failure_is_fatal(data_file, monkeypatch):
    data_file.write_text("not json", encoding="utf-8")

    def failing_replace(src, dst):
        raise PermissionError("read-only")

    monkeypatch.setattr(os, "replace", failing_replace)
    with pytest.raises(OSError):
        make_store(data_file).initialize()
    assert data_file.read_text(encoding="utf-8") == "not json"


def test_ut_sto_12_sample_data_is_valid():
    data = DataFile.model_validate_json((PROJECT_ROOT / "data" / "sample.json").read_bytes())
    assert len(data.expenses) > 0
    assert {s.status for s in data.subscriptions} == {"active", "paused"}


def test_stored_models_accept_valid_records():
    """Sanity check for the storage models used by the services."""
    StoredExpense(id="exp-000001", date=date(2026, 10, 1), amount=1, category_id="cat-000001")
    StoredSubscription(
        id="sub-000001",
        name="x",
        amount=1,
        cycle="yearly",
        next_renewal_date=date(2026, 10, 1),
        anchor_day=1,
        anchor_month=10,
        status="active",
    )
