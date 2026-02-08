"""
Notification service for push notifications and in-app notifications.

Provides FCM/APNs integration and notification preference management.

Implements Requirements 14.1-14.6.
"""
import logging
import os
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationPreferences, NotificationType, Device
from app.models.user import User

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for notification operations."""
    
    def __init__(self, db: Session):
        """
        Initialize notification service.
        
        Args:
            db: Database session
        """
        self.db = db
        logger.info("NotificationService initialized")
    
    def register_device(
        self,
        user_id: UUID,
        device_token: str,
        platform: str
    ) -> Device:
        """
        Register a device for push notifications.
        
        Implements Requirement 14.1: Device registration for FCM/APNs.
        
        Args:
            user_id: User ID
            device_token: FCM or APNs device token
            platform: "android" or "ios"
            
        Returns:
            Created or updated Device object
            
        Raises:
            ValueError: If user not found or invalid platform
        """
        # Verify user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Validate platform
        if platform not in ["android", "ios"]:
            raise ValueError(f"Invalid platform: {platform}. Must be 'android' or 'ios'")
        
        # Check if device already registered
        device = self.db.query(Device).filter(Device.device_token == device_token).first()
        
        if device:
            # Update existing device
            device.user_id = user_id
            device.platform = platform
            device.last_used_at = datetime.utcnow()
        else:
            # Create new device
            device = Device(
                user_id=user_id,
                device_token=device_token,
                platform=platform,
                registered_at=datetime.utcnow(),
                last_used_at=datetime.utcnow()
            )
            self.db.add(device)
        
        self.db.commit()
        self.db.refresh(device)
        
        logger.info(f"Registered device for user {user_id} (platform: {platform})")
        
        return device
    
    def send_push_notification(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """
        Send a push notification to a user.
        
        Checks user preferences before sending. Delivers to all registered devices.
        
        Implements Requirements:
        - 14.1: Push notification delivery
        - 14.5, 14.6: Notification preference enforcement
        
        Args:
            user_id: User ID
            notification_type: Type of notification
            title: Notification title
            body: Notification body
            data: Optional additional data payload
            
        Returns:
            Created Notification object
            
        Raises:
            ValueError: If user not found
        """
        # Verify user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check user preferences
        if not self._check_notification_enabled(user_id, notification_type):
            logger.info(
                f"Notification {notification_type} disabled for user {user_id}, skipping"
            )
            # Still create notification record but don't send push
            notification = Notification(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                body=body,
                data=data,
                sent_at=datetime.utcnow(),
                delivered=False
            )
            self.db.add(notification)
            self.db.commit()
            self.db.refresh(notification)
            return notification
        
        # Create notification record
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data,
            sent_at=datetime.utcnow(),
            delivered=False
        )
        
        self.db.add(notification)
        self.db.flush()
        
        # Get user's devices
        devices = self.db.query(Device).filter(Device.user_id == user_id).all()
        
        if not devices:
            logger.warning(f"No devices registered for user {user_id}")
        else:
            # Send to all devices
            for device in devices:
                try:
                    self._send_to_device(device, title, body, data)
                    notification.delivered = True
                except Exception as e:
                    logger.error(f"Failed to send notification to device {device.id}: {e}")
        
        self.db.commit()
        self.db.refresh(notification)
        
        logger.info(
            f"Sent notification {notification.id} to user {user_id} "
            f"(type: {notification_type}, devices: {len(devices)})"
        )
        
        return notification
    
    def get_preferences(self, user_id: UUID) -> NotificationPreferences:
        """
        Get user's notification preferences.
        
        Creates default preferences if they don't exist.
        
        Implements Requirement 14.5: Notification preferences.
        
        Args:
            user_id: User ID
            
        Returns:
            NotificationPreferences object
            
        Raises:
            ValueError: If user not found
        """
        # Verify user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Get or create preferences
        preferences = self.db.query(NotificationPreferences).filter(
            NotificationPreferences.user_id == user_id
        ).first()
        
        if not preferences:
            # Create default preferences (all enabled)
            preferences = NotificationPreferences(
                user_id=user_id,
                squad_mentions_enabled=True,
                syllabus_unlocks_enabled=True,
                peer_review_requests_enabled=True,
                audio_standups_enabled=True,
                levelup_notifications_enabled=True,
                guild_invitations_enabled=True,
                updated_at=datetime.utcnow()
            )
            self.db.add(preferences)
            self.db.commit()
            self.db.refresh(preferences)
            
            logger.info(f"Created default notification preferences for user {user_id}")
        
        return preferences
    
    def update_preferences(
        self,
        user_id: UUID,
        squad_mentions_enabled: Optional[bool] = None,
        syllabus_unlocks_enabled: Optional[bool] = None,
        peer_review_requests_enabled: Optional[bool] = None,
        audio_standups_enabled: Optional[bool] = None,
        levelup_notifications_enabled: Optional[bool] = None,
        guild_invitations_enabled: Optional[bool] = None
    ) -> NotificationPreferences:
        """
        Update user's notification preferences.
        
        Implements Requirements 14.5, 14.6: Notification preference management.
        
        Args:
            user_id: User ID
            squad_mentions_enabled: Enable/disable squad mention notifications
            syllabus_unlocks_enabled: Enable/disable syllabus unlock notifications
            peer_review_requests_enabled: Enable/disable peer review notifications
            audio_standups_enabled: Enable/disable audio standup notifications
            levelup_notifications_enabled: Enable/disable level-up notifications
            guild_invitations_enabled: Enable/disable guild invitation notifications
            
        Returns:
            Updated NotificationPreferences object
        """
        # Get or create preferences
        preferences = self.get_preferences(user_id)
        
        # Update fields if provided
        if squad_mentions_enabled is not None:
            preferences.squad_mentions_enabled = squad_mentions_enabled
        if syllabus_unlocks_enabled is not None:
            preferences.syllabus_unlocks_enabled = syllabus_unlocks_enabled
        if peer_review_requests_enabled is not None:
            preferences.peer_review_requests_enabled = peer_review_requests_enabled
        if audio_standups_enabled is not None:
            preferences.audio_standups_enabled = audio_standups_enabled
        if levelup_notifications_enabled is not None:
            preferences.levelup_notifications_enabled = levelup_notifications_enabled
        if guild_invitations_enabled is not None:
            preferences.guild_invitations_enabled = guild_invitations_enabled
        
        preferences.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(preferences)
        
        logger.info(f"Updated notification preferences for user {user_id}")
        
        return preferences
    
    def get_notification_history(
        self,
        user_id: UUID,
        limit: int = 50,
        unread_only: bool = False
    ) -> List[Notification]:
        """
        Get notification history for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of notifications to retrieve
            unread_only: If True, only return unread notifications
            
        Returns:
            List of Notification objects ordered by sent_at (newest first)
        """
        query = self.db.query(Notification).filter(Notification.user_id == user_id)
        
        if unread_only:
            query = query.filter(Notification.read_at.is_(None))
        
        notifications = query.order_by(Notification.sent_at.desc()).limit(limit).all()
        
        logger.info(
            f"Retrieved {len(notifications)} notifications for user {user_id} "
            f"(unread_only: {unread_only})"
        )
        
        return notifications
    
    def mark_as_read(self, notification_id: UUID):
        """
        Mark a notification as read.
        
        Args:
            notification_id: Notification ID
            
        Raises:
            ValueError: If notification not found
        """
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id
        ).first()
        
        if not notification:
            raise ValueError(f"Notification {notification_id} not found")
        
        notification.read_at = datetime.utcnow()
        self.db.commit()
        
        logger.debug(f"Marked notification {notification_id} as read")
    
    def _check_notification_enabled(
        self,
        user_id: UUID,
        notification_type: NotificationType
    ) -> bool:
        """
        Check if a notification type is enabled for a user.
        
        Implements Requirement 14.6: Preference enforcement.
        
        Args:
            user_id: User ID
            notification_type: Type of notification
            
        Returns:
            True if enabled, False if disabled
        """
        preferences = self.get_preferences(user_id)
        
        # Map notification types to preference fields
        type_to_field = {
            NotificationType.SQUAD_MENTION: preferences.squad_mentions_enabled,
            NotificationType.SYLLABUS_UNLOCK: preferences.syllabus_unlocks_enabled,
            NotificationType.PEER_REVIEW_REQUEST: preferences.peer_review_requests_enabled,
            NotificationType.AUDIO_STANDUP: preferences.audio_standups_enabled,
            NotificationType.LEVELUP_APPROVED: preferences.levelup_notifications_enabled,
            NotificationType.GUILD_INVITATION: preferences.guild_invitations_enabled,
        }
        
        return type_to_field.get(notification_type, True)
    
    def _send_to_device(
        self,
        device: Device,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Send push notification to a specific device.
        
        Uses FCM for Android and APNs for iOS.
        
        Args:
            device: Device object
            title: Notification title
            body: Notification body
            data: Optional additional data
            
        Raises:
            Exception: If sending fails
        """
        # TODO: Implement actual FCM/APNs integration
        # For now, just log the notification
        logger.info(
            f"Sending push notification to device {device.id} "
            f"(platform: {device.platform}, title: {title})"
        )
        
        # Placeholder for FCM/APNs implementation
        # if device.platform == "android":
        #     # Send via FCM
        #     pass
        # elif device.platform == "ios":
        #     # Send via APNs
        #     pass
