"""UT-CAT: fixed categories and name rules (DATA-05)."""

import pytest

from app.domain.categories import (
    FIXED_CATEGORIES,
    build_resolver,
    is_name_taken,
    translation_key,
)
from app.repositories.models import DataFile, StoredCategory


def test_ut_cat_01_translation_key():
    assert translation_key("food") == "category.food"
    assert translation_key(None) is None


def test_ut_cat_02_fixed_master():
    assert [(c.id, c.code) for c in FIXED_CATEGORIES] == [
        ("cat-000001", "food"),
        ("cat-000002", "daily_goods"),
        ("cat-000003", "housing"),
        ("cat-000004", "utilities"),
        ("cat-000005", "transportation"),
        ("cat-000006", "communication"),
        ("cat-000007", "entertainment"),
        ("cat-000008", "other"),
    ]


@pytest.mark.parametrize("name", ["食費", "FOOD", " Food ", "daily goods", "その他"])
def test_ut_cat_03_fixed_alias_is_taken(name):
    assert is_name_taken(name, [])


def test_ut_cat_04_user_name_duplicate():
    assert is_name_taken("pets", ["Pets"])
    assert is_name_taken(" Pets ", ["pets"])


def test_ut_cat_05_free_name():
    assert not is_name_taken("Hobby", ["Pets"])


def test_ut_cat_06_resolver():
    data = DataFile.initial()
    categories = [*data.categories, StoredCategory(id="cat-000009", code=None, name="Pets", is_fixed=False)]
    resolver = build_resolver(categories)
    assert resolver["食費"] == "cat-000001"
    assert resolver["daily goods"] == "cat-000002"
    assert resolver["pets"] == "cat-000009"
    assert "unknown" not in resolver
