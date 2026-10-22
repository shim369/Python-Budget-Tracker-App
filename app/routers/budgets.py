"""[API-19..20] Budgets."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_budget_service
from app.routers.common import error_responses
from app.schemas.budget import BudgetsIn, BudgetsOut
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/api/budgets", tags=["budgets"])
Service = Annotated[BudgetService, Depends(get_budget_service)]


@router.get("", response_model=BudgetsOut, summary="Get budget settings")
def get_budgets(service: Service) -> BudgetsOut:
    return service.get()


@router.put("", response_model=BudgetsOut, responses=error_responses(400), summary="Replace budget settings")
def replace_budgets(payload: BudgetsIn, service: Service) -> BudgetsOut:
    return service.replace(payload)
