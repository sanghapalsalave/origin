"""
Tests for SkillAssessment and VectorEmbedding models.

Validates Requirements 1.3, 1.4, 1.5, 1.6 (portfolio analysis and skill assessment).
"""
import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy import text
from app.models.user import User, UserProfile
from app.models.skill_assessment import SkillAssessment, VectorEmbedding, AssessmentSource


def test_skill_assessment_creation(test_db):
    """Test creating a SkillAssessment record."""
    # Create a user first
    user = User(
        email="test@example.com",
        password_hash="hashed_password"
    )
    test_db.add(user)
    test_db.commit()
    
    # Create a skill assessment
    assessment = SkillAssessment(
        user_id=user.id,
        source=AssessmentSource.GITHUB,
        skill_level=7,
        confidence_score=0.85,
        source_url="https://github.com/testuser",
        detected_skills=["Python", "JavaScript", "React"],
        experience_years=3.5,
        proficiency_levels={"Python": "advanced", "JavaScript": "intermediate"},
        analysis_summary="Strong backend developer with Python expertise"
    )
    test_db.add(assessment)
    test_db.commit()
    
    # Verify the assessment was created
    assert assessment.id is not None
    assert assessment.user_id == user.id
    assert assessment.source == AssessmentSource.GITHUB
    assert assessment.skill_level == 7
    assert assessment.confidence_score == 0.85
    assert "Python" in assessment.detected_skills
    assert assessment.created_at is not None


def test_skill_assessment_valid_skill_level_range(test_db):
    """Test that skill level is within valid range (1-10)."""
    user = User(email="test2@example.com", password_hash="hashed_password")
    test_db.add(user)
    test_db.commit()
    
    # Test valid skill levels
    for level in [1, 5, 10]:
        assessment = SkillAssessment(
            user_id=user.id,
            source=AssessmentSource.MANUAL,
            skill_level=level
        )
        test_db.add(assessment)
        test_db.commit()
        assert assessment.skill_level == level


def test_multiple_assessments_per_user(test_db):
    """Test that a user can have multiple skill assessments from different sources."""
    user = User(email="test3@example.com", password_hash="hashed_password")
    test_db.add(user)
    test_db.commit()
    
    # Create assessments from different sources
    sources = [AssessmentSource.GITHUB, AssessmentSource.LINKEDIN, AssessmentSource.RESUME]
    for source in sources:
        assessment = SkillAssessment(
            user_id=user.id,
            source=source,
            skill_level=7
        )
        test_db.add(assessment)
    
    test_db.commit()
    
    # Verify all assessments were created
    assessments = test_db.query(SkillAssessment).filter_by(user_id=user.id).all()
    assert len(assessments) == 3
    assert set(a.source for a in assessments) == set(sources)


def test_vector_embedding_creation(test_db):
    """Test creating a VectorEmbedding record."""
    # Create a user first
    user = User(email="test4@example.com", password_hash="hashed_password")
    test_db.add(user)
    test_db.commit()
    
    # Create a vector embedding
    embedding = VectorEmbedding(
        user_id=user.id,
        pinecone_id=f"user_{user.id}",
        skill_level=7,
        learning_velocity=2.5,
        timezone_offset=-5.0,  # EST
        language_code="en",
        interest_area="web_development"
    )
    test_db.add(embedding)
    test_db.commit()
    
    # Verify the embedding was created
    assert embedding.id is not None
    assert embedding.user_id == user.id
    assert embedding.pinecone_id == f"user_{user.id}"
    assert embedding.skill_level == 7
    assert embedding.learning_velocity == 2.5
    assert embedding.timezone_offset == -5.0
    assert embedding.language_code == "en"
    assert embedding.interest_area == "web_development"
    assert embedding.embedding_version == "v1"
    assert embedding.dimensions == 384
    assert embedding.created_at is not None


def test_vector_embedding_unique_per_user(test_db):
    """Test that each user can have only one vector embedding."""
    user = User(email="test5@example.com", password_hash="hashed_password")
    test_db.add(user)
    test_db.commit()
    
    # Create first embedding
    embedding1 = VectorEmbedding(
        user_id=user.id,
        pinecone_id=f"user_{user.id}_v1",
        skill_level=5,
        learning_velocity=1.5,
        timezone_offset=0.0,
        language_code="en",
        interest_area="data_science"
    )
    test_db.add(embedding1)
    test_db.commit()
    
    # Try to create second embedding for same user (should fail due to unique constraint)
    embedding2 = VectorEmbedding(
        user_id=user.id,
        pinecone_id=f"user_{user.id}_v2",
        skill_level=6,
        learning_velocity=2.0,
        timezone_offset=0.0,
        language_code="en",
        interest_area="data_science"
    )
    test_db.add(embedding2)
    
    with pytest.raises(Exception):  # Should raise IntegrityError
        test_db.commit()


def test_vector_embedding_pinecone_id_unique(test_db):
    """Test that pinecone_id is unique across all embeddings."""
    user1 = User(email="test6@example.com", password_hash="hashed_password")
    user2 = User(email="test7@example.com", password_hash="hashed_password")
    test_db.add_all([user1, user2])
    test_db.commit()
    
    pinecone_id = "shared_pinecone_id"
    
    # Create first embedding
    embedding1 = VectorEmbedding(
        user_id=user1.id,
        pinecone_id=pinecone_id,
        skill_level=5,
        learning_velocity=1.5,
        timezone_offset=0.0,
        language_code="en",
        interest_area="data_science"
    )
    test_db.add(embedding1)
    test_db.commit()
    
    # Try to create second embedding with same pinecone_id (should fail)
    embedding2 = VectorEmbedding(
        user_id=user2.id,
        pinecone_id=pinecone_id,
        skill_level=6,
        learning_velocity=2.0,
        timezone_offset=0.0,
        language_code="en",
        interest_area="data_science"
    )
    test_db.add(embedding2)
    
    with pytest.raises(Exception):  # Should raise IntegrityError
        test_db.commit()


def test_cascade_delete_skill_assessments(test_db):
    """Test that skill assessments are deleted when user is deleted (database cascade)."""
    user = User(email="test8@example.com", password_hash="hashed_password")
    test_db.add(user)
    test_db.commit()
    
    # Create skill assessment
    assessment = SkillAssessment(
        user_id=user.id,
        source=AssessmentSource.GITHUB,
        skill_level=7
    )
    test_db.add(assessment)
    test_db.commit()
    
    assessment_id = assessment.id
    user_id = user.id
    
    # Verify both exist
    assert test_db.query(User).filter_by(id=user_id).first() is not None
    assert test_db.query(SkillAssessment).filter_by(id=assessment_id).first() is not None
    
    # Delete user directly via SQL to test database cascade
    test_db.execute(text(f"DELETE FROM users WHERE id = '{user_id}'"))
    test_db.commit()
    
    # Verify both were deleted (cascade at database level)
    assert test_db.query(User).filter_by(id=user_id).first() is None
    assert test_db.query(SkillAssessment).filter_by(id=assessment_id).first() is None


def test_cascade_delete_vector_embedding(test_db):
    """Test that vector embedding is deleted when user is deleted (database cascade)."""
    user = User(email="test9@example.com", password_hash="hashed_password")
    test_db.add(user)
    test_db.commit()
    
    # Create vector embedding
    embedding = VectorEmbedding(
        user_id=user.id,
        pinecone_id=f"user_{user.id}",
        skill_level=7,
        learning_velocity=2.0,
        timezone_offset=0.0,
        language_code="en",
        interest_area="web_development"
    )
    test_db.add(embedding)
    test_db.commit()
    
    embedding_id = embedding.id
    user_id = user.id
    
    # Verify both exist
    assert test_db.query(User).filter_by(id=user_id).first() is not None
    assert test_db.query(VectorEmbedding).filter_by(id=embedding_id).first() is not None
    
    # Delete user directly via SQL to test database cascade
    test_db.execute(text(f"DELETE FROM users WHERE id = '{user_id}'"))
    test_db.commit()
    
    # Verify both were deleted (cascade at database level)
    assert test_db.query(User).filter_by(id=user_id).first() is None
    assert test_db.query(VectorEmbedding).filter_by(id=embedding_id).first() is None


def test_assessment_source_enum_values(test_db):
    """Test all AssessmentSource enum values."""
    user = User(email="test10@example.com", password_hash="hashed_password")
    test_db.add(user)
    test_db.commit()
    
    # Test all enum values
    sources = [
        AssessmentSource.GITHUB,
        AssessmentSource.LINKEDIN,
        AssessmentSource.RESUME,
        AssessmentSource.PORTFOLIO_WEBSITE,
        AssessmentSource.MANUAL,
        AssessmentSource.COMBINED
    ]
    
    for source in sources:
        assessment = SkillAssessment(
            user_id=user.id,
            source=source,
            skill_level=5
        )
        test_db.add(assessment)
        test_db.commit()
        assert assessment.source == source
        test_db.delete(assessment)
        test_db.commit()
