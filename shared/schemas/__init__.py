"""Pydantic schemas for API serialization."""

from .base import (
    BaseSchema, TimestampSchema, UUIDSchema, PaginationRequest, 
    PaginationResponse, ErrorResponse, HealthResponse
)
from .user import (
    UserCreate, UserUpdate, UserResponse, UserProfile, 
    UserLogin, UserToken, UserReputationUpdate
)
from .opportunity import (
    OpportunityCreate, OpportunityUpdate, OpportunityResponse, 
    OpportunityListResponse, OpportunitySearchRequest,
    OpportunityRecommendationRequest, OpportunityStats, OpportunityBookmark
)
from .market_signal import MarketSignalCreate, MarketSignalResponse
from .validation import (
    ValidationCreate, ValidationUpdate, ValidationResponse,
    ValidationVote, ValidationFlag, ValidationStats, ValidationSummary
)
from .ai_capability import AICapabilityResponse
from .implementation_guide import ImplementationGuideResponse
from .reputation import (
    ReputationEventCreate, ReputationEventResponse,
    BadgeCreate, BadgeResponse, ExpertiseVerificationCreate,
    ExpertiseVerificationResponse, ReputationSummaryResponse
)
from .auth import (
    LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse,
    RegisterRequest, RegisterResponse, PasswordResetRequest, PasswordResetResponse,
    PasswordResetConfirm, ChangePasswordRequest, CurrentUser, SessionInfo
)
from .discussion import (
    DiscussionCreate, DiscussionUpdate, DiscussionResponse,
    CommentCreate, CommentUpdate, CommentResponse,
    VoteRequest, VoteResponse, DiscussionFlag, CommentFlag,
    DiscussionStats, DiscussionSearch
)
from .user_matching import (
    UserMatchRequest, UserMatchResponse, UserMatchListResponse,
    SkillAnalysisRequest, SkillAnalysisResponse, TeamFormationRequest,
    TeamFormationResponse, MatchFeedback, MatchingPreferences,
    MatchingPreferencesUpdate, MatchingAnalytics
)
from .api import (
    APIResponse, APIError, PaginatedResponse, SearchResponse,
    BulkOperationRequest, BulkOperationResponse, AdvancedSearchRequest,
    AdvancedSearchResponse, ExportRequest, ExportResponse,
    WebhookRequest, WebhookResponse, NotificationRequest, NotificationResponse,
    AnalyticsRequest, AnalyticsResponse, SystemStatusResponse, APIMetadata
)

__all__ = [
    # Base schemas
    "BaseSchema", "TimestampSchema", "UUIDSchema", "PaginationRequest", 
    "PaginationResponse", "ErrorResponse", "HealthResponse",
    
    # User schemas
    "UserCreate", "UserUpdate", "UserResponse", "UserProfile", 
    "UserLogin", "UserToken", "UserReputationUpdate",
    
    # Opportunity schemas
    "OpportunityCreate", "OpportunityUpdate", "OpportunityResponse", 
    "OpportunityListResponse", "OpportunitySearchRequest",
    "OpportunityRecommendationRequest", "OpportunityStats", "OpportunityBookmark",
    
    # Market signal schemas
    "MarketSignalCreate", "MarketSignalResponse",
    
    # Validation schemas
    "ValidationCreate", "ValidationUpdate", "ValidationResponse",
    "ValidationVote", "ValidationFlag", "ValidationStats", "ValidationSummary",
    
    # AI capability schemas
    "AICapabilityResponse",
    
    # Implementation guide schemas
    "ImplementationGuideResponse",
    
    # Reputation schemas
    "ReputationEventCreate", "ReputationEventResponse",
    "BadgeCreate", "BadgeResponse", "ExpertiseVerificationCreate",
    "ExpertiseVerificationResponse", "ReputationSummaryResponse",
    
    # Authentication schemas
    "LoginRequest", "LoginResponse", "RefreshTokenRequest", "RefreshTokenResponse",
    "RegisterRequest", "RegisterResponse", "PasswordResetRequest", "PasswordResetResponse",
    "PasswordResetConfirm", "ChangePasswordRequest", "CurrentUser", "SessionInfo",
    
    # Discussion schemas
    "DiscussionCreate", "DiscussionUpdate", "DiscussionResponse",
    "CommentCreate", "CommentUpdate", "CommentResponse",
    "VoteRequest", "VoteResponse", "DiscussionFlag", "CommentFlag",
    "DiscussionStats", "DiscussionSearch",
    
    # User matching schemas
    "UserMatchRequest", "UserMatchResponse", "UserMatchListResponse",
    "SkillAnalysisRequest", "SkillAnalysisResponse", "TeamFormationRequest",
    "TeamFormationResponse", "MatchFeedback", "MatchingPreferences",
    "MatchingPreferencesUpdate", "MatchingAnalytics",
    
    # API schemas
    "APIResponse", "APIError", "PaginatedResponse", "SearchResponse",
    "BulkOperationRequest", "BulkOperationResponse", "AdvancedSearchRequest",
    "AdvancedSearchResponse", "ExportRequest", "ExportResponse",
    "WebhookRequest", "WebhookResponse", "NotificationRequest", "NotificationResponse",
    "AnalyticsRequest", "AnalyticsResponse", "SystemStatusResponse", "APIMetadata",
]