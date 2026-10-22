"""Budget use cases. Design refs: API-19, API-20, BR-01-1."""

from __future__ import annotations

from app.errors import validation_error
from app.repositories.json_store import JsonStore
from app.repositories.models import StoredBudgets
from app.schemas.budget import BudgetsIn, BudgetsOut, CategoryBudgetOut
from app.schemas.common import ErrorDetail


def _normalize(amount: int | None) -> int | None:
    """[BR-01-1] 0 and null both mean "not set" and are stored as null."""
    return amount if amount else None


def _budgets_out(budgets: StoredBudgets) -> BudgetsOut:
    return BudgetsOut(
        overall=budgets.overall,
        categories=[
            CategoryBudgetOut(category_id=cid, amount=amount)
            for cid, amount in sorted(budgets.categories.items())
        ],
    )


class BudgetService:
    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def get(self) -> BudgetsOut:
        """[API-19]"""
        return _budgets_out(self._store.read().budgets)

    def replace(self, payload: BudgetsIn) -> BudgetsOut:
        """[API-20] Full replacement; categories not sent lose their budget."""
        with self._store.transaction() as tx:
            known = {c.id for c in tx.data.categories}
            details: list[ErrorDetail] = []
            seen: set[str] = set()
            for index, item in enumerate(payload.categories):
                field = f"categories.{index}.category_id"
                if item.category_id in seen:
                    details.append(ErrorDetail(field=field, code="DUPLICATED_CATEGORY"))
                elif item.category_id not in known:
                    details.append(ErrorDetail(field=field, code="UNKNOWN_CATEGORY"))
                seen.add(item.category_id)
            if details:
                raise validation_error(details)
            categories = {
                item.category_id: amount
                for item in payload.categories
                if (amount := _normalize(item.amount)) is not None
            }
            tx.data.budgets = StoredBudgets(overall=_normalize(payload.overall), categories=categories)
            result = _budgets_out(tx.data.budgets)
        return result
