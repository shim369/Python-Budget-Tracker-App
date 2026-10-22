"""Category use cases. Design refs: API-02..04, DATA-02 (delete cascade), DATA-05."""

from __future__ import annotations

from app.domain.categories import is_name_taken
from app.errors import ErrorCode, conflict, not_found
from app.repositories.json_store import JsonStore
from app.repositories.models import StoredCategory, next_id
from app.schemas.category import CategoryIn, CategoryListOut, CategoryOut
from app.services.views import category_label


def _category_out(category: StoredCategory, in_use: bool) -> CategoryOut:
    key, name = category_label(category)
    return CategoryOut(id=category.id, key=key, name=name, is_fixed=category.is_fixed, in_use=in_use)


class CategoryService:
    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def list(self) -> CategoryListOut:
        """[API-02] Fixed categories first, then user categories, each in id order."""
        data = self._store.read()
        used = {e.category_id for e in data.expenses}
        ordered = sorted(data.categories, key=lambda c: (not c.is_fixed, c.id))
        return CategoryListOut(items=[_category_out(c, c.id in used) for c in ordered])

    def create(self, payload: CategoryIn) -> CategoryOut:
        """[API-03] Names must not clash with user names or fixed aliases (DATA-05)."""
        with self._store.transaction() as tx:
            user_names = [c.name for c in tx.data.categories if c.name is not None]
            if is_name_taken(payload.name, user_names):
                raise conflict(ErrorCode.CATEGORY_NAME_DUPLICATED, "Category name already exists.")
            category = StoredCategory(
                id=next_id(tx.data, "category"), code=None, name=payload.name, is_fixed=False
            )
            tx.data.categories.append(category)
        return _category_out(category, in_use=False)

    def delete(self, category_id: str) -> None:
        """[API-04] Fixed or used categories cannot be deleted; its budget goes with it."""
        with self._store.transaction() as tx:
            category = next((c for c in tx.data.categories if c.id == category_id), None)
            if category is None:
                raise not_found(ErrorCode.CATEGORY_NOT_FOUND, category_id)
            if category.is_fixed:
                raise conflict(ErrorCode.CATEGORY_FIXED, "Fixed categories cannot be deleted.")
            count = sum(1 for e in tx.data.expenses if e.category_id == category_id)
            if count:
                raise conflict(
                    ErrorCode.CATEGORY_IN_USE, "Category is in use.", {"count": count}
                )
            tx.data.categories.remove(category)
            tx.data.budgets.categories.pop(category_id, None)
