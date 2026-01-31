"""Database models package."""
# Import all models here for Alembic autogenerate
from app.models.user import User, UserProfile
from app.models.skill_assessment import SkillAssessment, VectorEmbedding, AssessmentSource

# Export models
__all__ = ["User", "UserProfile", "SkillAssessment", "VectorEmbedding", "AssessmentSource"]
