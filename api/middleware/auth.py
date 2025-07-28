"""
Authentication and authorization middleware for the AI Opportunity Browser.

This module provides middleware and decorators for role-based access control,
permission checking, and authentication enforcement.
"""

from functools import wraps
from typing import List, Optional, Callable, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from shared.models.user import UserRole
from shared.schemas.auth import CurrentUser
from api.routers.auth import get_current_user

logger = logging.getLogger(__name__)
security = HTTPBearer()


class PermissionDeniedError(Exception):
    """Exception raised when user lacks required permissions."""
    pass


class AuthorizationMiddleware:
    """Authorization middleware for role-based access control."""
    
    def __init__(self):
        self.role_hierarchy = {
            UserRole.ADMIN: 4,
            UserRole.MODERATOR: 3,
            UserRole.EXPERT: 2,
            UserRole.USER: 1
        }
    
    def check_role_hierarchy(self, user_role: UserRole, required_role: UserRole) -> bool:
        """Check if user role meets or exceeds required role level."""
        user_level = self.role_hierarchy.get(user_role, 0)
        required_level = self.role_hierarchy.get(required_role, 0)
        return user_level >= required_level
    
    def check_permission(self, user_permissions: List[str], required_permission: str) -> bool:
        """Check if user has specific permission."""
        return required_permission in user_permissions
    
    def check_resource_access(
        self, 
        user: CurrentUser, 
        resource_type: str, 
        resource_id: Optional[str] = None,
        action: str = "read"
    ) -> bool:
        """Check if user can access specific resource."""
        # Admin can access everything
        if user.role == UserRole.ADMIN:
            return True
        
        # Check specific resource access patterns
        if resource_type == "user" and resource_id:
            # Users can access their own profile
            if action in ["read", "write"] and resource_id == user.id:
                return True
            # Moderators and above can read all user profiles
            if action == "read" and user.role in [UserRole.MODERATOR, UserRole.EXPERT]:
                return True
            # Only admins can modify other users
            if action in ["write", "delete"]:
                return user.role == UserRole.ADMIN
        
        elif resource_type == "opportunity":
            # All authenticated users can read opportunities
            if action == "read":
                return True
            # Experts and above can create/modify opportunities
            if action in ["write", "create"]:
                return user.role in [UserRole.ADMIN, UserRole.MODERATOR, UserRole.EXPERT]
            # Only admins and moderators can delete opportunities
            if action == "delete":
                return user.role in [UserRole.ADMIN, UserRole.MODERATOR]
        
        elif resource_type == "validation":
            # All authenticated users can read validations
            if action == "read":
                return True
            # Experts and above can create validations
            if action in ["write", "create"]:
                return user.role in [UserRole.ADMIN, UserRole.MODERATOR, UserRole.EXPERT]
            # Users can modify their own validations
            if action in ["write", "delete"] and resource_id:
                # This would need to check if the validation belongs to the user
                # For now, allow experts and above
                return user.role in [UserRole.ADMIN, UserRole.MODERATOR, UserRole.EXPERT]
        
        return False


# Global authorization middleware instance
auth_middleware = AuthorizationMiddleware()


def require_auth(func: Callable = None):
    """
    Decorator to require authentication for an endpoint.
    
    Usage:
        @require_auth
        async def protected_endpoint(current_user: CurrentUser = Depends(get_current_user)):
            return {"message": "Protected content"}
    """
    def decorator(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            # The actual authentication is handled by get_current_user dependency
            # This decorator is mainly for documentation and consistency
            return await f(*args, **kwargs)
        return wrapper
    
    if func is None:
        return decorator
    return decorator(func)


def require_role(required_role: UserRole):
    """
    Decorator to require specific role or higher for an endpoint.
    
    Args:
        required_role: Minimum required role
        
    Usage:
        @require_role(UserRole.EXPERT)
        async def expert_endpoint(current_user: CurrentUser = Depends(get_current_user)):
            return {"message": "Expert content"}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, CurrentUser):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not auth_middleware.check_role_hierarchy(current_user.role, required_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires {required_role.value} role or higher"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_permission(required_permission: str):
    """
    Decorator to require specific permission for an endpoint.
    
    Args:
        required_permission: Required permission string
        
    Usage:
        @require_permission("manage:users")
        async def admin_endpoint(current_user: CurrentUser = Depends(get_current_user)):
            return {"message": "Admin content"}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, CurrentUser):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not auth_middleware.check_permission(current_user.permissions, required_permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires permission: {required_permission}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_resource_access(resource_type: str, action: str = "read"):
    """
    Decorator to require access to specific resource type.
    
    Args:
        resource_type: Type of resource (user, opportunity, validation)
        action: Action being performed (read, write, delete)
        
    Usage:
        @require_resource_access("opportunity", "write")
        async def update_opportunity(
            opportunity_id: str,
            current_user: CurrentUser = Depends(get_current_user)
        ):
            return {"message": "Opportunity updated"}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs
            current_user = None
            resource_id = None
            
            for key, value in kwargs.items():
                if isinstance(value, CurrentUser):
                    current_user = value
                elif key.endswith("_id") and isinstance(value, str):
                    resource_id = value
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not auth_middleware.check_resource_access(
                current_user, resource_type, resource_id, action
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied for {action} on {resource_type}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_self_or_admin(user_id_param: str = "user_id"):
    """
    Decorator to require user to be accessing their own resource or be an admin.
    
    Args:
        user_id_param: Name of the parameter containing the user ID
        
    Usage:
        @require_self_or_admin("user_id")
        async def get_user_profile(
            user_id: str,
            current_user: CurrentUser = Depends(get_current_user)
        ):
            return {"message": "User profile"}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user and target user_id from kwargs
            current_user = None
            target_user_id = None
            
            for key, value in kwargs.items():
                if isinstance(value, CurrentUser):
                    current_user = value
                elif key == user_id_param:
                    target_user_id = value
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Allow if user is admin or accessing their own resource
            if current_user.role == UserRole.ADMIN or current_user.id == target_user_id:
                return await func(*args, **kwargs)
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only access your own resources"
            )
        return wrapper
    return decorator


def require_verified_user(func: Callable):
    """
    Decorator to require user to have verified email.
    
    Usage:
        @require_verified_user
        async def verified_only_endpoint(current_user: CurrentUser = Depends(get_current_user)):
            return {"message": "Verified user content"}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract current_user from kwargs
        current_user = None
        for key, value in kwargs.items():
            if isinstance(value, CurrentUser):
                current_user = value
                break
        
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        if not current_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email verification required"
            )
        
        return await func(*args, **kwargs)
    return wrapper


# Dependency functions for FastAPI
async def require_admin_user(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency to require admin user."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_moderator_user(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency to require moderator user or higher."""
    if not auth_middleware.check_role_hierarchy(current_user.role, UserRole.MODERATOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator access required"
        )
    return current_user


async def require_expert_user(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency to require expert user or higher."""
    if not auth_middleware.check_role_hierarchy(current_user.role, UserRole.EXPERT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Expert access required"
        )
    return current_user


async def require_verified_email(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency to require verified email."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return current_user


# Permission checking utilities
class PermissionChecker:
    """Utility class for checking permissions."""
    
    @staticmethod
    def can_manage_users(user: CurrentUser) -> bool:
        """Check if user can manage other users."""
        return user.role == UserRole.ADMIN
    
    @staticmethod
    def can_moderate_content(user: CurrentUser) -> bool:
        """Check if user can moderate content."""
        return user.role in [UserRole.ADMIN, UserRole.MODERATOR]
    
    @staticmethod
    def can_validate_opportunities(user: CurrentUser) -> bool:
        """Check if user can validate opportunities."""
        return user.role in [UserRole.ADMIN, UserRole.MODERATOR, UserRole.EXPERT]
    
    @staticmethod
    def can_create_opportunities(user: CurrentUser) -> bool:
        """Check if user can create opportunities."""
        return user.role in [UserRole.ADMIN, UserRole.MODERATOR, UserRole.EXPERT]
    
    @staticmethod
    def can_delete_opportunities(user: CurrentUser) -> bool:
        """Check if user can delete opportunities."""
        return user.role in [UserRole.ADMIN, UserRole.MODERATOR]
    
    @staticmethod
    def can_access_analytics(user: CurrentUser) -> bool:
        """Check if user can access analytics."""
        return user.role in [UserRole.ADMIN, UserRole.MODERATOR, UserRole.EXPERT]
    
    @staticmethod
    def can_manage_system(user: CurrentUser) -> bool:
        """Check if user can manage system settings."""
        return user.role == UserRole.ADMIN


# Export commonly used functions
__all__ = [
    "AuthorizationMiddleware",
    "auth_middleware",
    "require_auth",
    "require_role", 
    "require_permission",
    "require_resource_access",
    "require_self_or_admin",
    "require_verified_user",
    "require_admin_user",
    "require_moderator_user", 
    "require_expert_user",
    "require_verified_email",
    "PermissionChecker",
    "PermissionDeniedError"
]