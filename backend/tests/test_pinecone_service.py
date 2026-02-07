"""
Unit tests for Pinecone vector similarity search service.

Tests the PineconeService class with mocked Pinecone client to verify:
- Vector storage and retrieval
- Similarity search with filtering
- Update and delete operations
- Error handling and retry logic
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from uuid import uuid4, UUID
from datetime import datetime
from app.services.pinecone_service import PineconeService
from app.models.skill_assessment import VectorEmbedding
from sqlalchemy.orm import Session


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_pinecone_client():
    """Mock Pinecone client."""
    mock_pc = Mock()
    mock_index = Mock()
    
    # Mock list_indexes to return empty list (index doesn't exist)
    mock_pc.list_indexes.return_value = []
    
    # Mock create_index
    mock_pc.create_index.return_value = None
    
    # Mock Index() to return mock index
    mock_pc.Index.return_value = mock_index
    
    return mock_pc, mock_index


@pytest.fixture
def pinecone_service(mock_db, mock_pinecone_client):
    """Create PineconeService with mocked dependencies."""
    mock_pc, mock_index = mock_pinecone_client
    
    with patch('app.services.pinecone_service.Pinecone', return_value=mock_pc):
        with patch('app.services.pinecone_service.settings') as mock_settings:
            mock_settings.PINECONE_API_KEY = "test-api-key"
            mock_settings.PINECONE_ENVIRONMENT = "us-east-1"
            
            # Mock time.sleep to speed up tests
            with patch('time.sleep'):
                service = PineconeService(mock_db)
                service.index = mock_index  # Ensure index is set
                return service


class TestPineconeServiceInitialization:
    """Test PineconeService initialization."""
    
    def test_initialization_without_api_key(self, mock_db):
        """Test that initialization fails without API key."""
        with patch('app.services.pinecone_service.settings') as mock_settings:
            mock_settings.PINECONE_API_KEY = None
            
            with pytest.raises(ValueError, match="Pinecone API key not configured"):
                PineconeService(mock_db)
    
    def test_initialization_creates_index_if_not_exists(self, mock_db):
        """Test that initialization creates index if it doesn't exist."""
        mock_pc = Mock()
        mock_pc.list_indexes.return_value = []
        
        with patch('app.services.pinecone_service.Pinecone', return_value=mock_pc):
            with patch('app.services.pinecone_service.settings') as mock_settings:
                mock_settings.PINECONE_API_KEY = "test-api-key"
                mock_settings.PINECONE_ENVIRONMENT = "us-east-1"
                
                with patch('time.sleep'):
                    service = PineconeService(mock_db)
                    
                    # Verify create_index was called
                    mock_pc.create_index.assert_called_once()
                    call_kwargs = mock_pc.create_index.call_args[1]
                    assert call_kwargs['name'] == "origin-user-embeddings"
                    assert call_kwargs['dimension'] == 384
                    assert call_kwargs['metric'] == "cosine"
    
    def test_initialization_skips_index_creation_if_exists(self, mock_db):
        """Test that initialization skips index creation if it already exists."""
        mock_pc = Mock()
        
        # Mock existing index
        mock_index_info = Mock()
        mock_index_info.name = "origin-user-embeddings"
        mock_pc.list_indexes.return_value = [mock_index_info]
        
        with patch('app.services.pinecone_service.Pinecone', return_value=mock_pc):
            with patch('app.services.pinecone_service.settings') as mock_settings:
                mock_settings.PINECONE_API_KEY = "test-api-key"
                mock_settings.PINECONE_ENVIRONMENT = "us-east-1"
                
                service = PineconeService(mock_db)
                
                # Verify create_index was NOT called
                mock_pc.create_index.assert_not_called()


class TestStoreEmbedding:
    """Test store_embedding method."""
    
    def test_store_embedding_success(self, pinecone_service):
        """Test successful embedding storage."""
        user_id = uuid4()
        embedding_vector = [0.1] * 384
        metadata = {
            "skill_level": 7,
            "learning_velocity": 2.5,
            "timezone": "America/New_York",
            "timezone_offset": -5.0,
            "language": "en",
            "interest_area": "Python Development"
        }
        
        # Mock successful upsert
        pinecone_service.index.upsert.return_value = None
        
        # Store embedding
        pinecone_id = pinecone_service.store_embedding(user_id, embedding_vector, metadata)
        
        # Verify result
        assert pinecone_id == f"user_{user_id}"
        
        # Verify upsert was called with correct parameters
        pinecone_service.index.upsert.assert_called_once()
        call_args = pinecone_service.index.upsert.call_args[1]
        
        assert len(call_args['vectors']) == 1
        vector_data = call_args['vectors'][0]
        
        assert vector_data['id'] == f"user_{user_id}"
        assert vector_data['values'] == embedding_vector
        assert vector_data['metadata']['user_id'] == str(user_id)
        assert vector_data['metadata']['skill_level'] == 7
        assert 'updated_at' in vector_data['metadata']
    
    def test_store_embedding_invalid_dimensions(self, pinecone_service):
        """Test that storing embedding with wrong dimensions raises error."""
        user_id = uuid4()
        embedding_vector = [0.1] * 100  # Wrong dimension
        metadata = {"skill_level": 5}
        
        with pytest.raises(ValueError, match="Expected 384-dimensional embedding"):
            pinecone_service.store_embedding(user_id, embedding_vector, metadata)
    
    def test_store_embedding_retry_on_failure(self, pinecone_service):
        """Test that store_embedding retries on failure."""
        user_id = uuid4()
        embedding_vector = [0.1] * 384
        metadata = {"skill_level": 5}
        
        # Mock failure then success
        pinecone_service.index.upsert.side_effect = [
            Exception("Network error"),
            None  # Success on retry
        ]
        
        # Should succeed after retry
        pinecone_id = pinecone_service.store_embedding(user_id, embedding_vector, metadata)
        
        assert pinecone_id == f"user_{user_id}"
        assert pinecone_service.index.upsert.call_count == 2


class TestQuerySimilarUsers:
    """Test query_similar_users method."""
    
    def test_query_similar_users_success(self, pinecone_service, mock_db):
        """Test successful similarity search."""
        user_id = uuid4()
        
        # Mock database query for user embedding
        mock_embedding = Mock(spec=VectorEmbedding)
        mock_embedding.user_id = user_id
        mock_embedding.timezone_offset = -5.0
        mock_db.query.return_value.filter.return_value.first.return_value = mock_embedding
        
        # Mock Pinecone fetch (get user's vector)
        user_vector = [0.1] * 384
        mock_fetch_response = Mock()
        mock_fetch_response.vectors = {
            f"user_{user_id}": Mock(values=user_vector)
        }
        pinecone_service.index.fetch.return_value = mock_fetch_response
        
        # Mock Pinecone query (find similar users)
        match1 = Mock()
        match1.id = f"user_{uuid4()}"
        match1.score = 0.85
        match1.metadata = {
            "skill_level": 7,
            "learning_velocity": 2.5,
            "timezone": "America/New_York",
            "timezone_offset": -5.0,
            "language": "en",
            "interest_area": "Python Development"
        }
        
        match2 = Mock()
        match2.id = f"user_{user_id}"  # The user themselves (should be filtered out)
        match2.score = 1.0
        match2.metadata = {}
        
        match3 = Mock()
        match3.id = f"user_{uuid4()}"
        match3.score = 0.75
        match3.metadata = {
            "skill_level": 6,
            "learning_velocity": 2.0,
            "timezone": "America/Chicago",
            "timezone_offset": -6.0,
            "language": "en",
            "interest_area": "Python Development"
        }
        
        mock_query_response = Mock()
        mock_query_response.matches = [match1, match2, match3]
        pinecone_service.index.query.return_value = mock_query_response
        
        # Query similar users
        similar_users = pinecone_service.query_similar_users(
            user_id=user_id,
            guild_interest_area="Python Development",
            top_k=10,
            min_similarity=0.7
        )
        
        # Verify results
        assert len(similar_users) == 2  # match2 (self) should be filtered out
        
        # Verify first match
        assert similar_users[0]['similarity_score'] == 0.85
        assert similar_users[0]['skill_level'] == 7
        assert similar_users[0]['interest_area'] == "Python Development"
        
        # Verify second match
        assert similar_users[1]['similarity_score'] == 0.75
        assert similar_users[1]['skill_level'] == 6
        
        # Verify query was called with correct filters
        pinecone_service.index.query.assert_called_once()
        call_kwargs = pinecone_service.index.query.call_args[1]
        
        assert call_kwargs['vector'] == user_vector
        assert call_kwargs['top_k'] == 11  # +1 for self
        assert call_kwargs['include_metadata'] is True
        
        # Verify filters
        filter_dict = call_kwargs['filter']
        assert filter_dict['interest_area'] == {"$eq": "Python Development"}
        assert filter_dict['timezone_offset']['$gte'] == -8.0  # -5 - 3
        assert filter_dict['timezone_offset']['$lte'] == -2.0  # -5 + 3
    
    def test_query_similar_users_with_language_filter(self, pinecone_service, mock_db):
        """Test similarity search with language filter."""
        user_id = uuid4()
        
        # Mock database query
        mock_embedding = Mock(spec=VectorEmbedding)
        mock_embedding.user_id = user_id
        mock_embedding.timezone_offset = 0.0
        mock_db.query.return_value.filter.return_value.first.return_value = mock_embedding
        
        # Mock Pinecone fetch
        user_vector = [0.1] * 384
        mock_fetch_response = Mock()
        mock_fetch_response.vectors = {
            f"user_{user_id}": Mock(values=user_vector)
        }
        pinecone_service.index.fetch.return_value = mock_fetch_response
        
        # Mock Pinecone query
        mock_query_response = Mock()
        mock_query_response.matches = []
        pinecone_service.index.query.return_value = mock_query_response
        
        # Query with language filter
        pinecone_service.query_similar_users(
            user_id=user_id,
            guild_interest_area="Web Development",
            language="es"
        )
        
        # Verify language filter was applied
        call_kwargs = pinecone_service.index.query.call_args[1]
        filter_dict = call_kwargs['filter']
        assert filter_dict['language'] == {"$eq": "es"}
    
    def test_query_similar_users_filters_by_min_similarity(self, pinecone_service, mock_db):
        """Test that results below min_similarity threshold are filtered out."""
        user_id = uuid4()
        
        # Mock database query
        mock_embedding = Mock(spec=VectorEmbedding)
        mock_embedding.user_id = user_id
        mock_embedding.timezone_offset = 0.0
        mock_db.query.return_value.filter.return_value.first.return_value = mock_embedding
        
        # Mock Pinecone fetch
        user_vector = [0.1] * 384
        mock_fetch_response = Mock()
        mock_fetch_response.vectors = {
            f"user_{user_id}": Mock(values=user_vector)
        }
        pinecone_service.index.fetch.return_value = mock_fetch_response
        
        # Mock Pinecone query with low similarity matches
        match1 = Mock()
        match1.id = f"user_{uuid4()}"
        match1.score = 0.85  # Above threshold
        match1.metadata = {"skill_level": 7, "interest_area": "Python"}
        
        match2 = Mock()
        match2.id = f"user_{uuid4()}"
        match2.score = 0.65  # Below threshold
        match2.metadata = {"skill_level": 5, "interest_area": "Python"}
        
        mock_query_response = Mock()
        mock_query_response.matches = [match1, match2]
        pinecone_service.index.query.return_value = mock_query_response
        
        # Query with min_similarity=0.7
        similar_users = pinecone_service.query_similar_users(
            user_id=user_id,
            guild_interest_area="Python",
            min_similarity=0.7
        )
        
        # Only match1 should be returned
        assert len(similar_users) == 1
        assert similar_users[0]['similarity_score'] == 0.85
    
    def test_query_similar_users_no_embedding_found(self, pinecone_service, mock_db):
        """Test error when user embedding not found in database."""
        user_id = uuid4()
        
        # Mock database query returning None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(ValueError, match="No vector embedding found"):
            pinecone_service.query_similar_users(
                user_id=user_id,
                guild_interest_area="Python"
            )
    
    def test_query_similar_users_vector_not_in_pinecone(self, pinecone_service, mock_db):
        """Test error when vector not found in Pinecone."""
        user_id = uuid4()
        
        # Mock database query
        mock_embedding = Mock(spec=VectorEmbedding)
        mock_embedding.user_id = user_id
        mock_embedding.timezone_offset = 0.0
        mock_db.query.return_value.filter.return_value.first.return_value = mock_embedding
        
        # Mock Pinecone fetch returning empty
        mock_fetch_response = Mock()
        mock_fetch_response.vectors = {}
        pinecone_service.index.fetch.return_value = mock_fetch_response
        
        with pytest.raises(ValueError, match="Vector not found in Pinecone"):
            pinecone_service.query_similar_users(
                user_id=user_id,
                guild_interest_area="Python"
            )


class TestUpdateEmbedding:
    """Test update_embedding method."""
    
    def test_update_embedding_success(self, pinecone_service):
        """Test successful embedding update."""
        user_id = uuid4()
        embedding_vector = [0.2] * 384
        metadata = {"skill_level": 8}
        
        # Mock successful upsert
        pinecone_service.index.upsert.return_value = None
        
        # Update embedding
        pinecone_id = pinecone_service.update_embedding(user_id, embedding_vector, metadata)
        
        # Verify result
        assert pinecone_id == f"user_{user_id}"
        
        # Verify upsert was called (update uses same upsert operation)
        pinecone_service.index.upsert.assert_called_once()


class TestDeleteEmbedding:
    """Test delete_embedding method."""
    
    def test_delete_embedding_success(self, pinecone_service):
        """Test successful embedding deletion."""
        user_id = uuid4()
        
        # Mock successful delete
        pinecone_service.index.delete.return_value = None
        
        # Delete embedding
        result = pinecone_service.delete_embedding(user_id)
        
        # Verify result
        assert result is True
        
        # Verify delete was called with correct ID
        pinecone_service.index.delete.assert_called_once_with(ids=[f"user_{user_id}"])
    
    def test_delete_embedding_retry_on_failure(self, pinecone_service):
        """Test that delete_embedding retries on failure."""
        user_id = uuid4()
        
        # Mock failure then success
        pinecone_service.index.delete.side_effect = [
            Exception("Network error"),
            None  # Success on retry
        ]
        
        # Should succeed after retry
        result = pinecone_service.delete_embedding(user_id)
        
        assert result is True
        assert pinecone_service.index.delete.call_count == 2


class TestGetEmbedding:
    """Test get_embedding method."""
    
    def test_get_embedding_success(self, pinecone_service):
        """Test successful embedding retrieval."""
        user_id = uuid4()
        pinecone_id = f"user_{user_id}"
        
        # Mock Pinecone fetch
        mock_vector_data = Mock()
        mock_vector_data.id = pinecone_id
        mock_vector_data.values = [0.1] * 384
        mock_vector_data.metadata = {"skill_level": 7}
        
        mock_fetch_response = Mock()
        mock_fetch_response.vectors = {pinecone_id: mock_vector_data}
        pinecone_service.index.fetch.return_value = mock_fetch_response
        
        # Get embedding
        result = pinecone_service.get_embedding(user_id)
        
        # Verify result
        assert result is not None
        assert result['id'] == pinecone_id
        assert len(result['values']) == 384
        assert result['metadata']['skill_level'] == 7
    
    def test_get_embedding_not_found(self, pinecone_service):
        """Test get_embedding when vector not found."""
        user_id = uuid4()
        
        # Mock Pinecone fetch returning empty
        mock_fetch_response = Mock()
        mock_fetch_response.vectors = {}
        pinecone_service.index.fetch.return_value = mock_fetch_response
        
        # Get embedding
        result = pinecone_service.get_embedding(user_id)
        
        # Should return None
        assert result is None


class TestCalculateSimilarity:
    """Test calculate_similarity method."""
    
    def test_calculate_similarity_success(self, pinecone_service):
        """Test successful similarity calculation."""
        user_id_1 = uuid4()
        user_id_2 = uuid4()
        
        # Create similar vectors
        vector_1 = [0.5] * 384
        vector_2 = [0.5] * 384
        
        # Mock get_embedding for both users
        def mock_get_embedding(user_id):
            if user_id == user_id_1:
                return {
                    "id": f"user_{user_id_1}",
                    "values": vector_1,
                    "metadata": {}
                }
            elif user_id == user_id_2:
                return {
                    "id": f"user_{user_id_2}",
                    "values": vector_2,
                    "metadata": {}
                }
            return None
        
        pinecone_service.get_embedding = Mock(side_effect=mock_get_embedding)
        
        # Calculate similarity
        similarity = pinecone_service.calculate_similarity(user_id_1, user_id_2)
        
        # Verify result (identical vectors should have similarity ~1.0)
        # Allow for floating point precision errors
        assert 0.99 <= similarity <= 1.01
    
    def test_calculate_similarity_orthogonal_vectors(self, pinecone_service):
        """Test similarity calculation with orthogonal vectors."""
        user_id_1 = uuid4()
        user_id_2 = uuid4()
        
        # Create orthogonal vectors
        vector_1 = [1.0] + [0.0] * 383
        vector_2 = [0.0, 1.0] + [0.0] * 382
        
        # Mock get_embedding
        def mock_get_embedding(user_id):
            if user_id == user_id_1:
                return {"id": f"user_{user_id_1}", "values": vector_1, "metadata": {}}
            elif user_id == user_id_2:
                return {"id": f"user_{user_id_2}", "values": vector_2, "metadata": {}}
            return None
        
        pinecone_service.get_embedding = Mock(side_effect=mock_get_embedding)
        
        # Calculate similarity
        similarity = pinecone_service.calculate_similarity(user_id_1, user_id_2)
        
        # Orthogonal vectors should have similarity ~0.0
        assert -0.01 <= similarity <= 0.01
    
    def test_calculate_similarity_user_not_found(self, pinecone_service):
        """Test error when user embedding not found."""
        user_id_1 = uuid4()
        user_id_2 = uuid4()
        
        # Mock get_embedding returning None for first user
        pinecone_service.get_embedding = Mock(return_value=None)
        
        with pytest.raises(ValueError, match="No embedding found"):
            pinecone_service.calculate_similarity(user_id_1, user_id_2)


class TestGetIndexStats:
    """Test get_index_stats method."""
    
    def test_get_index_stats_success(self, pinecone_service):
        """Test successful index stats retrieval."""
        # Mock describe_index_stats
        mock_stats = Mock()
        mock_stats.total_vector_count = 1000
        mock_stats.dimension = 384
        mock_stats.index_fullness = 0.5
        mock_stats.namespaces = {}
        
        pinecone_service.index.describe_index_stats.return_value = mock_stats
        
        # Get stats
        stats = pinecone_service.get_index_stats()
        
        # Verify result
        assert stats['total_vectors'] == 1000
        assert stats['dimension'] == 384
        assert stats['index_fullness'] == 0.5
        assert 'namespaces' in stats


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_query_results(self, pinecone_service, mock_db):
        """Test handling of empty query results."""
        user_id = uuid4()
        
        # Mock database query
        mock_embedding = Mock(spec=VectorEmbedding)
        mock_embedding.user_id = user_id
        mock_embedding.timezone_offset = 0.0
        mock_db.query.return_value.filter.return_value.first.return_value = mock_embedding
        
        # Mock Pinecone fetch
        user_vector = [0.1] * 384
        mock_fetch_response = Mock()
        mock_fetch_response.vectors = {
            f"user_{user_id}": Mock(values=user_vector)
        }
        pinecone_service.index.fetch.return_value = mock_fetch_response
        
        # Mock empty query results
        mock_query_response = Mock()
        mock_query_response.matches = []
        pinecone_service.index.query.return_value = mock_query_response
        
        # Query should return empty list
        similar_users = pinecone_service.query_similar_users(
            user_id=user_id,
            guild_interest_area="Rare Interest"
        )
        
        assert similar_users == []
    
    def test_calculate_similarity_zero_vectors(self, pinecone_service):
        """Test similarity calculation with zero vectors."""
        user_id_1 = uuid4()
        user_id_2 = uuid4()
        
        # Create zero vectors
        vector_1 = [0.0] * 384
        vector_2 = [0.0] * 384
        
        # Mock get_embedding
        def mock_get_embedding(user_id):
            if user_id == user_id_1:
                return {"id": f"user_{user_id_1}", "values": vector_1, "metadata": {}}
            elif user_id == user_id_2:
                return {"id": f"user_{user_id_2}", "values": vector_2, "metadata": {}}
            return None
        
        pinecone_service.get_embedding = Mock(side_effect=mock_get_embedding)
        
        # Calculate similarity (should handle division by zero)
        similarity = pinecone_service.calculate_similarity(user_id_1, user_id_2)
        
        # Should return 0.0 for zero vectors
        assert similarity == 0.0
