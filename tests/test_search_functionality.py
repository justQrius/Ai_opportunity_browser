"""Unit tests for search functionality implementation.

Tests Requirements 6.1.2 (Semantic search with vector similarity and faceted search capabilities).
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.schemas.opportunity import OpportunitySearchRequest
from shared.services.opportunity_service import opportunity_service
from shared.services.ai_service import ai_service
from shared.vector_db import opportunity_vector_service


@pytest.fixture
def sample_opportunities():
    """Create sample opportunities for testing."""
    from datetime import datetime
    
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
            implementation_complexity="Medium",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
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
            implementation_complexity="High",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
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
            implementation_complexity="High",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    ]


class TestSemanticSearchService:
    """Test semantic search functionality in opportunity service."""
    
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
    async def test_semantic_search_with_filters(self, sample_opportunities):
        """Test semantic search with additional filters."""
        mock_db = AsyncMock()
        mock_embedding = [0.1] * 1536
        mock_vector_results = [
            {"id": "opp-1", "score": 0.95, "metadata": {"title": "AI Chatbot"}}
        ]
        
        with patch.object(ai_service, 'generate_search_query_embedding', return_value=mock_embedding), \
             patch.object(opportunity_vector_service, 'find_similar_opportunities', return_value=mock_vector_results), \
             patch('shared.services.opportunity_service.select') as mock_select:
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = sample_opportunities[:1]
            mock_db.execute.return_value = mock_result
            
            # Create search request with filters
            search_request = OpportunitySearchRequest(
                query="customer service automation",
                ai_solution_types=["NLP", "ML"],
                target_industries=["Technology"],
                min_validation_score=8.0,
                status=[OpportunityStatus.VALIDATED],
                page=1,
                page_size=10
            )
            
            # Execute semantic search
            opportunities, total_count = await opportunity_service.semantic_search_opportunities(
                mock_db, search_request, "user-123"
            )
            
            # Assertions
            assert len(opportunities) == 1
            assert total_count == 1
            
            # Verify filters were passed to vector search
            call_args = opportunity_vector_service.find_similar_opportunities.call_args
            filters = call_args[1]["filters"]
            assert "status" in filters
            assert filters["status"]["$in"] == ["validated"]
    
    @pytest.mark.asyncio
    async def test_semantic_search_no_query_raises_error(self):
        """Test that semantic search without query raises ValueError."""
        mock_db = AsyncMock()
        
        search_request = OpportunitySearchRequest(
            page=1,
            page_size=10
        )
        
        with pytest.raises(ValueError, match="Query is required for semantic search"):
            await opportunity_service.semantic_search_opportunities(
                mock_db, search_request, "user-123"
            )
    
    @pytest.mark.asyncio
    async def test_semantic_search_fallback_on_error(self, sample_opportunities):
        """Test that semantic search falls back to regular search on error."""
        mock_db = AsyncMock()
        
        with patch.object(ai_service, 'generate_search_query_embedding', side_effect=Exception("AI service error")), \
             patch.object(opportunity_service, 'search_opportunities', return_value=(sample_opportunities, 3)) as mock_fallback:
            
            search_request = OpportunitySearchRequest(
                query="AI chatbot",
                page=1,
                page_size=10
            )
            
            # Execute semantic search (should fallback)
            opportunities, total_count = await opportunity_service.semantic_search_opportunities(
                mock_db, search_request, "user-123"
            )
            
            # Verify fallback was called
            mock_fallback.assert_called_once_with(mock_db, search_request, "user-123")
            assert len(opportunities) == 3
            assert total_count == 3


class TestFacetedSearchService:
    """Test faceted search functionality in opportunity service."""
    
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
            assert facets["validation_score_ranges"]["8-10"] == 2  # Two with scores 9.2 and 8.5
            assert facets["validation_score_ranges"]["6-8"] == 1  # One with score 6.8
            
            # Check metadata
            assert facets["_metadata"]["total_opportunities"] == 3
            assert facets["_metadata"]["query"] is None
    
    @pytest.mark.asyncio
    async def test_get_search_facets_with_query(self, sample_opportunities):
        """Test faceted search with query filter."""
        mock_db = AsyncMock()
        
        with patch('shared.services.opportunity_service.select') as mock_select:
            # Mock database query with filtered results
            filtered_opportunities = [sample_opportunities[0]]  # Only chatbot opportunity
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = filtered_opportunities
            mock_db.execute.return_value = mock_result
            
            # Execute facets generation with query
            facets = await opportunity_service.get_search_facets(mock_db, "chatbot")
            
            # Assertions
            assert facets["_metadata"]["total_opportunities"] == 1
            assert facets["_metadata"]["query"] == "chatbot"
            
            # Check that only relevant facets are present
            assert facets["status"]["validated"] == 1
            assert "validating" not in facets["status"]
    
    @pytest.mark.asyncio
    async def test_get_search_facets_error_handling(self):
        """Test faceted search error handling."""
        mock_db = AsyncMock()
        
        with patch('shared.services.opportunity_service.select', side_effect=Exception("Database error")):
            
            # Execute facets generation (should handle error gracefully)
            facets = await opportunity_service.get_search_facets(mock_db, "test")
            
            # Should return empty facets structure with error info
            assert facets["_metadata"]["total_opportunities"] == 0
            assert facets["_metadata"]["query"] == "test"
            assert "error" in facets["_metadata"]
            
            # All facet categories should be empty
            assert facets["status"] == {}
            assert facets["ai_solution_types"] == {}
            assert facets["target_industries"] == {}


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


class TestAIServiceEmbedding:
    """Test AI service embedding generation."""
    
    @pytest.mark.asyncio
    async def test_generate_search_query_embedding(self):
        """Test search query embedding generation."""
        mock_embedding = [0.1] * 1536
        
        with patch.object(ai_service, 'generate_text_embedding', return_value=mock_embedding):
            
            # Test basic query
            embedding = await ai_service.generate_search_query_embedding("AI chatbot")
            
            assert embedding == mock_embedding
            ai_service.generate_text_embedding.assert_called_once()
            
            # Verify the combined text includes the query
            call_args = ai_service.generate_text_embedding.call_args[0][0]
            assert "Search Query: AI chatbot" in call_args
    
    @pytest.mark.asyncio
    async def test_generate_search_query_embedding_with_filters(self):
        """Test search query embedding generation with filters."""
        mock_embedding = [0.1] * 1536
        
        with patch.object(ai_service, 'generate_text_embedding', return_value=mock_embedding):
            
            filters = {
                "ai_solution_types": ["NLP", "ML"],
                "target_industries": ["Technology"],
                "tags": ["automation"]
            }
            
            embedding = await ai_service.generate_search_query_embedding("chatbot", filters)
            
            assert embedding == mock_embedding
            
            # Verify the combined text includes filters
            call_args = ai_service.generate_text_embedding.call_args[0][0]
            assert "Search Query: chatbot" in call_args
            assert "AI Types: NLP, ML" in call_args
            assert "Industries: Technology" in call_args
            assert "Tags: automation" in call_args
    
    @pytest.mark.asyncio
    async def test_generate_opportunity_embedding(self):
        """Test opportunity embedding generation."""
        mock_embedding = [0.1] * 1536
        
        with patch.object(ai_service, 'generate_text_embedding', return_value=mock_embedding):
            
            opportunity_data = {
                "title": "AI Chatbot",
                "description": "Customer service automation",
                "summary": "AI-powered support",
                "ai_solution_types": ["NLP", "ML"],
                "target_industries": ["Technology"],
                "tags": ["chatbot", "automation"]
            }
            
            embedding = await ai_service.generate_opportunity_embedding(opportunity_data)
            
            assert embedding == mock_embedding
            
            # Verify the combined text includes all fields
            call_args = ai_service.generate_text_embedding.call_args[0][0]
            assert "Title: AI Chatbot" in call_args
            assert "Description: Customer service automation" in call_args
            assert "AI Solution Types: NLP, ML" in call_args
            assert "Target Industries: Technology" in call_args
            assert "Tags: chatbot, automation" in call_args


if __name__ == "__main__":
    pytest.main([__file__])