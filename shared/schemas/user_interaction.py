"""User interaction and preference related Pydantic schemas."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import Field, validator
from .base import BaseSchema, TimestampSchema, UUIDSchema
from shared.models.user_interaction import InteractionType


class UserInteractionBase(BaseSchema):
    """Base user interaction schema."""
    
    opportunity_id: Optional[str] = Field(None, description="ID of the opportunity interacted with")
    interaction_type: InteractionType = Field(..., description="Type of interaction")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Time spent on opportunity")
    search_query: Optional[str] = Field(None, max_length=500, description="Search query if applicable")
    filters_applied: Optional[Dict[str, Any]] = Field(None, description="Applied filters as JSON")
    referrer_source: Optional[str] = Field(None, max_length=100, description="How user found this opportunity")


class UserInteractionCreate(UserInteractionBase):
    """Schema for creating a new user interaction."""
    pass


class UserInteractionResponse(UserInteractionBase, UUIDSchema, TimestampSchema):
    """Schema for user interaction responses."""
    
    user_id: str
    engagement_score: float


class BookmarkRequest(BaseSchema):
    """Schema for bookmark requests."""
    
    opportunity_id: str = Field(..., description="ID of the opportunity to bookmark")


class BookmarkResponse(BaseSchema):
    """Schema for bookmark responses."""
    
    id: str
    user_id: str
    opportunity_id: str
    created_at: datetime
    opportunity_title: Optional[str] = None
    opportunity_description: Optional[str] = None


class UserPreferenceBase(BaseSchema):
    """Base user preference schema."""
    
    preferred_ai_types: Optional[Dict[str, float]] = Field(None, description="AI types with confidence scores")
    preferred_industries: Optional[Dict[str, float]] = Field(None, description="Industries with confidence scores")
    preferred_complexity: Optional[str] = Field(None, pattern="^(low|medium|high)$", description="Preferred complexity level")
    preferred_market_size: Optional[str] = Field(None, pattern="^(small|medium|large)$", description="Preferred market size")
    min_validation_score: float = Field(5.0, ge=0.0, le=10.0, description="Minimum validation score threshold")
    prefers_trending: bool = Field(True, description="Prefer trending opportunities")
    prefers_new_opportunities: bool = Field(True, description="Prefer new opportunities")
    preferred_geographic_scope: Optional[str] = Field(None, max_length=100, description="Geographic preference")


class UserPreferenceUpdate(UserPreferenceBase):
    """Schema for updating user preferences."""
    pass


class UserPreferenceResponse(UserPreferenceBase, UUIDSchema, TimestampSchema):
    """Schema for user preference responses."""
    
    user_id: str
    confidence_score: float
    interaction_count: int
    last_updated: datetime


class ActivitySummary(BaseSchema):
    """Schema for user activity summary."""
    
    total_interactions: int
    recent_views: int
    bookmarks_count: int
    searches_count: int
    validations_count: int
    average_engagement_score: float
    most_viewed_categories: List[str]
    most_bookmarked_categories: List[str]


class RecommendationFeedbackRequest(BaseSchema):
    """Schema for recommendation feedback."""
    
    opportunity_id: str = Field(..., description="ID of the recommended opportunity")
    is_relevant: bool = Field(..., description="Was this recommendation relevant?")
    feedback_score: Optional[int] = Field(None, ge=1, le=5, description="1-5 rating")
    feedback_text: Optional[str] = Field(None, max_length=1000, description="Optional text feedback")
    recommendation_algorithm: str = Field(..., max_length=100, description="Algorithm used for recommendation")
    recommendation_score: float = Field(..., ge=0.0, description="Original recommendation score")
    recommendation_rank: int = Field(..., ge=1, description="Position in recommendation list")


class RecommendationFeedbackResponse(RecommendationFeedbackRequest, UUIDSchema, TimestampSchema):
    """Schema for recommendation feedback responses."""
    
    user_id: str


class UserCollectionCreate(BaseSchema):
    """Schema for creating a user collection."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Collection name")
    description: Optional[str] = Field(None, max_length=500, description="Collection description")
    is_public: bool = Field(False, description="Is this collection public?")
    tags: Optional[List[str]] = Field(None, description="Collection tags")


class UserCollectionUpdate(BaseSchema):
    """Schema for updating a user collection."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Collection name")
    description: Optional[str] = Field(None, max_length=500, description="Collection description")
    is_public: Optional[bool] = Field(None, description="Is this collection public?")
    tags: Optional[List[str]] = Field(None, description="Collection tags")


class UserCollectionResponse(UUIDSchema, TimestampSchema):
    """Schema for user collection responses."""
    
    user_id: str
    name: str
    description: Optional[str] = None
    is_public: bool
    tags: Optional[List[str]] = None
    opportunity_count: int = 0


class CollectionOpportunityAdd(BaseSchema):
    """Schema for adding opportunity to collection."""
    
    opportunity_id: str = Field(..., description="ID of the opportunity to add")
    note: Optional[str] = Field(None, max_length=500, description="Optional note about why this was added")


class CollectionOpportunityResponse(BaseSchema):
    """Schema for opportunities in collections."""
    
    opportunity_id: str
    added_at: datetime
    note: Optional[str] = None
    opportunity_title: Optional[str] = None
    opportunity_description: Optional[str] = None