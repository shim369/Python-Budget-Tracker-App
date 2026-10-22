"""UT-SVC: service layer on a temporary store with "today" fixed to 2026-10-23."""

from datetime import date

import pytest

from app.config import CSV_MAX_ROWS
from app.errors import AppError
from app.repositories.json_store import JsonStore
from app.repositories.models import StoredExpense, StoredSubscription
from app.schemas.budget import BudgetsIn
from app.schemas.category import CategoryIn
from app.schemas.expense import ExpenseIn
from app.schemas.subscription import SubscriptionIn
from app.services.budget_service import BudgetService
from app.services.category_service import CategoryService
from app.services.expense_service import ExpenseService
from app.services.import_service import ImportService
from app.services.subscription_service import SubscriptionService
from app.services.summary_service import SummaryService

HEADER = "date,amount,category,memo\n"


def add_expense(store: JsonStore, d: date, amount: int, category_id: str = "cat-000001") -> None:
    with store.transaction() as tx:
        n = tx.data.sequences.expense + 1
        tx.data.sequences.expense = n
        tx.data.expenses.append(
            StoredExpense(id=f"exp-{n:06d}", date=d, amount=amount, category_id=category_id, memo="")
        )


def add_subscription(store: JsonStore, next_date: date, status: str = "active", anchor_day: int | None = None) -> str:
    with store.transaction() as tx:
        n = tx.data.sequences.subscription + 1
        tx.data.sequences.subscription = n
        sub_id = f"sub-{n:06d}"
        tx.data.subscriptions.append(
            StoredSubscription(
                id=sub_id,
                name="Video",
                amount=990,
                cycle="monthly",
                next_renewal_date=next_date,
                anchor_day=anchor_day or next_date.day,
                anchor_month=None,
                status=status,
            )
        )
    return sub_id


def error_of(call) -> AppError:
    with pytest.raises(AppError) as exc_info:
        call()
    return exc_info.value


# ---- categories -------------------------------------------------------------


def test_ut_svc_01_delete_category_removes_its_budget(store):
    categories = CategoryService(store)
    pets = categories.create(CategoryIn(name="Pets"))
    BudgetService(store).replace(
        BudgetsIn.model_validate({"overall": None, "categories": [{"category_id": pets.id, "amount": 5000}]})
    )
    categories.delete(pets.id)
    data = store.read()
    assert pets.id not in {c.id for c in data.categories}
    assert pets.id not in data.budgets.categories


def test_ut_svc_02_delete_category_errors(store):
    categories = CategoryService(store)
    pets = categories.create(CategoryIn(name="Pets"))
    add_expense(store, date(2026, 10, 1), 100, pets.id)
    add_expense(store, date(2026, 10, 2), 200, pets.id)

    assert error_of(lambda: categories.delete("cat-000001")).code == "CATEGORY_FIXED"
    in_use = error_of(lambda: categories.delete(pets.id))
    assert (in_use.code, in_use.status, in_use.details[0].params) == ("CATEGORY_IN_USE", 409, {"count": 2})
    assert error_of(lambda: categories.delete("cat-999999")).code == "CATEGORY_NOT_FOUND"
    assert categories.list().items[-1].in_use is True


# ---- expenses ----------------------------------------------------------------


def test_ut_svc_03_unknown_category_is_validation_error(store, clock, data_file):
    before = data_file.read_bytes()
    payload = ExpenseIn.model_validate({"date": "2026-10-01", "amount": 100, "category_id": "cat-999999"})
    err = error_of(lambda: ExpenseService(store, clock).create(payload))
    assert (err.code, err.status) == ("VALIDATION_ERROR", 400)
    assert (err.details[0].field, err.details[0].code) == ("category_id", "UNKNOWN_CATEGORY")
    assert data_file.read_bytes() == before


def test_ut_svc_04_list_defaults_to_current_month_and_sorts(store, clock):
    add_expense(store, date(2026, 10, 1), 1)  # exp-000001
    add_expense(store, date(2026, 10, 5), 2)  # exp-000002
    add_expense(store, date(2026, 10, 1), 3)  # exp-000003
    add_expense(store, date(2026, 9, 30), 4)
    result = ExpenseService(store, clock).list(None)
    assert result.month == "2026-10"
    assert [e.id for e in result.items] == ["exp-000002", "exp-000003", "exp-000001"]
    assert (result.total, result.count) == (6, 3)


# ---- subscriptions -------------------------------------------------------------


def test_ut_svc_05_edit_keeps_anchor_day(store, clock):
    service = SubscriptionService(store, clock)
    created = service.create(
        SubscriptionIn(name="Gym", amount=7700, cycle="monthly", next_renewal_date=date(2027, 1, 31))
    )
    with store.transaction() as tx:  # simulate one renewal: 1/31 -> 2/28
        tx.data.subscriptions[0].next_renewal_date = date(2027, 2, 28)
    updated = service.update(
        created.id, SubscriptionIn(name="Gym Plus", amount=8800, cycle="monthly", next_renewal_date=date(2027, 2, 28))
    )
    assert (updated.anchor_day, updated.name) == (31, "Gym Plus")


def test_ut_svc_06_renew_rejections(store, clock):
    service = SubscriptionService(store, clock)
    far = add_subscription(store, date(2026, 10, 31))  # 8 days ahead
    paused = add_subscription(store, date(2026, 10, 23), status="paused")
    assert error_of(lambda: service.renew(far)).code == "SUBSCRIPTION_RENEW_TOO_EARLY"
    assert error_of(lambda: service.renew(paused)).code == "SUBSCRIPTION_INACTIVE"


def test_ut_svc_07_date_limit(store, data_file):
    from app.clock import FixedClock

    late = FixedClock(date(2099, 12, 25))
    service = SubscriptionService(store, late)
    active = add_subscription(store, date(2099, 12, 31))
    paused = add_subscription(store, date(2099, 11, 30), status="paused")
    before = data_file.read_bytes()
    assert error_of(lambda: service.renew(active)).code == "SUBSCRIPTION_DATE_LIMIT"
    with store.transaction() as tx:  # make resume roll past 2099-12-31
        tx.data.subscriptions[1].next_renewal_date = date(2099, 12, 1)
    late_resume = SubscriptionService(store, FixedClock(date(2099, 12, 31)))
    assert error_of(lambda: late_resume.resume(paused)).code == "SUBSCRIPTION_DATE_LIMIT"
    assert store.read().subscriptions[0].next_renewal_date == date(2099, 12, 31)
    assert before  # file existed before the failed operations


def test_ut_svc_08_state_conflicts(store, clock):
    service = SubscriptionService(store, clock)
    active = add_subscription(store, date(2026, 10, 25))
    paused = add_subscription(store, date(2026, 10, 25), status="paused")
    assert error_of(lambda: service.resume(active)).code == "SUBSCRIPTION_STATE_CONFLICT"
    assert error_of(lambda: service.pause(paused)).code == "SUBSCRIPTION_STATE_CONFLICT"
    assert error_of(lambda: service.get("sub-999999")).code == "SUBSCRIPTION_NOT_FOUND"


# ---- budgets ---------------------------------------------------------------------


def test_ut_svc_09_budget_normalize_and_errors(store):
    service = BudgetService(store)
    result = service.replace(
        BudgetsIn.model_validate(
            {
                "overall": 0,
                "categories": [
                    {"category_id": "cat-000001", "amount": 40000},
                    {"category_id": "cat-000002", "amount": 0},
                    {"category_id": "cat-000003", "amount": None},
                ],
            }
        )
    )
    assert result.overall is None
    assert [(c.category_id, c.amount) for c in result.categories] == [("cat-000001", 40000)]

    err = error_of(
        lambda: service.replace(
            BudgetsIn.model_validate(
                {
                    "overall": 1,
                    "categories": [
                        {"category_id": "cat-000001", "amount": 1},
                        {"category_id": "cat-000001", "amount": 2},
                        {"category_id": "cat-999999", "amount": 3},
                    ],
                }
            )
        )
    )
    assert [(d.field, d.code) for d in err.details] == [
        ("categories.1.category_id", "DUPLICATED_CATEGORY"),
        ("categories.2.category_id", "UNKNOWN_CATEGORY"),
    ]


# ---- CSV import --------------------------------------------------------------------


def test_ut_svc_10_all_invalid_rows_leave_file_untouched(store, data_file):
    before = data_file.read_bytes()
    report = ImportService(store).import_csv((HEADER + "bad,1,food,\n2026-10-01,0,food,\n").encode())
    assert (report.imported_count, report.error_count) == (0, 2)
    assert data_file.read_bytes() == before


@pytest.mark.parametrize(
    "raw",
    [pytest.param(b"", id="zero-bytes"), pytest.param(b" \n\n", id="blank"), pytest.param(HEADER.encode(), id="header-only")],
)
def test_ut_svc_11_empty(store, raw):
    assert error_of(lambda: ImportService(store).import_csv(raw)).code == "CSV_EMPTY"


def test_ut_svc_12_row_limit(store):
    def rows(n: int) -> bytes:
        body = "".join(f"2026-10-01,{i + 1},food,\n" for i in range(n))
        return (HEADER + body).encode()

    assert ImportService(store).import_csv(rows(CSV_MAX_ROWS)).imported_count == CSV_MAX_ROWS
    err = error_of(lambda: ImportService(store).import_csv(rows(CSV_MAX_ROWS + 1)))
    assert (err.code, err.status, err.details[0].params) == ("CSV_TOO_MANY_ROWS", 413, {"max": CSV_MAX_ROWS})


def test_ut_svc_13_parse_error(store):
    raw = (HEADER + "2026-10-01,1,food," + "x" * 200_000 + "\n").encode()
    assert error_of(lambda: ImportService(store).import_csv(raw)).code == "CSV_PARSE_ERROR"


def test_ut_svc_13b_header_and_encoding_errors(store):
    assert error_of(lambda: ImportService(store).import_csv(b"a,b\n1,2\n")).code == "CSV_HEADER_INVALID"
    assert error_of(lambda: ImportService(store).import_csv("x".encode("utf-16"))).code == "CSV_ENCODING_UNSUPPORTED"


# ---- summary -------------------------------------------------------------------------


def test_ut_svc_14_first_supported_month(store, clock):
    add_expense(store, date(2000, 1, 15), 500)
    summary = SummaryService(store, clock).summary("2000-01")
    assert (summary.previous_month, summary.previous_total, summary.change_rate) == (None, 0, None)
    assert summary.total == 500
