"""
Rate limiting middleware for the AI Opportunity Browser API.

This module implements rate limiting to protect the API from abuse
and ensure fair usage across all clients.
"""

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict
import time
import asyncio
from collections import defaultdict, deque
from api.core.config import get_settings

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to implement rate limiting based on client IP."""
    
    def __init__(self, app, requests_per_minute: int = None, window_seconds: int = None):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute or settings.RATE_LIMIT_REQUESTS
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW
        self.clients: Dict[str, deque] = defaultdict(deque)
        self._cleanup_task = None
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit and process request."""
        
        # Get client identifier (IP address)
        client_ip = self._get_client_ip(request)
        
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)
        
        # Check rate limit
        current_time = time.time()
        client_requests = self.clients[client_ip]
        
        # Remove old requests outside the window
        while client_requests and client_requests[0] <= current_time - self.window_seconds:
            client_requests.popleft()
        
        # Check if rate limit exceeded
        if len(client_requests) >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {self.requests_per_minute} requests per {self.window_seconds} seconds",
                    "retry_after": self.window_seconds
                },
                headers={"Retry-After": str(self.window_seconds)}
            )
        
        # Add current request to the queue
        client_requests.append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, self.requests_per_minute - len(client_requests))
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_seconds))
        
        # Start cleanup task if not already running
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_old_entries())
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers (when behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    async def _cleanup_old_entries(self):
        """Periodically cleanup old rate limit entries."""
        while True:
            try:
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                current_time = time.time()
                cutoff_time = current_time - self.window_seconds
                
                # Remove old entries
                clients_to_remove = []
                for client_ip, requests in self.clients.items():
                    while requests and requests[0] <= cutoff_time:
                        requests.popleft()
                    
                    # Remove empty client entries
                    if not requests:
                        clients_to_remove.append(client_ip)
                
                for client_ip in clients_to_remove:
                    del self.clients[client_ip]
                    
            except Exception:
                # Continue cleanup on error
                pass