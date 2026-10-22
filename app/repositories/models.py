"""Storage models for data/budget.json. Loading and validation share these models.

Design refs: DATA-02 (structure, integrity rules), DATA-03 (ids), DATA-05 (fixed categories).
"""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from app.domain.categories import FIXED_CATEGORIES
from app.domain.money import AMOUNT_MAX, AMOUNT_MIN, BUDGET_MAX
from app.domain.period import MAX_DATE, MIN_DATE

IdKind = Literal["expense", "category", "subscription"]
ID_PREFIX: dict[str, str] = {"expense": "exp", "category": "cat", "subscription": "sub"}
_ID_RE = re.compile(r"^(exp|cat|sub)-(\d{6,})$")

StoredAmount = Annotated[StrictInt, Field(ge=AMOUNT_MIN, le=AMOUNT_MAX)]
StoredBudget = Annotated[StrictInt, Field(ge=1, le=BUDGET_MAX)]
StoredDate = Annotated[date, Field(ge=MIN_DATE, le=MAX_DATE)]


class _Stored(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StoredCategory(_Stored):
    id: Annotated[str, Field(pattern=r"^cat-\d{6,}$")]
    code: str | None = None
    name: Annotated[str, Field(min_length=1, max_length=30)] | None = None
    is_fixed: bool


class StoredExpense(_Stored):
    id: Annotated[str, Field(pattern=r"^exp-\d{6,}$")]
    date: StoredDate
    amount: StoredAmount
    category_id: str
    memo: Annotated[str, Field(max_length=100)] = ""


class StoredSubscription(_Stored):
    id: Annotated[str, Field(pattern=r"^sub-\d{6,}$")]
    name: Annotated[str, Field(min_length=1, max_length=50)]
    amount: StoredAmount
    cycle: Literal["monthly", "yearly"]
    next_renewal_date: StoredDate
    anchor_day: Annotated[StrictInt, Field(ge=1, le=31)]
    anchor_month: Annotated[StrictInt, Field(ge=1, le=12)] | None = None
    status: Literal["active", "paused"]

    @model_validator(mode="after")
    def _anchor_matches_cycle(self) -> Self:
        if (self.cycle == "yearly") != (self.anchor_month is not None):
            raise ValueError("anchor_month must be set only for yearly subscriptions")
        return self


class StoredBudgets(_Stored):
    overall: StoredBudget | None = None
    categories: dict[str, StoredBudget] = Field(default_factory=dict)


class Sequences(_Stored):
    expense: Annotated[StrictInt, Field(ge=0)] = 0
    category: Annotated[StrictInt, Field(ge=0)] = 0
    subscription: Annotated[StrictInt, Field(ge=0)] = 0


def id_number(entity_id: str) -> int:
    match = _ID_RE.match(entity_id)
    return int(match.group(2)) if match else 0


class DataFile(_Stored):
    """[DATA-02] Whole data file. Integrity violations make the file "corrupted" (ERR-30)."""

    schema_version: Literal[1] = 1
    sequences: Sequences = Field(default_factory=Sequences)
    categories: list[StoredCategory] = Field(default_factory=list)
    expenses: list[StoredExpense] = Field(default_factory=list)
    subscriptions: list[StoredSubscription] = Field(default_factory=list)
    budgets: StoredBudgets = Field(default_factory=StoredBudgets)

    @model_validator(mode="after")
    def _check_integrity(self) -> Self:
        # 1. unique ids
        for name, items in (
            ("categories", self.categories),
            ("expenses", self.expenses),
            ("subscriptions", self.subscriptions),
        ):
            ids = [item.id for item in items]
            if len(ids) != len(set(ids)):
                raise ValueError(f"duplicate ids in {name}")
        # 2. references
        category_ids = {c.id for c in self.categories}
        if any(e.category_id not in category_ids for e in self.expenses):
            raise ValueError("expense refers to an unknown category")
        if any(cid not in category_ids for cid in self.budgets.categories):
            raise ValueError("budget refers to an unknown category")
        # 3. fixed categories
        fixed = {(c.id, c.code) for c in self.categories if c.is_fixed}
        if fixed != {(f.id, f.code) for f in FIXED_CATEGORIES}:
            raise ValueError("fixed categories are missing or altered")
        if any(c.name is None for c in self.categories if not c.is_fixed):
            raise ValueError("user category without a name")
        # 4. sequences cover existing ids
        for kind, items in (
            ("expense", self.expenses),
            ("category", self.categories),
            ("subscription", self.subscriptions),
        ):
            if max((id_number(i.id) for i in items), default=0) > getattr(self.sequences, kind):
                raise ValueError(f"sequence for {kind} is behind existing ids")
        return self

    @classmethod
    def initial(cls) -> DataFile:
        """[DATA-06] Fixed categories only, no expenses/subscriptions/budgets."""
        categories = [
            StoredCategory(id=c.id, code=c.code, name=None, is_fixed=True) for c in FIXED_CATEGORIES
        ]
        return cls(sequences=Sequences(category=len(categories)), categories=categories)


def next_id(data: DataFile, kind: IdKind) -> str:
    """[DATA-03] Monotonic, never reused. Call inside a store transaction."""
    value = getattr(data.sequences, kind) + 1
    setattr(data.sequences, kind, value)
    return f"{ID_PREFIX[kind]}-{value:06d}"
