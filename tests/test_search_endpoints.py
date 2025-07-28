"""Tests for search endpoints implementation.

Tests Requirements 6.1.2 (Semantic search with vector similarity and faceted search capabilities).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch, MagicMock
import json

from api.main import app
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.user import User, UserRole
from shared.schemas.opportunity import OpportunitySearchRequest
from shared.services.opportunity_service import opportunity_service
from shared.services.ai_service import ai_service
from shared.vector_db import opportunity_vector_service


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create mock user for testing."""
    return User(
        id="test-user-id",
        email="test@example.com",
        username="testuser",
        role=UserRole.USER,
        is_active=True
    )


@pytest.fixture
def sample_opportunities():
    """Create sample opportunities for testing."""
    return [
        Opportunity(
            id="opp-1",
            title="AI-Powered Customer Service Chatbot",
            description="Develop an intelligent chatbot for customer service automation using NLP",
            summary="AI chatbot for customer support",
            ai_solution_types='["NLP", "ML"]',
            target_industries='["Technology", "E-commerce"]',
            tags='["chatbot", "customer-service", "automation"]',
            status=OpportunityStatus.VALIDATED,
            validation_score=8.5,
            ai_feasibility_score=7.8,
            geographic_scope="Global",
            implementation_complexity="Medium"
        ),
        Opportunity(
            id="opp-2",
            title="Computer Vision for Quality Control",
            description="Implement computer vision system for manufacturing quality control",
            summary="CV system for quality assurance",
            ai_solution_types='["Computer Vision", "ML"]',
            target_industries='["Manufacturing", "Automotive"]',
            tags='["computer-vision", "quality-control", "manufacturing"]',
            status=OpportunityStatus.VALIDATED,
            validation_score=9.2,
            ai_feasibility_score=8.1,
            geographic_scope="North America",
            implementation_complexity="High"
        ),
        Opportunity(
            id="opp-3",
            title="Predictive Analytics for Healthcare",
            description="Build predictive models for patient outcome prediction",
            summary="Predictive analytics in healthcare",
            ai_solution_types='["ML", "Predictive Analytics"]',
            target_industries='["Healthcare", "Medical"]',
            tags='["healthcare", "predictive-analytics", "patient-care"]',
            status=OpportunityStatus.VALIDATING,
            validation_score=6.8,
            ai_feasibility_score=7.2,
            geographic_scope="United States",
            implementation_complexity="High"
        )
    ]


class TestSemanticSearch:
    """Test semantic search functionality."""
    
    @pytest.mark.asyncio
    async def test_semantic_search_success(self, client, mock_user, sample_opportunities):
        """Test successful semantic search."""
        # Mock dependencies
        with patch('api.routers.opportunities.get_optional_user', return_value=mock_user), \
             patch('api.routers.opportunities.get_db') as mock_db, \
             patch.object(opportunity_service, 'semantic_search_opportunities') as mock_search:
            
            # Setup mocks
            mock_db.return_value = AsyncMock()
            mock_search.return_value = (sample_opportunities[:2], 2)
            
            # Make request
            response = client.post("/api/v1/opportunities/search/semantic", json={
                "query": "AI chatbot for customer service",
                "page": 1,
                "page_size": 10
            })
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            
            assert "items" in data
            assert "pagination" in data
            assert "total_count" in data
            assert data["total_count"] == 2
            assert len(data["items"]) == 2
            assert data["metadata"]["search_type"] == "semantic"
            assert data["metadata"]["embedding_based"] is True
            
            # Verify search was called with correct parameters
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            search_request = call_args[0][1]
            assert search_request.query == "AI chatbot for customer service"
    
    @pytest.mark.asyncio
    async def test_semantic_search_no_query(self, client, mock_user):
        """Test semantic search without query parameter."""
        with patch('api.routers.opportunities.get_optional_user', return_value=mock_user), \
             patch('api.routers.opportunities.get_db') as mock_db:
            
            mock_db.return_value = AsyncMock()
            
            # Make request without query
            response = client.post("/api/v1/opportunities/search/semantic", json={
                "page": 1,
                "page_size": 10
            })
            
            # Should return 400 Bad Request
            assert response.status_code == 400
            assert "Query parameter is required" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_semantic_search_with_filters(self, client, mock_user, sample_opportunities):
        """Test semantic search with additional filters."""
        with patch('api.routers.opportunities.get_optional_user', return_value=mock_user), \
             patch('api.routers.opportunities.get_db') as mock_db, \
             patch.object(opportunity_service, 'semantic_search_opportunities') as mock_search:
            
            mock_db.return_value = AsyncMock()
            mock_search.return_value = (sample_opportunities[:1], 1)
            
            # Make request with filters
            response = client.post("/api/v1/opportunities/search/semantic", json={
                "query": "customer service automation",
                "ai_solution_types": ["NLP", "ML"],
                "target_industries": ["Technology"],
                "min_validation_score": 8.0,
                "page": 1,
                "page_size": 10
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 1
            
            # Verify filters were passed
            call_args = mock_search.call_args
            search_request = call_args[0][1]
            assert search_request.ai_solution_types == ["NLP", "ML"]
            assert search_request.target_industries == ["Technology"]
            assert search_request.min_validation_score == 8.0


class TestFacetedSearch:
    """Test faceted search functionality."""
    
    @pytest.mark.asyncio
    async def test_get_search_facets_success(self, client, mock_user):
        """Test successful facets retrieval."""
        mock_facets = {
            "status": {
                "validated": 15,
                "validating": 8,
                "discovered": 5
            },
            "ai_solution_types": {
                "NLP": 12,
                "ML": 18,
                "Computer Vision": 7,
                "Predictive Analytics": 5
            },
            "target_industries": {
                "Technology": 10,
                "Healthcare": 8,
                "Manufacturing": 6,
                "Finance": 4
            },
            "implementation_complexity": {
                "Low": 5,
                "Medium": 12,
                "High": 11
            },
            "geographic_scope": {
                "Global": 8,
                "North America": 7,
                "United States": 6,
                "Europe": 4
            },
            "validation_score_ranges": {
                "0-2": 2,
                "2-4": 3,
                "4-6": 5,
                "6-8": 8,
                "8-10": 10
            },
            "tags": {
                "automation": 8,
                "customer-service": 6,
                "healthcare": 5,
                "manufacturing": 4
            },
            "_metadata": {
                "total_opportunities": 28,
                "query": None,
                "generated_at": "2024-01-15T10:30:00"
            }
        }
        
        with patch('api.routers.opportunities.get_optional_user', return_value=mock_user), \
             patch('api.routers.opportunities.get_db') as mock_db, \
             patch.object(opportunity_service, 'get_search_facets') as mock_facets_method:
            
            mock_db.return_value = AsyncMock()
            mock_facets_method.return_value = mock_facets
            
            # Make request
            response = client.get("/api/v1/opportunities/search/facets")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "facets" in data
            assert "query" in data
            assert "generated_at" in data
            
            facets = data["facets"]
            assert "status" in facets
            assert "ai_solution_types" in facets
            assert "target_industries" in facets
            assert "implementation_complexity" in facets
            assert "validation_score_ranges" in facets
            assert "_metadata" in facets
            
            # Check specific facet values
            assert facets["status"]["validated"] == 15
            assert facets["ai_solution_types"]["ML"] == 18
            assert facets["_metadata"]["total_opportunities"] == 28
    
    @pytest.mark.asyncio
    async def test_get_search_facets_with_query(self, client, mock_user):
        """Test facets retrieval with query filter."""
        mock_facets = {
            "status": {"validated": 5, "validating": 2},
            "ai_solution_types": {"NLP": 4, "ML": 3},
            "_metadata": {
                "total_opportunities": 7,
                "query": "chatbot",
                "generated_at": "2024-01-15T10:30:00"
            }
        }
        
        with patch('api.routers.opportunities.get_optional_user', return_value=mock_user), \
             patch('api.routers.opportunities.get_db') as mock_db, \
             patch.object(opportunity_service, 'get_search_facets') as mock_facets_method:
            
            mock_db.return_value = AsyncMock()
            mock_facets_method.return_value = mock_facets
            
            # Make request with query
            response = client.get("/api/v1/opportunities/search/facets?query=chatbot")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["query"] == "chatbot"
            assert data["facets"]["_metadata"]["query"] == "chatbot"
            assert data["facets"]["_metadata"]["total_opportunities"] == 7
            
            # Verify method was called with query
            mock_facets_method.assert_called_once_with(mock_db.return_value, "chatbot")


class TestOpportunityServiceSemanticSearch:
    """Test opportunity service semantic search methods."""
    
    @pytest.mark.asyncio
    async def test_semantic_search_opportunities(self, sample_opportunities):
        """Test semantic search in opportunity service."""
        mock_db = AsyncMock()
        
        # Mock AI service embedding generation
        mock_embedding = [0.1] * 1536  # Mock 1536-dimensional embedding
        
        # Mock vector search results
        mock_vector_results = [
            {"id": "opp-1", "score": 0.95, "metadata": {"title": "AI Chatbot"}},
            {"id": "opp-2", "score": 0.87, "metadata": {"title": "Computer Vision"}}
        ]
        
        with patch.object(ai_service, 'generate_search_query_embedding', return_value=mock_embedding), \
             patch.object(opportunity_vector_service, 'find_similar_opportunities', return_value=mock_vector_results), \
             patch('shared.services.opportunity_service.select') as mock_select:
            
            # Mock database query
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = sample_opportunities[:2]
            mock_db.execute.return_value = mock_result
            
            # Create search request
            search_request = OpportunitySearchRequest(
                query="AI chatbot customer service",
                page=1,
                page_size=10
            )
            
            # Execute semantic search
            opportunities, total_count = await opportunity_service.semantic_search_opportunities(
                mock_db, search_request, "user-123"
            )
            
            # Assertions
            assert len(opportunities) == 2
            assert total_count == 2
            assert opportunities[0].id == "opp-1"
            assert opportunities[1].id == "opp-2"
            
            # Verify AI service was called
            ai_service.generate_search_query_embedding.assert_called_once()
            
            # Verify vector search was called
            opportunity_vector_service.find_similar_opportunities.assert_called_once_with(
                query_embedding=mock_embedding,
                top_k=30,  # page_size * 3
                filters={}
            )
    
    @pytest.mark.asyncio
    async def test_get_search_facets(self, sample_opportunities):
        """Test faceted search data generation."""
        mock_db = AsyncMock()
        
        with patch('shared.services.opportunity_service.select') as mock_select:
            # Mock database query
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = sample_opportunities
            mock_db.execute.return_value = mock_result
            
            # Execute facets generation
            facets = await opportunity_service.get_search_facets(mock_db, None)
            
            # Assertions
            assert "status" in facets
            assert "ai_solution_types" in facets
            assert "target_industries" in facets
            assert "implementation_complexity" in facets
            assert "validation_score_ranges" in facets
            assert "_metadata" in facets
            
            # Check status facet
            assert facets["status"]["validated"] == 2  # Two validated opportunities
            assert facets["status"]["validating"] == 1  # One validating opportunity
            
            # Check AI solution types facet
            assert "NLP" in facets["ai_solution_types"]
            assert "ML" in facets["ai_solution_types"]
            assert "Computer Vision" in facets["ai_solution_types"]
            
            # Check validation score ranges
            assert facets["validation_score_ranges"]["8-10"] == 1  # One with score 9.2
            assert facets["validation_score_ranges"]["6-8"] == 2  # Two with scores 8.5 and 6.8
            
            # Check metadata
            assert facets["_metadata"]["total_opportunities"] == 3
            assert facets["_metadata"]["query"] is None


class TestEmbeddingGeneration:
    """Test embedding generation and storage."""
    
    @pytest.mark.asyncio
    async def test_generate_and_store_embedding(self, sample_opportunities):
        """Test embedding generation and storage for opportunities."""
        opportunity = sample_opportunities[0]
        mock_embedding = [0.1] * 1536
        
        with patch.object(ai_service, 'generate_opportunity_embedding', return_value=mock_embedding), \
             patch.object(opportunity_vector_service, 'store_opportunity_embedding', return_value=True) as mock_store:
            
            # Execute embedding generation
            await opportunity_service._generate_and_store_embedding(opportunity)
            
            # Verify AI service was called
            ai_service.generate_opportunity_embedding.assert_called_once()
            
            # Verify vector storage was called
            mock_store.assert_called_once()
            call_args = mock_store.call_args
            
            assert call_args[1]["opportunity_id"] == opportunity.id
            assert call_args[1]["embedding"] == mock_embedding
            assert "metadata" in call_args[1]
            
            metadata = call_args[1]["metadata"]
            assert metadata["title"] == opportunity.title
            assert metadata["status"] == opportunity.status.value
            assert metadata["validation_score"] == opportunity.validation_score
    
    @pytest.mark.asyncio
    async def test_embedding_generation_failure_handling(self, sample_opportunities):
        """Test that embedding generation failures don't break opportunity creation."""
        opportunity = sample_opportunities[0]
        
        with patch.object(ai_service, 'generate_opportunity_embedding', side_effect=Exception("AI service error")):
            
            # Should not raise exception
            try:
                await opportunity_service._generate_and_store_embedding(opportunity)
            except Exception:
                pytest.fail("Embedding generation failure should not raise exception")


if __name__ == "__main__":
    pytest.main([__file__])