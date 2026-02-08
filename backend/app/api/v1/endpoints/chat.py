"""
Chat API endpoints.

Provides endpoints for real-time messaging, chat history, and file attachments.

Implements Requirements 9.1-9.6.
"""
from typing import List
from uuid import UUID
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.chat_service import ChatService
from app.schemas.chat import (
    ChatChannelResponse,
    MessageCreate,
    MessageResponse,
    MessageHistoryResponse,
    AttachmentResponse,
)

router = APIRouter()


@router.post("/channels", response_model=ChatChannelResponse, status_code=status.HTTP_201_CREATED)
def create_chat_channel(
    squad_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a chat channel for a squad.
    
    Implements Requirement 9.1: Squad chat channel creation.
    """
    service = ChatService(db)
    
    try:
        channel = service.create_squad_channel(squad_id)
        return ChatChannelResponse(
            id=channel.id,
            squad_id=channel.squad_id,
            realtime_channel_id=channel.realtime_channel_id,
            created_at=channel.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/channels/{channel_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    channel_id: UUID,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message to a chat channel.
    
    Implements Requirements:
    - 9.2: Message delivery within 2 seconds
    - 9.4: Support for text, code, images, files
    - 9.5: User mentions with notifications
    """
    service = ChatService(db)
    
    try:
        msg = service.send_message(
            channel_id=channel_id,
            user_id=current_user.id,
            content=message.content,
            message_type=message.message_type
        )
        
        return MessageResponse(
            id=msg.id,
            channel_id=msg.channel_id,
            user_id=msg.user_id,
            content=msg.content,
            message_type=msg.message_type,
            sent_at=msg.sent_at,
            edited_at=msg.edited_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/channels/{channel_id}/history", response_model=MessageHistoryResponse)
def get_message_history(
    channel_id: UUID,
    limit: int = 50,
    before: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Retrieve chat history with pagination.
    
    Implements Requirement 9.6: Chat history persistence.
    """
    service = ChatService(db)
    
    messages = service.get_message_history(channel_id, limit, before)
    
    return MessageHistoryResponse(
        channel_id=channel_id,
        messages=[
            MessageResponse(
                id=msg.id,
                channel_id=msg.channel_id,
                user_id=msg.user_id,
                content=msg.content,
                message_type=msg.message_type,
                sent_at=msg.sent_at,
                edited_at=msg.edited_at
            )
            for msg in messages
        ],
        count=len(messages)
    )


@router.post("/channels/{channel_id}/attachments", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    channel_id: UUID,
    message_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a file attachment for a message.
    
    Implements Requirement 9.4: File attachment support (10MB limit).
    """
    service = ChatService(db)
    
    # Read file
    file_content = await file.read()
    file_size = len(file_content)
    
    # TODO: Upload to cloud storage (AWS S3/GCS) and get URL
    # For now, use placeholder URL
    storage_url = f"https://storage.example.com/attachments/{message_id}/{file.filename}"
    
    try:
        attachment = service.upload_attachment(
            message_id=message_id,
            filename=file.filename,
            file_size=file_size,
            file_type=file.content_type,
            storage_url=storage_url
        )
        
        return AttachmentResponse(
            id=attachment.id,
            message_id=attachment.message_id,
            filename=attachment.filename,
            file_size=attachment.file_size,
            file_type=attachment.file_type,
            storage_url=attachment.storage_url,
            uploaded_at=attachment.uploaded_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/channels/{channel_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_messages_as_read(
    channel_id: UUID,
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark messages as read up to a specific message.
    """
    service = ChatService(db)
    
    try:
        service.mark_as_read(channel_id, current_user.id, message_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/channels/{channel_id}/presence", status_code=status.HTTP_204_NO_CONTENT)
def update_presence(
    channel_id: UUID,
    online: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user's online/offline presence in a channel.
    """
    service = ChatService(db)
    
    try:
        service.update_user_presence(channel_id, current_user.id, online)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
