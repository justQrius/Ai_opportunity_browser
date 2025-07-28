"""
Event Bus Middleware for FastAPI

This middleware integrates the event bus system with the FastAPI application,
enabling automatic event publishing for API operations and request tracking.
"""

import asyncio
import logging
import time
import uuid
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from shared.event_publishers import SystemEventPublisher
from shared.event_bus import EventType

logger = logging.getLogger(__name__)


class EventBusMiddleware(BaseHTTPMiddleware):
    """
    Middleware that publishes system events for API requests and responses.
    
    Features:
    - Request/response tracking
    - Performance monitoring
    - Error event publishing
    - Health check events
    """
    
    def __init__(self, app, enable_request_events: bool = True, enable_health_events: bool = True):
        super().__init__(app)
        self.enable_request_events = enable_request_events
        self.enable_health_events = enable_health_events
        self.system_publisher = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure the event publisher is initialized."""
        if not self._initialized:
            try:
                self.system_publisher = SystemEventPublisher()
                self._initialized = True
            except Exception as e:
                logger.warning(f"Failed to initialize event publisher: {e}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and publish events."""
        await self._ensure_initialized()
        
        # Generate correlation ID for request tracking
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Record start time
        start_time = time.time()
        
        # Publish request started event (if enabled)
        if self.enable_request_events and self.system_publisher:
            try:
                await self._publish_request_started(request, correlation_id)
            except Exception as e:
                logger.warning(f"Failed to publish request started event: {e}")
        
        # Process request
        response = None
        error = None
        
        try:
            response = await call_next(request)
        except Exception as e:
            error = e
            # Create error response
            response = Response(
                content=f"Internal Server Error: {str(e)}",
                status_code=500,
                media_type="text/plain"
            )
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Publish response/error events
        if self.system_publisher:
            try:
                if error:
                    await self._publish_request_error(request, error, response_time, correlation_id)
                else:
                    await self._publish_request_completed(request, response, response_time, correlation_id)
                
                # Publish health check events for specific endpoints
                if self.enable_health_events and request.url.path in ["/health", "/status"]:
                    await self._publish_health_check(request, response, response_time)
                    
            except Exception as e:
                logger.warning(f"Failed to publish response event: {e}")
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
    
    async def _publish_request_started(self, request: Request, correlation_id: str):
        """Publish request started event."""
        await self.system_publisher.publish(
            "api.request_started",
            {
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "user_agent": request.headers.get("user-agent"),
                "client_ip": request.client.host if request.client else None
            },
            metadata={
                "correlation_id": correlation_id,
                "component": "api_middleware"
            }
        )
    
    async def _publish_request_completed(
        self, 
        request: Request, 
        response: Response, 
        response_time: float, 
        correlation_id: str
    ):
        """Publish request completed event."""
        await self.system_publisher.publish(
            "api.request_completed",
            {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "success": 200 <= response.status_code < 400
            },
            metadata={
                "correlation_id": correlation_id,
                "component": "api_middleware"
            }
        )
    
    async def _publish_request_error(
        self, 
        request: Request, 
        error: Exception, 
        response_time: float, 
        correlation_id: str
    ):
        """Publish request error event."""
        await self.system_publisher.system_error(
            component="api",
            error_message=str(error),
            severity="high",
            error_code=type(error).__name__,
            method=request.method,
            path=request.url.path,
            response_time_ms=response_time,
            correlation_id=correlation_id
        )
    
    async def _publish_health_check(self, request: Request, response: Response, response_time: float):
        """Publish health check event."""
        status = "healthy" if response.status_code == 200 else "unhealthy"
        
        await self.system_publisher.health_check(
            component="api",
            status=status,
            response_time_ms=response_time,
            details={
                "endpoint": request.url.path,
                "status_code": response.status_code
            }
        )


class EventContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds event publishing context to requests.
    
    This middleware makes event publishers available in request context
    for use in route handlers.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add event publishers to request state."""
        # Add event publishers to request state
        request.state.event_publishers = {
            "system": SystemEventPublisher(correlation_id=getattr(request.state, 'correlation_id', None)),
            # Add other publishers as needed
        }
        
        response = await call_next(request)
        return response


# Utility functions for route handlers
async def publish_api_event(request: Request, event_type: str, payload: dict):
    """
    Utility function to publish events from route handlers.
    
    Args:
        request: FastAPI request object
        event_type: Type of event to publish
        payload: Event payload data
    """
    if hasattr(request.state, 'event_publishers'):
        system_publisher = request.state.event_publishers.get('system')
        if system_publisher:
            await system_publisher.publish(event_type, payload)


async def publish_operation_event(
    request: Request, 
    operation: str, 
    resource_type: str, 
    resource_id: str, 
    success: bool = True,
    details: Optional[dict] = None
):
    """
    Utility function to publish operation events from route handlers.
    
    Args:
        request: FastAPI request object
        operation: Operation type (create, update, delete, etc.)
        resource_type: Type of resource (opportunity, user, etc.)
        resource_id: ID of the resource
        success: Whether the operation was successful
        details: Additional operation details
    """
    if hasattr(request.state, 'event_publishers'):
        system_publisher = request.state.event_publishers.get('system')
        if system_publisher:
            await system_publisher.publish(
                f"api.{operation}_{resource_type}",
                {
                    "operation": operation,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "success": success,
                    "details": details or {},
                    "user_id": getattr(request.state, 'user_id', None),
                    "method": request.method,
                    "path": request.url.path
                }
            )


# Example usage in route handlers:
"""
from fastapi import APIRouter, Request, Depends
from .middleware.event_middleware import publish_operation_event

router = APIRouter()

@router.post("/opportunities")
async def create_opportunity(
    request: Request,
    opportunity_data: OpportunityCreate,
    current_user: User = Depends(get_current_user)
):
    # Create opportunity
    opportunity = await opportunity_service.create(opportunity_data)
    
    # Publish operation event
    await publish_operation_event(
        request,
        operation="create",
        resource_type="opportunity",
        resource_id=opportunity.id,
        success=True,
        details={
            "title": opportunity.title,
            "ai_solution_type": opportunity.ai_solution_type
        }
    )
    
    return opportunity
"""