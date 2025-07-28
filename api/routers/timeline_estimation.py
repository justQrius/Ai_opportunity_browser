"""
Timeline Estimation API endpoints.

Provides endpoints for generating development timeline estimates
and resource requirement analysis for AI opportunities.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from shared.database import get_db
from shared.models.opportunity import Opportunity
from shared.services.timeline_estimation_service import (
    timeline_estimation_service,
    EstimationMethod,
    TimelineEstimate
)
from shared.services.technical_roadmap_service import technical_roadmap_service
from shared.services.business_intelligence_service import business_intelligence_service
from shared.auth import get_current_user
from shared.models.user import User

router = APIRouter(prefix="/timeline", tags=["timeline-estimation"])


class TimelineEstimationRequest(BaseModel):
    """Request model for timeline estimation."""
    opportunity_id: str = Field(..., description="ID of the opportunity to estimate")
    estimation_method: EstimationMethod = Field(
        EstimationMethod.EXPERT_JUDGMENT,
        description="Estimation method to use"
    )
    include_monte_carlo: bool = Field(
        False,
        description="Whether to include Monte Carlo simulation"
    )


class TimelineEstimationResponse(BaseModel):
    """Response model for timeline estimation."""
    estimate_id: str
    opportunity_id: str
    estimation_method: str
    total_duration_days: int
    confidence_level: float
    estimated_cost_total: float
    estimated_cost_monthly: float
    team_size: int
    critical_path_tasks: int
    timeline_risks_count: int
    monte_carlo_mean_days: Optional[float] = None
    monte_carlo_confidence_90: Optional[str] = None


@router.post("/estimate", response_model=TimelineEstimationResponse)
async def generate_timeline_estimate(
    request: TimelineEstimationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a comprehensive timeline estimate for an opportunity.
    
    This endpoint creates detailed development timeline estimates including:
    - Task breakdown and effort estimation
    - Resource requirement analysis
    - Risk assessment and mitigation
    - Critical path analysis
    - Optional Monte Carlo simulation
    
    Args:
        request: Timeline estimation request parameters
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TimelineEstimationResponse: Comprehensive timeline estimate
        
    Raises:
        HTTPException: If opportunity not found or estimation fails
    """
    # Get opportunity
    opportunity = await db.get(Opportunity, request.opportunity_id)
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    
    try:
        # Generate technical roadmap first
        technical_roadmap = await technical_roadmap_service.generate_technical_roadmap(
            db, opportunity
        )
        
        # Get market analysis for context
        market_analysis = None
        try:
            market_analysis = await business_intelligence_service.analyze_market_opportunity(
                db, opportunity
            )
        except Exception:
            # Market analysis is optional, continue without it
            pass
        
        # Use Monte Carlo if requested or if method is Monte Carlo
        estimation_method = request.estimation_method
        if request.include_monte_carlo:
            estimation_method = EstimationMethod.MONTE_CARLO
        
        # Generate timeline estimate
        timeline_estimate = await timeline_estimation_service.generate_timeline_estimate(
            db=db,
            opportunity=opportunity,
            technical_roadmap=technical_roadmap,
            market_analysis=market_analysis,
            estimation_method=estimation_method
        )
        
        # Extract Monte Carlo data if available
        monte_carlo_mean = None
        monte_carlo_confidence_90 = None
        if timeline_estimate.monte_carlo_simulation:
            mc = timeline_estimate.monte_carlo_simulation
            monte_carlo_mean = mc.mean_duration_days
            confidence_90 = mc.confidence_intervals.get("90%")
            if confidence_90:
                monte_carlo_confidence_90 = f"{confidence_90[0]:.1f}-{confidence_90[1]:.1f} days"
        
        return TimelineEstimationResponse(
            estimate_id=timeline_estimate.estimate_id,
            opportunity_id=timeline_estimate.opportunity_id,
            estimation_method=timeline_estimate.estimation_method.value,
            total_duration_days=timeline_estimate.total_duration_days,
            confidence_level=timeline_estimate.confidence_level,
            estimated_cost_total=timeline_estimate.resource_allocation.estimated_cost_total,
            estimated_cost_monthly=timeline_estimate.resource_allocation.estimated_cost_monthly,
            team_size=len(timeline_estimate.resource_allocation.team_composition),
            critical_path_tasks=len(timeline_estimate.critical_path),
            timeline_risks_count=len(timeline_estimate.timeline_risks),
            monte_carlo_mean_days=monte_carlo_mean,
            monte_carlo_confidence_90=monte_carlo_confidence_90
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate timeline estimate: {str(e)}"
        )


@router.get("/methods")
async def get_estimation_methods():
    """
    Get available timeline estimation methods.
    
    Returns:
        Dict: Available estimation methods with descriptions
    """
    return {
        "methods": [
            {
                "value": EstimationMethod.EXPERT_JUDGMENT.value,
                "name": "Expert Judgment",
                "description": "Traditional expert-based estimation using industry experience",
                "accuracy": "Medium",
                "speed": "Fast"
            },
            {
                "value": EstimationMethod.FUNCTION_POINT.value,
                "name": "Function Point Analysis",
                "description": "Structured estimation based on functional complexity",
                "accuracy": "High",
                "speed": "Medium"
            },
            {
                "value": EstimationMethod.STORY_POINT.value,
                "name": "Story Point Estimation",
                "description": "Agile-based relative estimation using Fibonacci sequence",
                "accuracy": "Medium",
                "speed": "Fast"
            },
            {
                "value": EstimationMethod.HISTORICAL_DATA.value,
                "name": "Historical Data Analysis",
                "description": "Data-driven estimation based on past project performance",
                "accuracy": "High",
                "speed": "Medium"
            },
            {
                "value": EstimationMethod.MONTE_CARLO.value,
                "name": "Monte Carlo Simulation",
                "description": "Probabilistic estimation with risk analysis and confidence intervals",
                "accuracy": "Very High",
                "speed": "Slow"
            },
            {
                "value": EstimationMethod.PARAMETRIC.value,
                "name": "Parametric Estimation",
                "description": "Mathematical model-based estimation using project parameters",
                "accuracy": "High",
                "speed": "Medium"
            }
        ]
    }


@router.get("/estimate/{estimate_id}")
async def get_timeline_estimate(
    estimate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed timeline estimate by ID.
    
    Note: This is a placeholder endpoint. In a full implementation,
    timeline estimates would be stored in the database for retrieval.
    
    Args:
        estimate_id: Timeline estimate ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dict: Detailed timeline estimate information
    """
    # In a full implementation, this would retrieve from database
    # For now, return a placeholder response
    return {
        "message": "Timeline estimate retrieval not yet implemented",
        "estimate_id": estimate_id,
        "note": "Timeline estimates are currently generated on-demand only"
    }


@router.get("/resource-rates")
async def get_resource_rates():
    """
    Get current resource hourly rates by role and skill level.
    
    Returns:
        Dict: Resource rates by role and skill level
    """
    return {
        "resource_rates": {
            resource_type.value: rates
            for resource_type, rates in timeline_estimation_service.resource_rates.items()
        },
        "currency": "USD",
        "note": "Rates are estimates based on industry averages and may vary by location and market conditions"
    }