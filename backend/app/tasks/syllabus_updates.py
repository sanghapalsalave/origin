"""
Celery tasks for syllabus updates and pivots.

Implements scheduled syllabus updates and automatic pivot logic.
"""
import logging
from datetime import datetime, timedelta
from uuid import UUID
from typing import Dict, Any
from celery import Task
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.db.base import SessionLocal
from app.services.guild_master_service import GuildMasterService
from app.services.notification_service import NotificationService
from app.models.syllabus import Syllabus
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


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.syllabus_updates.update_syllabi")
def update_syllabi(self) -> Dict[str, Any]:
    """
    Scheduled task to update syllabi for active squads.
    
    Runs weekly and:
    1. Checks completion rates for the past 3 days
    2. Triggers pivot if completion < 60% for 3 consecutive days
    3. Updates syllabi that haven't been updated in 7+ days
    
    Returns:
        Dictionary with update results
    """
    try:
        logger.info("Starting syllabus update task")
        
        # Get all active squads with syllabi
        squads = self.db.query(Squad).filter(
            Squad.is_active == True,
            Squad.syllabus_id.isnot(None)
        ).all()
        
        guild_master_service = GuildMasterService(self.db)
        notification_service = NotificationService(self.db)
        
        updated_count = 0
        pivoted_count = 0
        failed_count = 0
        skipped_count = 0
        
        for squad in squads:
            try:
                syllabus = squad.syllabus
                if not syllabus:
                    continue
                
                # Check if pivot is needed (low completion for 3 consecutive days)
                needs_pivot = check_pivot_needed(self.db, squad.id)
                
                if needs_pivot:
                    logger.info(f"Pivoting syllabus for squad {squad.id} due to low completion")
                    
                    # Pivot syllabus
                    new_syllabus = guild_master_service.pivot_syllabus(squad.id)
                    
                    # Send notification to squad members
                    for membership in squad.memberships:
                        notification_service.send_notification(
                            user_id=membership.user_id,
                            notification_type="syllabus_pivot",
                            title="Syllabus Updated",
                            body="Your learning path has been adjusted based on squad progress",
                            data={
                                "squad_id": str(squad.id),
                                "syllabus_id": str(new_syllabus.id),
                                "reason": "low_completion"
                            }
                        )
                    
                    pivoted_count += 1
                    logger.info(f"Syllabus pivoted for squad {squad.id}")
                    
                # Check if regular update is needed (7+ days since last update)
                elif syllabus.updated_at:
                    days_since_update = (datetime.utcnow() - syllabus.updated_at).days
                    if days_since_update >= 7:
                        logger.info(f"Updating syllabus for squad {squad.id} (weekly update)")
                        
                        # Update syllabus
                        updated_syllabus = guild_master_service.update_syllabus(squad.id)
                        
                        # Send notification to squad members
                        for membership in squad.memberships:
                            notification_service.send_notification(
                                user_id=membership.user_id,
                                notification_type="syllabus_update",
                                title="Syllabus Refreshed",
                                body="Your learning content has been updated for the week",
                                data={
                                    "squad_id": str(squad.id),
                                    "syllabus_id": str(updated_syllabus.id)
                                }
                            )
                        
                        updated_count += 1
                        logger.info(f"Syllabus updated for squad {squad.id}")
                    else:
                        skipped_count += 1
                else:
                    skipped_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to update syllabus for squad {squad.id}: {str(e)}", exc_info=True)
                failed_count += 1
        
        logger.info(
            f"Syllabus update completed: "
            f"updated={updated_count}, pivoted={pivoted_count}, "
            f"failed={failed_count}, skipped={skipped_count}"
        )
        
        return {
            "success": True,
            "updated_count": updated_count,
            "pivoted_count": pivoted_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "total_squads": len(squads)
        }
        
    except Exception as e:
        logger.error(f"Syllabus update task failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


def check_pivot_needed(db: Session, squad_id: UUID) -> bool:
    """
    Check if syllabus pivot is needed based on completion rates.
    
    Pivot is triggered if completion rate < 60% for 3 consecutive days.
    
    Args:
        db: Database session
        squad_id: Squad UUID
        
    Returns:
        True if pivot is needed, False otherwise
    """
    from app.models.syllabus import TaskCompletion, SyllabusDay
    from sqlalchemy import func
    
    # Get completion rates for the past 3 days
    three_days_ago = datetime.utcnow() - timedelta(days=3)
    
    squad = db.query(Squad).filter(Squad.id == squad_id).first()
    if not squad or not squad.syllabus:
        return False
    
    # Get all tasks for the past 3 days
    recent_days = db.query(SyllabusDay).filter(
        SyllabusDay.syllabus_id == squad.syllabus_id,
        SyllabusDay.unlock_date >= three_days_ago,
        SyllabusDay.unlock_date <= datetime.utcnow()
    ).all()
    
    if len(recent_days) < 3:
        return False
    
    # Check completion rate for each day
    low_completion_days = 0
    
    for day in recent_days:
        total_tasks = len(day.tasks)
        if total_tasks == 0:
            continue
        
        # Count completed tasks
        completed_tasks = db.query(func.count(TaskCompletion.id)).filter(
            TaskCompletion.task_id.in_([task.id for task in day.tasks]),
            TaskCompletion.completed_at.isnot(None)
        ).scalar()
        
        completion_rate = (completed_tasks / total_tasks) * 100
        
        if completion_rate < 60:
            low_completion_days += 1
    
    return low_completion_days >= 3


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.syllabus_updates.pivot_syllabus_for_squad")
def pivot_syllabus_for_squad(self, squad_id: str) -> Dict[str, Any]:
    """
    Pivot syllabus for a specific squad.
    
    Can be triggered manually or by other tasks.
    
    Args:
        squad_id: Squad UUID as string
        
    Returns:
        Dictionary with pivot results
    """
    try:
        logger.info(f"Pivoting syllabus for squad {squad_id}")
        
        squad = self.db.query(Squad).filter(Squad.id == UUID(squad_id)).first()
        if not squad:
            raise ValueError(f"Squad {squad_id} not found")
        
        guild_master_service = GuildMasterService(self.db)
        notification_service = NotificationService(self.db)
        
        # Pivot syllabus
        new_syllabus = guild_master_service.pivot_syllabus(UUID(squad_id))
        
        # Send notification to squad members
        for membership in squad.memberships:
            notification_service.send_notification(
                user_id=membership.user_id,
                notification_type="syllabus_pivot",
                title="Syllabus Updated",
                body="Your learning path has been adjusted based on squad progress",
                data={
                    "squad_id": str(squad.id),
                    "syllabus_id": str(new_syllabus.id),
                    "reason": "manual_trigger"
                }
            )
        
        logger.info(f"Syllabus pivoted for squad {squad_id}")
        
        return {
            "success": True,
            "squad_id": squad_id,
            "syllabus_id": str(new_syllabus.id),
            "notifications_sent": len(squad.memberships)
        }
        
    except Exception as e:
        logger.error(f"Failed to pivot syllabus for squad {squad_id}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
