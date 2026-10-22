"""FastAPI dependencies that build services. Design ref: MOD-20."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.clock import Clock, get_clock
from app.repositories.json_store import JsonStore
from app.services.budget_service import BudgetService
from app.services.category_service import CategoryService
from app.services.expense_service import ExpenseService
from app.services.import_service import ImportService
from app.services.subscription_service import SubscriptionService
from app.services.summary_service import SummaryService


def get_store(request: Request) -> JsonStore:
    """The single store created in create_app (shared lock)."""
    return request.app.state.store


StoreDep = Annotated[JsonStore, Depends(get_store)]
ClockDep = Annotated[Clock, Depends(get_clock)]


def get_category_service(store: StoreDep) -> CategoryService:
    return CategoryService(store)


def get_expense_service(store: StoreDep, clock: ClockDep) -> ExpenseService:
    return ExpenseService(store, clock)


def get_subscription_service(store: StoreDep, clock: ClockDep) -> SubscriptionService:
    return SubscriptionService(store, clock)


def get_budget_service(store: StoreDep) -> BudgetService:
    return BudgetService(store)


def get_summary_service(store: StoreDep, clock: ClockDep) -> SummaryService:
    return SummaryService(store, clock)


def get_import_service(store: StoreDep) -> ImportService:
    return ImportService(store)
