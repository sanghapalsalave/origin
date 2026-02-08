"""
Pydantic schemas for notification API.

Defines request and response models for notifications, preferences, and devices.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.notification import NotificationType


# Device Schemas

class DeviceRegisterRequest(BaseModel):
    """Request schema for device registration."""
    device_token: str = Field(..., min_length=1)
    platform: str = Field(..., pattern="^(android|ios)$")


class DeviceResponse(BaseModel):
    """Response schema for device."""
    id: UUID
    user_id: UUID
    device_token: str
    platform: str
    registered_at: datetime
    
    class Config:
        from_attributes = True


# Notification Preferences Schemas

class NotificationPreferencesResponse(BaseModel):
    """Response schema for notification preferences."""
    user_id: UUID
    squad_mentions_enabled: bool
    syllabus_unlocks_enabled: bool
    peer_review_requests_enabled: bool
    audio_standups_enabled: bool
    levelup_notifications_enabled: bool
    guild_invitations_enabled: bool
    
    class Config:
        from_attributes = True


class NotificationPreferencesUpdate(BaseModel):
    """Request schema for updating notification preferences."""
    squad_mentions_enabled: Optional[bool] = None
    syllabus_unlocks_enabled: Optional[bool] = None
    peer_review_requests_enabled: Optional[bool] = None
    audio_standups_enabled: Optional[bool] = None
    levelup_notifications_enabled: Optional[bool] = None
    guild_invitations_enabled: Optional[bool] = None


# Notification Schemas

class NotificationResponse(BaseModel):
    """Response schema for notification."""
    id: UUID
    notification_type: NotificationType
    title: str
    body: str
    sent_at: datetime
    read_at: Optional[datetime]
    delivered: bool
    
    class Config:
        from_attributes = True
