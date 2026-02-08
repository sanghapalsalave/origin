"""
Mool reputation system API endpoints.

Provides endpoints for work submission, peer review, reputation tracking,
and level-up project management.

Implements Requirements 7.1-7.6, 8.1-8.7.
"""
from typing import List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.mool_service import MoolService
from app.schemas.mool import (
    WorkSubmissionCreate,
    WorkSubmissionResponse,
    PeerReviewCreate,
    PeerReviewResponse,
    LevelUpRequestCreate,
    LevelUpRequestResponse,
    ReputationResponse,
    ReputationBreakdownResponse,
    ReviewerPrivilegesResponse,
    LevelUpApprovalResponse,
    ProjectAssessmentCreate,
    ProjectAssessmentResponse,
)

router = APIRouter()


@router.post("/work/submit", response_model=WorkSubmissionResponse, status_code=status.HTTP_201_CREATED)
def submit_work_for_review(
    submission: WorkSubmissionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit work for peer review.
    
    Creates a work submission and notifies eligible reviewers within the same guild.
    Eligible reviewers are guild members who are not direct collaborators (same squad).
    
    Implements Requirements 7.1, 7.6.
    """
    service = MoolService(db)
    
    try:
        work_submission = service.submit_work_for_review(
            user_id=current_user.id,
            squad_id=submission.squad_id,
            title=submission.title,
            description=submission.description,
            submission_url=submission.submission_url
        )
        
        return WorkSubmissionResponse(
            id=work_submission.id,
            user_id=work_submission.user_id,
            squad_id=work_submission.squad_id,
            title=work_submission.title,
            description=work_submission.description,
            submission_url=work_submission.submission_url,
            submitted_at=work_submission.submitted_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/work/{submission_id}/review", response_model=PeerReviewResponse, status_code=status.HTTP_201_CREATED)
def submit_peer_review(
    submission_id: UUID,
    review: PeerReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a peer review for a work submission.
    
    Calculates and awards reputation points to the reviewer based on:
    - Base points: 10
    - Reviewer level multiplier
    - Quality bonus for detailed reviews
    - Consistency bonus for quick reviews
    
    Implements Requirements 7.2, 7.3.
    """
    service = MoolService(db)
    
    # Check if user can review this submission
    can_review, reason = service.can_review_submission(current_user.id, submission_id)
    if not can_review:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason)
    
    try:
        peer_review = service.submit_peer_review(
            reviewer_id=current_user.id,
            submission_id=submission_id,
            review_content=review.review_content,
            rating=review.rating
        )
        
        return PeerReviewResponse(
            id=peer_review.id,
            submission_id=peer_review.submission_id,
            reviewer_id=peer_review.reviewer_id,
            review_content=peer_review.review_content,
            rating=peer_review.rating,
            reputation_awarded=peer_review.reputation_awarded,
            submitted_at=peer_review.submitted_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/users/{user_id}/reputation", response_model=ReputationResponse)
def get_user_reputation(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get total reputation points for a user.
    
    Implements Requirement 7.4.
    """
    service = MoolService(db)
    
    try:
        reputation = service.get_user_reputation(user_id)
        return ReputationResponse(
            user_id=user_id,
            reputation_points=reputation
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/users/{user_id}/reputation/breakdown", response_model=ReputationBreakdownResponse)
def get_user_reputation_breakdown(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get detailed breakdown of user's reputation points.
    
    Includes total reputation, review count, average per review, and recent reviews.
    
    Implements Requirement 7.4.
    """
    service = MoolService(db)
    
    try:
        breakdown = service.get_user_reputation_breakdown(user_id)
        return ReputationBreakdownResponse(**breakdown)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/users/{user_id}/reviewer-privileges", response_model=ReviewerPrivilegesResponse)
def get_reviewer_privileges(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get reviewer privileges for a user.
    
    Shows which submission levels the user can review based on their reputation.
    
    Implements Requirement 7.5.
    """
    service = MoolService(db)
    
    try:
        privileges = service.unlock_reviewer_privileges(user_id)
        return ReviewerPrivilegesResponse(**privileges)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/levelup/submit", response_model=LevelUpRequestResponse, status_code=status.HTTP_201_CREATED)
def submit_levelup_project(
    request: LevelUpRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a level-up project for assessment.
    
    Creates a level-up request that will undergo:
    1. AI Guild Master automated quality assessment
    2. Two peer reviews from senior guild members (2+ levels higher)
    
    Implements Requirements 8.1, 8.2.
    """
    service = MoolService(db)
    
    try:
        levelup_request = service.submit_levelup_project(
            user_id=current_user.id,
            project_title=request.project_title,
            project_description=request.project_description,
            project_url=request.project_url
        )
        
        return LevelUpRequestResponse(
            id=levelup_request.id,
            user_id=levelup_request.user_id,
            current_level=levelup_request.current_level,
            target_level=levelup_request.target_level,
            project_title=levelup_request.project_title,
            project_description=levelup_request.project_description,
            project_url=levelup_request.project_url,
            status=levelup_request.status,
            created_at=levelup_request.created_at,
            completed_at=levelup_request.completed_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/levelup/{request_id}/status", response_model=LevelUpRequestResponse)
def get_levelup_status(
    request_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get status of a level-up request.
    
    Returns the current status and details of a level-up request.
    
    Implements Requirements 8.1-8.7.
    """
    service = MoolService(db)
    
    levelup_request = service.get_levelup_request(request_id)
    if not levelup_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Level-up request {request_id} not found"
        )
    
    return LevelUpRequestResponse(
        id=levelup_request.id,
        user_id=levelup_request.user_id,
        current_level=levelup_request.current_level,
        target_level=levelup_request.target_level,
        project_title=levelup_request.project_title,
        project_description=levelup_request.project_description,
        project_url=levelup_request.project_url,
        status=levelup_request.status,
        created_at=levelup_request.created_at,
        completed_at=levelup_request.completed_at
    )


@router.post("/levelup/{request_id}/assess", response_model=ProjectAssessmentResponse, status_code=status.HTTP_201_CREATED)
def assess_levelup_project(
    request_id: UUID,
    assessment: ProjectAssessmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit an assessment for a level-up project.
    
    Can be used by:
    - AI Guild Master (assessment_type="ai")
    - Peer reviewers (assessment_type="peer")
    
    Implements Requirements 8.2, 8.3, 8.5.
    """
    service = MoolService(db)
    
    # Verify level-up request exists
    levelup_request = service.get_levelup_request(request_id)
    if not levelup_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Level-up request {request_id} not found"
        )
    
    # For peer assessments, verify reviewer is eligible
    if assessment.assessment_type == "peer":
        # Check if reviewer is at least 2 levels higher
        if current_user.current_level < levelup_request.current_level + 2:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient level to review. Must be at least level {levelup_request.current_level + 2}"
            )
    
    try:
        if assessment.approved:
            # Create approval assessment
            from app.models.mool import ProjectAssessment
            project_assessment = ProjectAssessment(
                levelup_request_id=request_id,
                assessment_type=assessment.assessment_type,
                assessed_by=str(current_user.id) if assessment.assessment_type == "peer" else "guild_master_ai",
                approved="true",
                feedback=assessment.feedback,
                assessed_at=datetime.utcnow()
            )
            db.add(project_assessment)
            db.commit()
            db.refresh(project_assessment)
            
            # Check if all approvals received and process level-up
            approval_result = service.process_levelup_approval(request_id)
            
            return ProjectAssessmentResponse(
                id=project_assessment.id,
                levelup_request_id=project_assessment.levelup_request_id,
                assessment_type=project_assessment.assessment_type,
                assessed_by=project_assessment.assessed_by,
                approved=True,
                feedback=project_assessment.feedback,
                assessed_at=project_assessment.assessed_at
            )
        else:
            # Create rejection assessment
            project_assessment = service.provide_rejection_feedback(
                levelup_request_id=request_id,
                assessor_id=str(current_user.id) if assessment.assessment_type == "peer" else "guild_master_ai",
                assessment_type=assessment.assessment_type,
                feedback=assessment.feedback
            )
            
            return ProjectAssessmentResponse(
                id=project_assessment.id,
                levelup_request_id=project_assessment.levelup_request_id,
                assessment_type=project_assessment.assessment_type,
                assessed_by=project_assessment.assessed_by,
                approved=False,
                feedback=project_assessment.feedback,
                assessed_at=project_assessment.assessed_at
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/users/{user_id}/levelup-requests", response_model=List[LevelUpRequestResponse])
def get_user_levelup_requests(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get all level-up requests for a user.
    
    Returns list of level-up requests ordered by creation date (newest first).
    
    Implements Requirements 8.1-8.7.
    """
    service = MoolService(db)
    
    levelup_requests = service.get_user_levelup_requests(user_id)
    
    return [
        LevelUpRequestResponse(
            id=req.id,
            user_id=req.user_id,
            current_level=req.current_level,
            target_level=req.target_level,
            project_title=req.project_title,
            project_description=req.project_description,
            project_url=req.project_url,
            status=req.status,
            created_at=req.created_at,
            completed_at=req.completed_at
        )
        for req in levelup_requests
    ]
