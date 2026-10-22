"""Category schemas. Design refs: API-02..04, DATA-05."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.common import InputModel


class CategoryIn(InputModel):
    """[API-03] New user category."""

    name: Annotated[str, Field(min_length=1, max_length=30)]


class CategoryOut(BaseModel):
    """[API-02] key is set for fixed categories (translated by the UI), name for user ones."""

    id: str
    key: str | None
    name: str | None
    is_fixed: bool
    in_use: bool


class CategoryListOut(BaseModel):
    items: list[CategoryOut]
