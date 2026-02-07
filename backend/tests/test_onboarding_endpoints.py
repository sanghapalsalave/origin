"""
Tests for onboarding API endpoints.

Tests Requirements:
- 1.1: Interest selection interface
- 1.2: Multiple portfolio input options
- 1.7: Manual entry option
- 1.9: Create user account with vector embedding
- 1.11: Collect timezone and preferred language
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User, UserProfile
from app.models.skill_assessment import SkillAssessment, AssessmentSource
from app.services.auth_service import AuthService


@pytest.fixture
def test_user(test_db: Session):
    """Create a test user."""
    auth_service = AuthService(test_db)
    user = auth_service.register_user(
        email="test@example.com",
        password="TestPassword123!"
    )
    return user


@pytest.fixture
def auth_headers(test_user: User, test_db: Session):
    """Get authentication headers for test user."""
    auth_service = AuthService(test_db)
    token = auth_service.login("test@example.com", "TestPassword123!")
    return {"Authorization": f"Bearer {token.access_token}"}


def test_set_interests(client: TestClient, auth_headers: dict):
    """
    Test setting user interests during onboarding.
    
    Validates Requirement 1.1: Interest selection interface
    """
    response = client.post(
        "/api/v1/onboarding/interests",
        json={"interest_area": "Web Development"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["interest_area"] == "Web Development"


def test_set_interests_invalid(client: TestClient, auth_headers: dict):
    """Test setting interests with invalid data."""
    response = client.post(
        "/api/v1/onboarding/interests",
        json={"interest_area": ""},
        headers=auth_headers
    )
    
    assert response.status_code == 422  # Validation error


def test_submit_portfolio_manual(client: TestClient, auth_headers: dict):
    """
    Test submitting manual portfolio data.
    
    Validates Requirements:
    - 1.2: Multiple portfolio input options
    - 1.7: Manual entry option
    """
    response = client.post(
        "/api/v1/onboarding/portfolio",
        json={
            "method": "manual",
            "manual_skills": ["Python", "JavaScript", "React"],
            "manual_experience_years": 3.5,
            "manual_proficiency_level": 7
        },
        headers=auth_headers
    )
    
    assert response.status_code == 202  # Accepted (async processing)
    data = response.json()
    assert data["success"] is True
    assert data["method"] == "manual"
    assert "task_id" in data
    assert data["status"] == "processing"


def test_submit_portfolio_github(client: TestClient, auth_headers: dict):
    """
    Test submitting GitHub portfolio.
    
    Validates Requirement 1.3: GitHub integration
    """
    response = client.post(
        "/api/v1/onboarding/portfolio",
        json={
            "method": "github",
            "github_url": "https://github.com/testuser"
        },
        headers=auth_headers
    )
    
    assert response.status_code == 202
    data = response.json()
    assert data["success"] is True
    assert data["method"] == "github"
    assert "task_id" in data


def test_submit_portfolio_missing_data(client: TestClient, auth_headers: dict):
    """Test submitting portfolio without required data."""
    response = client.post(
        "/api/v1/onboarding/portfolio",
        json={
            "method": "github"
            # Missing github_url
        },
        headers=auth_headers
    )
    
    assert response.status_code == 422  # Validation error


def test_complete_onboarding(
    client: TestClient,
    auth_headers: dict,
    test_user: User,
    test_db: Session
):
    """
    Test completing onboarding and creating profile.
    
    Validates Requirements:
    - 1.9: Create user account with vector embedding
    - 1.11: Collect timezone and preferred language
    """
    # First create a manual assessment
    from app.services.portfolio_analysis_service import PortfolioAnalysisService
    portfolio_service = PortfolioAnalysisService(test_db)
    assessment = portfolio_service.create_manual_assessment(
        skills=["Python", "FastAPI"],
        experience_years=3.0,
        proficiency_level=7,
        user_id=test_user.id
    )
    
    # Complete onboarding
    response = client.post(
        "/api/v1/onboarding/complete",
        json={
            "display_name": "Test User",
            "timezone": "America/New_York",
            "preferred_language": "en",
            "confirmed_skill_level": 7
        },
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "profile" in data
    assert data["profile"]["display_name"] == "Test User"
    assert data["profile"]["timezone"] == "America/New_York"
    assert data["profile"]["preferred_language"] == "en"
    assert data["profile"]["skill_level"] == 7
    
    # Check status
    assert "status" in data
    assert data["status"]["profile_created"] is True


def test_complete_onboarding_duplicate(
    client: TestClient,
    auth_headers: dict,
    test_user: User,
    test_db: Session
):
    """Test completing onboarding when profile already exists."""
    # Create profile first
    from app.services.user_service import UserService
    user_service = UserService(test_db)
    user_service.create_profile(
        user_id=test_user.id,
        display_name="Existing User",
        interest_area="Web Development",
        timezone="America/New_York",
        preferred_language="en",
        skill_level=5
    )
    
    # Try to complete onboarding again
    response = client.post(
        "/api/v1/onboarding/complete",
        json={
            "display_name": "Test User",
            "timezone": "America/New_York",
            "preferred_language": "en"
        },
        headers=auth_headers
    )
    
    assert response.status_code == 409  # Conflict


def test_get_onboarding_status(
    client: TestClient,
    auth_headers: dict,
    test_user: User,
    test_db: Session
):
    """Test getting onboarding status."""
    # Create an assessment
    from app.services.portfolio_analysis_service import PortfolioAnalysisService
    portfolio_service = PortfolioAnalysisService(test_db)
    assessment = portfolio_service.create_manual_assessment(
        skills=["Python"],
        experience_years=2.0,
        proficiency_level=6,
        user_id=test_user.id
    )
    
    response = client.get(
        "/api/v1/onboarding/status",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user.id)
    assert data["skill_assessments_count"] == 1
    assert data["combined_skill_level"] == 6
    assert data["profile_created"] is False
    assert "manual" in data["portfolio_methods_used"]


def test_get_portfolio_assessments(
    client: TestClient,
    auth_headers: dict,
    test_user: User,
    test_db: Session
):
    """Test getting portfolio assessments."""
    # Create multiple assessments
    from app.services.portfolio_analysis_service import PortfolioAnalysisService
    portfolio_service = PortfolioAnalysisService(test_db)
    
    assessment1 = portfolio_service.create_manual_assessment(
        skills=["Python", "Django"],
        experience_years=3.0,
        proficiency_level=7,
        user_id=test_user.id
    )
    
    assessment2 = portfolio_service.create_manual_assessment(
        skills=["JavaScript", "React"],
        experience_years=2.0,
        proficiency_level=6,
        user_id=test_user.id
    )
    
    response = client.get(
        "/api/v1/onboarding/assessments",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all("assessment_id" in item for item in data)
    assert all("skill_level" in item for item in data)
    assert all("detected_skills" in item for item in data)


def test_onboarding_without_auth(client: TestClient):
    """Test that onboarding endpoints require authentication."""
    response = client.post(
        "/api/v1/onboarding/interests",
        json={"interest_area": "Web Development"}
    )
    
    assert response.status_code == 403  # Forbidden (no auth)


def test_complete_onboarding_invalid_timezone(
    client: TestClient,
    auth_headers: dict
):
    """Test completing onboarding with invalid timezone."""
    response = client.post(
        "/api/v1/onboarding/complete",
        json={
            "display_name": "Test User",
            "timezone": "InvalidTimezone",
            "preferred_language": "en"
        },
        headers=auth_headers
    )
    
    assert response.status_code == 422  # Validation error


def test_complete_onboarding_invalid_language(
    client: TestClient,
    auth_headers: dict
):
    """Test completing onboarding with invalid language code."""
    response = client.post(
        "/api/v1/onboarding/complete",
        json={
            "display_name": "Test User",
            "timezone": "America/New_York",
            "preferred_language": "english"  # Should be 2-letter code
        },
        headers=auth_headers
    )
    
    assert response.status_code == 422  # Validation error
