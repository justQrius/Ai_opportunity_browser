"""API endpoints for user matching and team formation.

Supports Requirements 9.1-9.2 (Marketplace and Networking Features):
- Interest-based user matching endpoints
- Complementary skill identification endpoints
- Team formation recommendations
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.auth import get_current_user
from shared.models.user import User
from shared.services.user_matching_service import user_matching_service, MatchingType
from shared.schemas.user_matching import (
    UserMatchRequest,
    UserMatchResponse,
    UserMatchListResponse,
    SkillAnalysisRequest,
    SkillAnalysisResponse,
    TeamFormationRequest,
    TeamFormationResponse,
    MatchFeedback,
    MatchingPreferences,
    MatchingPreferencesUpdate,
    MatchingAnalytics
)
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/matching", tags=["User Matching"])


@router.get("/interest-based", response_model=UserMatchListResponse)
async def find_interest_based_matches(
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of matches"),
    min_match_score: float = Query(default=0.3, ge=0.0, le=1.0, description="Minimum match score"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Find users with similar interests for potential collaboration.
    
    Supports Requirement 9.1 (Interest-based matching).
    """
    try:
        matches = await user_matching_service.find_interest_based_matches(
            db=db,
            user_id=current_user.id,
            limit=limit,
            min_match_score=min_match_score
        )
        
        match_responses = [
            UserMatchResponse(
                user_id=match.user_id,
                username=match.username,
                full_name=match.full_name,
                avatar_url=match.avatar_url,
                match_score=match.match_score,
                match_type=match.match_type,
                match_reasons=match.match_reasons,
                common_interests=match.common_interests,
                complementary_skills=match.complementary_skills,
                expertise_domains=match.expertise_domains,
                reputation_score=match.reputation_score,
                compatibility_factors=match.compatibility_factors
            )
            for match in matches
        ]
        
        logger.info(
            "Interest-based matches retrieved",
            user_id=current_user.id,
            match_count=len(match_responses)
        )
        
        return UserMatchListResponse(
            matches=match_responses,
            total_count=len(match_responses),
            algorithm_used="interest_based",
            user_id=current_user.id
        )
        
    except Exception as e:
        logger.error("Failed to find interest-based matches", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find interest-based matches"
        )


@router.get("/skill-complementary", response_model=UserMatchListResponse)
async def find_skill_complementary_matches(
    opportunity_id: Optional[str] = Query(None, description="Opportunity context for skill matching"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of matches"),
    min_match_score: float = Query(default=0.4, ge=0.0, le=1.0, description="Minimum match score"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Find users with complementary skills for team formation.
    
    Supports Requirement 9.2 (Complementary skill identification).
    """
    try:
        matches = await user_matching_service.find_complementary_skill_matches(
            db=db,
            user_id=current_user.id,
            opportunity_id=opportunity_id,
            limit=limit,
            min_match_score=min_match_score
        )
        
        match_responses = [
            UserMatchResponse(
                user_id=match.user_id,
                username=match.username,
                full_name=match.full_name,
                avatar_url=match.avatar_url,
                match_score=match.match_score,
                match_type=match.match_type,
                match_reasons=match.match_reasons,
                common_interests=match.common_interests,
                complementary_skills=match.complementary_skills,
                expertise_domains=match.expertise_domains,
                reputation_score=match.reputation_score,
                compatibility_factors=match.compatibility_factors
            )
            for match in matches
        ]
        
        logger.info(
            "Skill-complementary matches retrieved",
            user_id=current_user.id,
            opportunity_id=opportunity_id,
            match_count=len(match_responses)
        )
        
        return UserMatchListResponse(
            matches=match_responses,
            total_count=len(match_responses),
            algorithm_used="skill_complementary",
            user_id=current_user.id
        )
        
    except Exception as e:
        logger.error(
            "Failed to find skill-complementary matches", 
            error=str(e), 
            user_id=current_user.id,
            opportunity_id=opportunity_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find skill-complementary matches"
        )


@router.get("/hybrid", response_model=UserMatchListResponse)
async def find_hybrid_matches(
    opportunity_id: Optional[str] = Query(None, description="Opportunity context"),
    limit: int = Query(default=15, ge=1, le=50, description="Maximum number of matches"),
    min_match_score: float = Query(default=0.35, ge=0.0, le=1.0, description="Minimum match score"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Find matches using both interest and skill complementarity algorithms.
    
    Combines Requirements 9.1 and 9.2 for comprehensive matching.
    """
    try:
        matches = await user_matching_service.find_hybrid_matches(
            db=db,
            user_id=current_user.id,
            opportunity_id=opportunity_id,
            limit=limit,
            min_match_score=min_match_score
        )
        
        match_responses = [
            UserMatchResponse(
                user_id=match.user_id,
                username=match.username,
                full_name=match.full_name,
                avatar_url=match.avatar_url,
                match_score=match.match_score,
                match_type=match.match_type,
                match_reasons=match.match_reasons,
                common_interests=match.common_interests,
                complementary_skills=match.complementary_skills,
                expertise_domains=match.expertise_domains,
                reputation_score=match.reputation_score,
                compatibility_factors=match.compatibility_factors
            )
            for match in matches
        ]
        
        logger.info(
            "Hybrid matches retrieved",
            user_id=current_user.id,
            opportunity_id=opportunity_id,
            match_count=len(match_responses)
        )
        
        return UserMatchListResponse(
            matches=match_responses,
            total_count=len(match_responses),
            algorithm_used="hybrid",
            user_id=current_user.id
        )
        
    except Exception as e:
        logger.error(
            "Failed to find hybrid matches", 
            error=str(e), 
            user_id=current_user.id,
            opportunity_id=opportunity_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find hybrid matches"
        )


@router.post("/find", response_model=UserMatchListResponse)
async def find_matches_with_request(
    request: UserMatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Find matches using a detailed request specification.
    
    Supports flexible matching with custom parameters.
    """
    # Validate that user is requesting matches for themselves or has permission
    if request.user_id != current_user.id and current_user.role.value not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only request matches for yourself"
        )
    
    try:
        if request.match_type == MatchingType.INTEREST_BASED:
            matches = await user_matching_service.find_interest_based_matches(
                db=db,
                user_id=request.user_id,
                limit=request.limit,
                min_match_score=request.min_match_score
            )
        elif request.match_type == MatchingType.SKILL_COMPLEMENTARY:
            matches = await user_matching_service.find_complementary_skill_matches(
                db=db,
                user_id=request.user_id,
                opportunity_id=request.opportunity_id,
                limit=request.limit,
                min_match_score=request.min_match_score
            )
        elif request.match_type == MatchingType.HYBRID:
            matches = await user_matching_service.find_hybrid_matches(
                db=db,
                user_id=request.user_id,
                opportunity_id=request.opportunity_id,
                limit=request.limit,
                min_match_score=request.min_match_score
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported match type: {request.match_type}"
            )
        
        match_responses = [
            UserMatchResponse(
                user_id=match.user_id,
                username=match.username,
                full_name=match.full_name,
                avatar_url=match.avatar_url,
                match_score=match.match_score,
                match_type=match.match_type,
                match_reasons=match.match_reasons if request.include_reasons else [],
                common_interests=match.common_interests,
                complementary_skills=match.complementary_skills,
                expertise_domains=match.expertise_domains,
                reputation_score=match.reputation_score,
                compatibility_factors=match.compatibility_factors
            )
            for match in matches
        ]
        
        logger.info(
            "Custom matches retrieved",
            user_id=request.user_id,
            match_type=request.match_type,
            match_count=len(match_responses)
        )
        
        return UserMatchListResponse(
            matches=match_responses,
            total_count=len(match_responses),
            algorithm_used=request.match_type.value,
            user_id=request.user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to find custom matches", 
            error=str(e), 
            user_id=request.user_id,
            match_type=request.match_type
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find matches"
        )


@router.get("/skill-analysis", response_model=SkillAnalysisResponse)
async def analyze_user_skills(
    opportunity_id: Optional[str] = Query(None, description="Opportunity context for analysis"),
    include_gaps: bool = Query(default=True, description="Include skill gap analysis"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Analyze user's current skills and identify gaps.
    
    Supports skill-based matching by providing skill analysis.
    """
    try:
        # Extract user skills
        user_skills = await user_matching_service._extract_user_skills(db, current_user.id)
        
        # Identify skill gaps if requested
        skill_gaps = []
        if include_gaps:
            gaps = await user_matching_service._identify_skill_gaps(
                db, current_user.id, opportunity_id
            )
            skill_gaps = [
                {
                    "skill_category": gap.skill_category,
                    "skill_name": gap.skill_name,
                    "importance_score": gap.importance_score,
                    "gap_severity": gap.gap_severity
                }
                for gap in gaps
            ]
        
        # Generate skill recommendations
        skill_recommendations = []
        complementary_skill_needs = []
        
        for gap in skill_gaps[:5]:  # Top 5 gaps
            skill_recommendations.append(f"Develop {gap['skill_name']} in {gap['skill_category']}")
            complementary_skill_needs.append(f"{gap['skill_category']}: {gap['skill_name']}")
        
        # Group skills by category
        skill_categories = {}
        for skill_key, score in user_skills.items():
            if "_" in skill_key:
                category, skill = skill_key.split("_", 1)
                if category not in skill_categories:
                    skill_categories[category] = []
                skill_categories[category].append(skill)
        
        logger.info(
            "Skill analysis completed",
            user_id=current_user.id,
            skill_count=len(user_skills),
            gap_count=len(skill_gaps)
        )
        
        return SkillAnalysisResponse(
            user_id=current_user.id,
            current_skills=user_skills,
            skill_gaps=skill_gaps,
            skill_recommendations=skill_recommendations,
            complementary_skill_needs=complementary_skill_needs,
            skill_categories=skill_categories,
            analysis_context=opportunity_id
        )
        
    except Exception as e:
        logger.error("Failed to analyze user skills", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze user skills"
        )


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def submit_match_feedback(
    feedback: MatchFeedback,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit feedback on a user match.
    
    Helps improve matching algorithms through user feedback.
    """
    try:
        # TODO: Store feedback in database for algorithm improvement
        # This would involve creating a MatchFeedback model and storing the feedback
        
        logger.info(
            "Match feedback submitted",
            user_id=current_user.id,
            matched_user_id=feedback.matched_user_id,
            feedback_score=feedback.feedback_score,
            would_collaborate=feedback.would_collaborate
        )
        
        return {"message": "Feedback submitted successfully"}
        
    except Exception as e:
        logger.error("Failed to submit match feedback", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )


@router.get("/analytics", response_model=MatchingAnalytics)
async def get_matching_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analytics on the matching system performance.
    
    Available to admins and moderators for system monitoring.
    """
    if current_user.role.value not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view analytics"
        )
    
    try:
        # TODO: Implement comprehensive analytics
        # This would involve querying match history, feedback, and success metrics
        
        analytics = MatchingAnalytics(
            total_matches_generated=0,  # Placeholder
            average_match_score=0.0,
            match_type_distribution={},
            user_engagement_rate=0.0,
            successful_collaborations=0,
            feedback_summary={},
            algorithm_performance={}
        )
        
        logger.info("Matching analytics retrieved", user_id=current_user.id)
        
        return analytics
        
    except Exception as e:
        logger.error("Failed to retrieve matching analytics", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics"
        )