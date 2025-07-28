"""AI capability assessment-related Pydantic schemas."""

from typing import Optional, List, Dict, Any
from pydantic import Field
from .base import BaseSchema, TimestampSchema, UUIDSchema
from shared.models.ai_capability import ComplexityLevel


class AICapabilityResponse(UUIDSchema, TimestampSchema):
    """Schema for AI capability assessment responses.
    
    Supports Requirements 5.5 (Capability Agents) and 7.4 (Technical Implementation).
    """
    
    opportunity_id: str
    
    # Required AI capabilities
    required_capabilities: List[str] = Field(..., description="List of required AI capabilities")
    primary_ai_type: Optional[str] = Field(None, description="Primary AI type: nlp, computer_vision, ml, etc.")
    secondary_ai_types: Optional[List[str]] = Field(None, description="Secondary AI types")
    
    # Model availability and recommendations
    recommended_models: Optional[List[str]] = Field(None, description="Recommended AI models")
    model_availability: Optional[Dict[str, Any]] = Field(None, description="Model availability status")
    api_requirements: Optional[List[str]] = Field(None, description="Required APIs")
    
    # Implementation complexity
    implementation_complexity: ComplexityLevel
    estimated_development_time: Optional[int] = Field(None, description="Estimated development time in days")
    required_expertise_level: Optional[str] = Field(None, description="Required expertise level")
    
    # Technical requirements
    compute_requirements: Optional[Dict[str, Any]] = Field(None, description="Compute resource needs")
    data_requirements: Optional[Dict[str, Any]] = Field(None, description="Data requirements")
    infrastructure_needs: Optional[Dict[str, Any]] = Field(None, description="Infrastructure requirements")
    
    # Risk assessment
    technical_risks: Optional[List[str]] = Field(None, description="Technical risks")
    risk_mitigation_strategies: Optional[List[str]] = Field(None, description="Risk mitigation approaches")
    
    # Cost estimates
    development_cost_estimate: Optional[Dict[str, Any]] = Field(None, description="Development cost breakdown")
    operational_cost_estimate: Optional[Dict[str, Any]] = Field(None, description="Ongoing operational costs")
    
    # Technology stack recommendations
    recommended_frameworks: Optional[List[str]] = Field(None, description="Recommended frameworks")
    programming_languages: Optional[List[str]] = Field(None, description="Recommended programming languages")
    deployment_platforms: Optional[List[str]] = Field(None, description="Deployment platform options")
    
    # Assessment metadata
    assessment_version: Optional[str] = None
    assessed_by_agent: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence in assessment")


class AICapabilityUpdate(BaseSchema):
    """Schema for updating AI capability assessments."""
    
    required_capabilities: Optional[List[str]] = None
    primary_ai_type: Optional[str] = None
    secondary_ai_types: Optional[List[str]] = None
    recommended_models: Optional[List[str]] = None
    model_availability: Optional[Dict[str, Any]] = None
    api_requirements: Optional[List[str]] = None
    implementation_complexity: Optional[ComplexityLevel] = None
    estimated_development_time: Optional[int] = None
    required_expertise_level: Optional[str] = None
    technical_risks: Optional[List[str]] = None
    risk_mitigation_strategies: Optional[List[str]] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class AICapabilityStats(BaseSchema):
    """Schema for AI capability statistics."""
    
    total_assessments: int
    assessments_by_complexity: Dict[str, int]
    assessments_by_ai_type: Dict[str, int]
    average_development_time: Optional[float] = None
    most_common_capabilities: List[str]
    trending_technologies: List[str]
    risk_frequency: Dict[str, int]


class AIModelAvailability(BaseSchema):
    """Schema for AI model availability information."""
    
    model_name: str
    provider: str  # openai, anthropic, google, etc.
    availability_status: str  # available, limited, unavailable
    cost_per_token: Optional[float] = None
    rate_limits: Optional[Dict[str, Any]] = None
    capabilities: List[str]
    performance_metrics: Optional[Dict[str, Any]] = None
    last_updated: Optional[str] = None


class TechnicalRisk(BaseSchema):
    """Schema for technical risk information."""
    
    risk_type: str
    severity: str  # low, medium, high, critical
    probability: float = Field(..., ge=0.0, le=1.0)
    impact: str
    mitigation_strategy: str
    estimated_cost: Optional[float] = None