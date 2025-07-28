"""
Authentication endpoints for the AI Opportunity Browser.

This module provides endpoints for user registration, login, token refresh,
and password management operations.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging

from shared.database import get_db
from shared.schemas.auth import (
    LoginRequest, LoginResponse, RegisterRequest, RegisterResponse,
    RefreshTokenRequest, RefreshTokenResponse, PasswordResetRequest,
    PasswordResetResponse, PasswordResetConfirm, ChangePasswordRequest,
    CurrentUser, LogoutRequest, LogoutResponse, TwoFactorSetupRequest,
    TwoFactorSetupResponse, TwoFactorVerifyRequest, TwoFactorVerifyResponse
)
from shared.models.user import User, UserRole
from shared.auth import (
    create_access_token, create_refresh_token, verify_token, hash_password,
    verify_password, create_password_reset_token, verify_password_reset_token,
    get_user_from_token, AuthenticationError, TokenExpiredError, InvalidTokenError
)
from api.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> CurrentUser:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        Current user information
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        # Extract token from credentials
        token = credentials.credentials
        
        # Get user info from token
        user_info = get_user_from_token(token)
        
        # Fetch user from database to ensure they still exist and are active
        user = db.query(User).filter(User.id == user_info["id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive"
            )
        
        # Convert to CurrentUser schema
        return CurrentUser(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            reputation_score=user.reputation_score,
            expertise_domains=user.expertise_domains.split(",") if user.expertise_domains else [],
            permissions=_get_user_permissions(user.role)
        )
        
    except (TokenExpiredError, InvalidTokenError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def _get_user_permissions(role: UserRole) -> list[str]:
    """Get permissions based on user role."""
    permissions = {
        UserRole.ADMIN: [
            "read:all", "write:all", "delete:all", "manage:users", 
            "manage:opportunities", "manage:validations", "manage:system"
        ],
        UserRole.MODERATOR: [
            "read:all", "write:opportunities", "write:validations", 
            "moderate:content", "manage:validations"
        ],
        UserRole.EXPERT: [
            "read:all", "write:validations", "write:opportunities", 
            "validate:opportunities"
        ],
        UserRole.USER: [
            "read:opportunities", "write:validations", "read:profile", 
            "write:profile"
        ]
    }
    return permissions.get(role, [])


@router.post("/register", response_model=RegisterResponse)
async def register_user(
    user_data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    Supports Requirements 4.1 (Community Engagement Platform)
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == user_data.email) | (User.username == user_data.username)
        ).first()
        
        if existing_user:
            if existing_user.email == user_data.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Hash password
        hashed_password = hash_password(user_data.password)
        
        # Create new user
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=UserRole.USER,  # Default role
            expertise_domains=",".join(user_data.expertise_domains) if user_data.expertise_domains else None,
            linkedin_url=user_data.linkedin_url,
            github_url=user_data.github_url,
            is_active=True,
            is_verified=False  # Requires email verification
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # TODO: Send verification email in background
        # background_tasks.add_task(send_verification_email, new_user.email, new_user.id)
        
        logger.info(f"New user registered: {new_user.username} ({new_user.email})")
        
        return RegisterResponse(
            user_id=new_user.id,
            email=new_user.email,
            username=new_user.username,
            message="Registration successful. Please check your email for verification.",
            verification_required=True
        )
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed due to data conflict"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=LoginResponse)
async def login_user(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return access tokens.
    
    Supports Requirements 4.1 (Community Engagement Platform)
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == login_data.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive"
            )
        
        # Check if 2FA is required
        requires_2fa = hasattr(user, 'two_factor_enabled') and user.two_factor_enabled
        
        # Create tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        if login_data.remember_me:
            access_token_expires = timedelta(days=7)  # Extended for remember me
        
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            username=user.username,
            role=user.role,
            expires_delta=access_token_expires
        )
        
        refresh_token = create_refresh_token(
            user_id=user.id,
            email=user.email,
            username=user.username,
            role=user.role
        )
        
        # Extract token JTIs for session management
        from shared.auth import get_user_from_token
        try:
            access_token_info = get_user_from_token(access_token)
            refresh_token_payload = verify_token(refresh_token, expected_type="refresh")
            
            access_token_jti = access_token_info["token_id"]
            refresh_token_jti = refresh_token_payload.jti
        except Exception as e:
            logger.error(f"Error extracting token JTIs: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token creation failed"
            )
        
        # Create session
        from shared.services.session_management import session_manager
        try:
            # Get client information
            ip_address = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")
            
            session_info = session_manager.create_session(
                user=user,
                access_token_jti=access_token_jti,
                refresh_token_jti=refresh_token_jti,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            # Continue with login even if session creation fails
        
        # Prepare user data for response
        user_data = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.value,
            "is_verified": user.is_verified,
            "reputation_score": user.reputation_score,
            "expertise_domains": user.expertise_domains.split(",") if user.expertise_domains else [],
            "two_factor_enabled": requires_2fa
        }
        
        logger.info(f"User logged in: {user.username} ({user.email}) - Session: {session_info.session_id if 'session_info' in locals() else 'unknown'}")
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
            user=user_data
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_access_token(
    refresh_data: RefreshTokenRequest
):
    """
    Refresh access token using refresh token.
    """
    try:
        from shared.auth import refresh_access_token
        
        new_access_token, new_refresh_token = refresh_access_token(refresh_data.refresh_token)
        
        return RefreshTokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except (TokenExpiredError, InvalidTokenError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.get("/me", response_model=CurrentUser)
async def get_current_user_info(
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    """
    return current_user


@router.post("/logout", response_model=LogoutResponse)
async def logout_user(
    logout_data: LogoutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    request: Request = None
):
    """
    Logout user and invalidate tokens using Redis blacklisting.
    """
    try:
        from shared.auth import blacklist_token, blacklist_user_tokens, get_user_from_token
        
        sessions_terminated = 0
        
        # Use session management for proper logout
        from shared.services.session_management import session_manager
        
        sessions_terminated = 0
        
        # Get the current token from the request headers
        authorization = request.headers.get("Authorization") if request else None
        if authorization and authorization.startswith("Bearer "):
            current_token = authorization[7:]  # Remove "Bearer " prefix
            
            try:
                # Get token info
                token_info = get_user_from_token(current_token)
                current_jti = token_info["token_id"]
                
                # Find and revoke the current session
                user_sessions = session_manager.get_user_sessions(current_user.id)
                current_session_id = None
                
                for session_id in user_sessions:
                    session_info = session_manager.get_session(session_id)
                    if session_info and session_info.access_token_jti == current_jti:
                        current_session_id = session_id
                        break
                
                if current_session_id:
                    if logout_data.all_sessions:
                        # Revoke all sessions
                        sessions_terminated = session_manager.revoke_all_user_sessions(current_user.id)
                        logger.info(f"Revoked all {sessions_terminated} sessions for user {current_user.username}")
                    else:
                        # Revoke only current session
                        if session_manager.revoke_session(current_session_id, "user_logout"):
                            sessions_terminated = 1
                            logger.info(f"Revoked current session for user {current_user.username}")
                else:
                    # Fallback to token blacklisting if session not found
                    blacklist_token(token_info["token_id"], token_info["expires_at"])
                    sessions_terminated = 1
                    
                    if logout_data.all_sessions:
                        additional_sessions = blacklist_user_tokens(current_user.id)
                        sessions_terminated += additional_sessions
                
            except Exception as logout_error:
                logger.error(f"Error during logout: {logout_error}")
                # Continue with logout even if session management fails
                sessions_terminated = 1
        
        logger.info(f"User logged out: {current_user.username} ({sessions_terminated} sessions terminated)")
        
        return LogoutResponse(
            message="Logged out successfully",
            sessions_terminated=sessions_terminated
        )
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/password-reset", response_model=PasswordResetResponse)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Request password reset email.
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == reset_data.email).first()
        
        if user and user.is_active:
            # Create password reset token
            reset_token = create_password_reset_token(user.id, user.email)
            
            # TODO: Send password reset email in background
            # background_tasks.add_task(send_password_reset_email, user.email, reset_token)
            
            logger.info(f"Password reset requested for: {user.email}")
        
        # Always return the same response for security
        return PasswordResetResponse(
            message="If the email exists, a reset link has been sent."
        )
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        # Still return success to avoid email enumeration
        return PasswordResetResponse(
            message="If the email exists, a reset link has been sent."
        )


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Confirm password reset with token.
    """
    try:
        # Verify reset token
        token_data = verify_password_reset_token(reset_data.token)
        
        # Find user
        user = db.query(User).filter(User.id == token_data["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        # Update password
        user.hashed_password = hash_password(reset_data.new_password)
        db.commit()
        
        logger.info(f"Password reset completed for: {user.email}")
        
        return {"message": "Password reset successfully"}
        
    except (TokenExpiredError, InvalidTokenError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Password reset confirmation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password (requires authentication).
    """
    try:
        # Find user in database
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        user.hashed_password = hash_password(password_data.new_password)
        db.commit()
        
        logger.info(f"Password changed for user: {user.username}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


# Two-Factor Authentication Endpoints

@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_two_factor(
    setup_data: TwoFactorSetupRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Setup two-factor authentication for the current user.
    """
    try:
        from shared.services.two_factor import two_factor_service
        
        # Get user from database
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if 2FA is already enabled
        if user.two_factor_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Two-factor authentication is already enabled"
            )
        
        # Setup based on method
        if setup_data.method == "totp":
            setup_info = two_factor_service.setup_totp(user)
            
            return TwoFactorSetupResponse(
                method="totp",
                secret=setup_info["secret"],
                qr_code=setup_info["qr_code"],
                backup_codes=setup_info["backup_codes"]
            )
        
        elif setup_data.method == "sms":
            if not setup_data.phone_number:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number required for SMS 2FA"
                )
            
            # Update user's phone number
            user.phone_number = setup_data.phone_number
            db.commit()
            
            # Send SMS code
            code = two_factor_service.send_sms_code(setup_data.phone_number)
            
            return TwoFactorSetupResponse(
                method="sms",
                message="SMS code sent to your phone"
            )
        
        elif setup_data.method == "email":
            # Send email code
            code = two_factor_service.send_email_code(user.email)
            
            return TwoFactorSetupResponse(
                method="email",
                message="Email code sent to your email address"
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported 2FA method"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"2FA setup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Two-factor authentication setup failed"
        )


@router.post("/2fa/verify-setup", response_model=TwoFactorVerifyResponse)
async def verify_two_factor_setup(
    verify_data: TwoFactorVerifyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify and complete two-factor authentication setup.
    """
    try:
        from shared.services.two_factor import two_factor_service
        
        # Get user from database
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify the setup code
        if not two_factor_service.verify_setup_code(user, verify_data.code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )
        
        # Complete the setup
        completion_info = two_factor_service.complete_setup(user)
        
        # Update user in database
        user.two_factor_enabled = True
        user.two_factor_method = completion_info["method"]
        
        # Get setup data to update encrypted fields
        from shared.database import get_redis_client
        import json
        
        redis_client = get_redis_client()
        setup_key = f"2fa_setup:{user.id}"
        setup_data_json = redis_client.get(setup_key)
        
        if setup_data_json:
            setup_data = json.loads(setup_data_json)
            
            if setup_data["method"] == "totp":
                user.totp_secret = two_factor_service.encrypt_secret(setup_data["secret"])
                user.backup_codes = two_factor_service.encrypt_secret(json.dumps(setup_data["backup_codes"]))
        
        db.commit()
        
        logger.info(f"2FA setup completed for user: {user.username}")
        
        return TwoFactorVerifyResponse(
            success=True,
            message="Two-factor authentication enabled successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"2FA verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Two-factor authentication verification failed"
        )


@router.post("/2fa/verify", response_model=TwoFactorVerifyResponse)
async def verify_two_factor_code(
    verify_data: TwoFactorVerifyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify a two-factor authentication code during login.
    Note: This endpoint is typically used in the login flow.
    """
    try:
        from shared.services.two_factor import two_factor_service
        
        # Get user from database
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify the code
        is_valid = two_factor_service.verify_code(user, verify_data.code, verify_data.method)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid two-factor authentication code"
            )
        
        # If backup code was used, update the database
        if verify_data.method == "backup":
            import json
            used_codes = []
            if user.backup_codes_used:
                used_codes = json.loads(user.backup_codes_used)
            
            if verify_data.code not in used_codes:
                used_codes.append(verify_data.code)
                user.backup_codes_used = json.dumps(used_codes)
                db.commit()
        
        logger.info(f"2FA verification successful for user: {user.username}")
        
        return TwoFactorVerifyResponse(
            success=True,
            message="Two-factor authentication verified successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA code verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication verification failed"
        )


@router.post("/2fa/disable", response_model=TwoFactorVerifyResponse)
async def disable_two_factor(
    password_data: ChangePasswordRequest,  # Reuse for password confirmation
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disable two-factor authentication (requires password confirmation).
    """
    try:
        from shared.services.two_factor import two_factor_service
        
        # Get user from database
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid current password"
            )
        
        # Disable 2FA
        two_factor_service.disable_two_factor(user)
        
        # Update user in database
        user.two_factor_enabled = False
        user.totp_secret = None
        user.backup_codes = None
        user.backup_codes_used = None
        user.two_factor_method = None
        
        db.commit()
        
        logger.info(f"2FA disabled for user: {user.username}")
        
        return TwoFactorVerifyResponse(
            success=True,
            message="Two-factor authentication disabled successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"2FA disable error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable two-factor authentication"
        )


@router.post("/2fa/regenerate-backup-codes", response_model=TwoFactorSetupResponse)
async def regenerate_backup_codes(
    password_data: ChangePasswordRequest,  # Reuse for password confirmation
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Regenerate backup codes for two-factor authentication.
    """
    try:
        from shared.services.two_factor import two_factor_service
        
        # Get user from database
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if 2FA is enabled
        if not user.two_factor_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Two-factor authentication is not enabled"
            )
        
        # Verify current password
        if not verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid current password"
            )
        
        # Regenerate backup codes
        new_codes = two_factor_service.regenerate_backup_codes(user)
        
        # Update user in database
        import json
        user.backup_codes = two_factor_service.encrypt_secret(json.dumps(new_codes))
        user.backup_codes_used = None  # Reset used codes
        
        db.commit()
        
        logger.info(f"Backup codes regenerated for user: {user.username}")
        
        return TwoFactorSetupResponse(
            method="backup_codes",
            backup_codes=new_codes,
            message="New backup codes generated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Backup code regeneration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate backup codes"
        )


@router.get("/2fa/status", response_model=dict)
async def get_two_factor_status(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current two-factor authentication status.
    """
    try:
        from shared.services.two_factor import two_factor_service
        
        # Get user from database
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get 2FA status
        status_info = two_factor_service.get_two_factor_status(user)
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA status check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get two-factor authentication status"
        )


# Session Management Endpoints

@router.get("/sessions", response_model=dict)
async def get_user_sessions(
    current_user: CurrentUser = Depends(get_current_user),
    request: Request = None
):
    """
    Get all active sessions for the current user.
    """
    try:
        from shared.services.session_management import session_manager
        
        # Get user session details
        session_details = session_manager.get_user_session_details(current_user.id)
        
        # Mark current session if possible
        if request:
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                current_token = authorization[7:]
                try:
                    token_info = get_user_from_token(current_token)
                    current_jti = token_info["token_id"]
                    
                    for session in session_details:
                        session_info = session_manager.get_session(session["session_id"])
                        if session_info and session_info.access_token_jti == current_jti:
                            session["is_current"] = True
                            break
                except:
                    pass  # Ignore errors in marking current session
        
        return {
            "sessions": session_details,
            "total_count": len(session_details)
        }
        
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user sessions"
        )


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Revoke a specific session.
    """
    try:
        from shared.services.session_management import session_manager
        
        # Get session to verify ownership
        session_info = session_manager.get_session(session_id)
        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Verify session belongs to current user
        if session_info.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to revoke this session"
            )
        
        # Revoke the session
        if session_manager.revoke_session(session_id, "user_revoked"):
            logger.info(f"Session {session_id} revoked by user {current_user.username}")
            return {"message": "Session revoked successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to revoke session"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke session"
        )


@router.delete("/sessions")
async def revoke_all_sessions(
    current_user: CurrentUser = Depends(get_current_user),
    request: Request = None
):
    """
    Revoke all sessions except the current one.
    """
    try:
        from shared.services.session_management import session_manager
        
        # Identify current session to keep it active
        current_session_id = None
        if request:
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                current_token = authorization[7:]
                try:
                    token_info = get_user_from_token(current_token)
                    current_jti = token_info["token_id"]
                    
                    user_sessions = session_manager.get_user_sessions(current_user.id)
                    for session_id in user_sessions:
                        session_info = session_manager.get_session(session_id)
                        if session_info and session_info.access_token_jti == current_jti:
                            current_session_id = session_id
                            break
                except:
                    pass  # Ignore errors in finding current session
        
        # Revoke all sessions except current
        revoked_count = session_manager.revoke_all_user_sessions(
            current_user.id, 
            except_session=current_session_id
        )
        
        logger.info(f"Revoked {revoked_count} sessions for user {current_user.username}")
        
        return {
            "message": f"Revoked {revoked_count} sessions successfully",
            "sessions_revoked": revoked_count
        }
        
    except Exception as e:
        logger.error(f"Error revoking all sessions for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke sessions"
        )