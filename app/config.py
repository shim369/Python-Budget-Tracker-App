"""Application settings and fixed limits.

Design refs: DATA-01 (data file path), BR-02 (timezone), CSV-03 (import limits).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# [BR-02] All "today" / month decisions use this timezone.
TIMEZONE = "Asia/Tokyo"

# [CSV-03] Upload limits.
CSV_MAX_BYTES = 1_048_576
CSV_MAX_ROWS = 5_000

# [BR-04-2] Renewal notice window in days (also the renew window in BR-03).
UPCOMING_WINDOW_DAYS = 7

DATA_FILE_ENV = "BUDGET_DATA_FILE"


@dataclass(frozen=True)
class Settings:
    """Runtime settings. Tests build their own instance with a temp data file."""

    data_file: Path
    static_dir: Path

    @classmethod
    def from_env(cls) -> Settings:
        """[DATA-01] Data file defaults to data/budget.json, overridable by env."""
        data_file = Path(os.environ.get(DATA_FILE_ENV, PROJECT_ROOT / "data" / "budget.json"))
        return cls(data_file=data_file, static_dir=PROJECT_ROOT / "static")
