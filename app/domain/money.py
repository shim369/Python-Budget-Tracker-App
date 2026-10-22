"""Money rules. Amounts are always int yen, never float.

Design refs: BR-01 (range, rounding, CSV amount format), BR-04-1 (monthly equivalent).
"""

from __future__ import annotations

import re
from typing import Literal

Cycle = Literal["monthly", "yearly"]

# [BR-01-1] Ranges (inclusive).
AMOUNT_MIN = 1
AMOUNT_MAX = 9_999_999
BUDGET_MIN = 0
BUDGET_MAX = 99_999_999

_PLAIN_DIGITS = re.compile(r"^[0-9]+$")
_GROUPED_DIGITS = re.compile(r"^[0-9]{1,3}(,[0-9]{3})+$")


def is_amount_in_range(amount: int) -> bool:
    return AMOUNT_MIN <= amount <= AMOUNT_MAX


def monthly_equivalent(amount: int, cycle: Cycle) -> int:
    """[BR-04-1][BR-01-2] Yearly amounts are divided by 12 and floored."""
    if cycle == "monthly":
        return amount
    return amount // 12


def parse_csv_amount(text: str) -> int | str:
    """[BR-01-3] Parse a CSV amount cell.

    Returns the amount as int, or an error code string:
    AMOUNT_REQUIRED / INVALID_AMOUNT / AMOUNT_OUT_OF_RANGE.
    """
    value = text.strip()
    if value == "":
        return "AMOUNT_REQUIRED"
    if not (_PLAIN_DIGITS.match(value) or _GROUPED_DIGITS.match(value)):
        return "INVALID_AMOUNT"
    amount = int(value.replace(",", ""))
    if not is_amount_in_range(amount):
        return "AMOUNT_OUT_OF_RANGE"
    return amount
