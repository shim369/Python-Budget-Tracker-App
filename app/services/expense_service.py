"""Expense use cases. Design refs: API-05..09, BR-02."""

from __future__ import annotations

from app.clock import Clock
from app.domain.period import month_of
from app.errors import ErrorCode, field_error, not_found
from app.repositories.json_store import JsonStore
from app.repositories.models import DataFile, StoredExpense, next_id
from app.schemas.expense import ExpenseIn, ExpenseListOut, ExpenseOut
from app.services.views import expense_out


def _ensure_category(data: DataFile, category_id: str) -> None:
    if not any(c.id == category_id for c in data.categories):
        raise field_error("category_id", "UNKNOWN_CATEGORY")


def _find(data: DataFile, expense_id: str) -> StoredExpense:
    expense = next((e for e in data.expenses if e.id == expense_id), None)
    if expense is None:
        raise not_found(ErrorCode.EXPENSE_NOT_FOUND, expense_id)
    return expense


class ExpenseService:
    def __init__(self, store: JsonStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    def list(self, month: str | None) -> ExpenseListOut:
        """[API-05] Month defaults to the current month; newest first (date desc, id desc)."""
        ym = month or month_of(self._clock.today())
        data = self._store.read()
        items = [e for e in data.expenses if month_of(e.date) == ym]
        items.sort(key=lambda e: (e.date, e.id), reverse=True)
        return ExpenseListOut(
            month=ym,
            total=sum(e.amount for e in items),
            count=len(items),
            items=[expense_out(e) for e in items],
        )

    def get(self, expense_id: str) -> ExpenseOut:
        return expense_out(_find(self._store.read(), expense_id))

    def create(self, payload: ExpenseIn) -> ExpenseOut:
        """[API-06]"""
        with self._store.transaction() as tx:
            _ensure_category(tx.data, payload.category_id)
            expense = StoredExpense(id=next_id(tx.data, "expense"), **payload.model_dump())
            tx.data.expenses.append(expense)
        return expense_out(expense)

    def update(self, expense_id: str, payload: ExpenseIn) -> ExpenseOut:
        """[API-08] Full replacement of all fields."""
        with self._store.transaction() as tx:
            expense = _find(tx.data, expense_id)
            _ensure_category(tx.data, payload.category_id)
            updated = StoredExpense(id=expense.id, **payload.model_dump())
            tx.data.expenses[tx.data.expenses.index(expense)] = updated
        return expense_out(updated)

    def delete(self, expense_id: str) -> None:
        """[API-09]"""
        with self._store.transaction() as tx:
            tx.data.expenses.remove(_find(tx.data, expense_id))
