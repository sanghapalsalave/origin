"""
Tests for UserService.

Tests profile creation with required fields including timezone, language,
and vector embedding generation.

Validates Requirements 1.9, 1.11.
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from app.models.user import User, UserProfile
from app.models.skill_assessment import VectorEmbedding
from app.services.user_service import UserService
from app.services.portfolio_analysis_service import PortfolioAnalysisService


class TestCreateProfile:
    """Tests for create_profile method."""
    
    def test_create_profile_with_all_required_fields(self, test_db: Session):
        """Test creating a profile with all required fields."""
        # Create a test user
        user = User(
            email="test@example.com",
            password_hash="hashed_password"
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        # Mock the vector embedding generation
        user_service = UserService(test_db)
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
            # Create profile
            profile = user_service.create_profile(
                user_id=user.id,
                display_name="Test User",
                interest_area="Web Development",
                timezone="America/New_York",
                preferred_language="en",
                skill_level=7
            )
        
        # Verify profile was created with all required fields
        assert profile is not None
        assert profile.user_id == user.id
        assert profile.display_name == "Test User"
        assert profile.interest_area == "Web Development"
        assert profile.timezone == "America/New_York"
        assert profile.preferred_language == "en"
        assert profile.skill_level == 7
        assert profile.vector_embedding_id is not None
        assert profile.vector_embedding_id == f"user_{user.id}"
    
    def test_create_profile_validates_timezone_required(self, test_db: Session):
        """Test that timezone is required for profile creation."""
        user = User(email="test2@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        user_service = UserService(test_db)
        
        with pytest.raises(ValueError, match="Timezone is required"):
            user_service.create_profile(
                user_id=user.id,
                display_name="Test User",
                interest_area="Web Development",
                timezone="",  # Empty timezone
                preferred_language="en",
                skill_level=5
            )
    
    def test_create_profile_validates_language_required(self, test_db: Session):
        """Test that preferred language is required for profile creation."""
        user = User(email="test3@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        user_service = UserService(test_db)
        
        with pytest.raises(ValueError, match="Preferred language is required"):
            user_service.create_profile(
                user_id=user.id,
                display_name="Test User",
                interest_area="Web Development",
                timezone="America/New_York",
                preferred_language="",  # Empty language
                skill_level=5
            )
    
    def test_create_profile_validates_interest_area_required(self, test_db: Session):
        """Test that interest area is required for profile creation."""
        user = User(email="test4@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        user_service = UserService(test_db)
        
        with pytest.raises(ValueError, match="Interest area is required"):
            user_service.create_profile(
                user_id=user.id,
                display_name="Test User",
                interest_area="",  # Empty interest area
                timezone="America/New_York",
                preferred_language="en",
                skill_level=5
            )
    
    def test_create_profile_validates_skill_level_range(self, test_db: Session):
        """Test that skill level must be between 1 and 10."""
        user = User(email="test5@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        user_service = UserService(test_db)
        
        # Test skill level too low
        with pytest.raises(ValueError, match="Skill level must be between 1 and 10"):
            user_service.create_profile(
                user_id=user.id,
                display_name="Test User",
                interest_area="Web Development",
                timezone="America/New_York",
                preferred_language="en",
                skill_level=0
            )
        
        # Test skill level too high
        with pytest.raises(ValueError, match="Skill level must be between 1 and 10"):
            user_service.create_profile(
                user_id=user.id,
                display_name="Test User",
                interest_area="Web Development",
                timezone="America/New_York",
                preferred_language="en",
                skill_level=11
            )
    
    def test_create_profile_generates_vector_embedding(self, test_db: Session):
        """Test that profile creation generates a vector embedding."""
        user = User(email="test6@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        user_service = UserService(test_db)
        
        # Mock the embedding generation to verify it's called
        mock_embedding = VectorEmbedding(
            user_id=user.id,
            pinecone_id=f"user_{user.id}",
            skill_level=5,
            learning_velocity=0.0,
            timezone_offset=-5.0,
            language_code="en",
            interest_area="Data Science",
            embedding_version="v1",
            dimensions=384
        )
        
        with patch.object(
            user_service.portfolio_service,
            'generate_vector_embedding',
            return_value=mock_embedding
        ) as mock_generate:
            profile = user_service.create_profile(
                user_id=user.id,
                display_name="Test User",
                interest_area="Data Science",
                timezone="America/New_York",
                preferred_language="en",
                skill_level=5
            )
            
            # Verify generate_vector_embedding was called with correct parameters
            mock_generate.assert_called_once_with(
                user_id=user.id,
                skill_level=5,
                learning_velocity=0.0,
                timezone="America/New_York",
                language="en",
                interest_area="Data Science"
            )
            
            # Verify profile has embedding ID
            assert profile.vector_embedding_id is not None
    
    def test_create_profile_handles_embedding_generation_failure(self, test_db: Session):
        """Test that profile creation fails gracefully if embedding generation fails."""
        user = User(email="test7@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        user_service = UserService(test_db)
        
        # Mock embedding generation to raise an exception
        with patch.object(
            user_service.portfolio_service,
            'generate_vector_embedding',
            side_effect=Exception("Pinecone connection failed")
        ):
            with pytest.raises(ValueError, match="Failed to generate vector embedding"):
                user_service.create_profile(
                    user_id=user.id,
                    display_name="Test User",
                    interest_area="Web Development",
                    timezone="America/New_York",
                    preferred_language="en",
                    skill_level=5
                )
        
        # Verify profile was not created
        profile = test_db.query(UserProfile).filter(
            UserProfile.user_id == user.id
        ).first()
        assert profile is None
    
    def test_create_profile_defaults_skill_level_when_not_provided(self, test_db: Session):
        """Test that skill level defaults to 5 when not provided and no assessments exist."""
        user = User(email="test8@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        user_service = UserService(test_db)
        
        mock_embedding = VectorEmbedding(
            user_id=user.id,
            pinecone_id=f"user_{user.id}",
            skill_level=5,
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
                preferred_language="en"
                # skill_level not provided
            )
        
        assert profile.skill_level == 5
    
    def test_create_profile_calculates_skill_level_from_assessments(self, test_db: Session):
        """Test that skill level is calculated from assessments when not provided."""
        user = User(email="test9@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        # Create skill assessments
        portfolio_service = PortfolioAnalysisService(test_db)
        portfolio_service.create_manual_assessment(
            skills=["Python", "Django"],
            experience_years=3.0,
            proficiency_level=7,
            user_id=user.id
        )
        
        user_service = UserService(test_db)
        
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
                preferred_language="en"
                # skill_level not provided, should be calculated from assessment
            )
        
        assert profile.skill_level == 7
    
    def test_create_profile_prevents_duplicate_profiles(self, test_db: Session):
        """Test that creating a duplicate profile raises an error."""
        user = User(email="test10@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        user_service = UserService(test_db)
        
        mock_embedding = VectorEmbedding(
            user_id=user.id,
            pinecone_id=f"user_{user.id}",
            skill_level=5,
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
            # Create first profile
            user_service.create_profile(
                user_id=user.id,
                display_name="Test User",
                interest_area="Web Development",
                timezone="America/New_York",
                preferred_language="en",
                skill_level=5
            )
            
            # Try to create second profile
            with pytest.raises(ValueError, match="Profile already exists"):
                user_service.create_profile(
                    user_id=user.id,
                    display_name="Another Name",
                    interest_area="Data Science",
                    timezone="America/Los_Angeles",
                    preferred_language="es",
                    skill_level=6
                )
    
    def test_create_profile_validates_user_exists(self, test_db: Session):
        """Test that profile creation fails if user doesn't exist."""
        user_service = UserService(test_db)
        non_existent_user_id = uuid4()
        
        with pytest.raises(ValueError, match="User not found"):
            user_service.create_profile(
                user_id=non_existent_user_id,
                display_name="Test User",
                interest_area="Web Development",
                timezone="America/New_York",
                preferred_language="en",
                skill_level=5
            )


class TestUpdateVectorEmbedding:
    """Tests for update_vector_embedding method."""
    
    def test_update_vector_embedding_regenerates_embedding(self, test_db: Session):
        """Test that updating vector embedding regenerates it with current profile data."""
        user = User(email="test11@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        # Create profile
        profile = UserProfile(
            user_id=user.id,
            display_name="Test User",
            interest_area="Web Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en",
            learning_velocity=2.5,
            vector_embedding_id="old_embedding_id"
        )
        test_db.add(profile)
        test_db.commit()
        test_db.refresh(profile)
        
        user_service = UserService(test_db)
        
        # Mock new embedding
        new_embedding = VectorEmbedding(
            user_id=user.id,
            pinecone_id=f"user_{user.id}_updated",
            skill_level=5,
            learning_velocity=2.5,
            timezone_offset=-5.0,
            language_code="en",
            interest_area="Web Development",
            embedding_version="v1",
            dimensions=384
        )
        
        with patch.object(
            user_service.portfolio_service,
            'generate_vector_embedding',
            return_value=new_embedding
        ) as mock_generate:
            updated_embedding = user_service.update_vector_embedding(user.id)
            
            # Verify generate_vector_embedding was called with updated profile data
            mock_generate.assert_called_once_with(
                user_id=user.id,
                skill_level=5,
                learning_velocity=2.5,
                timezone="America/New_York",
                language="en",
                interest_area="Web Development"
            )
            
            # Verify profile was updated with new embedding ID
            test_db.refresh(profile)
            assert profile.vector_embedding_id == f"user_{user.id}_updated"
    
    def test_update_vector_embedding_fails_if_profile_not_found(self, test_db: Session):
        """Test that updating vector embedding fails if profile doesn't exist."""
        user_service = UserService(test_db)
        non_existent_user_id = uuid4()
        
        with pytest.raises(ValueError, match="Profile not found"):
            user_service.update_vector_embedding(non_existent_user_id)


class TestGetProfile:
    """Tests for get_profile method."""
    
    def test_get_profile_returns_profile(self, test_db: Session):
        """Test that get_profile returns the user's profile."""
        user = User(email="test12@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        profile = UserProfile(
            user_id=user.id,
            display_name="Test User",
            interest_area="Web Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en",
            learning_velocity=0.0,
            vector_embedding_id="test_embedding_id"
        )
        test_db.add(profile)
        test_db.commit()
        test_db.refresh(profile)
        
        user_service = UserService(test_db)
        retrieved_profile = user_service.get_profile(user.id)
        
        assert retrieved_profile is not None
        assert retrieved_profile.user_id == user.id
        assert retrieved_profile.display_name == "Test User"
    
    def test_get_profile_returns_none_if_not_found(self, test_db: Session):
        """Test that get_profile returns None if profile doesn't exist."""
        user_service = UserService(test_db)
        non_existent_user_id = uuid4()
        
        profile = user_service.get_profile(non_existent_user_id)
        assert profile is None



class TestUpdatePortfolioSources:
    """Tests for update_portfolio_sources method."""
    
    def test_update_portfolio_sources_updates_github_url(self, test_db: Session):
        """Test that updating GitHub URL updates the profile."""
        user = User(email="test13@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        profile = UserProfile(
            user_id=user.id,
            display_name="Test User",
            interest_area="Web Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en",
            learning_velocity=0.0,
            vector_embedding_id="test_embedding_id"
        )
        test_db.add(profile)
        test_db.commit()
        test_db.refresh(profile)
        
        user_service = UserService(test_db)
        
        # Update without triggering reassessment
        updated_profile = user_service.update_portfolio_sources(
            user_id=user.id,
            github_url="https://github.com/testuser",
            trigger_reassessment=False
        )
        
        assert updated_profile.github_url == "https://github.com/testuser"
    
    def test_update_portfolio_sources_updates_multiple_sources(self, test_db: Session):
        """Test that updating multiple sources updates all fields."""
        user = User(email="test14@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        profile = UserProfile(
            user_id=user.id,
            display_name="Test User",
            interest_area="Web Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en",
            learning_velocity=0.0,
            vector_embedding_id="test_embedding_id"
        )
        test_db.add(profile)
        test_db.commit()
        test_db.refresh(profile)
        
        user_service = UserService(test_db)
        
        # Update multiple sources without triggering reassessment
        updated_profile = user_service.update_portfolio_sources(
            user_id=user.id,
            github_url="https://github.com/testuser",
            portfolio_url="https://testuser.dev",
            manual_skills=["Python", "JavaScript", "React"],
            trigger_reassessment=False
        )
        
        assert updated_profile.github_url == "https://github.com/testuser"
        assert updated_profile.portfolio_url == "https://testuser.dev"
        assert updated_profile.manual_skills == ["Python", "JavaScript", "React"]
    
    def test_update_portfolio_sources_triggers_github_reassessment(self, test_db: Session):
        """Test that updating GitHub URL triggers skill reassessment."""
        user = User(email="test15@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        profile = UserProfile(
            user_id=user.id,
            display_name="Test User",
            interest_area="Web Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en",
            learning_velocity=0.0,
            vector_embedding_id="test_embedding_id"
        )
        test_db.add(profile)
        test_db.commit()
        test_db.refresh(profile)
        
        user_service = UserService(test_db)
        
        # Mock GitHub analysis
        from app.models.skill_assessment import SkillAssessment, AssessmentSource
        mock_assessment = SkillAssessment(
            user_id=user.id,
            source=AssessmentSource.GITHUB,
            skill_level=7,
            confidence_score=0.8,
            detected_skills=["Python", "Django", "PostgreSQL"],
            source_data={"repos": 10}
        )
        
        mock_combined = SkillAssessment(
            user_id=user.id,
            source=AssessmentSource.COMBINED,
            skill_level=7,
            confidence_score=0.8,
            detected_skills=["Python", "Django", "PostgreSQL"],
            source_data={}
        )
        
        mock_embedding = VectorEmbedding(
            user_id=user.id,
            pinecone_id=f"user_{user.id}_updated",
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
            'analyze_github',
            return_value=mock_assessment
        ) as mock_analyze, \
        patch.object(
            user_service.portfolio_service,
            'combine_assessments',
            return_value=mock_combined
        ) as mock_combine, \
        patch.object(
            user_service.portfolio_service,
            'generate_vector_embedding',
            return_value=mock_embedding
        ) as mock_generate:
            
            # Update with reassessment (default)
            updated_profile = user_service.update_portfolio_sources(
                user_id=user.id,
                github_url="https://github.com/testuser"
            )
            
            # Verify GitHub analysis was called
            mock_analyze.assert_called_once_with("https://github.com/testuser", user.id)
            
            # Verify assessments were combined
            mock_combine.assert_called_once()
            
            # Verify skill level was updated
            assert updated_profile.skill_level == 7
            
            # Verify vector embedding was regenerated
            mock_generate.assert_called_once()
    
    def test_update_portfolio_sources_triggers_multiple_reassessments(self, test_db: Session):
        """Test that updating multiple sources triggers multiple reassessments."""
        user = User(email="test16@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        profile = UserProfile(
            user_id=user.id,
            display_name="Test User",
            interest_area="Web Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en",
            learning_velocity=0.0,
            vector_embedding_id="test_embedding_id"
        )
        test_db.add(profile)
        test_db.commit()
        test_db.refresh(profile)
        
        user_service = UserService(test_db)
        
        # Mock assessments
        from app.models.skill_assessment import SkillAssessment, AssessmentSource
        mock_github_assessment = SkillAssessment(
            user_id=user.id,
            source=AssessmentSource.GITHUB,
            skill_level=7,
            confidence_score=0.8,
            detected_skills=["Python", "Django"],
            source_data={}
        )
        
        mock_linkedin_assessment = SkillAssessment(
            user_id=user.id,
            source=AssessmentSource.LINKEDIN,
            skill_level=8,
            confidence_score=0.9,
            detected_skills=["Python", "AWS"],
            source_data={}
        )
        
        mock_combined = SkillAssessment(
            user_id=user.id,
            source=AssessmentSource.COMBINED,
            skill_level=8,
            confidence_score=0.85,
            detected_skills=["Python", "Django", "AWS"],
            source_data={}
        )
        
        mock_embedding = VectorEmbedding(
            user_id=user.id,
            pinecone_id=f"user_{user.id}_updated",
            skill_level=8,
            learning_velocity=0.0,
            timezone_offset=-5.0,
            language_code="en",
            interest_area="Web Development",
            embedding_version="v1",
            dimensions=384
        )
        
        with patch.object(
            user_service.portfolio_service,
            'analyze_github',
            return_value=mock_github_assessment
        ) as mock_github, \
        patch.object(
            user_service.portfolio_service,
            'analyze_linkedin',
            return_value=mock_linkedin_assessment
        ) as mock_linkedin, \
        patch.object(
            user_service.portfolio_service,
            'combine_assessments',
            return_value=mock_combined
        ) as mock_combine, \
        patch.object(
            user_service.portfolio_service,
            'generate_vector_embedding',
            return_value=mock_embedding
        ):
            
            # Update multiple sources
            updated_profile = user_service.update_portfolio_sources(
                user_id=user.id,
                github_url="https://github.com/testuser",
                linkedin_profile={"id": "testuser", "experience": []}
            )
            
            # Verify both analyses were called
            mock_github.assert_called_once()
            mock_linkedin.assert_called_once()
            
            # Verify assessments were combined
            mock_combine.assert_called_once()
            
            # Verify skill level was updated
            assert updated_profile.skill_level == 8
    
    def test_update_portfolio_sources_handles_analysis_failure_gracefully(self, test_db: Session):
        """Test that analysis failures don't prevent profile update."""
        user = User(email="test17@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        profile = UserProfile(
            user_id=user.id,
            display_name="Test User",
            interest_area="Web Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en",
            learning_velocity=0.0,
            vector_embedding_id="test_embedding_id"
        )
        test_db.add(profile)
        test_db.commit()
        test_db.refresh(profile)
        
        user_service = UserService(test_db)
        
        # Mock GitHub analysis to fail
        with patch.object(
            user_service.portfolio_service,
            'analyze_github',
            side_effect=Exception("GitHub API error")
        ):
            # Update should still succeed even if analysis fails
            updated_profile = user_service.update_portfolio_sources(
                user_id=user.id,
                github_url="https://github.com/testuser"
            )
            
            # Profile should be updated with new URL
            assert updated_profile.github_url == "https://github.com/testuser"
            
            # Skill level should remain unchanged since analysis failed
            assert updated_profile.skill_level == 5
    
    def test_update_portfolio_sources_skips_reassessment_when_disabled(self, test_db: Session):
        """Test that reassessment can be disabled."""
        user = User(email="test18@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        profile = UserProfile(
            user_id=user.id,
            display_name="Test User",
            interest_area="Web Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en",
            learning_velocity=0.0,
            vector_embedding_id="test_embedding_id"
        )
        test_db.add(profile)
        test_db.commit()
        test_db.refresh(profile)
        
        user_service = UserService(test_db)
        
        with patch.object(
            user_service.portfolio_service,
            'analyze_github'
        ) as mock_analyze:
            
            # Update with reassessment disabled
            updated_profile = user_service.update_portfolio_sources(
                user_id=user.id,
                github_url="https://github.com/testuser",
                trigger_reassessment=False
            )
            
            # Verify analysis was NOT called
            mock_analyze.assert_not_called()
            
            # Profile should be updated
            assert updated_profile.github_url == "https://github.com/testuser"
            
            # Skill level should remain unchanged
            assert updated_profile.skill_level == 5
    
    def test_update_portfolio_sources_creates_manual_assessment(self, test_db: Session):
        """Test that updating manual skills creates a manual assessment."""
        user = User(email="test19@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        profile = UserProfile(
            user_id=user.id,
            display_name="Test User",
            interest_area="Web Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en",
            learning_velocity=0.0,
            vector_embedding_id="test_embedding_id"
        )
        test_db.add(profile)
        test_db.commit()
        test_db.refresh(profile)
        
        user_service = UserService(test_db)
        
        # Mock manual assessment
        from app.models.skill_assessment import SkillAssessment, AssessmentSource
        mock_manual_assessment = SkillAssessment(
            user_id=user.id,
            source=AssessmentSource.MANUAL,
            skill_level=6,
            confidence_score=0.7,
            detected_skills=["Python", "JavaScript", "React"],
            source_data={}
        )
        
        mock_combined = SkillAssessment(
            user_id=user.id,
            source=AssessmentSource.COMBINED,
            skill_level=6,
            confidence_score=0.7,
            detected_skills=["Python", "JavaScript", "React"],
            source_data={}
        )
        
        mock_embedding = VectorEmbedding(
            user_id=user.id,
            pinecone_id=f"user_{user.id}_updated",
            skill_level=6,
            learning_velocity=0.0,
            timezone_offset=-5.0,
            language_code="en",
            interest_area="Web Development",
            embedding_version="v1",
            dimensions=384
        )
        
        with patch.object(
            user_service.portfolio_service,
            'create_manual_assessment',
            return_value=mock_manual_assessment
        ) as mock_manual, \
        patch.object(
            user_service.portfolio_service,
            'combine_assessments',
            return_value=mock_combined
        ), \
        patch.object(
            user_service.portfolio_service,
            'generate_vector_embedding',
            return_value=mock_embedding
        ):
            
            # Update with manual skills
            updated_profile = user_service.update_portfolio_sources(
                user_id=user.id,
                manual_skills=["Python", "JavaScript", "React"]
            )
            
            # Verify manual assessment was created
            mock_manual.assert_called_once_with(
                skills=["Python", "JavaScript", "React"],
                experience_years=None,
                proficiency_level=None,
                user_id=user.id
            )
            
            # Verify skill level was updated
            assert updated_profile.skill_level == 6
    
    def test_update_portfolio_sources_regenerates_vector_embedding(self, test_db: Session):
        """Test that successful reassessment regenerates vector embedding."""
        user = User(email="test20@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        profile = UserProfile(
            user_id=user.id,
            display_name="Test User",
            interest_area="Web Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en",
            learning_velocity=0.0,
            vector_embedding_id="old_embedding_id"
        )
        test_db.add(profile)
        test_db.commit()
        test_db.refresh(profile)
        
        user_service = UserService(test_db)
        
        # Mock assessments
        from app.models.skill_assessment import SkillAssessment, AssessmentSource
        mock_assessment = SkillAssessment(
            user_id=user.id,
            source=AssessmentSource.GITHUB,
            skill_level=7,
            confidence_score=0.8,
            detected_skills=["Python"],
            source_data={}
        )
        
        mock_combined = SkillAssessment(
            user_id=user.id,
            source=AssessmentSource.COMBINED,
            skill_level=7,
            confidence_score=0.8,
            detected_skills=["Python"],
            source_data={}
        )
        
        mock_embedding = VectorEmbedding(
            user_id=user.id,
            pinecone_id="new_embedding_id",
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
            'analyze_github',
            return_value=mock_assessment
        ), \
        patch.object(
            user_service.portfolio_service,
            'combine_assessments',
            return_value=mock_combined
        ), \
        patch.object(
            user_service.portfolio_service,
            'generate_vector_embedding',
            return_value=mock_embedding
        ) as mock_generate:
            
            # Update with reassessment
            updated_profile = user_service.update_portfolio_sources(
                user_id=user.id,
                github_url="https://github.com/testuser"
            )
            
            # Verify vector embedding was regenerated
            mock_generate.assert_called_once_with(
                user_id=user.id,
                skill_level=7,
                learning_velocity=0.0,
                timezone="America/New_York",
                language="en",
                interest_area="Web Development"
            )
            
            # Verify profile has new embedding ID
            test_db.refresh(updated_profile)
            assert updated_profile.vector_embedding_id == "new_embedding_id"
    
    def test_update_portfolio_sources_handles_embedding_regeneration_failure(self, test_db: Session):
        """Test that embedding regeneration failure doesn't prevent skill level update."""
        user = User(email="test21@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        profile = UserProfile(
            user_id=user.id,
            display_name="Test User",
            interest_area="Web Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en",
            learning_velocity=0.0,
            vector_embedding_id="old_embedding_id"
        )
        test_db.add(profile)
        test_db.commit()
        test_db.refresh(profile)
        
        user_service = UserService(test_db)
        
        # Mock assessments
        from app.models.skill_assessment import SkillAssessment, AssessmentSource
        mock_assessment = SkillAssessment(
            user_id=user.id,
            source=AssessmentSource.GITHUB,
            skill_level=7,
            confidence_score=0.8,
            detected_skills=["Python"],
            source_data={}
        )
        
        mock_combined = SkillAssessment(
            user_id=user.id,
            source=AssessmentSource.COMBINED,
            skill_level=7,
            confidence_score=0.8,
            detected_skills=["Python"],
            source_data={}
        )
        
        with patch.object(
            user_service.portfolio_service,
            'analyze_github',
            return_value=mock_assessment
        ), \
        patch.object(
            user_service.portfolio_service,
            'combine_assessments',
            return_value=mock_combined
        ), \
        patch.object(
            user_service.portfolio_service,
            'generate_vector_embedding',
            side_effect=Exception("Pinecone connection failed")
        ):
            
            # Update should still succeed even if embedding regeneration fails
            updated_profile = user_service.update_portfolio_sources(
                user_id=user.id,
                github_url="https://github.com/testuser"
            )
            
            # Skill level should be updated
            assert updated_profile.skill_level == 7
            
            # Embedding ID should remain unchanged
            assert updated_profile.vector_embedding_id == "old_embedding_id"
    
    def test_update_portfolio_sources_fails_if_profile_not_found(self, test_db: Session):
        """Test that updating portfolio sources fails if profile doesn't exist."""
        user_service = UserService(test_db)
        non_existent_user_id = uuid4()
        
        with pytest.raises(ValueError, match="Profile not found"):
            user_service.update_portfolio_sources(
                user_id=non_existent_user_id,
                github_url="https://github.com/testuser"
            )
    
    def test_update_portfolio_sources_no_reassessment_if_no_sources_updated(self, test_db: Session):
        """Test that reassessment is not triggered if no sources are updated."""
        user = User(email="test22@example.com", password_hash="hashed")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        profile = UserProfile(
            user_id=user.id,
            display_name="Test User",
            interest_area="Web Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en",
            learning_velocity=0.0,
            vector_embedding_id="test_embedding_id"
        )
        test_db.add(profile)
        test_db.commit()
        test_db.refresh(profile)
        
        user_service = UserService(test_db)
        
        with patch.object(
            user_service.portfolio_service,
            'analyze_github'
        ) as mock_analyze:
            
            # Call without updating any sources
            updated_profile = user_service.update_portfolio_sources(
                user_id=user.id
            )
            
            # Verify analysis was NOT called
            mock_analyze.assert_not_called()
            
            # Skill level should remain unchanged
            assert updated_profile.skill_level == 5
