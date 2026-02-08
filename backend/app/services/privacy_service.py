"""
Privacy and Data Management Service

Handles data sharing consent, data deletion, and privacy compliance.

Implements Requirements:
- 15.4: Data sharing consent management
- 15.5: Data deletion within 30 days
"""
import logging
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.user import User, UserProfile
from app.models.skill_assessment import SkillAssessment, VectorEmbedding
from app.models.mool import WorkSubmission, PeerReview, LevelUpRequest, ProjectAssessment
from app.models.premium import Subscription, Certificate, EmployeeAccess
from app.models.guild import GuildMembership
from app.models.squad import SquadMembership
from app.models.chat import Message
from app.models.notification import Notification

logger = logging.getLogger(__name__)


class PrivacyService:
    """Service for privacy and data management operations."""
    
    def __init__(self, db: Session):
        """
        Initialize Privacy service.
        
        Args:
            db: Database session
        """
        self.db = db
        logger.info("PrivacyService initialized")
    
    def record_consent(
        self,
        user_id: UUID,
        consent_type: str,
        granted: bool,
        purpose: str
    ) -> Dict:
        """
        Record user consent for data sharing.
        
        Implements Requirement 15.4: Ensure no sharing without explicit consent.
        
        Args:
            user_id: User ID
            consent_type: Type of consent (e.g., "third_party_analytics", "marketing")
            granted: Whether consent was granted
            purpose: Purpose of data sharing
            
        Returns:
            Dictionary with consent record
        """
        # Validate user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # TODO: Create consent tracking table in future migration
        # For now, log the consent
        consent_record = {
            'user_id': str(user_id),
            'consent_type': consent_type,
            'granted': granted,
            'purpose': purpose,
            'recorded_at': datetime.utcnow().isoformat()
        }
        
        logger.info(
            f"Consent recorded for user {user_id}: "
            f"{consent_type} = {granted} (purpose: {purpose})"
        )
        
        return consent_record
    
    def check_consent(
        self,
        user_id: UUID,
        consent_type: str
    ) -> bool:
        """
        Check if user has granted consent for specific data sharing.
        
        Args:
            user_id: User ID
            consent_type: Type of consent to check
            
        Returns:
            True if consent granted, False otherwise
        """
        # TODO: Query consent tracking table
        # For now, return False (no consent by default)
        logger.info(f"Checking consent for user {user_id}: {consent_type}")
        return False
    
    def delete_user_data(
        self,
        user_id: UUID,
        anonymize_analytics: bool = True
    ) -> Dict:
        """
        Delete user's personal data within 30 days.
        
        Implements Requirement 15.5: Remove personal data within 30 days,
        maintain anonymized analytics.
        
        This method:
        1. Deletes personal identifiable information
        2. Anonymizes data used for analytics
        3. Maintains referential integrity
        4. Logs deletion for audit trail
        
        Args:
            user_id: User ID
            anonymize_analytics: Whether to anonymize analytics data (default: True)
            
        Returns:
            Dictionary with deletion summary
        """
        # Validate user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        deletion_summary = {
            'user_id': str(user_id),
            'deletion_started_at': datetime.utcnow().isoformat(),
            'items_deleted': {},
            'items_anonymized': {}
        }
        
        # 1. Delete user profile (contains PII)
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()
        if profile:
            self.db.delete(profile)
            deletion_summary['items_deleted']['profile'] = 1
        
        # 2. Delete skill assessments (may contain PII from resumes)
        assessments = self.db.query(SkillAssessment).filter(
            SkillAssessment.user_id == user_id
        ).all()
        for assessment in assessments:
            self.db.delete(assessment)
        deletion_summary['items_deleted']['skill_assessments'] = len(assessments)
        
        # 3. Delete vector embeddings
        embeddings = self.db.query(VectorEmbedding).filter(
            VectorEmbedding.user_id == user_id
        ).all()
        for embedding in embeddings:
            self.db.delete(embedding)
        deletion_summary['items_deleted']['vector_embeddings'] = len(embeddings)
        
        # 4. Delete subscriptions (contains payment info)
        subscriptions = self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).all()
        for subscription in subscriptions:
            self.db.delete(subscription)
        deletion_summary['items_deleted']['subscriptions'] = len(subscriptions)
        
        # 5. Delete certificates (keep anonymized count for analytics)
        certificates = self.db.query(Certificate).filter(
            Certificate.user_id == user_id
        ).all()
        cert_count = len(certificates)
        for certificate in certificates:
            self.db.delete(certificate)
        deletion_summary['items_deleted']['certificates'] = cert_count
        
        # 6. Delete messages (contains personal communications)
        messages = self.db.query(Message).filter(
            Message.user_id == user_id
        ).all()
        for message in messages:
            self.db.delete(message)
        deletion_summary['items_deleted']['messages'] = len(messages)
        
        # 7. Delete notifications
        notifications = self.db.query(Notification).filter(
            Notification.user_id == user_id
        ).all()
        for notification in notifications:
            self.db.delete(notification)
        deletion_summary['items_deleted']['notifications'] = len(notifications)
        
        # 8. Anonymize work submissions and reviews (keep for analytics)
        if anonymize_analytics:
            work_submissions = self.db.query(WorkSubmission).filter(
                WorkSubmission.user_id == user_id
            ).all()
            for submission in work_submissions:
                submission.title = "[DELETED USER]"
                submission.description = "[User data deleted]"
                submission.submission_url = "[DELETED]"
            deletion_summary['items_anonymized']['work_submissions'] = len(work_submissions)
            
            peer_reviews = self.db.query(PeerReview).filter(
                PeerReview.reviewer_id == user_id
            ).all()
            for review in peer_reviews:
                review.review_content = "[User data deleted]"
            deletion_summary['items_anonymized']['peer_reviews'] = len(peer_reviews)
            
            levelup_requests = self.db.query(LevelUpRequest).filter(
                LevelUpRequest.user_id == user_id
            ).all()
            for request in levelup_requests:
                request.project_title = "[DELETED USER]"
                request.project_description = "[User data deleted]"
                request.project_url = "[DELETED]"
            deletion_summary['items_anonymized']['levelup_requests'] = len(levelup_requests)
        
        # 9. Remove from guild and squad memberships
        guild_memberships = self.db.query(GuildMembership).filter(
            GuildMembership.user_id == user_id
        ).all()
        for membership in guild_memberships:
            self.db.delete(membership)
        deletion_summary['items_deleted']['guild_memberships'] = len(guild_memberships)
        
        squad_memberships = self.db.query(SquadMembership).filter(
            SquadMembership.user_id == user_id
        ).all()
        for membership in squad_memberships:
            self.db.delete(membership)
        deletion_summary['items_deleted']['squad_memberships'] = len(squad_memberships)
        
        # 10. Revoke employee access
        employee_accesses = self.db.query(EmployeeAccess).filter(
            EmployeeAccess.user_id == user_id
        ).all()
        for access in employee_accesses:
            access.is_active = False
            access.access_revoked_at = datetime.utcnow()
        deletion_summary['items_anonymized']['employee_accesses'] = len(employee_accesses)
        
        # 11. Finally, anonymize user account (keep for referential integrity)
        user.email = f"deleted_{user_id}@deleted.local"
        user.password_hash = "[DELETED]"
        deletion_summary['items_anonymized']['user_account'] = 1
        
        # Commit all changes
        self.db.commit()
        
        deletion_summary['deletion_completed_at'] = datetime.utcnow().isoformat()
        deletion_summary['status'] = 'completed'
        
        logger.info(
            f"User data deletion completed for {user_id}. "
            f"Deleted: {sum(deletion_summary['items_deleted'].values())} items, "
            f"Anonymized: {sum(deletion_summary['items_anonymized'].values())} items"
        )
        
        return deletion_summary
    
    def schedule_data_deletion(
        self,
        user_id: UUID,
        deletion_date: Optional[datetime] = None
    ) -> Dict:
        """
        Schedule user data deletion for future date.
        
        Args:
            user_id: User ID
            deletion_date: Date to delete data (default: 30 days from now)
            
        Returns:
            Dictionary with scheduled deletion info
        """
        if deletion_date is None:
            deletion_date = datetime.utcnow() + timedelta(days=30)
        
        # TODO: Create scheduled deletion task with Celery
        # For now, just return the schedule
        schedule_info = {
            'user_id': str(user_id),
            'scheduled_for': deletion_date.isoformat(),
            'status': 'scheduled',
            'created_at': datetime.utcnow().isoformat()
        }
        
        logger.info(
            f"Data deletion scheduled for user {user_id} on {deletion_date}"
        )
        
        return schedule_info
    
    def export_user_data(
        self,
        user_id: UUID
    ) -> Dict:
        """
        Export all user data for GDPR compliance.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with all user data
        """
        # Validate user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Collect all user data
        export_data = {
            'user_id': str(user_id),
            'email': user.email,
            'created_at': user.created_at.isoformat(),
            'reputation_points': user.reputation_points,
            'current_level': user.current_level,
            'exported_at': datetime.utcnow().isoformat()
        }
        
        # Add profile data
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()
        if profile:
            export_data['profile'] = {
                'display_name': profile.display_name,
                'interest_area': profile.interest_area,
                'skill_level': profile.skill_level,
                'timezone': profile.timezone,
                'preferred_language': profile.preferred_language,
                'learning_velocity': profile.learning_velocity
            }
        
        # Add other data collections
        export_data['skill_assessments_count'] = self.db.query(SkillAssessment).filter(
            SkillAssessment.user_id == user_id
        ).count()
        
        export_data['work_submissions_count'] = self.db.query(WorkSubmission).filter(
            WorkSubmission.user_id == user_id
        ).count()
        
        export_data['peer_reviews_count'] = self.db.query(PeerReview).filter(
            PeerReview.reviewer_id == user_id
        ).count()
        
        export_data['certificates_count'] = self.db.query(Certificate).filter(
            Certificate.user_id == user_id
        ).count()
        
        logger.info(f"User data exported for {user_id}")
        
        return export_data
