"""
Celery tasks for audio standup generation.

Implements scheduled audio standup generation for active squads.
"""
import logging
from datetime import datetime, timedelta
from uuid import UUID
from typing import Dict, Any, List
from celery import Task
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.db.base import SessionLocal
from app.services.guild_master_service import GuildMasterService
from app.services.notification_service import NotificationService
from app.models.squad import Squad

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


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.audio_standup.generate_standups")
def generate_standups(self) -> Dict[str, Any]:
    """
    Scheduled task to generate audio standups for active squads.
    
    Runs daily and checks which squads need a new standup (every 7 days).
    Generates audio standup and sends notifications to all squad members.
    
    Returns:
        Dictionary with generation results
    """
    try:
        logger.info("Starting audio standup generation task")
        
        # Get all active squads
        squads = self.db.query(Squad).filter(
            Squad.is_active == True
        ).all()
        
        guild_master_service = GuildMasterService(self.db)
        notification_service = NotificationService(self.db)
        
        generated_count = 0
        failed_count = 0
        skipped_count = 0
        
        for squad in squads:
            try:
                # Check if squad needs a new standup (7 days since last one)
                if squad.last_standup_at:
                    days_since_last = (datetime.utcnow() - squad.last_standup_at).days
                    if days_since_last < 7:
                        skipped_count += 1
                        continue
                
                logger.info(f"Generating audio standup for squad {squad.id}")
                
                # Generate audio standup
                audio_url = guild_master_service.generate_audio_standup(squad.id)
                
                # Update squad's last standup timestamp
                squad.last_standup_at = datetime.utcnow()
                self.db.commit()
                
                # Send notification to all squad members
                for membership in squad.memberships:
                    notification_service.send_notification(
                        user_id=membership.user_id,
                        notification_type="audio_standup",
                        title=f"New Audio Standup for {squad.guild.name}",
                        body="Your weekly squad update is ready!",
                        data={
                            "squad_id": str(squad.id),
                            "audio_url": audio_url,
                            "standup_date": datetime.utcnow().isoformat()
                        }
                    )
                
                generated_count += 1
                logger.info(f"Audio standup generated and notifications sent for squad {squad.id}")
                
            except Exception as e:
                logger.error(f"Failed to generate standup for squad {squad.id}: {str(e)}", exc_info=True)
                failed_count += 1
        
        logger.info(
            f"Audio standup generation completed: "
            f"generated={generated_count}, failed={failed_count}, skipped={skipped_count}"
        )
        
        return {
            "success": True,
            "generated_count": generated_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "total_squads": len(squads)
        }
        
    except Exception as e:
        logger.error(f"Audio standup generation task failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.audio_standup.generate_standup_for_squad")
def generate_standup_for_squad(self, squad_id: str) -> Dict[str, Any]:
    """
    Generate audio standup for a specific squad.
    
    Can be triggered manually or by other tasks.
    
    Args:
        squad_id: Squad UUID as string
        
    Returns:
        Dictionary with generation results
    """
    try:
        logger.info(f"Generating audio standup for squad {squad_id}")
        
        squad = self.db.query(Squad).filter(Squad.id == UUID(squad_id)).first()
        if not squad:
            raise ValueError(f"Squad {squad_id} not found")
        
        guild_master_service = GuildMasterService(self.db)
        notification_service = NotificationService(self.db)
        
        # Generate audio standup
        audio_url = guild_master_service.generate_audio_standup(UUID(squad_id))
        
        # Update squad's last standup timestamp
        squad.last_standup_at = datetime.utcnow()
        self.db.commit()
        
        # Send notification to all squad members
        for membership in squad.memberships:
            notification_service.send_notification(
                user_id=membership.user_id,
                notification_type="audio_standup",
                title=f"New Audio Standup for {squad.guild.name}",
                body="Your weekly squad update is ready!",
                data={
                    "squad_id": str(squad.id),
                    "audio_url": audio_url,
                    "standup_date": datetime.utcnow().isoformat()
                }
            )
        
        logger.info(f"Audio standup generated and notifications sent for squad {squad_id}")
        
        return {
            "success": True,
            "squad_id": squad_id,
            "audio_url": audio_url,
            "notifications_sent": len(squad.memberships)
        }
        
    except Exception as e:
        logger.error(f"Failed to generate standup for squad {squad_id}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
