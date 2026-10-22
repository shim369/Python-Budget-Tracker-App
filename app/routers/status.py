"""[API-01] Application status."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import TIMEZONE
from app.dependencies import ClockDep, StoreDep
from app.domain.period import month_of
from app.schemas.status import StatusOut

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status", response_model=StatusOut, summary="Today and data recovery status")
def get_status(store: StoreDep, clock: ClockDep) -> StatusOut:
    today = clock.today()
    return StatusOut(
        today=today,
        timezone=TIMEZONE,
        current_month=month_of(today),
        data_recovered=store.recovery is not None,
        backup_file=store.recovery.backup_file if store.recovery else None,
    )
