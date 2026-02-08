"""
Notification data models.

Implements Requirements 14.1-14.6.
"""
from datetime import datetime
from enum import Enum
from uuid import uuid4
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class NotificationType(str, Enum):
    """Type of notification."""
    SQUAD_MENTION = "squad_mention"
    SYLLABUS_UNLOCK = "syllabus_unlock"
    PEER_REVIEW_REQUEST = "peer_review_request"
    AUDIO_STANDUP = "audio_standup"
    LEVELUP_APPROVED = "levelup_approved"
    GUILD_INVITATION = "guild_invitation"


class Notification(Base):
    """
    Notification model for push notifications and in-app notifications.
    
    Implements Requirements 14.1-14.4.
    """
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Notification content
    notification_type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)  # Additional payload
    
    # Delivery status
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    read_at = Column(DateTime, nullable=True)
    delivered = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user = relationship("User", backref="notifications")
    
    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, type={self.notification_type}, user_id={self.user_id})>"


class NotificationPreferences(Base):
    """
    User notification preferences.
    
    Allows users to configure which types of notifications they want to receive.
    
    Implements Requirements 14.5, 14.6.
    """
    __tablename__ = "notification_preferences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Preference flags (default: all enabled)
    squad_mentions_enabled = Column(Boolean, default=True, nullable=False)
    syllabus_unlocks_enabled = Column(Boolean, default=True, nullable=False)
    peer_review_requests_enabled = Column(Boolean, default=True, nullable=False)
    audio_standups_enabled = Column(Boolean, default=True, nullable=False)
    levelup_notifications_enabled = Column(Boolean, default=True, nullable=False)
    guild_invitations_enabled = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="notification_preferences")
    
    def __repr__(self) -> str:
        return f"<NotificationPreferences(id={self.id}, user_id={self.user_id})>"


class Device(Base):
    """
    Device model for push notification tokens.
    
    Stores device tokens for Firebase Cloud Messaging (FCM) and
    Apple Push Notification Service (APNs).
    
    Implements Requirement 14.1.
    """
    __tablename__ = "devices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Device information
    device_token = Column(String, nullable=False, unique=True)
    platform = Column(String, nullable=False)  # "android" or "ios"
    
    # Metadata
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="devices")
    
    def __repr__(self) -> str:
        return f"<Device(id={self.id}, user_id={self.user_id}, platform={self.platform})>"
