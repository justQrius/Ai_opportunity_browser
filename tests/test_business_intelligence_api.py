"""
Tests for Business Intelligence API endpoints.

Tests comprehensive business intelligence API functionality including:
- Market analysis endpoints
- Trend forecasting endpoints
- ROI projection endpoints
- Advanced ROI analysis endpoints
- Business model recommendation endpoints
- Monte Carlo simulation endpoints
- Authentication and authorization
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from fastapi.testclient import TestClient
from fastapi import status
from httpx import AsyncClient

from api.main import app
from shared.models.user import User, UserRole
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.services.business_intelligence_service import (
    MarketAnalysisResult,
    TrendForecast,
    ROIProjection,
    BusinessIntelligenceReport
)
from shared.services.advanced_roi_service import (
    AdvancedROIAnalysis,
    BusinessModelRecommendation,
    MonteCarloResult,
    BusinessModel
)


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return User(
        id="test-user-bi",
        email="bi.analyst@example.com",
        username="bi_analyst",
        full_name="Business Intelligence Analyst",
        is_active=True,
        is_premium=True,
        roles=["analyst", "user"],
        created_at=datetime.utcnow()
    )


@pytest.fixture
def sample_opportunity():
    """Sample opportunity for testing."""
    return Opportunity(
        id="test-opp-bi-api",
        title="AI Business Intelligence Platform",
        description="Advanced AI-powered business intelligence and analytics platform",
        status=OpportunityStatus.VALIDATED,
        ai_solution_types='["ml", "nlp", "analytics"]',
        target_industries='["finance", "retail", "healthcare"]',
        required_capabilities='["machine_learning", "data_analytics", "reporting"]',
        created_at=datetime.utcnow()
    )


@pytest.fixture
def sample_market_analysis():
    """Sample market analysis result."""
    return MarketAnalysisResult(
        market_id="market_test-opp-bi-api",
        market_name="AI Business Intelligence Market",
        total_addressable_market=50000000000,
        serviceable_addressable_market=15000000000,
        serviceable_obtainable_market=1500000000,
        market_growth_rate=22.5,
        market_maturity="growth",
        key_players=[{"name": "BI Corp", "mentions": 12, "market_position": "established"}],
        market_trends=[{"keyword": "ai_analytics", "trend_strength": 0.85, "total_mentions": 35}],
        barriers_to_entry=["Technical complexity", "Data requirements"],
        success_factors=["Domain expertise", "Data quality"],
        risk_assessment={"technology_risk": 0.3, "market_risk": 0.2},
        confidence_score=0.82
    )


@pytest.fixture
def mock_auth_user(sample_user):
    """Mock authenticated user dependency."""
    async def mock_get_current_user():
        return sample_user
    return mock_get_current_user


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    session.get = AsyncMock()
    return session


class TestMarketAnalysisEndpoints:
    """Test market analysis API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_market_analysis_success(self, client, sample_opportunity, sample_market_analysis, mock_auth_user, mock_db_session):
        """Test successful market analysis retrieval."""
        with patch('api.routers.business_intelligence.get_current_user', return_value=mock_auth_user), \
             patch('api.routers.business_intelligence.get_db_session', return_value=mock_db_session), \
             patch('shared.services.business_intelligence_service.business_intelligence_service') as mock_service:
            
            # Setup mocks
            mock_db_session.get.return_value = sample_opportunity
            mock_service._get_related_market_signals.return_value = []
            mock_service.generate_market_analysis.return_value = sample_market_analysis
            
            response = client.get(f"/api/v1/business-intelligence/opportunities/{sample_opportunity.id}/market-analysis")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "market_analysis" in data
            assert "generated_at" in data
            assert "opportunity_id" in data
            assert data["opportunity_id"] == sample_opportunity.id
            
            market_data = data["market_analysis"]
            assert market_data["market_id"] == "market_test-opp-bi-api"
            assert market_data["total_addressable_market"] == 50000000000
            assert market_data["market_growth_rate"] == 22.5
    
    @pytest.mark.asyncio
    async def test_get_market_analysis_opportunity_not_found(self, client, mock_auth_user, mock_db_session):
        """Test market analysis with non-existent opportunity."""
        with patch('api.routers.business_intelligence.get_current_user', return_value=mock_auth_user), \
             patch('api.routers.business_intelligence.get_db_session', return_value=mock_db_session):
            
            # Setup mocks
            mock_db_session.get.return_value = None
            
            response = client.get("/api/v1/business-intelligence/opportunities/nonexistent/market-analysis")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Opportunity not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_market_analysis_unauthorized(self, client):
        """Test market analysis without authentication."""
        response = client.get("/api/v1/business-intelligence/opportunities/test-id/market-analysis")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTrendForecastEndpoints:
    """Test trend forecast API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_trend_forecast_success(self, client, sample_opportunity, mock_auth_user, mock_db_session):
        """Test successful trend forecast retrieval."""
        sample_trend_forecast = TrendForecast(
            trend_id="trend_test-opp-bi-api",
            trend_name="AI BI Trend",
            current_strength=78.5,
            predicted_strength_3m=85.2,
            predicted_strength_6m=91.8,
            predicted_strength_12m=96.3,
            trajectory="accelerating",
            key_drivers=["Market demand", "Technology advancement"],
            risk_factors=["Competition", "Regulation"],
            opportunity_windows=[{"window": "Q2 2024", "strength": "high"}],
            confidence_interval=(0.7, 0.9),
            supporting_data={"signal_count": 125}
        )
        
        with patch('api.routers.business_intelligence.get_current_user', return_value=mock_auth_user), \
             patch('api.routers.business_intelligence.get_db_session', return_value=mock_db_session), \
             patch('shared.services.business_intelligence_service.business_intelligence_service') as mock_service:
            
            # Setup mocks
            mock_db_session.get.return_value = sample_opportunity
            mock_service._get_related_market_signals.return_value = []
            mock_service.generate_trend_forecast.return_value = sample_trend_forecast
            
            response = client.get(
                f"/api/v1/business-intelligence/opportunities/{sample_opportunity.id}/trend-forecast",
                params={"forecast_horizon": 180}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "trend_forecast" in data
            assert "forecast_horizon_days" in data
            assert data["forecast_horizon_days"] == 180
            
            trend_data = data["trend_forecast"]
            assert trend_data["current_strength"] == 78.5
            assert trend_data["trajectory"] == "accelerating"
    
    @pytest.mark.asyncio
    async def test_get_trend_forecast_invalid_horizon(self, client, mock_auth_user):
        """Test trend forecast with invalid forecast horizon."""
        with patch('api.routers.business_intelligence.get_current_user', return_value=mock_auth_user):
            
            # Test horizon too short
            response = client.get(
                "/api/v1/business-intelligence/opportunities/test-id/trend-forecast",
                params={"forecast_horizon": 15}
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            
            # Test horizon too long
            response = client.get(
                "/api/v1/business-intelligence/opportunities/test-id/trend-forecast",
                params={"forecast_horizon": 2000}
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestROIProjectionEndpoints:
    """Test ROI projection API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_roi_projection_success(self, client, sample_opportunity, sample_market_analysis, mock_auth_user, mock_db_session):
        """Test successful ROI projection retrieval."""
        sample_roi_projection = ROIProjection(
            projection_id="roi_test-opp-bi-api",
            opportunity_id=str(sample_opportunity.id),
            investment_scenarios={"medium": {"initial_investment": 1000000, "annual_opex": 500000}},
            revenue_projections={"medium": [100000, 300000, 600000, 1000000, 1500000]},
            cost_breakdown={"development": 0.4, "marketing": 0.3, "operations": 0.3},
            break_even_analysis={"medium_scenario": {"break_even_month": 24}},
            roi_metrics={"roi_5yr": 350.0, "irr": 42.0, "npv": 2500000},
            risk_adjusted_returns={"roi_5yr": 280.0, "irr": 33.6},
            sensitivity_analysis={"revenue_10_increase": 1.15, "cost_10_increase": 0.88},
            market_assumptions={"growth_rate": 22.5, "market_maturity": "growth"}
        )
        
        with patch('api.routers.business_intelligence.get_current_user', return_value=mock_auth_user), \
             patch('api.routers.business_intelligence.get_db_session', return_value=mock_db_session), \
             patch('shared.services.business_intelligence_service.business_intelligence_service') as mock_service:
            
            # Setup mocks
            mock_db_session.get.return_value = sample_opportunity
            mock_service._get_related_market_signals.return_value = []
            mock_service.generate_market_analysis.return_value = sample_market_analysis
            mock_service.generate_roi_projection.return_value = sample_roi_projection
            
            response = client.get(f"/api/v1/business-intelligence/opportunities/{sample_opportunity.id}/roi-projection")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "roi_projection" in data
            assert "market_analysis_summary" in data
            
            roi_data = data["roi_projection"]
            assert roi_data["projection_id"] == "roi_test-opp-bi-api"
            assert roi_data["roi_metrics"]["roi_5yr"] == 350.0
            
            market_summary = data["market_analysis_summary"]
            assert market_summary["tam"] == 50000000000
            assert market_summary["growth_rate"] == 22.5


class TestAdvancedROIEndpoints:
    """Test advanced ROI analysis API endpoints."""
    
    @pytest.mark.asyncio
    async def test_generate_advanced_roi_analysis_success(self, client, sample_opportunity, mock_auth_user, mock_db_session):
        """Test successful advanced ROI analysis generation."""
        sample_advanced_analysis = AdvancedROIAnalysis(
            analysis_id="advanced_roi_test-opp-bi-api",
            opportunity_id=str(sample_opportunity.id),
            generated_at=datetime.utcnow(),
            investment_scenarios=[],
            revenue_models=[],
            cost_structures=[],
            cash_flow_projections={},
            monte_carlo_results=MonteCarloResult(
                simulation_id="mc_test",
                iterations=10000,
                confidence_intervals={},
                percentile_results={},
                risk_metrics={},
                success_probability=0.75,
                break_even_probability=0.85,
                unicorn_probability=0.15,
                distribution_summary={"mean_roi": 285.5}
            ),
            business_model_recommendation=BusinessModelRecommendation(
                recommended_model=BusinessModel.SAAS,
                confidence_score=0.82,
                reasoning=["Recurring revenue model", "Scalable solution"],
                revenue_potential={"year_1": 500000, "year_3": 2000000, "year_5": 8000000},
                implementation_complexity="medium",
                time_to_market=12,
                capital_requirements={"initial": 1000000, "total_5yr": 5000000},
                risk_assessment={"market_risk": 0.3, "execution_risk": 0.4},
                comparable_companies=[],
                strategic_considerations=["Focus on enterprise market"],
                alternative_models=[]
            ),
            valuation_analysis={},
            exit_strategy_analysis={},
            funding_roadmap=[],
            key_metrics_dashboard={"expected_roi": 285.5, "capital_efficiency": 4.2}
        )
        
        with patch('api.routers.business_intelligence.get_current_user', return_value=mock_auth_user), \
             patch('api.routers.business_intelligence.get_db_session', return_value=mock_db_session), \
             patch('shared.services.advanced_roi_service.advanced_roi_service') as mock_advanced_service, \
             patch('shared.services.business_intelligence_service.business_intelligence_service') as mock_service:
            
            # Setup mocks
            mock_db_session.get.return_value = sample_opportunity
            mock_service._get_related_market_signals.return_value = []
            mock_service.generate_market_analysis.return_value = sample_market_analysis
            mock_service.generate_trend_forecast.return_value = MagicMock()
            mock_advanced_service.generate_advanced_roi_analysis.return_value = sample_advanced_analysis
            
            response = client.post(
                f"/api/v1/business-intelligence/opportunities/{sample_opportunity.id}/advanced-roi-analysis",
                json={"custom_parameters": {"initial_capital": 2000000}}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "advanced_analysis" in data
            assert "executive_summary" in data
            
            exec_summary = data["executive_summary"]
            assert exec_summary["recommended_business_model"] == "saas"
            assert exec_summary["expected_roi"] == 285.5
            assert exec_summary["break_even_probability"] == 0.85
    
    @pytest.mark.asyncio
    async def test_advanced_roi_analysis_permission_denied(self, client, mock_db_session):
        """Test advanced ROI analysis with insufficient permissions."""
        basic_user = User(
            id="basic-user",
            email="basic@example.com",
            username="basic_user",
            is_premium=False,
            roles=["user"]
        )
        
        with patch('api.routers.business_intelligence.get_current_user', return_value=basic_user), \
             patch('api.routers.business_intelligence.get_db_session', return_value=mock_db_session):
            
            response = client.post("/api/v1/business-intelligence/opportunities/test-id/advanced-roi-analysis")
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "premium access or analyst role" in response.json()["detail"]


class TestBusinessModelRecommendationEndpoints:
    """Test business model recommendation API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_business_model_recommendation_success(self, client, sample_opportunity, mock_auth_user, mock_db_session):
        """Test successful business model recommendation retrieval."""
        sample_recommendation = BusinessModelRecommendation(
            recommended_model=BusinessModel.API_SERVICE,
            confidence_score=0.78,
            reasoning=["Pay-per-use aligns with AI processing", "Easy enterprise integration"],
            revenue_potential={"year_1": 300000, "year_3": 1500000, "year_5": 6000000},
            implementation_complexity="low",
            time_to_market=8,
            capital_requirements={"initial": 500000, "working_capital": 100000},
            risk_assessment={"market_risk": 0.25, "execution_risk": 0.35},
            comparable_companies=[{"name": "AI API Corp", "valuation": 100000000}],
            strategic_considerations=["Focus on developer experience"],
            alternative_models=[{"model": "saas", "score": 0.65}]
        )
        
        with patch('api.routers.business_intelligence.get_current_user', return_value=mock_auth_user), \
             patch('api.routers.business_intelligence.get_db_session', return_value=mock_db_session), \
             patch('shared.services.advanced_roi_service.advanced_roi_service') as mock_advanced_service, \
             patch('shared.services.business_intelligence_service.business_intelligence_service') as mock_service:
            
            # Setup mocks
            mock_db_session.get.return_value = sample_opportunity
            mock_service._get_related_market_signals.return_value = []
            mock_service.generate_market_analysis.return_value = sample_market_analysis
            mock_advanced_service._generate_investment_scenarios.return_value = []
            mock_advanced_service._create_revenue_models.return_value = []
            mock_advanced_service._build_cost_structures.return_value = []
            mock_advanced_service._generate_cash_flow_projections.return_value = {}
            mock_advanced_service._recommend_business_model.return_value = sample_recommendation
            
            response = client.get(f"/api/v1/business-intelligence/opportunities/{sample_opportunity.id}/business-model-recommendation")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "recommendation" in data
            assert "analysis_date" in data
            
            recommendation_data = data["recommendation"]
            assert recommendation_data["recommended_model"] == "api_service"
            assert recommendation_data["confidence_score"] == 0.78
            assert recommendation_data["time_to_market"] == 8


class TestMonteCarloSimulationEndpoints:
    """Test Monte Carlo simulation API endpoints."""
    
    @pytest.mark.asyncio
    async def test_run_monte_carlo_simulation_success(self, client, sample_opportunity, mock_auth_user, mock_db_session):
        """Test successful Monte Carlo simulation execution."""
        analyst_user = User(
            id="analyst-user",
            email="analyst@example.com",
            username="analyst",
            roles=["analyst", "user"]
        )
        
        sample_monte_carlo = MonteCarloResult(
            simulation_id="mc_test_123",
            iterations=5000,
            confidence_intervals={
                "roi_5yr": {"90%": (150.0, 450.0), "95%": (120.0, 480.0)},
                "break_even_month": {"90%": (18, 36), "95%": (15, 42)}
            },
            percentile_results={
                "roi_5yr": {"P10": 165.0, "P50": 285.0, "P90": 425.0},
                "break_even_month": {"P10": 20, "P50": 28, "P90": 38}
            },
            risk_metrics={"value_at_risk_95": 165.0, "volatility": 85.2},
            success_probability=0.82,
            break_even_probability=0.89,
            unicorn_probability=0.12,
            distribution_summary={"mean_roi": 295.5, "median_roi": 285.0}
        )
        
        with patch('api.routers.business_intelligence.require_roles', return_value=analyst_user), \
             patch('api.routers.business_intelligence.get_db_session', return_value=mock_db_session), \
             patch('shared.services.advanced_roi_service.advanced_roi_service') as mock_advanced_service, \
             patch('shared.services.business_intelligence_service.business_intelligence_service') as mock_service:
            
            # Setup mocks
            mock_db_session.get.return_value = sample_opportunity
            mock_service._get_related_market_signals.return_value = []
            mock_service.generate_market_analysis.return_value = sample_market_analysis
            mock_advanced_service._generate_investment_scenarios.return_value = []
            mock_advanced_service._create_revenue_models.return_value = []
            mock_advanced_service._build_cost_structures.return_value = []
            mock_advanced_service._run_monte_carlo_simulation.return_value = sample_monte_carlo
            
            response = client.post(
                f"/api/v1/business-intelligence/opportunities/{sample_opportunity.id}/monte-carlo-simulation",
                params={"iterations": 5000}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "simulation_results" in data
            assert "parameters" in data
            
            sim_results = data["simulation_results"]
            assert sim_results["iterations"] == 5000
            assert sim_results["success_probability"] == 0.82
            assert "confidence_intervals" in sim_results
            
            params = data["parameters"]
            assert params["iterations"] == 5000
            assert params["opportunity_id"] == sample_opportunity.id
    
    @pytest.mark.asyncio
    async def test_monte_carlo_simulation_invalid_iterations(self, client, mock_auth_user):
        """Test Monte Carlo simulation with invalid iteration count."""
        analyst_user = User(id="analyst", roles=["analyst"])
        
        with patch('api.routers.business_intelligence.require_roles', return_value=analyst_user):
            
            # Test too few iterations
            response = client.post(
                "/api/v1/business-intelligence/opportunities/test-id/monte-carlo-simulation",
                params={"iterations": 500}
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            
            # Test too many iterations
            response = client.post(
                "/api/v1/business-intelligence/opportunities/test-id/monte-carlo-simulation",
                params={"iterations": 200000}
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestValuationEndpoints:
    """Test valuation analysis API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_valuation_analysis_success(self, client, sample_opportunity, mock_auth_user, mock_db_session):
        """Test successful valuation analysis retrieval."""
        sample_valuation = {
            "revenue_multiple_valuation": 25000000,
            "dcf_valuation": 22000000,
            "market_multiple_valuation": 30000000,
            "recommended_valuation": 23500000,
            "valuation_range": {"low": 18800000, "high": 30550000}
        }
        
        with patch('api.routers.business_intelligence.get_current_user', return_value=mock_auth_user), \
             patch('api.routers.business_intelligence.get_db_session', return_value=mock_db_session), \
             patch('shared.services.advanced_roi_service.advanced_roi_service') as mock_advanced_service, \
             patch('shared.services.business_intelligence_service.business_intelligence_service') as mock_service:
            
            # Setup mocks
            mock_db_session.get.return_value = sample_opportunity
            mock_service._get_related_market_signals.return_value = []
            mock_service.generate_market_analysis.return_value = sample_market_analysis
            mock_service.generate_trend_forecast.return_value = MagicMock()
            mock_advanced_service._generate_investment_scenarios.return_value = []
            mock_advanced_service._create_revenue_models.return_value = []
            mock_advanced_service._build_cost_structures.return_value = []
            mock_advanced_service._generate_cash_flow_projections.return_value = {}
            mock_advanced_service._perform_valuation_analysis.return_value = sample_valuation
            
            response = client.get(f"/api/v1/business-intelligence/opportunities/{sample_opportunity.id}/valuation")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "valuation_analysis" in data
            assert "cash_flow_summary" in data
            
            valuation_data = data["valuation_analysis"]
            assert valuation_data["recommended_valuation"] == 23500000
            assert valuation_data["valuation_range"]["low"] < valuation_data["valuation_range"]["high"]


class TestDashboardEndpoints:
    """Test dashboard and summary API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_analytics_dashboard_summary(self, client, mock_auth_user, mock_db_session):
        """Test analytics dashboard summary retrieval."""
        with patch('api.routers.business_intelligence.get_current_user', return_value=mock_auth_user), \
             patch('api.routers.business_intelligence.get_db_session', return_value=mock_db_session):
            
            response = client.get("/api/v1/business-intelligence/dashboard/analytics-summary")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "total_opportunities_analyzed" in data
            assert "average_market_size" in data
            assert "trending_ai_categories" in data
            assert "average_roi_projection" in data
            assert "market_readiness_distribution" in data
            assert "business_model_preferences" in data
            assert "generated_at" in data
            
            # Validate structure
            assert isinstance(data["trending_ai_categories"], list)
            assert isinstance(data["market_readiness_distribution"], dict)
            assert isinstance(data["business_model_preferences"], dict)


class TestHealthCheckEndpoints:
    """Test health check API endpoints."""
    
    def test_business_intelligence_health_check(self, client):
        """Test business intelligence health check endpoint."""
        response = client.get("/api/v1/business-intelligence/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "business_intelligence_service" in data
        assert "advanced_roi_service" in data
        assert "timestamp" in data


class TestComprehensiveReportEndpoints:
    """Test comprehensive business intelligence report endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_comprehensive_report_success(self, client, sample_opportunity, mock_auth_user, mock_db_session):
        """Test successful comprehensive business intelligence report generation."""
        sample_report = BusinessIntelligenceReport(
            report_id="bi_report_test-opp-bi-api",
            opportunity_id=str(sample_opportunity.id),
            generated_at=datetime.utcnow(),
            market_analysis=sample_market_analysis,
            trend_forecast=MagicMock(),
            roi_projection=MagicMock(),
            competitive_intelligence=MagicMock(),
            executive_summary={"opportunity_overview": "High-potential AI opportunity"},
            strategic_recommendations=["Focus on enterprise market", "Build partnerships"],
            implementation_roadmap=[{"phase": "Phase 1", "duration": "3 months"}],
            key_metrics={"market_attractiveness": 8.5, "overall_score": 7.8}
        )
        
        with patch('api.routers.business_intelligence.get_current_user', return_value=mock_auth_user), \
             patch('api.routers.business_intelligence.get_db_session', return_value=mock_db_session), \
             patch('shared.services.business_intelligence_service.business_intelligence_service') as mock_service:
            
            # Setup mocks
            mock_service.generate_comprehensive_report.return_value = sample_report
            
            response = client.get(f"/api/v1/business-intelligence/opportunities/{sample_opportunity.id}/comprehensive-report")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "report" in data
            assert "summary" in data
            
            summary = data["summary"]
            assert summary["market_attractiveness"] == 8.5
            assert summary["overall_score"] == 7.8


class TestErrorHandling:
    """Test error handling in business intelligence endpoints."""
    
    @pytest.mark.asyncio
    async def test_internal_server_error_handling(self, client, mock_auth_user, mock_db_session):
        """Test internal server error handling."""
        with patch('api.routers.business_intelligence.get_current_user', return_value=mock_auth_user), \
             patch('api.routers.business_intelligence.get_db_session', return_value=mock_db_session), \
             patch('shared.services.business_intelligence_service.business_intelligence_service') as mock_service:
            
            # Setup mock to raise exception
            mock_db_session.get.side_effect = Exception("Database connection failed")
            
            response = client.get("/api/v1/business-intelligence/opportunities/test-id/market-analysis")
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to generate market analysis" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_authentication_required(self, client):
        """Test that authentication is required for all endpoints."""
        endpoints = [
            "/api/v1/business-intelligence/opportunities/test-id/market-analysis",
            "/api/v1/business-intelligence/opportunities/test-id/trend-forecast",
            "/api/v1/business-intelligence/opportunities/test-id/roi-projection",
            "/api/v1/business-intelligence/opportunities/test-id/competitive-intelligence",
            "/api/v1/business-intelligence/opportunities/test-id/comprehensive-report",
            "/api/v1/business-intelligence/opportunities/test-id/business-model-recommendation",
            "/api/v1/business-intelligence/opportunities/test-id/valuation",
            "/api/v1/business-intelligence/dashboard/analytics-summary"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED


if __name__ == "__main__":
    pytest.main([__file__])