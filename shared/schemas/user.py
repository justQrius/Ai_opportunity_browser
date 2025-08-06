"""User-related Pydantic schemas."""

from typing import Optional, List
from datetime import datetime
from pydantic import Field, validator
from .base import BaseSchema, TimestampSchema, UUIDSchema
from shared.models.user import UserRole
from shared.models.reputation import BadgeType


class UserBase(BaseSchema):
    """Base user schema with common fields."""
    
    email: str
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = Field(None, max_length=1000)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserCreate(UserBase):
    """Schema for creating a new user.
    
    Supports Requirements 4.1 (Expert profiles) and authentication.
    """
    
    password: str = Field(..., min_length=8, max_length=128)
    expertise_domains: Optional[List[str]] = Field(None, description="List of expertise domains")
    linkedin_url: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = Field(None, max_length=500)
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseSchema):
    """Schema for updating user information."""
    
    full_name: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = Field(None, max_length=1000)
    avatar_url: Optional[str] = Field(None, max_length=500)
    expertise_domains: Optional[List[str]] = None
    linkedin_url: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = Field(None, max_length=500)


class UserResponse(UserBase, UUIDSchema, TimestampSchema):
    """Schema for user responses (public information).
    
    Supports Requirements 4.1 (Expert profiles) and 4.4 (Reputation system).
    """
    
    role: UserRole
    is_active: bool
    is_verified: bool
    reputation_score: float
    validation_count: int
    validation_accuracy: float
    expertise_domains: Optional[List[str]] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None


class UserLogin(BaseSchema):
    """Schema for user login."""
    
    email: str
    password: str


class UserToken(BaseSchema):
    """Schema for authentication token response."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class UserReputationUpdate(BaseSchema):
    """Schema for updating user reputation."""
    
    reputation_score: float = Field(..., ge=0.0, le=10.0)
    validation_count: int = Field(..., ge=0)
    validation_accuracy: float = Field(..., ge=0.0, le=1.0)


class UserBadgeResponse(BaseSchema):
    """Schema for user badge information."""
    
    id: str
    badge_type: BadgeType
    title: str
    description: str
    earned_for: Optional[str] = None
    milestone_value: Optional[int] = None
    icon_url: Optional[str] = None
    color: Optional[str] = None
    is_visible: bool = True
    created_at: datetime


class ExpertiseVerificationResponse(BaseSchema):
    """Schema for expertise verification information."""
    
    id: str
    domain: str
    verification_method: str
    verification_status: str
    evidence_url: Optional[str] = None
    years_experience: Optional[int] = None
    verified_at: Optional[datetime] = None
    expertise_score: float
    confidence_level: float
    created_at: datetime


class UserStatsResponse(BaseSchema):
    """Schema for user statistics."""
    
    total_validations: int
    helpful_validations: int
    accuracy_score: float
    total_votes_received: int
    helpful_votes_received: int
    badges_earned: int
    verified_domains: int
    days_active: int
    quality_score: float


class UserProfile(UserResponse):
    """Extended user profile with additional details."""
    
    badges: List[UserBadgeResponse] = []
    expertise_verifications: List[ExpertiseVerificationResponse] = []
    stats: Optional[UserStatsResponse] = None