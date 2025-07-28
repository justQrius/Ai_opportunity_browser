"""Validation-related Pydantic schemas."""

from typing import Optional, List
from pydantic import Field, validator
from .base import BaseSchema, TimestampSchema, UUIDSchema
from shared.models.validation import ValidationType


class ValidationBase(BaseSchema):
    """Base validation schema."""
    
    validation_type: ValidationType
    score: float = Field(..., ge=1.0, le=10.0, description="Validation score (1-10 scale)")
    confidence: float = Field(5.0, ge=1.0, le=10.0, description="Confidence in validation (1-10 scale)")


class ValidationCreate(ValidationBase):
    """Schema for creating validations.
    
    Supports Requirements 2.1-2.5 (Opportunity Validation Framework).
    """
    
    opportunity_id: str
    comments: Optional[str] = Field(None, max_length=2000)
    strengths: Optional[str] = Field(None, max_length=1000)
    weaknesses: Optional[str] = Field(None, max_length=1000)
    recommendations: Optional[str] = Field(None, max_length=1000)
    evidence_links: Optional[List[str]] = Field(None, description="Supporting evidence URLs")
    supporting_data: Optional[dict] = Field(None, description="Additional supporting data")
    methodology: Optional[str] = Field(None, max_length=100, description="Validation methodology")
    time_spent_minutes: Optional[int] = Field(None, ge=0, le=480, description="Time spent on validation")
    expertise_relevance: Optional[float] = Field(None, ge=0.0, le=10.0, description="Relevance of validator's expertise")


class ValidationUpdate(BaseSchema):
    """Schema for updating validations."""
    
    score: Optional[float] = Field(None, ge=1.0, le=10.0)
    confidence: Optional[float] = Field(None, ge=1.0, le=10.0)
    comments: Optional[str] = Field(None, max_length=2000)
    strengths: Optional[str] = Field(None, max_length=1000)
    weaknesses: Optional[str] = Field(None, max_length=1000)
    recommendations: Optional[str] = Field(None, max_length=1000)
    evidence_links: Optional[List[str]] = None
    supporting_data: Optional[dict] = None


class ValidationResponse(ValidationBase, UUIDSchema, TimestampSchema):
    """Schema for validation responses.
    
    Supports Requirements 4.3-4.4 (Community validation tracking).
    """
    
    opportunity_id: str
    validator_id: str
    comments: Optional[str] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    recommendations: Optional[str] = None
    evidence_links: Optional[List[str]] = None
    supporting_data: Optional[dict] = None
    methodology: Optional[str] = None
    time_spent_minutes: Optional[int] = None
    expertise_relevance: Optional[float] = None
    
    # Quality control
    is_flagged: bool
    flag_reason: Optional[str] = None
    moderator_reviewed: bool
    
    # Community feedback
    helpful_votes: int
    unhelpful_votes: int
    
    # Validator information (from relationship)
    validator_username: Optional[str] = None
    validator_reputation: Optional[float] = None


class ValidationVote(BaseSchema):
    """Schema for voting on validation helpfulness."""
    
    validation_id: str
    is_helpful: bool = Field(..., description="True for helpful, False for unhelpful")


class ValidationFlag(BaseSchema):
    """Schema for flagging inappropriate validations."""
    
    validation_id: str
    reason: str = Field(..., max_length=255, description="Reason for flagging")
    details: Optional[str] = Field(None, max_length=1000, description="Additional details")


class ValidationStats(BaseSchema):
    """Schema for validation statistics."""
    
    total_validations: int
    validations_by_type: dict
    average_score: float
    average_confidence: float
    top_validators: List[dict]
    validation_trends: dict


class ValidationSummary(BaseSchema):
    """Schema for opportunity validation summary.
    
    Supports Requirement 2.3 (Confidence ratings based on community feedback).
    """
    
    opportunity_id: str
    total_validations: int
    average_score: float
    confidence_rating: float
    validations_by_type: dict
    consensus_strengths: List[str]
    consensus_weaknesses: List[str]
    top_recommendations: List[str]
    validation_quality_score: float  # Based on validator reputation and evidence quality