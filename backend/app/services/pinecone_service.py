"""
Pinecone Vector Similarity Search Service

Provides vector similarity search functionality for squad matching using Pinecone.

Implements Requirements:
- 2.1: Vector embedding storage and retrieval
- 2.2: Interest area filtering for squad matching
- 2.3: Cosine similarity calculation for compatibility
"""
import logging
from typing import List, Dict, Optional, Any
from uuid import UUID
from datetime import datetime
from pinecone import Pinecone, ServerlessSpec
from app.core.config import settings
from app.core.retry import retry_with_exponential_backoff
from sqlalchemy.orm import Session
from app.models.skill_assessment import VectorEmbedding

logger = logging.getLogger(__name__)


class PineconeService:
    """Service for Pinecone vector similarity search operations."""
    
    # Index configuration
    INDEX_NAME = "origin-user-embeddings"
    EMBEDDING_DIMENSIONS = 384
    SIMILARITY_METRIC = "cosine"
    
    def __init__(self, db: Session):
        """
        Initialize Pinecone service.
        
        Args:
            db: Database session for VectorEmbedding operations
            
        Raises:
            ValueError: If Pinecone API key is not configured
        """
        self.db = db
        
        if not settings.PINECONE_API_KEY:
            raise ValueError("Pinecone API key not configured. Set PINECONE_API_KEY in environment.")
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        
        # Ensure index exists
        self._ensure_index_exists()
        
        # Get index reference
        self.index = self.pc.Index(self.INDEX_NAME)
        
        logger.info(f"PineconeService initialized with index: {self.INDEX_NAME}")
    
    def _ensure_index_exists(self) -> None:
        """
        Ensure the Pinecone index exists, create if it doesn't.
        
        Creates a serverless index with cosine similarity metric for
        384-dimensional embeddings.
        """
        try:
            existing_indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes]
            
            if self.INDEX_NAME not in index_names:
                logger.info(f"Creating Pinecone index: {self.INDEX_NAME}")
                
                self.pc.create_index(
                    name=self.INDEX_NAME,
                    dimension=self.EMBEDDING_DIMENSIONS,
                    metric=self.SIMILARITY_METRIC,
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=settings.PINECONE_ENVIRONMENT or "us-east-1"
                    )
                )
                
                # Wait for index to be ready
                import time
                time.sleep(5)
                
                logger.info(f"Pinecone index created: {self.INDEX_NAME}")
            else:
                logger.debug(f"Pinecone index already exists: {self.INDEX_NAME}")
                
        except Exception as e:
            logger.error(f"Error ensuring Pinecone index exists: {str(e)}")
            raise
    
    @retry_with_exponential_backoff(max_retries=3, base_delay=1.0, max_delay=16.0)
    def store_embedding(
        self,
        user_id: UUID,
        embedding_vector: List[float],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Store a user's vector embedding in Pinecone.
        
        Implements Requirement 2.1: Store user vector embeddings in Pinecone.
        
        Args:
            user_id: User ID
            embedding_vector: 384-dimensional embedding vector
            metadata: Metadata to store with the vector (skill_level, timezone, etc.)
            
        Returns:
            Pinecone vector ID (format: "user_{user_id}")
            
        Raises:
            ValueError: If embedding dimensions are incorrect
            Exception: If Pinecone upsert fails after retries
        """
        # Validate embedding dimensions
        if len(embedding_vector) != self.EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Expected {self.EMBEDDING_DIMENSIONS}-dimensional embedding, "
                f"got {len(embedding_vector)}"
            )
        
        # Generate Pinecone ID
        pinecone_id = f"user_{user_id}"
        
        # Add timestamp to metadata
        metadata["user_id"] = str(user_id)
        metadata["updated_at"] = datetime.utcnow().isoformat()
        
        try:
            # Upsert vector to Pinecone
            self.index.upsert(
                vectors=[
                    {
                        "id": pinecone_id,
                        "values": embedding_vector,
                        "metadata": metadata
                    }
                ]
            )
            
            logger.info(f"Successfully stored embedding for user {user_id} in Pinecone")
            return pinecone_id
            
        except Exception as e:
            logger.error(f"Failed to store embedding in Pinecone: {str(e)}")
            raise
    
    @retry_with_exponential_backoff(max_retries=3, base_delay=1.0, max_delay=16.0)
    def query_similar_users(
        self,
        user_id: UUID,
        guild_interest_area: str,
        top_k: int = 50,
        min_similarity: float = 0.7,
        timezone_tolerance_hours: float = 3.0,
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar users for squad matching using vector similarity search.
        
        Implements Requirements:
        - 2.2: Filter by guild interest area
        - 2.3: Calculate cosine similarity for compatibility
        
        Args:
            user_id: User ID to find matches for
            guild_interest_area: Interest area to filter by (e.g., "Python Development")
            top_k: Maximum number of similar users to return
            min_similarity: Minimum cosine similarity threshold (default: 0.7)
            timezone_tolerance_hours: Maximum timezone difference in hours (default: ±3)
            language: Optional language filter (ISO 639-1 code)
            
        Returns:
            List of similar users with their similarity scores and metadata.
            Each item contains:
            - user_id: User ID
            - similarity_score: Cosine similarity score (0-1)
            - skill_level: User's skill level
            - learning_velocity: User's learning velocity
            - timezone: User's timezone
            - timezone_offset: UTC offset in hours
            - language: User's language
            - interest_area: User's interest area
            
        Raises:
            ValueError: If user embedding not found
            Exception: If Pinecone query fails after retries
        """
        # Get the user's embedding from database
        user_embedding = self.db.query(VectorEmbedding).filter(
            VectorEmbedding.user_id == user_id
        ).first()
        
        if not user_embedding:
            raise ValueError(f"No vector embedding found for user {user_id}")
        
        # Get the user's vector from Pinecone
        pinecone_id = f"user_{user_id}"
        
        try:
            fetch_response = self.index.fetch(ids=[pinecone_id])
            
            if pinecone_id not in fetch_response.vectors:
                raise ValueError(f"Vector not found in Pinecone for user {user_id}")
            
            user_vector = fetch_response.vectors[pinecone_id].values
            
        except Exception as e:
            logger.error(f"Failed to fetch user vector from Pinecone: {str(e)}")
            raise
        
        # Build filter for metadata
        filter_dict = {
            "interest_area": {"$eq": guild_interest_area}
        }
        
        # Add language filter if specified
        if language:
            filter_dict["language"] = {"$eq": language}
        
        # Add timezone filter (within tolerance)
        user_timezone_offset = user_embedding.timezone_offset
        filter_dict["timezone_offset"] = {
            "$gte": user_timezone_offset - timezone_tolerance_hours,
            "$lte": user_timezone_offset + timezone_tolerance_hours
        }
        
        try:
            # Query Pinecone for similar vectors
            query_response = self.index.query(
                vector=user_vector,
                top_k=top_k + 1,  # +1 to account for the user themselves
                include_metadata=True,
                filter=filter_dict
            )
            
            # Process results
            similar_users = []
            
            for match in query_response.matches:
                # Skip the user themselves
                if match.id == pinecone_id:
                    continue
                
                # Filter by minimum similarity threshold
                if match.score < min_similarity:
                    continue
                
                # Extract user ID from Pinecone ID
                match_user_id = match.id.replace("user_", "")
                
                # Build result
                similar_user = {
                    "user_id": match_user_id,
                    "similarity_score": float(match.score),
                    "skill_level": match.metadata.get("skill_level"),
                    "learning_velocity": match.metadata.get("learning_velocity"),
                    "timezone": match.metadata.get("timezone"),
                    "timezone_offset": match.metadata.get("timezone_offset"),
                    "language": match.metadata.get("language"),
                    "interest_area": match.metadata.get("interest_area")
                }
                
                similar_users.append(similar_user)
            
            logger.info(
                f"Found {len(similar_users)} similar users for user {user_id} "
                f"in interest area '{guild_interest_area}' with similarity >= {min_similarity}"
            )
            
            return similar_users
            
        except Exception as e:
            logger.error(f"Failed to query similar users from Pinecone: {str(e)}")
            raise
    
    @retry_with_exponential_backoff(max_retries=3, base_delay=1.0, max_delay=16.0)
    def update_embedding(
        self,
        user_id: UUID,
        embedding_vector: List[float],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Update an existing user's vector embedding in Pinecone.
        
        This is an alias for store_embedding since Pinecone's upsert
        operation handles both insert and update.
        
        Args:
            user_id: User ID
            embedding_vector: Updated 384-dimensional embedding vector
            metadata: Updated metadata
            
        Returns:
            Pinecone vector ID
            
        Raises:
            ValueError: If embedding dimensions are incorrect
            Exception: If Pinecone update fails after retries
        """
        logger.info(f"Updating embedding for user {user_id}")
        return self.store_embedding(user_id, embedding_vector, metadata)
    
    @retry_with_exponential_backoff(max_retries=3, base_delay=1.0, max_delay=16.0)
    def delete_embedding(self, user_id: UUID) -> bool:
        """
        Delete a user's vector embedding from Pinecone.
        
        Used when a user is removed from the system or their profile is deleted.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deletion was successful
            
        Raises:
            Exception: If Pinecone delete fails after retries
        """
        pinecone_id = f"user_{user_id}"
        
        try:
            self.index.delete(ids=[pinecone_id])
            logger.info(f"Successfully deleted embedding for user {user_id} from Pinecone")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete embedding from Pinecone: {str(e)}")
            raise
    
    def get_embedding(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieve a user's vector embedding from Pinecone.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary containing the vector and metadata, or None if not found
            
        Raises:
            Exception: If Pinecone fetch fails
        """
        pinecone_id = f"user_{user_id}"
        
        try:
            fetch_response = self.index.fetch(ids=[pinecone_id])
            
            if pinecone_id not in fetch_response.vectors:
                logger.warning(f"No embedding found in Pinecone for user {user_id}")
                return None
            
            vector_data = fetch_response.vectors[pinecone_id]
            
            return {
                "id": vector_data.id,
                "values": vector_data.values,
                "metadata": vector_data.metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch embedding from Pinecone: {str(e)}")
            raise
    
    def calculate_similarity(
        self,
        user_id_1: UUID,
        user_id_2: UUID
    ) -> float:
        """
        Calculate cosine similarity between two users' embeddings.
        
        Implements Requirement 2.3: Compute cosine similarity between user embeddings.
        
        Args:
            user_id_1: First user ID
            user_id_2: Second user ID
            
        Returns:
            Cosine similarity score between -1 and 1 (typically 0 to 1 for normalized vectors)
            
        Raises:
            ValueError: If either user's embedding is not found
            Exception: If Pinecone operations fail
        """
        # Fetch both embeddings
        embedding_1 = self.get_embedding(user_id_1)
        embedding_2 = self.get_embedding(user_id_2)
        
        if not embedding_1:
            raise ValueError(f"No embedding found for user {user_id_1}")
        
        if not embedding_2:
            raise ValueError(f"No embedding found for user {user_id_2}")
        
        # Calculate cosine similarity
        import numpy as np
        
        vec1 = np.array(embedding_1["values"])
        vec2 = np.array(embedding_2["values"])
        
        # Cosine similarity = dot product / (norm1 * norm2)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        logger.debug(f"Cosine similarity between users {user_id_1} and {user_id_2}: {similarity:.4f}")
        
        return float(similarity)
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Pinecone index.
        
        Returns:
            Dictionary containing index statistics (total vectors, dimension, etc.)
        """
        try:
            stats = self.index.describe_index_stats()
            
            return {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": stats.namespaces
            }
            
        except Exception as e:
            logger.error(f"Failed to get index stats: {str(e)}")
            raise
