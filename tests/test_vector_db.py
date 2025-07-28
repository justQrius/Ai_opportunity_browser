"""Tests for vector database functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from shared.vector_db import (
    VectorDatabaseManager,
    OpportunityVectorService,
    MarketSignalVectorService,
    UserPreferenceVectorService
)


class TestVectorDatabaseManager:
    """Test vector database manager functionality."""
    
    @pytest.fixture
    def mock_pinecone(self):
        """Mock Pinecone client."""
        with patch('shared.vector_db.Pinecone') as mock_pc:
            mock_instance = Mock()
            mock_pc.return_value = mock_instance
            
            # Mock list_indexes
            mock_index = Mock()
            mock_index.name = "test-index"
            mock_instance.list_indexes.return_value = [mock_index]
            
            # Mock create_index
            mock_instance.create_index = Mock()
            
            # Mock Index
            mock_index_instance = Mock()
            mock_instance.Index.return_value = mock_index_instance
            
            yield mock_instance
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_pinecone):
        """Test vector database initialization."""
        with patch.dict('os.environ', {'PINECONE_API_KEY': 'test-key'}):
            vector_db = VectorDatabaseManager()
            await vector_db.initialize()
            
            assert vector_db.pc is not None
            assert vector_db.api_key == 'test-key'
    
    @pytest.mark.asyncio
    async def test_initialization_missing_api_key(self):
        """Test initialization fails without API key."""
        with patch.dict('os.environ', {}, clear=True):
            vector_db = VectorDatabaseManager()
            
            with pytest.raises(ValueError, match="PINECONE_API_KEY"):
                await vector_db.initialize()
    
    @pytest.mark.asyncio
    async def test_upsert_vectors(self, mock_pinecone):
        """Test vector upsert functionality."""
        with patch.dict('os.environ', {'PINECONE_API_KEY': 'test-key'}):
            vector_db = VectorDatabaseManager()
            await vector_db.initialize()
            
            # Mock index
            mock_index = Mock()
            vector_db.pc.Index.return_value = mock_index
            
            vectors = [
                {
                    "id": "test-1",
                    "values": [0.1, 0.2, 0.3],
                    "metadata": {"type": "test"}
                }
            ]
            
            result = await vector_db.upsert_vectors("opportunities", vectors)
            
            assert result is True
            mock_index.upsert.assert_called_once_with(vectors=vectors)
    
    @pytest.mark.asyncio
    async def test_query_vectors(self, mock_pinecone):
        """Test vector query functionality."""
        with patch.dict('os.environ', {'PINECONE_API_KEY': 'test-key'}):
            vector_db = VectorDatabaseManager()
            await vector_db.initialize()
            
            # Mock index and query response
            mock_index = Mock()
            mock_match = Mock()
            mock_match.id = "test-1"
            mock_match.score = 0.95
            mock_match.metadata = {"type": "test"}
            mock_match.values = None
            
            mock_response = Mock()
            mock_response.matches = [mock_match]
            mock_index.query.return_value = mock_response
            
            vector_db.pc.Index.return_value = mock_index
            
            query_vector = [0.1, 0.2, 0.3]
            results = await vector_db.query_vectors("opportunities", query_vector)
            
            assert len(results) == 1
            assert results[0]["id"] == "test-1"
            assert results[0]["score"] == 0.95
            assert results[0]["metadata"]["type"] == "test"
    
    @pytest.mark.asyncio
    async def test_delete_vectors(self, mock_pinecone):
        """Test vector deletion functionality."""
        with patch.dict('os.environ', {'PINECONE_API_KEY': 'test-key'}):
            vector_db = VectorDatabaseManager()
            await vector_db.initialize()
            
            # Mock index
            mock_index = Mock()
            vector_db.pc.Index.return_value = mock_index
            
            ids = ["test-1", "test-2"]
            result = await vector_db.delete_vectors("opportunities", ids)
            
            assert result is True
            mock_index.delete.assert_called_once_with(ids=ids)
    
    @pytest.mark.asyncio
    async def test_get_index_stats(self, mock_pinecone):
        """Test getting index statistics."""
        with patch.dict('os.environ', {'PINECONE_API_KEY': 'test-key'}):
            vector_db = VectorDatabaseManager()
            await vector_db.initialize()
            
            # Mock index and stats
            mock_index = Mock()
            mock_stats = Mock()
            mock_stats.total_vector_count = 100
            mock_stats.dimension = 1536
            mock_stats.index_fullness = 0.1
            mock_stats.namespaces = {}
            
            mock_index.describe_index_stats.return_value = mock_stats
            vector_db.pc.Index.return_value = mock_index
            
            stats = await vector_db.get_index_stats("opportunities")
            
            assert stats["total_vector_count"] == 100
            assert stats["dimension"] == 1536
            assert stats["index_fullness"] == 0.1


class TestOpportunityVectorService:
    """Test opportunity vector service."""
    
    @pytest.fixture
    def mock_vector_db(self):
        """Mock vector database manager."""
        mock_db = Mock(spec=VectorDatabaseManager)
        mock_db.upsert_vectors = AsyncMock(return_value=True)
        mock_db.query_vectors = AsyncMock(return_value=[
            {
                "id": "opp-1",
                "score": 0.95,
                "metadata": {"title": "Test Opportunity"}
            }
        ])
        return mock_db
    
    @pytest.mark.asyncio
    async def test_store_opportunity_embedding(self, mock_vector_db):
        """Test storing opportunity embedding."""
        service = OpportunityVectorService(mock_vector_db)
        
        embedding = [0.1, 0.2, 0.3]
        metadata = {"title": "Test Opportunity", "industry": "tech"}
        
        result = await service.store_opportunity_embedding("opp-1", embedding, metadata)
        
        assert result is True
        mock_vector_db.upsert_vectors.assert_called_once()
        
        # Check the call arguments
        call_args = mock_vector_db.upsert_vectors.call_args
        assert call_args[0][0] == "opportunities"  # index_name
        
        vector_data = call_args[0][1][0]  # first vector in the list
        assert vector_data["id"] == "opp-1"
        assert vector_data["values"] == embedding
        assert vector_data["metadata"]["title"] == "Test Opportunity"
        assert vector_data["metadata"]["type"] == "opportunity"
    
    @pytest.mark.asyncio
    async def test_find_similar_opportunities(self, mock_vector_db):
        """Test finding similar opportunities."""
        service = OpportunityVectorService(mock_vector_db)
        
        query_embedding = [0.1, 0.2, 0.3]
        filters = {"industry": "tech"}
        
        results = await service.find_similar_opportunities(
            query_embedding, top_k=5, filters=filters
        )
        
        assert len(results) == 1
        assert results[0]["id"] == "opp-1"
        assert results[0]["score"] == 0.95
        
        mock_vector_db.query_vectors.assert_called_once_with(
            index_name="opportunities",
            query_vector=query_embedding,
            top_k=5,
            filter_dict=filters,
            include_metadata=True
        )


class TestMarketSignalVectorService:
    """Test market signal vector service."""
    
    @pytest.fixture
    def mock_vector_db(self):
        """Mock vector database manager."""
        mock_db = Mock(spec=VectorDatabaseManager)
        mock_db.upsert_vectors = AsyncMock(return_value=True)
        mock_db.query_vectors = AsyncMock(return_value=[])
        return mock_db
    
    @pytest.mark.asyncio
    async def test_store_signal_embedding(self, mock_vector_db):
        """Test storing market signal embedding."""
        service = MarketSignalVectorService(mock_vector_db)
        
        embedding = [0.4, 0.5, 0.6]
        metadata = {"source": "reddit", "signal_type": "pain_point"}
        
        result = await service.store_signal_embedding("signal-1", embedding, metadata)
        
        assert result is True
        mock_vector_db.upsert_vectors.assert_called_once()
        
        # Check the call arguments
        call_args = mock_vector_db.upsert_vectors.call_args
        assert call_args[0][0] == "market-signals"  # index_name
        
        vector_data = call_args[0][1][0]  # first vector in the list
        assert vector_data["id"] == "signal-1"
        assert vector_data["values"] == embedding
        assert vector_data["metadata"]["source"] == "reddit"
        assert vector_data["metadata"]["type"] == "market_signal"


class TestUserPreferenceVectorService:
    """Test user preference vector service."""
    
    @pytest.fixture
    def mock_vector_db(self):
        """Mock vector database manager."""
        mock_db = Mock(spec=VectorDatabaseManager)
        mock_db.upsert_vectors = AsyncMock(return_value=True)
        mock_db.query_vectors = AsyncMock(return_value=[])
        return mock_db
    
    @pytest.mark.asyncio
    async def test_store_user_preferences(self, mock_vector_db):
        """Test storing user preference embedding."""
        service = UserPreferenceVectorService(mock_vector_db)
        
        embedding = [0.7, 0.8, 0.9]
        metadata = {"interests": ["AI", "ML"], "experience_level": "expert"}
        
        result = await service.store_user_preferences("user-1", embedding, metadata)
        
        assert result is True
        mock_vector_db.upsert_vectors.assert_called_once()
        
        # Check the call arguments
        call_args = mock_vector_db.upsert_vectors.call_args
        assert call_args[0][0] == "user-preferences"  # index_name
        
        vector_data = call_args[0][1][0]  # first vector in the list
        assert vector_data["id"] == "user-1"
        assert vector_data["values"] == embedding
        assert vector_data["metadata"]["interests"] == ["AI", "ML"]
        assert vector_data["metadata"]["type"] == "user_preferences"
    
    @pytest.mark.asyncio
    async def test_find_similar_users(self, mock_vector_db):
        """Test finding similar users."""
        service = UserPreferenceVectorService(mock_vector_db)
        
        user_embedding = [0.7, 0.8, 0.9]
        
        await service.find_similar_users(user_embedding, top_k=5, exclude_user_id="user-1")
        
        mock_vector_db.query_vectors.assert_called_once_with(
            index_name="user-preferences",
            query_vector=user_embedding,
            top_k=5,
            filter_dict={"id": {"$ne": "user-1"}},
            include_metadata=True
        )