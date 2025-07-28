"""Tests for Opportunity model and service."""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, Mock

from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.schemas.opportunity import OpportunityCreate, OpportunityUpdate, OpportunitySearchRequest
from shared.services.opportunity_service import OpportunityService


class TestOpportunityModel:
    """Test Opportunity model functionality."""
    
    def test_opportunity_model_creation(self):
        """Test Opportunity model instance creation."""
        opportunity = Opportunity(
            title="AI-Powered Customer Service",
            description="Automated customer service using NLP and ML",
            ai_solution_types='["nlp", "ml"]',
            target_industries='["retail", "ecommerce"]',
            status=OpportunityStatus.DISCOVERED
        )
        
        assert opportunity.title == "AI-Powered Customer Service"
        assert opportunity.status == OpportunityStatus.DISCOVERED
        assert opportunity.validation_score == 0.0
        assert opportunity.confidence_rating == 0.0
        assert opportunity.ai_feasibility_score == 0.0
    
    def test_opportunity_status_enum(self):
        """Test opportunity status enumeration."""
        assert OpportunityStatus.DISCOVERED == "discovered"
        assert OpportunityStatus.ANALYZING == "analyzing"
        assert OpportunityStatus.VALIDATING == "validating"
        assert OpportunityStatus.VALIDATED == "validated"
        assert OpportunityStatus.REJECTED == "rejected"
        assert OpportunityStatus.ARCHIVED == "archived"
    
    def test_opportunity_repr(self):
        """Test Opportunity string representation."""
        opportunity = Opportunity(
            id="test-id",
            title="Test Opportunity",
            description="Test description",
            status=OpportunityStatus.VALIDATED
        )
        
        repr_str = repr(opportunity)
        assert "Test Opportunity" in repr_str
        assert "validated" in repr_str


class TestOpportunityService:
    """Test OpportunityService functionality."""
    
    @pytest.fixture
    def opportunity_service(self):
        """Create OpportunityService instance."""
        return OpportunityService()
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def sample_opportunity_create(self):
        """Sample opportunity creation data."""
        return OpportunityCreate(
            title="AI-Powered Document Analysis",
            description="Automated document processing and analysis using NLP and computer vision to extract insights from unstructured documents.",
            summary="AI solution for document processing automation",
            ai_solution_types=["nlp", "computer_vision", "ml"],
            required_capabilities=["text_extraction", "image_processing", "classification"],
            target_industries=["legal", "healthcare", "finance"],
            geographic_scope="global",
            tags=["automation", "document_processing", "ai"],
            source_urls=["https://example.com/source1", "https://example.com/source2"],
            discovery_method="reddit_monitoring"
        )
    
    @pytest.mark.asyncio
    async def test_create_opportunity(self, opportunity_service, mock_db_session, sample_opportunity_create):
        """Test opportunity creation."""
        # Mock database operations
        mock_db_session.add = AsyncMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        
        with patch.object(opportunity_service, '_clear_opportunity_caches', return_value=None), \
             patch.object(opportunity_service, '_initiate_validation_workflow', return_value=None):
            
            opportunity = await opportunity_service.create_opportunity(
                mock_db_session, 
                sample_opportunity_create,
                discovered_by_agent="monitoring_agent_1"
            )
            
            assert opportunity.title == sample_opportunity_create.title
            assert opportunity.description == sample_opportunity_create.description
            assert opportunity.status == OpportunityStatus.DISCOVERED
            assert opportunity.discovery_method == "monitoring_agent_1"
            
            # Verify JSON fields are properly serialized
            assert opportunity.ai_solution_types is not None
            assert opportunity.target_industries is not None
            assert opportunity.tags is not None
    
    @pytest.mark.asyncio
    async def test_get_opportunity_by_id_with_cache(self, opportunity_service, mock_db_session):
        """Test getting opportunity by ID with caching."""
        opportunity_id = "test-opportunity-id"
        cached_data = {
            "id": opportunity_id,
            "title": "Cached Opportunity",
            "description": "Cached description",
            "status": "validated",
            "validation_score": 8.5,
            "ai_feasibility_score": 7.2
        }
        
        with patch('shared.services.opportunity_service.cache_manager') as mock_cache:
            mock_cache.get.return_value = cached_data
            
            opportunity = await opportunity_service.get_opportunity_by_id(
                mock_db_session, opportunity_id, include_relationships=False
            )
            
            # Should return cached data without hitting database
            assert opportunity.title == "Cached Opportunity"
            mock_db_session.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_opportunity_by_id_from_database(self, opportunity_service, mock_db_session):
        """Test getting opportunity by ID from database."""
        opportunity_id = "test-opportunity-id"
        
        # Mock database result
        mock_opportunity = Opportunity(
            id=opportunity_id,
            title="Database Opportunity",
            description="Database description",
            status=OpportunityStatus.VALIDATED
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_opportunity
        mock_db_session.execute.return_value = mock_result
        
        with patch('shared.services.opportunity_service.cache_manager') as mock_cache:
            mock_cache.get.return_value = None  # No cache hit
            mock_cache.set = AsyncMock()
            
            opportunity = await opportunity_service.get_opportunity_by_id(
                mock_db_session, opportunity_id, include_relationships=False
            )
            
            assert opportunity.title == "Database Opportunity"
            mock_db_session.execute.assert_called_once()
            mock_cache.set.assert_called_once()  # Should cache the result
    
    @pytest.mark.asyncio
    async def test_update_opportunity(self, opportunity_service, mock_db_session):
        """Test opportunity update."""
        opportunity_id = "test-opportunity-id"
        
        # Mock existing opportunity
        existing_opportunity = Opportunity(
            id=opportunity_id,
            title="Original Title",
            description="Original description",
            status=OpportunityStatus.DISCOVERED
        )
        
        update_data = OpportunityUpdate(
            title="Updated Title",
            summary="Updated summary",
            status=OpportunityStatus.VALIDATING,
            ai_solution_types=["nlp", "updated_ml"],
            tags=["updated", "tags"]
        )
        
        with patch.object(opportunity_service, 'get_opportunity_by_id', return_value=existing_opportunity), \
             patch.object(opportunity_service, '_clear_opportunity_caches', return_value=None):
            
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()
            
            updated_opportunity = await opportunity_service.update_opportunity(
                mock_db_session, opportunity_id, update_data
            )
            
            assert updated_opportunity.title == "Updated Title"
            assert updated_opportunity.summary == "Updated summary"
            assert updated_opportunity.status == OpportunityStatus.VALIDATING
            mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_opportunities_with_filters(self, opportunity_service, mock_db_session):
        """Test opportunity search with various filters."""
        search_request = OpportunitySearchRequest(
            query="AI automation",
            min_validation_score=6.0,
            max_validation_score=10.0,
            status=[OpportunityStatus.VALIDATED],
            implementation_complexity=["medium", "high"],
            geographic_scope="global",
            page=1,
            page_size=10
        )
        
        # Mock search results
        mock_opportunities = [
            Opportunity(
                id="opp1",
                title="AI Automation Solution 1",
                description="First automation solution",
                validation_score=8.5,
                status=OpportunityStatus.VALIDATED
            ),
            Opportunity(
                id="opp2",
                title="AI Automation Solution 2", 
                description="Second automation solution",
                validation_score=7.2,
                status=OpportunityStatus.VALIDATED
            )
        ]
        
        # Mock database execution
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_opportunities
        
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 2
        
        mock_db_session.execute.side_effect = [mock_count_result, mock_result]
        
        opportunities, total_count = await opportunity_service.search_opportunities(
            mock_db_session, search_request, user_id="test-user"
        )
        
        assert len(opportunities) == 2
        assert total_count == 2
        assert opportunities[0].title == "AI Automation Solution 1"
        assert opportunities[1].validation_score == 7.2
    
    @pytest.mark.asyncio
    async def test_get_personalized_recommendations(self, opportunity_service, mock_db_session):
        """Test personalized opportunity recommendations."""
        from shared.schemas.opportunity import OpportunityRecommendationRequest
        
        request = OpportunityRecommendationRequest(
            user_id="test-user-id",
            limit=5,
            ai_solution_types=["nlp", "ml"],
            industries=["healthcare", "finance"]
        )
        
        # Mock user service
        mock_user = Mock()
        mock_user.id = "test-user-id"
        
        # Mock recommended opportunities
        mock_recommendations = [
            Opportunity(
                id="rec1",
                title="Healthcare AI Solution",
                description="AI for healthcare automation",
                validation_score=8.5,
                ai_feasibility_score=7.8,
                status=OpportunityStatus.VALIDATED
            ),
            Opportunity(
                id="rec2",
                title="Finance ML Platform",
                description="ML platform for financial analysis",
                validation_score=8.2,
                ai_feasibility_score=8.1,
                status=OpportunityStatus.VALIDATED
            )
        ]
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_recommendations
        mock_db_session.execute.return_value = mock_result
        
        with patch('shared.services.opportunity_service.user_service') as mock_user_service, \
             patch('shared.services.opportunity_service.cache_manager') as mock_cache:
            
            mock_user_service.get_user_by_id.return_value = mock_user
            mock_cache.get.return_value = None  # No cache hit
            mock_cache.set = AsyncMock()
            
            recommendations = await opportunity_service.get_personalized_recommendations(
                mock_db_session, request
            )
            
            assert len(recommendations) == 2
            assert recommendations[0].title == "Healthcare AI Solution"
            assert recommendations[1].validation_score == 8.2
            mock_cache.set.assert_called_once()  # Should cache recommendations
    
    @pytest.mark.asyncio
    async def test_update_validation_scores(self, opportunity_service, mock_db_session):
        """Test validation score updates based on community feedback."""
        opportunity_id = "test-opportunity-id"
        
        # Mock opportunity with validations
        from shared.models.validation import ValidationResult
        
        mock_validations = [
            ValidationResult(
                id="val1",
                validator_id="validator1",
                score=8.5,
                validation_type="market_demand"
            ),
            ValidationResult(
                id="val2",
                validator_id="validator2", 
                score=7.8,
                validation_type="technical_feasibility"
            ),
            ValidationResult(
                id="val3",
                validator_id="validator3",
                score=8.2,
                validation_type="business_viability"
            )
        ]
        
        mock_opportunity = Opportunity(
            id=opportunity_id,
            title="Test Opportunity",
            description="Test description",
            status=OpportunityStatus.VALIDATING,
            validations=mock_validations
        )
        
        with patch.object(opportunity_service, 'get_opportunity_by_id', return_value=mock_opportunity), \
             patch('shared.services.opportunity_service.user_service') as mock_user_service, \
             patch.object(opportunity_service, '_clear_opportunity_caches', return_value=None):
            
            # Mock user influence weights
            mock_user_service.get_user_influence_weight.side_effect = [1.2, 1.0, 1.1]
            
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()
            
            updated_opportunity = await opportunity_service.update_validation_scores(
                mock_db_session, opportunity_id
            )
            
            assert updated_opportunity is not None
            assert updated_opportunity.validation_score > 0
            assert updated_opportunity.confidence_rating >= 0
            # Should be validated due to high scores and multiple validations
            assert updated_opportunity.status == OpportunityStatus.VALIDATED
    
    @pytest.mark.asyncio
    async def test_get_opportunity_analytics(self, opportunity_service, mock_db_session):
        """Test opportunity analytics generation."""
        # Mock database queries for analytics
        mock_total_count = AsyncMock()
        mock_total_count.scalar.return_value = 150
        
        mock_status_stats = [
            Mock(status=OpportunityStatus.DISCOVERED, count=50),
            Mock(status=OpportunityStatus.VALIDATING, count=40),
            Mock(status=OpportunityStatus.VALIDATED, count=45),
            Mock(status=OpportunityStatus.REJECTED, count=15)
        ]
        
        mock_avg_score = AsyncMock()
        mock_avg_score.scalar.return_value = 6.8
        
        mock_trending = AsyncMock()
        mock_trending.scalars.return_value.all.return_value = [
            Opportunity(id="trend1", title="Trending Opp 1", validation_score=9.2),
            Opportunity(id="trend2", title="Trending Opp 2", validation_score=8.9)
        ]
        
        # Mock database execution sequence
        mock_db_session.execute.side_effect = [
            mock_total_count,
            mock_status_stats,
            mock_avg_score,
            mock_trending
        ]
        
        analytics = await opportunity_service.get_opportunity_analytics(
            mock_db_session, timeframe_days=30
        )
        
        assert analytics["total_opportunities"] == 150
        assert analytics["average_validation_score"] == 6.8
        assert analytics["trending_opportunities_count"] == 2
        assert analytics["timeframe_days"] == 30
        assert "opportunities_by_status" in analytics
        assert "generated_at" in analytics
    
    @pytest.mark.asyncio
    async def test_initiate_validation_workflow(self, opportunity_service, mock_db_session):
        """Test validation workflow initiation."""
        opportunity = Opportunity(
            id="test-opp-id",
            title="Test Opportunity",
            description="Test description",
            ai_solution_types='["nlp", "ml"]',
            target_industries='["healthcare", "finance"]'
        )
        
        # Mock relevant experts
        mock_experts = [
            Mock(id="expert1", username="nlp_expert"),
            Mock(id="expert2", username="healthcare_expert")
        ]
        
        with patch('shared.services.opportunity_service.user_service') as mock_user_service:
            mock_user_service.get_experts_for_opportunity.return_value = mock_experts
            
            await opportunity_service._initiate_validation_workflow(mock_db_session, opportunity)
            
            # Should have called user service to find relevant experts
            mock_user_service.get_experts_for_opportunity.assert_called_once_with(
                mock_db_session, ["nlp", "ml"], ["healthcare", "finance"]
            )