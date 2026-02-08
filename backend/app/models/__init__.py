"""Database models package."""
# Import all models here for Alembic autogenerate
from app.models.user import User, UserProfile
from app.models.skill_assessment import SkillAssessment, VectorEmbedding, AssessmentSource
from app.models.mool import WorkSubmission, PeerReview, LevelUpRequest, ProjectAssessment, LevelUpStatus

# Export models
__all__ = [
    "User",
    "UserProfile",
    "SkillAssessment",
    "VectorEmbedding",
    "AssessmentSource",
    "WorkSubmission",
    "PeerReview",
    "LevelUpRequest",
    "ProjectAssessment",
    "LevelUpStatus",
]
