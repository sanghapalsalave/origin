"""
Example usage of vector embedding generation.

This example demonstrates how to use the generate_vector_embedding method
to create vector representations of users for squad matching.

Requirements:
- Pinecone API key configured in environment
- Database connection available
"""
from uuid import uuid4
from app.services.portfolio_analysis_service import PortfolioAnalysisService
from app.db.session import SessionLocal
from app.core.config import settings


def example_generate_vector_embedding():
    """
    Example: Generate vector embedding for a user.
    
    This demonstrates the complete flow of creating a vector embedding
    that includes skill level, learning velocity, timezone, language,
    and interest area.
    """
    # Create database session
    db = SessionLocal()
    
    try:
        # Initialize service
        service = PortfolioAnalysisService(db)
        
        # Example user data
        user_id = uuid4()
        skill_level = 7  # 1-10 scale
        learning_velocity = 2.5  # tasks per day
        timezone = "America/New_York"  # IANA timezone
        language = "en"  # ISO 639-1 code
        interest_area = "Python Development"
        
        print(f"Generating vector embedding for user {user_id}")
        print(f"  Skill Level: {skill_level}/10")
        print(f"  Learning Velocity: {learning_velocity} tasks/day")
        print(f"  Timezone: {timezone}")
        print(f"  Language: {language}")
        print(f"  Interest Area: {interest_area}")
        print()
        
        # Generate vector embedding
        embedding = service.generate_vector_embedding(
            user_id=user_id,
            skill_level=skill_level,
            learning_velocity=learning_velocity,
            timezone=timezone,
            language=language,
            interest_area=interest_area
        )
        
        print("✓ Vector embedding generated successfully!")
        print(f"  Embedding ID: {embedding.id}")
        print(f"  Pinecone ID: {embedding.pinecone_id}")
        print(f"  Dimensions: {embedding.dimensions}")
        print(f"  Timezone Offset: {embedding.timezone_offset} hours from UTC")
        print(f"  Embedding Version: {embedding.embedding_version}")
        print()
        
        # Display normalized values
        print("Normalized values:")
        print(f"  Skill Level: {embedding.extra_metadata['normalized_skill_level']}")
        print(f"  Velocity: {embedding.extra_metadata['normalized_velocity']}")
        print(f"  Timezone: {embedding.extra_metadata['normalized_timezone']}")
        print()
        
        # Display feature text used for embedding
        print("Feature text used for embedding:")
        print(f"  {embedding.extra_metadata['feature_text']}")
        print()
        
        return embedding
        
    except Exception as e:
        print(f"✗ Error generating vector embedding: {str(e)}")
        raise
    finally:
        db.close()


def example_multiple_users():
    """
    Example: Generate vector embeddings for multiple users with different profiles.
    
    This demonstrates how embeddings capture different user characteristics.
    """
    db = SessionLocal()
    
    try:
        service = PortfolioAnalysisService(db)
        
        # Define different user profiles
        users = [
            {
                "name": "Beginner Python Developer",
                "skill_level": 3,
                "learning_velocity": 1.0,
                "timezone": "America/New_York",
                "language": "en",
                "interest_area": "Python Development"
            },
            {
                "name": "Intermediate Python Developer",
                "skill_level": 6,
                "learning_velocity": 2.5,
                "timezone": "America/Los_Angeles",
                "language": "en",
                "interest_area": "Python Development"
            },
            {
                "name": "Advanced Data Scientist",
                "skill_level": 9,
                "learning_velocity": 4.0,
                "timezone": "Europe/London",
                "language": "en",
                "interest_area": "Data Science"
            },
            {
                "name": "Spanish Web Developer",
                "skill_level": 5,
                "learning_velocity": 2.0,
                "timezone": "Europe/Madrid",
                "language": "es",
                "interest_area": "Web Development"
            }
        ]
        
        print("Generating vector embeddings for multiple users:")
        print("=" * 60)
        print()
        
        embeddings = []
        for user_profile in users:
            user_id = uuid4()
            
            print(f"User: {user_profile['name']}")
            print(f"  Skill: {user_profile['skill_level']}/10")
            print(f"  Velocity: {user_profile['learning_velocity']} tasks/day")
            print(f"  Timezone: {user_profile['timezone']}")
            print(f"  Language: {user_profile['language']}")
            print(f"  Interest: {user_profile['interest_area']}")
            
            embedding = service.generate_vector_embedding(
                user_id=user_id,
                skill_level=user_profile['skill_level'],
                learning_velocity=user_profile['learning_velocity'],
                timezone=user_profile['timezone'],
                language=user_profile['language'],
                interest_area=user_profile['interest_area']
            )
            
            embeddings.append({
                "profile": user_profile,
                "embedding": embedding
            })
            
            print(f"  ✓ Embedding created: {embedding.pinecone_id}")
            print()
        
        print(f"Successfully created {len(embeddings)} vector embeddings!")
        print()
        print("These embeddings can now be used by the Node Logic matching engine")
        print("to find compatible squad members based on:")
        print("  - Similar skill levels")
        print("  - Compatible learning velocities")
        print("  - Overlapping timezones")
        print("  - Shared languages")
        print("  - Common interest areas")
        
        return embeddings
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Vector Embedding Generation Examples")
    print("=" * 60)
    print()
    
    # Check if Pinecone is configured
    if not settings.PINECONE_API_KEY:
        print("⚠ Warning: PINECONE_API_KEY not configured")
        print("Please set PINECONE_API_KEY in your .env file to run these examples")
        print()
    else:
        # Example 1: Single user
        print("Example 1: Generate embedding for a single user")
        print("-" * 60)
        example_generate_vector_embedding()
        
        print()
        print("=" * 60)
        print()
        
        # Example 2: Multiple users
        print("Example 2: Generate embeddings for multiple users")
        print("-" * 60)
        example_multiple_users()
