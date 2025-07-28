"""Opportunity-related Pydantic schemas."""

from typing import Optional, List, Dict, Any
from pydantic import Field, validator
from .base import BaseSchema, TimestampSchema, UUIDSchema, PaginationRequest
from shared.models.opportunity import OpportunityStatus


class OpportunityBase(BaseSchema):
    """Base opportunity schema with common fields."""
    
    title: str = Field(..., min_length=10, max_length=255)
    description: str = Field(..., min_length=50)
    summary: Optional[str] = Field(None, max_length=500)
    ai_solution_types: Optional[List[str]] = Field(None, description="AI solution types: ML, NLP, CV, etc.")
    target_industries: Optional[List[str]] = Field(None, description="Target industries")
    geographic_scope: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = Field(None, description="Categorization tags")


class OpportunityCreate(OpportunityBase):
    """Schema for creating a new opportunity.
    
    Supports Requirements 1.1-1.4 (Opportunity Discovery System).
    """
    
    required_capabilities: Optional[List[str]] = Field(None, description="Required AI capabilities")
    source_urls: Optional[List[str]] = Field(None, description="Source URLs for discovery")
    discovery_method: Optional[str] = Field(None, max_length=100)


class OpportunityUpdate(BaseSchema):
    """Schema for updating opportunity information."""
    
    title: Optional[str] = Field(None, min_length=10, max_length=255)
    description: Optional[str] = Field(None, min_length=50)
    summary: Optional[str] = Field(None, max_length=500)
    status: Optional[OpportunityStatus] = None
    ai_solution_types: Optional[List[str]] = None
    target_industries: Optional[List[str]] = None
    geographic_scope: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    competitive_advantage: Optional[str] = None


class OpportunityResponse(OpportunityBase, UUIDSchema, TimestampSchema):
    """Schema for opportunity responses.
    
    Supports Requirements 3.1-3.5 (User-Friendly Opportunity Browser).
    """
    
    status: OpportunityStatus
    required_capabilities: Optional[List[str]] = None
    
    # Scoring and validation (Requirement 2.3, 2.5)
    validation_score: float
    confidence_rating: float
    ai_feasibility_score: float
    
    # Market analysis (Requirement 1.3)
    market_size_estimate: Optional[Dict[str, Any]] = None
    competition_analysis: Optional[Dict[str, Any]] = None
    competitive_advantage: Optional[str] = None
    
    # Implementation guidance (Requirements 7.1-7.5)
    implementation_complexity: Optional[str] = None
    estimated_development_time: Optional[int] = None
    required_team_size: Optional[int] = None
    estimated_budget_range: Optional[str] = None
    
    # Business intelligence (Requirements 8.1-8.5)
    revenue_projections: Optional[Dict[str, Any]] = None
    monetization_strategies: Optional[List[str]] = None
    go_to_market_strategy: Optional[Dict[str, Any]] = None
    
    # Metadata
    source_urls: Optional[List[str]] = None
    discovery_method: Optional[str] = None


class OpportunityListResponse(BaseSchema):
    """Schema for paginated opportunity list responses."""
    
    opportunities: List[OpportunityResponse]
    pagination: Dict[str, Any]


class OpportunitySearchRequest(PaginationRequest):
    """Schema for opportunity search requests.
    
    Supports Requirements 3.1-3.2 (Searchable interface and filtering).
    """
    
    query: Optional[str] = Field(None, description="Search query")
    ai_solution_types: Optional[List[str]] = Field(None, description="Filter by AI solution types")
    target_industries: Optional[List[str]] = Field(None, description="Filter by industries")
    min_validation_score: Optional[float] = Field(None, ge=0.0, le=10.0)
    max_validation_score: Optional[float] = Field(None, ge=0.0, le=10.0)
    min_market_size: Optional[int] = Field(None, ge=0)
    status: Optional[List[OpportunityStatus]] = Field(None, description="Filter by status")
    implementation_complexity: Optional[List[str]] = Field(None, description="Filter by complexity")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    geographic_scope: Optional[str] = Field(None, description="Filter by geographic scope")
    
    @validator('max_validation_score')
    def validate_score_range(cls, v, values):
        """Ensure max score is greater than min score."""
        if v is not None and 'min_validation_score' in values and values['min_validation_score'] is not None:
            if v < values['min_validation_score']:
                raise ValueError('max_validation_score must be greater than min_validation_score')
        return v


class OpportunityRecommendationRequest(BaseSchema):
    """Schema for personalized opportunity recommendations.
    
    Supports Requirement 3.5 (Personalized recommendations).
    """
    
    user_id: str
    limit: int = Field(10, ge=1, le=50)
    include_viewed: bool = Field(False, description="Include previously viewed opportunities")
    ai_solution_types: Optional[List[str]] = Field(None, description="Preferred AI solution types")
    industries: Optional[List[str]] = Field(None, description="Preferred industries")


class OpportunityStats(BaseSchema):
    """Schema for opportunity statistics and analytics."""
    
    total_opportunities: int
    opportunities_by_status: Dict[str, int]
    opportunities_by_ai_type: Dict[str, int]
    opportunities_by_industry: Dict[str, int]
    average_validation_score: float
    trending_opportunities: List[OpportunityResponse]


class OpportunityBookmark(BaseSchema):
    """Schema for user opportunity bookmarks.
    
    Supports Requirement 3.4 (Save to personal collections).
    """
    
    user_id: str
    opportunity_id: str
    collection_name: Optional[str] = Field(None, description="Optional collection name")
    notes: Optional[str] = Field(None, max_length=1000, description="User notes")