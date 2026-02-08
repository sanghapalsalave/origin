"""
Notification API endpoints.

Provides endpoints for device registration, notification preferences, and history.

Implements Requirements 14.1-14.6.
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService
from app.schemas.notifications import (
    DeviceRegisterRequest,
    DeviceResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    NotificationResponse,
)

router = APIRouter()


@router.post("/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def register_device(
    request: DeviceRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Register a device for push notifications.
    
    Implements Requirement 14.1: Device registration for FCM/APNs.
    """
    service = NotificationService(db)
    
    try:
        device = service.register_device(
            user_id=current_user.id,
            device_token=request.device_token,
            platform=request.platform
        )
        
        return DeviceResponse(
            id=device.id,
            user_id=device.user_id,
            device_token=device.device_token,
            platform=device.platform,
            registered_at=device.registered_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/preferences", response_model=NotificationPreferencesResponse)
def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's notification preferences.
    
    Implements Requirement 14.5: Notification preferences.
    """
    service = NotificationService(db)
    
    try:
        preferences = service.get_preferences(current_user.id)
        
        return NotificationPreferencesResponse(
            user_id=preferences.user_id,
            squad_mentions_enabled=preferences.squad_mentions_enabled,
            syllabus_unlocks_enabled=preferences.syllabus_unlocks_enabled,
            peer_review_requests_enabled=preferences.peer_review_requests_enabled,
            audio_standups_enabled=preferences.audio_standups_enabled,
            levelup_notifications_enabled=preferences.levelup_notifications_enabled,
            guild_invitations_enabled=preferences.guild_invitations_enabled
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/preferences", response_model=NotificationPreferencesResponse)
def update_notification_preferences(
    request: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user's notification preferences.
    
    Implements Requirements 14.5, 14.6: Notification preference management.
    """
    service = NotificationService(db)
    
    preferences = service.update_preferences(
        user_id=current_user.id,
        squad_mentions_enabled=request.squad_mentions_enabled,
        syllabus_unlocks_enabled=request.syllabus_unlocks_enabled,
        peer_review_requests_enabled=request.peer_review_requests_enabled,
        audio_standups_enabled=request.audio_standups_enabled,
        levelup_notifications_enabled=request.levelup_notifications_enabled,
        guild_invitations_enabled=request.guild_invitations_enabled
    )
    
    return NotificationPreferencesResponse(
        user_id=preferences.user_id,
        squad_mentions_enabled=preferences.squad_mentions_enabled,
        syllabus_unlocks_enabled=preferences.syllabus_unlocks_enabled,
        peer_review_requests_enabled=preferences.peer_review_requests_enabled,
        audio_standups_enabled=preferences.audio_standups_enabled,
        levelup_notifications_enabled=preferences.levelup_notifications_enabled,
        guild_invitations_enabled=preferences.guild_invitations_enabled
    )


@router.get("/history", response_model=List[NotificationResponse])
def get_notification_history(
    limit: int = 50,
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get notification history for the current user.
    """
    service = NotificationService(db)
    
    notifications = service.get_notification_history(
        user_id=current_user.id,
        limit=limit,
        unread_only=unread_only
    )
    
    return [
        NotificationResponse(
            id=notif.id,
            notification_type=notif.notification_type,
            title=notif.title,
            body=notif.body,
            sent_at=notif.sent_at,
            read_at=notif.read_at,
            delivered=notif.delivered
        )
        for notif in notifications
    ]


@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notification_as_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a notification as read.
    """
    service = NotificationService(db)
    
    try:
        service.mark_as_read(notification_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
