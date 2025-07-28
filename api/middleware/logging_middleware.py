"""
Logging middleware for FastAPI to handle correlation IDs and request tracking.

This middleware automatically:
- Generates or extracts correlation IDs from requests
- Sets up request context for logging
- Adds correlation headers to responses
- Logs request/response information
"""

import time
import uuid
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from shared.logging_config import (
    get_logger,
    set_correlation_id,
    set_request_id,
    set_user_id,
    get_correlation_id,
    RequestContext
)
from shared.monitoring import get_metrics_collector

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request logging and correlation ID tracking."""
    
    def __init__(
        self,
        app: ASGIApp,
        correlation_header: str = "X-Correlation-ID",
        request_id_header: str = "X-Request-ID",
        user_id_header: str = "X-User-ID",
        skip_paths: Optional[list] = None
    ):
        """
        Initialize logging middleware.
        
        Args:
            app: ASGI application
            correlation_header: Header name for correlation ID
            request_id_header: Header name for request ID
            user_id_header: Header name for user ID
            skip_paths: List of paths to skip logging for
        """
        super().__init__(app)
        self.correlation_header = correlation_header
        self.request_id_header = request_id_header
        self.user_id_header = user_id_header
        self.skip_paths = skip_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        self.metrics = get_metrics_collector()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging and correlation tracking."""
        # Skip logging for certain paths
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)
        
        # Extract or generate correlation ID
        correlation_id = (
            request.headers.get(self.correlation_header) or
            str(uuid.uuid4())
        )
        
        # Extract or generate request ID
        request_id = (
            request.headers.get(self.request_id_header) or
            str(uuid.uuid4())
        )
        
        # Extract user ID if available
        user_id = request.headers.get(self.user_id_header)
        
        # Set up request context
        with RequestContext(request_id, correlation_id, user_id):
            start_time = time.time()
            
            # Log request start
            await self._log_request_start(request, correlation_id, request_id, user_id)
            
            try:
                # Process request
                response = await call_next(request)
                
                # Calculate duration
                duration = time.time() - start_time
                
                # Add correlation headers to response
                response.headers[self.correlation_header] = correlation_id
                response.headers[self.request_id_header] = request_id
                if user_id:
                    response.headers[self.user_id_header] = user_id
                
                # Log successful response
                await self._log_request_success(
                    request, response, correlation_id, request_id, user_id, duration
                )
                
                # Record metrics
                self.metrics.record_http_request(
                    method=request.method,
                    endpoint=self._get_endpoint_pattern(request),
                    status_code=response.status_code,
                    duration=duration
                )
                
                return response
                
            except Exception as exc:
                # Calculate duration
                duration = time.time() - start_time
                
                # Log error
                await self._log_request_error(
                    request, exc, correlation_id, request_id, user_id, duration
                )
                
                # Record error metrics
                self.metrics.record_http_request(
                    method=request.method,
                    endpoint=self._get_endpoint_pattern(request),
                    status_code=500,
                    duration=duration
                )
                
                # Return error response with correlation headers
                error_response = JSONResponse(
                    status_code=500,
                    content={
                        "error": "Internal Server Error",
                        "correlation_id": correlation_id,
                        "request_id": request_id
                    }
                )
                error_response.headers[self.correlation_header] = correlation_id
                error_response.headers[self.request_id_header] = request_id
                if user_id:
                    error_response.headers[self.user_id_header] = user_id
                
                return error_response
    
    async def _log_request_start(
        self,
        request: Request,
        correlation_id: str,
        request_id: str,
        user_id: Optional[str]
    ) -> None:
        """Log request start information."""
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params) if request.query_params else None,
            client_ip=client_ip,
            user_agent=user_agent,
            content_type=request.headers.get("content-type"),
            content_length=request.headers.get("content-length"),
            correlation_id=correlation_id,
            request_id=request_id,
            user_id=user_id
        )
    
    async def _log_request_success(
        self,
        request: Request,
        response: Response,
        correlation_id: str,
        request_id: str,
        user_id: Optional[str],
        duration: float
    ) -> None:
        """Log successful request completion."""
        logger.info(
            "Request completed successfully",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
            response_size=response.headers.get("content-length"),
            correlation_id=correlation_id,
            request_id=request_id,
            user_id=user_id
        )
    
    async def _log_request_error(
        self,
        request: Request,
        exception: Exception,
        correlation_id: str,
        request_id: str,
        user_id: Optional[str],
        duration: float
    ) -> None:
        """Log request error information."""
        logger.error(
            "Request failed with exception",
            method=request.method,
            path=request.url.path,
            error_type=type(exception).__name__,
            error_message=str(exception),
            duration_ms=round(duration * 1000, 2),
            correlation_id=correlation_id,
            request_id=request_id,
            user_id=user_id,
            exc_info=True
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    def _get_endpoint_pattern(self, request: Request) -> str:
        """Get endpoint pattern for metrics (removes path parameters)."""
        # Try to get route pattern from FastAPI
        if hasattr(request, "scope") and "route" in request.scope:
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path
        
        # Fall back to actual path
        return request.url.path


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Lightweight middleware that only handles correlation ID propagation."""
    
    def __init__(
        self,
        app: ASGIApp,
        correlation_header: str = "X-Correlation-ID"
    ):
        """
        Initialize correlation middleware.
        
        Args:
            app: ASGI application
            correlation_header: Header name for correlation ID
        """
        super().__init__(app)
        self.correlation_header = correlation_header
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID tracking."""
        # Extract or generate correlation ID
        correlation_id = (
            request.headers.get(self.correlation_header) or
            str(uuid.uuid4())
        )
        
        # Set correlation ID in context
        set_correlation_id(correlation_id)
        
        # Process request
        response = await call_next(request)
        
        # Add correlation header to response
        response.headers[self.correlation_header] = correlation_id
        
        return response


class UserContextMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and set user context from JWT tokens."""
    
    def __init__(self, app: ASGIApp):
        """Initialize user context middleware."""
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with user context extraction."""
        # Extract user ID from JWT token if available
        user_id = await self._extract_user_id(request)
        
        if user_id:
            set_user_id(user_id)
        
        return await call_next(request)
    
    async def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from JWT token."""
        try:
            # Get authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            # Extract token
            token = auth_header.split(" ")[1]
            
            # Decode token (simplified - in real implementation, use proper JWT validation)
            # This would typically use the JWT utilities from shared.auth
            from shared.auth import decode_access_token
            payload = decode_access_token(token)
            
            return payload.get("sub")  # Subject claim typically contains user ID
            
        except Exception:
            # If token extraction fails, continue without user context
            return None