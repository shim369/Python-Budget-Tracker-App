"""[API-05..09] Expenses."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.dependencies import get_expense_service
from app.routers.common import error_responses
from app.schemas.common import MonthStr
from app.schemas.expense import ExpenseIn, ExpenseListOut, ExpenseOut
from app.services.expense_service import ExpenseService

router = APIRouter(prefix="/api/expenses", tags=["expenses"])
Service = Annotated[ExpenseService, Depends(get_expense_service)]
MonthQuery = Annotated[MonthStr | None, Query(description="YYYY-MM; defaults to the current month")]


@router.get("", response_model=ExpenseListOut, responses=error_responses(400), summary="List expenses of a month")
def list_expenses(service: Service, month: MonthQuery = None) -> ExpenseListOut:
    return service.list(month)


@router.post(
    "",
    response_model=ExpenseOut,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(400),
    summary="Create an expense",
)
def create_expense(payload: ExpenseIn, service: Service) -> ExpenseOut:
    return service.create(payload)


@router.get("/{expense_id}", response_model=ExpenseOut, responses=error_responses(404), summary="Get an expense")
def get_expense(expense_id: str, service: Service) -> ExpenseOut:
    return service.get(expense_id)


@router.put(
    "/{expense_id}",
    response_model=ExpenseOut,
    responses=error_responses(400, 404),
    summary="Replace an expense",
)
def update_expense(expense_id: str, payload: ExpenseIn, service: Service) -> ExpenseOut:
    return service.update(expense_id, payload)


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=error_responses(404),
    summary="Delete an expense",
)
def delete_expense(expense_id: str, service: Service) -> Response:
    service.delete(expense_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
