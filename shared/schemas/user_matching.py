"""Pydantic schemas for user matching functionality."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import Field, validator
from enum import Enum

from .base import BaseSchema, UUIDSchema, TimestampSchema


class MatchingType(str, Enum):
    """Types of user matching algorithms."""
    INTEREST_BASED = "interest_based"
    SKILL_COMPLEMENTARY = "skill_complementary"
    COLLABORATION_HISTORY = "collaboration_history"
    EXPERTISE_OVERLAP = "expertise_overlap"
    HYBRID = "hybrid"


class UserMatchRequest(BaseSchema):
    """Request schema for finding user matches."""
    
    user_id: str = Field(..., description="ID of the user to find matches for")
    match_type: MatchingType = Field(default=MatchingType.INTEREST_BASED, description="Type of matching algorithm")
    opportunity_id: Optional[str] = Field(None, description="Optional opportunity context for skill matching")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of matches to return")
    min_match_score: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum match score threshold")
    include_reasons: bool = Field(default=True, description="Include detailed match reasons")


class SkillGapResponse(BaseSchema):
    """Schema for skill gap information."""
    
    skill_category: str = Field(..., description="Category of the skill (e.g., 'ai', 'technical', 'business')")
    skill_name: str = Field(..., description="Name of the specific skill")
    importance_score: float = Field(..., ge=0.0, le=1.0, description="Importance of this skill (0-1)")
    gap_severity: float = Field(..., ge=0.0, le=1.0, description="Severity of the gap (0-1, higher = more critical)")


class InterestProfileResponse(BaseSchema):
    """Schema for user interest profile."""
    
    ai_solution_preferences: Dict[str, float] = Field(default_factory=dict, description="AI type preferences with scores")
    industry_preferences: Dict[str, float] = Field(default_factory=dict, description="Industry preferences with scores")
    complexity_preference: Optional[str] = Field(None, description="Preferred complexity level")
    market_size_preference: Optional[str] = Field(None, description="Preferred market size")
    engagement_level: float = Field(..., ge=0.0, le=1.0, description="User engagement level (0-1)")
    activity_patterns: Dict[str, Any] = Field(default_factory=dict, description="User activity patterns")


class UserMatchResponse(BaseSchema):
    """Schema for user match results."""
    
    user_id: str = Field(..., description="Matched user ID")
    username: str = Field(..., description="Matched user username")
    full_name: Optional[str] = Field(None, description="Matched user full name")
    avatar_url: Optional[str] = Field(None, description="Matched user avatar URL")
    match_score: float = Field(..., ge=0.0, le=1.0, description="Match compatibility score (0-1)")
    match_type: MatchingType = Field(..., description="Type of matching algorithm used")
    match_reasons: List[str] = Field(default_factory=list, description="Reasons for the match")
    common_interests: List[str] = Field(default_factory=list, description="Shared interests")
    complementary_skills: List[str] = Field(default_factory=list, description="Skills that complement the user")
    expertise_domains: List[str] = Field(default_factory=list, description="User's expertise domains")
    reputation_score: float = Field(..., ge=0.0, description="User's reputation score")
    compatibility_factors: Dict[str, float] = Field(default_factory=dict, description="Detailed compatibility metrics")


class UserMatchListResponse(BaseSchema):
    """Schema for list of user matches."""
    
    matches: List[UserMatchResponse] = Field(..., description="List of user matches")
    total_count: int = Field(..., ge=0, description="Total number of matches found")
    algorithm_used: str = Field(..., description="Matching algorithm used")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="When matches were generated")
    user_id: str = Field(..., description="ID of the user matches were generated for")


class SkillAnalysisRequest(BaseSchema):
    """Request schema for skill analysis."""
    
    user_id: str = Field(..., description="User ID to analyze")
    opportunity_id: Optional[str] = Field(None, description="Optional opportunity context")
    include_gaps: bool = Field(default=True, description="Include skill gap analysis")
    include_recommendations: bool = Field(default=True, description="Include skill development recommendations")


class SkillAnalysisResponse(BaseSchema):
    """Schema for skill analysis results."""
    
    user_id: str = Field(..., description="Analyzed user ID")
    current_skills: Dict[str, float] = Field(default_factory=dict, description="Current skills with proficiency scores")
    skill_gaps: List[SkillGapResponse] = Field(default_factory=list, description="Identified skill gaps")
    skill_recommendations: List[str] = Field(default_factory=list, description="Recommended skills to develop")
    complementary_skill_needs: List[str] = Field(default_factory=list, description="Skills needed from collaborators")
    skill_categories: Dict[str, List[str]] = Field(default_factory=dict, description="Skills grouped by category")
    analysis_context: Optional[str] = Field(None, description="Context used for analysis (e.g., opportunity ID)")


class CollaborationSuggestion(BaseSchema):
    """Schema for collaboration suggestions."""
    
    suggested_user: UserMatchResponse = Field(..., description="Suggested collaborator")
    collaboration_type: str = Field(..., description="Type of collaboration (co-founder, advisor, contractor)")
    project_fit_score: float = Field(..., ge=0.0, le=1.0, description="How well they fit the project")
    collaboration_benefits: List[str] = Field(default_factory=list, description="Benefits of this collaboration")
    potential_challenges: List[str] = Field(default_factory=list, description="Potential collaboration challenges")
    recommended_next_steps: List[str] = Field(default_factory=list, description="Suggested next steps")


class TeamFormationRequest(BaseSchema):
    """Request schema for team formation recommendations."""
    
    user_id: str = Field(..., description="User ID forming the team")
    opportunity_id: str = Field(..., description="Opportunity context for team formation")
    team_size_preference: Optional[int] = Field(None, ge=2, le=10, description="Preferred team size")
    required_roles: List[str] = Field(default_factory=list, description="Required team roles")
    budget_constraint: Optional[str] = Field(None, description="Budget constraint level")
    timeline_constraint: Optional[str] = Field(None, description="Timeline constraint")


class TeamFormationResponse(BaseSchema):
    """Schema for team formation recommendations."""
    
    user_id: str = Field(..., description="User ID who requested team formation")
    opportunity_id: str = Field(..., description="Opportunity context")
    recommended_team_size: int = Field(..., ge=2, description="Recommended team size")
    collaboration_suggestions: List[CollaborationSuggestion] = Field(
        default_factory=list, 
        description="Suggested collaborators"
    )
    team_composition_analysis: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Analysis of recommended team composition"
    )
    skill_coverage_analysis: Dict[str, float] = Field(
        default_factory=dict, 
        description="How well the team covers required skills"
    )
    estimated_success_probability: float = Field(
        ..., ge=0.0, le=1.0, 
        description="Estimated probability of team success"
    )
    formation_recommendations: List[str] = Field(
        default_factory=list, 
        description="Recommendations for team formation process"
    )


class MatchingPreferences(BaseSchema):
    """Schema for user matching preferences."""
    
    preferred_match_types: List[MatchingType] = Field(
        default_factory=lambda: [MatchingType.INTEREST_BASED], 
        description="Preferred matching algorithms"
    )
    min_reputation_score: float = Field(default=1.0, ge=0.0, description="Minimum reputation score for matches")
    max_distance_km: Optional[float] = Field(None, ge=0.0, description="Maximum geographic distance in km")
    preferred_collaboration_types: List[str] = Field(
        default_factory=list, 
        description="Preferred types of collaboration"
    )
    availability_status: str = Field(default="available", description="Current availability status")
    communication_preferences: List[str] = Field(
        default_factory=list, 
        description="Preferred communication methods"
    )
    
    @validator('preferred_match_types')
    def validate_match_types(cls, v):
        """Validate that at least one match type is specified."""
        if not v:
            raise ValueError("At least one match type must be specified")
        return v


class MatchingPreferencesUpdate(BaseSchema):
    """Schema for updating matching preferences."""
    
    preferred_match_types: Optional[List[MatchingType]] = None
    min_reputation_score: Optional[float] = Field(None, ge=0.0)
    max_distance_km: Optional[float] = Field(None, ge=0.0)
    preferred_collaboration_types: Optional[List[str]] = None
    availability_status: Optional[str] = None
    communication_preferences: Optional[List[str]] = None


class MatchFeedback(BaseSchema):
    """Schema for feedback on user matches."""
    
    match_id: str = Field(..., description="ID of the match being rated")
    matched_user_id: str = Field(..., description="ID of the matched user")
    feedback_score: int = Field(..., ge=1, le=5, description="Feedback score (1-5)")
    feedback_text: Optional[str] = Field(None, max_length=1000, description="Optional feedback text")
    match_quality_rating: int = Field(..., ge=1, le=5, description="Quality of the match (1-5)")
    would_collaborate: bool = Field(..., description="Would consider collaborating with this user")
    feedback_categories: List[str] = Field(
        default_factory=list, 
        description="Categories of feedback (e.g., 'skills', 'communication', 'availability')"
    )


class MatchingAnalytics(BaseSchema):
    """Schema for matching system analytics."""
    
    total_matches_generated: int = Field(..., ge=0, description="Total matches generated")
    average_match_score: float = Field(..., ge=0.0, le=1.0, description="Average match score")
    match_type_distribution: Dict[str, int] = Field(
        default_factory=dict, 
        description="Distribution of match types"
    )
    user_engagement_rate: float = Field(..., ge=0.0, le=1.0, description="User engagement with matches")
    successful_collaborations: int = Field(..., ge=0, description="Number of successful collaborations")
    feedback_summary: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Summary of user feedback"
    )
    algorithm_performance: Dict[str, float] = Field(
        default_factory=dict, 
        description="Performance metrics for each algorithm"
    )