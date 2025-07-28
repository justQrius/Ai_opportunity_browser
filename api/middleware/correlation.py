"""
Correlation ID middleware for request tracking.

This middleware ensures that every request has a unique correlation ID
that can be used to trace requests across services and logs.
"""

import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from api.core.logging import correlation_id_var, request_id_var, user_id_var


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation IDs to requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID."""
        
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Extract user ID from request if available
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = str(request.state.user.id)
        
        # Set context variables
        correlation_id_var.set(correlation_id)
        request_id_var.set(request_id)
        if user_id:
            user_id_var.set(user_id)
        
        # Store in request state for access in endpoints
        request.state.correlation_id = correlation_id
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Request-ID"] = request_id
        
        return response