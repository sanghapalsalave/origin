"""
User Service

Manages user profiles, preferences, and skill assessments.

Implements Requirements:
- 1.9: Create user account with vector embedding
- 1.11: Collect timezone and preferred language
- 1.12: Combine multiple input methods
"""
import logging
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.user import User, UserProfile
from app.models.skill_assessment import SkillAssessment, VectorEmbedding, AssessmentSource
from app.services.portfolio_analysis_service import PortfolioAnalysisService

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing user profiles and skill assessments."""
    
    def __init__(self, db: Session):
        """
        Initialize user service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.portfolio_service = PortfolioAnalysisService(db)
    
    def create_profile(
        self,
        user_id: UUID,
        display_name: str,
        interest_area: str,
        timezone: str,
        preferred_language: str,
        skill_level: Optional[int] = None
    ) -> UserProfile:
        """
        Create user profile with required fields.
        
        Implements Requirements:
        - 1.9: Create user account with vector embedding representation
        - 1.11: Collect timezone and preferred language
        
        Args:
            user_id: User UUID
            display_name: User's display name
            interest_area: Primary interest area for guild matching
            timezone: IANA timezone (e.g., 'America/New_York')
            preferred_language: ISO 639-1 language code (e.g., 'en')
            skill_level: Skill level (1-10). If not provided, calculated from assessments.
            
        Returns:
            Created UserProfile object with vector embedding
            
        Raises:
            ValueError: If user not found, profile already exists, or required fields missing
        """
        # Validate required fields
        if not timezone:
            raise ValueError("Timezone is required for profile creation")
        if not preferred_language:
            raise ValueError("Preferred language is required for profile creation")
        if not interest_area:
            raise ValueError("Interest area is required for profile creation")
        
        # Verify user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        # Check if profile already exists
        existing_profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()
        if existing_profile:
            raise ValueError(f"Profile already exists for user: {user_id}")
        
        # Calculate skill level from assessments if not provided
        if skill_level is None:
            skill_level = self._calculate_combined_skill_level(user_id)
            if skill_level is None:
                # Default to mid-level if no assessments
                skill_level = 5
                logger.warning(f"No skill assessments found for user {user_id}, defaulting to skill_level=5")
        
        # Validate skill level
        if not 1 <= skill_level <= 10:
            raise ValueError(f"Skill level must be between 1 and 10, got: {skill_level}")
        
        # Generate vector embedding for matching
        # Initial learning velocity is 0.0 for new users
        try:
            vector_embedding = self.portfolio_service.generate_vector_embedding(
                user_id=user_id,
                skill_level=skill_level,
                learning_velocity=0.0,
                timezone=timezone,
                language=preferred_language,
                interest_area=interest_area
            )
            vector_embedding_id = str(vector_embedding.pinecone_id)
            logger.info(f"Vector embedding generated for user {user_id}: {vector_embedding_id}")
        except Exception as e:
            logger.error(f"Failed to generate vector embedding for user {user_id}: {str(e)}")
            raise ValueError(f"Failed to generate vector embedding: {str(e)}")
        
        # Create profile with vector embedding ID
        profile = UserProfile(
            user_id=user_id,
            display_name=display_name,
            interest_area=interest_area,
            skill_level=skill_level,
            timezone=timezone,
            preferred_language=preferred_language,
            learning_velocity=0.0,  # Will be calculated as user completes tasks
            vector_embedding_id=vector_embedding_id
        )
        
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        
        logger.info(f"Profile created for user {user_id}: skill_level={skill_level}, vector_embedding_id={vector_embedding_id}")
        return profile
    
    def update_profile(self, user_id: UUID, updates: dict) -> UserProfile:
        """
        Update user profile fields.
        
        Args:
            user_id: User UUID
            updates: Dictionary of fields to update
            
        Returns:
            Updated UserProfile object
            
        Raises:
            ValueError: If profile not found
        """
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()
        
        if not profile:
            raise ValueError(f"Profile not found for user: {user_id}")
        
        # Update allowed fields
        allowed_fields = {
            "display_name", "interest_area", "skill_level", "timezone",
            "preferred_language", "learning_velocity", "github_url",
            "linkedin_profile", "portfolio_url", "resume_data", "manual_skills"
        }
        
        for field, value in updates.items():
            if field in allowed_fields and hasattr(profile, field):
                setattr(profile, field, value)
        
        self.db.commit()
        self.db.refresh(profile)
        
        logger.info(f"Profile updated for user {user_id}")
        return profile
    
    def get_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """
        Retrieve user profile by ID.
        
        Args:
            user_id: User UUID
            
        Returns:
            UserProfile object or None if not found
        """
        return self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()
    
    def update_skill_level(self, user_id: UUID, skill_level: int) -> UserProfile:
        """
        Update user skill level.
        
        Args:
            user_id: User UUID
            skill_level: New skill level (1-10)
            
        Returns:
            Updated UserProfile object
            
        Raises:
            ValueError: If profile not found or skill_level invalid
        """
        if not 1 <= skill_level <= 10:
            raise ValueError(f"Skill level must be between 1 and 10, got: {skill_level}")
        
        profile = self.get_profile(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user: {user_id}")
        
        profile.skill_level = skill_level
        self.db.commit()
        self.db.refresh(profile)
        
        logger.info(f"Skill level updated for user {user_id}: {skill_level}")
        return profile
    
    def get_skill_assessments(self, user_id: UUID) -> List[SkillAssessment]:
        """
        Get all skill assessments for a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of SkillAssessment objects
        """
        return self.db.query(SkillAssessment).filter(
            SkillAssessment.user_id == user_id
        ).order_by(SkillAssessment.created_at.desc()).all()
    
    def _calculate_combined_skill_level(self, user_id: UUID) -> Optional[int]:
        """
        Calculate combined skill level from all assessments.
        
        Implements Requirement 1.12: Combine multiple input methods to build
        comprehensive profile.
        
        Args:
            user_id: User UUID
            
        Returns:
            Combined skill level (1-10) or None if no assessments
        """
        assessments = self.get_skill_assessments(user_id)
        
        if not assessments:
            return None
        
        # If there's a combined assessment, use it
        combined = next(
            (a for a in assessments if a.source == AssessmentSource.COMBINED),
            None
        )
        if combined:
            return combined.skill_level
        
        # Otherwise, calculate weighted average based on confidence scores
        total_weight = 0.0
        weighted_sum = 0.0
        
        for assessment in assessments:
            confidence = assessment.confidence_score or 0.5
            weighted_sum += assessment.skill_level * confidence
            total_weight += confidence
        
        if total_weight == 0:
            # Fallback to simple average
            return round(sum(a.skill_level for a in assessments) / len(assessments))
        
        combined_level = round(weighted_sum / total_weight)
        return max(1, min(10, combined_level))  # Ensure 1-10 range
    
    def update_portfolio_sources(
        self,
        user_id: UUID,
        github_url: Optional[str] = None,
        linkedin_profile: Optional[dict] = None,
        portfolio_url: Optional[str] = None,
        resume_data: Optional[dict] = None,
        manual_skills: Optional[List[str]] = None,
        trigger_reassessment: bool = True
    ) -> UserProfile:
        """
        Update user's portfolio sources and trigger skill reassessment.
        
        Implements Requirement 13.14: Allow users to update portfolio sources
        at any time to refresh skill assessment.
        
        When portfolio sources are updated, this method:
        1. Updates the portfolio source fields in the user profile
        2. Triggers new skill assessments for the updated sources
        3. Combines all assessments to calculate updated skill level
        4. Updates the user's skill level in their profile
        5. Regenerates the vector embedding for matching
        
        Args:
            user_id: User UUID
            github_url: GitHub profile URL (if provided, triggers GitHub analysis)
            linkedin_profile: LinkedIn profile data (if provided, triggers LinkedIn analysis)
            portfolio_url: Portfolio website URL (if provided, triggers website analysis)
            resume_data: Parsed resume data (if provided, triggers resume analysis)
            manual_skills: Manually entered skills (if provided, creates manual assessment)
            trigger_reassessment: Whether to trigger skill reassessment (default: True)
            
        Returns:
            Updated UserProfile object with refreshed skill level
            
        Raises:
            ValueError: If profile not found
        """
        profile = self.get_profile(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user: {user_id}")
        
        # Track which sources were updated
        sources_updated = []
        
        # Update portfolio sources
        if github_url is not None:
            profile.github_url = github_url
            sources_updated.append("github")
        if linkedin_profile is not None:
            profile.linkedin_profile = linkedin_profile
            sources_updated.append("linkedin")
        if portfolio_url is not None:
            profile.portfolio_url = portfolio_url
            sources_updated.append("portfolio_website")
        if resume_data is not None:
            profile.resume_data = resume_data
            sources_updated.append("resume")
        if manual_skills is not None:
            profile.manual_skills = manual_skills
            sources_updated.append("manual")
        
        self.db.commit()
        self.db.refresh(profile)
        
        logger.info(f"Portfolio sources updated for user {user_id}: {sources_updated}")
        
        # Trigger skill reassessment if requested and sources were updated
        if trigger_reassessment and sources_updated:
            logger.info(f"Triggering skill reassessment for user {user_id}")
            
            # Analyze each updated source
            assessments = []
            
            if "github" in sources_updated and github_url:
                try:
                    assessment = self.portfolio_service.analyze_github(github_url, user_id)
                    assessments.append(assessment)
                    logger.info(f"GitHub analysis completed for user {user_id}: skill_level={assessment.skill_level}")
                except Exception as e:
                    logger.error(f"GitHub analysis failed for user {user_id}: {str(e)}")
            
            if "linkedin" in sources_updated and linkedin_profile:
                try:
                    assessment = self.portfolio_service.analyze_linkedin(linkedin_profile, user_id)
                    assessments.append(assessment)
                    logger.info(f"LinkedIn analysis completed for user {user_id}: skill_level={assessment.skill_level}")
                except Exception as e:
                    logger.error(f"LinkedIn analysis failed for user {user_id}: {str(e)}")
            
            if "portfolio_website" in sources_updated and portfolio_url:
                try:
                    assessment = self.portfolio_service.analyze_portfolio_website(portfolio_url, user_id)
                    assessments.append(assessment)
                    logger.info(f"Portfolio website analysis completed for user {user_id}: skill_level={assessment.skill_level}")
                except Exception as e:
                    logger.error(f"Portfolio website analysis failed for user {user_id}: {str(e)}")
            
            if "resume" in sources_updated and resume_data:
                try:
                    # Resume data should contain file_content and file_type
                    file_content = resume_data.get("file_content")
                    file_type = resume_data.get("file_type")
                    if file_content and file_type:
                        assessment = self.portfolio_service.parse_resume(file_content, file_type, user_id)
                        assessments.append(assessment)
                        logger.info(f"Resume analysis completed for user {user_id}: skill_level={assessment.skill_level}")
                except Exception as e:
                    logger.error(f"Resume analysis failed for user {user_id}: {str(e)}")
            
            if "manual" in sources_updated and manual_skills:
                try:
                    # Create manual assessment from skills list
                    assessment = self.portfolio_service.create_manual_assessment(
                        skills=manual_skills,
                        experience_years=None,  # Not provided in update
                        proficiency_level=None,  # Will be inferred
                        user_id=user_id
                    )
                    assessments.append(assessment)
                    logger.info(f"Manual assessment completed for user {user_id}: skill_level={assessment.skill_level}")
                except Exception as e:
                    logger.error(f"Manual assessment failed for user {user_id}: {str(e)}")
            
            # If we have new assessments, combine them and update skill level
            if assessments:
                try:
                    # Get all existing assessments for this user
                    all_assessments = self.get_skill_assessments(user_id)
                    
                    # Combine all assessments (new and existing)
                    combined_assessment = self.portfolio_service.combine_assessments(all_assessments)
                    
                    # Update profile with new skill level
                    old_skill_level = profile.skill_level
                    profile.skill_level = combined_assessment.skill_level
                    self.db.commit()
                    self.db.refresh(profile)
                    
                    logger.info(f"Skill level updated for user {user_id}: {old_skill_level} -> {combined_assessment.skill_level}")
                    
                    # Regenerate vector embedding with updated skill level
                    try:
                        self.update_vector_embedding(user_id)
                        logger.info(f"Vector embedding regenerated for user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to regenerate vector embedding for user {user_id}: {str(e)}")
                        # Don't fail the entire operation if embedding update fails
                
                except Exception as e:
                    logger.error(f"Failed to combine assessments for user {user_id}: {str(e)}")
                    # Don't fail the entire operation if assessment combination fails
        
        return profile
    
    def update_vector_embedding(self, user_id: UUID) -> VectorEmbedding:
        """
        Regenerate user's vector embedding for matching.
        
        Should be called when user's skill level, learning velocity, or other
        matching-relevant attributes change significantly.
        
        Args:
            user_id: User UUID
            
        Returns:
            Updated VectorEmbedding object
            
        Raises:
            ValueError: If profile not found
        """
        profile = self.get_profile(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user: {user_id}")
        
        # Generate new vector embedding
        vector_embedding = self.portfolio_service.generate_vector_embedding(
            user_id=user_id,
            skill_level=profile.skill_level,
            learning_velocity=profile.learning_velocity,
            timezone=profile.timezone,
            language=profile.preferred_language,
            interest_area=profile.interest_area
        )
        
        # Update profile with new embedding ID
        profile.vector_embedding_id = str(vector_embedding.pinecone_id)
        self.db.commit()
        self.db.refresh(profile)
        
        logger.info(f"Vector embedding updated for user {user_id}: {vector_embedding.pinecone_id}")
        return vector_embedding

    def get_vector_embedding(self, user_id: UUID) -> Optional[VectorEmbedding]:
        """
        Get user's vector embedding.
        
        Args:
            user_id: User UUID
            
        Returns:
            VectorEmbedding object or None if not found
        """
        return self.db.query(VectorEmbedding).filter(
            VectorEmbedding.user_id == user_id
        ).first()
    
    def has_vector_embedding(self, user_id: UUID) -> bool:
        """
        Check if user has a vector embedding.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if embedding exists, False otherwise
        """
        return self.db.query(
            self.db.query(VectorEmbedding).filter(
                VectorEmbedding.user_id == user_id
            ).exists()
        ).scalar()
