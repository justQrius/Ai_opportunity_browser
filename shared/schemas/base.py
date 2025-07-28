"""Base Pydantic schemas for API serialization."""

from datetime import datetime
from typing import Optional, Generic, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar('T')


class BaseSchema(BaseModel):
    """Base Pydantic schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
    )


class TimestampSchema(BaseSchema):
    """Schema mixin for timestamp fields."""
    
    created_at: datetime
    updated_at: datetime


class UUIDSchema(BaseSchema):
    """Schema mixin for UUID primary key."""
    
    id: str


class PaginationRequest(BaseSchema):
    """Schema for pagination parameters."""
    
    page: int = 1
    page_size: int = 20
    
    def get_offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.page_size


class PaginationResponse(BaseSchema):
    """Schema for paginated responses."""
    
    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_previous: bool
    
    @classmethod
    def create(
        cls, 
        page: int, 
        page_size: int, 
        total_count: int
    ) -> "PaginationResponse":
        """Create pagination response from parameters."""
        total_pages = (total_count + page_size - 1) // page_size
        
        return cls(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )


class ErrorResponse(BaseSchema):
    """Schema for error responses."""
    
    error_code: str
    error_message: str
    error_details: Optional[dict] = None
    timestamp: datetime = datetime.utcnow()


class PaginatedResponse(BaseSchema):
    """Schema for paginated list responses."""
    
    items: list
    pagination: PaginationResponse
    total_count: int
    filters_applied: Optional[dict] = None


class APIResponse(BaseSchema, Generic[T]):
    """Schema for general API responses."""
    
    success: bool = True
    message: str
    data: Optional[T] = None


class HealthResponse(BaseSchema):
    """Schema for health check responses."""
    
    status: str  # healthy, degraded, unhealthy
    message: str
    services: Optional[dict] = None
    timestamp: str