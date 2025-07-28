"""
API-specific schemas for the AI Opportunity Browser.

This module contains schemas specifically designed for API endpoints,
including request/response models, error handling, and API metadata.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import Field, validator
from .base import BaseSchema, PaginationResponse


class APIResponse(BaseSchema):
    """Generic API response wrapper."""
    
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class APIError(BaseSchema):
    """API error response schema."""
    
    success: bool = False
    error_code: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseSchema):
    """Generic paginated response schema."""
    
    items: List[Any]
    pagination: PaginationResponse
    total_count: int
    filters_applied: Optional[Dict[str, Any]] = None


class SearchResponse(BaseSchema):
    """Search response with relevance scoring."""
    
    query: str
    results: List[Any]
    total_results: int
    search_time_ms: float
    suggestions: Optional[List[str]] = None
    filters_applied: Optional[Dict[str, Any]] = None
    pagination: Optional[PaginationResponse] = None


class BulkOperationRequest(BaseSchema):
    """Schema for bulk operations."""
    
    operation: str = Field(..., description="Operation type: create, update, delete")
    items: List[Dict[str, Any]] = Field(..., min_items=1, max_items=100)
    options: Optional[Dict[str, Any]] = None


class BulkOperationResponse(BaseSchema):
    """Schema for bulk operation responses."""
    
    operation: str
    total_items: int
    successful_items: int
    failed_items: int
    results: List[Dict[str, Any]]
    errors: Optional[List[Dict[str, Any]]] = None


class FilterRequest(BaseSchema):
    """Generic filter request schema."""
    
    field: str
    operator: str = Field(..., pattern="^(eq|ne|gt|gte|lt|lte|in|nin|contains|startswith|endswith)$")
    value: Union[str, int, float, bool, List[Any]]


class SortRequest(BaseSchema):
    """Generic sort request schema."""
    
    field: str
    direction: str = Field("asc", pattern="^(asc|desc)$")


class AdvancedSearchRequest(BaseSchema):
    """Advanced search request with filters and sorting."""
    
    query: Optional[str] = None
    filters: Optional[List[FilterRequest]] = None
    sort: Optional[List[SortRequest]] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    include_facets: bool = False
    highlight: bool = False


class FacetResponse(BaseSchema):
    """Faceted search response."""
    
    field: str
    values: List[Dict[str, Any]]  # [{"value": "AI/ML", "count": 42}, ...]


class AdvancedSearchResponse(BaseSchema):
    """Advanced search response with facets."""
    
    query: Optional[str] = None
    results: List[Any]
    total_results: int
    search_time_ms: float
    facets: Optional[List[FacetResponse]] = None
    suggestions: Optional[List[str]] = None
    pagination: PaginationResponse


class ExportRequest(BaseSchema):
    """Data export request schema."""
    
    format: str = Field(..., pattern="^(json|csv|xlsx)$")
    filters: Optional[Dict[str, Any]] = None
    fields: Optional[List[str]] = None
    include_metadata: bool = True


class ExportResponse(BaseSchema):
    """Data export response schema."""
    
    export_id: str
    format: str
    status: str  # pending, processing, completed, failed
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    file_size_bytes: Optional[int] = None
    record_count: Optional[int] = None


class WebhookRequest(BaseSchema):
    """Webhook registration request."""
    
    url: str = Field(..., pattern="^https?://")
    events: List[str] = Field(..., min_items=1)
    secret: Optional[str] = None
    active: bool = True
    description: Optional[str] = None


class WebhookResponse(BaseSchema):
    """Webhook registration response."""
    
    id: str
    url: str
    events: List[str]
    active: bool
    created_at: datetime
    last_triggered: Optional[datetime] = None
    delivery_count: int = 0
    failure_count: int = 0


class NotificationRequest(BaseSchema):
    """Notification request schema."""
    
    user_id: str
    type: str
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    priority: str = Field("normal", pattern="^(low|normal|high|urgent)$")
    channels: List[str] = Field(["in_app"], description="Notification channels")


class NotificationResponse(BaseSchema):
    """Notification response schema."""
    
    id: str
    user_id: str
    type: str
    title: str
    message: str
    read: bool = False
    created_at: datetime
    read_at: Optional[datetime] = None


class AnalyticsRequest(BaseSchema):
    """Analytics request schema."""
    
    metric: str
    start_date: datetime
    end_date: datetime
    granularity: str = Field("day", pattern="^(hour|day|week|month)$")
    filters: Optional[Dict[str, Any]] = None
    group_by: Optional[List[str]] = None


class AnalyticsResponse(BaseSchema):
    """Analytics response schema."""
    
    metric: str
    data_points: List[Dict[str, Any]]
    summary: Dict[str, Any]
    period: Dict[str, datetime]
    metadata: Optional[Dict[str, Any]] = None


class SystemStatusResponse(BaseSchema):
    """System status response schema."""
    
    status: str  # operational, degraded, maintenance, outage
    services: Dict[str, Dict[str, Any]]
    uptime_percentage: float
    response_time_ms: float
    last_updated: datetime
    incidents: Optional[List[Dict[str, Any]]] = None


class RateLimitInfo(BaseSchema):
    """Rate limit information schema."""
    
    limit: int
    remaining: int
    reset_at: datetime
    retry_after: Optional[int] = None


class APIMetadata(BaseSchema):
    """API metadata schema."""
    
    version: str
    environment: str
    request_id: str
    rate_limit: Optional[RateLimitInfo] = None
    processing_time_ms: float
    cached: bool = False