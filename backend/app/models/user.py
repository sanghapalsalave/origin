"""
User and UserProfile data models.

Implements Requirements 15.1 (password hashing with bcrypt).
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.core.security import get_password_hash, verify_password


class User(Base):
    """
    User model for authentication and core user data.
    
    Implements password hashing with bcrypt (12 rounds minimum) as per Requirement 15.1.
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    # Reputation and level tracking
    reputation_points = Column(Integer, default=0, nullable=False)
    current_level = Column(Integer, default=1, nullable=False)
    
    def set_password(self, password: str) -> None:
        """
        Hash and set user password using bcrypt with 12 rounds minimum.
        
        Args:
            password: Plain text password
        """
        self.password_hash = get_password_hash(password)
    
    def verify_password(self, password: str) -> bool:
        """
        Verify password against stored hash.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        return verify_password(password, self.password_hash)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class UserProfile(Base):
    """
    User profile model for storing user preferences and skill information.
    
    Stores portfolio sources, skill assessments, and vector embeddings for matching.
    """
    __tablename__ = "user_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Profile information
    display_name = Column(String, nullable=False)
    interest_area = Column(String, nullable=False)
    skill_level = Column(Integer, nullable=False)  # 1-10 scale
    timezone = Column(String, nullable=False)  # IANA timezone (e.g., "America/New_York")
    preferred_language = Column(String, nullable=False)  # ISO 639-1 code (e.g., "en")
    
    # Learning metrics
    learning_velocity = Column(Float, default=0.0, nullable=False)  # tasks per day
    vector_embedding_id = Column(String, nullable=True)  # Pinecone vector ID
    
    # Portfolio sources (optional)
    github_url = Column(String, nullable=True)
    linkedin_profile = Column(JSON, nullable=True)  # Stored as JSON
    portfolio_url = Column(String, nullable=True)
    resume_data = Column(JSON, nullable=True)  # Parsed resume data as JSON
    manual_skills = Column(JSON, nullable=True)  # List of manually entered skills
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="profile")
    
    def __repr__(self) -> str:
        return f"<UserProfile(user_id={self.user_id}, display_name={self.display_name}, skill_level={self.skill_level})>"
