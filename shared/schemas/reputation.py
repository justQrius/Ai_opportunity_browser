"""Pydantic schemas for reputation and community engagement."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator

from shared.models.reputation import ReputationEventType, BadgeType


class ReputationEventCreate(BaseModel):
    """Schema for creating reputation events."""
    user_id: str
    event_type: ReputationEventType
    description: str
    points_override: Optional[float] = None
    related_validation_id: Optional[str] = None
    related_opportunity_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ReputationEventResponse(BaseModel):
    """Schema for reputation event responses."""
    id: str
    user_id: str
    event_type: ReputationEventType
    points_change: float
    description: str
    related_validation_id: Optional[str] = None
    related_opportunity_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class BadgeCreate(BaseModel):
    """Schema for creating badges."""
    user_id: str
    badge_type: BadgeType
    title: str
    description: str
    earned_for: Optional[str] = None
    milestone_value: Optional[int] = None
    icon_url: Optional[str] = None
    color: Optional[str] = None


class BadgeResponse(BaseModel):
    """Schema for badge responses."""
    id: str
    user_id: str
    badge_type: BadgeType
    title: str
    description: str
    earned_for: Optional[str] = None
    milestone_value: Optional[int] = None
    icon_url: Optional[str] = None
    color: Optional[str] = None
    is_visible: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ExpertiseVerificationCreate(BaseModel):
    """Schema for creating expertise verifications."""
    user_id: str
    domain: str = Field(..., min_length=1, max_length=100)
    verification_method: str = Field(..., min_length=1, max_length=50)
    evidence_url: Optional[str] = Field(None, max_length=500)
    credentials: Optional[str] = None
    years_experience: Optional[int] = Field(None, ge=0, le=50)
    
    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v):
        """Validate domain format."""
        if not v.strip():
            raise ValueError('Domain cannot be empty')
        return v.strip().lower()


class ExpertiseVerificationUpdate(BaseModel):
    """Schema for updating expertise verifications."""
    verification_method: Optional[str] = Field(None, min_length=1, max_length=50)
    verification_status: Optional[str] = Field(None, pattern=r'^(pending|verified|rejected)$')
    evidence_url: Optional[str] = Field(None, max_length=500)
    credentials: Optional[str] = None
    years_experience: Optional[int] = Field(None, ge=0, le=50)
    expertise_score: Optional[float] = Field(None, ge=1.0, le=10.0)
    confidence_level: Optional[float] = Field(None, ge=1.0, le=10.0)
    verification_notes: Optional[str] = None


class ExpertiseVerificationResponse(BaseModel):
    """Schema for expertise verification responses."""
    id: str
    user_id: str
    domain: str
    verification_method: str
    verification_status: str
    evidence_url: Optional[str] = None
    credentials: Optional[str] = None
    years_experience: Optional[int] = None
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None
    expertise_score: float
    confidence_level: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ReputationSummaryResponse(BaseModel):
    """Schema for reputation summary responses."""
    id: str
    user_id: str
    total_reputation_points: float
    reputation_rank: Optional[int] = None
    influence_weight: float
    total_validations: int
    helpful_validations: int
    accuracy_score: float
    total_votes_received: int
    helpful_votes_received: int
    badges_earned: int
    verified_domains: int
    average_expertise_score: float
    days_active: int
    last_activity_at: Optional[datetime] = None
    flagged_validations: int
    moderation_actions: int
    quality_score: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserReputationProfile(BaseModel):
    """Comprehensive user reputation profile."""
    user_id: str
    username: str
    avatar_url: Optional[str] = None
    reputation_summary: ReputationSummaryResponse
    badges: List[BadgeResponse]
    expertise_verifications: List[ExpertiseVerificationResponse]
    recent_events: List[ReputationEventResponse]


class LeaderboardEntry(BaseModel):
    """Schema for leaderboard entries."""
    rank: int
    user_id: str
    username: str
    avatar_url: Optional[str] = None
    reputation_points: float
    influence_weight: float
    total_validations: int
    accuracy_score: float
    badges_earned: int
    verified_domains: int


class ReputationAnalytics(BaseModel):
    """Schema for reputation analytics."""
    total_users: int
    total_reputation_points: float
    average_reputation: float
    total_badges_awarded: int
    total_verifications: int
    top_domains: List[Dict[str, Any]]
    reputation_distribution: Dict[str, int]
    badge_distribution: Dict[str, int]
    activity_trends: Dict[str, int]
    generated_at: datetime