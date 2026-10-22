"""Fixed category master and name matching rules.

Design ref: DATA-05.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

OTHERS_KEY = "category.others"  # [BR-07-2] aggregated pie slice, distinct from category.other


@dataclass(frozen=True)
class FixedCategory:
    id: str
    code: str
    aliases: tuple[str, ...]  # CSV matching names (data rules, not UI text)


# [DATA-05] Order and ids are fixed; ids cat-000001..cat-000008 are reserved.
FIXED_CATEGORIES: tuple[FixedCategory, ...] = (
    FixedCategory("cat-000001", "food", ("food", "Food", "食費")),
    FixedCategory("cat-000002", "daily_goods", ("daily_goods", "Daily goods", "日用品")),
    FixedCategory("cat-000003", "housing", ("housing", "Housing", "住居費")),
    FixedCategory("cat-000004", "utilities", ("utilities", "Utilities", "水道光熱費")),
    FixedCategory("cat-000005", "transportation", ("transportation", "Transportation", "交通費")),
    FixedCategory("cat-000006", "communication", ("communication", "Communication", "通信費")),
    FixedCategory("cat-000007", "entertainment", ("entertainment", "Entertainment", "娯楽費")),
    FixedCategory("cat-000008", "other", ("other", "Other", "その他")),
)

FIXED_BY_CODE = {c.code: c for c in FIXED_CATEGORIES}


class CategoryLike(Protocol):
    id: str
    code: str | None
    name: str | None


def translation_key(code: str | None) -> str | None:
    """[DATA-05] Translation key is derived as "category." + code."""
    return f"category.{code}" if code else None


def normalize_name(name: str) -> str:
    """Names are compared trimmed and case-insensitively."""
    return name.strip().casefold()


def reserved_names() -> set[str]:
    """Normalized aliases of fixed categories; user categories may not reuse them."""
    return {normalize_name(alias) for c in FIXED_CATEGORIES for alias in c.aliases}


def is_name_taken(name: str, user_category_names: Iterable[str]) -> bool:
    """[DATA-05] Duplicate check for a new user category name."""
    normalized = normalize_name(name)
    if normalized in reserved_names():
        return True
    return any(normalize_name(existing) == normalized for existing in user_category_names)


def build_resolver(categories: Iterable[CategoryLike]) -> dict[str, str]:
    """[CSV-04] Map of normalized name -> category id used by CSV row validation."""
    resolver: dict[str, str] = {}
    for category in categories:
        if category.code is not None and category.code in FIXED_BY_CODE:
            for alias in FIXED_BY_CODE[category.code].aliases:
                resolver[normalize_name(alias)] = category.id
        elif category.name is not None:
            resolver[normalize_name(category.name)] = category.id
    return resolver
