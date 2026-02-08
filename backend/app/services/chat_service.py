"""
Chat service for real-time messaging.

Provides squad chat functionality with Firebase integration.

Implements Requirements 9.1-9.6.
"""
import logging
import re
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.chat import ChatChannel, Message, MessageType, Attachment, MessageMention
from app.models.squad import Squad
from app.models.user import User
from app.services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)


class ChatService:
    """Service for chat operations."""
    
    def __init__(self, db: Session):
        """
        Initialize chat service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.firebase = FirebaseService()
        logger.info("ChatService initialized")
    
    def create_squad_channel(self, squad_id: UUID) -> ChatChannel:
        """
        Create a dedicated chat channel for a squad.
        
        Creates both a database record and a Firebase Realtime Database channel.
        
        Implements Requirement 9.1: Squad chat channel creation.
        
        Args:
            squad_id: Squad ID
            
        Returns:
            Created ChatChannel object
            
        Raises:
            ValueError: If squad not found or channel already exists
        """
        # Verify squad exists
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()
        if not squad:
            raise ValueError(f"Squad {squad_id} not found")
        
        # Check if channel already exists
        existing_channel = self.db.query(ChatChannel).filter(
            ChatChannel.squad_id == squad_id
        ).first()
        
        if existing_channel:
            raise ValueError(f"Chat channel already exists for squad {squad_id}")
        
        # Create Firebase channel
        realtime_channel_id = f"squad_{squad_id}"
        self.firebase.create_channel(realtime_channel_id, {
            'squad_id': str(squad_id),
            'squad_name': squad.name,
            'created_at': datetime.utcnow().isoformat()
        })
        
        # Create database record
        channel = ChatChannel(
            squad_id=squad_id,
            realtime_channel_id=realtime_channel_id,
            created_at=datetime.utcnow()
        )
        
        self.db.add(channel)
        self.db.commit()
        self.db.refresh(channel)
        
        logger.info(f"Created chat channel {channel.id} for squad {squad_id}")
        
        return channel
    
    def send_message(
        self,
        channel_id: UUID,
        user_id: UUID,
        content: str,
        message_type: MessageType = MessageType.TEXT
    ) -> Message:
        """
        Send a message to a chat channel.
        
        Delivers message to Firebase for real-time sync and stores in database
        for history. Processes mentions and sends notifications.
        
        Implements Requirements:
        - 9.2: Message delivery within 2 seconds
        - 9.4: Support for text, code, images, files
        - 9.5: User mentions with notifications
        
        Args:
            channel_id: Chat channel ID
            user_id: Sender user ID
            content: Message content
            message_type: Type of message (text, code, image, file)
            
        Returns:
            Created Message object
            
        Raises:
            ValueError: If channel or user not found
        """
        # Verify channel exists
        channel = self.db.query(ChatChannel).filter(ChatChannel.id == channel_id).first()
        if not channel:
            raise ValueError(f"Chat channel {channel_id} not found")
        
        # Verify user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Create message record
        message = Message(
            channel_id=channel_id,
            user_id=user_id,
            content=content,
            message_type=message_type,
            sent_at=datetime.utcnow(),
            realtime_message_id=f"msg_{datetime.utcnow().timestamp()}"
        )
        
        self.db.add(message)
        self.db.flush()
        
        # Send to Firebase for real-time delivery
        firebase_message_data = {
            'id': str(message.id),
            'user_id': str(user_id),
            'content': content,
            'message_type': message_type.value,
            'timestamp': int(datetime.utcnow().timestamp() * 1000),
            'user_name': user.email  # TODO: Use display_name when available
        }
        
        self.firebase.send_message(
            channel.realtime_channel_id,
            message.realtime_message_id,
            firebase_message_data
        )
        
        # Process mentions
        mentioned_users = self._extract_mentions(content)
        for mentioned_user_id in mentioned_users:
            self._create_mention(message.id, mentioned_user_id)
        
        self.db.commit()
        self.db.refresh(message)
        
        logger.info(
            f"Sent message {message.id} to channel {channel_id} "
            f"(type: {message_type}, mentions: {len(mentioned_users)})"
        )
        
        return message
    
    def get_message_history(
        self,
        channel_id: UUID,
        limit: int = 50,
        before: Optional[datetime] = None
    ) -> List[Message]:
        """
        Retrieve chat history with pagination.
        
        Implements Requirement 9.6: Chat history persistence.
        
        Args:
            channel_id: Chat channel ID
            limit: Maximum number of messages to retrieve
            before: Optional datetime to get messages before (for pagination)
            
        Returns:
            List of Message objects ordered by sent_at (newest first)
        """
        query = self.db.query(Message).filter(Message.channel_id == channel_id)
        
        if before:
            query = query.filter(Message.sent_at < before)
        
        messages = query.order_by(Message.sent_at.desc()).limit(limit).all()
        
        logger.info(f"Retrieved {len(messages)} messages from channel {channel_id}")
        
        return messages
    
    def upload_attachment(
        self,
        message_id: UUID,
        filename: str,
        file_size: int,
        file_type: str,
        storage_url: str
    ) -> Attachment:
        """
        Create attachment record for a message.
        
        Implements Requirement 9.4: File attachment support.
        
        Args:
            message_id: Message ID
            filename: Original filename
            file_size: File size in bytes
            file_type: MIME type
            storage_url: Cloud storage URL
            
        Returns:
            Created Attachment object
            
        Raises:
            ValueError: If message not found or file size exceeds limit
        """
        # Verify message exists
        message = self.db.query(Message).filter(Message.id == message_id).first()
        if not message:
            raise ValueError(f"Message {message_id} not found")
        
        # Validate file size (10MB limit)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File size {file_size} exceeds maximum {MAX_FILE_SIZE} bytes")
        
        # Create attachment record
        attachment = Attachment(
            message_id=message_id,
            filename=filename,
            file_size=file_size,
            file_type=file_type,
            storage_url=storage_url,
            uploaded_at=datetime.utcnow()
        )
        
        self.db.add(attachment)
        self.db.commit()
        self.db.refresh(attachment)
        
        logger.info(
            f"Created attachment {attachment.id} for message {message_id} "
            f"(filename: {filename}, size: {file_size})"
        )
        
        return attachment
    
    def mark_as_read(self, channel_id: UUID, user_id: UUID, message_id: UUID):
        """
        Mark messages as read by a user.
        
        Updates Firebase read receipts for real-time sync.
        
        Args:
            channel_id: Chat channel ID
            user_id: User ID
            message_id: Last read message ID
        """
        # Verify channel exists
        channel = self.db.query(ChatChannel).filter(ChatChannel.id == channel_id).first()
        if not channel:
            raise ValueError(f"Chat channel {channel_id} not found")
        
        # Update Firebase read receipt
        self.firebase.mark_message_as_read(
            channel.realtime_channel_id,
            str(user_id),
            str(message_id)
        )
        
        logger.debug(f"Marked message {message_id} as read by user {user_id}")
    
    def _extract_mentions(self, content: str) -> List[UUID]:
        """
        Extract user mentions from message content.
        
        Mentions are in the format @user_id or @username.
        
        Args:
            content: Message content
            
        Returns:
            List of mentioned user IDs
        """
        # Extract @mentions (assuming format @user_id)
        mention_pattern = r'@([a-f0-9\-]{36})'  # UUID pattern
        matches = re.findall(mention_pattern, content)
        
        mentioned_user_ids = []
        for match in matches:
            try:
                user_id = UUID(match)
                # Verify user exists
                user = self.db.query(User).filter(User.id == user_id).first()
                if user:
                    mentioned_user_ids.append(user_id)
            except ValueError:
                logger.warning(f"Invalid UUID in mention: {match}")
                continue
        
        return mentioned_user_ids
    
    def _create_mention(self, message_id: UUID, mentioned_user_id: UUID):
        """
        Create a mention record and send notification.
        
        Implements Requirement 9.5: Mention notification trigger.
        
        Args:
            message_id: Message ID
            mentioned_user_id: Mentioned user ID
        """
        # Create mention record
        mention = MessageMention(
            message_id=message_id,
            mentioned_user_id=mentioned_user_id,
            created_at=datetime.utcnow()
        )
        
        self.db.add(mention)
        
        # TODO: Send push notification to mentioned user
        # This will be implemented when notification service is ready
        logger.info(f"Created mention for user {mentioned_user_id} in message {message_id}")
    
    def update_user_presence(self, channel_id: UUID, user_id: UUID, online: bool):
        """
        Update user's online/offline presence in a channel.
        
        Args:
            channel_id: Chat channel ID
            user_id: User ID
            online: True if user is online, False if offline
        """
        # Verify channel exists
        channel = self.db.query(ChatChannel).filter(ChatChannel.id == channel_id).first()
        if not channel:
            raise ValueError(f"Chat channel {channel_id} not found")
        
        # Update Firebase presence
        self.firebase.update_user_presence(
            channel.realtime_channel_id,
            str(user_id),
            online
        )
        
        logger.debug(f"Updated presence for user {user_id} in channel {channel_id}: {online}")
