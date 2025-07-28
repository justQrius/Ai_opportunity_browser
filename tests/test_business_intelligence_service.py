"""
Tests for BusinessIntelligenceService.

Tests comprehensive business intelligence functionality including:
- Market analysis algorithms
- Trend forecasting capabilities  
- ROI projection calculations
- Competitive intelligence analysis
- Comprehensive business intelligence reports
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.services.business_intelligence_service import (
    BusinessIntelligenceService,
    MarketAnalysisResult,
    TrendForecast,
    ROIProjection,
    CompetitiveIntelligence,
    BusinessIntelligenceReport,
    business_intelligence_service
)
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.market_signal import MarketSignal, SignalType
from shared.models.user import User


@pytest.fixture
def bi_service():
    """Business Intelligence Service fixture."""
    return BusinessIntelligenceService()


@pytest.fixture
def sample_opportunity():
    """Sample opportunity for testing."""
    return Opportunity(
        id="test-opp-123",
        title="AI-Powered Customer Service Automation",
        description="Automated customer service solution using NLP and ML to handle customer inquiries",
        status=OpportunityStatus.VALIDATED,
        ai_solution_types='["nlp", "ml", "automation"]',
        target_industries='["retail", "finance", "healthcare"]',
        required_capabilities='["natural_language_processing", "machine_learning", "api_integration"]',
        geographic_scope="global",
        market_size_estimate='{"tam": 50000000000, "sam": 15000000000, "som": 1500000000}',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_market_signals():
    """Sample market signals for testing."""
    base_time = datetime.utcnow()
    return [
        MarketSignal(
            id=f"signal-{i}",
            signal_type=SignalType.PAIN_POINT,
            content=f"Customer service automation pain point {i}",
            source_url=f"https://example.com/signal-{i}",
            keywords='["automation", "customer service", "AI"]',
            engagement_score=0.7 + (i * 0.05),
            confidence_score=0.8,
            created_at=base_time - timedelta(days=i*5)
        )
        for i in range(20)
    ]


@pytest.fixture
async def mock_db_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


class TestBusinessIntelligenceService:
    """Test cases for BusinessIntelligenceService."""
    
    @pytest.mark.asyncio
    async def test_generate_market_analysis(self, bi_service, mock_db_session, sample_opportunity, sample_market_signals):
        """Test market analysis generation."""
        result = await bi_service.generate_market_analysis(
            mock_db_session, sample_opportunity, sample_market_signals
        )
        
        assert isinstance(result, MarketAnalysisResult)
        assert result.market_id == "market_test-opp-123"
        assert result.market_name == "AI-Powered AI Solutions Market"
        assert result.total_addressable_market > 0
        assert result.serviceable_addressable_market > 0
        assert result.serviceable_obtainable_market > 0
        assert 0 <= result.market_growth_rate <= 50
        assert result.market_maturity in ["emerging", "growth", "mature", "declining", "early"]
        assert isinstance(result.key_players, list)
        assert isinstance(result.market_trends, list)
        assert isinstance(result.barriers_to_entry, list)
        assert isinstance(result.success_factors, list)
        assert isinstance(result.risk_assessment, dict)
        assert 0 <= result.confidence_score <= 1
    
    @pytest.mark.asyncio
    async def test_generate_trend_forecast(self, bi_service, mock_db_session, sample_opportunity, sample_market_signals):
        """Test trend forecasting."""
        result = await bi_service.generate_trend_forecast(
            mock_db_session, sample_opportunity, sample_market_signals
        )
        
        assert isinstance(result, TrendForecast)
        assert result.trend_id == "trend_test-opp-123"
        assert result.trend_name == "AI-Powered Market Trend"
        assert 0 <= result.current_strength <= 100
        assert 0 <= result.predicted_strength_3m <= 100
        assert 0 <= result.predicted_strength_6m <= 100
        assert 0 <= result.predicted_strength_12m <= 100
        assert result.trajectory in ["accelerating", "stable", "declining"]
        assert isinstance(result.key_drivers, list)
        assert isinstance(result.risk_factors, list)
        assert isinstance(result.opportunity_windows, list)
        assert len(result.confidence_interval) == 2
        assert isinstance(result.supporting_data, dict)
    
    @pytest.mark.asyncio
    async def test_generate_roi_projection(self, bi_service, mock_db_session, sample_opportunity):
        """Test ROI projection generation."""
        # Create sample market analysis
        market_analysis = MarketAnalysisResult(
            market_id="test_market",
            market_name="Test Market",
            total_addressable_market=1000000000,
            serviceable_addressable_market=300000000,
            serviceable_obtainable_market=30000000,
            market_growth_rate=15.0,
            market_maturity="growth",
            key_players=[],
            market_trends=[],
            barriers_to_entry=[],
            success_factors=[],
            risk_assessment={},
            confidence_score=0.8
        )
        
        result = await bi_service.generate_roi_projection(
            mock_db_session, sample_opportunity, market_analysis
        )
        
        assert isinstance(result, ROIProjection)
        assert result.projection_id == "roi_test-opp-123"
        assert result.opportunity_id == "test-opp-123"
        assert isinstance(result.investment_scenarios, dict)
        assert "low" in result.investment_scenarios
        assert "medium" in result.investment_scenarios
        assert "high" in result.investment_scenarios
        assert isinstance(result.revenue_projections, dict)
        assert isinstance(result.cost_breakdown, dict)
        assert isinstance(result.break_even_analysis, dict)
        assert isinstance(result.roi_metrics, dict)
        assert isinstance(result.risk_adjusted_returns, dict)
        assert isinstance(result.sensitivity_analysis, dict)
        assert isinstance(result.market_assumptions, dict)
    
    @pytest.mark.asyncio
    async def test_generate_competitive_intelligence(self, bi_service, mock_db_session, sample_opportunity, sample_market_signals):
        """Test competitive intelligence generation."""
        result = await bi_service.generate_competitive_intelligence(
            mock_db_session, sample_opportunity, sample_market_signals
        )
        
        assert isinstance(result, CompetitiveIntelligence)
        assert result.analysis_id == "competitive_test-opp-123"
        assert result.market_segment == "AI-powered business solutions"
        assert isinstance(result.competitors, list)
        assert isinstance(result.competitive_positioning, dict)
        assert isinstance(result.market_share_analysis, dict)
        assert isinstance(result.competitive_advantages, list)
        assert isinstance(result.threats_analysis, list)
        assert isinstance(result.strategic_recommendations, list)
        assert isinstance(result.market_gaps, list)
        assert isinstance(result.differentiation_opportunities, list)
    
    @pytest.mark.asyncio
    async def test_generate_comprehensive_report(self, bi_service, mock_db_session, sample_opportunity, sample_market_signals):
        """Test comprehensive business intelligence report generation."""
        # Mock database queries
        mock_db_session.execute = AsyncMock()
        
        # Mock opportunity query
        opportunity_result = MagicMock()
        opportunity_result.scalar_one_or_none.return_value = sample_opportunity
        
        # Mock signals query
        signals_result = MagicMock()
        signals_result.scalars.return_value.all.return_value = sample_market_signals
        
        mock_db_session.execute.side_effect = [opportunity_result, signals_result]
        
        result = await bi_service.generate_comprehensive_report(
            mock_db_session, "test-opp-123"
        )
        
        assert isinstance(result, BusinessIntelligenceReport)
        assert result.report_id == "bi_report_test-opp-123"
        assert result.opportunity_id == "test-opp-123"
        assert isinstance(result.generated_at, datetime)
        assert isinstance(result.market_analysis, MarketAnalysisResult)
        assert isinstance(result.trend_forecast, TrendForecast)
        assert isinstance(result.roi_projection, ROIProjection)
        assert isinstance(result.competitive_intelligence, CompetitiveIntelligence)
        assert isinstance(result.executive_summary, dict)
        assert isinstance(result.strategic_recommendations, list)
        assert isinstance(result.implementation_roadmap, list)
        assert isinstance(result.key_metrics, dict)
    
    @pytest.mark.asyncio
    async def test_market_size_estimation(self, bi_service, mock_db_session, sample_opportunity, sample_market_signals):
        """Test market size estimation algorithms."""
        tam, sam, som = await bi_service._estimate_market_size(
            mock_db_session, sample_opportunity, sample_market_signals
        )
        
        assert tam > sam > som > 0
        assert sam == tam * 0.3  # 30% of TAM
        assert som == sam * 0.1  # 10% of SAM
    
    @pytest.mark.asyncio
    async def test_market_growth_calculation(self, bi_service, mock_db_session, sample_opportunity, sample_market_signals):
        """Test market growth rate calculation."""
        growth_rate = await bi_service._calculate_market_growth(
            mock_db_session, sample_opportunity, sample_market_signals
        )
        
        assert isinstance(growth_rate, float)
        assert 5.0 <= growth_rate <= 50.0  # Reasonable bounds
    
    @pytest.mark.asyncio
    async def test_market_maturity_assessment(self, bi_service, sample_market_signals):
        """Test market maturity assessment."""
        maturity = await bi_service._assess_market_maturity(sample_market_signals)
        
        assert maturity in ["emerging", "growth", "mature", "declining", "early"]
    
    @pytest.mark.asyncio
    async def test_trend_strength_calculation(self, bi_service, sample_market_signals):
        """Test current trend strength calculation."""
        strength = await bi_service._calculate_current_trend_strength(sample_market_signals)
        
        assert isinstance(strength, float)
        assert 0 <= strength <= 100
    
    @pytest.mark.asyncio
    async def test_trend_prediction(self, bi_service, sample_market_signals):
        """Test trend evolution prediction."""
        predictions = await bi_service._predict_trend_evolution(sample_market_signals, 365)
        
        assert isinstance(predictions, dict)
        assert '3m' in predictions
        assert '6m' in predictions
        assert '12m' in predictions
        
        for timeframe, prediction in predictions.items():
            assert isinstance(prediction, float)
            assert 0 <= prediction <= 100
    
    @pytest.mark.asyncio
    async def test_key_players_identification(self, bi_service, mock_db_session, sample_opportunity, sample_market_signals):
        """Test key market players identification."""
        # Add some company mentions to signals
        sample_market_signals[0].content = "Customer service company ServiceNow is leading the automation space"
        sample_market_signals[1].content = "Zendesk company has strong market presence"
        sample_market_signals[2].content = "ServiceNow company continues to innovate"
        
        players = await bi_service._identify_key_players(
            mock_db_session, sample_opportunity, sample_market_signals
        )
        
        assert isinstance(players, list)
        for player in players:
            assert "name" in player
            assert "mentions" in player
            assert "market_position" in player
            assert isinstance(player["mentions"], int)
            assert player["market_position"] in ["established", "emerging"]
    
    @pytest.mark.asyncio
    async def test_market_trends_analysis(self, bi_service, sample_market_signals):
        """Test market trends analysis."""
        trends = await bi_service._analyze_market_trends(sample_market_signals)
        
        assert isinstance(trends, list)
        assert len(trends) <= 10  # Top 10 trends
        
        for trend in trends:
            assert "keyword" in trend
            assert "trend_strength" in trend
            assert "total_mentions" in trend
            assert "recent_mentions" in trend
            assert "trend_type" in trend
            assert 0 <= trend["trend_strength"] <= 1
            assert trend["trend_type"] in ["growing", "stable"]
    
    @pytest.mark.asyncio
    async def test_barriers_identification(self, bi_service, sample_opportunity, sample_market_signals):
        """Test barriers to entry identification."""
        barriers = await bi_service._identify_barriers_to_entry(sample_opportunity, sample_market_signals)
        
        assert isinstance(barriers, list)
        assert len(barriers) <= 5  # Top 5 barriers
        
        for barrier in barriers:
            assert isinstance(barrier, str)
            assert len(barrier) > 10  # Meaningful description
    
    @pytest.mark.asyncio
    async def test_success_factors_identification(self, bi_service, sample_opportunity, sample_market_signals):
        """Test success factors identification."""
        factors = await bi_service._identify_success_factors(sample_opportunity, sample_market_signals)
        
        assert isinstance(factors, list)
        assert len(factors) <= 5  # Top 5 factors
        
        for factor in factors:
            assert isinstance(factor, str)
            assert len(factor) > 10  # Meaningful description
    
    @pytest.mark.asyncio
    async def test_risk_assessment(self, bi_service, sample_opportunity, sample_market_signals):
        """Test market risk assessment."""
        risks = await bi_service._assess_market_risks(sample_opportunity, sample_market_signals)
        
        assert isinstance(risks, dict)
        expected_risks = ["technology_risk", "market_risk", "competitive_risk", "regulatory_risk", "execution_risk"]
        
        for risk_type in expected_risks:
            assert risk_type in risks
            assert 0 <= risks[risk_type] <= 1
    
    def test_confidence_calculation(self, bi_service, sample_opportunity, sample_market_signals):
        """Test analysis confidence calculation."""
        confidence = bi_service._calculate_analysis_confidence(sample_market_signals, sample_opportunity)
        
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1
    
    def test_market_name_generation(self, bi_service, sample_opportunity):
        """Test market name generation."""
        name = bi_service._generate_market_name(sample_opportunity)
        
        assert isinstance(name, str)
        assert "AI Solutions Market" in name
        assert len(name) > 10
    
    def test_trend_name_generation(self, bi_service, sample_opportunity):
        """Test trend name generation."""
        name = bi_service._generate_trend_name(sample_opportunity)
        
        assert isinstance(name, str)
        assert "Market Trend" in name
        assert len(name) > 10
    
    def test_trajectory_determination(self, bi_service):
        """Test trend trajectory determination."""
        # Test accelerating trajectory
        predictions_acc = {'3m': 50, '6m': 60, '12m': 80}
        trajectory_acc = bi_service._determine_trend_trajectory(predictions_acc)
        assert trajectory_acc == "accelerating"
        
        # Test declining trajectory
        predictions_dec = {'3m': 80, '6m': 70, '12m': 50}
        trajectory_dec = bi_service._determine_trend_trajectory(predictions_dec)
        assert trajectory_dec == "declining"
        
        # Test stable trajectory
        predictions_stable = {'3m': 60, '6m': 62, '12m': 65}
        trajectory_stable = bi_service._determine_trend_trajectory(predictions_stable)
        assert trajectory_stable == "stable"
    
    @pytest.mark.asyncio
    async def test_opportunity_not_found_error(self, bi_service, mock_db_session):
        """Test error handling when opportunity is not found."""
        # Mock database query to return None
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = result_mock
        
        with pytest.raises(ValueError, match="Opportunity nonexistent not found"):
            await bi_service._get_opportunity(mock_db_session, "nonexistent")
    
    @pytest.mark.asyncio
    async def test_serialization_methods(self, bi_service, mock_db_session, sample_opportunity, sample_market_signals):
        """Test data class serialization methods."""
        # Test MarketAnalysisResult serialization
        market_analysis = await bi_service.generate_market_analysis(
            mock_db_session, sample_opportunity, sample_market_signals
        )
        market_dict = market_analysis.to_dict()
        assert isinstance(market_dict, dict)
        assert "market_id" in market_dict
        assert "confidence_score" in market_dict
        
        # Test TrendForecast serialization
        trend_forecast = await bi_service.generate_trend_forecast(
            mock_db_session, sample_opportunity, sample_market_signals
        )
        trend_dict = trend_forecast.to_dict()
        assert isinstance(trend_dict, dict)
        assert "trend_id" in trend_dict
        assert "trajectory" in trend_dict
    
    @pytest.mark.asyncio
    async def test_empty_signals_handling(self, bi_service, mock_db_session, sample_opportunity):
        """Test handling of empty market signals."""
        empty_signals = []
        
        # Market analysis with empty signals should still work
        result = await bi_service.generate_market_analysis(
            mock_db_session, sample_opportunity, empty_signals
        )
        assert isinstance(result, MarketAnalysisResult)
        assert result.confidence_score < 0.8  # Lower confidence with no signals
        
        # Trend forecast with empty signals
        trend_result = await bi_service.generate_trend_forecast(
            mock_db_session, sample_opportunity, empty_signals
        )
        assert isinstance(trend_result, TrendForecast)
        assert trend_result.current_strength == 50.0  # Default value
    
    @pytest.mark.asyncio
    async def test_json_field_parsing(self, bi_service, mock_db_session, sample_opportunity, sample_market_signals):
        """Test JSON field parsing in opportunity data."""
        # Test with string JSON fields (as they come from database)
        sample_opportunity.ai_solution_types = '["nlp", "computer_vision"]'
        sample_opportunity.target_industries = '["healthcare", "finance"]'
        
        result = await bi_service.generate_market_analysis(
            mock_db_session, sample_opportunity, sample_market_signals
        )
        
        assert isinstance(result, MarketAnalysisResult)
        # Should handle JSON parsing without errors
        
        # Test with invalid JSON (should not crash)
        sample_opportunity.ai_solution_types = 'invalid json'
        
        result2 = await bi_service.generate_market_analysis(
            mock_db_session, sample_opportunity, sample_market_signals
        )
        assert isinstance(result2, MarketAnalysisResult)
    
    @pytest.mark.asyncio
    async def test_forecast_confidence_intervals(self, bi_service, sample_market_signals):
        """Test forecast confidence interval calculation."""
        predictions = {'3m': 60, '6m': 65, '12m': 70}
        confidence_interval = bi_service._calculate_forecast_confidence(sample_market_signals, predictions)
        
        assert isinstance(confidence_interval, tuple)
        assert len(confidence_interval) == 2
        assert confidence_interval[0] < confidence_interval[1]
        assert 0 <= confidence_interval[0] <= 1
        assert 0 <= confidence_interval[1] <= 1


class TestBusinessIntelligenceIntegration:
    """Integration tests for Business Intelligence Service."""
    
    @pytest.mark.asyncio
    async def test_service_singleton(self):
        """Test that the service singleton works correctly."""
        assert business_intelligence_service is not None
        assert isinstance(business_intelligence_service, BusinessIntelligenceService)
    
    @pytest.mark.asyncio
    async def test_full_workflow_integration(self, bi_service, mock_db_session, sample_opportunity, sample_market_signals):
        """Test the full business intelligence workflow."""
        # Mock database queries for comprehensive report
        mock_db_session.execute = AsyncMock()
        
        # Mock opportunity query
        opportunity_result = MagicMock()
        opportunity_result.scalar_one_or_none.return_value = sample_opportunity
        
        # Mock signals query
        signals_result = MagicMock()
        signals_result.scalars.return_value.all.return_value = sample_market_signals
        
        mock_db_session.execute.side_effect = [opportunity_result, signals_result]
        
        # Generate comprehensive report
        report = await bi_service.generate_comprehensive_report(mock_db_session, "test-opp-123")
        
        # Validate that all components are properly integrated
        assert report.market_analysis.market_id == "market_test-opp-123"
        assert report.trend_forecast.trend_id == "trend_test-opp-123"
        assert report.roi_projection.opportunity_id == "test-opp-123"
        assert report.competitive_intelligence.analysis_id == "competitive_test-opp-123"
        
        # Test serialization of complete report
        report_dict = report.to_dict()
        assert isinstance(report_dict, dict)
        assert "report_id" in report_dict
        assert "generated_at" in report_dict
        assert "market_analysis" in report_dict
        assert "trend_forecast" in report_dict
        assert "roi_projection" in report_dict
        assert "competitive_intelligence" in report_dict
        
        # Validate nested serialization
        assert isinstance(report_dict["market_analysis"], dict)
        assert isinstance(report_dict["trend_forecast"], dict)
        assert isinstance(report_dict["roi_projection"], dict)
        assert isinstance(report_dict["competitive_intelligence"], dict)


# Performance and edge case tests
class TestBusinessIntelligenceEdgeCases:
    """Edge case tests for Business Intelligence Service."""
    
    @pytest.mark.asyncio
    async def test_large_signal_dataset(self, bi_service, mock_db_session, sample_opportunity):
        """Test performance with large signal datasets."""
        # Create a large number of signals
        large_signal_set = []
        base_time = datetime.utcnow()
        
        for i in range(1000):
            signal = MarketSignal(
                id=f"signal-{i}",
                signal_type=SignalType.PAIN_POINT,
                content=f"Signal content {i} about automation and AI",
                source_url=f"https://example.com/signal-{i}",
                keywords='["automation", "AI", "customer service"]',
                engagement_score=0.5 + (i % 10) * 0.05,
                confidence_score=0.8,
                created_at=base_time - timedelta(hours=i)
            )
            large_signal_set.append(signal)
        
        # Should handle large datasets efficiently
        result = await bi_service.generate_market_analysis(
            mock_db_session, sample_opportunity, large_signal_set
        )
        
        assert isinstance(result, MarketAnalysisResult)
        assert result.confidence_score > 0.8  # Should have high confidence with many signals
    
    @pytest.mark.asyncio
    async def test_minimal_opportunity_data(self, bi_service, mock_db_session, sample_market_signals):
        """Test with minimal opportunity data."""
        minimal_opportunity = Opportunity(
            id="minimal-opp",
            title="Basic AI Opportunity",
            description="A basic AI opportunity with minimal information",
            status=OpportunityStatus.DISCOVERED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        result = await bi_service.generate_market_analysis(
            mock_db_session, minimal_opportunity, sample_market_signals
        )
        
        assert isinstance(result, MarketAnalysisResult)
        # Should still work but with lower confidence
        assert result.confidence_score < 0.7
    
    @pytest.mark.asyncio
    async def test_extreme_engagement_scores(self, bi_service, sample_opportunity):
        """Test with extreme engagement score values."""
        extreme_signals = [
            MarketSignal(
                id="high-engagement",
                signal_type=SignalType.PAIN_POINT,
                content="High engagement signal",
                engagement_score=1.0,  # Maximum
                confidence_score=1.0,
                created_at=datetime.utcnow()
            ),
            MarketSignal(
                id="zero-engagement",
                signal_type=SignalType.SOLUTION_MENTION,
                content="Zero engagement signal",
                engagement_score=0.0,  # Minimum
                confidence_score=0.0,
                created_at=datetime.utcnow()
            ),
            MarketSignal(
                id="none-engagement",
                signal_type=SignalType.MARKET_TREND,
                content="None engagement signal",
                engagement_score=None,  # None value
                confidence_score=None,
                created_at=datetime.utcnow()
            )
        ]
        
        strength = await bi_service._calculate_current_trend_strength(extreme_signals)
        assert isinstance(strength, float)
        assert 0 <= strength <= 100


if __name__ == "__main__":
    pytest.main([__file__])