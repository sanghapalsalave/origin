"""
Chat data models for real-time messaging.

Implements Requirement 9.1: Real-time squad chat.
"""
from datetime import datetime
from enum import Enum
from uuid import uuid4
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class MessageType(str, Enum):
    """Type of chat message."""
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    FILE = "file"


class ChatChannel(Base):
    """
    Chat channel model for squad communication.
    
    Each squad has a dedicated chat channel for real-time messaging.
    The actual messages are stored in Firebase/Supabase for real-time sync,
    while this model stores metadata and references.
    
    Implements Requirement 9.1: Squad chat channel creation.
    """
    __tablename__ = "chat_channels"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    squad_id = Column(UUID(as_uuid=True), ForeignKey("squads.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Firebase/Supabase reference
    realtime_channel_id = Column(String, nullable=False, unique=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    squad = relationship("Squad", backref="chat_channel")
    
    def __repr__(self) -> str:
        return f"<ChatChannel(id={self.id}, squad_id={self.squad_id}, realtime_channel_id={self.realtime_channel_id})>"


class Message(Base):
    """
    Message model for chat messages.
    
    Stores metadata about messages sent in chat channels.
    The actual message content is stored in Firebase/Supabase for real-time delivery,
    while this model provides a persistent record for history and search.
    
    Implements Requirements:
    - 9.2: Message delivery within 2 seconds
    - 9.3: Offline message queueing
    - 9.4: Support for text, code, images, files
    - 9.5: User mentions with notifications
    """
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("chat_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Message content
    content = Column(Text, nullable=False)
    message_type = Column(SQLEnum(MessageType), nullable=False, default=MessageType.TEXT)
    
    # Metadata
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    edited_at = Column(DateTime, nullable=True)
    
    # Firebase/Supabase reference
    realtime_message_id = Column(String, nullable=False)
    
    # Relationships
    channel = relationship("ChatChannel", backref="messages")
    user = relationship("User", backref="messages_sent")
    attachments = relationship("Attachment", back_populates="message", cascade="all, delete-orphan")
    mentions = relationship("MessageMention", back_populates="message", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, channel_id={self.channel_id}, user_id={self.user_id}, type={self.message_type})>"


class Attachment(Base):
    """
    Attachment model for file attachments in messages.
    
    Supports images, files, and other attachments up to 10MB.
    Files are stored in cloud storage (AWS S3/GCS) with CDN delivery.
    
    Implements Requirement 9.4: File attachment support.
    """
    __tablename__ = "attachments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # File metadata
    filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_type = Column(String, nullable=False)  # MIME type
    
    # Storage
    storage_url = Column(String, nullable=False)  # Cloud storage URL
    
    # Metadata
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    message = relationship("Message", back_populates="attachments")
    
    def __repr__(self) -> str:
        return f"<Attachment(id={self.id}, filename={self.filename}, size={self.file_size})>"


class MessageMention(Base):
    """
    Message mention model for tracking user mentions in messages.
    
    When a user is mentioned in a message, a push notification is sent.
    
    Implements Requirement 9.5: User mentions with notifications.
    """
    __tablename__ = "message_mentions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    mentioned_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    message = relationship("Message", back_populates="mentions")
    mentioned_user = relationship("User", backref="mentions_received")
    
    def __repr__(self) -> str:
        return f"<MessageMention(id={self.id}, message_id={self.message_id}, mentioned_user_id={self.mentioned_user_id})>"
