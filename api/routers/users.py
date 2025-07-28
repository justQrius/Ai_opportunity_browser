"""
Users API endpoints for the AI Opportunity Browser.

This module provides REST API endpoints for user management,
including authentication, profiles, and user-related operations.

Supports Requirements 4 (Community Engagement Platform) and 10 (API Access).
"""

from fastapi import APIRouter, HTTPException, Query, Depends, status
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
import json

from shared.database import get_db
from shared.schemas.user import (
    UserUpdate, UserResponse, UserProfile, UserBadgeResponse, 
    ExpertiseVerificationResponse, UserStatsResponse
)
from shared.schemas.user_interaction import (
    UserInteractionCreate, UserInteractionResponse, BookmarkRequest, BookmarkResponse,
    UserPreferenceUpdate, UserPreferenceResponse, ActivitySummary, 
    RecommendationFeedbackRequest, RecommendationFeedbackResponse,
    UserCollectionCreate, UserCollectionUpdate, UserCollectionResponse,
    CollectionOpportunityAdd, CollectionOpportunityResponse
)
from shared.schemas.auth import CurrentUser
from shared.schemas.base import APIResponse, PaginatedResponse, PaginationResponse
from shared.services.user_service import user_service
from shared.services.user_interaction_service import (
    get_interaction_service, get_bookmark_service, get_collection_service
)
from shared.models.user import User, UserRole
from shared.models.reputation import UserBadge, ExpertiseVerification, ReputationSummary, BadgeType
from shared.models.validation import ValidationResult
from api.routers.auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user profile.
    
    Supports Requirements 4.1 (Expert profiles showcasing expertise).
    """
    try:
        # Get user with all related data
        result = db.execute(
            select(User)
            .options(
                selectinload(User.badges),
                selectinload(User.expertise_verifications),
                selectinload(User.reputation_summary)
            )
            .where(User.id == current_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Parse expertise domains
        expertise_domains = []
        if user.expertise_domains:
            try:
                expertise_domains = json.loads(user.expertise_domains)
            except json.JSONDecodeError:
                expertise_domains = user.expertise_domains.split(",") if user.expertise_domains else []
        
        # Build response with badges and stats
        profile = _build_user_profile_response(user)
        
        logger.info(f"Retrieved profile for user: {user.username}")
        return profile
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )


@router.put("/me", response_model=UserProfile)
async def update_current_user(
    user_update: UserUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user profile.
    
    Supports Requirements 4.1 (Expert profiles) and profile management.
    """
    try:
        # Get current user from database
        result = db.execute(
            select(User)
            .options(
                selectinload(User.badges),
                selectinload(User.expertise_verifications),
                selectinload(User.reputation_summary)
            )
            .where(User.id == current_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user fields
        update_data = user_update.dict(exclude_unset=True)
        
        # Handle expertise domains
        if "expertise_domains" in update_data:
            if update_data["expertise_domains"]:
                user.expertise_domains = json.dumps(update_data["expertise_domains"])
            else:
                user.expertise_domains = None
            del update_data["expertise_domains"]
        
        # Apply other updates
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        # Build response with badges and stats
        profile = _build_user_profile_response(user)
        
        logger.info(f"Updated profile for user: {user.username}")
        return profile
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )


@router.get("/{user_id}", response_model=UserProfile)
async def get_user_profile(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get public user profile by ID.
    
    Supports Requirements 4.1 (Expert profiles) and community visibility.
    """
    try:
        # Get user with all related data
        result = db.execute(
            select(User)
            .options(
                selectinload(User.badges),
                selectinload(User.expertise_verifications),
                selectinload(User.reputation_summary)
            )
            .where(and_(User.id == user_id, User.is_active == True))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Build response with badges and stats
        profile = _build_user_profile_response(user)
        
        logger.info(f"Retrieved public profile for user: {user.username}")
        return profile
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )


@router.get("/", response_model=PaginatedResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    role: Optional[str] = Query(None, description="Filter by user role"),
    expertise_domain: Optional[str] = Query(None, description="Filter by expertise domain"),
    min_reputation: Optional[float] = Query(None, ge=0.0, description="Minimum reputation score"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
    search: Optional[str] = Query(None, description="Search by username or full name"),
    db: Session = Depends(get_db)
):
    """
    List users with filtering and pagination.
    
    Supports Requirements 4.1-4.2 (Expert profiles and domain matching).
    """
    try:
        # Build query
        query = select(User).where(User.is_active == True)
        
        # Apply filters
        if role:
            try:
                role_enum = UserRole(role)
                query = query.where(User.role == role_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role: {role}"
                )
        
        if expertise_domain:
            query = query.where(User.expertise_domains.contains(expertise_domain))
        
        if min_reputation is not None:
            query = query.where(User.reputation_score >= min_reputation)
        
        if is_verified is not None:
            query = query.where(User.is_verified == is_verified)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    User.username.ilike(search_term),
                    User.full_name.ilike(search_term)
                )
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        result = db.execute(query)
        users = result.scalars().all()
        
        # Convert to response format
        user_items = []
        for user in users:
            expertise_domains = []
            if user.expertise_domains:
                try:
                    expertise_domains = json.loads(user.expertise_domains)
                except json.JSONDecodeError:
                    expertise_domains = user.expertise_domains.split(",") if user.expertise_domains else []
            
            user_items.append({
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role.value,
                "reputation_score": user.reputation_score,
                "validation_count": user.validation_count,
                "validation_accuracy": user.validation_accuracy,
                "expertise_domains": expertise_domains,
                "is_verified": user.is_verified,
                "created_at": user.created_at
            })
        
        from shared.schemas.base import PaginationResponse
        pagination = PaginationResponse.create(
            page=page,
            page_size=page_size,
            total_count=total_count
        )
        
        return PaginatedResponse(
            items=user_items,
            pagination=pagination,
            total_count=total_count,
            filters_applied={
                "role": role,
                "expertise_domain": expertise_domain,
                "min_reputation": min_reputation,
                "is_verified": is_verified,
                "search": search
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )


@router.get("/experts/by-domain", response_model=PaginatedResponse)
async def get_experts_by_domain(
    domain: str = Query(..., description="Expertise domain to search for"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_reputation: Optional[float] = Query(None, ge=0.0, description="Minimum reputation score"),
    verified_only: bool = Query(False, description="Only include verified experts"),
    db: Session = Depends(get_db)
):
    """
    Get experts filtered by domain expertise.
    
    Supports Requirements 4.2 (Expert-opportunity domain matching).
    """
    try:
        # Build base query for experts
        query = select(User).where(
            and_(
                User.is_active == True,
                or_(User.role == UserRole.EXPERT, User.role == UserRole.MODERATOR, User.role == UserRole.ADMIN),
                User.expertise_domains.isnot(None),
                User.expertise_domains.contains(domain)
            )
        )
        
        # Apply reputation filter
        if min_reputation is not None:
            query = query.where(User.reputation_score >= min_reputation)
        
        # Apply verification filter
        if verified_only:
            query = query.where(User.is_verified == True)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = db.execute(count_query).scalar()
        
        # Apply pagination and ordering
        offset = (page - 1) * page_size
        query = query.order_by(User.reputation_score.desc()).offset(offset).limit(page_size)
        
        # Execute query
        result = db.execute(query)
        experts = result.scalars().all()
        
        # Convert to response format
        expert_items = []
        for expert in experts:
            expertise_domains = []
            if expert.expertise_domains:
                try:
                    expertise_domains = json.loads(expert.expertise_domains)
                except json.JSONDecodeError:
                    expertise_domains = expert.expertise_domains.split(",") if expert.expertise_domains else []
            
            expert_items.append({
                "id": expert.id,
                "username": expert.username,
                "full_name": expert.full_name,
                "role": expert.role.value,
                "reputation_score": expert.reputation_score,
                "validation_count": expert.validation_count,
                "validation_accuracy": expert.validation_accuracy,
                "expertise_domains": expertise_domains,
                "is_verified": expert.is_verified,
                "linkedin_url": expert.linkedin_url,
                "github_url": expert.github_url,
                "created_at": expert.created_at
            })
        
        from shared.schemas.base import PaginationResponse
        pagination = PaginationResponse.create(
            page=page,
            page_size=page_size,
            total_count=total_count
        )
        
        return PaginatedResponse(
            items=expert_items,
            pagination=pagination,
            total_count=total_count,
            filters_applied={
                "domain": domain,
                "min_reputation": min_reputation,
                "verified_only": verified_only
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting experts by domain: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get experts by domain"
        )


@router.get("/{user_id}/reputation", response_model=dict)
async def get_user_reputation(user_id: str):
    """
    Get detailed user reputation information.
    
    Supports Requirements 4.3-4.4 (Contribution tracking and influence weight).
    This endpoint will be fully implemented in Phase 6.
    """
    # Placeholder implementation
    raise HTTPException(
        status_code=404,
        detail={
            "error": "User not found",
            "message": "User reputation endpoint will be implemented in Phase 6",
            "user_id": user_id
        }
    )


@router.get("/{user_id}/validations", response_model=PaginatedResponse)
async def get_user_validations(
    user_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    validation_type: Optional[str] = Query(None, description="Filter by validation type")
):
    """
    Get user's validation history.
    
    Supports Requirements 4.3 (Track contribution history and accuracy).
    This endpoint will be fully implemented in Phase 6.
    """
    # Placeholder implementation
    from shared.schemas.base import PaginationResponse
    
    pagination = PaginationResponse.create(
        page=page,
        page_size=page_size,
        total_count=0
    )
    
    return PaginatedResponse(
        items=[],
        pagination=pagination,
        total_count=0,
        filters_applied={
            "user_id": user_id,
            "validation_type": validation_type
        }
    )


@router.get("/{user_id}/badges", response_model=List[dict])
async def get_user_badges(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get user's earned badges.
    
    Supports Requirements 4.5 (Earn reputation points and badges).
    """
    try:
        # Check if user exists
        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get user badges
        result = db.execute(
            select(UserBadge)
            .where(and_(UserBadge.user_id == user_id, UserBadge.is_visible == True))
            .order_by(UserBadge.created_at.desc())
        )
        badges = result.scalars().all()
        
        # Convert to response format
        badge_items = []
        for badge in badges:
            badge_items.append({
                "id": badge.id,
                "badge_type": badge.badge_type.value,
                "title": badge.title,
                "description": badge.description,
                "earned_for": badge.earned_for,
                "milestone_value": badge.milestone_value,
                "icon_url": badge.icon_url,
                "color": badge.color,
                "created_at": badge.created_at
            })
        
        return badge_items
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user badges: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user badges"
        )


@router.post("/{user_id}/follow", response_model=APIResponse)
async def follow_user(user_id: str):
    """
    Follow another user for updates.
    
    Supports community networking features.
    This endpoint will be fully implemented in Phase 8.
    """
    # Placeholder implementation
    raise HTTPException(
        status_code=501,
        detail={
            "error": "Not implemented",
            "message": "Follow user endpoint will be implemented in Phase 8",
            "user_id": user_id
        }
    )


@router.delete("/{user_id}/follow", response_model=APIResponse)
async def unfollow_user(user_id: str):
    """
    Unfollow a user.
    
    Supports community networking features.
    This endpoint will be fully implemented in Phase 8.
    """
    # Placeholder implementation
    raise HTTPException(
        status_code=501,
        detail={
            "error": "Not implemented",
            "message": "Unfollow user endpoint will be implemented in Phase 8",
            "user_id": user_id
        }
    )


@router.get("/leaderboard/reputation", response_model=PaginatedResponse)
async def get_reputation_leaderboard(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    domain: Optional[str] = Query(None, description="Filter by expertise domain"),
    time_period: str = Query("all_time", pattern="^(week|month|quarter|year|all_time)$")
):
    """
    Get reputation leaderboard.
    
    Supports Requirements 4.4-4.5 (Reputation system and community engagement).
    This endpoint will be fully implemented in Phase 6.
    """
    # Placeholder implementation
    from shared.schemas.base import PaginationResponse
    
    pagination = PaginationResponse.create(
        page=page,
        page_size=page_size,
        total_count=0
    )
    
    return PaginatedResponse(
        items=[],
        pagination=pagination,
        total_count=0,
        filters_applied={
            "domain": domain,
            "time_period": time_period
        }
    )


# ============================================================================
# USER INTERACTION ENDPOINTS - Task 6.2.2
# ============================================================================

@router.post("/me/interactions", response_model=UserInteractionResponse)
async def create_user_interaction(
    interaction_data: UserInteractionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user interaction record.
    
    Supports Requirements 6.2.2 (User activity tracking).
    """
    try:
        interaction_service = get_interaction_service(db)
        interaction = await interaction_service.create_interaction(
            current_user.id, 
            interaction_data
        )
        
        return UserInteractionResponse(
            id=interaction.id,
            user_id=interaction.user_id,
            opportunity_id=interaction.opportunity_id,
            interaction_type=interaction.interaction_type,
            duration_seconds=interaction.duration_seconds,
            search_query=interaction.search_query,
            filters_applied=json.loads(interaction.filters_applied) if interaction.filters_applied else None,
            referrer_source=interaction.referrer_source,
            engagement_score=interaction.engagement_score,
            created_at=interaction.created_at,
            updated_at=interaction.updated_at
        )
        
    except Exception as e:
        logger.error(f"Error creating user interaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create interaction"
        )


@router.get("/me/activity", response_model=ActivitySummary)
async def get_user_activity_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user activity summary.
    
    Supports Requirements 6.2.2 (User activity tracking).
    """
    try:
        interaction_service = get_interaction_service(db)
        summary = interaction_service.get_activity_summary(current_user.id, days)
        
        logger.info(f"Retrieved activity summary for user: {current_user.id}")
        return summary
        
    except Exception as e:
        logger.error(f"Error getting user activity summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get activity summary"
        )


@router.get("/me/preferences", response_model=UserPreferenceResponse)
async def get_user_preferences(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user preferences for personalization.
    
    Supports Requirements 6.1.3 (User preference learning).
    """
    try:
        from shared.models.user_interaction import UserPreference
        
        result = db.execute(
            select(UserPreference).where(UserPreference.user_id == current_user.id)
        )
        preferences = result.scalar_one_or_none()
        
        if not preferences:
            # Create default preferences
            preferences = UserPreference(user_id=current_user.id)
            db.add(preferences)
            db.commit()
            db.refresh(preferences)
        
        # Parse JSON fields
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
        
        return UserPreferenceResponse(
            id=preferences.id,
            user_id=preferences.user_id,
            preferred_ai_types=preferred_ai_types,
            preferred_industries=preferred_industries,
            preferred_complexity=preferences.preferred_complexity,
            preferred_market_size=preferences.preferred_market_size,
            min_validation_score=preferences.min_validation_score,
            prefers_trending=preferences.prefers_trending,
            prefers_new_opportunities=preferences.prefers_new_opportunities,
            preferred_geographic_scope=preferences.preferred_geographic_scope,
            confidence_score=preferences.confidence_score,
            interaction_count=preferences.interaction_count,
            last_updated=preferences.last_updated,
            created_at=preferences.created_at,
            updated_at=preferences.updated_at
        )
        
    except Exception as e:
        logger.error(f"Error getting user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user preferences"
        )


@router.put("/me/preferences", response_model=UserPreferenceResponse)
async def update_user_preferences(
    preferences_update: UserPreferenceUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user preferences.
    
    Supports Requirements 6.1.3 (User preference learning).
    """
    try:
        interaction_service = get_interaction_service(db)
        preferences = interaction_service.update_user_preferences(
            current_user.id,
            preferences_update
        )
        
        # Parse JSON fields for response
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
        
        return UserPreferenceResponse(
            id=preferences.id,
            user_id=preferences.user_id,
            preferred_ai_types=preferred_ai_types,
            preferred_industries=preferred_industries,
            preferred_complexity=preferences.preferred_complexity,
            preferred_market_size=preferences.preferred_market_size,
            min_validation_score=preferences.min_validation_score,
            prefers_trending=preferences.prefers_trending,
            prefers_new_opportunities=preferences.prefers_new_opportunities,
            preferred_geographic_scope=preferences.preferred_geographic_scope,
            confidence_score=preferences.confidence_score,
            interaction_count=preferences.interaction_count,
            last_updated=preferences.last_updated,
            created_at=preferences.created_at,
            updated_at=preferences.updated_at
        )
        
    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user preferences"
        )


# ============================================================================
# BOOKMARK ENDPOINTS
# ============================================================================

@router.post("/me/bookmarks", response_model=BookmarkResponse)
async def create_bookmark(
    bookmark_request: BookmarkRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bookmark an opportunity.
    
    Supports Requirements 6.2.2 (Bookmarking features).
    """
    try:
        bookmark_service = get_bookmark_service(db)
        bookmark = bookmark_service.create_bookmark(
            current_user.id,
            bookmark_request.opportunity_id
        )
        
        # Get opportunity details
        from shared.models.opportunity import Opportunity
        opportunity = db.execute(
            select(Opportunity).where(Opportunity.id == bookmark_request.opportunity_id)
        ).scalar_one_or_none()
        
        return BookmarkResponse(
            id=bookmark.id,
            user_id=bookmark.user_id,
            opportunity_id=bookmark.opportunity_id,
            created_at=bookmark.created_at,
            opportunity_title=opportunity.title if opportunity else None,
            opportunity_description=opportunity.summary if opportunity else None
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating bookmark: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create bookmark"
        )


@router.delete("/me/bookmarks/{opportunity_id}", response_model=APIResponse)
async def remove_bookmark(
    opportunity_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a bookmark.
    
    Supports Requirements 6.2.2 (Bookmarking features).
    """
    try:
        bookmark_service = get_bookmark_service(db)
        success = bookmark_service.remove_bookmark(current_user.id, opportunity_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bookmark not found"
            )
        
        return APIResponse(
            success=True,
            message="Bookmark removed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing bookmark: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove bookmark"
        )


@router.get("/me/bookmarks", response_model=PaginatedResponse)
async def get_user_bookmarks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user bookmarks.
    
    Supports Requirements 6.2.2 (Bookmarking features).
    """
    try:
        bookmark_service = get_bookmark_service(db)
        offset = (page - 1) * page_size
        bookmarks = bookmark_service.get_user_bookmarks(
            current_user.id,
            limit=page_size,
            offset=offset
        )
        
        # Convert to response format
        bookmark_items = []
        for bookmark in bookmarks:
            bookmark_items.append({
                "id": bookmark.id,
                "opportunity_id": bookmark.opportunity_id,
                "note": bookmark.note,
                "created_at": bookmark.created_at,
                "opportunity_title": bookmark.opportunity.title if bookmark.opportunity else None,
                "opportunity_description": bookmark.opportunity.summary if bookmark.opportunity else None
            })
        
        # Get total count
        from shared.models.user_collection import BookmarkInteraction
        total_count = db.execute(
            select(func.count(BookmarkInteraction.id))
            .where(BookmarkInteraction.user_id == current_user.id)
        ).scalar()
        
        pagination = PaginationResponse.create(
            page=page,
            page_size=page_size,
            total_count=total_count
        )
        
        return PaginatedResponse(
            items=bookmark_items,
            pagination=pagination,
            total_count=total_count
        )
        
    except Exception as e:
        logger.error(f"Error getting user bookmarks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bookmarks"
        )


# ============================================================================
# COLLECTION ENDPOINTS
# ============================================================================

@router.post("/me/collections", response_model=UserCollectionResponse)
async def create_collection(
    collection_data: UserCollectionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new collection.
    
    Supports Requirements 6.2.2 (Collection features).
    """
    try:
        collection_service = get_collection_service(db)
        collection = collection_service.create_collection(current_user.id, collection_data)
        
        # Parse tags for response
        tags = []
        if collection.tags:
            try:
                tags = json.loads(collection.tags)
            except json.JSONDecodeError:
                pass
        
        return UserCollectionResponse(
            id=collection.id,
            user_id=collection.user_id,
            name=collection.name,
            description=collection.description,
            is_public=collection.is_public,
            tags=tags,
            opportunity_count=len(collection.opportunities) if collection.opportunities else 0,
            created_at=collection.created_at,
            updated_at=collection.updated_at
        )
        
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create collection"
        )


@router.get("/me/collections", response_model=List[UserCollectionResponse])
async def get_user_collections(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user collections.
    
    Supports Requirements 6.2.2 (Collection features).
    """
    try:
        collection_service = get_collection_service(db)
        collections = collection_service.get_user_collections(current_user.id)
        
        # Convert to response format
        collection_items = []
        for collection in collections:
            tags = []
            if collection.tags:
                try:
                    tags = json.loads(collection.tags)
                except json.JSONDecodeError:
                    pass
            
            collection_items.append(UserCollectionResponse(
                id=collection.id,
                user_id=collection.user_id,
                name=collection.name,
                description=collection.description,
                is_public=collection.is_public,
                tags=tags,
                opportunity_count=len(collection.opportunities) if collection.opportunities else 0,
                created_at=collection.created_at,
                updated_at=collection.updated_at
            ))
        
        return collection_items
        
    except Exception as e:
        logger.error(f"Error getting user collections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get collections"
        )


@router.put("/me/collections/{collection_id}", response_model=UserCollectionResponse)
async def update_collection(
    collection_id: str,
    update_data: UserCollectionUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a collection.
    
    Supports Requirements 6.2.2 (Collection features).
    """
    try:
        collection_service = get_collection_service(db)
        collection = collection_service.update_collection(
            collection_id,
            current_user.id,
            update_data
        )
        
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found"
            )
        
        # Parse tags for response
        tags = []
        if collection.tags:
            try:
                tags = json.loads(collection.tags)
            except json.JSONDecodeError:
                pass
        
        return UserCollectionResponse(
            id=collection.id,
            user_id=collection.user_id,
            name=collection.name,
            description=collection.description,
            is_public=collection.is_public,
            tags=tags,
            opportunity_count=len(collection.opportunities) if collection.opportunities else 0,
            created_at=collection.created_at,
            updated_at=collection.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update collection"
        )


@router.delete("/me/collections/{collection_id}", response_model=APIResponse)
async def delete_collection(
    collection_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a collection.
    
    Supports Requirements 6.2.2 (Collection features).
    """
    try:
        collection_service = get_collection_service(db)
        success = collection_service.delete_collection(collection_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found"
            )
        
        return APIResponse(
            success=True,
            message="Collection deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete collection"
        )


@router.post("/me/collections/{collection_id}/opportunities", response_model=APIResponse)
async def add_opportunity_to_collection(
    collection_id: str,
    opportunity_data: CollectionOpportunityAdd,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add an opportunity to a collection.
    
    Supports Requirements 6.2.2 (Collection features).
    """
    try:
        collection_service = get_collection_service(db)
        success = collection_service.add_opportunity_to_collection(
            collection_id,
            current_user.id,
            opportunity_data
        )
        
        return APIResponse(
            success=True,
            message="Opportunity added to collection"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding opportunity to collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add opportunity to collection"
        )


@router.delete("/me/collections/{collection_id}/opportunities/{opportunity_id}", response_model=APIResponse)
async def remove_opportunity_from_collection(
    collection_id: str,
    opportunity_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove an opportunity from a collection.
    
    Supports Requirements 6.2.2 (Collection features).
    """
    try:
        collection_service = get_collection_service(db)
        success = collection_service.remove_opportunity_from_collection(
            collection_id,
            current_user.id,
            opportunity_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found in collection"
            )
        
        return APIResponse(
            success=True,
            message="Opportunity removed from collection"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing opportunity from collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove opportunity from collection"
        )


@router.post("/me/feedback", response_model=RecommendationFeedbackResponse)
async def create_recommendation_feedback(
    feedback_data: RecommendationFeedbackRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create recommendation feedback for learning.
    
    Supports Requirements 6.1.3 (User preference learning).
    """
    try:
        interaction_service = get_interaction_service(db)
        feedback = interaction_service.create_recommendation_feedback(
            current_user.id,
            feedback_data
        )
        
        return RecommendationFeedbackResponse(
            id=feedback.id,
            user_id=feedback.user_id,
            opportunity_id=feedback.opportunity_id,
            is_relevant=feedback.is_relevant,
            feedback_score=feedback.feedback_score,
            feedback_text=feedback.feedback_text,
            recommendation_algorithm=feedback.recommendation_algorithm,
            recommendation_score=feedback.recommendation_score,
            recommendation_rank=feedback.recommendation_rank,
            created_at=feedback.created_at,
            updated_at=feedback.updated_at
        )
        
    except Exception as e:
        logger.error(f"Error creating recommendation feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create feedback"
        )


def _build_user_profile_response(user: User) -> UserProfile:
    """
    Build a complete user profile response with badges and stats.
    
    Args:
        user: User model instance with loaded relationships
        
    Returns:
        UserProfile response schema
    """
    # Parse expertise domains
    expertise_domains = []
    if user.expertise_domains:
        try:
            expertise_domains = json.loads(user.expertise_domains)
        except json.JSONDecodeError:
            expertise_domains = user.expertise_domains.split(",") if user.expertise_domains else []
    
    # Build badges list
    badges = []
    for badge in user.badges:
        if badge.is_visible:
            badges.append({
                "id": badge.id,
                "badge_type": badge.badge_type,
                "title": badge.title,
                "description": badge.description,
                "earned_for": badge.earned_for,
                "milestone_value": badge.milestone_value,
                "icon_url": badge.icon_url,
                "color": badge.color,
                "is_visible": badge.is_visible,
                "created_at": badge.created_at
            })
    
    # Build expertise verifications list
    expertise_verifications = []
    for verification in user.expertise_verifications:
        expertise_verifications.append({
            "id": verification.id,
            "domain": verification.domain,
            "verification_method": verification.verification_method,
            "verification_status": verification.verification_status,
            "evidence_url": verification.evidence_url,
            "years_experience": verification.years_experience,
            "verified_at": verification.verified_at,
            "expertise_score": verification.expertise_score,
            "confidence_level": verification.confidence_level,
            "created_at": verification.created_at
        })
    
    # Build stats from reputation summary
    stats = None
    if user.reputation_summary:
        stats = {
            "total_validations": user.reputation_summary.total_validations,
            "helpful_validations": user.reputation_summary.helpful_validations,
            "accuracy_score": user.reputation_summary.accuracy_score,
            "total_votes_received": user.reputation_summary.total_votes_received,
            "helpful_votes_received": user.reputation_summary.helpful_votes_received,
            "badges_earned": user.reputation_summary.badges_earned,
            "verified_domains": user.reputation_summary.verified_domains,
            "days_active": user.reputation_summary.days_active,
            "quality_score": user.reputation_summary.quality_score
        }
    
    return UserProfile(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        bio=user.bio,
        avatar_url=user.avatar_url,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        reputation_score=user.reputation_score,
        validation_count=user.validation_count,
        validation_accuracy=user.validation_accuracy,
        expertise_domains=expertise_domains,
        linkedin_url=user.linkedin_url,
        github_url=user.github_url,
        created_at=user.created_at,
        updated_at=user.updated_at,
        badges=badges,
        expertise_verifications=expertise_verifications,
        stats=stats
    )