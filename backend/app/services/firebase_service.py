"""
Firebase service for real-time messaging.

Provides Firebase Realtime Database integration for squad chat functionality.

Implements Requirement 9.1: Real-time squad chat.
"""
import logging
import os
from typing import Optional, Dict, Any
import firebase_admin
from firebase_admin import credentials, db

logger = logging.getLogger(__name__)


class FirebaseService:
    """Service for Firebase Realtime Database operations."""
    
    _instance: Optional['FirebaseService'] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern to ensure single Firebase app instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Firebase service."""
        if not self._initialized:
            self._initialize_firebase()
            FirebaseService._initialized = True
    
    def _initialize_firebase(self):
        """
        Initialize Firebase Admin SDK.
        
        Requires environment variables:
        - FIREBASE_CREDENTIALS_PATH: Path to Firebase service account JSON
        - FIREBASE_DATABASE_URL: Firebase Realtime Database URL
        """
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                credentials_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
                database_url = os.getenv('FIREBASE_DATABASE_URL')
                
                if not credentials_path or not database_url:
                    logger.warning(
                        "Firebase credentials not configured. "
                        "Set FIREBASE_CREDENTIALS_PATH and FIREBASE_DATABASE_URL environment variables."
                    )
                    return
                
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': database_url
                })
                
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                logger.info("Firebase Admin SDK already initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise
    
    def create_channel(self, channel_id: str, initial_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new chat channel in Firebase.
        
        Args:
            channel_id: Unique identifier for the channel (typically squad ID)
            initial_data: Optional initial data for the channel
            
        Returns:
            Channel ID (Firebase reference path)
        """
        try:
            ref = db.reference(f'channels/{channel_id}')
            
            # Set initial channel data
            channel_data = initial_data or {
                'created_at': db.ServerValue.TIMESTAMP,
                'message_count': 0
            }
            
            ref.set(channel_data)
            
            logger.info(f"Created Firebase channel: {channel_id}")
            return channel_id
        except Exception as e:
            logger.error(f"Failed to create Firebase channel {channel_id}: {e}")
            raise
    
    def send_message(
        self,
        channel_id: str,
        message_id: str,
        message_data: Dict[str, Any]
    ) -> str:
        """
        Send a message to a chat channel.
        
        Args:
            channel_id: Channel identifier
            message_id: Unique message identifier
            message_data: Message data including content, sender, timestamp, etc.
            
        Returns:
            Message ID
        """
        try:
            ref = db.reference(f'channels/{channel_id}/messages/{message_id}')
            ref.set(message_data)
            
            # Increment message count
            channel_ref = db.reference(f'channels/{channel_id}')
            channel_ref.update({
                'message_count': db.ServerValue.increment(1),
                'last_message_at': db.ServerValue.TIMESTAMP
            })
            
            logger.info(f"Sent message {message_id} to channel {channel_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to send message to channel {channel_id}: {e}")
            raise
    
    def get_messages(
        self,
        channel_id: str,
        limit: int = 50,
        before_timestamp: Optional[int] = None
    ) -> list:
        """
        Retrieve messages from a chat channel.
        
        Args:
            channel_id: Channel identifier
            limit: Maximum number of messages to retrieve
            before_timestamp: Optional timestamp to get messages before (for pagination)
            
        Returns:
            List of message dictionaries
        """
        try:
            ref = db.reference(f'channels/{channel_id}/messages')
            
            # Query messages ordered by timestamp
            query = ref.order_by_child('timestamp')
            
            if before_timestamp:
                query = query.end_at(before_timestamp)
            
            query = query.limit_to_last(limit)
            
            messages = query.get() or {}
            
            # Convert to list and sort by timestamp
            message_list = [
                {'id': msg_id, **msg_data}
                for msg_id, msg_data in messages.items()
            ]
            message_list.sort(key=lambda x: x.get('timestamp', 0))
            
            logger.info(f"Retrieved {len(message_list)} messages from channel {channel_id}")
            return message_list
        except Exception as e:
            logger.error(f"Failed to retrieve messages from channel {channel_id}: {e}")
            raise
    
    def delete_channel(self, channel_id: str):
        """
        Delete a chat channel and all its messages.
        
        Args:
            channel_id: Channel identifier
        """
        try:
            ref = db.reference(f'channels/{channel_id}')
            ref.delete()
            
            logger.info(f"Deleted Firebase channel: {channel_id}")
        except Exception as e:
            logger.error(f"Failed to delete Firebase channel {channel_id}: {e}")
            raise
    
    def update_user_presence(self, channel_id: str, user_id: str, online: bool):
        """
        Update user's online/offline presence in a channel.
        
        Args:
            channel_id: Channel identifier
            user_id: User identifier
            online: True if user is online, False if offline
        """
        try:
            ref = db.reference(f'channels/{channel_id}/presence/{user_id}')
            ref.set({
                'online': online,
                'last_seen': db.ServerValue.TIMESTAMP
            })
            
            logger.debug(f"Updated presence for user {user_id} in channel {channel_id}: {online}")
        except Exception as e:
            logger.error(f"Failed to update presence for user {user_id}: {e}")
            raise
    
    def mark_message_as_read(self, channel_id: str, user_id: str, message_id: str):
        """
        Mark a message as read by a user.
        
        Args:
            channel_id: Channel identifier
            user_id: User identifier
            message_id: Message identifier
        """
        try:
            ref = db.reference(f'channels/{channel_id}/read_receipts/{user_id}')
            ref.set({
                'last_read_message_id': message_id,
                'timestamp': db.ServerValue.TIMESTAMP
            })
            
            logger.debug(f"Marked message {message_id} as read by user {user_id}")
        except Exception as e:
            logger.error(f"Failed to mark message as read: {e}")
            raise
