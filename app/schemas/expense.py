"""Expense schemas. Design refs: API-05..09, BR-01, BR-02."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.common import Amount, AppDate, InputModel


class ExpenseIn(InputModel):
    """[API-06][API-08] Body for create and full update."""

    date: AppDate
    amount: Amount
    category_id: str
    memo: Annotated[str, Field(max_length=100)] = ""


class ExpenseOut(BaseModel):
    id: str
    date: date
    amount: int
    category_id: str
    memo: str


class ExpenseListOut(BaseModel):
    """[API-05] Expenses of one month, newest first."""

    month: str
    total: int
    count: int
    items: list[ExpenseOut]
