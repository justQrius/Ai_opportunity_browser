"""
Business Intelligence API endpoints.

Provides comprehensive business intelligence and advanced ROI projection capabilities
including market analysis, trend forecasting, competitive intelligence, and
sophisticated financial modeling with Monte Carlo simulation.

Supports Phase 7 Business Intelligence requirements.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db_session
from shared.auth import get_current_user, require_roles
from shared.models.user import User
from shared.models.opportunity import Opportunity
from shared.models.market_signal import MarketSignal
from shared.services.business_intelligence_service import (
    business_intelligence_service,
    BusinessIntelligenceReport,
    MarketAnalysisResult,
    TrendForecast,
    ROIProjection,
    CompetitiveIntelligence
)
from shared.services.advanced_roi_service import (
    advanced_roi_service,
    AdvancedROIAnalysis,
    InvestmentScenario,
    BusinessModelRecommendation,
    MonteCarloResult
)
from shared.services.technical_roadmap_service import (
    technical_roadmap_service,
    TechnicalRoadmap,
    TechnologyRecommendation,
    ArchitectureRecommendation,
    ImplementationPhaseDetail,
    ComplexityLevel,
    TechnologyCategory
)
from shared.services.timeline_estimation_service import (
    timeline_estimation_service,
    TimelineEstimate,
    EstimationMethod,
    ResourceAllocation,
    TimelineRisk,
    MonteCarloSimulation
)
from shared.schemas.base import PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/business-intelligence", tags=["Business Intelligence"])


@router.get("/opportunities/{opportunity_id}/market-analysis", response_model=Dict[str, Any])
async def get_market_analysis(
    opportunity_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate comprehensive market analysis for an opportunity.
    
    Provides market sizing (TAM/SAM/SOM), growth analysis, key players identification,
    market trends analysis, and risk assessment.
    """
    try:
        # Fetch opportunity
        opportunity = await db.get(Opportunity, opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )
        
        # Get related market signals
        market_signals = await business_intelligence_service._get_related_market_signals(db, opportunity_id)
        
        # Generate market analysis
        market_analysis = await business_intelligence_service.generate_market_analysis(
            db, opportunity, market_signals
        )
        
        logger.info(f"Generated market analysis for opportunity {opportunity_id} by user {current_user.id}")
        
        return {
            "market_analysis": market_analysis.to_dict(),
            "generated_at": datetime.utcnow().isoformat(),
            "opportunity_id": opportunity_id
        }
        
    except Exception as e:
        logger.error(f"Error generating market analysis for opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate market analysis"
        )


@router.get("/opportunities/{opportunity_id}/trend-forecast", response_model=Dict[str, Any])
async def get_trend_forecast(
    opportunity_id: str,
    forecast_horizon: int = Query(365, description="Forecast horizon in days"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate trend forecasting analysis for an opportunity.
    
    Provides predictive analytics with confidence intervals, trajectory analysis,
    and opportunity window identification.
    """
    try:
        # Validate forecast horizon
        if forecast_horizon < 30 or forecast_horizon > 1825:  # 30 days to 5 years
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Forecast horizon must be between 30 and 1825 days"
            )
        
        # Fetch opportunity
        opportunity = await db.get(Opportunity, opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )
        
        # Get related market signals
        market_signals = await business_intelligence_service._get_related_market_signals(db, opportunity_id)
        
        # Generate trend forecast
        trend_forecast = await business_intelligence_service.generate_trend_forecast(
            db, opportunity, market_signals, forecast_horizon
        )
        
        logger.info(f"Generated trend forecast for opportunity {opportunity_id} with {forecast_horizon} day horizon")
        
        return {
            "trend_forecast": trend_forecast.to_dict(),
            "forecast_horizon_days": forecast_horizon,
            "generated_at": datetime.utcnow().isoformat(),
            "opportunity_id": opportunity_id
        }
        
    except Exception as e:
        logger.error(f"Error generating trend forecast for opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate trend forecast"
        )


@router.get("/opportunities/{opportunity_id}/roi-projection", response_model=Dict[str, Any])
async def get_roi_projection(
    opportunity_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate ROI projections and investment analysis.
    
    Provides investment scenarios, revenue projections, cost breakdown,
    break-even analysis, and sensitivity analysis.
    """
    try:
        # Fetch opportunity
        opportunity = await db.get(Opportunity, opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )
        
        # Get market signals and generate market analysis first
        market_signals = await business_intelligence_service._get_related_market_signals(db, opportunity_id)
        market_analysis = await business_intelligence_service.generate_market_analysis(
            db, opportunity, market_signals
        )
        
        # Generate ROI projection
        roi_projection = await business_intelligence_service.generate_roi_projection(
            db, opportunity, market_analysis
        )
        
        logger.info(f"Generated ROI projection for opportunity {opportunity_id}")
        
        return {
            "roi_projection": roi_projection.to_dict(),
            "market_analysis_summary": {
                "tam": market_analysis.total_addressable_market,
                "sam": market_analysis.serviceable_addressable_market,
                "som": market_analysis.serviceable_obtainable_market,
                "growth_rate": market_analysis.market_growth_rate
            },
            "generated_at": datetime.utcnow().isoformat(),
            "opportunity_id": opportunity_id
        }
        
    except Exception as e:
        logger.error(f"Error generating ROI projection for opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate ROI projection"
        )


@router.get("/opportunities/{opportunity_id}/competitive-intelligence", response_model=Dict[str, Any])
async def get_competitive_intelligence(
    opportunity_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate competitive landscape analysis.
    
    Provides competitor identification, market positioning analysis,
    strategic recommendations, and differentiation opportunities.
    """
    try:
        # Fetch opportunity
        opportunity = await db.get(Opportunity, opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )
        
        # Get related market signals
        market_signals = await business_intelligence_service._get_related_market_signals(db, opportunity_id)
        
        # Generate competitive intelligence
        competitive_intelligence = await business_intelligence_service.generate_competitive_intelligence(
            db, opportunity, market_signals
        )
        
        logger.info(f"Generated competitive intelligence for opportunity {opportunity_id}")
        
        return {
            "competitive_intelligence": competitive_intelligence.to_dict(),
            "generated_at": datetime.utcnow().isoformat(),
            "opportunity_id": opportunity_id
        }
        
    except Exception as e:
        logger.error(f"Error generating competitive intelligence for opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate competitive intelligence"
        )


@router.get("/opportunities/{opportunity_id}/comprehensive-report", response_model=Dict[str, Any])
async def get_comprehensive_business_intelligence_report(
    opportunity_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate comprehensive business intelligence report.
    
    Provides complete analysis including market analysis, trend forecast,
    ROI projection, competitive intelligence, executive summary,
    and strategic recommendations.
    """
    try:
        # Generate comprehensive report
        report = await business_intelligence_service.generate_comprehensive_report(
            db, opportunity_id
        )
        
        logger.info(f"Generated comprehensive BI report for opportunity {opportunity_id}")
        
        return {
            "report": report.to_dict(),
            "summary": {
                "market_attractiveness": report.key_metrics.get("market_attractiveness", 0),
                "competitive_advantage": report.key_metrics.get("competitive_advantage", 0),
                "financial_viability": report.key_metrics.get("financial_viability", 0),
                "overall_score": report.key_metrics.get("overall_score", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating comprehensive BI report for opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate comprehensive business intelligence report"
        )


@router.post("/opportunities/{opportunity_id}/advanced-roi-analysis", response_model=Dict[str, Any])
async def generate_advanced_roi_analysis(
    opportunity_id: str,
    custom_parameters: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate advanced ROI analysis with Monte Carlo simulation.
    
    Provides sophisticated investment analysis including detailed cash flow projections,
    Monte Carlo risk simulation, business model recommendations, and valuation analysis.
    
    Requires premium access or specific user roles.
    """
    try:
        # Check user permissions for advanced features
        if not current_user.is_premium and "analyst" not in (current_user.roles or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Advanced ROI analysis requires premium access or analyst role"
            )
        
        # Fetch opportunity
        opportunity = await db.get(Opportunity, opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )
        
        # Generate prerequisite analyses
        market_signals = await business_intelligence_service._get_related_market_signals(db, opportunity_id)
        market_analysis = await business_intelligence_service.generate_market_analysis(
            db, opportunity, market_signals
        )
        trend_forecast = await business_intelligence_service.generate_trend_forecast(
            db, opportunity, market_signals
        )
        
        # Generate advanced ROI analysis
        advanced_analysis = await advanced_roi_service.generate_advanced_roi_analysis(
            db, opportunity, market_analysis, trend_forecast, custom_parameters
        )
        
        logger.info(f"Generated advanced ROI analysis for opportunity {opportunity_id} by user {current_user.id}")
        
        return {
            "advanced_analysis": advanced_analysis.to_dict(),
            "executive_summary": {
                "recommended_business_model": advanced_analysis.business_model_recommendation.recommended_model.value,
                "expected_roi": advanced_analysis.key_metrics_dashboard.get("expected_roi", 0),
                "break_even_probability": advanced_analysis.monte_carlo_results.break_even_probability,
                "capital_efficiency": advanced_analysis.key_metrics_dashboard.get("capital_efficiency", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating advanced ROI analysis for opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate advanced ROI analysis"
        )


@router.get("/opportunities/{opportunity_id}/business-model-recommendation", response_model=Dict[str, Any])
async def get_business_model_recommendation(
    opportunity_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get business model recommendation for an opportunity.
    
    Analyzes opportunity characteristics and market conditions to recommend
    optimal business model with reasoning and implementation guidance.
    """
    try:
        # Fetch opportunity
        opportunity = await db.get(Opportunity, opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )
        
        # Generate market analysis and basic projections for recommendation
        market_signals = await business_intelligence_service._get_related_market_signals(db, opportunity_id)
        market_analysis = await business_intelligence_service.generate_market_analysis(
            db, opportunity, market_signals
        )
        
        # Generate basic cash flows for recommendation engine
        scenarios = await advanced_roi_service._generate_investment_scenarios(
            opportunity, market_analysis, None
        )
        revenue_models = await advanced_roi_service._create_revenue_models(
            opportunity, market_analysis, None
        )
        cost_structures = await advanced_roi_service._build_cost_structures(
            opportunity, market_analysis, scenarios
        )
        cash_flows = await advanced_roi_service._generate_cash_flow_projections(
            scenarios, revenue_models, cost_structures
        )
        
        # Get business model recommendation
        recommendation = await advanced_roi_service._recommend_business_model(
            opportunity, market_analysis, cash_flows
        )
        
        logger.info(f"Generated business model recommendation for opportunity {opportunity_id}")
        
        return {
            "recommendation": recommendation.to_dict(),
            "analysis_date": datetime.utcnow().isoformat(),
            "opportunity_id": opportunity_id
        }
        
    except Exception as e:
        logger.error(f"Error generating business model recommendation for opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate business model recommendation"
        )


@router.post("/opportunities/{opportunity_id}/monte-carlo-simulation", response_model=Dict[str, Any])
async def run_monte_carlo_simulation(
    opportunity_id: str,
    iterations: int = Query(10000, description="Number of simulation iterations"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_roles(["analyst", "admin"]))
):
    """
    Run Monte Carlo simulation for risk analysis.
    
    Performs sophisticated risk modeling using Monte Carlo simulation
    to provide probability distributions for key financial metrics.
    
    Requires analyst or admin role.
    """
    try:
        # Validate iterations parameter
        if iterations < 1000 or iterations > 100000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Iterations must be between 1,000 and 100,000"
            )
        
        # Fetch opportunity
        opportunity = await db.get(Opportunity, opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )
        
        # Generate prerequisite data
        market_signals = await business_intelligence_service._get_related_market_signals(db, opportunity_id)
        market_analysis = await business_intelligence_service.generate_market_analysis(
            db, opportunity, market_signals
        )
        
        scenarios = await advanced_roi_service._generate_investment_scenarios(
            opportunity, market_analysis, None
        )
        revenue_models = await advanced_roi_service._create_revenue_models(
            opportunity, market_analysis, None
        )
        cost_structures = await advanced_roi_service._build_cost_structures(
            opportunity, market_analysis, scenarios
        )
        
        # Run Monte Carlo simulation
        monte_carlo_results = await advanced_roi_service._run_monte_carlo_simulation(
            scenarios, revenue_models, cost_structures, iterations
        )
        
        logger.info(f"Completed Monte Carlo simulation for opportunity {opportunity_id} with {iterations} iterations")
        
        return {
            "simulation_results": monte_carlo_results.to_dict(),
            "parameters": {
                "iterations": iterations,
                "opportunity_id": opportunity_id,
                "simulation_date": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error running Monte Carlo simulation for opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run Monte Carlo simulation"
        )


@router.get("/opportunities/{opportunity_id}/valuation", response_model=Dict[str, Any])
async def get_valuation_analysis(
    opportunity_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive valuation analysis for an opportunity.
    
    Provides multiple valuation methodologies including revenue multiples,
    DCF analysis, and market comparables.
    """
    try:
        # Fetch opportunity
        opportunity = await db.get(Opportunity, opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )
        
        # Generate prerequisite analyses
        market_signals = await business_intelligence_service._get_related_market_signals(db, opportunity_id)
        market_analysis = await business_intelligence_service.generate_market_analysis(
            db, opportunity, market_signals
        )
        trend_forecast = await business_intelligence_service.generate_trend_forecast(
            db, opportunity, market_signals
        )
        
        # Generate cash flows for valuation
        scenarios = await advanced_roi_service._generate_investment_scenarios(
            opportunity, market_analysis, None
        )
        revenue_models = await advanced_roi_service._create_revenue_models(
            opportunity, market_analysis, trend_forecast
        )
        cost_structures = await advanced_roi_service._build_cost_structures(
            opportunity, market_analysis, scenarios
        )
        cash_flows = await advanced_roi_service._generate_cash_flow_projections(
            scenarios, revenue_models, cost_structures
        )
        
        # Perform valuation analysis
        valuation = await advanced_roi_service._perform_valuation_analysis(
            cash_flows, market_analysis, trend_forecast
        )
        
        logger.info(f"Generated valuation analysis for opportunity {opportunity_id}")
        
        return {
            "valuation_analysis": valuation,
            "cash_flow_summary": {
                "year_1_revenue": cash_flows[list(cash_flows.keys())[1]].revenue[11],
                "year_5_revenue": cash_flows[list(cash_flows.keys())[1]].revenue[59],
                "total_investment": scenarios[1].initial_capital + scenarios[1].working_capital
            },
            "generated_at": datetime.utcnow().isoformat(),
            "opportunity_id": opportunity_id
        }
        
    except Exception as e:
        logger.error(f"Error generating valuation analysis for opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate valuation analysis"
        )


@router.get("/dashboard/analytics-summary", response_model=Dict[str, Any])
async def get_analytics_dashboard_summary(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get analytics dashboard summary with key business intelligence metrics.
    
    Provides high-level overview of business intelligence activities and insights.
    """
    try:
        # This would typically aggregate data across multiple opportunities
        # For now, return a summary structure
        
        summary = {
            "total_opportunities_analyzed": 42,  # Would query from database
            "average_market_size": 15000000,     # Average SAM
            "high_potential_opportunities": 8,    # Opportunities with high BI scores
            "trending_ai_categories": [
                {"category": "NLP", "growth": 25.5},
                {"category": "Computer Vision", "growth": 18.2},
                {"category": "ML/AI", "growth": 22.1}
            ],
            "average_roi_projection": 245.5,     # Average 5-year ROI %
            "market_readiness_distribution": {
                "emerging": 35,
                "growth": 45,
                "mature": 15,
                "declining": 5
            },
            "business_model_preferences": {
                "saas": 60,
                "api_service": 25,
                "platform": 10,
                "other": 5
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Generated analytics dashboard summary for user {current_user.id}")
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating analytics dashboard summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate analytics dashboard summary"
        )


@router.get("/opportunities/{opportunity_id}/technical-roadmap", response_model=Dict[str, Any])
async def get_technical_roadmap(
    opportunity_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate technical roadmap with architecture recommendations and implementation guidance.
    
    Provides comprehensive technical implementation plan including:
    - Architecture pattern recommendations
    - Technology stack suggestions
    - Implementation phases with timelines
    - Team size and effort estimates
    - Technical risk assessment
    """
    try:
        # Fetch opportunity
        opportunity = await db.get(Opportunity, opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )
        
        # Generate market analysis for context
        market_signals = await business_intelligence_service._get_related_market_signals(db, opportunity_id)
        market_analysis = await business_intelligence_service.generate_market_analysis(
            db, opportunity, market_signals
        )
        
        # Generate technical roadmap
        technical_roadmap = await technical_roadmap_service.generate_technical_roadmap(
            db, opportunity, market_analysis
        )
        
        logger.info(f"Generated technical roadmap for opportunity {opportunity_id}")
        
        return {
            "technical_roadmap": technical_roadmap.to_dict(),
            "executive_summary": {
                "recommended_architecture": technical_roadmap.architecture_recommendation.pattern.value,
                "estimated_timeline_weeks": technical_roadmap.estimated_timeline_weeks,
                "total_estimated_hours": technical_roadmap.total_estimated_hours,
                "recommended_team_size": technical_roadmap.recommended_team_size,
                "overall_complexity": technical_roadmap.overall_complexity.value,
                "key_technologies": [tech.name for tech in technical_roadmap.technology_stack[:5]]
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating technical roadmap for opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate technical roadmap"
        )


@router.get("/opportunities/{opportunity_id}/architecture-recommendation", response_model=Dict[str, Any])
async def get_architecture_recommendation(
    opportunity_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get architecture pattern recommendation for an opportunity.
    
    Analyzes opportunity requirements and recommends optimal architecture pattern
    with detailed reasoning, advantages, and implementation considerations.
    """
    try:
        # Fetch opportunity
        opportunity = await db.get(Opportunity, opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )
        
        # Analyze AI requirements
        ai_requirements = await technical_roadmap_service._analyze_ai_requirements(opportunity)
        technical_complexity = await technical_roadmap_service._assess_technical_complexity(
            opportunity, ai_requirements
        )
        
        # Generate architecture recommendation
        architecture = await technical_roadmap_service._recommend_architecture(
            opportunity, ai_requirements, technical_complexity, None
        )
        
        logger.info(f"Generated architecture recommendation for opportunity {opportunity_id}")
        
        return {
            "architecture_recommendation": architecture.to_dict(),
            "ai_requirements_analysis": ai_requirements,
            "technical_complexity": technical_complexity.value,
            "analysis_date": datetime.utcnow().isoformat(),
            "opportunity_id": opportunity_id
        }
        
    except Exception as e:
        logger.error(f"Error generating architecture recommendation for opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate architecture recommendation"
        )


@router.get("/opportunities/{opportunity_id}/technology-stack", response_model=Dict[str, Any])
async def get_technology_stack_recommendation(
    opportunity_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get technology stack recommendations for an opportunity.
    
    Provides detailed technology recommendations organized by category
    with reasoning, alternatives, and integration effort estimates.
    """
    try:
        # Fetch opportunity
        opportunity = await db.get(Opportunity, opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )
        
        # Analyze requirements and generate recommendations
        ai_requirements = await technical_roadmap_service._analyze_ai_requirements(opportunity)
        technical_complexity = await technical_roadmap_service._assess_technical_complexity(
            opportunity, ai_requirements
        )
        
        # Get architecture recommendation for context
        architecture = await technical_roadmap_service._recommend_architecture(
            opportunity, ai_requirements, technical_complexity, None
        )
        
        # Generate technology stack
        tech_stack = await technical_roadmap_service._recommend_technology_stack(
            opportunity, ai_requirements, architecture, technical_complexity
        )
        
        # Organize by category
        tech_by_category = {}
        for tech in tech_stack:
            category = tech.category.value
            if category not in tech_by_category:
                tech_by_category[category] = []
            tech_by_category[category].append(tech.to_dict())
        
        logger.info(f"Generated technology stack recommendations for opportunity {opportunity_id}")
        
        return {
            "technology_stack": [tech.to_dict() for tech in tech_stack],
            "technologies_by_category": tech_by_category,
            "stack_summary": {
                "total_technologies": len(tech_stack),
                "complexity_distribution": {
                    level.value: len([t for t in tech_stack if t.complexity == level])
                    for level in [ComplexityLevel.LOW, ComplexityLevel.MEDIUM, ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]
                },
                "primary_ai_framework": next((t.name for t in tech_stack if t.category == TechnologyCategory.AI_FRAMEWORK), "Not specified"),
                "recommended_cloud": next((t.name for t in tech_stack if t.category == TechnologyCategory.CLOUD_PLATFORM), "Not specified")
            },
            "analysis_date": datetime.utcnow().isoformat(),
            "opportunity_id": opportunity_id
        }
        
    except Exception as e:
        logger.error(f"Error generating technology stack for opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate technology stack recommendations"
        )


@router.get("/opportunities/{opportunity_id}/implementation-timeline", response_model=Dict[str, Any])
async def get_implementation_timeline(
    opportunity_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed implementation timeline with phases, deliverables, and resource estimates.
    
    Provides comprehensive project planning information including phases,
    effort estimates, team size recommendations, and risk assessment.
    """
    try:
        # Fetch opportunity
        opportunity = await db.get(Opportunity, opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )
        
        # Generate prerequisites for timeline
        ai_requirements = await technical_roadmap_service._analyze_ai_requirements(opportunity)
        technical_complexity = await technical_roadmap_service._assess_technical_complexity(
            opportunity, ai_requirements
        )
        
        architecture = await technical_roadmap_service._recommend_architecture(
            opportunity, ai_requirements, technical_complexity, None
        )
        
        tech_stack = await technical_roadmap_service._recommend_technology_stack(
            opportunity, ai_requirements, architecture, technical_complexity
        )
        
        # Create implementation phases
        phases = await technical_roadmap_service._create_implementation_phases(
            opportunity, architecture, tech_stack, technical_complexity
        )
        
        # Calculate timeline metrics
        total_weeks = sum(phase.duration_weeks for phase in phases)
        total_hours = sum(phase.estimated_effort_hours for phase in phases)
        team_size = await technical_roadmap_service._recommend_team_size(
            technical_complexity, total_hours, total_weeks
        )
        
        # Generate timeline visualization data
        timeline_data = []
        current_week = 0
        for phase in phases:
            timeline_data.append({
                "phase": phase.phase.value,
                "name": phase.name,
                "start_week": current_week,
                "end_week": current_week + phase.duration_weeks,
                "duration_weeks": phase.duration_weeks,
                "effort_hours": phase.estimated_effort_hours,
                "team_size": phase.team_size_recommendation,
                "key_deliverables": phase.key_deliverables[:3]  # Top 3 deliverables
            })
            current_week += phase.duration_weeks
        
        logger.info(f"Generated implementation timeline for opportunity {opportunity_id}")
        
        return {
            "implementation_phases": [phase.to_dict() for phase in phases],
            "timeline_visualization": timeline_data,
            "project_summary": {
                "total_duration_weeks": total_weeks,
                "total_effort_hours": total_hours,
                "recommended_team_size": team_size,
                "complexity_level": technical_complexity.value,
                "number_of_phases": len(phases),
                "estimated_monthly_cost": f"${(team_size * 8000):,}"  # Rough estimate: $8k per team member per month
            },
            "critical_path": [
                {"phase": phase.name, "dependencies": phase.dependencies}
                for phase in phases if phase.dependencies
            ],
            "analysis_date": datetime.utcnow().isoformat(),
            "opportunity_id": opportunity_id
        }
        
    except Exception as e:
        logger.error(f"Error generating implementation timeline for opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate implementation timeline"
        )


@router.get("/opportunities/{opportunity_id}/timeline-estimation", response_model=Dict[str, Any])
async def get_timeline_estimation(
    opportunity_id: str,
    estimation_method: str = Query("monte_carlo", description="Estimation method: expert_judgment, function_point, story_point, historical_data, monte_carlo"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate comprehensive timeline estimation with resource analysis and risk assessment.
    
    Provides advanced timeline estimation including:
    - Detailed task breakdown and estimates
    - Resource requirement analysis with team composition
    - Timeline risk assessment and mitigation strategies
    - Monte Carlo simulation for confidence intervals
    - Critical path analysis
    - Cost analysis and budget projections
    """
    try:
        
        # Validate estimation method
        method_mapping = {
            "expert_judgment": EstimationMethod.EXPERT_JUDGMENT,
            "function_point": EstimationMethod.FUNCTION_POINT,
            "story_point": EstimationMethod.STORY_POINT,
            "historical_data": EstimationMethod.HISTORICAL_DATA,
            "monte_carlo": EstimationMethod.MONTE_CARLO,
            "parametric": EstimationMethod.PARAMETRIC
        }
        
        if estimation_method not in method_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid estimation method. Must be one of: {list(method_mapping.keys())}"
            )
        
        # Fetch opportunity
        opportunity = await db.get(Opportunity, opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )
        
        # Generate technical roadmap first (required dependency)
        market_signals = await business_intelligence_service._get_related_market_signals(db, opportunity_id)
        market_analysis = await business_intelligence_service.generate_market_analysis(
            db, opportunity, market_signals
        )
        
        technical_roadmap = await technical_roadmap_service.generate_technical_roadmap(
            db, opportunity, market_analysis
        )
        
        # Generate comprehensive timeline estimation
        timeline_estimate = await timeline_estimation_service.generate_timeline_estimate(
            db,
            opportunity,
            technical_roadmap,
            market_analysis,
            method_mapping[estimation_method]
        )
        
        logger.info(f"Generated timeline estimation for opportunity {opportunity_id} using {estimation_method} method")
        
        return {
            "timeline_estimate": timeline_estimate.to_dict(),
            "executive_summary": {
                "total_duration_days": timeline_estimate.total_duration_days,
                "total_duration_weeks": round(timeline_estimate.total_duration_days / 7, 1),
                "confidence_level": timeline_estimate.confidence_level,
                "estimation_method": timeline_estimate.estimation_method.value,
                "recommended_team_size": timeline_estimate.resource_allocation.team_composition,
                "total_estimated_cost": timeline_estimate.resource_allocation.estimated_cost_total,
                "monthly_burn_rate": timeline_estimate.resource_allocation.estimated_cost_monthly,
                "critical_path_tasks": len(timeline_estimate.critical_path),
                "identified_risks": len(timeline_estimate.timeline_risks),
                "monte_carlo_confidence": (
                    timeline_estimate.monte_carlo_simulation.confidence_intervals if 
                    timeline_estimate.monte_carlo_simulation else None
                )
            },
            "risk_analysis": {
                "high_risk_count": len([r for r in timeline_estimate.timeline_risks if r.probability > 0.7]),
                "medium_risk_count": len([r for r in timeline_estimate.timeline_risks if 0.3 < r.probability <= 0.7]),
                "low_risk_count": len([r for r in timeline_estimate.timeline_risks if r.probability <= 0.3]),
                "total_risk_impact_days": sum(r.impact_days * r.probability for r in timeline_estimate.timeline_risks),
                "recommended_buffer_days": sum(timeline_estimate.buffer_recommendations.values())
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating timeline estimation for opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate timeline estimation"
        )


@router.get("/opportunities/{opportunity_id}/resource-analysis", response_model=Dict[str, Any])
async def get_resource_analysis(
    opportunity_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate detailed resource requirement analysis for an opportunity.
    
    Provides comprehensive resource planning including:
    - Detailed resource requirements by type and skill level
    - Team composition recommendations
    - Resource allocation timeline
    - Cost analysis and budget planning
    - Resource conflict identification
    - Scaling strategy recommendations
    """
    try:
        
        # Fetch opportunity
        opportunity = await db.get(Opportunity, opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )
        
        # Generate prerequisites
        market_signals = await business_intelligence_service._get_related_market_signals(db, opportunity_id)
        market_analysis = await business_intelligence_service.generate_market_analysis(
            db, opportunity, market_signals
        )
        
        technical_roadmap = await technical_roadmap_service.generate_technical_roadmap(
            db, opportunity, market_analysis
        )
        
        # Generate timeline estimation to get resource analysis
        timeline_estimate = await timeline_estimation_service.generate_timeline_estimate(
            db,
            opportunity,
            technical_roadmap,
            market_analysis,
            EstimationMethod.EXPERT_JUDGMENT  # Use expert judgment for resource analysis
        )
        
        # Extract resource allocation details
        resource_allocation = timeline_estimate.resource_allocation
        
        logger.info(f"Generated resource analysis for opportunity {opportunity_id}")
        
        return {
            "resource_allocation": resource_allocation.to_dict(),
            "resource_summary": {
                "total_team_size": sum(resource_allocation.team_composition.values()),
                "team_composition": {k.value: v for k, v in resource_allocation.team_composition.items()},
                "total_estimated_cost": resource_allocation.estimated_cost_total,
                "monthly_burn_rate": resource_allocation.estimated_cost_monthly,
                "resource_conflicts": len(resource_allocation.resource_conflicts),
                "optimization_opportunities": len(resource_allocation.optimization_recommendations)
            },
            "cost_breakdown": {
                "development_cost": resource_allocation.estimated_cost_total * 0.7,  # Approximate breakdown
                "management_cost": resource_allocation.estimated_cost_total * 0.15,
                "infrastructure_cost": resource_allocation.estimated_cost_total * 0.10,
                "contingency_cost": resource_allocation.estimated_cost_total * 0.05
            },
            "hiring_timeline": await timeline_estimation_service._generate_hiring_timeline(
                resource_allocation.resource_requirements
            ) if hasattr(timeline_estimation_service, '_generate_hiring_timeline') else {},
            "analysis_date": datetime.utcnow().isoformat(),
            "opportunity_id": opportunity_id
        }
        
    except Exception as e:
        logger.error(f"Error generating resource analysis for opportunity {opportunity_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate resource analysis"
        )


# Health check endpoint for business intelligence services
@router.get("/health", response_model=Dict[str, str])
async def business_intelligence_health_check():
    """Health check for business intelligence services."""
    try:
        # Test basic service availability
        test_result = {
            "status": "healthy",
            "business_intelligence_service": "available",
            "advanced_roi_service": "available",
            "technical_roadmap_service": "available",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return test_result
        
    except Exception as e:
        logger.error(f"Business intelligence health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Business intelligence services unavailable"
        )