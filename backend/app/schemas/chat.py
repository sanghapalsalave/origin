"""
Pydantic schemas for chat API.

Defines request and response models for chat channels, messages, and attachments.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.chat import MessageType


# Chat Channel Schemas

class ChatChannelResponse(BaseModel):
    """Response schema for chat channel."""
    id: UUID
    squad_id: UUID
    realtime_channel_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Message Schemas

class MessageCreate(BaseModel):
    """Request schema for creating a message."""
    content: str = Field(..., min_length=1, max_length=10000)
    message_type: MessageType = MessageType.TEXT


class MessageResponse(BaseModel):
    """Response schema for message."""
    id: UUID
    channel_id: UUID
    user_id: UUID
    content: str
    message_type: MessageType
    sent_at: datetime
    edited_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class MessageHistoryResponse(BaseModel):
    """Response schema for message history."""
    channel_id: UUID
    messages: List[MessageResponse]
    count: int


# Attachment Schemas

class AttachmentResponse(BaseModel):
    """Response schema for attachment."""
    id: UUID
    message_id: UUID
    filename: str
    file_size: int
    file_type: str
    storage_url: str
    uploaded_at: datetime
    
    class Config:
        from_attributes = True
