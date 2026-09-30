from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from core.auth import require_current_user_id
from schemas.push_schemas import (
    NotificationSettingsResponse,
    NotificationSettingsUpdateRequest,
    PushStatusResponse,
    PushSubscriptionRequest,
    PushSubscriptionResponse,
    PushTestResponse,
)
from services.push_service import PushService, get_push_service


router = APIRouter(prefix="/push", tags=["push"])


@router.get("/config", response_model=PushStatusResponse)
def get_push_config(push_service: PushService = Depends(get_push_service)) -> dict:
    return {"success": True, "data": push_service.get_public_config()}


@router.post("/subscribe", response_model=PushSubscriptionResponse)
def subscribe(
    body: PushSubscriptionRequest,
    user_id: str = Depends(require_current_user_id),
    user_agent: str | None = Header(default=None),
    push_service: PushService = Depends(get_push_service),
) -> dict:
    subscription = push_service.subscribe(
        user_id=user_id,
        endpoint=body.endpoint,
        p256dh=body.keys.p256dh,
        auth=body.keys.auth,
        user_agent=user_agent,
    )
    return {"success": True, "data": subscription}


@router.post("/unsubscribe", response_model=PushStatusResponse)
def unsubscribe(
    body: PushSubscriptionRequest,
    user_id: str = Depends(require_current_user_id),
    push_service: PushService = Depends(get_push_service),
) -> dict:
    push_service.unsubscribe(user_id=user_id, endpoint=body.endpoint)
    return {"success": True, "data": {"unsubscribed": True}}


@router.post("/test", response_model=PushTestResponse)
def send_test_push(
    user_id: str = Depends(require_current_user_id),
    push_service: PushService = Depends(get_push_service),
) -> dict:
    result = push_service.send_test_push(user_id=user_id)
    return {"success": True, "data": result}


@router.get("/settings", response_model=NotificationSettingsResponse)
def get_notification_settings(
    user_id: str = Depends(require_current_user_id),
    push_service: PushService = Depends(get_push_service),
) -> dict:
    return {"success": True, "data": push_service.get_notification_settings(user_id=user_id)}


@router.patch("/settings", response_model=NotificationSettingsResponse)
def update_notification_settings(
    body: NotificationSettingsUpdateRequest,
    user_id: str = Depends(require_current_user_id),
    push_service: PushService = Depends(get_push_service),
) -> dict:
    return {
        "success": True,
        "data": push_service.update_notification_settings(
            user_id=user_id,
            enabled=body.enabled,
            notification_time=body.notification_time,
            timezone=body.timezone,
        ),
    }
