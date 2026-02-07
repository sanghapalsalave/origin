"""
Learning Velocity Tracking Service

Tracks task completions and calculates learning velocity for users.

Implements Requirements:
- 4.1: Record task completion timestamps
- 4.2: Calculate learning velocity
- 4.3: Update vector embeddings on velocity changes
- 4.4: Track velocity by task type
"""
import logging
from typing import Dict, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.syllabus import TaskCompletion, Task, TaskType
from app.models.user import User, UserProfile
from app.services.pinecone_service import PineconeService
from app.services.portfolio_analysis_service import PortfolioAnalysisService

logger = logging.getLogger(__name__)


class VelocityService:
    """Service for learning velocity tracking and management."""
    
    VELOCITY_CHANGE_THRESHOLD = 0.5  # 50% change triggers embedding update
    
    def __init__(self, db: Session):
        """
        Initialize velocity service.
        
        Args:
            db: Database session
        """
        self.db = db
        logger.info("VelocityService initialized")
    
    def record_task_completion(
        self,
        user_id: UUID,
        task_id: UUID,
        squad_id: UUID,
        time_spent_minutes: Optional[int] = None,
        quality_score: Optional[float] = None,
        notes: Optional[str] = None
    ) -> TaskCompletion:
        """
        Record task completion for a user.
        
        Implements Requirement 4.1: Record completion timestamp.
        
        Args:
            user_id: User ID
            task_id: Task ID
            squad_id: Squad ID
            time_spent_minutes: Optional actual time spent
            quality_score: Optional quality score (0-1)
            notes: Optional user notes
            
        Returns:
            TaskCompletion object
            
        Raises:
            ValueError: If user or task not found
        """
        # Verify user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Verify task exists
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Check if already completed
        existing = self.db.query(TaskCompletion).filter(
            TaskCompletion.user_id == user_id,
            TaskCompletion.task_id == task_id
        ).first()
        
        if existing:
            logger.warning(f"Task {task_id} already completed by user {user_id}")
            return existing
        
        # Create completion record
        completion = TaskCompletion(
            user_id=user_id,
            task_id=task_id,
            squad_id=squad_id,
            time_spent_minutes=time_spent_minutes,
            quality_score=quality_score,
            notes=notes
        )
        
        self.db.add(completion)
        self.db.commit()
        self.db.refresh(completion)
        
        logger.info(f"Recorded task completion for user {user_id}, task {task_id}")
        
        # Update user's learning velocity
        self._update_user_velocity(user_id)
        
        return completion
    
    def get_learning_velocity(
        self,
        user_id: UUID,
        task_type: Optional[TaskType] = None
    ) -> float:
        """
        Calculate user's learning velocity.
        
        Implements Requirements:
        - 4.2: Calculate average time between assignments and completions
        - 4.4: Track velocity by task type
        
        Args:
            user_id: User ID
            task_type: Optional task type filter
            
        Returns:
            Learning velocity in tasks per day
        """
        # Get completions
        query = self.db.query(TaskCompletion).filter(
            TaskCompletion.user_id == user_id
        )
        
        # Filter by task type if specified
        if task_type:
            query = query.join(Task).filter(Task.task_type == task_type)
        
        completions = query.order_by(TaskCompletion.completed_at).all()
        
        if len(completions) < 2:
            # Not enough data, return estimated velocity
            user = self.db.query(User).filter(User.id == user_id).first()
            if user and user.profile:
                return user.profile.learning_velocity
            return 1.0  # Default
        
        # Calculate time span
        first_completion = completions[0].completed_at
        last_completion = completions[-1].completed_at
        time_span_days = (last_completion - first_completion).total_seconds() / 86400
        
        if time_span_days == 0:
            return float(len(completions))
        
        # Velocity = tasks / days
        velocity = len(completions) / time_span_days
        
        logger.debug(f"Calculated velocity for user {user_id}: {velocity:.2f} tasks/day")
        
        return velocity
    
    def get_velocity_by_task_type(self, user_id: UUID) -> Dict[str, float]:
        """
        Get learning velocity partitioned by task type.
        
        Implements Requirement 4.4: Track velocity by task type.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary mapping task type to velocity
        """
        velocities = {}
        
        for task_type in TaskType:
            velocity = self.get_learning_velocity(user_id, task_type)
            velocities[task_type.value] = velocity
        
        return velocities
    
    def _update_user_velocity(self, user_id: UUID) -> None:
        """
        Update user's stored learning velocity.
        
        Implements Requirement 4.3: Update embedding on velocity changes > 50%.
        
        Args:
            user_id: User ID
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.profile:
            return
        
        # Calculate new velocity
        new_velocity = self.get_learning_velocity(user_id)
        old_velocity = user.profile.learning_velocity
        
        # Check if change is significant
        if old_velocity > 0:
            change_ratio = abs(new_velocity - old_velocity) / old_velocity
            
            if change_ratio > self.VELOCITY_CHANGE_THRESHOLD:
                logger.info(
                    f"Significant velocity change for user {user_id}: "
                    f"{old_velocity:.2f} -> {new_velocity:.2f} ({change_ratio:.1%})"
                )
                
                # Update profile
                user.profile.learning_velocity = new_velocity
                
                # Update vector embedding
                try:
                    portfolio_service = PortfolioAnalysisService(self.db)
                    portfolio_service.update_vector_embedding(user_id)
                    logger.info(f"Updated vector embedding for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to update vector embedding: {str(e)}")
        else:
            # First velocity calculation
            user.profile.learning_velocity = new_velocity
        
        self.db.commit()
