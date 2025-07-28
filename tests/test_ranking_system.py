"""
Tests for the opportunity ranking system implementation.
Tests ranking algorithms, filtering capabilities, and personalization features.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from shared.services.ranking_system import (
    OpportunityRankingSystem,
    FilterCriteria,
    RankingConfig,
    UserPreferences,
    RankingCriteria,
    SortOrder,
    RankedOpportunity,
    RankingResult
)
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.user import User
from shared.models.validation import ValidationResult


class TestFilterCriteria:
    """Test cases for FilterCriteria."""
    
    def test_filter_criteria_creation(self):
        """Test FilterCriteria creation and serialization."""
        criteria = FilterCriteria(
            ai_solution_types=["machine_learning", "nlp"],
            target_industries=["healthcare", "finance"],
            min_validation_score=7.0,
            max_validation_score=10.0,
            search_query="AI automation"
        )
        
        assert criteria.ai_solution_types == ["machine_learning", "nlp"]
        assert criteria.target_industries == ["healthcare", "finance"]
        assert criteria.min_validation_score == 7.0
        assert criteria.search_query == "AI automation"
        
        # Test serialization
        criteria_dict = criteria.to_dict()
        assert "ai_solution_types" in criteria_dict
        assert "target_industries" in criteria_dict
        assert "min_validation_score" in criteria_dict
        assert "search_query" in criteria_dict
    
    def test_filter_criteria_empty(self):
        """Test empty FilterCriteria."""
        criteria = FilterCriteria()
        criteria_dict = criteria.to_dict()
        
        # Should only contain non-None values
        assert len(criteria_dict) == 0
    
    def test_filter_criteria_with_dates(self):
        """Test FilterCriteria with datetime fields."""
        now = datetime.utcnow()
        criteria = FilterCriteria(
            created_after=now - timedelta(days=30),
            created_before=now
        )
        
        criteria_dict = criteria.to_dict()
        assert "created_after" in criteria_dict
        assert "created_before" in criteria_dict
        # Dates should be serialized as ISO strings
        assert isinstance(criteria_dict["created_after"], str)


class TestRankingConfig:
    """Test cases for RankingConfig."""
    
    def test_ranking_config_defaults(self):
        """Test RankingConfig default values."""
        config = RankingConfig()
        
        assert config.primary_criteria == RankingCriteria.OVERALL_SCORE
        assert config.primary_weight == 0.4
        assert config.sort_order == SortOrder.DESC
        assert config.enable_personalization is True
        assert config.personalization_weight == 0.3
        
        # Should have default secondary criteria
        assert config.secondary_criteria is not None
        assert len(config.secondary_criteria) > 0
    
    def test_ranking_config_custom(self):
        """Test RankingConfig with custom values."""
        custom_secondary = {
            RankingCriteria.VALIDATION_SCORE: 0.5,
            RankingCriteria.AI_FEASIBILITY: 0.3
        }
        
        config = RankingConfig(
            primary_criteria=RankingCriteria.VALIDATION_SCORE,
            primary_weight=0.6,
            secondary_criteria=custom_secondary,
            sort_order=SortOrder.ASC,
            enable_personalization=False
        )
        
        assert config.primary_criteria == RankingCriteria.VALIDATION_SCORE
        assert config.primary_weight == 0.6
        assert config.secondary_criteria == custom_secondary
        assert config.sort_order == SortOrder.ASC
        assert config.enable_personalization is False


class TestUserPreferences:
    """Test cases for UserPreferences."""
    
    def test_user_preferences_creation(self):
        """Test UserPreferences creation with defaults."""
        prefs = UserPreferences(user_id="user123")
        
        assert prefs.user_id == "user123"
        assert prefs.preferred_ai_types == []
        assert prefs.preferred_industries == []
        assert prefs.viewed_opportunities == []
        assert prefs.ai_type_weight == 0.3
        assert prefs.interaction_decay_days == 90
    
    def test_user_preferences_with_data(self):
        """Test UserPreferences with actual preference data."""
        prefs = UserPreferences(
            user_id="user123",
            preferred_ai_types=["machine_learning", "nlp"],
            preferred_industries=["healthcare", "fintech"],
            preferred_complexity_levels=["low", "medium"],
            bookmarked_opportunities=["opp1", "opp2"],
            ai_type_weight=0.4,
            industry_weight=0.4
        )
        
        assert prefs.preferred_ai_types == ["machine_learning", "nlp"]
        assert prefs.preferred_industries == ["healthcare", "fintech"]
        assert prefs.bookmarked_opportunities == ["opp1", "opp2"]
        assert prefs.ai_type_weight == 0.4
        assert prefs.industry_weight == 0.4


class TestOpportunityRankingSystem:
    """Test cases for OpportunityRankingSystem."""
    
    @pytest.fixture
    def ranking_system(self):
        """Create OpportunityRankingSystem instance for testing."""
        config = {
            "cache_ttl": 60,
            "enable_caching": False,  # Disable caching for tests
            "max_opportunities": 100
        }
        return OpportunityRankingSystem(config)
    
    @pytest.fixture
    def sample_opportunities(self):
        """Create sample opportunities for testing."""
        opportunities = []
        
        # High-scoring opportunity
        opp1 = Opportunity(
            id="opp1",
            title="AI-Powered Fraud Detection",
            description="Machine learning solution for real-time fraud detection",
            status=OpportunityStatus.VALIDATED,
            validation_score=9.2,
            ai_feasibility_score=8.8,
            confidence_rating=0.9,
            ai_solution_types='["machine_learning", "predictive_analytics"]',
            target_industries='["fintech", "ecommerce"]',
            implementation_complexity="medium",
            created_at=datetime.utcnow() - timedelta(days=5),
            updated_at=datetime.utcnow() - timedelta(days=1)
        )
        opportunities.append(opp1)
        
        # Medium-scoring opportunity
        opp2 = Opportunity(
            id="opp2",
            title="NLP Document Processing",
            description="Natural language processing for document automation",
            status=OpportunityStatus.VALIDATING,
            validation_score=7.5,
            ai_feasibility_score=7.2,
            confidence_rating=0.75,
            ai_solution_types='["natural_language_processing", "automation"]',
            target_industries='["legal", "healthcare"]',
            implementation_complexity="high",
            created_at=datetime.utcnow() - timedelta(days=15),
            updated_at=datetime.utcnow() - timedelta(days=3)
        )
        opportunities.append(opp2)
        
        # Lower-scoring opportunity
        opp3 = Opportunity(
            id="opp3",
            title="Basic Task Automation",
            description="Simple automation for routine tasks",
            status=OpportunityStatus.DISCOVERED,
            validation_score=5.0,
            ai_feasibility_score=6.0,
            confidence_rating=0.6,
            ai_solution_types='["automation"]',
            target_industries='["general"]',
            implementation_complexity="low",
            created_at=datetime.utcnow() - timedelta(days=30),
            updated_at=datetime.utcnow() - timedelta(days=10)
        )
        opportunities.append(opp3)
        
        return opportunities
    
    @pytest.fixture
    def sample_user_preferences(self):
        """Create sample user preferences."""
        return UserPreferences(
            user_id="user123",
            preferred_ai_types=["machine_learning", "predictive_analytics"],
            preferred_industries=["fintech", "healthcare"],
            preferred_complexity_levels=["low", "medium"],
            bookmarked_opportunities=["opp1"],
            ai_type_weight=0.4,
            industry_weight=0.3
        )
    
    @pytest.mark.asyncio
    async def test_get_opportunity_metric(self, ranking_system, sample_opportunities):
        """Test getting specific metrics from opportunities."""
        opp = sample_opportunities[0]  # High-scoring opportunity
        
        # Test validation score
        validation_score = ranking_system._get_opportunity_metric(opp, RankingCriteria.VALIDATION_SCORE)
        assert validation_score == 9.2
        
        # Test AI feasibility score
        ai_score = ranking_system._get_opportunity_metric(opp, RankingCriteria.AI_FEASIBILITY)
        assert ai_score == 8.8
        
        # Test implementation complexity (should convert to score)
        complexity_score = ranking_system._get_opportunity_metric(opp, RankingCriteria.IMPLEMENTATION_COMPLEXITY)
        assert complexity_score == 50.0  # "medium" -> 50.0
        
        # Test created date (more recent = higher score)
        date_score = ranking_system._get_opportunity_metric(opp, RankingCriteria.CREATED_DATE)
        assert date_score > 90  # Should be high for recent opportunity
    
    @pytest.mark.asyncio
    async def test_calculate_base_score(self, ranking_system, sample_opportunities):
        """Test base score calculation."""
        opp = sample_opportunities[0]  # High-scoring opportunity
        config = RankingConfig()
        
        base_score = await ranking_system._calculate_base_score(opp, config)
        
        assert 0 <= base_score <= 100
        assert base_score > 70  # Should be high for high-scoring opportunity
    
    @pytest.mark.asyncio
    async def test_calculate_personalization_score(self, ranking_system, sample_opportunities, sample_user_preferences):
        """Test personalization score calculation."""
        opp = sample_opportunities[0]  # Has matching AI types and industries
        
        personalization_score = await ranking_system._calculate_personalization_score(
            opp, sample_user_preferences
        )
        
        assert 0 <= personalization_score <= 100
        assert personalization_score > 50  # Should be high due to matching preferences and bookmark
    
    def test_calculate_freshness_score(self, ranking_system, sample_opportunities):
        """Test freshness score calculation."""
        recent_opp = sample_opportunities[0]  # Created 5 days ago
        old_opp = sample_opportunities[2]     # Created 30 days ago
        
        recent_score = ranking_system._calculate_freshness_score(recent_opp)
        old_score = ranking_system._calculate_freshness_score(old_opp)
        
        assert 0 <= recent_score <= 100
        assert 0 <= old_score <= 100
        assert recent_score > old_score  # Recent should score higher
    
    @pytest.mark.asyncio
    async def test_calculate_trending_score(self, ranking_system):
        """Test trending score calculation."""
        # Create opportunity with recent validations
        opp = Opportunity(
            id="trending_opp",
            title="Trending Opportunity",
            description="Test opportunity",
            validations=[]
        )
        
        # Add recent validations
        recent_validation = ValidationResult(
            opportunity_id="trending_opp",
            validator_id="validator1",
            score=8.5,
            validated_at=datetime.utcnow() - timedelta(days=2)
        )
        opp.validations = [recent_validation]
        
        trending_score = await ranking_system._calculate_trending_score(opp)
        
        assert 0 <= trending_score <= 100
        assert trending_score > 0  # Should have some trending score
    
    @pytest.mark.asyncio
    async def test_calculate_ranking_scores(self, ranking_system, sample_opportunities, sample_user_preferences):
        """Test ranking score calculation for multiple opportunities."""
        config = RankingConfig(enable_personalization=True)
        
        ranked_opportunities = await ranking_system._calculate_ranking_scores(
            sample_opportunities, config, sample_user_preferences
        )
        
        assert len(ranked_opportunities) == 3
        
        for ranked_opp in ranked_opportunities:
            assert isinstance(ranked_opp, RankedOpportunity)
            assert 0 <= ranked_opp.rank_score <= 100
            assert 0 <= ranked_opp.base_score <= 100
            assert 0 <= ranked_opp.personalization_score <= 100
            assert 0 <= ranked_opp.freshness_score <= 100
            assert 0 <= ranked_opp.trending_score <= 100
            assert isinstance(ranked_opp.ranking_factors, dict)
        
        # First opportunity should have highest personalization score (bookmarked + matching prefs)
        first_opp = next(r for r in ranked_opportunities if r.opportunity.id == "opp1")
        assert first_opp.personalization_score > 0
    
    @pytest.mark.asyncio
    async def test_get_filtered_opportunities_basic(self, ranking_system):
        """Test basic opportunity filtering."""
        # Mock database session and query results
        mock_db = AsyncMock()
        
        # Mock opportunities
        mock_opportunities = [
            Opportunity(id="opp1", title="Test 1", status=OpportunityStatus.VALIDATED),
            Opportunity(id="opp2", title="Test 2", status=OpportunityStatus.VALIDATING)
        ]
        
        # Mock query execution
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_opportunities
        mock_db.execute.return_value = mock_result
        
        # Mock count query
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 2
        
        # Set up side effects for different queries
        async def execute_side_effect(query):
            # Check if it's a count query by looking for func.count
            query_str = str(query)
            if "count" in query_str.lower():
                return mock_count_result
            else:
                return mock_result
        
        mock_db.execute.side_effect = execute_side_effect
        
        # Test filtering
        filter_criteria = FilterCriteria(
            status=[OpportunityStatus.VALIDATED, OpportunityStatus.VALIDATING]
        )
        
        opportunities, total_count = await ranking_system._get_filtered_opportunities(
            mock_db, filter_criteria, page=1, page_size=10
        )
        
        assert len(opportunities) == 2
        assert total_count == 2
        assert all(isinstance(opp, Opportunity) for opp in opportunities)
    
    def test_generate_cache_key(self, ranking_system):
        """Test cache key generation."""
        filter_criteria = FilterCriteria(ai_solution_types=["ml"])
        ranking_config = RankingConfig()
        user_preferences = UserPreferences(user_id="user123")
        
        cache_key = ranking_system._generate_cache_key(
            filter_criteria, ranking_config, user_preferences, 1, 20
        )
        
        assert isinstance(cache_key, str)
        assert "ranking" in cache_key
        assert "page_1" in cache_key
        assert "size_20" in cache_key
        
        # Different inputs should generate different keys
        different_filter = FilterCriteria(ai_solution_types=["nlp"])
        different_key = ranking_system._generate_cache_key(
            different_filter, ranking_config, user_preferences, 1, 20
        )
        
        assert cache_key != different_key
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_default(self, ranking_system):
        """Test getting default user preferences."""
        mock_db = AsyncMock()
        
        # Mock user not found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Mock cache miss
        with patch('shared.services.ranking_system.cache_manager') as mock_cache:
            mock_cache.get.return_value = None
            
            preferences = await ranking_system.get_user_preferences(mock_db, "unknown_user")
            
            assert preferences.user_id == "unknown_user"
            assert preferences.preferred_ai_types == []
            assert preferences.preferred_industries == []
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_cached(self, ranking_system):
        """Test getting cached user preferences."""
        mock_db = AsyncMock()
        
        cached_prefs = {
            "user_id": "user123",
            "preferred_ai_types": ["ml", "nlp"],
            "preferred_industries": ["tech"],
            "preferred_complexity_levels": [],
            "preferred_market_sizes": [],
            "viewed_opportunities": [],
            "bookmarked_opportunities": [],
            "validated_opportunities": [],
            "ai_type_weight": 0.3,
            "industry_weight": 0.3,
            "complexity_weight": 0.2,
            "market_size_weight": 0.2,
            "interaction_decay_days": 90,
            "min_interactions_for_learning": 5
        }
        
        with patch('shared.services.ranking_system.cache_manager') as mock_cache:
            mock_cache.get.return_value = cached_prefs
            
            preferences = await ranking_system.get_user_preferences(mock_db, "user123")
            
            assert preferences.user_id == "user123"
            assert preferences.preferred_ai_types == ["ml", "nlp"]
            assert preferences.preferred_industries == ["tech"]
    
    @pytest.mark.asyncio
    async def test_update_user_preferences(self, ranking_system):
        """Test updating user preferences."""
        mock_db = AsyncMock()
        
        preferences = UserPreferences(
            user_id="user123",
            preferred_ai_types=["ml"],
            preferred_industries=["healthcare"]
        )
        
        with patch('shared.services.ranking_system.cache_manager') as mock_cache:
            mock_cache.set = AsyncMock()
            
            await ranking_system.update_user_preferences(mock_db, "user123", preferences)
            
            # Should update cache
            mock_cache.set.assert_called_once()
            call_args = mock_cache.set.call_args
            assert call_args[0][0] == "user_preferences:user123"  # cache key
            assert call_args[0][1]["user_id"] == "user123"  # cached data
    
    def test_ranking_system_initialization(self):
        """Test OpportunityRankingSystem initialization."""
        custom_config = {
            "cache_ttl": 600,
            "enable_caching": True,
            "max_opportunities": 500,
            "batch_size": 50
        }
        
        system = OpportunityRankingSystem(custom_config)
        
        assert system.cache_ttl == 600
        assert system.enable_caching is True
        assert system.max_opportunities_per_query == 500
        assert system.batch_size == 50
        assert isinstance(system.default_ranking_config, RankingConfig)


class TestRankingIntegration:
    """Integration tests for the ranking system."""
    
    @pytest.fixture
    def ranking_system(self):
        """Create ranking system with test configuration."""
        return OpportunityRankingSystem({"enable_caching": False})
    
    @pytest.mark.asyncio
    async def test_ranking_with_different_configs(self, ranking_system):
        """Test ranking with different configurations."""
        mock_db = AsyncMock()
        
        # Mock opportunities
        opportunities = [
            Opportunity(
                id="opp1",
                title="High Validation",
                validation_score=9.0,
                ai_feasibility_score=7.0,
                status=OpportunityStatus.VALIDATED,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Opportunity(
                id="opp2", 
                title="High AI Feasibility",
                validation_score=6.0,
                ai_feasibility_score=9.5,
                status=OpportunityStatus.VALIDATED,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        # Mock database responses
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = opportunities
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 2
        
        async def execute_side_effect(query):
            query_str = str(query)
            if "count" in query_str.lower():
                return mock_count_result
            else:
                return mock_result
        
        mock_db.execute.side_effect = execute_side_effect
        
        # Test ranking prioritizing validation score
        validation_config = RankingConfig(
            primary_criteria=RankingCriteria.VALIDATION_SCORE,
            primary_weight=0.8
        )
        
        with patch('shared.services.ranking_system.cache_manager') as mock_cache:
            mock_cache.get.return_value = None
            mock_cache.set = AsyncMock()
            
            result = await ranking_system.rank_opportunities(
                db=mock_db,
                ranking_config=validation_config,
                page_size=10
            )
            
            assert len(result.ranked_opportunities) == 2
            assert result.total_count == 2
            
            # First opportunity should be the one with higher validation score
            first_opp = result.ranked_opportunities[0]
            assert first_opp.opportunity.id == "opp1"  # Higher validation score
            assert first_opp.rank_position == 1
        
        # Test ranking prioritizing AI feasibility
        ai_config = RankingConfig(
            primary_criteria=RankingCriteria.AI_FEASIBILITY,
            primary_weight=0.8
        )
        
        with patch('shared.services.ranking_system.cache_manager') as mock_cache:
            mock_cache.get.return_value = None
            mock_cache.set = AsyncMock()
            
            result = await ranking_system.rank_opportunities(
                db=mock_db,
                ranking_config=ai_config,
                page_size=10
            )
            
            # First opportunity should be the one with higher AI feasibility
            first_opp = result.ranked_opportunities[0]
            assert first_opp.opportunity.id == "opp2"  # Higher AI feasibility score
    
    @pytest.mark.asyncio
    async def test_personalized_ranking(self, ranking_system):
        """Test personalized ranking with user preferences."""
        mock_db = AsyncMock()
        
        # Mock opportunities with different characteristics
        opportunities = [
            Opportunity(
                id="ml_opp",
                title="ML Opportunity",
                validation_score=8.0,
                ai_feasibility_score=8.0,
                ai_solution_types='["machine_learning"]',
                target_industries='["healthcare"]',
                status=OpportunityStatus.VALIDATED,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Opportunity(
                id="nlp_opp",
                title="NLP Opportunity", 
                validation_score=8.0,
                ai_feasibility_score=8.0,
                ai_solution_types='["natural_language_processing"]',
                target_industries='["finance"]',
                status=OpportunityStatus.VALIDATED,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        # Mock database responses
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = opportunities
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 2
        
        async def execute_side_effect(query):
            query_str = str(query)
            if "count" in query_str.lower():
                return mock_count_result
            else:
                return mock_result
        
        mock_db.execute.side_effect = execute_side_effect
        
        # User preferences favoring ML and healthcare
        user_preferences = UserPreferences(
            user_id="user123",
            preferred_ai_types=["machine_learning"],
            preferred_industries=["healthcare"],
            ai_type_weight=0.5,
            industry_weight=0.5
        )
        
        config = RankingConfig(
            enable_personalization=True,
            personalization_weight=0.6
        )
        
        with patch('shared.services.ranking_system.cache_manager') as mock_cache:
            mock_cache.get.return_value = None
            mock_cache.set = AsyncMock()
            
            result = await ranking_system.rank_opportunities(
                db=mock_db,
                ranking_config=config,
                user_preferences=user_preferences,
                page_size=10
            )
            
            assert len(result.ranked_opportunities) == 2
            
            # ML opportunity should rank higher due to personalization
            first_opp = result.ranked_opportunities[0]
            assert first_opp.opportunity.id == "ml_opp"
            assert first_opp.personalization_score > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])