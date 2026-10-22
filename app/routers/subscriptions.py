"""[API-10..18] Subscriptions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.dependencies import get_subscription_service
from app.routers.common import error_responses
from app.schemas.subscription import (
    SubscriptionIn,
    SubscriptionListOut,
    SubscriptionOut,
    UpcomingListOut,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])
Service = Annotated[SubscriptionService, Depends(get_subscription_service)]


@router.get("", response_model=SubscriptionListOut, summary="List subscriptions")
def list_subscriptions(service: Service) -> SubscriptionListOut:
    return service.list()


# [API-18] Registered before "/{subscription_id}" so that "upcoming" is not taken as an id.
@router.get("/upcoming", response_model=UpcomingListOut, summary="Renewals due within 7 days or overdue")
def upcoming(service: Service) -> UpcomingListOut:
    return service.upcoming()


@router.post(
    "",
    response_model=SubscriptionOut,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(400),
    summary="Create a subscription",
)
def create_subscription(payload: SubscriptionIn, service: Service) -> SubscriptionOut:
    return service.create(payload)


@router.get(
    "/{subscription_id}", response_model=SubscriptionOut, responses=error_responses(404), summary="Get a subscription"
)
def get_subscription(subscription_id: str, service: Service) -> SubscriptionOut:
    return service.get(subscription_id)


@router.put(
    "/{subscription_id}",
    response_model=SubscriptionOut,
    responses=error_responses(400, 404),
    summary="Update a subscription",
)
def update_subscription(subscription_id: str, payload: SubscriptionIn, service: Service) -> SubscriptionOut:
    return service.update(subscription_id, payload)


@router.delete(
    "/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=error_responses(404),
    summary="Delete a subscription",
)
def delete_subscription(subscription_id: str, service: Service) -> Response:
    service.delete(subscription_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{subscription_id}/pause",
    response_model=SubscriptionOut,
    responses=error_responses(404, 409),
    summary="Pause a subscription",
)
def pause(subscription_id: str, service: Service) -> SubscriptionOut:
    return service.pause(subscription_id)


@router.post(
    "/{subscription_id}/resume",
    response_model=SubscriptionOut,
    responses=error_responses(404, 409),
    summary="Resume a subscription",
)
def resume(subscription_id: str, service: Service) -> SubscriptionOut:
    return service.resume(subscription_id)


@router.post(
    "/{subscription_id}/renew",
    response_model=SubscriptionOut,
    responses=error_responses(404, 409),
    summary="Mark as renewed (advance the next renewal date)",
)
def renew(subscription_id: str, service: Service) -> SubscriptionOut:
    return service.renew(subscription_id)
