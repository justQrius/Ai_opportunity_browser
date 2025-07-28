"""Implementation guide-related Pydantic schemas."""

from typing import Optional, List, Dict, Any
from pydantic import Field
from .base import BaseSchema, TimestampSchema, UUIDSchema


class ImplementationGuideResponse(UUIDSchema, TimestampSchema):
    """Schema for implementation guide responses.
    
    Supports Requirements 7.1-7.5 (Implementation Guidance System).
    """
    
    opportunity_id: str
    
    # Technical architecture
    technical_architecture: Optional[Dict[str, Any]] = Field(None, description="Architecture diagram/description")
    system_components: Optional[List[str]] = Field(None, description="System components")
    data_flow: Optional[Dict[str, Any]] = Field(None, description="Data flow description")
    
    # Development phases
    development_phases: Optional[List[Dict[str, Any]]] = Field(None, description="Development phases")
    milestone_timeline: Optional[Dict[str, Any]] = Field(None, description="Timeline with milestones")
    critical_path: Optional[List[str]] = Field(None, description="Critical path items")
    
    # Team requirements
    required_team_skills: Optional[List[str]] = Field(None, description="Required skills")
    team_composition: Optional[Dict[str, Any]] = Field(None, description="Recommended team structure")
    estimated_team_size: Optional[int] = Field(None, ge=1, description="Estimated team size")
    key_roles: Optional[List[str]] = Field(None, description="Key roles needed")
    
    # Budget estimates
    estimated_budget: Optional[Dict[str, Any]] = Field(None, description="Budget breakdown")
    cost_categories: Optional[List[str]] = Field(None, description="Cost categories")
    funding_requirements: Optional[Dict[str, Any]] = Field(None, description="Funding needs by phase")
    
    # Go-to-market strategy
    go_to_market_strategy: Optional[Dict[str, Any]] = Field(None, description="GTM strategy details")
    target_customer_segments: Optional[List[str]] = Field(None, description="Customer segments")
    marketing_channels: Optional[List[str]] = Field(None, description="Marketing channels")
    pricing_strategy: Optional[Dict[str, Any]] = Field(None, description="Pricing recommendations")
    
    # Risk management
    implementation_risks: Optional[List[str]] = Field(None, description="Implementation risks")
    risk_mitigation_plans: Optional[List[Dict[str, Any]]] = Field(None, description="Risk mitigation strategies")
    contingency_plans: Optional[List[Dict[str, Any]]] = Field(None, description="Backup plans")
    
    # Success metrics
    success_metrics: Optional[List[str]] = Field(None, description="KPIs and success metrics")
    validation_criteria: Optional[List[str]] = Field(None, description="Success validation criteria")
    
    # Resources and references
    learning_resources: Optional[List[Dict[str, Any]]] = Field(None, description="Educational resources")
    reference_implementations: Optional[List[Dict[str, Any]]] = Field(None, description="Similar implementations")
    useful_tools: Optional[List[str]] = Field(None, description="Recommended tools")
    
    # Guide metadata
    guide_version: Optional[str] = None
    generated_by_agent: Optional[str] = None
    last_updated_by: Optional[str] = None


class ImplementationGuideUpdate(BaseSchema):
    """Schema for updating implementation guides."""
    
    technical_architecture: Optional[Dict[str, Any]] = None
    system_components: Optional[List[str]] = None
    data_flow: Optional[Dict[str, Any]] = None
    development_phases: Optional[List[Dict[str, Any]]] = None
    milestone_timeline: Optional[Dict[str, Any]] = None
    critical_path: Optional[List[str]] = None
    required_team_skills: Optional[List[str]] = None
    team_composition: Optional[Dict[str, Any]] = None
    estimated_team_size: Optional[int] = Field(None, ge=1)
    key_roles: Optional[List[str]] = None
    estimated_budget: Optional[Dict[str, Any]] = None
    go_to_market_strategy: Optional[Dict[str, Any]] = None
    target_customer_segments: Optional[List[str]] = None
    marketing_channels: Optional[List[str]] = None
    pricing_strategy: Optional[Dict[str, Any]] = None
    implementation_risks: Optional[List[str]] = None
    risk_mitigation_plans: Optional[List[Dict[str, Any]]] = None
    success_metrics: Optional[List[str]] = None
    learning_resources: Optional[List[Dict[str, Any]]] = None
    useful_tools: Optional[List[str]] = None


class DevelopmentPhase(BaseSchema):
    """Schema for development phase information."""
    
    phase_name: str
    description: str
    duration_weeks: int = Field(..., ge=1)
    deliverables: List[str]
    dependencies: Optional[List[str]] = None
    required_skills: List[str]
    estimated_cost: Optional[float] = None
    success_criteria: List[str]


class TeamRole(BaseSchema):
    """Schema for team role requirements."""
    
    role_name: str
    description: str
    required_skills: List[str]
    experience_level: str  # junior, mid, senior, expert
    time_commitment: str  # full-time, part-time, consultant
    estimated_salary_range: Optional[Dict[str, float]] = None


class BudgetCategory(BaseSchema):
    """Schema for budget category breakdown."""
    
    category_name: str
    description: str
    estimated_cost: float
    cost_type: str  # one-time, monthly, annual
    priority: str  # essential, important, nice-to-have
    cost_breakdown: Optional[Dict[str, float]] = None


class MarketingChannel(BaseSchema):
    """Schema for marketing channel information."""
    
    channel_name: str
    description: str
    target_audience: str
    estimated_cost: Optional[float] = None
    expected_roi: Optional[float] = None
    timeline: Optional[str] = None
    success_metrics: List[str]


class ImplementationRisk(BaseSchema):
    """Schema for implementation risk details."""
    
    risk_name: str
    description: str
    probability: float = Field(..., ge=0.0, le=1.0)
    impact: str  # low, medium, high, critical
    mitigation_strategy: str
    contingency_plan: Optional[str] = None
    owner: Optional[str] = None