"""
Celery tasks for notification delivery.

Implements batched notification delivery for efficiency.
"""
import logging
from datetime import datetime, timedelta
from uuid import UUID
from typing import Dict, Any, List
from celery import Task
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.db.base import SessionLocal
from app.services.notification_service import NotificationService
from app.models.notification import Notification

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session management."""
    _db = None
    
    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.notifications.send_batch_notifications")
def send_batch_notifications(self) -> Dict[str, Any]:
    """
    Scheduled task to send batched push notifications.
    
    Runs every 5 minutes and:
    1. Gets all pending notifications
    2. Batches them by user for efficiency
    3. Sends push notifications via FCM/APNs
    4. Marks notifications as sent
    
    Returns:
        Dictionary with delivery results
    """
    try:
        logger.info("Starting batch notification delivery task")
        
        # Get all pending notifications (not sent yet)
        pending_notifications = self.db.query(Notification).filter(
            Notification.sent_at.is_(None),
            Notification.created_at >= datetime.utcnow() - timedelta(hours=24)  # Only last 24 hours
        ).order_by(Notification.created_at).limit(1000).all()  # Batch limit
        
        if not pending_notifications:
            logger.info("No pending notifications to send")
            return {
                "success": True,
                "sent_count": 0,
                "failed_count": 0
            }
        
        logger.info(f"Found {len(pending_notifications)} pending notifications")
        
        notification_service = NotificationService(self.db)
        
        sent_count = 0
        failed_count = 0
        
        # Group notifications by user for batching
        user_notifications: Dict[UUID, List[Notification]] = {}
        for notification in pending_notifications:
            if notification.user_id not in user_notifications:
                user_notifications[notification.user_id] = []
            user_notifications[notification.user_id].append(notification)
        
        # Send notifications for each user
        for user_id, notifications in user_notifications.items():
            try:
                # Send most recent notification (or batch if supported)
                # For now, send the most recent one to avoid spam
                latest_notification = notifications[-1]
                
                success = notification_service.send_push_notification(
                    user_id=user_id,
                    notification_type=latest_notification.notification_type,
                    title=latest_notification.title,
                    body=latest_notification.body,
                    data=latest_notification.data or {}
                )
                
                if success:
                    # Mark all notifications for this user as sent
                    for notification in notifications:
                        notification.sent_at = datetime.utcnow()
                    self.db.commit()
                    sent_count += len(notifications)
                    logger.info(f"Sent {len(notifications)} notifications to user {user_id}")
                else:
                    failed_count += len(notifications)
                    logger.warning(f"Failed to send notifications to user {user_id}")
                    
            except Exception as e:
                logger.error(f"Failed to send notifications to user {user_id}: {str(e)}", exc_info=True)
                failed_count += len(notifications)
        
        logger.info(
            f"Batch notification delivery completed: "
            f"sent={sent_count}, failed={failed_count}"
        )
        
        return {
            "success": True,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "total_users": len(user_notifications)
        }
        
    except Exception as e:
        logger.error(f"Batch notification delivery task failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.notifications.send_notification_async")
def send_notification_async(
    self,
    user_id: str,
    notification_type: str,
    title: str,
    body: str,
    data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Asynchronous task to send a single notification.
    
    Used for high-priority notifications that need immediate delivery.
    
    Args:
        user_id: User UUID as string
        notification_type: Type of notification
        title: Notification title
        body: Notification body
        data: Optional notification data
        
    Returns:
        Dictionary with delivery results
    """
    try:
        logger.info(f"Sending async notification to user {user_id}: {notification_type}")
        
        notification_service = NotificationService(self.db)
        
        # Create notification record
        notification = notification_service.send_notification(
            user_id=UUID(user_id),
            notification_type=notification_type,
            title=title,
            body=body,
            data=data or {}
        )
        
        # Send push notification immediately
        success = notification_service.send_push_notification(
            user_id=UUID(user_id),
            notification_type=notification_type,
            title=title,
            body=body,
            data=data or {}
        )
        
        if success:
            notification.sent_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Async notification sent to user {user_id}")
        else:
            logger.warning(f"Failed to send async notification to user {user_id}")
        
        return {
            "success": success,
            "notification_id": str(notification.id),
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Failed to send async notification to user {user_id}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.notifications.cleanup_old_notifications")
def cleanup_old_notifications(self) -> Dict[str, Any]:
    """
    Cleanup task to remove old notifications.
    
    Removes notifications older than 30 days to keep database clean.
    
    Returns:
        Dictionary with cleanup results
    """
    try:
        logger.info("Starting notification cleanup task")
        
        # Delete notifications older than 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        deleted_count = self.db.query(Notification).filter(
            Notification.created_at < thirty_days_ago
        ).delete()
        
        self.db.commit()
        
        logger.info(f"Notification cleanup completed: deleted={deleted_count}")
        
        return {
            "success": True,
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Notification cleanup task failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
