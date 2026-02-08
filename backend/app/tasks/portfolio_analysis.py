"""
Celery tasks for portfolio analysis.

Implements asynchronous portfolio analysis for onboarding flow.
"""
import logging
from uuid import UUID
from typing import Dict, Any
from celery import Task
from app.core.celery_app import celery_app
from app.db.base import SessionLocal
from app.services.portfolio_analysis_service import PortfolioAnalysisService
from app.models.skill_assessment import AssessmentSource, SkillAssessment

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


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.portfolio_analysis.analyze_github")
def analyze_github_task(self, user_id: str, github_url: str) -> Dict[str, Any]:
    """
    Asynchronous task to analyze GitHub portfolio.
    
    Args:
        user_id: User UUID as string
        github_url: GitHub profile URL
        
    Returns:
        Dictionary with assessment results
    """
    try:
        logger.info(f"Starting GitHub analysis for user {user_id}")
        
        service = PortfolioAnalysisService(self.db)
        assessment = service.analyze_github(github_url, UUID(user_id))
        
        logger.info(f"GitHub analysis completed for user {user_id}: skill_level={assessment.skill_level}")
        
        return {
            "success": True,
            "assessment_id": str(assessment.id),
            "skill_level": assessment.skill_level,
            "confidence_score": assessment.confidence_score,
            "detected_skills": assessment.detected_skills,
            "experience_years": assessment.experience_years,
            "analysis_summary": assessment.analysis_summary
        }
    except Exception as e:
        logger.error(f"GitHub analysis failed for user {user_id}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.portfolio_analysis.analyze_linkedin")
def analyze_linkedin_task(self, user_id: str, linkedin_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Asynchronous task to analyze LinkedIn portfolio.
    
    Args:
        user_id: User UUID as string
        linkedin_data: LinkedIn profile data
        
    Returns:
        Dictionary with assessment results
    """
    try:
        logger.info(f"Starting LinkedIn analysis for user {user_id}")
        
        service = PortfolioAnalysisService(self.db)
        assessment = service.analyze_linkedin(linkedin_data, UUID(user_id))
        
        logger.info(f"LinkedIn analysis completed for user {user_id}: skill_level={assessment.skill_level}")
        
        return {
            "success": True,
            "assessment_id": str(assessment.id),
            "skill_level": assessment.skill_level,
            "confidence_score": assessment.confidence_score,
            "detected_skills": assessment.detected_skills,
            "experience_years": assessment.experience_years,
            "analysis_summary": assessment.analysis_summary
        }
    except Exception as e:
        logger.error(f"LinkedIn analysis failed for user {user_id}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.portfolio_analysis.parse_resume")
def parse_resume_task(self, user_id: str, resume_content: bytes, file_type: str) -> Dict[str, Any]:
    """
    Asynchronous task to parse and analyze resume.
    
    Args:
        user_id: User UUID as string
        resume_content: Resume file content as bytes
        file_type: File type (pdf, docx, txt)
        
    Returns:
        Dictionary with assessment results
    """
    try:
        logger.info(f"Starting resume parsing for user {user_id}")
        
        service = PortfolioAnalysisService(self.db)
        assessment = service.parse_resume(resume_content, file_type, UUID(user_id))
        
        logger.info(f"Resume parsing completed for user {user_id}: skill_level={assessment.skill_level}")
        
        return {
            "success": True,
            "assessment_id": str(assessment.id),
            "skill_level": assessment.skill_level,
            "confidence_score": assessment.confidence_score,
            "detected_skills": assessment.detected_skills,
            "experience_years": assessment.experience_years,
            "analysis_summary": assessment.analysis_summary
        }
    except Exception as e:
        logger.error(f"Resume parsing failed for user {user_id}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.portfolio_analysis.analyze_portfolio_website")
def analyze_portfolio_website_task(self, user_id: str, portfolio_url: str) -> Dict[str, Any]:
    """
    Asynchronous task to analyze portfolio website.
    
    Args:
        user_id: User UUID as string
        portfolio_url: Portfolio website URL
        
    Returns:
        Dictionary with assessment results
    """
    try:
        logger.info(f"Starting portfolio website analysis for user {user_id}")
        
        service = PortfolioAnalysisService(self.db)
        assessment = service.analyze_portfolio_website(portfolio_url, UUID(user_id))
        
        logger.info(f"Portfolio website analysis completed for user {user_id}: skill_level={assessment.skill_level}")
        
        return {
            "success": True,
            "assessment_id": str(assessment.id),
            "skill_level": assessment.skill_level,
            "confidence_score": assessment.confidence_score,
            "detected_skills": assessment.detected_skills,
            "experience_years": assessment.experience_years,
            "analysis_summary": assessment.analysis_summary
        }
    except Exception as e:
        logger.error(f"Portfolio website analysis failed for user {user_id}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.portfolio_analysis.create_manual_assessment")
def create_manual_assessment_task(
    self,
    user_id: str,
    skills: list,
    experience_years: float,
    proficiency_level: int
) -> Dict[str, Any]:
    """
    Asynchronous task to create manual skill assessment.
    
    Args:
        user_id: User UUID as string
        skills: List of manually entered skills
        experience_years: Years of experience
        proficiency_level: Self-assessed proficiency level (1-10)
        
    Returns:
        Dictionary with assessment results
    """
    try:
        logger.info(f"Creating manual assessment for user {user_id}")
        
        service = PortfolioAnalysisService(self.db)
        assessment = service.create_manual_assessment(
            skills=skills,
            experience_years=experience_years,
            proficiency_level=proficiency_level,
            user_id=UUID(user_id)
        )
        
        logger.info(f"Manual assessment created for user {user_id}: skill_level={assessment.skill_level}")
        
        return {
            "success": True,
            "assessment_id": str(assessment.id),
            "skill_level": assessment.skill_level,
            "confidence_score": assessment.confidence_score,
            "detected_skills": assessment.detected_skills,
            "experience_years": assessment.experience_years,
            "analysis_summary": assessment.analysis_summary
        }
    except Exception as e:
        logger.error(f"Manual assessment creation failed for user {user_id}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.portfolio_analysis.complete_portfolio_analysis")
def complete_portfolio_analysis_task(
    self,
    user_id: str,
    sources: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Comprehensive portfolio analysis task that handles multiple sources.
    
    Analyzes all provided portfolio sources (GitHub, LinkedIn, resume, website, manual),
    combines the assessments, generates vector embedding, and sends notification.
    
    Args:
        user_id: User UUID as string
        sources: Dictionary with portfolio sources:
            - github_url: Optional GitHub profile URL
            - linkedin_data: Optional LinkedIn profile data
            - resume_content: Optional resume file content (bytes)
            - resume_file_type: Optional resume file type
            - portfolio_url: Optional portfolio website URL
            - manual_skills: Optional manual skills data
            
    Returns:
        Dictionary with combined assessment results
    """
    try:
        logger.info(f"Starting complete portfolio analysis for user {user_id}")
        
        service = PortfolioAnalysisService(self.db)
        assessment_ids = []
        
        # Analyze GitHub if provided
        if sources.get("github_url"):
            try:
                assessment = service.analyze_github(sources["github_url"], UUID(user_id))
                assessment_ids.append(assessment.id)
                logger.info(f"GitHub analysis completed for user {user_id}")
            except Exception as e:
                logger.warning(f"GitHub analysis failed for user {user_id}: {str(e)}")
        
        # Analyze LinkedIn if provided
        if sources.get("linkedin_data"):
            try:
                assessment = service.analyze_linkedin(sources["linkedin_data"], UUID(user_id))
                assessment_ids.append(assessment.id)
                logger.info(f"LinkedIn analysis completed for user {user_id}")
            except Exception as e:
                logger.warning(f"LinkedIn analysis failed for user {user_id}: {str(e)}")
        
        # Parse resume if provided
        if sources.get("resume_content") and sources.get("resume_file_type"):
            try:
                assessment = service.parse_resume(
                    sources["resume_content"],
                    sources["resume_file_type"],
                    UUID(user_id)
                )
                assessment_ids.append(assessment.id)
                logger.info(f"Resume parsing completed for user {user_id}")
            except Exception as e:
                logger.warning(f"Resume parsing failed for user {user_id}: {str(e)}")
        
        # Analyze portfolio website if provided
        if sources.get("portfolio_url"):
            try:
                assessment = service.analyze_portfolio_website(sources["portfolio_url"], UUID(user_id))
                assessment_ids.append(assessment.id)
                logger.info(f"Portfolio website analysis completed for user {user_id}")
            except Exception as e:
                logger.warning(f"Portfolio website analysis failed for user {user_id}: {str(e)}")
        
        # Create manual assessment if provided
        if sources.get("manual_skills"):
            try:
                manual_data = sources["manual_skills"]
                assessment = service.create_manual_assessment(
                    skills=manual_data.get("skills", []),
                    experience_years=manual_data.get("experience_years", 0),
                    proficiency_level=manual_data.get("proficiency_level", 5),
                    user_id=UUID(user_id)
                )
                assessment_ids.append(assessment.id)
                logger.info(f"Manual assessment created for user {user_id}")
            except Exception as e:
                logger.warning(f"Manual assessment creation failed for user {user_id}: {str(e)}")
        
        # Combine assessments if multiple sources
        if len(assessment_ids) > 1:
            combined_assessment = service.combine_assessments(assessment_ids, UUID(user_id))
            logger.info(f"Combined assessment created for user {user_id}: skill_level={combined_assessment.skill_level}")
        elif len(assessment_ids) == 1:
            combined_assessment = self.db.query(SkillAssessment).filter(
                SkillAssessment.id == assessment_ids[0]
            ).first()
        else:
            raise ValueError("No valid portfolio sources provided")
        
        # Generate vector embedding
        from app.services.pinecone_service import PineconeService
        from app.models.user import User
        
        user = self.db.query(User).filter(User.id == UUID(user_id)).first()
        if user and user.profile:
            pinecone_service = PineconeService()
            embedding = pinecone_service.generate_vector_embedding(
                skill_level=combined_assessment.skill_level,
                velocity=user.profile.learning_velocity or 1.0,
                timezone=user.profile.timezone,
                language=user.profile.language,
                detected_skills=combined_assessment.detected_skills
            )
            
            # Store embedding
            from app.models.skill_assessment import VectorEmbedding
            vector_embedding = VectorEmbedding(
                user_id=UUID(user_id),
                embedding=embedding,
                skill_level=combined_assessment.skill_level,
                velocity=user.profile.learning_velocity or 1.0
            )
            self.db.add(vector_embedding)
            self.db.commit()
            logger.info(f"Vector embedding generated for user {user_id}")
        
        # Send notification
        from app.services.notification_service import NotificationService
        notification_service = NotificationService(self.db)
        notification_service.send_notification(
            user_id=UUID(user_id),
            notification_type="portfolio_analysis_complete",
            title="Portfolio Analysis Complete",
            body=f"Your skill assessment is ready! Skill level: {combined_assessment.skill_level}/10",
            data={
                "assessment_id": str(combined_assessment.id),
                "skill_level": combined_assessment.skill_level
            }
        )
        logger.info(f"Notification sent to user {user_id}")
        
        logger.info(f"Complete portfolio analysis finished for user {user_id}")
        
        return {
            "success": True,
            "assessment_id": str(combined_assessment.id),
            "skill_level": combined_assessment.skill_level,
            "confidence_score": combined_assessment.confidence_score,
            "detected_skills": combined_assessment.detected_skills,
            "experience_years": combined_assessment.experience_years,
            "analysis_summary": combined_assessment.analysis_summary,
            "sources_analyzed": len(assessment_ids)
        }
        
    except Exception as e:
        logger.error(f"Complete portfolio analysis failed for user {user_id}: {str(e)}", exc_info=True)
        
        # Send error notification
        try:
            from app.services.notification_service import NotificationService
            notification_service = NotificationService(self.db)
            notification_service.send_notification(
                user_id=UUID(user_id),
                notification_type="portfolio_analysis_failed",
                title="Portfolio Analysis Failed",
                body="We encountered an issue analyzing your portfolio. Please try again or contact support.",
                data={"error": str(e)}
            )
        except Exception as notif_error:
            logger.error(f"Failed to send error notification: {str(notif_error)}")
        
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
