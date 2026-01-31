"""
SkillAssessment and VectorEmbedding data models.

Implements Requirements 1.3, 1.4, 1.5, 1.6 (portfolio analysis and skill assessment).
"""
from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from enum import Enum
from app.db.base import Base


class AssessmentSource(str, Enum):
    """Source of skill assessment."""
    GITHUB = "github"
    LINKEDIN = "linkedin"
    RESUME = "resume"
    PORTFOLIO_WEBSITE = "portfolio_website"
    MANUAL = "manual"
    COMBINED = "combined"


class SkillAssessment(Base):
    """
    Skill assessment model for storing portfolio analysis results.
    
    Stores skill level assessments from various sources (GitHub, LinkedIn, resume,
    portfolio website, manual entry) and combined assessments.
    
    Implements Requirements:
    - 1.3: GitHub integration and skill level detection
    - 1.4: LinkedIn integration and skill analysis
    - 1.5: Resume upload and parsing
    - 1.6: Portfolio URL analysis
    """
    __tablename__ = "skill_assessments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Assessment metadata
    source = Column(SQLEnum(AssessmentSource), nullable=False)
    skill_level = Column(Integer, nullable=False)  # 1-10 scale
    confidence_score = Column(Float, nullable=True)  # 0.0-1.0, how confident the assessment is
    
    # Source-specific data
    source_url = Column(String, nullable=True)  # GitHub URL, LinkedIn profile URL, portfolio URL
    source_data = Column(JSON, nullable=True)  # Raw data from source (repos, experience, etc.)
    
    # Extracted information
    detected_skills = Column(ARRAY(String), nullable=True)  # List of detected technical skills
    experience_years = Column(Float, nullable=True)  # Estimated years of experience
    proficiency_levels = Column(JSON, nullable=True)  # Dict of skill: proficiency_level
    
    # Analysis details
    analysis_summary = Column(Text, nullable=True)  # Human-readable summary of assessment
    extra_metadata = Column(JSON, nullable=True)  # Additional metadata (commit frequency, project complexity, etc.)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="skill_assessments")
    
    def __repr__(self) -> str:
        return f"<SkillAssessment(id={self.id}, user_id={self.user_id}, source={self.source}, skill_level={self.skill_level})>"


class VectorEmbedding(Base):
    """
    Vector embedding model for storing user embeddings for squad matching.
    
    Stores vector representations of users based on skill level, learning velocity,
    timezone, language, and interest area. Used by Node Logic matching engine.
    
    Implements Requirements:
    - 2.1: Vector embedding generation for matching
    """
    __tablename__ = "vector_embeddings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Pinecone integration
    pinecone_id = Column(String, unique=True, nullable=False, index=True)  # ID in Pinecone vector database
    
    # Embedding components (for reference and debugging)
    skill_level = Column(Integer, nullable=False)  # 1-10
    learning_velocity = Column(Float, nullable=False)  # tasks per day
    timezone_offset = Column(Float, nullable=False)  # hours from UTC
    language_code = Column(String, nullable=False)  # ISO 639-1 code
    interest_area = Column(String, nullable=False)  # Primary interest/guild area
    
    # Embedding metadata
    embedding_version = Column(String, nullable=False, default="v1")  # Version for tracking embedding algorithm changes
    dimensions = Column(Integer, nullable=False, default=384)  # Number of dimensions in vector
    
    # Additional metadata
    extra_metadata = Column(JSON, nullable=True)  # Additional metadata for matching (preferences, constraints, etc.)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="vector_embedding", uselist=False)
    
    def __repr__(self) -> str:
        return f"<VectorEmbedding(id={self.id}, user_id={self.user_id}, pinecone_id={self.pinecone_id}, skill_level={self.skill_level})>"
