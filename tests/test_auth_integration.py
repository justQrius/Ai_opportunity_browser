"""
Integration tests for authentication system.

This module contains comprehensive tests for the authentication workflows,
including user registration, login, token management, and protected endpoints.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from api.main import create_application
from shared.database import get_db
from shared.models.base import Base
from shared.models.user import User, UserRole
from shared.schemas.auth import CurrentUser
from api.routers.auth import get_current_user
from api.middleware.auth import require_role, require_permission


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def test_app():
    """Create test FastAPI application."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create app and override dependencies
    app = create_application()
    app.dependency_overrides[get_db] = override_get_db
    
    yield app
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def db_session():
    """Create database session for testing."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_user_data():
    """Sample user registration data."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPassword123!",
        "full_name": "Test User",
        "expertise_domains": ["AI", "Machine Learning"],
        "linkedin_url": "https://linkedin.com/in/testuser",
        "github_url": "https://github.com/testuser",
        "terms_accepted": True
    }


@pytest.fixture
def sample_login_data():
    """Sample login data."""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "remember_me": False
    }


class TestUserRegistration:
    """Test user registration workflows."""
    
    def test_successful_registration(self, client, sample_user_data):
        """Test successful user registration."""
        response = client.post("/api/v1/auth/register", json=sample_user_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "user_id" in data
        assert data["email"] == sample_user_data["email"]
        assert data["username"] == sample_user_data["username"]
        assert data["verification_required"] is True
        assert "Registration successful" in data["message"]
    
    def test_duplicate_email_registration(self, client, sample_user_data):
        """Test registration with duplicate email."""
        # First registration
        client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Second registration with same email
        response = client.post("/api/v1/auth/register", json=sample_user_data)
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    def test_duplicate_username_registration(self, client, sample_user_data):
        """Test registration with duplicate username."""
        # First registration
        client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Second registration with different email but same username
        duplicate_data = sample_user_data.copy()
        duplicate_data["email"] = "different@example.com"
        
        response = client.post("/api/v1/auth/register", json=duplicate_data)
        
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]
    
    def test_invalid_email_registration(self, client, sample_user_data):
        """Test registration with invalid email."""
        invalid_data = sample_user_data.copy()
        invalid_data["email"] = "invalid-email"
        
        response = client.post("/api/v1/auth/register", json=invalid_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_weak_password_registration(self, client, sample_user_data):
        """Test registration with weak password."""
        weak_data = sample_user_data.copy()
        weak_data["password"] = "weak"
        
        response = client.post("/api/v1/auth/register", json=weak_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_terms_not_accepted_registration(self, client, sample_user_data):
        """Test registration without accepting terms."""
        invalid_data = sample_user_data.copy()
        invalid_data["terms_accepted"] = False
        
        response = client.post("/api/v1/auth/register", json=invalid_data)
        
        assert response.status_code == 422  # Validation error


class TestUserLogin:
    """Test user login workflows."""
    
    def test_successful_login(self, client, sample_user_data, sample_login_data):
        """Test successful user login."""
        # Register user first
        client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Login
        response = client.post("/api/v1/auth/login", json=sample_login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert "user" in data
        
        user_data = data["user"]
        assert user_data["email"] == sample_user_data["email"]
        assert user_data["username"] == sample_user_data["username"]
        assert user_data["role"] == "user"
    
    def test_invalid_email_login(self, client, sample_login_data):
        """Test login with invalid email."""
        invalid_login = sample_login_data.copy()
        invalid_login["email"] = "nonexistent@example.com"
        
        response = client.post("/api/v1/auth/login", json=invalid_login)
        
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]
    
    def test_invalid_password_login(self, client, sample_user_data, sample_login_data):
        """Test login with invalid password."""
        # Register user first
        client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Login with wrong password
        invalid_login = sample_login_data.copy()
        invalid_login["password"] = "WrongPassword123!"
        
        response = client.post("/api/v1/auth/login", json=invalid_login)
        
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]
    
    def test_remember_me_login(self, client, sample_user_data, sample_login_data):
        """Test login with remember me option."""
        # Register user first
        client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Login with remember me
        remember_login = sample_login_data.copy()
        remember_login["remember_me"] = True
        
        response = client.post("/api/v1/auth/login", json=remember_login)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have longer expiration time
        assert data["expires_in"] > 3600  # More than 1 hour


class TestTokenManagement:
    """Test JWT token management."""
    
    def test_token_refresh(self, client, sample_user_data, sample_login_data):
        """Test token refresh workflow."""
        # Register and login
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json=sample_login_data)
        
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        data = refresh_response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    def test_invalid_refresh_token(self, client):
        """Test refresh with invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )
        
        assert response.status_code == 401
    
    def test_get_current_user(self, client, sample_user_data, sample_login_data):
        """Test getting current user information."""
        # Register and login
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json=sample_login_data)
        
        access_token = login_response.json()["access_token"]
        
        # Get current user
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == sample_user_data["email"]
        assert data["username"] == sample_user_data["username"]
        assert data["role"] == "user"
        assert "id" in data
        assert "reputation_score" in data
    
    def test_unauthorized_access(self, client):
        """Test access without token."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 403  # No Authorization header
    
    def test_invalid_token_access(self, client):
        """Test access with invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401


class TestPasswordManagement:
    """Test password management workflows."""
    
    def test_password_reset_request(self, client, sample_user_data):
        """Test password reset request."""
        # Register user first
        client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Request password reset
        response = client.post(
            "/api/v1/auth/password-reset",
            json={"email": sample_user_data["email"]}
        )
        
        assert response.status_code == 200
        assert "reset link has been sent" in response.json()["message"]
    
    def test_password_reset_nonexistent_email(self, client):
        """Test password reset for nonexistent email."""
        response = client.post(
            "/api/v1/auth/password-reset",
            json={"email": "nonexistent@example.com"}
        )
        
        # Should still return success for security
        assert response.status_code == 200
        assert "reset link has been sent" in response.json()["message"]
    
    def test_change_password(self, client, sample_user_data, sample_login_data):
        """Test password change for authenticated user."""
        # Register and login
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json=sample_login_data)
        
        access_token = login_response.json()["access_token"]
        
        # Change password
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": sample_user_data["password"],
                "new_password": "NewPassword123!"
            },
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]
    
    def test_change_password_wrong_current(self, client, sample_user_data, sample_login_data):
        """Test password change with wrong current password."""
        # Register and login
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json=sample_login_data)
        
        access_token = login_response.json()["access_token"]
        
        # Change password with wrong current password
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewPassword123!"
            },
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 400
        assert "Current password is incorrect" in response.json()["detail"]


class TestLogout:
    """Test logout functionality."""
    
    def test_logout(self, client, sample_user_data, sample_login_data):
        """Test user logout."""
        # Register and login
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json=sample_login_data)
        
        access_token = login_response.json()["access_token"]
        
        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            json={"all_sessions": False},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Logged out successfully" in data["message"]
        assert data["sessions_terminated"] == 1
    
    def test_logout_all_sessions(self, client, sample_user_data, sample_login_data):
        """Test logout from all sessions."""
        # Register and login
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json=sample_login_data)
        
        access_token = login_response.json()["access_token"]
        
        # Logout from all sessions
        response = client.post(
            "/api/v1/auth/logout",
            json={"all_sessions": True},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Logged out successfully" in data["message"]


class TestProtectedEndpoints:
    """Test protected endpoints with authorization."""
    
    def test_protected_endpoint_without_auth(self, test_app):
        """Test accessing protected endpoint without authentication."""
        # Create a test protected endpoint
        @test_app.get("/test/protected")
        async def protected_endpoint(current_user: CurrentUser = Depends(get_current_user)):
            return {"message": f"Hello {current_user.username}"}
        
        client = TestClient(test_app)
        response = client.get("/test/protected")
        
        assert response.status_code == 403  # No Authorization header
    
    def test_protected_endpoint_with_auth(self, client, sample_user_data, sample_login_data):
        """Test accessing protected endpoint with valid authentication."""
        # Register and login
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json=sample_login_data)
        
        access_token = login_response.json()["access_token"]
        
        # Access current user endpoint (protected)
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["username"] == sample_user_data["username"]


class TestRoleBasedAccess:
    """Test role-based access control."""
    
    def test_admin_user_creation(self, db_session):
        """Test creating admin user directly in database."""
        from shared.auth import hash_password
        
        admin_user = User(
            email="admin@example.com",
            username="admin",
            hashed_password=hash_password("AdminPassword123!"),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        
        db_session.add(admin_user)
        db_session.commit()
        
        assert admin_user.role == UserRole.ADMIN
        assert admin_user.is_active is True
    
    def test_expert_user_creation(self, db_session):
        """Test creating expert user directly in database."""
        from shared.auth import hash_password
        
        expert_user = User(
            email="expert@example.com",
            username="expert",
            hashed_password=hash_password("ExpertPassword123!"),
            role=UserRole.EXPERT,
            is_active=True,
            is_verified=True,
            expertise_domains="AI,Machine Learning,NLP"
        )
        
        db_session.add(expert_user)
        db_session.commit()
        
        assert expert_user.role == UserRole.EXPERT
        assert expert_user.expertise_domains == "AI,Machine Learning,NLP"


class TestAuthenticationWorkflows:
    """Test complete authentication workflows."""
    
    def test_complete_registration_login_workflow(self, client, sample_user_data):
        """Test complete workflow from registration to accessing protected resources."""
        # 1. Register user
        register_response = client.post("/api/v1/auth/register", json=sample_user_data)
        assert register_response.status_code == 200
        
        user_id = register_response.json()["user_id"]
        
        # 2. Login user
        login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        assert login_response.status_code == 200
        
        tokens = login_response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        # 3. Access protected resource
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["id"] == user_id
        
        # 4. Refresh token
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == 200
        
        new_access_token = refresh_response.json()["access_token"]
        
        # 5. Use new token
        me_response_2 = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        assert me_response_2.status_code == 200
        
        # 6. Logout
        logout_response = client.post(
            "/api/v1/auth/logout",
            json={"all_sessions": False},
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        assert logout_response.status_code == 200
    
    def test_password_management_workflow(self, client, sample_user_data):
        """Test password management workflow."""
        # 1. Register and login
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        
        access_token = login_response.json()["access_token"]
        
        # 2. Change password
        new_password = "NewPassword123!"
        change_response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": sample_user_data["password"],
                "new_password": new_password
            },
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert change_response.status_code == 200
        
        # 3. Login with new password
        new_login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": new_password
        })
        assert new_login_response.status_code == 200
        
        # 4. Verify old password doesn't work
        old_login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        assert old_login_response.status_code == 401


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])