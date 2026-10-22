"""[API-21..23] Monthly summary and chart data."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_summary_service
from app.routers.common import error_responses
from app.schemas.chart import CategoryBreakdownOut, MonthlyTrendOut
from app.schemas.common import MonthStr
from app.schemas.summary import MonthlySummaryOut
from app.services.summary_service import SummaryService

router = APIRouter(prefix="/api", tags=["summary"])
Service = Annotated[SummaryService, Depends(get_summary_service)]
MonthQuery = Annotated[MonthStr | None, Query(description="YYYY-MM; defaults to the current month")]


@router.get("/summary", response_model=MonthlySummaryOut, responses=error_responses(400), summary="Monthly summary")
def summary(service: Service, month: MonthQuery = None) -> MonthlySummaryOut:
    return service.summary(month)


@router.get(
    "/charts/category-breakdown",
    response_model=CategoryBreakdownOut,
    responses=error_responses(400),
    summary="Pie chart data (top 7 + others)",
)
def category_breakdown(service: Service, month: MonthQuery = None) -> CategoryBreakdownOut:
    return service.breakdown(month)


@router.get(
    "/charts/monthly-trend",
    response_model=MonthlyTrendOut,
    responses=error_responses(400),
    summary="Bar chart data (last 6 months)",
)
def monthly_trend(service: Service, month: MonthQuery = None) -> MonthlyTrendOut:
    return service.trend(month)
