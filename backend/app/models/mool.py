"""
Mool reputation system data models.

Implements Requirements 7.1, 7.2, 8.1 (Mool reputation system and level-up verification).
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum
from app.db.base import Base


class WorkSubmission(Base):
    """
    Work submission model for users submitting work for peer review.
    
    Users submit work to earn reputation points through peer reviews.
    Submissions are visible to eligible reviewers within the same guild,
    excluding direct collaborators.
    
    Implements Requirements:
    - 7.1: Work submission for review
    - 7.6: Collaborator exclusion
    """
    __tablename__ = "work_submissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    squad_id = Column(UUID(as_uuid=True), ForeignKey("squads.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Submission details
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    submission_url = Column(String, nullable=False)  # GitHub repo, portfolio link, etc.
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="work_submissions")
    squad = relationship("Squad", backref="work_submissions")
    reviews = relationship("PeerReview", back_populates="submission", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<WorkSubmission(id={self.id}, title={self.title}, user_id={self.user_id})>"


class PeerReview(Base):
    """
    Peer review model for reviews of work submissions.
    
    Reviewers earn reputation points based on review quality and their level.
    Points calculation: base_points * (1 + reviewer_level * 0.1) + bonuses
    - Base points: 10
    - Quality bonus: +5 for detailed reviews (> 200 words)
    - Consistency bonus: +3 for reviews within 24 hours
    - Maximum points: 25
    
    Implements Requirements:
    - 7.2: Peer review completion and reputation award
    - 7.3: Reputation weighting by reviewer level
    """
    __tablename__ = "peer_reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("work_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Review content
    review_content = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 scale
    
    # Reputation tracking
    reputation_awarded = Column(Integer, nullable=False)  # Calculated based on formula
    
    # Timestamps
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    submission = relationship("WorkSubmission", back_populates="reviews")
    reviewer = relationship("User", backref="peer_reviews_given")
    
    def __repr__(self) -> str:
        return f"<PeerReview(id={self.id}, submission_id={self.submission_id}, reviewer_id={self.reviewer_id}, reputation={self.reputation_awarded})>"


class LevelUpStatus(str, Enum):
    """Status of level-up request."""
    PENDING = "pending"              # Initial submission
    AI_APPROVED = "ai_approved"      # AI assessment passed
    PEER_REVIEW = "peer_review"      # Awaiting peer reviews
    APPROVED = "approved"            # All approvals received, level-up granted
    REJECTED = "rejected"            # Rejected by AI or peers


class LevelUpRequest(Base):
    """
    Level-up request model for users submitting projects for level progression.
    
    Users must complete all requirements for their current level before submitting.
    The process requires:
    1. AI Guild Master automated quality assessment
    2. Two peer reviewers (minimum 2 levels higher)
    3. Approval from both AI and both peer reviewers
    
    Implements Requirements:
    - 8.1: Level-up project submission
    - 8.2: AI automated quality assessment
    - 8.3: Peer reviewer assignment
    - 8.4: Dual approval requirement
    - 8.6: Reviewer level requirement (2+ levels higher)
    """
    __tablename__ = "levelup_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Level progression
    current_level = Column(Integer, nullable=False)
    target_level = Column(Integer, nullable=False)
    
    # Project submission details
    project_title = Column(String, nullable=False)
    project_description = Column(Text, nullable=False)
    project_url = Column(String, nullable=False)  # GitHub repo, demo link, etc.
    
    # Status tracking
    status = Column(SQLEnum(LevelUpStatus), nullable=False, default=LevelUpStatus.PENDING)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="levelup_requests")
    assessments = relationship("ProjectAssessment", back_populates="levelup_request", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<LevelUpRequest(id={self.id}, user_id={self.user_id}, {self.current_level}->{self.target_level}, status={self.status})>"


class ProjectAssessment(Base):
    """
    Project assessment model for AI and peer assessments of level-up projects.
    
    Each level-up request receives:
    - 1 AI assessment from Guild Master
    - 2 peer assessments from senior guild members (2+ levels higher)
    
    All assessments must approve for level-up to be granted.
    Rejections include detailed feedback and allow resubmission.
    
    Implements Requirements:
    - 8.2: AI assessment for all submissions
    - 8.3: Peer reviewer assignment
    - 8.5: Rejection feedback provision
    """
    __tablename__ = "project_assessments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    levelup_request_id = Column(UUID(as_uuid=True), ForeignKey("levelup_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Assessment type and assessor
    assessment_type = Column(String, nullable=False)  # "ai" or "peer"
    assessed_by = Column(String, nullable=False)  # user_id (UUID as string) or "guild_master_ai"
    
    # Assessment result
    approved = Column(String, nullable=False)  # "true" or "false" as string for consistency
    feedback = Column(Text, nullable=False)  # Detailed feedback, required for rejections
    
    # Timestamp
    assessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    levelup_request = relationship("LevelUpRequest", back_populates="assessments")
    
    def __repr__(self) -> str:
        return f"<ProjectAssessment(id={self.id}, type={self.assessment_type}, approved={self.approved}, assessed_by={self.assessed_by})>"
