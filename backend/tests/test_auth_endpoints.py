"""
Tests for authentication API endpoints.

Tests POST /auth/register, /auth/login, /auth/logout, /auth/refresh endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.base import Base, get_db
from app.core.config import settings


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auth_endpoints.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create and drop test database for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestAuthEndpoints:
    """Test suite for authentication endpoints."""
    
    def test_register_success(self):
        """Test successful user registration."""
        response = client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
                "display_name": "Test User",
                "interest_area": "Web Development",
                "timezone": "America/New_York",
                "preferred_language": "en"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        
        # Verify user data
        user = data["user"]
        assert user["email"] == "test@example.com"
        assert "id" in user
        assert "created_at" in user
    
    def test_register_duplicate_email(self):
        """Test registration with duplicate email fails."""
        # Register first user
        client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePass123!",
                "display_name": "First User",
                "interest_area": "Web Development",
                "timezone": "America/New_York",
                "preferred_language": "en"
            }
        )
        
        # Try to register with same email
        response = client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "DifferentPass456!",
                "display_name": "Second User",
                "interest_area": "Data Science",
                "timezone": "America/Los_Angeles",
                "preferred_language": "en"
            }
        )
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()
    
    def test_register_invalid_email(self):
        """Test registration with invalid email format fails."""
        response = client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123!",
                "display_name": "Test User",
                "interest_area": "Web Development",
                "timezone": "America/New_York",
                "preferred_language": "en"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_register_short_password(self):
        """Test registration with short password fails."""
        response = client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "test@example.com",
                "password": "short",
                "display_name": "Test User",
                "interest_area": "Web Development",
                "timezone": "America/New_York",
                "preferred_language": "en"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_login_success(self):
        """Test successful user login."""
        # First register a user
        client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "login@example.com",
                "password": "SecurePass123!",
                "display_name": "Login User",
                "interest_area": "Web Development",
                "timezone": "America/New_York",
                "preferred_language": "en"
            }
        )
        
        # Now login
        response = client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={
                "email": "login@example.com",
                "password": "SecurePass123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        
        # Verify user data
        user = data["user"]
        assert user["email"] == "login@example.com"
        assert "id" in user
        assert "reputation_points" in user
        assert "current_level" in user
    
    def test_login_invalid_email(self):
        """Test login with non-existent email fails."""
        response = client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123!"
            }
        )
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    def test_login_wrong_password(self):
        """Test login with wrong password fails."""
        # Register a user
        client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "wrongpass@example.com",
                "password": "CorrectPass123!",
                "display_name": "Test User",
                "interest_area": "Web Development",
                "timezone": "America/New_York",
                "preferred_language": "en"
            }
        )
        
        # Try to login with wrong password
        response = client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={
                "email": "wrongpass@example.com",
                "password": "WrongPass123!"
            }
        )
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    def test_refresh_token_success(self):
        """Test successful token refresh."""
        # Register and get tokens
        register_response = client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "refresh@example.com",
                "password": "SecurePass123!",
                "display_name": "Refresh User",
                "interest_area": "Web Development",
                "timezone": "America/New_York",
                "preferred_language": "en"
            }
        )
        
        refresh_token = register_response.json()["refresh_token"]
        
        # Refresh the token
        response = client.post(
            f"{settings.API_V1_STR}/auth/refresh",
            json={
                "refresh_token": refresh_token
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        
        # Verify we got a new access token
        assert data["access_token"] != register_response.json()["access_token"]
        # Refresh token should be the same
        assert data["refresh_token"] == refresh_token
    
    def test_refresh_token_invalid(self):
        """Test token refresh with invalid token fails."""
        response = client.post(
            f"{settings.API_V1_STR}/auth/refresh",
            json={
                "refresh_token": "invalid.token.here"
            }
        )
        
        assert response.status_code == 401
    
    def test_logout_success(self):
        """Test successful logout."""
        # Register a user
        register_response = client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "logout@example.com",
                "password": "SecurePass123!",
                "display_name": "Logout User",
                "interest_area": "Web Development",
                "timezone": "America/New_York",
                "preferred_language": "en"
            }
        )
        
        access_token = register_response.json()["access_token"]
        
        # Logout with authentication header
        response = client.post(
            f"{settings.API_V1_STR}/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "logged out" in data["message"].lower()
    
    def test_logout_without_token(self):
        """Test logout without authentication token fails."""
        response = client.post(
            f"{settings.API_V1_STR}/auth/logout"
        )
        
        assert response.status_code == 403  # Forbidden (no credentials)
    
    def test_register_missing_fields(self):
        """Test registration with missing required fields fails."""
        response = client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": "incomplete@example.com",
                "password": "SecurePass123!"
                # Missing display_name, interest_area, timezone, preferred_language
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_login_missing_fields(self):
        """Test login with missing fields fails."""
        response = client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={
                "email": "test@example.com"
                # Missing password
            }
        )
        
        assert response.status_code == 422  # Validation error

