"""
Metrics collection middleware for HTTP requests.

This middleware automatically collects metrics for all HTTP requests
including response times, status codes, and request counts.
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from shared.monitoring import get_metrics_collector

logger = structlog.get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request metrics."""
    
    def __init__(self, app, collect_detailed_metrics: bool = True):
        super().__init__(app)
        self.collect_detailed_metrics = collect_detailed_metrics
        self.metrics_collector = get_metrics_collector()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        
        # Skip metrics collection for metrics endpoint to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)
        
        start_time = time.time()
        
        # Extract request information
        method = request.method
        path = request.url.path
        
        # Normalize path for metrics (remove IDs and dynamic parts)
        normalized_path = self._normalize_path(path)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            self.metrics_collector.record_http_request(
                method=method,
                endpoint=normalized_path,
                status_code=response.status_code,
                duration=duration
            )
            
            # Add timing header
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            
            return response
            
        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            self.metrics_collector.record_http_request(
                method=method,
                endpoint=normalized_path,
                status_code=500,
                duration=duration
            )
            
            logger.error(
                "Request processing failed",
                method=method,
                path=path,
                duration=duration,
                error=str(e)
            )
            
            raise
    
    def _normalize_path(self, path: str) -> str:
        """Normalize URL path for metrics to avoid high cardinality."""
        
        # Common patterns to normalize
        normalizations = [
            # Replace UUIDs with placeholder
            (r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}'),
            # Replace numeric IDs
            (r'/\d+', '/{id}'),
            # Replace user IDs in paths
            (r'/users/[^/]+', '/users/{user_id}'),
            (r'/opportunities/[^/]+', '/opportunities/{opportunity_id}'),
            (r'/validations/[^/]+', '/validations/{validation_id}'),
            (r'/discussions/[^/]+', '/discussions/{discussion_id}'),
        ]
        
        import re
        normalized = path
        for pattern, replacement in normalizations:
            normalized = re.sub(pattern, replacement, normalized)
        
        return normalized