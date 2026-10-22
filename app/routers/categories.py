"""[API-02..04] Categories."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.dependencies import get_category_service
from app.routers.common import error_responses
from app.schemas.category import CategoryIn, CategoryListOut, CategoryOut
from app.services.category_service import CategoryService

router = APIRouter(prefix="/api/categories", tags=["categories"])
Service = Annotated[CategoryService, Depends(get_category_service)]


@router.get("", response_model=CategoryListOut, summary="List categories")
def list_categories(service: Service) -> CategoryListOut:
    return service.list()


@router.post(
    "",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(400, 409),
    summary="Add a user category",
)
def create_category(payload: CategoryIn, service: Service) -> CategoryOut:
    return service.create(payload)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=error_responses(404, 409),
    summary="Delete an unused user category",
)
def delete_category(category_id: str, service: Service) -> Response:
    service.delete(category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
