"""
Enhanced FastAPI dependencies with zero trust security integration.

This module provides dependency functions for user authentication,
role-based access control, service authentication, and zero trust validation.
"""

from typing import List, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.user import User, UserRole
from shared.services.user_service import user_service
from shared.auth import verify_token, TokenExpiredError, InvalidTokenError
from shared.security.zero_trust import (
    get_zero_trust_manager,
    SecurityPrincipal,
    SecurityRequest,
    SecurityContext,
    TrustLevel
)
import structlog

logger = structlog.get_logger(__name__)

# HTTP Bearer token scheme - auto_error=False allows optional authentication
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token with zero trust validation.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        Current user instance
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        # Verify the token using zero trust manager
        zt_manager = get_zero_trust_manager()
        principal = zt_manager.authenticate_user(credentials.credentials)
        
        # Get user from database
        user = await user_service.get_user_by_id(db, principal.id)
        
        if not user:
            logger.warning("Token valid but user not found", user_id=principal.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            logger.warning("Inactive user attempted access", user_id=user.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify trust level meets minimum requirements
        if not principal.is_trusted(TrustLevel.LOW):
            logger.warning(
                "User with insufficient trust level attempted access",
                user_id=user.id,
                trust_level=principal.trust_level.value
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient trust level"
            )
        
        return user
        
    except TokenExpiredError:
        logger.info("Expired token used for authentication")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    except InvalidTokenError as e:
        logger.warning("Invalid token used for authentication", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    except Exception as e:
        logger.error("Unexpected error during authentication", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )


async def get_security_principal(
    request: Request
) -> Optional[SecurityPrincipal]:
    """
    Get security principal from request state (set by zero trust middleware).
    
    Args:
        request: FastAPI request
        
    Returns:
        SecurityPrincipal if available
    """
    return getattr(request.state, "security_principal", None)


async def get_service_principal(
    request: Request,
    service_token: Optional[str] = None
) -> SecurityPrincipal:
    """
    Get service principal for service-to-service authentication.
    
    Args:
        request: FastAPI request
        service_token: Optional service token from header
        
    Returns:
        SecurityPrincipal for the service
        
    Raises:
        HTTPException: If service authentication fails
    """
    try:
        # Try to get from request state first (set by middleware)
        principal = getattr(request.state, "security_principal", None)
        if principal and principal.type == "service":
            return principal
        
        # Try service token from header
        if not service_token:
            service_token = request.headers.get("X-Service-Token")
        
        if not service_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Service token required"
            )
        
        # Authenticate service
        zt_manager = get_zero_trust_manager()
        principal = zt_manager.authenticate_service(
            service_token,
            "ai-opportunity-browser"
        )
        
        return principal
        
    except (TokenExpiredError, InvalidTokenError) as e:
        logger.warning("Service authentication failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token"
        )
    
    except Exception as e:
        logger.error("Service authentication error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service authentication error"
        )


def require_role(allowed_roles: List[UserRole]):
    """
    Create a dependency that requires specific user roles.
    
    Args:
        allowed_roles: List of roles that are allowed access
        
    Returns:
        Dependency function that checks user role
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            logger.warning(
                "User attempted access without required role",
                user_id=current_user.id,
                user_role=current_user.role,
                required_roles=[role.value for role in allowed_roles]
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[role.value for role in allowed_roles]}"
            )
        
        return current_user
    
    return role_checker


def require_admin():
    """Dependency that requires admin role."""
    return require_role([UserRole.ADMIN])


def require_moderator():
    """Dependency that requires moderator or admin role."""
    return require_role([UserRole.ADMIN, UserRole.MODERATOR])


def require_expert():
    """Dependency that requires expert, moderator, or admin role."""
    return require_role([UserRole.ADMIN, UserRole.MODERATOR, UserRole.EXPERT])


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get the current user if authenticated, otherwise return None.
    
    This is useful for endpoints that work for both authenticated and
    anonymous users but provide different functionality.
    
    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session
        
    Returns:
        Current user instance or None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        # If authentication fails, return None instead of raising
        return None


def get_pagination_params(
    page: int = 1,
    size: int = 20,
    max_size: int = 100
):
    """
    Get pagination parameters with validation.
    
    Args:
        page: Page number (1-based)
        size: Page size
        max_size: Maximum allowed page size
        
    Returns:
        Tuple of (offset, limit)
        
    Raises:
        HTTPException: If parameters are invalid
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be >= 1"
        )
    
    if size < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be >= 1"
        )
    
    if size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Page size cannot exceed {max_size}"
        )
    
    offset = (page - 1) * size
    return offset, size


class PaginationParams:
    """Pagination parameters class."""
    
    def __init__(self, page: int = 1, size: int = 20):
        self.page = page
        self.size = size
        self.offset = (page - 1) * size
        self.limit = size


def get_search_params(
    q: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "desc"
):
    """
    Get search and sorting parameters.
    
    Args:
        q: Search query
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        
    Returns:
        Dictionary of search parameters
        
    Raises:
        HTTPException: If parameters are invalid
    """
    if sort_order not in ["asc", "desc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sort order must be 'asc' or 'desc'"
        )
    
    return {
        "query": q.strip() if q else None,
        "sort_by": sort_by,
        "sort_order": sort_order
    }


async def validate_user_access(
    target_user_id: str,
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Validate that current user can access target user's data.
    
    Users can access their own data, admins and moderators can access any data.
    
    Args:
        target_user_id: ID of user whose data is being accessed
        current_user: Current authenticated user
        
    Returns:
        Current user if access is allowed
        
    Raises:
        HTTPException: If access is denied
    """
    if (target_user_id != current_user.id and 
        current_user.role not in [UserRole.ADMIN, UserRole.MODERATOR]):
        
        logger.warning(
            "User attempted unauthorized data access",
            current_user_id=current_user.id,
            target_user_id=target_user_id
        )
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return current_user


def require_trust_level(minimum_level: TrustLevel):
    """
    Create a dependency that requires minimum trust level.
    
    Args:
        minimum_level: Minimum required trust level
        
    Returns:
        Dependency function that checks trust level
    """
    async def trust_level_checker(
        request: Request,
        current_user: User = Depends(get_current_user)
    ) -> User:
        principal = await get_security_principal(request)
        
        if not principal or not principal.is_trusted(minimum_level):
            logger.warning(
                "User with insufficient trust level attempted access",
                user_id=current_user.id,
                current_trust=principal.trust_level.value if principal else "unknown",
                required_trust=minimum_level.value
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum_level.value} trust level"
            )
        
        return current_user
    
    return trust_level_checker


def require_verified_trust():
    """Dependency that requires verified trust level."""
    return require_trust_level(TrustLevel.VERIFIED)


def require_high_trust():
    """Dependency that requires high trust level."""
    return require_trust_level(TrustLevel.HIGH)


def require_medium_trust():
    """Dependency that requires medium trust level."""
    return require_trust_level(TrustLevel.MEDIUM)


async def require_service_auth(
    request: Request,
    service_token: Optional[str] = None
) -> SecurityPrincipal:
    """
    Dependency that requires service authentication.
    
    Args:
        request: FastAPI request
        service_token: Optional service token
        
    Returns:
        SecurityPrincipal for the service
    """
    return await get_service_principal(request, service_token)


def get_rate_limit_key(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user)
) -> str:
    """
    Get rate limiting key for the current request.
    
    Uses user ID if authenticated, otherwise uses IP address.
    
    Args:
        request: FastAPI request
        current_user: Current user if authenticated
        
    Returns:
        Rate limiting key
    """
    if current_user:
        return f"user:{current_user.id}"
    else:
        # Get IP from request
        client_ip = "unknown"
        if hasattr(request, "client") and request.client:
            client_ip = request.client.host
        
        # Check forwarded headers
        forwarded_headers = ["X-Forwarded-For", "X-Real-IP", "X-Client-IP"]
        for header in forwarded_headers:
            if header in request.headers:
                client_ip = request.headers[header].split(",")[0].strip()
                break
        
        return f"ip:{client_ip}"


async def validate_zero_trust_request(
    request: Request,
    resource: str,
    action: str,
    context: SecurityContext = SecurityContext.AUTHENTICATED
) -> SecurityPrincipal:
    """
    Validate a request using zero trust principles.
    
    Args:
        request: FastAPI request
        resource: Resource being accessed
        action: Action being performed
        context: Security context
        
    Returns:
        SecurityPrincipal if authorized
        
    Raises:
        HTTPException: If not authorized
    """
    try:
        # Get security principal from request state
        principal = await get_security_principal(request)
        
        if not principal:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Create security request
        security_request = SecurityRequest(
            principal=principal,
            resource=resource,
            action=action,
            context=context,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        # Evaluate with zero trust manager
        zt_manager = get_zero_trust_manager()
        decision = zt_manager.authorize_request(security_request)
        
        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=decision.reason
            )
        
        return principal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Zero trust validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authorization error"
        )