"""
Recommendations API endpoints for the AI Opportunity Browser.

This module provides REST API endpoints for personalized opportunity recommendations,
user preference learning, and recommendation feedback.

Supports Requirements 6.1.3 (Personalized recommendation engine and user preference learning).
"""

import json
from fastapi import APIRouter, HTTPException, Query, Depends, Body, status
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from shared.schemas import (
    OpportunityRecommendationRequest, OpportunityResponse, APIResponse, PaginatedResponse
)
from shared.schemas.base import PaginationResponse
from shared.services.recommendation_service import recommendation_service
from shared.database import get_db
from api.core.dependencies import get_current_user
from shared.models.user import User
from shared.models.user_interaction import InteractionType
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=PaginatedResponse)
async def get_personalized_recommendations(
    request: OpportunityRecommendationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get personalized opportunity recommendations using advanced ML algorithms.
    
    Supports Requirements 6.1.3 (Personalized recommendation engine and user preference learning).
    
    This endpoint uses a hybrid recommendation system that combines:
    - Collaborative filtering (users with similar preferences)
    - Content-based filtering (matching user preferences)
    - Popularity-based recommendations (trending opportunities)
    - Semantic similarity (AI-powered content matching)
    """
    try:
        # Ensure user can only get their own recommendations or is admin
        if request.user_id != current_user.id and current_user.role.value != "admin":
            logger.warning(
                "User attempted to get recommendations for another user",
                current_user_id=current_user.id,
                requested_user_id=request.user_id
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only get your own recommendations"
            )
        
        # Get personalized recommendations using the enhanced recommendation service
        recommendations = await recommendation_service.get_personalized_recommendations(
            db, request
        )
        
        # Convert to response format
        recommendation_responses = [
            OpportunityResponse.model_validate(opp) for opp in recommendations
        ]
        
        # Create pagination response
        pagination = PaginationResponse.create(
            page=1,
            page_size=request.limit,
            total_count=len(recommendation_responses)
        )
        
        logger.info(
            "Personalized recommendations generated",
            user_id=request.user_id,
            recommendation_count=len(recommendation_responses),
            requested_by=current_user.id,
            algorithm="hybrid"
        )
        
        return PaginatedResponse(
            items=recommendation_responses,
            pagination=pagination,
            total_count=len(recommendation_responses),
            filters_applied={
                "user_id": request.user_id,
                "ai_solution_types": request.ai_solution_types,
                "industries": request.industries,
                "include_viewed": request.include_viewed
            },
            metadata={
                "recommendation_algorithm": "hybrid",
                "includes_preference_learning": True,
                "personalization_enabled": True
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generating personalized recommendations", error=str(e), user_id=request.user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations"
        )


@router.post("/feedback", response_model=APIResponse)
async def record_recommendation_feedback(
    feedback_data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record user feedback on recommendations to improve the system.
    
    Supports Requirements 6.1.3 (User preference learning).
    
    Expected feedback_data format:
    {
        "opportunity_id": "opportunity_uuid",
        "is_relevant": true,
        "feedback_score": 5,
        "feedback_text": "This was very relevant to my interests",
        "recommendation_algorithm": "hybrid",
        "recommendation_score": 0.85,
        "recommendation_rank": 1
    }
    """
    try:
        # Validate required fields
        required_fields = ["opportunity_id", "is_relevant", "recommendation_algorithm", "recommendation_score", "recommendation_rank"]
        for field in required_fields:
            if field not in feedback_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )
        
        # Record the feedback
        feedback = await recommendation_service.record_recommendation_feedback(
            db=db,
            user_id=current_user.id,
            opportunity_id=feedback_data["opportunity_id"],
            is_relevant=feedback_data["is_relevant"],
            feedback_score=feedback_data.get("feedback_score"),
            feedback_text=feedback_data.get("feedback_text"),
            recommendation_algorithm=feedback_data["recommendation_algorithm"],
            recommendation_score=feedback_data["recommendation_score"],
            recommendation_rank=feedback_data["recommendation_rank"]
        )
        
        logger.info(
            "Recommendation feedback recorded",
            user_id=current_user.id,
            opportunity_id=feedback_data["opportunity_id"],
            is_relevant=feedback_data["is_relevant"],
            feedback_score=feedback_data.get("feedback_score")
        )
        
        return APIResponse(
            success=True,
            message="Recommendation feedback recorded successfully",
            data={
                "feedback_id": feedback.id,
                "opportunity_id": feedback.opportunity_id,
                "is_relevant": feedback.is_relevant,
                "feedback_score": feedback.feedback_score
            },
            metadata={
                "recorded_at": feedback.created_at.isoformat(),
                "user_id": current_user.id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error recording recommendation feedback", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record recommendation feedback"
        )


@router.get("/explain/{opportunity_id}", response_model=Dict[str, Any])
async def explain_recommendation(
    opportunity_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Explain why an opportunity was recommended to the user.
    
    Supports Requirements 6.1.3 (Personalized recommendation engine).
    
    Returns detailed explanation of recommendation factors and scoring.
    """
    try:
        # Get recommendation explanation
        explanation = await recommendation_service.explain_recommendation(
            db, current_user.id, opportunity_id
        )
        
        logger.info(
            "Recommendation explanation generated",
            user_id=current_user.id,
            opportunity_id=opportunity_id,
            overall_score=explanation.get("overall_score", 0.0)
        )
        
        return {
            "opportunity_id": opportunity_id,
            "user_id": current_user.id,
            "explanation": explanation,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Error generating recommendation explanation", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendation explanation"
        )


@router.post("/interactions", response_model=APIResponse)
async def record_user_interaction(
    interaction_data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record user interaction for preference learning.
    
    Supports Requirements 6.1.3 (User preference learning).
    
    Expected interaction_data format:
    {
        "interaction_type": "view|click|bookmark|search|filter",
        "opportunity_id": "optional_opportunity_id",
        "search_query": "optional_search_query",
        "filters_applied": {"optional": "filters"},
        "duration_seconds": 30,
        "referrer_source": "search_results"
    }
    """
    try:
        # Validate required fields
        if "interaction_type" not in interaction_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required field: interaction_type"
            )
        
        # Validate interaction type
        try:
            interaction_type = InteractionType(interaction_data["interaction_type"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid interaction_type: {interaction_data['interaction_type']}"
            )
        
        # Record the interaction
        interaction = await recommendation_service.record_interaction(
            db=db,
            user_id=current_user.id,
            interaction_type=interaction_type,
            opportunity_id=interaction_data.get("opportunity_id"),
            search_query=interaction_data.get("search_query"),
            filters_applied=json.dumps(interaction_data.get("filters_applied")) if interaction_data.get("filters_applied") else None,
            duration_seconds=interaction_data.get("duration_seconds"),
            referrer_source=interaction_data.get("referrer_source")
        )
        
        logger.info(
            "User interaction recorded",
            user_id=current_user.id,
            interaction_type=interaction_type.value,
            opportunity_id=interaction_data.get("opportunity_id"),
            engagement_score=interaction.engagement_score
        )
        
        return APIResponse(
            success=True,
            message="User interaction recorded successfully",
            data={
                "interaction_id": interaction.id,
                "interaction_type": interaction.interaction_type.value,
                "engagement_score": interaction.engagement_score,
                "opportunity_id": interaction.opportunity_id
            },
            metadata={
                "recorded_at": interaction.created_at.isoformat(),
                "user_id": current_user.id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error recording user interaction", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record user interaction"
        )


@router.get("/preferences", response_model=Dict[str, Any])
async def get_user_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's learned preferences for recommendations.
    
    Supports Requirements 6.1.3 (User preference learning).
    """
    try:
        # Get user preferences
        preferences = await recommendation_service.get_or_create_user_preferences(
            db, current_user.id
        )
        
        # Parse JSON fields safely
        preferred_ai_types = {}
        preferred_industries = {}
        
        if preferences.preferred_ai_types:
            try:
                preferred_ai_types = json.loads(preferences.preferred_ai_types)
            except json.JSONDecodeError:
                pass
        
        if preferences.preferred_industries:
            try:
                preferred_industries = json.loads(preferences.preferred_industries)
            except json.JSONDecodeError:
                pass
        
        logger.info(
            "User preferences retrieved",
            user_id=current_user.id,
            confidence_score=preferences.confidence_score,
            interaction_count=preferences.interaction_count
        )
        
        return {
            "user_id": current_user.id,
            "preferences": {
                "preferred_ai_types": preferred_ai_types,
                "preferred_industries": preferred_industries,
                "preferred_complexity": preferences.preferred_complexity,
                "preferred_market_size": preferences.preferred_market_size,
                "min_validation_score": preferences.min_validation_score,
                "prefers_trending": preferences.prefers_trending,
                "prefers_new_opportunities": preferences.prefers_new_opportunities,
                "preferred_geographic_scope": preferences.preferred_geographic_scope
            },
            "learning_metadata": {
                "confidence_score": preferences.confidence_score,
                "interaction_count": preferences.interaction_count,
                "last_updated": preferences.last_updated.isoformat()
            },
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Error retrieving user preferences", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user preferences"
        )


@router.post("/preferences/update", response_model=APIResponse)
async def update_user_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update user preferences based on their interaction history.
    
    Supports Requirements 6.1.3 (User preference learning).
    
    This endpoint triggers the preference learning algorithm to analyze
    the user's recent interactions and update their preference profile.
    """
    try:
        # Update preferences from interactions
        updated_preferences = await recommendation_service.update_user_preferences_from_interactions(
            db, current_user.id
        )
        
        if not updated_preferences:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User preferences not found"
            )
        
        logger.info(
            "User preferences updated from interactions",
            user_id=current_user.id,
            confidence_score=updated_preferences.confidence_score,
            interaction_count=updated_preferences.interaction_count
        )
        
        return APIResponse(
            success=True,
            message="User preferences updated successfully",
            data={
                "confidence_score": updated_preferences.confidence_score,
                "interaction_count": updated_preferences.interaction_count,
                "last_updated": updated_preferences.last_updated.isoformat()
            },
            metadata={
                "user_id": current_user.id,
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating user preferences", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user preferences"
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_recommendation_stats(
    timeframe_days: int = Query(30, ge=1, le=365, description="Timeframe in days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get recommendation system statistics for the user.
    
    Supports Requirements 6.1.3 (Personalized recommendation engine).
    
    Returns statistics about recommendation performance, user engagement,
    and preference learning progress.
    """
    try:
        from datetime import timedelta
        from sqlalchemy import select, func, and_
        from shared.models.user_interaction import UserInteraction, RecommendationFeedback
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=timeframe_days)
        
        # Get interaction statistics
        interaction_query = select(
            UserInteraction.interaction_type,
            func.count(UserInteraction.id).label('count'),
            func.avg(UserInteraction.engagement_score).label('avg_engagement')
        ).where(
            and_(
                UserInteraction.user_id == current_user.id,
                UserInteraction.created_at >= start_date
            )
        ).group_by(UserInteraction.interaction_type)
        
        result = await db.execute(interaction_query)
        interaction_stats = {
            row.interaction_type.value: {
                "count": row.count,
                "avg_engagement": float(row.avg_engagement) if row.avg_engagement else 0.0
            }
            for row in result
        }
        
        # Get feedback statistics
        feedback_query = select(
            func.count(RecommendationFeedback.id).label('total_feedback'),
            func.sum(func.cast(RecommendationFeedback.is_relevant, func.Integer())).label('relevant_count'),
            func.avg(RecommendationFeedback.feedback_score).label('avg_score')
        ).where(
            and_(
                RecommendationFeedback.user_id == current_user.id,
                RecommendationFeedback.created_at >= start_date
            )
        )
        
        result = await db.execute(feedback_query)
        feedback_row = result.first()
        
        feedback_stats = {
            "total_feedback": feedback_row.total_feedback or 0,
            "relevant_count": feedback_row.relevant_count or 0,
            "avg_score": float(feedback_row.avg_score) if feedback_row.avg_score else 0.0,
            "relevance_rate": (feedback_row.relevant_count / feedback_row.total_feedback) if feedback_row.total_feedback else 0.0
        }
        
        # Get user preferences for context
        preferences = await recommendation_service.get_or_create_user_preferences(
            db, current_user.id
        )
        
        logger.info(
            "Recommendation statistics retrieved",
            user_id=current_user.id,
            timeframe_days=timeframe_days,
            total_interactions=sum(stat["count"] for stat in interaction_stats.values()),
            total_feedback=feedback_stats["total_feedback"]
        )
        
        return {
            "user_id": current_user.id,
            "timeframe_days": timeframe_days,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "interaction_stats": interaction_stats,
            "feedback_stats": feedback_stats,
            "preference_learning": {
                "confidence_score": preferences.confidence_score,
                "interaction_count": preferences.interaction_count,
                "last_updated": preferences.last_updated.isoformat()
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Error retrieving recommendation statistics", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recommendation statistics"
        )