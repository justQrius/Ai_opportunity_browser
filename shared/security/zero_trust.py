"""
Zero Trust Security Architecture for AI Opportunity Browser.

This module implements zero trust security principles:
- Never trust, always verify
- Least privilege access
- Continuous verification
- Service-to-service authentication
- Enhanced token validation
"""

import time
import hmac
import hashlib
import secrets
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import jwt
import structlog

from shared.auth import verify_token, TokenExpiredError, InvalidTokenError
from shared.models.user import User, UserRole

logger = structlog.get_logger(__name__)


class TrustLevel(Enum):
    """Trust levels for zero trust evaluation."""
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


class SecurityContext(Enum):
    """Security contexts for different operations."""
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    INTERNAL = "internal"
    ADMIN = "admin"
    SYSTEM = "system"


@dataclass
class SecurityPrincipal:
    """Represents a security principal (user, service, or system)."""
    id: str
    type: str  # user, service, system
    name: str
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    trust_level: TrustLevel = TrustLevel.UNTRUSTED
    last_verified: Optional[datetime] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def has_role(self, role: str) -> bool:
        """Check if principal has a specific role."""
        return role in self.roles
    
    def has_permission(self, permission: str) -> bool:
        """Check if principal has a specific permission."""
        return permission in self.permissions
    
    def is_trusted(self, minimum_level: TrustLevel = TrustLevel.LOW) -> bool:
        """Check if principal meets minimum trust level."""
        trust_levels = {
            TrustLevel.UNTRUSTED: 0,
            TrustLevel.LOW: 1,
            TrustLevel.MEDIUM: 2,
            TrustLevel.HIGH: 3,
            TrustLevel.VERIFIED: 4
        }
        return trust_levels.get(self.trust_level, 0) >= trust_levels.get(minimum_level, 0)


@dataclass
class SecurityRequest:
    """Represents a security request for evaluation."""
    principal: SecurityPrincipal
    resource: str
    action: str
    context: SecurityContext
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    additional_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityDecision:
    """Represents a security decision."""
    allowed: bool
    reason: str
    trust_level: TrustLevel
    conditions: List[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ServiceAuthenticator:
    """Handles service-to-service authentication."""
    
    def __init__(self, service_secrets: Dict[str, str]):
        """
        Initialize service authenticator.
        
        Args:
            service_secrets: Dictionary of service_name -> secret_key
        """
        self.service_secrets = service_secrets
        self.valid_services: Set[str] = set(service_secrets.keys())
    
    def generate_service_token(
        self,
        service_name: str,
        target_service: str,
        expires_in: int = 3600
    ) -> str:
        """
        Generate a service-to-service authentication token.
        
        Args:
            service_name: Name of the calling service
            target_service: Name of the target service
            expires_in: Token expiration in seconds
            
        Returns:
            JWT token for service authentication
        """
        if service_name not in self.service_secrets:
            raise ValueError(f"Unknown service: {service_name}")
        
        now = datetime.now(timezone.utc)
        payload = {
            "iss": service_name,  # Issuer
            "aud": target_service,  # Audience
            "sub": f"service:{service_name}",  # Subject
            "iat": int(now.timestamp()),  # Issued at
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),  # Expires
            "jti": secrets.token_urlsafe(16),  # JWT ID
            "type": "service_token"
        }
        
        secret = self.service_secrets[service_name]
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        logger.info(
            "Service token generated",
            issuer=service_name,
            audience=target_service,
            expires_in=expires_in
        )
        
        return token
    
    def verify_service_token(self, token: str, expected_audience: str) -> SecurityPrincipal:
        """
        Verify a service-to-service token.
        
        Args:
            token: JWT token to verify
            expected_audience: Expected audience (target service)
            
        Returns:
            SecurityPrincipal for the service
        """
        try:
            # Decode without verification first to get the issuer
            unverified = jwt.decode(token, options={"verify_signature": False})
            issuer = unverified.get("iss")
            
            if not issuer or issuer not in self.service_secrets:
                raise InvalidTokenError(f"Unknown service issuer: {issuer}")
            
            # Verify with the service's secret
            secret = self.service_secrets[issuer]
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience=expected_audience
            )
            
            # Validate token type
            if payload.get("type") != "service_token":
                raise InvalidTokenError("Invalid token type")
            
            # Create security principal
            principal = SecurityPrincipal(
                id=payload["sub"],
                type="service",
                name=issuer,
                roles=["service"],
                permissions=["service:call"],
                trust_level=TrustLevel.HIGH,
                last_verified=datetime.now(timezone.utc),
                attributes={
                    "issuer": issuer,
                    "audience": payload["aud"],
                    "token_id": payload["jti"]
                }
            )
            
            logger.info(
                "Service token verified",
                service=issuer,
                audience=expected_audience
            )
            
            return principal
            
        except jwt.ExpiredSignatureError:
            logger.warning("Service token expired", issuer=issuer)
            raise TokenExpiredError("Service token has expired")
        
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid service token", error=str(e))
            raise InvalidTokenError(f"Invalid service token: {e}")


class ZeroTrustEvaluator:
    """Evaluates security requests using zero trust principles."""
    
    def __init__(self):
        """Initialize zero trust evaluator."""
        self.trust_policies: Dict[str, Any] = {}
        self.risk_factors: Dict[str, float] = {}
        self.blocked_ips: Set[str] = set()
        self.suspicious_patterns: List[str] = []
    
    def evaluate_request(self, request: SecurityRequest) -> SecurityDecision:
        """
        Evaluate a security request using zero trust principles.
        
        Args:
            request: Security request to evaluate
            
        Returns:
            Security decision
        """
        logger.info(
            "Evaluating security request",
            principal_id=request.principal.id,
            resource=request.resource,
            action=request.action,
            context=request.context.value
        )
        
        # Start with base trust evaluation
        trust_score = self._calculate_trust_score(request)
        
        # Check for immediate blocks
        if self._is_blocked(request):
            return SecurityDecision(
                allowed=False,
                reason="Request blocked due to security policy",
                trust_level=TrustLevel.UNTRUSTED
            )
        
        # Evaluate based on context
        if request.context == SecurityContext.PUBLIC:
            return self._evaluate_public_request(request, trust_score)
        elif request.context == SecurityContext.AUTHENTICATED:
            return self._evaluate_authenticated_request(request, trust_score)
        elif request.context == SecurityContext.INTERNAL:
            return self._evaluate_internal_request(request, trust_score)
        elif request.context == SecurityContext.ADMIN:
            return self._evaluate_admin_request(request, trust_score)
        elif request.context == SecurityContext.SYSTEM:
            return self._evaluate_system_request(request, trust_score)
        
        # Default deny
        return SecurityDecision(
            allowed=False,
            reason="No matching security policy",
            trust_level=TrustLevel.UNTRUSTED
        )
    
    def _calculate_trust_score(self, request: SecurityRequest) -> float:
        """Calculate trust score for a request."""
        score = 0.0
        
        # Principal trust level
        trust_weights = {
            TrustLevel.UNTRUSTED: 0.0,
            TrustLevel.LOW: 0.2,
            TrustLevel.MEDIUM: 0.5,
            TrustLevel.HIGH: 0.8,
            TrustLevel.VERIFIED: 1.0
        }
        score += trust_weights.get(request.principal.trust_level, 0.0) * 0.4
        
        # Time since last verification
        if request.principal.last_verified:
            time_diff = datetime.now(timezone.utc) - request.principal.last_verified
            if time_diff.total_seconds() < 300:  # 5 minutes
                score += 0.3
            elif time_diff.total_seconds() < 3600:  # 1 hour
                score += 0.2
            elif time_diff.total_seconds() < 86400:  # 24 hours
                score += 0.1
        
        # Principal type bonus
        if request.principal.type == "service":
            score += 0.2
        elif request.principal.type == "system":
            score += 0.3
        
        # IP reputation (simplified)
        if request.ip_address and request.ip_address not in self.blocked_ips:
            score += 0.1
        
        return min(1.0, score)
    
    def _is_blocked(self, request: SecurityRequest) -> bool:
        """Check if request should be immediately blocked."""
        # Check blocked IPs
        if request.ip_address in self.blocked_ips:
            return True
        
        # Check suspicious patterns in user agent
        if request.user_agent:
            for pattern in self.suspicious_patterns:
                if pattern.lower() in request.user_agent.lower():
                    return True
        
        return False
    
    def _evaluate_public_request(self, request: SecurityRequest, trust_score: float) -> SecurityDecision:
        """Evaluate public access requests."""
        # Public endpoints have minimal restrictions
        if request.action in ["read", "list"] and "public" in request.resource:
            return SecurityDecision(
                allowed=True,
                reason="Public resource access allowed",
                trust_level=request.principal.trust_level,
                conditions=["rate_limited"]
            )
        
        return SecurityDecision(
            allowed=False,
            reason="Public access not allowed for this resource",
            trust_level=request.principal.trust_level
        )
    
    def _evaluate_authenticated_request(self, request: SecurityRequest, trust_score: float) -> SecurityDecision:
        """Evaluate authenticated user requests."""
        # Require minimum trust level
        if not request.principal.is_trusted(TrustLevel.LOW):
            return SecurityDecision(
                allowed=False,
                reason="Insufficient trust level for authenticated access",
                trust_level=request.principal.trust_level
            )
        
        # Check role-based permissions
        if request.action == "read":
            return SecurityDecision(
                allowed=True,
                reason="Authenticated read access allowed",
                trust_level=request.principal.trust_level,
                conditions=["rate_limited", "audit_logged"]
            )
        elif request.action in ["create", "update"] and request.principal.has_role("user"):
            return SecurityDecision(
                allowed=True,
                reason="Authenticated write access allowed",
                trust_level=request.principal.trust_level,
                conditions=["rate_limited", "audit_logged", "content_validated"]
            )
        
        return SecurityDecision(
            allowed=False,
            reason="Insufficient permissions for requested action",
            trust_level=request.principal.trust_level
        )
    
    def _evaluate_internal_request(self, request: SecurityRequest, trust_score: float) -> SecurityDecision:
        """Evaluate internal service requests."""
        # Require service or system principal
        if request.principal.type not in ["service", "system"]:
            return SecurityDecision(
                allowed=False,
                reason="Internal access requires service or system principal",
                trust_level=request.principal.trust_level
            )
        
        # Require high trust level
        if not request.principal.is_trusted(TrustLevel.HIGH):
            return SecurityDecision(
                allowed=False,
                reason="Insufficient trust level for internal access",
                trust_level=request.principal.trust_level
            )
        
        return SecurityDecision(
            allowed=True,
            reason="Internal service access allowed",
            trust_level=request.principal.trust_level,
            conditions=["audit_logged"]
        )
    
    def _evaluate_admin_request(self, request: SecurityRequest, trust_score: float) -> SecurityDecision:
        """Evaluate admin requests."""
        # Require admin role
        if not request.principal.has_role("admin"):
            return SecurityDecision(
                allowed=False,
                reason="Admin role required",
                trust_level=request.principal.trust_level
            )
        
        # Require verified trust level
        if not request.principal.is_trusted(TrustLevel.VERIFIED):
            return SecurityDecision(
                allowed=False,
                reason="Verified trust level required for admin access",
                trust_level=request.principal.trust_level
            )
        
        return SecurityDecision(
            allowed=True,
            reason="Admin access allowed",
            trust_level=request.principal.trust_level,
            conditions=["audit_logged", "mfa_verified", "time_limited"],
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
    
    def _evaluate_system_request(self, request: SecurityRequest, trust_score: float) -> SecurityDecision:
        """Evaluate system-level requests."""
        # Only allow system principals
        if request.principal.type != "system":
            return SecurityDecision(
                allowed=False,
                reason="System access requires system principal",
                trust_level=request.principal.trust_level
            )
        
        return SecurityDecision(
            allowed=True,
            reason="System access allowed",
            trust_level=request.principal.trust_level,
            conditions=["audit_logged"]
        )


class SecurityEventLogger:
    """Logs security events for monitoring and alerting."""
    
    def __init__(self):
        """Initialize security event logger."""
        self.logger = structlog.get_logger("security")
    
    def log_authentication_event(
        self,
        event_type: str,
        principal_id: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log authentication events."""
        self.logger.info(
            "Authentication event",
            event_type=event_type,
            principal_id=principal_id,
            success=success,
            details=details or {}
        )
    
    def log_authorization_event(
        self,
        principal_id: str,
        resource: str,
        action: str,
        allowed: bool,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log authorization events."""
        self.logger.info(
            "Authorization event",
            principal_id=principal_id,
            resource=resource,
            action=action,
            allowed=allowed,
            reason=reason,
            details=details or {}
        )
    
    def log_security_violation(
        self,
        violation_type: str,
        principal_id: Optional[str],
        details: Dict[str, Any]
    ):
        """Log security violations."""
        self.logger.warning(
            "Security violation",
            violation_type=violation_type,
            principal_id=principal_id,
            details=details
        )
    
    def log_suspicious_activity(
        self,
        activity_type: str,
        principal_id: Optional[str],
        risk_score: float,
        details: Dict[str, Any]
    ):
        """Log suspicious activities."""
        self.logger.warning(
            "Suspicious activity detected",
            activity_type=activity_type,
            principal_id=principal_id,
            risk_score=risk_score,
            details=details
        )


class ZeroTrustManager:
    """Main manager for zero trust security architecture."""
    
    def __init__(self, service_secrets: Dict[str, str]):
        """
        Initialize zero trust manager.
        
        Args:
            service_secrets: Service authentication secrets
        """
        self.service_auth = ServiceAuthenticator(service_secrets)
        self.evaluator = ZeroTrustEvaluator()
        self.event_logger = SecurityEventLogger()
    
    def authenticate_user(self, token: str) -> SecurityPrincipal:
        """
        Authenticate a user token and create security principal.
        
        Args:
            token: JWT token
            
        Returns:
            SecurityPrincipal for the user
        """
        try:
            # Verify the token
            payload = verify_token(token, expected_type="access")
            
            # Create security principal
            principal = SecurityPrincipal(
                id=payload.sub,
                type="user",
                name=payload.username,
                roles=[payload.role],
                permissions=self._get_user_permissions(payload.role),
                trust_level=self._determine_user_trust_level(payload),
                last_verified=datetime.now(timezone.utc),
                attributes={
                    "email": payload.email,
                    "token_id": payload.jti
                }
            )
            
            self.event_logger.log_authentication_event(
                "user_token_verified",
                principal.id,
                True,
                {"username": payload.username, "role": payload.role}
            )
            
            return principal
            
        except (TokenExpiredError, InvalidTokenError) as e:
            self.event_logger.log_authentication_event(
                "user_token_failed",
                "unknown",
                False,
                {"error": str(e)}
            )
            raise
    
    def authenticate_service(self, token: str, expected_audience: str) -> SecurityPrincipal:
        """
        Authenticate a service token.
        
        Args:
            token: Service JWT token
            expected_audience: Expected audience
            
        Returns:
            SecurityPrincipal for the service
        """
        try:
            principal = self.service_auth.verify_service_token(token, expected_audience)
            
            self.event_logger.log_authentication_event(
                "service_token_verified",
                principal.id,
                True,
                {"service": principal.name, "audience": expected_audience}
            )
            
            return principal
            
        except (TokenExpiredError, InvalidTokenError) as e:
            self.event_logger.log_authentication_event(
                "service_token_failed",
                "unknown",
                False,
                {"error": str(e), "audience": expected_audience}
            )
            raise
    
    def authorize_request(self, request: SecurityRequest) -> SecurityDecision:
        """
        Authorize a security request.
        
        Args:
            request: Security request
            
        Returns:
            Security decision
        """
        decision = self.evaluator.evaluate_request(request)
        
        self.event_logger.log_authorization_event(
            request.principal.id,
            request.resource,
            request.action,
            decision.allowed,
            decision.reason,
            {
                "trust_level": decision.trust_level.value,
                "conditions": decision.conditions,
                "context": request.context.value
            }
        )
        
        return decision
    
    def _get_user_permissions(self, role: str) -> List[str]:
        """Get permissions for a user role."""
        role_permissions = {
            "user": ["read:opportunities", "create:validations", "read:profile"],
            "expert": ["read:opportunities", "create:validations", "create:opportunities", "read:analytics"],
            "moderator": ["read:opportunities", "create:validations", "create:opportunities", "moderate:content", "read:analytics"],
            "admin": ["*"]  # All permissions
        }
        return role_permissions.get(role, [])
    
    def _determine_user_trust_level(self, payload) -> TrustLevel:
        """Determine trust level for a user."""
        # This would typically involve more complex logic
        # For now, use simple role-based trust levels
        role_trust = {
            "user": TrustLevel.LOW,
            "expert": TrustLevel.MEDIUM,
            "moderator": TrustLevel.HIGH,
            "admin": TrustLevel.VERIFIED
        }
        return role_trust.get(payload.role, TrustLevel.UNTRUSTED)


# Global zero trust manager instance
_zero_trust_manager: Optional[ZeroTrustManager] = None


def setup_zero_trust(service_secrets: Dict[str, str]) -> ZeroTrustManager:
    """Setup global zero trust manager."""
    global _zero_trust_manager
    _zero_trust_manager = ZeroTrustManager(service_secrets)
    logger.info("Zero trust security architecture initialized")
    return _zero_trust_manager


def get_zero_trust_manager() -> ZeroTrustManager:
    """Get the global zero trust manager."""
    if _zero_trust_manager is None:
        raise RuntimeError("Zero trust manager not initialized. Call setup_zero_trust() first.")
    return _zero_trust_manager