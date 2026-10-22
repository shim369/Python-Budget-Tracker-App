"""Conversions from storage models to API schemas, shared by the services."""

from __future__ import annotations

from app.domain.categories import translation_key
from app.domain.money import monthly_equivalent
from app.repositories.models import DataFile, StoredCategory, StoredExpense, StoredSubscription
from app.schemas.expense import ExpenseOut
from app.schemas.subscription import SubscriptionOut


def category_label(category: StoredCategory | None) -> tuple[str | None, str | None]:
    """[AD-03] (key, name): fixed categories are translated by key, user ones show name."""
    if category is None:
        return None, None
    return translation_key(category.code), category.name


def categories_by_id(data: DataFile) -> dict[str, StoredCategory]:
    return {c.id: c for c in data.categories}


def expense_out(expense: StoredExpense) -> ExpenseOut:
    return ExpenseOut.model_validate(expense.model_dump())


def subscription_out(sub: StoredSubscription) -> SubscriptionOut:
    return SubscriptionOut(
        **sub.model_dump(), monthly_equivalent=monthly_equivalent(sub.amount, sub.cycle)
    )
