"""
Enhanced security middleware for the AI Opportunity Browser API.

This module implements comprehensive security middleware including:
- Security headers
- Zero trust request validation
- Threat detection
- Security event logging
"""

import time
import json
from typing import Callable, Optional, Dict, Any, Set
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import structlog

from shared.security.zero_trust import (
    get_zero_trust_manager,
    SecurityRequest,
    SecurityContext,
    SecurityPrincipal,
    TrustLevel
)

logger = structlog.get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware to add comprehensive security headers."""
    
    def __init__(self, app, enable_hsts: bool = True, enable_csp: bool = True):
        """
        Initialize security headers middleware.
        
        Args:
            app: FastAPI application
            enable_hsts: Enable HSTS headers
            enable_csp: Enable Content Security Policy
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.enable_csp = enable_csp
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add comprehensive security headers to response."""
        
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Record request start time
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Add security headers
        self._add_security_headers(request, response)
        
        # Add request tracking headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{response_time:.3f}s"
        
        # Log security event
        logger.info(
            "Request processed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            response_time=response_time,
            user_agent=request.headers.get("user-agent"),
            ip_address=self._get_client_ip(request)
        )
        
        return response
    
    def _add_security_headers(self, request: Request, response: Response):
        """Add comprehensive security headers."""
        # Basic security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["X-Download-Options"] = "noopen"
        
        # Remove server information
        response.headers["Server"] = "AI-Opportunity-Browser"
        
        # Add HSTS header for HTTPS
        if self.enable_hsts and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Add comprehensive CSP header
        if self.enable_csp:
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https:; "
                "media-src 'self'; "
                "object-src 'none'; "
                "child-src 'none'; "
                "frame-ancestors 'none'; "
                "form-action 'self'; "
                "base-uri 'self'; "
                "manifest-src 'self';"
            )
            response.headers["Content-Security-Policy"] = csp_policy
        
        # Add feature policy headers
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=(), "
            "accelerometer=(), ambient-light-sensor=()"
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers (in order of preference)
        forwarded_headers = [
            "X-Forwarded-For",
            "X-Real-IP", 
            "X-Client-IP",
            "CF-Connecting-IP"  # Cloudflare
        ]
        
        for header in forwarded_headers:
            if header in request.headers:
                # Take the first IP if multiple are present
                ip = request.headers[header].split(",")[0].strip()
                if ip:
                    return ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"


class ThreatDetectionMiddleware(BaseHTTPMiddleware):
    """Middleware for detecting and blocking threats."""
    
    def __init__(
        self,
        app,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        blocked_user_agents: Optional[Set[str]] = None,
        blocked_ips: Optional[Set[str]] = None,
        rate_limit_requests: int = 100,
        rate_limit_window: int = 60
    ):
        """
        Initialize threat detection middleware.
        
        Args:
            app: FastAPI application
            max_request_size: Maximum request size in bytes
            blocked_user_agents: Set of blocked user agent patterns
            blocked_ips: Set of blocked IP addresses
            rate_limit_requests: Number of requests per window
            rate_limit_window: Rate limit window in seconds
        """
        super().__init__(app)
        self.max_request_size = max_request_size
        self.blocked_user_agents = blocked_user_agents or set()
        self.blocked_ips = blocked_ips or set()
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        
        # Simple in-memory rate limiting (use Redis in production)
        self.request_counts: Dict[str, Dict[str, Any]] = {}
        
        # Suspicious patterns
        self.suspicious_patterns = [
            "sqlmap", "nmap", "nikto", "dirb", "gobuster",
            "burp", "owasp", "zap", "w3af", "skipfish"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Detect and block threats."""
        
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "").lower()
        
        # Check blocked IPs
        if client_ip in self.blocked_ips:
            logger.warning(
                "Blocked IP attempted access",
                ip_address=client_ip,
                path=request.url.path
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check blocked user agents
        for blocked_agent in self.blocked_user_agents:
            if blocked_agent.lower() in user_agent:
                logger.warning(
                    "Blocked user agent attempted access",
                    user_agent=user_agent,
                    ip_address=client_ip,
                    path=request.url.path
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if pattern in user_agent:
                logger.warning(
                    "Suspicious user agent detected",
                    pattern=pattern,
                    user_agent=user_agent,
                    ip_address=client_ip,
                    path=request.url.path
                )
                # Don't block immediately, but log for monitoring
        
        # Rate limiting check
        if not self._check_rate_limit(client_ip):
            logger.warning(
                "Rate limit exceeded",
                ip_address=client_ip,
                path=request.url.path
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(self.rate_limit_window)}
            )
        
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            logger.warning(
                "Request size exceeded",
                content_length=content_length,
                max_size=self.max_request_size,
                ip_address=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )
        
        # Process request
        response = await call_next(request)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers
        forwarded_headers = ["X-Forwarded-For", "X-Real-IP", "X-Client-IP"]
        
        for header in forwarded_headers:
            if header in request.headers:
                ip = request.headers[header].split(",")[0].strip()
                if ip:
                    return ip
        
        return request.client.host if request.client else "unknown"
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if client IP is within rate limits."""
        now = time.time()
        
        # Clean old entries
        if client_ip in self.request_counts:
            self.request_counts[client_ip]["requests"] = [
                req_time for req_time in self.request_counts[client_ip]["requests"]
                if now - req_time < self.rate_limit_window
            ]
        else:
            self.request_counts[client_ip] = {"requests": []}
        
        # Check current count
        current_requests = len(self.request_counts[client_ip]["requests"])
        
        if current_requests >= self.rate_limit_requests:
            return False
        
        # Add current request
        self.request_counts[client_ip]["requests"].append(now)
        return True


class ZeroTrustMiddleware(BaseHTTPMiddleware):
    """Middleware for zero trust security validation."""
    
    def __init__(
        self,
        app,
        exempt_paths: Optional[Set[str]] = None,
        public_paths: Optional[Set[str]] = None
    ):
        """
        Initialize zero trust middleware.
        
        Args:
            app: FastAPI application
            exempt_paths: Paths exempt from zero trust validation
            public_paths: Paths that allow public access
        """
        super().__init__(app)
        self.exempt_paths = exempt_paths or {"/health", "/metrics", "/docs", "/openapi.json"}
        self.public_paths = public_paths or {"/", "/health", "/docs"}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply zero trust validation to requests."""
        
        # Skip validation for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        try:
            # Get zero trust manager
            zt_manager = get_zero_trust_manager()
            
            # Determine security context
            context = self._determine_security_context(request)
            
            # Create security principal (if authenticated)
            principal = await self._get_security_principal(request, zt_manager)
            
            # Create security request
            security_request = SecurityRequest(
                principal=principal,
                resource=request.url.path,
                action=request.method.lower(),
                context=context,
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("user-agent"),
                additional_context={
                    "request_id": getattr(request.state, "request_id", None),
                    "content_type": request.headers.get("content-type"),
                    "content_length": request.headers.get("content-length")
                }
            )
            
            # Evaluate security request
            decision = zt_manager.authorize_request(security_request)
            
            if not decision.allowed:
                logger.warning(
                    "Zero trust access denied",
                    principal_id=principal.id,
                    resource=request.url.path,
                    action=request.method,
                    reason=decision.reason
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=decision.reason
                )
            
            # Store security context in request state
            request.state.security_principal = principal
            request.state.security_decision = decision
            
            # Process request
            response = await call_next(request)
            
            # Add security context to response headers (for debugging)
            if hasattr(request.state, "request_id"):
                response.headers["X-Trust-Level"] = decision.trust_level.value
                response.headers["X-Security-Context"] = context.value
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Zero trust middleware error",
                error=str(e),
                path=request.url.path,
                exc_info=True
            )
            # Allow request to proceed on middleware errors (fail open)
            return await call_next(request)
    
    def _determine_security_context(self, request: Request) -> SecurityContext:
        """Determine security context for the request."""
        path = request.url.path
        
        # Public paths
        if path in self.public_paths:
            return SecurityContext.PUBLIC
        
        # Admin paths
        if path.startswith("/admin"):
            return SecurityContext.ADMIN
        
        # Internal API paths
        if path.startswith("/internal"):
            return SecurityContext.INTERNAL
        
        # System paths
        if path.startswith("/system"):
            return SecurityContext.SYSTEM
        
        # Default to authenticated
        return SecurityContext.AUTHENTICATED
    
    async def _get_security_principal(
        self,
        request: Request,
        zt_manager
    ) -> SecurityPrincipal:
        """Get security principal from request."""
        
        # Check for service token first
        service_token = request.headers.get("X-Service-Token")
        if service_token:
            try:
                return zt_manager.authenticate_service(
                    service_token,
                    "ai-opportunity-browser"
                )
            except Exception as e:
                logger.warning("Service authentication failed", error=str(e))
        
        # Check for user token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            try:
                return zt_manager.authenticate_user(token)
            except Exception as e:
                logger.warning("User authentication failed", error=str(e))
        
        # Create anonymous principal
        return SecurityPrincipal(
            id="anonymous",
            type="anonymous",
            name="anonymous",
            roles=[],
            permissions=[],
            trust_level=TrustLevel.UNTRUSTED
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        forwarded_headers = ["X-Forwarded-For", "X-Real-IP", "X-Client-IP"]
        
        for header in forwarded_headers:
            if header in request.headers:
                ip = request.headers[header].split(",")[0].strip()
                if ip:
                    return ip
        
        return request.client.host if request.client else "unknown"