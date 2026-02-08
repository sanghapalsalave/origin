"""
Celery tasks for squad matching and rebalancing.

Implements scheduled squad rebalancing and waiting pool checks.
"""
import logging
from datetime import datetime, timedelta
from uuid import UUID
from typing import Dict, Any, List
from celery import Task
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.db.base import SessionLocal
from app.services.matching_service import MatchingService
from app.services.pinecone_service import PineconeService
from app.services.notification_service import NotificationService
from app.models.user import User, UserProfile
from app.models.squad import Squad
from app.models.skill_assessment import VectorEmbedding

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


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.squad_matching.rebalance_squads")
def rebalance_squads(self) -> Dict[str, Any]:
    """
    Scheduled task to rebalance squads based on velocity changes.
    
    Runs daily and:
    1. Identifies users with significant velocity changes (>50%)
    2. Updates their vector embeddings
    3. Optionally suggests squad changes (not implemented in MVP)
    
    Returns:
        Dictionary with rebalancing results
    """
    try:
        logger.info("Starting squad rebalancing task")
        
        # Get all users with profiles
        users = self.db.query(User).join(UserProfile).filter(
            UserProfile.learning_velocity.isnot(None)
        ).all()
        
        pinecone_service = PineconeService()
        updated_count = 0
        failed_count = 0
        
        for user in users:
            try:
                # Get user's current vector embedding
                current_embedding = self.db.query(VectorEmbedding).filter(
                    VectorEmbedding.user_id == user.id
                ).order_by(VectorEmbedding.created_at.desc()).first()
                
                if not current_embedding:
                    continue
                
                # Check if velocity has changed significantly (>50%)
                current_velocity = user.profile.learning_velocity
                embedding_velocity = current_embedding.velocity
                
                if embedding_velocity == 0:
                    continue
                
                velocity_change = abs(current_velocity - embedding_velocity) / embedding_velocity
                
                if velocity_change > 0.5:
                    logger.info(
                        f"Updating embedding for user {user.id}: "
                        f"velocity changed from {embedding_velocity} to {current_velocity}"
                    )
                    
                    # Get latest skill assessment
                    from app.models.skill_assessment import SkillAssessment
                    latest_assessment = self.db.query(SkillAssessment).filter(
                        SkillAssessment.user_id == user.id
                    ).order_by(SkillAssessment.created_at.desc()).first()
                    
                    if not latest_assessment:
                        continue
                    
                    # Generate new vector embedding
                    new_embedding_vector = pinecone_service.generate_vector_embedding(
                        skill_level=latest_assessment.skill_level,
                        velocity=current_velocity,
                        timezone=user.profile.timezone,
                        language=user.profile.language,
                        detected_skills=latest_assessment.detected_skills
                    )
                    
                    # Store new embedding
                    new_embedding = VectorEmbedding(
                        user_id=user.id,
                        embedding=new_embedding_vector,
                        skill_level=latest_assessment.skill_level,
                        velocity=current_velocity
                    )
                    self.db.add(new_embedding)
                    self.db.commit()
                    
                    updated_count += 1
                    logger.info(f"Embedding updated for user {user.id}")
                    
            except Exception as e:
                logger.error(f"Failed to rebalance user {user.id}: {str(e)}", exc_info=True)
                failed_count += 1
        
        logger.info(
            f"Squad rebalancing completed: "
            f"updated={updated_count}, failed={failed_count}, total_users={len(users)}"
        )
        
        return {
            "success": True,
            "updated_count": updated_count,
            "failed_count": failed_count,
            "total_users": len(users)
        }
        
    except Exception as e:
        logger.error(f"Squad rebalancing task failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.squad_matching.check_waiting_pool")
def check_waiting_pool(self) -> Dict[str, Any]:
    """
    Scheduled task to check waiting pool for new matches.
    
    Runs hourly and:
    1. Gets all users in waiting pool
    2. Attempts to find matches for them
    3. Notifies users when compatible squads form
    
    Returns:
        Dictionary with matching results
    """
    try:
        logger.info("Starting waiting pool check task")
        
        matching_service = MatchingService(self.db)
        notification_service = NotificationService(self.db)
        
        # Get all guilds
        from app.models.guild import Guild
        guilds = self.db.query(Guild).all()
        
        matched_count = 0
        notified_count = 0
        failed_count = 0
        
        for guild in guilds:
            try:
                # Get waiting pool for this guild
                waiting_users = matching_service.get_waiting_pool(guild.id)
                
                if len(waiting_users) < 12:
                    # Not enough users to form a squad
                    continue
                
                logger.info(f"Checking waiting pool for guild {guild.id}: {len(waiting_users)} users")
                
                # Try to form squads from waiting pool
                # Group users by similarity
                from app.services.pinecone_service import PineconeService
                pinecone_service = PineconeService()
                
                # Get embeddings for waiting users
                user_embeddings = {}
                for user_id in waiting_users:
                    embedding = self.db.query(VectorEmbedding).filter(
                        VectorEmbedding.user_id == user_id
                    ).order_by(VectorEmbedding.created_at.desc()).first()
                    
                    if embedding:
                        user_embeddings[user_id] = embedding.embedding
                
                # Find potential squads (groups of 12-15 similar users)
                potential_squads = find_potential_squads(user_embeddings, pinecone_service)
                
                for squad_users in potential_squads:
                    try:
                        # Create new squad
                        squad = matching_service.create_squad(
                            guild_id=guild.id,
                            member_ids=squad_users
                        )
                        
                        matched_count += 1
                        
                        # Notify all squad members
                        for user_id in squad_users:
                            notification_service.send_notification(
                                user_id=user_id,
                                notification_type="squad_matched",
                                title="Squad Match Found!",
                                body=f"You've been matched with a squad in {guild.name}",
                                data={
                                    "squad_id": str(squad.id),
                                    "guild_id": str(guild.id),
                                    "guild_name": guild.name
                                }
                            )
                            notified_count += 1
                        
                        logger.info(f"Squad created from waiting pool: {squad.id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to create squad from waiting pool: {str(e)}", exc_info=True)
                        failed_count += 1
                        
            except Exception as e:
                logger.error(f"Failed to check waiting pool for guild {guild.id}: {str(e)}", exc_info=True)
                failed_count += 1
        
        logger.info(
            f"Waiting pool check completed: "
            f"matched={matched_count}, notified={notified_count}, failed={failed_count}"
        )
        
        return {
            "success": True,
            "matched_count": matched_count,
            "notified_count": notified_count,
            "failed_count": failed_count
        }
        
    except Exception as e:
        logger.error(f"Waiting pool check task failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


def find_potential_squads(
    user_embeddings: Dict[UUID, List[float]],
    pinecone_service: PineconeService,
    min_similarity: float = 0.7
) -> List[List[UUID]]:
    """
    Find potential squads from user embeddings.
    
    Groups users with similarity > threshold into squads of 12-15 members.
    
    Args:
        user_embeddings: Dictionary mapping user IDs to embeddings
        pinecone_service: Pinecone service instance
        min_similarity: Minimum similarity threshold
        
    Returns:
        List of potential squads (each squad is a list of user IDs)
    """
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    
    if len(user_embeddings) < 12:
        return []
    
    # Convert to numpy arrays
    user_ids = list(user_embeddings.keys())
    embeddings = np.array([user_embeddings[uid] for uid in user_ids])
    
    # Calculate similarity matrix
    similarity_matrix = cosine_similarity(embeddings)
    
    # Find groups of similar users
    potential_squads = []
    used_users = set()
    
    for i, user_id in enumerate(user_ids):
        if user_id in used_users:
            continue
        
        # Find similar users
        similar_indices = np.where(similarity_matrix[i] >= min_similarity)[0]
        similar_users = [user_ids[j] for j in similar_indices if user_ids[j] not in used_users]
        
        # If we have enough users for a squad (12-15)
        if len(similar_users) >= 12:
            squad_users = similar_users[:15]  # Take up to 15 users
            potential_squads.append(squad_users)
            used_users.update(squad_users)
    
    return potential_squads
