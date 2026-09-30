from __future__ import annotations

from pydantic import BaseModel, Field


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=1)
    auth: str = Field(min_length=1)


class PushSubscriptionRequest(BaseModel):
    endpoint: str = Field(min_length=1)
    keys: PushKeys


class PushSubscriptionResponse(BaseModel):
    success: bool
    data: dict


class PushStatusResponse(BaseModel):
    success: bool
    data: dict


class PushTestResponse(BaseModel):
    success: bool
    data: dict


class NotificationSettingsUpdateRequest(BaseModel):
    enabled: bool | None = None
    notification_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    timezone: str | None = Field(default=None, min_length=1)


class NotificationSettingsResponse(BaseModel):
    success: bool
    data: dict
