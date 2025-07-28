"""Market signal-related Pydantic schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import Field
from .base import BaseSchema, TimestampSchema, UUIDSchema
from shared.models.market_signal import SignalType


class MarketSignalBase(BaseSchema):
    """Base market signal schema."""
    
    source: str = Field(..., max_length=50, description="Data source: reddit, github, etc.")
    signal_type: SignalType
    title: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., description="Signal content")
    author: Optional[str] = Field(None, max_length=255)


class MarketSignalCreate(MarketSignalBase):
    """Schema for creating market signals.
    
    Supports Requirement 5.1 (Agentic AI Discovery Engine).
    """
    
    source_id: Optional[str] = Field(None, max_length=255)
    source_url: Optional[str] = Field(None, max_length=1000)
    raw_content: Optional[str] = Field(None, description="Original unprocessed content")
    author_reputation: Optional[float] = None
    extracted_at: datetime
    
    # Engagement metrics
    upvotes: Optional[int] = Field(None, ge=0)
    downvotes: Optional[int] = Field(None, ge=0)
    comments_count: Optional[int] = Field(None, ge=0)
    shares_count: Optional[int] = Field(None, ge=0)
    views_count: Optional[int] = Field(None, ge=0)
    
    # Keywords and categorization
    keywords: Optional[List[str]] = None
    categories: Optional[List[str]] = None


class MarketSignalResponse(MarketSignalBase, UUIDSchema, TimestampSchema):
    """Schema for market signal responses."""
    
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    author_reputation: Optional[float] = None
    
    # Engagement metrics
    upvotes: Optional[int] = None
    downvotes: Optional[int] = None
    comments_count: Optional[int] = None
    shares_count: Optional[int] = None
    views_count: Optional[int] = None
    
    # AI analysis results
    sentiment_score: float
    confidence_level: float
    pain_point_intensity: Optional[float] = None
    market_validation_signals: Optional[List[str]] = None
    
    # Processing metadata
    extracted_at: datetime
    processed_at: Optional[datetime] = None
    processing_version: Optional[str] = None
    
    # Keywords and categorization
    keywords: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    ai_relevance_score: Optional[float] = None
    
    # Relationship
    opportunity_id: Optional[str] = None


class MarketSignalUpdate(BaseSchema):
    """Schema for updating market signal analysis."""
    
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    confidence_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    pain_point_intensity: Optional[float] = Field(None, ge=0.0, le=1.0)
    market_validation_signals: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    ai_relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    opportunity_id: Optional[str] = None


class MarketSignalSearch(BaseSchema):
    """Schema for searching market signals."""
    
    source: Optional[str] = None
    signal_type: Optional[SignalType] = None
    min_sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    max_sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    min_confidence_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    keywords: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    opportunity_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class MarketSignalStats(BaseSchema):
    """Schema for market signal statistics."""
    
    total_signals: int
    signals_by_source: Dict[str, int]
    signals_by_type: Dict[str, int]
    average_sentiment: float
    average_confidence: float
    top_keywords: List[Dict[str, Any]]
    trending_categories: List[str]