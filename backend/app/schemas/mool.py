"""
Pydantic schemas for Mool reputation system API.

Defines request and response models for work submission, peer review,
reputation tracking, and level-up project management.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator

from app.models.mool import LevelUpStatus


# Work Submission Schemas

class WorkSubmissionCreate(BaseModel):
    """Request schema for creating a work submission."""
    squad_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10)
    submission_url: str = Field(..., min_length=1)


class WorkSubmissionResponse(BaseModel):
    """Response schema for work submission."""
    id: UUID
    user_id: UUID
    squad_id: UUID
    title: str
    description: str
    submission_url: str
    submitted_at: datetime
    
    class Config:
        from_attributes = True


# Peer Review Schemas

class PeerReviewCreate(BaseModel):
    """Request schema for creating a peer review."""
    review_content: str = Field(..., min_length=10)
    rating: int = Field(..., ge=1, le=5)
    
    @validator('rating')
    def validate_rating(cls, v):
        if not (1 <= v <= 5):
            raise ValueError('Rating must be between 1 and 5')
        return v


class PeerReviewResponse(BaseModel):
    """Response schema for peer review."""
    id: UUID
    submission_id: UUID
    reviewer_id: UUID
    review_content: str
    rating: int
    reputation_awarded: int
    submitted_at: datetime
    
    class Config:
        from_attributes = True


# Reputation Schemas

class ReputationResponse(BaseModel):
    """Response schema for user reputation."""
    user_id: UUID
    reputation_points: int


class RecentReview(BaseModel):
    """Schema for recent review in reputation breakdown."""
    review_id: str
    submission_id: str
    reputation_awarded: int
    rating: int
    submitted_at: str


class ReputationBreakdownResponse(BaseModel):
    """Response schema for detailed reputation breakdown."""
    total_reputation: int
    review_count: int
    average_per_review: float
    recent_reviews: List[RecentReview]


class ReviewerPrivilegesResponse(BaseModel):
    """Response schema for reviewer privileges."""
    user_id: str
    current_level: int
    reputation_points: int
    max_reviewable_level: int
    levels_above_unlocked: int
    next_unlock_at: Optional[int]
    next_unlock_levels: Optional[int]


# Level-Up Request Schemas

class LevelUpRequestCreate(BaseModel):
    """Request schema for creating a level-up request."""
    project_title: str = Field(..., min_length=1, max_length=200)
    project_description: str = Field(..., min_length=50)
    project_url: str = Field(..., min_length=1)


class LevelUpRequestResponse(BaseModel):
    """Response schema for level-up request."""
    id: UUID
    user_id: UUID
    current_level: int
    target_level: int
    project_title: str
    project_description: str
    project_url: str
    status: LevelUpStatus
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Project Assessment Schemas

class ProjectAssessmentCreate(BaseModel):
    """Request schema for creating a project assessment."""
    assessment_type: str = Field(..., pattern="^(ai|peer)$")
    approved: bool
    feedback: str = Field(..., min_length=10)
    
    @validator('assessment_type')
    def validate_assessment_type(cls, v):
        if v not in ["ai", "peer"]:
            raise ValueError('Assessment type must be "ai" or "peer"')
        return v


class ProjectAssessmentResponse(BaseModel):
    """Response schema for project assessment."""
    id: UUID
    levelup_request_id: UUID
    assessment_type: str
    assessed_by: str
    approved: bool
    feedback: str
    assessed_at: datetime
    
    class Config:
        from_attributes = True


# Level-Up Approval Schemas

class LevelUpApprovalResponse(BaseModel):
    """Response schema for level-up approval processing."""
    approved: bool
    user_id: str
    old_level: int
    new_level: int
    message: str
