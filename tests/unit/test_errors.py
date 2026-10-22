"""UT-ERR: unified error conversion (ERR-01..03, ERR-10)."""

import pytest

from app.errors import (
    ErrorCode,
    conflict,
    error_body,
    field_error,
    not_found,
    pydantic_errors_to_details,
)
from app.schemas.common import ErrorDetail


def convert(error: dict) -> tuple:
    detail = pydantic_errors_to_details([error])[0]
    return detail.field, detail.code, detail.params


def test_ut_err_01_field_path():
    assert convert({"type": "missing", "loc": ("body", "categories", 0, "amount")})[0] == "categories.0.amount"
    assert convert({"type": "missing", "loc": ("query", "month")})[0] == "month"
    assert convert({"type": "missing", "loc": ("body",)})[0] is None


@pytest.mark.parametrize(
    ("error", "code", "params"),
    [
        ({"type": "missing"}, "FIELD_REQUIRED", {}),
        ({"type": "int_type"}, "INVALID_TYPE", {}),
        ({"type": "greater_than_equal", "ctx": {"ge": 1}}, "OUT_OF_RANGE", {"min": 1}),
        ({"type": "less_than_equal", "ctx": {"le": 9}}, "OUT_OF_RANGE", {"max": 9}),
        ({"type": "string_too_short", "ctx": {"min_length": 1}}, "TOO_SHORT", {"min": 1}),
        ({"type": "string_too_long", "ctx": {"max_length": 30}}, "TOO_LONG", {"max": 30}),
        ({"type": "date_from_datetime_parsing"}, "INVALID_DATE", {}),
        ({"type": "literal_error", "ctx": {"expected": "'a' or 'b'"}}, "INVALID_CHOICE", {"choices": ["a", "b"]}),
        ({"type": "extra_forbidden"}, "UNKNOWN_FIELD", {}),
    ],
)
def test_ut_err_02_type_mapping(error, code, params):
    _, actual_code, actual_params = convert({"loc": ("body", "x"), **error})
    assert (actual_code, actual_params) == (code, params)


def test_ut_err_03_custom_code_kept():
    error = {"type": "OUT_OF_RANGE", "loc": ("body", "amount"), "ctx": {"min": 1, "max": 9}}
    assert convert(error) == ("amount", "OUT_OF_RANGE", {"min": 1, "max": 9})


def test_ut_err_04_unknown_type():
    assert convert({"type": "something_new", "loc": ("body", "x")})[1] == "INVALID_VALUE"


def test_ut_err_05_error_body_shape():
    body = error_body("VALIDATION_ERROR", "msg", [ErrorDetail(field="amount", code="OUT_OF_RANGE", params={"min": 1})])
    assert body == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "msg",
            "details": [{"field": "amount", "code": "OUT_OF_RANGE", "params": {"min": 1}}],
        }
    }
    assert error_body("NOT_FOUND", "x") == {"error": {"code": "NOT_FOUND", "message": "x", "details": []}}


def test_ut_err_06_helpers():
    nf = not_found(ErrorCode.EXPENSE_NOT_FOUND, "exp-000001")
    assert (nf.code, nf.status, nf.details) == ("EXPENSE_NOT_FOUND", 404, [])

    with_params = conflict(ErrorCode.CATEGORY_IN_USE, "in use", {"count": 3})
    assert (with_params.status, with_params.details[0].params) == (409, {"count": 3})
    assert conflict(ErrorCode.CATEGORY_FIXED, "fixed").details == []

    fe = field_error("category_id", "UNKNOWN_CATEGORY")
    assert (fe.code, fe.status) == ("VALIDATION_ERROR", 400)
    assert (fe.details[0].field, fe.details[0].code, fe.details[0].params) == ("category_id", "UNKNOWN_CATEGORY", {})
