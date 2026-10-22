"""Status schema. Design refs: API-01, BR-02, ERR-30."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class StatusOut(BaseModel):
    today: date
    timezone: str
    current_month: str
    data_recovered: bool
    backup_file: str | None
