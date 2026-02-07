"""
Example usage of Pinecone vector similarity search service.

This example demonstrates how to use the PineconeService for squad matching:
- Storing user embeddings
- Querying for similar users
- Calculating similarity scores
- Updating and deleting embeddings

Requirements:
- Pinecone API key configured in environment
- Database connection available
"""
from uuid import uuid4
from app.services.pinecone_service import PineconeService
from app.db.session import SessionLocal
from app.core.config import settings
import numpy as np


def example_store_and_query():
    """
    Example: Store embeddings and query for similar users.
    
    This demonstrates the complete flow of storing user embeddings
    and finding compatible squad members.
    """
    db = SessionLocal()
    
    try:
        # Initialize service
        service = PineconeService(db)
        
        print("=" * 60)
        print("Example 1: Store and Query User Embeddings")
        print("=" * 60)
        print()
        
        # Create sample users with different profiles
        users = [
            {
                "name": "Alice - Senior Python Developer",
                "user_id": uuid4(),
                "skill_level": 8,
                "learning_velocity": 3.5,
                "timezone": "America/New_York",
                "timezone_offset": -5.0,
                "language": "en",
                "interest_area": "Python Development"
            },
            {
                "name": "Bob - Intermediate Python Developer",
                "user_id": uuid4(),
                "skill_level": 6,
                "learning_velocity": 2.5,
                "timezone": "America/New_York",
                "timezone_offset": -5.0,
                "language": "en",
                "interest_area": "Python Development"
            },
            {
                "name": "Carol - Junior Python Developer",
                "user_id": uuid4(),
                "skill_level": 4,
                "learning_velocity": 1.5,
                "timezone": "America/Chicago",
                "timezone_offset": -6.0,
                "language": "en",
                "interest_area": "Python Development"
            },
            {
                "name": "David - Advanced Data Scientist",
                "user_id": uuid4(),
                "skill_level": 9,
                "learning_velocity": 4.0,
                "timezone": "Europe/London",
                "timezone_offset": 0.0,
                "language": "en",
                "interest_area": "Data Science"
            },
            {
                "name": "Eva - Intermediate Web Developer",
                "user_id": uuid4(),
                "skill_level": 6,
                "learning_velocity": 2.0,
                "timezone": "America/Los_Angeles",
                "timezone_offset": -8.0,
                "language": "en",
                "interest_area": "Web Development"
            }
        ]
        
        # Store embeddings for all users
        print("Storing user embeddings in Pinecone...")
        print()
        
        for user in users:
            # Generate a simple embedding vector (in production, use Sentence Transformers)
            # For this example, we'll create a vector based on user attributes
            embedding_vector = generate_sample_embedding(
                user["skill_level"],
                user["learning_velocity"],
                user["interest_area"]
            )
            
            metadata = {
                "skill_level": user["skill_level"],
                "learning_velocity": user["learning_velocity"],
                "timezone": user["timezone"],
                "timezone_offset": user["timezone_offset"],
                "language": user["language"],
                "interest_area": user["interest_area"]
            }
            
            pinecone_id = service.store_embedding(
                user["user_id"],
                embedding_vector,
                metadata
            )
            
            print(f"✓ Stored: {user['name']}")
            print(f"  User ID: {user['user_id']}")
            print(f"  Pinecone ID: {pinecone_id}")
            print()
        
        print("=" * 60)
        print()
        
        # Query for similar users to Bob (Intermediate Python Developer)
        bob = users[1]
        print(f"Finding similar users to: {bob['name']}")
        print(f"  Skill Level: {bob['skill_level']}/10")
        print(f"  Interest Area: {bob['interest_area']}")
        print(f"  Timezone: {bob['timezone']}")
        print()
        
        # First, we need to create a VectorEmbedding record in the database
        # (In production, this would be done during user onboarding)
        from app.models.skill_assessment import VectorEmbedding
        
        bob_embedding = VectorEmbedding(
            user_id=bob["user_id"],
            pinecone_id=f"user_{bob['user_id']}",
            skill_level=bob["skill_level"],
            learning_velocity=bob["learning_velocity"],
            timezone_offset=bob["timezone_offset"],
            language_code=bob["language"],
            interest_area=bob["interest_area"]
        )
        db.add(bob_embedding)
        db.commit()
        
        # Query for similar users
        similar_users = service.query_similar_users(
            user_id=bob["user_id"],
            guild_interest_area="Python Development",
            top_k=10,
            min_similarity=0.7
        )
        
        print(f"Found {len(similar_users)} similar users:")
        print()
        
        for i, similar_user in enumerate(similar_users, 1):
            # Find the user name
            user_name = next(
                (u["name"] for u in users if str(u["user_id"]) == similar_user["user_id"]),
                "Unknown"
            )
            
            print(f"{i}. {user_name}")
            print(f"   Similarity Score: {similar_user['similarity_score']:.4f}")
            print(f"   Skill Level: {similar_user['skill_level']}/10")
            print(f"   Learning Velocity: {similar_user['learning_velocity']} tasks/day")
            print(f"   Timezone: {similar_user['timezone']}")
            print()
        
        return users, similar_users
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        raise
    finally:
        db.close()


def example_calculate_similarity():
    """
    Example: Calculate similarity between two specific users.
    """
    db = SessionLocal()
    
    try:
        service = PineconeService(db)
        
        print("=" * 60)
        print("Example 2: Calculate Pairwise Similarity")
        print("=" * 60)
        print()
        
        # Create two users
        user1_id = uuid4()
        user2_id = uuid4()
        
        # Generate embeddings
        embedding1 = generate_sample_embedding(7, 2.5, "Python Development")
        embedding2 = generate_sample_embedding(6, 2.0, "Python Development")
        
        # Store embeddings
        service.store_embedding(
            user1_id,
            embedding1,
            {
                "skill_level": 7,
                "learning_velocity": 2.5,
                "interest_area": "Python Development"
            }
        )
        
        service.store_embedding(
            user2_id,
            embedding2,
            {
                "skill_level": 6,
                "learning_velocity": 2.0,
                "interest_area": "Python Development"
            }
        )
        
        print("User 1: Skill 7/10, Velocity 2.5 tasks/day")
        print("User 2: Skill 6/10, Velocity 2.0 tasks/day")
        print()
        
        # Calculate similarity
        similarity = service.calculate_similarity(user1_id, user2_id)
        
        print(f"Cosine Similarity: {similarity:.4f}")
        print()
        
        if similarity >= 0.7:
            print("✓ These users are compatible for squad matching!")
        else:
            print("✗ These users are not compatible (similarity < 0.7)")
        
        print()
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        raise
    finally:
        db.close()


def example_update_and_delete():
    """
    Example: Update and delete user embeddings.
    """
    db = SessionLocal()
    
    try:
        service = PineconeService(db)
        
        print("=" * 60)
        print("Example 3: Update and Delete Embeddings")
        print("=" * 60)
        print()
        
        user_id = uuid4()
        
        # Store initial embedding
        print("1. Storing initial embedding...")
        embedding1 = generate_sample_embedding(5, 1.5, "Web Development")
        service.store_embedding(
            user_id,
            embedding1,
            {
                "skill_level": 5,
                "learning_velocity": 1.5,
                "interest_area": "Web Development"
            }
        )
        print("   ✓ Initial embedding stored")
        print()
        
        # Retrieve embedding
        print("2. Retrieving embedding...")
        retrieved = service.get_embedding(user_id)
        if retrieved:
            print(f"   ✓ Retrieved embedding with {len(retrieved['values'])} dimensions")
            print(f"   Metadata: {retrieved['metadata']}")
        print()
        
        # Update embedding (user improved their skills)
        print("3. Updating embedding (user leveled up)...")
        embedding2 = generate_sample_embedding(7, 2.5, "Web Development")
        service.update_embedding(
            user_id,
            embedding2,
            {
                "skill_level": 7,
                "learning_velocity": 2.5,
                "interest_area": "Web Development"
            }
        )
        print("   ✓ Embedding updated")
        print()
        
        # Delete embedding
        print("4. Deleting embedding...")
        service.delete_embedding(user_id)
        print("   ✓ Embedding deleted")
        print()
        
        # Verify deletion
        print("5. Verifying deletion...")
        retrieved_after_delete = service.get_embedding(user_id)
        if retrieved_after_delete is None:
            print("   ✓ Embedding successfully deleted (not found)")
        else:
            print("   ✗ Embedding still exists")
        print()
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        raise
    finally:
        db.close()


def example_index_stats():
    """
    Example: Get Pinecone index statistics.
    """
    db = SessionLocal()
    
    try:
        service = PineconeService(db)
        
        print("=" * 60)
        print("Example 4: Index Statistics")
        print("=" * 60)
        print()
        
        stats = service.get_index_stats()
        
        print("Pinecone Index Statistics:")
        print(f"  Total Vectors: {stats['total_vectors']}")
        print(f"  Dimensions: {stats['dimension']}")
        print(f"  Index Fullness: {stats['index_fullness']:.2%}")
        print()
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        raise
    finally:
        db.close()


def generate_sample_embedding(skill_level: int, learning_velocity: float, interest_area: str) -> list:
    """
    Generate a sample 384-dimensional embedding vector.
    
    In production, use Sentence Transformers to generate real embeddings.
    This is a simplified version for demonstration purposes.
    
    Args:
        skill_level: User's skill level (1-10)
        learning_velocity: User's learning velocity (tasks per day)
        interest_area: User's interest area
        
    Returns:
        384-dimensional embedding vector
    """
    # Create a deterministic but varied embedding based on inputs
    np.random.seed(hash(interest_area) % 2**32)
    
    # Base vector
    base = np.random.randn(384)
    
    # Add skill level component
    skill_component = np.ones(384) * (skill_level / 10.0)
    
    # Add velocity component
    velocity_component = np.ones(384) * (learning_velocity / 10.0)
    
    # Combine components
    embedding = base + skill_component * 0.3 + velocity_component * 0.2
    
    # Normalize to unit length (for cosine similarity)
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm
    
    return embedding.tolist()


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("Pinecone Vector Similarity Search Examples")
    print("=" * 60)
    print()
    
    # Check if Pinecone is configured
    if not settings.PINECONE_API_KEY:
        print("⚠ Warning: PINECONE_API_KEY not configured")
        print("Please set PINECONE_API_KEY in your .env file to run these examples")
        print()
    else:
        # Example 1: Store and query
        print()
        example_store_and_query()
        
        print()
        print("=" * 60)
        print()
        
        # Example 2: Calculate similarity
        example_calculate_similarity()
        
        print()
        print("=" * 60)
        print()
        
        # Example 3: Update and delete
        example_update_and_delete()
        
        print()
        print("=" * 60)
        print()
        
        # Example 4: Index stats
        example_index_stats()
        
        print()
        print("=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        print()
