"""
Tests for Mool reputation system models.

Validates that WorkSubmission, PeerReview, LevelUpRequest, and ProjectAssessment
models are correctly defined with proper relationships and constraints.

Implements Requirements 7.1, 7.2, 8.1 (Mool reputation system).
"""
import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from app.models.user import User, UserProfile
from app.models.guild import Guild, GuildType
from app.models.squad import Squad, SquadStatus
from app.models.mool import (
    WorkSubmission,
    PeerReview,
    LevelUpRequest,
    ProjectAssessment,
    LevelUpStatus,
)


def test_work_submission_model_creation(test_db: Session):
    """Test WorkSubmission model can be created with required fields."""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash="hashed_password",
    )
    test_db.add(user)
    
    # Create test guild
    guild = Guild(
        id=uuid4(),
        name="Test Guild",
        interest_area="Python",
        guild_type=GuildType.PUBLIC,
    )
    test_db.add(guild)
    
    # Create test squad
    squad = Squad(
        id=uuid4(),
        guild_id=guild.id,
        name="Test Squad",
        status=SquadStatus.ACTIVE,
    )
    test_db.add(squad)
    test_db.flush()
    
    # Create work submission
    submission = WorkSubmission(
        id=uuid4(),
        user_id=user.id,
        squad_id=squad.id,
        title="My Project",
        description="A detailed description of my project",
        submission_url="https://github.com/user/project",
        submitted_at=datetime.utcnow(),
    )
    test_db.add(submission)
    test_db.commit()
    
    # Verify submission was created
    assert submission.id is not None
    assert submission.user_id == user.id
    assert submission.squad_id == squad.id
    assert submission.title == "My Project"
    assert submission.submission_url == "https://github.com/user/project"


def test_peer_review_model_creation(test_db: Session):
    """Test PeerReview model can be created with reputation calculation."""
    # Create test users
    submitter = User(
        id=uuid4(),
        email="submitter@example.com",
        password_hash="hashed_password",
    )
    reviewer = User(
        id=uuid4(),
        email="reviewer@example.com",
        password_hash="hashed_password",
        current_level=5,
    )
    test_db.add_all([submitter, reviewer])
    
    # Create test guild and squad
    guild = Guild(
        id=uuid4(),
        name="Test Guild",
        interest_area="Python",
        guild_type=GuildType.PUBLIC,
    )
    squad = Squad(
        id=uuid4(),
        guild_id=guild.id,
        name="Test Squad",
        status=SquadStatus.ACTIVE,
    )
    test_db.add_all([guild, squad])
    test_db.flush()
    
    # Create work submission
    submission = WorkSubmission(
        id=uuid4(),
        user_id=submitter.id,
        squad_id=squad.id,
        title="My Project",
        description="A detailed description",
        submission_url="https://github.com/user/project",
    )
    test_db.add(submission)
    test_db.flush()
    
    # Create peer review
    # Reputation calculation: base_points * (1 + reviewer_level * 0.1) + bonuses
    # Base: 10, Level 5: 10 * (1 + 5 * 0.1) = 10 * 1.5 = 15
    review = PeerReview(
        id=uuid4(),
        submission_id=submission.id,
        reviewer_id=reviewer.id,
        review_content="Excellent work! Very thorough implementation.",
        rating=5,
        reputation_awarded=15,  # Calculated based on reviewer level
        submitted_at=datetime.utcnow(),
    )
    test_db.add(review)
    test_db.commit()
    
    # Verify review was created
    assert review.id is not None
    assert review.submission_id == submission.id
    assert review.reviewer_id == reviewer.id
    assert review.rating == 5
    assert review.reputation_awarded == 15


def test_levelup_request_model_creation(test_db: Session):
    """Test LevelUpRequest model can be created with proper status."""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash="hashed_password",
        current_level=3,
    )
    test_db.add(user)
    test_db.flush()
    
    # Create level-up request
    levelup_request = LevelUpRequest(
        id=uuid4(),
        user_id=user.id,
        current_level=3,
        target_level=4,
        project_title="Advanced Python Project",
        project_description="A comprehensive project demonstrating advanced Python skills",
        project_url="https://github.com/user/advanced-project",
        status=LevelUpStatus.PENDING,
        created_at=datetime.utcnow(),
    )
    test_db.add(levelup_request)
    test_db.commit()
    
    # Verify request was created
    assert levelup_request.id is not None
    assert levelup_request.user_id == user.id
    assert levelup_request.current_level == 3
    assert levelup_request.target_level == 4
    assert levelup_request.status == LevelUpStatus.PENDING
    assert levelup_request.completed_at is None


def test_project_assessment_model_creation(test_db: Session):
    """Test ProjectAssessment model for AI and peer assessments."""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash="hashed_password",
        current_level=3,
    )
    test_db.add(user)
    test_db.flush()
    
    # Create level-up request
    levelup_request = LevelUpRequest(
        id=uuid4(),
        user_id=user.id,
        current_level=3,
        target_level=4,
        project_title="Advanced Python Project",
        project_description="A comprehensive project",
        project_url="https://github.com/user/project",
        status=LevelUpStatus.PENDING,
    )
    test_db.add(levelup_request)
    test_db.flush()
    
    # Create AI assessment
    ai_assessment = ProjectAssessment(
        id=uuid4(),
        levelup_request_id=levelup_request.id,
        assessment_type="ai",
        assessed_by="guild_master_ai",
        approved="true",
        feedback="Code quality is excellent. All requirements met.",
        assessed_at=datetime.utcnow(),
    )
    test_db.add(ai_assessment)
    test_db.commit()
    
    # Verify assessment was created
    assert ai_assessment.id is not None
    assert ai_assessment.levelup_request_id == levelup_request.id
    assert ai_assessment.assessment_type == "ai"
    assert ai_assessment.assessed_by == "guild_master_ai"
    assert ai_assessment.approved == "true"


def test_work_submission_relationships(test_db: Session):
    """Test WorkSubmission relationships with User, Squad, and PeerReview."""
    # Create test data
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash="hashed_password",
    )
    reviewer = User(
        id=uuid4(),
        email="reviewer@example.com",
        password_hash="hashed_password",
    )
    guild = Guild(
        id=uuid4(),
        name="Test Guild",
        interest_area="Python",
        guild_type=GuildType.PUBLIC,
    )
    squad = Squad(
        id=uuid4(),
        guild_id=guild.id,
        name="Test Squad",
        status=SquadStatus.ACTIVE,
    )
    test_db.add_all([user, reviewer, guild, squad])
    test_db.flush()
    
    # Create submission with reviews
    submission = WorkSubmission(
        id=uuid4(),
        user_id=user.id,
        squad_id=squad.id,
        title="My Project",
        description="Description",
        submission_url="https://github.com/user/project",
    )
    test_db.add(submission)
    test_db.flush()
    
    review = PeerReview(
        id=uuid4(),
        submission_id=submission.id,
        reviewer_id=reviewer.id,
        review_content="Great work!",
        rating=5,
        reputation_awarded=10,
    )
    test_db.add(review)
    test_db.commit()
    
    # Test relationships
    assert submission.user == user
    assert submission.squad == squad
    assert len(submission.reviews) == 1
    assert submission.reviews[0] == review
    assert review.submission == submission


def test_levelup_request_relationships(test_db: Session):
    """Test LevelUpRequest relationships with User and ProjectAssessment."""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash="hashed_password",
        current_level=3,
    )
    test_db.add(user)
    test_db.flush()
    
    # Create level-up request with assessments
    levelup_request = LevelUpRequest(
        id=uuid4(),
        user_id=user.id,
        current_level=3,
        target_level=4,
        project_title="Project",
        project_description="Description",
        project_url="https://github.com/user/project",
        status=LevelUpStatus.PENDING,
    )
    test_db.add(levelup_request)
    test_db.flush()
    
    # Add AI assessment
    ai_assessment = ProjectAssessment(
        id=uuid4(),
        levelup_request_id=levelup_request.id,
        assessment_type="ai",
        assessed_by="guild_master_ai",
        approved="true",
        feedback="Approved",
    )
    test_db.add(ai_assessment)
    test_db.commit()
    
    # Test relationships
    assert levelup_request.user == user
    assert len(levelup_request.assessments) == 1
    assert levelup_request.assessments[0] == ai_assessment
    assert ai_assessment.levelup_request == levelup_request


def test_levelup_status_enum_values():
    """Test LevelUpStatus enum has all required values."""
    assert LevelUpStatus.PENDING == "pending"
    assert LevelUpStatus.AI_APPROVED == "ai_approved"
    assert LevelUpStatus.PEER_REVIEW == "peer_review"
    assert LevelUpStatus.APPROVED == "approved"
    assert LevelUpStatus.REJECTED == "rejected"


def test_work_submission_cascade_delete(test_db: Session):
    """Test that deleting a user cascades to work submissions."""
    # Create test data
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash="hashed_password",
    )
    guild = Guild(
        id=uuid4(),
        name="Test Guild",
        interest_area="Python",
        guild_type=GuildType.PUBLIC,
    )
    squad = Squad(
        id=uuid4(),
        guild_id=guild.id,
        name="Test Squad",
        status=SquadStatus.ACTIVE,
    )
    test_db.add_all([user, guild, squad])
    test_db.flush()
    
    submission = WorkSubmission(
        id=uuid4(),
        user_id=user.id,
        squad_id=squad.id,
        title="My Project",
        description="Description",
        submission_url="https://github.com/user/project",
    )
    test_db.add(submission)
    test_db.commit()
    
    submission_id = submission.id
    
    # Delete user
    test_db.delete(user)
    test_db.commit()
    
    # Verify submission was also deleted (cascade)
    deleted_submission = test_db.query(WorkSubmission).filter_by(id=submission_id).first()
    assert deleted_submission is None


def test_peer_review_cascade_delete(test_db: Session):
    """Test that deleting a submission cascades to peer reviews."""
    # Create test data
    user = User(
        id=uuid4(),
        email="submitter@example.com",
        password_hash="hashed_password",
    )
    reviewer = User(
        id=uuid4(),
        email="reviewer@example.com",
        password_hash="hashed_password",
    )
    guild = Guild(
        id=uuid4(),
        name="Test Guild",
        interest_area="Python",
        guild_type=GuildType.PUBLIC,
    )
    squad = Squad(
        id=uuid4(),
        guild_id=guild.id,
        name="Test Squad",
        status=SquadStatus.ACTIVE,
    )
    test_db.add_all([user, reviewer, guild, squad])
    test_db.flush()
    
    submission = WorkSubmission(
        id=uuid4(),
        user_id=user.id,
        squad_id=squad.id,
        title="My Project",
        description="Description",
        submission_url="https://github.com/user/project",
    )
    test_db.add(submission)
    test_db.flush()
    
    review = PeerReview(
        id=uuid4(),
        submission_id=submission.id,
        reviewer_id=reviewer.id,
        review_content="Great work!",
        rating=5,
        reputation_awarded=10,
    )
    test_db.add(review)
    test_db.commit()
    
    review_id = review.id
    
    # Delete submission
    test_db.delete(submission)
    test_db.commit()
    
    # Verify review was also deleted (cascade)
    deleted_review = test_db.query(PeerReview).filter_by(id=review_id).first()
    assert deleted_review is None
