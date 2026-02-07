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
from app.models.skill_assessment import AssessmentSource

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
