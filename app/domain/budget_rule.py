"""Budget judgement. Integer comparison only (no float).

Design ref: BR-05.
"""

from __future__ import annotations

from enum import StrEnum

CAUTION_PERCENT = 80


class BudgetStatus(StrEnum):
    NONE = "none"
    OK = "ok"
    CAUTION = "caution"
    OVER = "over"


def _has_budget(budget: int | None) -> bool:
    return budget is not None and budget > 0


def judge(spent: int, budget: int | None) -> BudgetStatus:
    """[BR-05] ok < 80% <= caution <= 100% < over. Exactly 100% is caution."""
    if not _has_budget(budget):
        return BudgetStatus.NONE
    assert budget is not None
    if spent > budget:
        return BudgetStatus.OVER
    if spent * 100 >= budget * CAUTION_PERCENT:
        return BudgetStatus.CAUTION
    return BudgetStatus.OK


def usage_percent(spent: int, budget: int | None) -> int | None:
    """[BR-05] Display-only usage, floored. Never used to decide the status."""
    if not _has_budget(budget):
        return None
    assert budget is not None
    return spent * 100 // budget
