#!/usr/bin/env python3
"""
Test script for JWT utilities and authentication functions.
This script validates that JWT token generation, validation, and refresh work correctly.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import time

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_jwt_imports():
    """Test that JWT utilities can be imported successfully."""
    print("🧪 Testing JWT Utility Imports")
    print("=" * 40)
    
    try:
        from shared.auth import (
            hash_password, verify_password, create_access_token, create_refresh_token,
            verify_token, refresh_access_token, get_user_from_token,
            create_password_reset_token, verify_password_reset_token,
            TokenPayload, AuthenticationError, TokenExpiredError, InvalidTokenError
        )
        from shared.models.user import UserRole
        
        print("✅ JWT utility functions imported successfully")
        print("✅ Exception classes imported successfully")
        print("✅ TokenPayload class imported successfully")
        print("✅ UserRole enum imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ JWT utility import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_password_hashing():
    """Test password hashing and verification."""
    print("\n🔒 Testing Password Hashing")
    print("=" * 40)
    
    try:
        from shared.auth import hash_password, verify_password
        
        # Test password hashing
        test_password = "SecurePassword123!"
        hashed = hash_password(test_password)
        
        print(f"✅ Password hashed successfully")
        print(f"  Original length: {len(test_password)}")
        print(f"  Hash length: {len(hashed)}")
        print(f"  Hash starts with: {hashed[:10]}...")
        
        # Test password verification - correct password
        is_valid = verify_password(test_password, hashed)
        if is_valid:
            print("✅ Password verification successful (correct password)")
        else:
            print("❌ Password verification failed (correct password)")
            return False
        
        # Test password verification - incorrect password
        is_invalid = verify_password("WrongPassword", hashed)
        if not is_invalid:
            print("✅ Password verification successful (incorrect password rejected)")
        else:
            print("❌ Password verification failed (incorrect password accepted)")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Password hashing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_token_creation():
    """Test JWT token creation."""
    print("\n🎫 Testing Token Creation")
    print("=" * 40)
    
    try:
        from shared.auth import create_access_token, create_refresh_token
        from shared.models.user import UserRole
        
        # Test data
        user_id = "test-user-123"
        email = "test@example.com"
        username = "testuser"
        role = UserRole.USER
        
        # Test access token creation
        access_token = create_access_token(user_id, email, username, role)
        print(f"✅ Access token created successfully")
        print(f"  Token length: {len(access_token)}")
        print(f"  Token starts with: {access_token[:20]}...")
        
        # Test refresh token creation
        refresh_token = create_refresh_token(user_id, email, username, role)
        print(f"✅ Refresh token created successfully")
        print(f"  Token length: {len(refresh_token)}")
        print(f"  Token starts with: {refresh_token[:20]}...")
        
        # Verify tokens are different
        if access_token != refresh_token:
            print("✅ Access and refresh tokens are different")
        else:
            print("❌ Access and refresh tokens are identical")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Token creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_token_verification():
    """Test JWT token verification."""
    print("\n🔍 Testing Token Verification")
    print("=" * 40)
    
    try:
        from shared.auth import create_access_token, create_refresh_token, verify_token, get_user_from_token
        from shared.models.user import UserRole
        
        # Test data
        user_id = "test-user-456"
        email = "verify@example.com"
        username = "verifyuser"
        role = UserRole.EXPERT
        
        # Create tokens
        access_token = create_access_token(user_id, email, username, role)
        refresh_token = create_refresh_token(user_id, email, username, role)
        
        # Test access token verification
        access_payload = verify_token(access_token, "access")
        print(f"✅ Access token verified successfully")
        print(f"  User ID: {access_payload.sub}")
        print(f"  Username: {access_payload.username}")
        print(f"  Role: {access_payload.role}")
        print(f"  Token type: {access_payload.token_type}")
        
        # Verify payload data
        if (access_payload.sub == user_id and 
            access_payload.username == username and 
            access_payload.email == email and
            access_payload.role == role.value):
            print("✅ Access token payload data correct")
        else:
            print("❌ Access token payload data incorrect")
            return False
        
        # Test refresh token verification
        refresh_payload = verify_token(refresh_token, "refresh")
        print(f"✅ Refresh token verified successfully")
        print(f"  Token type: {refresh_payload.token_type}")
        
        # Test get_user_from_token
        user_info = get_user_from_token(access_token)
        print(f"✅ User info extracted from token")
        print(f"  User info keys: {list(user_info.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Token verification test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_token_refresh():
    """Test JWT token refresh mechanism."""
    print("\n🔄 Testing Token Refresh")
    print("=" * 40)
    
    try:
        from shared.auth import create_refresh_token, refresh_access_token
        from shared.models.user import UserRole
        
        # Test data
        user_id = "test-user-789"
        email = "refresh@example.com"
        username = "refreshuser"
        role = UserRole.MODERATOR
        
        # Create refresh token
        refresh_token = create_refresh_token(user_id, email, username, role)
        
        # Test token refresh
        new_access_token, new_refresh_token = refresh_access_token(refresh_token)
        
        print(f"✅ Token refresh successful")
        print(f"  New access token length: {len(new_access_token)}")
        print(f"  New refresh token length: {len(new_refresh_token)}")
        
        # Verify new tokens are different from original
        if new_refresh_token != refresh_token:
            print("✅ New refresh token is different from original")
        else:
            print("❌ New refresh token is same as original")
            return False
        
        # Verify new access token works
        from shared.auth import verify_token
        new_payload = verify_token(new_access_token, "access")
        
        if (new_payload.sub == user_id and 
            new_payload.username == username):
            print("✅ New access token is valid and contains correct data")
        else:
            print("❌ New access token is invalid or contains incorrect data")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Token refresh test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_password_reset_tokens():
    """Test password reset token functionality."""
    print("\n🔑 Testing Password Reset Tokens")
    print("=" * 40)
    
    try:
        from shared.auth import create_password_reset_token, verify_password_reset_token
        
        # Test data
        user_id = "reset-user-123"
        email = "reset@example.com"
        
        # Create password reset token
        reset_token = create_password_reset_token(user_id, email)
        print(f"✅ Password reset token created")
        print(f"  Token length: {len(reset_token)}")
        
        # Verify password reset token
        reset_data = verify_password_reset_token(reset_token)
        print(f"✅ Password reset token verified")
        print(f"  User ID: {reset_data['user_id']}")
        print(f"  Email: {reset_data['email']}")
        
        # Verify data is correct
        if (reset_data['user_id'] == user_id and 
            reset_data['email'] == email):
            print("✅ Password reset token data is correct")
        else:
            print("❌ Password reset token data is incorrect")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Password reset token test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_token_expiration():
    """Test token expiration handling."""
    print("\n⏰ Testing Token Expiration")
    print("=" * 40)
    
    try:
        from shared.auth import create_access_token, verify_token, TokenExpiredError
        from shared.models.user import UserRole
        from datetime import timedelta
        
        # Test data
        user_id = "expire-user-123"
        email = "expire@example.com"
        username = "expireuser"
        role = UserRole.USER
        
        # Create token with very short expiration (1 second)
        short_token = create_access_token(
            user_id, email, username, role,
            expires_delta=timedelta(seconds=1)
        )
        
        print("✅ Short-lived token created (1 second expiration)")
        
        # Verify token works initially
        payload = verify_token(short_token, "access")
        print("✅ Token verified successfully before expiration")
        
        # Wait for token to expire
        print("⏳ Waiting for token to expire...")
        time.sleep(2)
        
        # Try to verify expired token
        try:
            verify_token(short_token, "access")
            print("❌ Expired token was accepted (should have been rejected)")
            return False
        except TokenExpiredError:
            print("✅ Expired token correctly rejected")
        
        return True
        
    except Exception as e:
        print(f"❌ Token expiration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_invalid_tokens():
    """Test handling of invalid tokens."""
    print("\n🚫 Testing Invalid Token Handling")
    print("=" * 40)
    
    try:
        from shared.auth import verify_token, InvalidTokenError, TokenExpiredError
        
        # Test completely invalid token
        try:
            verify_token("invalid.token.here", "access")
            print("❌ Invalid token was accepted")
            return False
        except InvalidTokenError:
            print("✅ Invalid token correctly rejected")
        
        # Test empty token
        try:
            verify_token("", "access")
            print("❌ Empty token was accepted")
            return False
        except InvalidTokenError:
            print("✅ Empty token correctly rejected")
        
        # Test malformed token
        try:
            verify_token("malformed-token-without-dots", "access")
            print("❌ Malformed token was accepted")
            return False
        except InvalidTokenError:
            print("✅ Malformed token correctly rejected")
        
        return True
        
    except Exception as e:
        print(f"❌ Invalid token test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_requirements_compliance():
    """Test that JWT utilities meet requirements."""
    print("\n📋 Testing Requirements Compliance")
    print("=" * 40)
    
    try:
        # Task 2.2.1 requires:
        # - Token generation and validation functions ✅
        # - Token refresh mechanism ✅
        
        from shared.auth import (
            create_access_token, create_refresh_token, verify_token, 
            refresh_access_token, hash_password, verify_password
        )
        
        print("✅ Token generation functions implemented:")
        print("  - create_access_token")
        print("  - create_refresh_token")
        print("  - create_password_reset_token")
        
        print("✅ Token validation functions implemented:")
        print("  - verify_token")
        print("  - get_user_from_token")
        print("  - verify_password_reset_token")
        
        print("✅ Token refresh mechanism implemented:")
        print("  - refresh_access_token")
        
        print("✅ Password security functions implemented:")
        print("  - hash_password")
        print("  - verify_password")
        
        print("✅ Error handling implemented:")
        print("  - AuthenticationError")
        print("  - TokenExpiredError")
        print("  - InvalidTokenError")
        
        # Verify alignment with Requirements 4.1 (Expert profiles) and authentication
        from shared.models.user import UserRole
        
        # Test that all user roles are supported
        roles_tested = [UserRole.USER, UserRole.EXPERT, UserRole.MODERATOR, UserRole.ADMIN]
        for role in roles_tested:
            token = create_access_token("test", "test@example.com", "test", role)
            payload = verify_token(token, "access")
            if payload.role != role.value:
                print(f"❌ Role {role} not properly handled in tokens")
                return False
        
        print("✅ All user roles supported in JWT tokens")
        print("✅ Requirements compliance verified")
        
        return True
        
    except Exception as e:
        print(f"❌ Requirements compliance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all JWT utility tests."""
    print("🔐 JWT UTILITIES TEST SUITE")
    print("=" * 60)
    print("Testing JWT token generation, validation, and refresh mechanisms.")
    
    tests = [
        test_jwt_imports,
        test_password_hashing,
        test_token_creation,
        test_token_verification,
        test_token_refresh,
        test_password_reset_tokens,
        test_token_expiration,
        test_invalid_tokens,
        test_requirements_compliance
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All JWT utility tests passed!")
        print("\nKey Achievements:")
        print("✅ JWT token generation and validation working")
        print("✅ Token refresh mechanism implemented")
        print("✅ Password hashing and verification secure")
        print("✅ Error handling comprehensive")
        print("✅ Requirements compliance verified")
        print("\nJWT utilities are ready for authentication system!")
        return 0
    else:
        print("❌ Some JWT utility tests failed!")
        print("Please fix the issues before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())