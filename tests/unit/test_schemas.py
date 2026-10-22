"""UT-SCH: Pydantic validation of request schemas, checked through the ERR-03 mapping."""

from decimal import Decimal

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from app.errors import pydantic_errors_to_details
from app.schemas.budget import BudgetsIn
from app.schemas.category import CategoryIn
from app.schemas.common import MonthStr, RatePercent
from app.schemas.expense import ExpenseIn
from app.schemas.subscription import SubscriptionIn

VALID_EXPENSE = {"date": "2026-10-23", "amount": 1200, "category_id": "cat-000001", "memo": "Lunch"}


def details_of(model: type[BaseModel], payload: dict) -> list[tuple[str | None, str, dict]]:
    with pytest.raises(ValidationError) as exc_info:
        model.model_validate(payload)
    return [(d.field, d.code, d.params) for d in pydantic_errors_to_details(exc_info.value.errors())]


def codes_of(model: type[BaseModel], payload: dict) -> list[str]:
    return [code for _, code, _ in details_of(model, payload)]


def test_ut_sch_01_valid_expense():
    expense = ExpenseIn.model_validate({**VALID_EXPENSE, "memo": "  Lunch  "})
    assert expense.memo == "Lunch"
    without_memo = {k: v for k, v in VALID_EXPENSE.items() if k != "memo"}
    assert ExpenseIn.model_validate(without_memo).memo == ""


@pytest.mark.parametrize("amount", [1200.0, "1200", True, None])
def test_ut_sch_02_amount_type(amount):
    assert codes_of(ExpenseIn, {**VALID_EXPENSE, "amount": amount}) == ["INVALID_TYPE"]


@pytest.mark.parametrize("amount", [0, 10_000_000])
def test_ut_sch_03_amount_range(amount):
    assert details_of(ExpenseIn, {**VALID_EXPENSE, "amount": amount}) == [
        ("amount", "OUT_OF_RANGE", {"min": 1, "max": 9_999_999})
    ]


@pytest.mark.parametrize("amount", [1, 9_999_999])
def test_ut_sch_04_amount_boundaries_ok(amount):
    assert ExpenseIn.model_validate({**VALID_EXPENSE, "amount": amount}).amount == amount


@pytest.mark.parametrize("value", ["2026-02-30", "2026/10/01", "2026-10-01T00:00:00"])
def test_ut_sch_05_date_format(value):
    assert codes_of(ExpenseIn, {**VALID_EXPENSE, "date": value}) == ["INVALID_DATE"]


def test_ut_sch_06_date_type():
    assert codes_of(ExpenseIn, {**VALID_EXPENSE, "date": 1_700_000_000}) == ["INVALID_TYPE"]


@pytest.mark.parametrize("value", ["1999-12-31", "2100-01-01"])
def test_ut_sch_07_date_range(value):
    assert details_of(ExpenseIn, {**VALID_EXPENSE, "date": value}) == [
        ("date", "DATE_OUT_OF_RANGE", {"min": "2000-01-01", "max": "2099-12-31"})
    ]


def test_ut_sch_08_memo_length():
    assert ExpenseIn.model_validate({**VALID_EXPENSE, "memo": "x" * 100})
    assert details_of(ExpenseIn, {**VALID_EXPENSE, "memo": "x" * 101}) == [("memo", "TOO_LONG", {"max": 100})]


def test_ut_sch_09_unknown_and_missing_fields():
    payload = {"amount": 1200, "category_id": "cat-000001", "extra": 1}
    assert sorted(details_of(ExpenseIn, payload)) == [
        ("date", "FIELD_REQUIRED", {}),
        ("extra", "UNKNOWN_FIELD", {}),
    ]


def test_ut_sch_10_cycle_choice():
    payload = {"name": "Video", "amount": 990, "cycle": "weekly", "next_renewal_date": "2026-10-31"}
    assert details_of(SubscriptionIn, payload) == [
        ("cycle", "INVALID_CHOICE", {"choices": ["monthly", "yearly"]})
    ]


@pytest.mark.parametrize(
    ("model", "payload", "expected"),
    [
        pytest.param(
            SubscriptionIn,
            {"name": "  ", "amount": 990, "cycle": "monthly", "next_renewal_date": "2026-10-31"},
            ("name", "TOO_SHORT", {"min": 1}),
            id="subscription-blank",
        ),
        pytest.param(
            SubscriptionIn,
            {"name": "x" * 51, "amount": 990, "cycle": "monthly", "next_renewal_date": "2026-10-31"},
            ("name", "TOO_LONG", {"max": 50}),
            id="subscription-51",
        ),
        pytest.param(CategoryIn, {"name": "x" * 31}, ("name", "TOO_LONG", {"max": 30}), id="category-31"),
    ],
)
def test_ut_sch_11_name_length(model, payload, expected):
    assert details_of(model, payload) == [expected]


@pytest.mark.parametrize("overall", [None, 0, 99_999_999])
def test_ut_sch_12_budget_valid(overall):
    assert BudgetsIn.model_validate({"overall": overall, "categories": []}).overall == overall


@pytest.mark.parametrize("overall", [-1, 100_000_000])
def test_ut_sch_12_budget_out_of_range(overall):
    assert details_of(BudgetsIn, {"overall": overall, "categories": []}) == [
        ("overall", "OUT_OF_RANGE", {"min": 0, "max": 99_999_999})
    ]


def test_ut_sch_12_budget_nested_path():
    payload = {"overall": None, "categories": [{"category_id": "cat-000001", "amount": -5}]}
    assert codes_of(BudgetsIn, payload) == ["OUT_OF_RANGE"]
    assert details_of(BudgetsIn, payload)[0][0] == "categories.0.amount"


def test_ut_sch_13_month():
    adapter = TypeAdapter(MonthStr)
    assert adapter.validate_python("2026-10") == "2026-10"
    with pytest.raises(ValidationError) as exc_info:
        adapter.validate_python("2026-13")
    assert pydantic_errors_to_details(exc_info.value.errors())[0].code == "INVALID_MONTH"


def test_ut_sch_14_rate_serialized_as_string():
    adapter = TypeAdapter(RatePercent)
    assert adapter.dump_json(Decimal("12.5")) == b'"12.5"'
    assert adapter.dump_json(None) == b"null"
