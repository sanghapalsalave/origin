"""
Basic tests for onboarding functionality.

Tests the core onboarding flow without requiring full integration.
"""
import pytest
from uuid import uuid4
from sqlalchemy.orm import Session
from app.models.user import User
from app.services.user_service import UserService
from app.services.portfolio_analysis_service import PortfolioAnalysisService


def test_create_manual_assessment(test_db: Session):
    """Test creating a manual skill assessment."""
    # Create a test user
    user = User(
        email="test@example.com",
        password_hash="hashed_password"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # Create manual assessment
    portfolio_service = PortfolioAnalysisService(test_db)
    assessment = portfolio_service.create_manual_assessment(
        skills=["Python", "FastAPI", "PostgreSQL"],
        experience_years=3.5,
        proficiency_level=7,
        user_id=user.id
    )
    
    assert assessment is not None
    assert assessment.skill_level == 7
    assert assessment.experience_years == 3.5
    assert len(assessment.detected_skills) == 3
    assert "Python" in assessment.detected_skills
    assert assessment.confidence_score > 0


def test_create_profile(test_db: Session):
    """Test creating a user profile with vector embedding generation."""
    # Create a test user
    user = User(
        email="test2@example.com",
        password_hash="hashed_password"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # Create profile
    user_service = UserService(test_db)
    
    # Mock the vector embedding generation since Pinecone may not be configured
    from unittest.mock import patch, MagicMock
    from app.models.skill_assessment import VectorEmbedding
    
    mock_embedding = VectorEmbedding(
        user_id=user.id,
        pinecone_id=f"user_{user.id}",
        skill_level=7,
        learning_velocity=0.0,
        timezone_offset=-5.0,
        language_code="en",
        interest_area="Web Development",
        embedding_version="v1",
        dimensions=384
    )
    
    with patch.object(
        user_service.portfolio_service,
        'generate_vector_embedding',
        return_value=mock_embedding
    ):
        profile = user_service.create_profile(
            user_id=user.id,
            display_name="Test User",
            interest_area="Web Development",
            timezone="America/New_York",
            preferred_language="en",
            skill_level=7
        )
    
    assert profile is not None
    assert profile.display_name == "Test User"
    assert profile.interest_area == "Web Development"
    assert profile.timezone == "America/New_York"
    assert profile.preferred_language == "en"
    assert profile.skill_level == 7
    # Verify vector embedding ID was set
    assert profile.vector_embedding_id is not None
    assert profile.vector_embedding_id == f"user_{user.id}"


def test_calculate_combined_skill_level(test_db: Session):
    """Test calculating combined skill level from multiple assessments."""
    # Create a test user
    user = User(
        email="test3@example.com",
        password_hash="hashed_password"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # Create multiple assessments
    portfolio_service = PortfolioAnalysisService(test_db)
    
    assessment1 = portfolio_service.create_manual_assessment(
        skills=["Python", "Django"],
        experience_years=3.0,
        proficiency_level=7,
        user_id=user.id
    )
    
    assessment2 = portfolio_service.create_manual_assessment(
        skills=["JavaScript", "React"],
        experience_years=2.0,
        proficiency_level=6,
        user_id=user.id
    )
    
    # Calculate combined skill level
    user_service = UserService(test_db)
    combined_level = user_service._calculate_combined_skill_level(user.id)
    
    assert combined_level is not None
    assert 1 <= combined_level <= 10
    # Should be somewhere between 6 and 7
    assert combined_level in [6, 7]


def test_get_skill_assessments(test_db: Session):
    """Test retrieving skill assessments for a user."""
    # Create a test user
    user = User(
        email="test4@example.com",
        password_hash="hashed_password"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # Create assessments
    portfolio_service = PortfolioAnalysisService(test_db)
    
    assessment1 = portfolio_service.create_manual_assessment(
        skills=["Python"],
        experience_years=3.0,
        proficiency_level=7,
        user_id=user.id
    )
    
    assessment2 = portfolio_service.create_manual_assessment(
        skills=["JavaScript"],
        experience_years=2.0,
        proficiency_level=6,
        user_id=user.id
    )
    
    # Get assessments
    user_service = UserService(test_db)
    assessments = user_service.get_skill_assessments(user.id)
    
    assert len(assessments) == 2
    assert all(a.user_id == user.id for a in assessments)


def test_update_profile(test_db: Session):
    """Test updating a user profile."""
    # Create a test user
    user = User(
        email="test5@example.com",
        password_hash="hashed_password"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # Create profile
    user_service = UserService(test_db)
    profile = user_service.create_profile(
        user_id=user.id,
        display_name="Original Name",
        interest_area="Web Development",
        timezone="America/New_York",
        preferred_language="en",
        skill_level=5
    )
    
    # Update profile
    updated_profile = user_service.update_profile(
        user_id=user.id,
        updates={
            "display_name": "Updated Name",
            "skill_level": 7
        }
    )
    
    assert updated_profile.display_name == "Updated Name"
    assert updated_profile.skill_level == 7
    assert updated_profile.interest_area == "Web Development"  # Unchanged


def test_profile_already_exists_error(test_db: Session):
    """Test that creating a duplicate profile raises an error."""
    # Create a test user
    user = User(
        email="test6@example.com",
        password_hash="hashed_password"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # Create profile
    user_service = UserService(test_db)
    profile = user_service.create_profile(
        user_id=user.id,
        display_name="Test User",
        interest_area="Web Development",
        timezone="America/New_York",
        preferred_language="en",
        skill_level=5
    )
    
    # Try to create another profile for the same user
    with pytest.raises(ValueError, match="Profile already exists"):
        user_service.create_profile(
            user_id=user.id,
            display_name="Another Name",
            interest_area="Data Science",
            timezone="America/Los_Angeles",
            preferred_language="en",
            skill_level=6
        )
