"""
Authentication and authorization schemas for the AI Opportunity Browser.

This module contains schemas for user authentication, JWT tokens,
and authorization-related operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import EmailStr, Field, validator
from .base import BaseSchema
from shared.models.user import UserRole


class LoginRequest(BaseSchema):
    """User login request schema."""
    
    email: EmailStr
    password: str = Field(..., min_length=1)
    remember_me: bool = False


class LoginResponse(BaseSchema):
    """User login response schema."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: Dict[str, Any]  # User profile data


class RefreshTokenRequest(BaseSchema):
    """Token refresh request schema."""
    
    refresh_token: str


class RefreshTokenResponse(BaseSchema):
    """Token refresh response schema."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RegisterRequest(BaseSchema):
    """User registration request schema."""
    
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    expertise_domains: Optional[List[str]] = None
    linkedin_url: Optional[str] = Field(None, pattern="^https://.*linkedin.com/.*")
    github_url: Optional[str] = Field(None, pattern="^https://github.com/.*")
    terms_accepted: bool = Field(..., description="Must accept terms and conditions")
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError('Password must contain uppercase, lowercase, and numeric characters')
        
        return v
    
    @validator('terms_accepted')
    def validate_terms_accepted(cls, v):
        """Ensure terms are accepted."""
        if not v:
            raise ValueError('Terms and conditions must be accepted')
        return v


class RegisterResponse(BaseSchema):
    """User registration response schema."""
    
    user_id: str
    email: str
    username: str
    message: str = "Registration successful. Please verify your email."
    verification_required: bool = True


class PasswordResetRequest(BaseSchema):
    """Password reset request schema."""
    
    email: EmailStr


class PasswordResetResponse(BaseSchema):
    """Password reset response schema."""
    
    message: str = "If the email exists, a reset link has been sent."


class PasswordResetConfirm(BaseSchema):
    """Password reset confirmation schema."""
    
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate new password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError('Password must contain uppercase, lowercase, and numeric characters')
        
        return v


class ChangePasswordRequest(BaseSchema):
    """Change password request schema."""
    
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate new password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError('Password must contain uppercase, lowercase, and numeric characters')
        
        return v


class EmailVerificationRequest(BaseSchema):
    """Email verification request schema."""
    
    token: str


class EmailVerificationResponse(BaseSchema):
    """Email verification response schema."""
    
    message: str = "Email verified successfully."
    verified: bool = True


class TokenPayload(BaseSchema):
    """JWT token payload schema."""
    
    sub: str  # subject (user_id)
    email: str
    username: str
    role: UserRole
    exp: datetime  # expiration time
    iat: datetime  # issued at
    jti: str  # JWT ID
    token_type: str = "access"  # access or refresh


class CurrentUser(BaseSchema):
    """Current authenticated user schema."""
    
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    role: UserRole
    is_active: bool
    is_verified: bool
    reputation_score: float
    expertise_domains: Optional[List[str]] = None
    permissions: List[str] = []


class PermissionCheck(BaseSchema):
    """Permission check request schema."""
    
    resource: str
    action: str
    resource_id: Optional[str] = None


class PermissionResponse(BaseSchema):
    """Permission check response schema."""
    
    allowed: bool
    reason: Optional[str] = None


class SessionInfo(BaseSchema):
    """User session information schema."""
    
    session_id: str
    user_id: str
    ip_address: str
    user_agent: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    is_active: bool


class LogoutRequest(BaseSchema):
    """Logout request schema."""
    
    all_sessions: bool = False  # Logout from all sessions


class LogoutResponse(BaseSchema):
    """Logout response schema."""
    
    message: str = "Logged out successfully."
    sessions_terminated: int = 1


class TwoFactorSetupRequest(BaseSchema):
    """Two-factor authentication setup request."""
    
    method: str = Field(..., pattern="^(totp|sms|email)$")
    phone_number: Optional[str] = Field(None, pattern="^\\+[1-9]\\d{1,14}$")


class TwoFactorSetupResponse(BaseSchema):
    """Two-factor authentication setup response."""
    
    method: str
    secret: Optional[str] = None  # For TOTP
    qr_code: Optional[str] = None  # For TOTP
    backup_codes: Optional[List[str]] = None


class TwoFactorVerifyRequest(BaseSchema):
    """Two-factor authentication verification request."""
    
    code: str = Field(..., min_length=6, max_length=8)
    method: str = Field(..., pattern="^(totp|sms|email|backup)$")


class TwoFactorVerifyResponse(BaseSchema):
    """Two-factor authentication verification response."""
    
    verified: bool
    message: str