"""
Tests for advanced scoring algorithms implementation.
Tests market validation scoring and competitive analysis automation.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from shared.services.scoring_algorithms import (
    MarketValidationScorer,
    CompetitiveAnalysisEngine,
    AdvancedScoringEngine,
    MarketValidationScore,
    CompetitiveAnalysis,
    AdvancedOpportunityScore
)


class TestMarketValidationScorer:
    """Test cases for MarketValidationScorer."""
    
    @pytest.fixture
    def scorer(self):
        """Create MarketValidationScorer instance for testing."""
        config = {
            "validation_weights": {
                "signal_strength": 0.25,
                "pain_intensity": 0.20,
                "market_demand": 0.20,
                "engagement_quality": 0.15,
                "source_credibility": 0.10,
                "temporal_relevance": 0.10
            }
        }
        return MarketValidationScorer(config)
    
    @pytest.fixture
    def sample_signals(self):
        """Sample market signals for testing."""
        return [
            {
                "signal_id": "signal_1",
                "content": "I'm struggling with critical data processing issues that are blocking our workflow",
                "signal_type": "pain_point",
                "source": "github",
                "engagement_metrics": {"total_engagement": 45, "upvotes": 30, "comments": 15},
                "ai_relevance_score": 85.0,
                "confidence": 0.9,
                "sentiment_score": -0.8,
                "extracted_at": datetime.utcnow().isoformat()
            },
            {
                "signal_id": "signal_2",
                "content": "Looking for automated solution to handle customer data processing needs",
                "signal_type": "feature_request",
                "source": "stackoverflow",
                "engagement_metrics": {"total_engagement": 32, "upvotes": 20, "comments": 12},
                "ai_relevance_score": 90.0,
                "confidence": 0.85,
                "sentiment_score": 0.2,
                "extracted_at": (datetime.utcnow() - timedelta(days=5)).isoformat()
            },
            {
                "signal_id": "signal_3",
                "content": "Users need better tools for data analysis and reporting automation",
                "signal_type": "opportunity",
                "source": "reddit",
                "engagement_metrics": {"total_engagement": 28, "upvotes": 18, "comments": 10},
                "ai_relevance_score": 75.0,
                "confidence": 0.8,
                "sentiment_score": 0.1,
                "extracted_at": (datetime.utcnow() - timedelta(days=15)).isoformat()
            }
        ]
    
    @pytest.mark.asyncio
    async def test_market_validation_scoring(self, scorer, sample_signals):
        """Test comprehensive market validation scoring."""
        result = await scorer.calculate_market_validation_score(sample_signals)
        
        assert isinstance(result, MarketValidationScore)
        assert 0 <= result.overall_score <= 100
        assert 0 <= result.signal_strength <= 100
        assert 0 <= result.pain_intensity <= 100
        assert 0 <= result.market_demand <= 100
        assert 0 <= result.engagement_quality <= 100
        assert 0 <= result.source_credibility <= 100
        assert 0 <= result.temporal_relevance <= 100
        assert 0 <= result.confidence_level <= 1
        
        # Should have high pain intensity due to "critical" and "blocking" keywords
        assert result.pain_intensity > 50, f"Expected high pain intensity, got {result.pain_intensity}"
        
        # Should have good source credibility (github, stackoverflow)
        assert result.source_credibility > 60, f"Expected good source credibility, got {result.source_credibility}"
        
        # Should have contributing factors
        assert "signal_count" in result.contributing_factors
        assert result.contributing_factors["signal_count"] == 3
    
    @pytest.mark.asyncio
    async def test_empty_signals_handling(self, scorer):
        """Test handling of empty signal list."""
        result = await scorer.calculate_market_validation_score([])
        
        assert result.overall_score == 0.0
        assert result.confidence_level == 0.0
        assert result.contributing_factors == {}
    
    @pytest.mark.asyncio
    async def test_pain_intensity_calculation(self, scorer):
        """Test pain intensity calculation with different pain levels."""
        high_pain_signals = [
            {
                "content": "This critical issue is blocking our entire workflow and causing major problems",
                "signal_type": "pain_point",
                "source": "github",
                "engagement_metrics": {"total_engagement": 50}
            }
        ]
        
        low_pain_signals = [
            {
                "content": "It would be nice to have some optimization improvements for better performance",
                "signal_type": "feature_request", 
                "source": "reddit",
                "engagement_metrics": {"total_engagement": 10}
            }
        ]
        
        high_pain_result = await scorer.calculate_market_validation_score(high_pain_signals)
        low_pain_result = await scorer.calculate_market_validation_score(low_pain_signals)
        
        assert high_pain_result.pain_intensity > low_pain_result.pain_intensity
        assert high_pain_result.pain_intensity > 50  # Should be high for critical issues
    
    @pytest.mark.asyncio
    async def test_temporal_relevance_calculation(self, scorer):
        """Test temporal relevance calculation."""
        recent_signals = [
            {
                "content": "Recent issue with data processing",
                "extracted_at": datetime.utcnow().isoformat(),
                "engagement_metrics": {"total_engagement": 20}
            }
        ]
        
        old_signals = [
            {
                "content": "Old issue with data processing",
                "extracted_at": (datetime.utcnow() - timedelta(days=200)).isoformat(),
                "engagement_metrics": {"total_engagement": 20}
            }
        ]
        
        recent_result = await scorer.calculate_market_validation_score(recent_signals)
        old_result = await scorer.calculate_market_validation_score(old_signals)
        
        assert recent_result.temporal_relevance > old_result.temporal_relevance
        assert recent_result.temporal_relevance > 80  # Should be high for recent signals
    
    @pytest.mark.asyncio
    async def test_source_credibility_scoring(self, scorer):
        """Test source credibility scoring."""
        high_credibility_signals = [
            {"content": "Test", "source": "github", "engagement_metrics": {"total_engagement": 10}},
            {"content": "Test", "source": "stackoverflow", "engagement_metrics": {"total_engagement": 10}}
        ]
        
        low_credibility_signals = [
            {"content": "Test", "source": "unknown", "engagement_metrics": {"total_engagement": 10}},
            {"content": "Test", "source": "random_blog", "engagement_metrics": {"total_engagement": 10}}
        ]
        
        high_cred_result = await scorer.calculate_market_validation_score(high_credibility_signals)
        low_cred_result = await scorer.calculate_market_validation_score(low_credibility_signals)
        
        assert high_cred_result.source_credibility > low_cred_result.source_credibility


class TestCompetitiveAnalysisEngine:
    """Test cases for CompetitiveAnalysisEngine."""
    
    @pytest.fixture
    def analyzer(self):
        """Create CompetitiveAnalysisEngine instance for testing."""
        return CompetitiveAnalysisEngine()
    
    @pytest.fixture
    def competitive_signals(self):
        """Sample signals with competitive information."""
        return [
            {
                "content": "Looking for alternative to Salesforce that's more affordable and easier to use",
                "signal_type": "pain_point",
                "source": "reddit",
                "engagement_metrics": {"total_engagement": 35}
            },
            {
                "content": "The market is saturated with CRM solutions but none address our specific needs",
                "signal_type": "opportunity",
                "source": "github",
                "engagement_metrics": {"total_engagement": 28}
            },
            {
                "content": "Existing tools like HubSpot and Pipedrive don't have good AI automation features",
                "signal_type": "feature_request",
                "source": "stackoverflow",
                "engagement_metrics": {"total_engagement": 42}
            },
            {
                "content": "No good solution exists for small business CRM with AI-powered lead scoring",
                "signal_type": "opportunity",
                "source": "hackernews",
                "engagement_metrics": {"total_engagement": 55}
            }
        ]
    
    @pytest.mark.asyncio
    async def test_competitive_analysis(self, analyzer, competitive_signals):
        """Test comprehensive competitive analysis."""
        result = await analyzer.analyze_competition(competitive_signals)
        
        assert isinstance(result, CompetitiveAnalysis)
        assert result.competition_level in ["low", "medium", "high"]
        assert 0 <= result.competition_score <= 100
        assert 0 <= result.market_saturation <= 100
        assert 0 <= result.confidence_level <= 1
        assert result.market_positioning in ["blue_ocean", "red_ocean", "niche", "unknown"]
        
        # Should identify competitors from the signals
        assert len(result.identified_competitors) > 0
        competitor_names = [c["name"] for c in result.identified_competitors]
        assert any("salesforce" in name.lower() for name in competitor_names)
    
    @pytest.mark.asyncio
    async def test_competitor_identification(self, analyzer, competitive_signals):
        """Test competitor identification from signals."""
        result = await analyzer.analyze_competition(competitive_signals)
        
        # Should identify mentioned competitors
        competitors = result.identified_competitors
        assert len(competitors) > 0
        
        # Check competitor structure
        for competitor in competitors:
            assert "name" in competitor
            assert "mention_count" in competitor
            assert "threat_level" in competitor
            assert competitor["mention_count"] >= 1
    
    @pytest.mark.asyncio
    async def test_market_saturation_assessment(self, analyzer):
        """Test market saturation assessment."""
        saturated_signals = [
            {
                "content": "The market is saturated with many options and established players dominating",
                "engagement_metrics": {"total_engagement": 20}
            },
            {
                "content": "Crowded market with lots of existing solutions and tools available",
                "engagement_metrics": {"total_engagement": 15}
            }
        ]
        
        unsaturated_signals = [
            {
                "content": "No good solution exists for this specific problem area",
                "engagement_metrics": {"total_engagement": 20}
            },
            {
                "content": "Gap in market with unmet needs and lacking options",
                "engagement_metrics": {"total_engagement": 15}
            }
        ]
        
        saturated_result = await analyzer.analyze_competition(saturated_signals)
        unsaturated_result = await analyzer.analyze_competition(unsaturated_signals)
        
        assert saturated_result.market_saturation > unsaturated_result.market_saturation
        assert len(unsaturated_result.market_gaps) > 0
    
    @pytest.mark.asyncio
    async def test_competitive_advantages_identification(self, analyzer):
        """Test identification of competitive advantages."""
        advantage_signals = [
            {
                "content": "Need AI-powered solution that's fast and efficient with seamless integration",
                "engagement_metrics": {"total_engagement": 25}
            },
            {
                "content": "Looking for innovative and user-friendly tool that's cost-effective",
                "engagement_metrics": {"total_engagement": 30}
            }
        ]
        
        result = await analyzer.analyze_competition(advantage_signals)
        
        # Should identify potential competitive advantages
        advantages = result.competitive_advantages
        assert len(advantages) > 0
        
        # Should identify AI-native advantage
        ai_advantage_found = any("ai" in adv.lower() for adv in advantages)
        assert ai_advantage_found, f"Expected AI advantage in {advantages}"
    
    @pytest.mark.asyncio
    async def test_market_positioning_determination(self, analyzer):
        """Test market positioning determination."""
        # Blue ocean scenario: low competition + gaps + advantages
        blue_ocean_signals = [
            {
                "content": "No solution exists for this AI-powered niche with unique innovative approach",
                "engagement_metrics": {"total_engagement": 20}
            }
        ]
        
        # Red ocean scenario: high competition
        red_ocean_signals = [
            {
                "content": "Market dominated by established players like Google, Microsoft, and Amazon with saturated competition",
                "engagement_metrics": {"total_engagement": 20}
            }
        ]
        
        blue_result = await analyzer.analyze_competition(blue_ocean_signals)
        red_result = await analyzer.analyze_competition(red_ocean_signals)
        
        # Blue ocean should have lower competition score
        assert blue_result.competition_score < red_result.competition_score
    
    @pytest.mark.asyncio
    async def test_empty_signals_handling(self, analyzer):
        """Test handling of empty signal list."""
        result = await analyzer.analyze_competition([])
        
        assert result.competition_level == "unknown"
        assert result.competition_score == 50.0  # Neutral score
        assert result.confidence_level == 0.0
        assert len(result.identified_competitors) == 0


class TestAdvancedScoringEngine:
    """Test cases for AdvancedScoringEngine."""
    
    @pytest.fixture
    def scoring_engine(self):
        """Create AdvancedScoringEngine instance for testing."""
        return AdvancedScoringEngine()
    
    @pytest.fixture
    def comprehensive_signals(self):
        """Comprehensive signal set for testing."""
        return [
            {
                "signal_id": "signal_1",
                "content": "Critical problem with manual data processing blocking our workflow daily",
                "signal_type": "pain_point",
                "source": "github",
                "engagement_metrics": {"total_engagement": 65, "upvotes": 40, "comments": 25},
                "ai_relevance_score": 90.0,
                "confidence": 0.9,
                "sentiment_score": -0.7,
                "extracted_at": datetime.utcnow().isoformat()
            },
            {
                "signal_id": "signal_2",
                "content": "Need automated ML solution for document classification and processing",
                "signal_type": "feature_request",
                "source": "stackoverflow",
                "engagement_metrics": {"total_engagement": 45, "upvotes": 30, "comments": 15},
                "ai_relevance_score": 95.0,
                "confidence": 0.85,
                "sentiment_score": 0.3,
                "extracted_at": (datetime.utcnow() - timedelta(days=3)).isoformat()
            },
            {
                "signal_id": "signal_3",
                "content": "Market opportunity for AI-powered automation tools in enterprise space",
                "signal_type": "opportunity",
                "source": "hackernews",
                "engagement_metrics": {"total_engagement": 85, "upvotes": 55, "comments": 30},
                "ai_relevance_score": 88.0,
                "confidence": 0.8,
                "sentiment_score": 0.5,
                "extracted_at": (datetime.utcnow() - timedelta(days=7)).isoformat()
            },
            {
                "signal_id": "signal_4",
                "content": "Existing solutions like legacy systems don't provide good AI integration",
                "signal_type": "complaint",
                "source": "reddit",
                "engagement_metrics": {"total_engagement": 35, "upvotes": 22, "comments": 13},
                "ai_relevance_score": 80.0,
                "confidence": 0.75,
                "sentiment_score": -0.4,
                "extracted_at": (datetime.utcnow() - timedelta(days=10)).isoformat()
            }
        ]
    
    @pytest.mark.asyncio
    async def test_advanced_scoring_comprehensive(self, scoring_engine, comprehensive_signals):
        """Test comprehensive advanced scoring."""
        opportunity_context = {
            "ai_solution_types": ["machine_learning", "natural_language_processing"],
            "target_industries": ["enterprise", "technology"],
            "title": "AI-Powered Document Processing Automation",
            "description": "Automated document processing using ML and NLP"
        }
        
        result = await scoring_engine.calculate_advanced_score(
            signals=comprehensive_signals,
            opportunity_context=opportunity_context
        )
        
        assert isinstance(result, AdvancedOpportunityScore)
        assert 0 <= result.overall_score <= 100
        assert 0 <= result.ai_feasibility_score <= 100
        assert 0 <= result.implementation_complexity <= 100
        assert 0 <= result.market_timing_score <= 100
        assert 0 <= result.business_viability_score <= 100
        assert 0 <= result.risk_assessment_score <= 100
        assert 0 <= result.confidence_level <= 1
        
        # Should have reasonable scores given the high-quality signals
        assert result.overall_score > 60, f"Expected high overall score, got {result.overall_score}"
        assert result.market_validation.overall_score > 50
        assert result.ai_feasibility_score > 70  # High AI relevance in signals
        
        # Should have detailed market validation
        assert result.market_validation.pain_intensity > 60  # Critical pain points
        assert result.market_validation.source_credibility > 60  # Good sources
    
    @pytest.mark.asyncio
    async def test_ai_feasibility_scoring(self, scoring_engine):
        """Test AI feasibility scoring with different AI types."""
        high_feasibility_context = {
            "ai_solution_types": ["automation", "recommendation_systems"],  # Mature AI types
            "target_industries": ["technology"]
        }
        
        low_feasibility_context = {
            "ai_solution_types": ["computer_vision", "speech_recognition"],  # More complex AI types
            "target_industries": ["healthcare"]
        }
        
        signals = [
            {
                "content": "Need AI solution for automation",
                "ai_relevance_score": 80.0,
                "engagement_metrics": {"total_engagement": 20}
            }
        ]
        
        high_result = await scoring_engine.calculate_advanced_score(
            signals=signals,
            opportunity_context=high_feasibility_context
        )
        
        low_result = await scoring_engine.calculate_advanced_score(
            signals=signals,
            opportunity_context=low_feasibility_context
        )
        
        # Mature AI types should have higher feasibility
        assert high_result.ai_feasibility_score >= low_result.ai_feasibility_score
    
    @pytest.mark.asyncio
    async def test_market_timing_scoring(self, scoring_engine):
        """Test market timing scoring."""
        urgent_signals = [
            {
                "content": "Urgent need for immediate solution to critical problem now",
                "engagement_metrics": {"total_engagement": 30},
                "extracted_at": datetime.utcnow().isoformat()
            }
        ]
        
        future_signals = [
            {
                "content": "Eventually we might need a solution for this someday in the future",
                "engagement_metrics": {"total_engagement": 30},
                "extracted_at": (datetime.utcnow() - timedelta(days=60)).isoformat()
            }
        ]
        
        urgent_result = await scoring_engine.calculate_advanced_score(signals=urgent_signals)
        future_result = await scoring_engine.calculate_advanced_score(signals=future_signals)
        
        # Urgent signals should have better timing score
        assert urgent_result.market_timing_score > future_result.market_timing_score
        assert urgent_result.market_timing_score > 70  # Should be high for urgent needs
    
    @pytest.mark.asyncio
    async def test_business_viability_calculation(self, scoring_engine, comprehensive_signals):
        """Test business viability calculation."""
        result = await scoring_engine.calculate_advanced_score(signals=comprehensive_signals)
        
        # Business viability should consider market demand, competition, and feasibility
        assert 0 <= result.business_viability_score <= 100
        
        # With high market demand and AI feasibility, should have good viability
        if result.market_validation.market_demand > 70 and result.ai_feasibility_score > 70:
            assert result.business_viability_score > 60
    
    @pytest.mark.asyncio
    async def test_risk_assessment_calculation(self, scoring_engine):
        """Test risk assessment calculation."""
        high_risk_signals = [
            {
                "content": "Highly competitive market with established dominant players and complex technical requirements",
                "engagement_metrics": {"total_engagement": 20}
            }
        ]
        
        low_risk_signals = [
            {
                "content": "Unmet market need with simple automation solution and no existing competitors",
                "engagement_metrics": {"total_engagement": 20}
            }
        ]
        
        high_risk_result = await scoring_engine.calculate_advanced_score(signals=high_risk_signals)
        low_risk_result = await scoring_engine.calculate_advanced_score(signals=low_risk_signals)
        
        # High risk scenario should have higher risk score
        assert high_risk_result.risk_assessment_score >= low_risk_result.risk_assessment_score
    
    @pytest.mark.asyncio
    async def test_scoring_with_agent_analysis(self, scoring_engine, comprehensive_signals):
        """Test scoring with agent analysis input."""
        agent_analysis = {
            "ai_feasibility_score": 85.0,
            "implementation_complexity": 45.0,
            "market_timing_score": 75.0
        }
        
        result = await scoring_engine.calculate_advanced_score(
            signals=comprehensive_signals,
            agent_analysis=agent_analysis
        )
        
        # Should use agent analysis values
        assert result.ai_feasibility_score == 85.0
        assert result.implementation_complexity == 45.0
        assert result.market_timing_score == 75.0
    
    def test_scoring_engine_initialization(self):
        """Test AdvancedScoringEngine initialization."""
        custom_config = {
            "scoring_weights": {
                "market_validation": 0.4,
                "competitive_analysis": 0.3,
                "ai_feasibility": 0.2,
                "implementation_complexity": 0.05,
                "market_timing": 0.05
            }
        }
        
        engine = AdvancedScoringEngine(custom_config)
        
        assert engine.scoring_weights["market_validation"] == 0.4
        assert engine.scoring_weights["competitive_analysis"] == 0.3
        assert isinstance(engine.market_validator, MarketValidationScorer)
        assert isinstance(engine.competitive_analyzer, CompetitiveAnalysisEngine)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])