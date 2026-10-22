"""Budget schemas. Design refs: API-19, API-20, BR-01-1."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import BudgetAmount, InputModel


class CategoryBudgetItem(InputModel):
    """0 or null means "not set" and is not stored."""

    category_id: str
    amount: BudgetAmount | None


class BudgetsIn(InputModel):
    """[API-20] Full replacement of the budget settings."""

    overall: BudgetAmount | None
    categories: list[CategoryBudgetItem]


class CategoryBudgetOut(BaseModel):
    category_id: str
    amount: int


class BudgetsOut(BaseModel):
    """[API-19] Only budgets that are set are listed."""

    overall: int | None
    categories: list[CategoryBudgetOut]
