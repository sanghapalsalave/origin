"""
Tests for vector embedding generation.

Tests the generate_vector_embedding method in PortfolioAnalysisService.

Implements Requirements:
- 2.1: Vector embedding generation based on skill level, velocity, timezone, language
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime
from app.services.portfolio_analysis_service import PortfolioAnalysisService
from app.models.skill_assessment import VectorEmbedding
from sqlalchemy.orm import Session


class TestVectorEmbeddingGeneration:
    """Test suite for vector embedding generation."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = Mock(spec=Session)
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        return db
    
    @pytest.fixture
    def service(self, mock_db):
        """Create PortfolioAnalysisService instance with mocked dependencies."""
        return PortfolioAnalysisService(mock_db)
    
    @pytest.fixture
    def mock_pinecone(self):
        """Mock Pinecone client and index."""
        with patch('app.services.portfolio_analysis_service.Pinecone') as mock_pc_class:
            mock_pc = Mock()
            mock_pc_class.return_value = mock_pc
            
            # Mock list_indexes
            mock_index_info = Mock()
            mock_index_info.name = "origin-user-embeddings"
            mock_pc.list_indexes.return_value = [mock_index_info]
            
            # Mock index
            mock_index = Mock()
            mock_index.upsert = Mock()
            mock_pc.Index.return_value = mock_index
            
            yield mock_pc, mock_index
    
    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock SentenceTransformer model."""
        with patch('app.services.portfolio_analysis_service.SentenceTransformer') as mock_st_class:
            mock_model = Mock()
            # Return a 384-dimensional vector
            import numpy as np
            mock_model.encode.return_value = np.random.rand(384)
            mock_st_class.return_value = mock_model
            yield mock_model
    
    @patch('app.services.portfolio_analysis_service.settings')
    def test_generate_vector_embedding_success(
        self,
        mock_settings,
        service,
        mock_db,
        mock_pinecone,
        mock_sentence_transformer
    ):
        """
        Test successful vector embedding generation.
        
        Validates Requirement 2.1: Vector embedding includes skill level, velocity,
        timezone, and language.
        """
        # Setup
        mock_settings.PINECONE_API_KEY = "test_api_key"
        mock_settings.PINECONE_ENVIRONMENT = "us-east-1"
        
        user_id = uuid4()
        skill_level = 7
        learning_velocity = 2.5
        timezone = "America/New_York"
        language = "en"
        interest_area = "Python Development"
        
        mock_pc, mock_index = mock_pinecone
        
        # Execute
        result = service.generate_vector_embedding(
            user_id=user_id,
            skill_level=skill_level,
            learning_velocity=learning_velocity,
            timezone=timezone,
            language=language,
            interest_area=interest_area
        )
        
        # Verify database operations
        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.refresh.called
        
        # Verify the VectorEmbedding was created with correct attributes
        added_embedding = mock_db.add.call_args[0][0]
        assert isinstance(added_embedding, VectorEmbedding)
        assert added_embedding.user_id == user_id
        assert added_embedding.skill_level == skill_level
        assert added_embedding.learning_velocity == learning_velocity
        assert added_embedding.language_code == language
        assert added_embedding.interest_area == interest_area
        assert added_embedding.embedding_version == "v1"
        assert added_embedding.dimensions == 384
        assert added_embedding.pinecone_id == f"user_{user_id}"
        
        # Verify Pinecone upsert was called
        assert mock_index.upsert.called
        upsert_args = mock_index.upsert.call_args[1]
        vectors = upsert_args['vectors']
        assert len(vectors) == 1
        assert vectors[0]['id'] == f"user_{user_id}"
        assert len(vectors[0]['values']) == 384
        assert vectors[0]['metadata']['user_id'] == str(user_id)
        assert vectors[0]['metadata']['skill_level'] == skill_level
        assert vectors[0]['metadata']['learning_velocity'] == learning_velocity
        assert vectors[0]['metadata']['timezone'] == timezone
        assert vectors[0]['metadata']['language'] == language
        assert vectors[0]['metadata']['interest_area'] == interest_area
    
    @patch('app.services.portfolio_analysis_service.settings')
    def test_generate_vector_embedding_includes_all_components(
        self,
        mock_settings,
        service,
        mock_db,
        mock_pinecone,
        mock_sentence_transformer
    ):
        """
        Test that vector embedding includes all required components.
        
        Validates Requirement 2.1: Embedding includes skill level, velocity, timezone, language.
        """
        mock_settings.PINECONE_API_KEY = "test_api_key"
        mock_settings.PINECONE_ENVIRONMENT = "us-east-1"
        
        user_id = uuid4()
        
        # Execute
        result = service.generate_vector_embedding(
            user_id=user_id,
            skill_level=5,
            learning_velocity=1.5,
            timezone="Europe/London",
            language="fr",
            interest_area="Machine Learning"
        )
        
        # Verify all components are present in the embedding
        added_embedding = mock_db.add.call_args[0][0]
        
        # Check that all required fields are present
        assert added_embedding.skill_level is not None
        assert added_embedding.learning_velocity is not None
        assert added_embedding.timezone_offset is not None
        assert added_embedding.language_code is not None
        assert added_embedding.interest_area is not None
        
        # Check extra metadata contains normalized values
        assert 'normalized_skill_level' in added_embedding.extra_metadata
        assert 'normalized_velocity' in added_embedding.extra_metadata
        assert 'normalized_timezone' in added_embedding.extra_metadata
        assert 'timezone' in added_embedding.extra_metadata
        assert 'feature_text' in added_embedding.extra_metadata
    
    @patch('app.services.portfolio_analysis_service.settings')
    def test_generate_vector_embedding_invalid_skill_level(
        self,
        mock_settings,
        service,
        mock_db
    ):
        """Test that invalid skill level raises ValueError."""
        mock_settings.PINECONE_API_KEY = "test_api_key"
        
        user_id = uuid4()
        
        # Test skill level too low
        with pytest.raises(ValueError, match="Skill level must be between 1 and 10"):
            service.generate_vector_embedding(
                user_id=user_id,
                skill_level=0,
                learning_velocity=1.0,
                timezone="UTC",
                language="en",
                interest_area="Test"
            )
        
        # Test skill level too high
        with pytest.raises(ValueError, match="Skill level must be between 1 and 10"):
            service.generate_vector_embedding(
                user_id=user_id,
                skill_level=11,
                learning_velocity=1.0,
                timezone="UTC",
                language="en",
                interest_area="Test"
            )
    
    @patch('app.services.portfolio_analysis_service.settings')
    def test_generate_vector_embedding_invalid_velocity(
        self,
        mock_settings,
        service,
        mock_db
    ):
        """Test that negative learning velocity raises ValueError."""
        mock_settings.PINECONE_API_KEY = "test_api_key"
        
        user_id = uuid4()
        
        with pytest.raises(ValueError, match="Learning velocity must be non-negative"):
            service.generate_vector_embedding(
                user_id=user_id,
                skill_level=5,
                learning_velocity=-1.0,
                timezone="UTC",
                language="en",
                interest_area="Test"
            )
    
    @patch('app.services.portfolio_analysis_service.settings')
    def test_generate_vector_embedding_missing_required_fields(
        self,
        mock_settings,
        service,
        mock_db
    ):
        """Test that missing required fields raise ValueError."""
        mock_settings.PINECONE_API_KEY = "test_api_key"
        
        user_id = uuid4()
        
        # Missing timezone
        with pytest.raises(ValueError, match="Timezone is required"):
            service.generate_vector_embedding(
                user_id=user_id,
                skill_level=5,
                learning_velocity=1.0,
                timezone="",
                language="en",
                interest_area="Test"
            )
        
        # Missing language
        with pytest.raises(ValueError, match="Language is required"):
            service.generate_vector_embedding(
                user_id=user_id,
                skill_level=5,
                learning_velocity=1.0,
                timezone="UTC",
                language="",
                interest_area="Test"
            )
        
        # Missing interest area
        with pytest.raises(ValueError, match="Interest area is required"):
            service.generate_vector_embedding(
                user_id=user_id,
                skill_level=5,
                learning_velocity=1.0,
                timezone="UTC",
                language="en",
                interest_area=""
            )
    
    @patch('app.services.portfolio_analysis_service.settings')
    def test_generate_vector_embedding_no_pinecone_config(
        self,
        mock_settings,
        service,
        mock_db
    ):
        """Test that missing Pinecone configuration raises ValueError."""
        mock_settings.PINECONE_API_KEY = None
        
        user_id = uuid4()
        
        with pytest.raises(ValueError, match="Pinecone API key not configured"):
            service.generate_vector_embedding(
                user_id=user_id,
                skill_level=5,
                learning_velocity=1.0,
                timezone="UTC",
                language="en",
                interest_area="Test"
            )
    
    @patch('app.services.portfolio_analysis_service.settings')
    def test_generate_vector_embedding_creates_index_if_not_exists(
        self,
        mock_settings,
        service,
        mock_db,
        mock_sentence_transformer
    ):
        """Test that Pinecone index is created if it doesn't exist."""
        mock_settings.PINECONE_API_KEY = "test_api_key"
        mock_settings.PINECONE_ENVIRONMENT = "us-east-1"
        
        with patch('app.services.portfolio_analysis_service.Pinecone') as mock_pc_class:
            mock_pc = Mock()
            mock_pc_class.return_value = mock_pc
            
            # Mock list_indexes to return empty list (index doesn't exist)
            mock_pc.list_indexes.return_value = []
            
            # Mock create_index
            mock_pc.create_index = Mock()
            
            # Mock index
            mock_index = Mock()
            mock_index.upsert = Mock()
            mock_pc.Index.return_value = mock_index
            
            user_id = uuid4()
            
            # Execute
            with patch('time.sleep'):  # Skip the sleep
                result = service.generate_vector_embedding(
                    user_id=user_id,
                    skill_level=5,
                    learning_velocity=1.0,
                    timezone="UTC",
                    language="en",
                    interest_area="Test"
                )
            
            # Verify create_index was called
            assert mock_pc.create_index.called
            create_args = mock_pc.create_index.call_args[1]
            assert create_args['name'] == "origin-user-embeddings"
            assert create_args['dimension'] == 384
            assert create_args['metric'] == "cosine"
    
    @patch('app.services.portfolio_analysis_service.settings')
    def test_generate_vector_embedding_different_timezones(
        self,
        mock_settings,
        service,
        mock_db,
        mock_pinecone,
        mock_sentence_transformer
    ):
        """Test vector embedding generation with different timezones."""
        mock_settings.PINECONE_API_KEY = "test_api_key"
        mock_settings.PINECONE_ENVIRONMENT = "us-east-1"
        
        user_id = uuid4()
        mock_pc, mock_index = mock_pinecone
        
        # Test with different timezones
        timezones = ["America/New_York", "Europe/London", "Asia/Tokyo", "Australia/Sydney"]
        
        for tz in timezones:
            result = service.generate_vector_embedding(
                user_id=uuid4(),
                skill_level=5,
                learning_velocity=1.0,
                timezone=tz,
                language="en",
                interest_area="Test"
            )
            
            # Verify timezone is stored
            added_embedding = mock_db.add.call_args[0][0]
            assert added_embedding.extra_metadata['timezone'] == tz
            assert isinstance(added_embedding.timezone_offset, float)
    
    @patch('app.services.portfolio_analysis_service.settings')
    def test_generate_vector_embedding_different_languages(
        self,
        mock_settings,
        service,
        mock_db,
        mock_pinecone,
        mock_sentence_transformer
    ):
        """Test vector embedding generation with different languages."""
        mock_settings.PINECONE_API_KEY = "test_api_key"
        mock_settings.PINECONE_ENVIRONMENT = "us-east-1"
        
        mock_pc, mock_index = mock_pinecone
        
        # Test with different languages
        languages = ["en", "es", "fr", "de", "zh", "ja"]
        
        for lang in languages:
            result = service.generate_vector_embedding(
                user_id=uuid4(),
                skill_level=5,
                learning_velocity=1.0,
                timezone="UTC",
                language=lang,
                interest_area="Test"
            )
            
            # Verify language is stored
            added_embedding = mock_db.add.call_args[0][0]
            assert added_embedding.language_code == lang
    
    @patch('app.services.portfolio_analysis_service.settings')
    def test_generate_vector_embedding_skill_level_normalization(
        self,
        mock_settings,
        service,
        mock_db,
        mock_pinecone,
        mock_sentence_transformer
    ):
        """Test that skill level is properly normalized to [0, 1]."""
        mock_settings.PINECONE_API_KEY = "test_api_key"
        mock_settings.PINECONE_ENVIRONMENT = "us-east-1"
        
        mock_pc, mock_index = mock_pinecone
        
        # Test with different skill levels
        for skill_level in range(1, 11):
            result = service.generate_vector_embedding(
                user_id=uuid4(),
                skill_level=skill_level,
                learning_velocity=1.0,
                timezone="UTC",
                language="en",
                interest_area="Test"
            )
            
            # Verify normalization
            added_embedding = mock_db.add.call_args[0][0]
            normalized = added_embedding.extra_metadata['normalized_skill_level']
            assert 0.0 <= normalized <= 1.0
            assert normalized == skill_level / 10.0
    
    @patch('app.services.portfolio_analysis_service.settings')
    def test_generate_vector_embedding_velocity_normalization(
        self,
        mock_settings,
        service,
        mock_db,
        mock_pinecone,
        mock_sentence_transformer
    ):
        """Test that learning velocity is properly normalized."""
        mock_settings.PINECONE_API_KEY = "test_api_key"
        mock_settings.PINECONE_ENVIRONMENT = "us-east-1"
        
        mock_pc, mock_index = mock_pinecone
        
        # Test with different velocities
        velocities = [0.5, 1.0, 2.5, 5.0, 10.0, 15.0]
        
        for velocity in velocities:
            result = service.generate_vector_embedding(
                user_id=uuid4(),
                skill_level=5,
                learning_velocity=velocity,
                timezone="UTC",
                language="en",
                interest_area="Test"
            )
            
            # Verify normalization (capped at 1.0)
            added_embedding = mock_db.add.call_args[0][0]
            normalized = added_embedding.extra_metadata['normalized_velocity']
            assert 0.0 <= normalized <= 1.0
            expected = min(velocity / 10.0, 1.0)
            assert normalized == expected
    
    @patch('app.services.portfolio_analysis_service.settings')
    def test_generate_vector_embedding_pinecone_upsert_failure(
        self,
        mock_settings,
        service,
        mock_db,
        mock_sentence_transformer
    ):
        """Test that Pinecone upsert failure raises exception."""
        mock_settings.PINECONE_API_KEY = "test_api_key"
        mock_settings.PINECONE_ENVIRONMENT = "us-east-1"
        
        with patch('app.services.portfolio_analysis_service.Pinecone') as mock_pc_class:
            mock_pc = Mock()
            mock_pc_class.return_value = mock_pc
            
            # Mock list_indexes
            mock_index_info = Mock()
            mock_index_info.name = "origin-user-embeddings"
            mock_pc.list_indexes.return_value = [mock_index_info]
            
            # Mock index with failing upsert
            mock_index = Mock()
            mock_index.upsert.side_effect = Exception("Pinecone upsert failed")
            mock_pc.Index.return_value = mock_index
            
            user_id = uuid4()
            
            # Execute and expect exception
            with pytest.raises(Exception, match="Pinecone upsert failed"):
                service.generate_vector_embedding(
                    user_id=user_id,
                    skill_level=5,
                    learning_velocity=1.0,
                    timezone="UTC",
                    language="en",
                    interest_area="Test"
                )
    
    @patch('app.services.portfolio_analysis_service.settings')
    def test_generate_vector_embedding_feature_text_generation(
        self,
        mock_settings,
        service,
        mock_db,
        mock_pinecone,
        mock_sentence_transformer
    ):
        """Test that feature text is properly generated for embedding."""
        mock_settings.PINECONE_API_KEY = "test_api_key"
        mock_settings.PINECONE_ENVIRONMENT = "us-east-1"
        
        mock_pc, mock_index = mock_pinecone
        
        user_id = uuid4()
        skill_level = 8
        learning_velocity = 3.5
        timezone = "America/Los_Angeles"
        language = "es"
        interest_area = "Data Science"
        
        # Execute
        result = service.generate_vector_embedding(
            user_id=user_id,
            skill_level=skill_level,
            learning_velocity=learning_velocity,
            timezone=timezone,
            language=language,
            interest_area=interest_area
        )
        
        # Verify feature text contains all components
        added_embedding = mock_db.add.call_args[0][0]
        feature_text = added_embedding.extra_metadata['feature_text']
        
        assert str(skill_level) in feature_text
        assert f"{learning_velocity:.2f}" in feature_text
        assert timezone in feature_text
        assert language in feature_text
        assert interest_area in feature_text
        
        # Verify SentenceTransformer was called with feature text
        assert mock_sentence_transformer.encode.called
        encode_args = mock_sentence_transformer.encode.call_args[0]
        assert encode_args[0] == feature_text
