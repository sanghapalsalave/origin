"""
Unit tests for User and UserProfile models.

Tests password hashing, model creation, and relationships.
"""
import pytest
from uuid import uuid4
from datetime import datetime
from app.models.user import User, UserProfile


class TestUserModel:
    """Test cases for User model."""
    
    def test_user_creation(self):
        """Test basic user creation."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed_password",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert user.reputation_points == 0
        assert user.current_level == 1
    
    def test_set_password(self):
        """Test password hashing with bcrypt (12 rounds minimum)."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        plain_password = "SecurePassword123!"
        user.set_password(plain_password)
        
        # Password should be hashed
        assert user.password_hash != plain_password
        # Hash should start with bcrypt identifier
        assert user.password_hash.startswith("$2b$")
        # Verify the password works
        assert user.verify_password(plain_password) is True
        # Verify wrong password fails
        assert user.verify_password("WrongPassword") is False
    
    def test_verify_password_with_correct_password(self):
        """Test password verification with correct password."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        password = "MySecurePassword123"
        user.set_password(password)
        
        assert user.verify_password(password) is True
    
    def test_verify_password_with_incorrect_password(self):
        """Test password verification with incorrect password."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        user.set_password("CorrectPassword")
        
        assert user.verify_password("WrongPassword") is False
    
    def test_bcrypt_rounds_minimum_12(self):
        """Test that bcrypt uses minimum 12 rounds as per Requirement 15.1."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        user.set_password("TestPassword123")
        
        # Bcrypt hash format: $2b$<rounds>$<salt+hash>
        # Extract rounds from hash
        hash_parts = user.password_hash.split("$")
        rounds = int(hash_parts[2])
        
        # Verify minimum 12 rounds
        assert rounds >= 12, f"Bcrypt rounds ({rounds}) should be >= 12"
    
    def test_user_repr(self):
        """Test user string representation."""
        user_id = uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            password_hash="hash",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        repr_str = repr(user)
        assert "User" in repr_str
        assert str(user_id) in repr_str
        assert "test@example.com" in repr_str


class TestUserProfileModel:
    """Test cases for UserProfile model."""
    
    def test_user_profile_creation(self):
        """Test basic user profile creation."""
        user_id = uuid4()
        profile = UserProfile(
            id=uuid4(),
            user_id=user_id,
            display_name="Test User",
            interest_area="Python Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en",
            learning_velocity=2.5,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        assert profile.user_id == user_id
        assert profile.display_name == "Test User"
        assert profile.interest_area == "Python Development"
        assert profile.skill_level == 5
        assert profile.timezone == "America/New_York"
        assert profile.preferred_language == "en"
        assert profile.learning_velocity == 2.5
    
    def test_user_profile_with_portfolio_sources(self):
        """Test user profile with multiple portfolio sources."""
        profile = UserProfile(
            id=uuid4(),
            user_id=uuid4(),
            display_name="Test User",
            interest_area="Web Development",
            skill_level=7,
            timezone="Europe/London",
            preferred_language="en",
            github_url="https://github.com/testuser",
            linkedin_profile={"id": "12345", "name": "Test User"},
            portfolio_url="https://testuser.dev",
            resume_data={"skills": ["Python", "JavaScript"], "experience": 5},
            manual_skills=["React", "Node.js", "Docker"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        assert profile.github_url == "https://github.com/testuser"
        assert profile.linkedin_profile == {"id": "12345", "name": "Test User"}
        assert profile.portfolio_url == "https://testuser.dev"
        assert profile.resume_data == {"skills": ["Python", "JavaScript"], "experience": 5}
        assert profile.manual_skills == ["React", "Node.js", "Docker"]
    
    def test_user_profile_skill_level_range(self):
        """Test that skill level is within valid range (1-10)."""
        # Valid skill levels
        for level in range(1, 11):
            profile = UserProfile(
                id=uuid4(),
                user_id=uuid4(),
                display_name="Test User",
                interest_area="Testing",
                skill_level=level,
                timezone="UTC",
                preferred_language="en",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            assert 1 <= profile.skill_level <= 10
    
    def test_user_profile_default_learning_velocity(self):
        """Test that learning velocity defaults to 0.0."""
        profile = UserProfile(
            id=uuid4(),
            user_id=uuid4(),
            display_name="Test User",
            interest_area="Testing",
            skill_level=5,
            timezone="UTC",
            preferred_language="en",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        assert profile.learning_velocity == 0.0
    
    def test_user_profile_optional_fields(self):
        """Test that portfolio source fields are optional."""
        profile = UserProfile(
            id=uuid4(),
            user_id=uuid4(),
            display_name="Test User",
            interest_area="Testing",
            skill_level=5,
            timezone="UTC",
            preferred_language="en",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        assert profile.github_url is None
        assert profile.linkedin_profile is None
        assert profile.portfolio_url is None
        assert profile.resume_data is None
        assert profile.manual_skills is None
        assert profile.vector_embedding_id is None
    
    def test_user_profile_repr(self):
        """Test user profile string representation."""
        user_id = uuid4()
        profile = UserProfile(
            id=uuid4(),
            user_id=user_id,
            display_name="Test User",
            interest_area="Testing",
            skill_level=5,
            timezone="UTC",
            preferred_language="en",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        repr_str = repr(profile)
        assert "UserProfile" in repr_str
        assert str(user_id) in repr_str
        assert "Test User" in repr_str
        assert "5" in repr_str


class TestUserProfileRelationship:
    """Test cases for User-UserProfile relationship."""
    
    def test_user_profile_relationship_setup(self):
        """Test that User and UserProfile can be linked."""
        user_id = uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            password_hash="hash",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        profile = UserProfile(
            id=uuid4(),
            user_id=user_id,
            display_name="Test User",
            interest_area="Testing",
            skill_level=5,
            timezone="UTC",
            preferred_language="en",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Verify the foreign key relationship
        assert profile.user_id == user.id
