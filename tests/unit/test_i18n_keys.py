"""UT-I18N: translation dictionaries stay consistent (REQ-023)."""

import json
import re

import pytest

from app.config import PROJECT_ROOT
from app.domain.categories import FIXED_CATEGORIES
from app.errors import ErrorCode

I18N_DIR = PROJECT_ROOT / "static" / "i18n"
CSV_ROW_CODES = [
    "COLUMN_COUNT_MISMATCH",
    "DATE_REQUIRED",
    "INVALID_DATE",
    "DATE_OUT_OF_RANGE",
    "AMOUNT_REQUIRED",
    "INVALID_AMOUNT",
    "AMOUNT_OUT_OF_RANGE",
    "CATEGORY_REQUIRED",
    "UNKNOWN_CATEGORY",
    "MEMO_TOO_LONG",
    "DUPLICATE_IN_FILE",
    "DUPLICATE_EXISTING",
]
FRONT_ONLY_CODES = ["NETWORK_ERROR", "UNKNOWN"]


def flatten(node: dict, prefix: str = "") -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten(value, path))
        else:
            result[path] = value
    return result


@pytest.fixture(scope="module")
def dicts() -> dict[str, dict[str, str]]:
    return {lang: flatten(json.loads((I18N_DIR / f"{lang}.json").read_text(encoding="utf-8"))) for lang in ("en", "ja")}


def test_ut_i18n_01_same_keys(dicts):
    en, ja = set(dicts["en"]), set(dicts["ja"])
    assert en - ja == set(), "keys missing in ja.json"
    assert ja - en == set(), "keys missing in en.json"


def test_ut_i18n_02_no_empty_values(dicts):
    for lang, entries in dicts.items():
        empty = [key for key, value in entries.items() if not isinstance(value, str) or value.strip() == ""]
        assert empty == [], f"empty values in {lang}.json"


def test_ut_i18n_03_backend_error_codes(dicts):
    codes = [value for name, value in vars(ErrorCode).items() if name.isupper()]
    for lang, entries in dicts.items():
        missing = [code for code in codes + FRONT_ONLY_CODES if f"errors.{code}" not in entries]
        assert missing == [], f"untranslated error codes in {lang}.json"


def test_ut_i18n_04_csv_row_codes(dicts):
    for lang, entries in dicts.items():
        missing = [code for code in CSV_ROW_CODES if f"csv.row.{code}" not in entries]
        assert missing == [], f"untranslated CSV row codes in {lang}.json"


def test_ut_i18n_05_fixed_category_names_match_csv_aliases(dicts):
    for category in FIXED_CATEGORIES:
        for lang in ("en", "ja"):
            label = dicts[lang][f"category.{category.code}"]
            assert label in category.aliases, f"{lang}: {label!r} is not a CSV alias of {category.code}"


def test_ut_i18n_06_same_placeholders(dicts):
    placeholder = re.compile(r"\{(\w+)\}")
    mismatched = [
        key
        for key, value in dicts["en"].items()
        if set(placeholder.findall(value)) != set(placeholder.findall(dicts["ja"].get(key, "")))
    ]
    assert mismatched == []
