"""Tests for User model and authentication system."""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from shared.models.user import User, UserRole
from shared.schemas.user import UserCreate, UserUpdate
from shared.auth import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
    calculate_reputation_score,
    determine_user_influence_weight,
    should_notify_expert
)
from shared.services.user_service import UserService


class TestUserModel:
    """Test User model functionality."""
    
    def test_user_model_creation(self):
        """Test User model instance creation."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
            full_name="Test User",
            role=UserRole.USER
        )
        
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.role == UserRole.USER
        assert user.reputation_score == 0.0
        assert user.validation_count == 0
        assert user.is_active is True
        assert user.is_verified is False
    
    def test_user_roles(self):
        """Test user role enumeration."""
        assert UserRole.ADMIN == "admin"
        assert UserRole.MODERATOR == "moderator"
        assert UserRole.EXPERT == "expert"
        assert UserRole.USER == "user"
    
    def test_user_repr(self):
        """Test User string representation."""
        user = User(
            id="test-id",
            username="testuser",
            email="test@example.com",
            hashed_password="hash",
            role=UserRole.EXPERT
        )
        
        repr_str = repr(user)
        assert "testuser" in repr_str
        assert "expert" in repr_str


class TestAuthentication:
    """Test authentication utilities."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False
    
    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "user123", "username": "testuser"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token(self):
        """Test JWT token verification."""
        data = {"sub": "user123", "username": "testuser"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        assert payload["sub"] == "user123"
        assert payload["username"] == "testuser"
        assert "exp" in payload
    
    def test_verify_expired_token(self):
        """Test verification of expired token."""
        data = {"sub": "user123"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        with pytest.raises(Exception):  # Should raise AuthenticationError
            verify_token(token)
    
    def test_calculate_reputation_score(self):
        """Test reputation score calculation."""
        # New user with no validations
        score = calculate_reputation_score(0, 0.0)
        assert score == 0.0
        
        # User with perfect accuracy and good volume
        score = calculate_reputation_score(
            validation_count=20,
            validation_accuracy=1.0,
            helpful_votes=15,
            unhelpful_votes=2,
            days_active=30
        )
        assert score > 7.0  # Should be high score
        
        # User with poor accuracy
        score = calculate_reputation_score(
            validation_count=10,
            validation_accuracy=0.3,
            helpful_votes=2,
            unhelpful_votes=8,
            days_active=10
        )
        assert score < 3.0  # Should be low score
    
    def test_determine_user_influence_weight(self):
        """Test user influence weight calculation."""
        # Regular user with low reputation
        weight = determine_user_influence_weight(2.0, "user")
        assert 0.1 <= weight <= 1.0
        
        # Expert with high reputation
        weight = determine_user_influence_weight(8.5, "expert")
        assert weight > 1.0
        
        # Admin with moderate reputation
        weight = determine_user_influence_weight(6.0, "admin")
        assert weight > 1.5
    
    def test_should_notify_expert(self):
        """Test expert notification logic."""
        # Expert with AI/ML expertise
        expert_domains = ["machine learning", "nlp", "computer vision"]
        
        # Opportunity matching AI type
        assert should_notify_expert(
            expert_domains,
            ["nlp", "text analysis"],
            ["healthcare"]
        ) is True
        
        # Opportunity matching industry
        expert_domains = ["healthcare", "medical ai"]
        assert should_notify_expert(
            expert_domains,
            ["computer vision"],
            ["healthcare", "medical"]
        ) is True
        
        # No match
        expert_domains = ["finance", "trading"]
        assert should_notify_expert(
            expert_domains,
            ["computer vision"],
            ["healthcare"]
        ) is False
        
        # General AI expertise should match
        expert_domains = ["ai", "artificial intelligence"]
        assert should_notify_expert(
            expert_domains,
            ["any_ai_type"],
            ["any_industry"]
        ) is True


class TestUserService:
    """Test UserService functionality."""
    
    @pytest.fixture
    def user_service(self):
        """Create UserService instance."""
        return UserService()
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def sample_user_create(self):
        """Sample user creation data."""
        return UserCreate(
            email="test@example.com",
            username="testuser",
            password="SecurePass123!",
            full_name="Test User",
            bio="Test bio",
            expertise_domains=["machine learning", "nlp"]
        )
    
    @pytest.mark.asyncio
    async def test_create_user(self, user_service, mock_db_session, sample_user_create):
        """Test user creation."""
        # Mock database operations
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_db_session.add = AsyncMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        
        with patch.object(user_service, 'get_user_by_email', return_value=None), \
             patch.object(user_service, 'get_user_by_username', return_value=None), \
             patch.object(user_service, '_clear_user_cache', return_value=None):
            
            user = await user_service.create_user(mock_db_session, sample_user_create)
            
            assert user.email == sample_user_create.email
            assert user.username == sample_user_create.username
            assert user.role == UserRole.EXPERT  # Should be expert due to expertise_domains
            assert user.hashed_password != sample_user_create.password  # Should be hashed
    
    @pytest.mark.asyncio
    async def test_create_duplicate_user(self, user_service, mock_db_session, sample_user_create):
        """Test creating user with duplicate email."""
        existing_user = User(
            email=sample_user_create.email,
            username="existing",
            hashed_password="hash"
        )
        
        with patch.object(user_service, 'get_user_by_email', return_value=existing_user):
            with pytest.raises(ValueError, match="User with this email already exists"):
                await user_service.create_user(mock_db_session, sample_user_create)
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, user_service, mock_db_session):
        """Test successful user authentication."""
        password = "test_password"
        hashed_password = hash_password(password)
        
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=hashed_password,
            is_active=True
        )
        
        with patch.object(user_service, 'get_user_by_email', return_value=user):
            authenticated_user = await user_service.authenticate_user(
                mock_db_session, "test@example.com", password
            )
            
            assert authenticated_user is not None
            assert authenticated_user.email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, user_service, mock_db_session):
        """Test authentication with wrong password."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=hash_password("correct_password"),
            is_active=True
        )
        
        with patch.object(user_service, 'get_user_by_email', return_value=user):
            authenticated_user = await user_service.authenticate_user(
                mock_db_session, "test@example.com", "wrong_password"
            )
            
            assert authenticated_user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self, user_service, mock_db_session):
        """Test authentication of inactive user."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=hash_password("password"),
            is_active=False
        )
        
        with patch.object(user_service, 'get_user_by_email', return_value=user):
            authenticated_user = await user_service.authenticate_user(
                mock_db_session, "test@example.com", "password"
            )
            
            assert authenticated_user is None
    
    @pytest.mark.asyncio
    async def test_get_experts_for_opportunity(self, user_service, mock_db_session):
        """Test getting relevant experts for opportunity."""
        # Mock experts with different domains
        expert1 = User(
            id="expert1",
            username="ml_expert",
            email="expert1@example.com",
            hashed_password="hash",
            role=UserRole.EXPERT,
            reputation_score=8.0,
            expertise_domains='["machine learning", "nlp"]'
        )
        
        expert2 = User(
            id="expert2",
            username="cv_expert",
            email="expert2@example.com",
            hashed_password="hash",
            role=UserRole.EXPERT,
            reputation_score=7.5,
            expertise_domains='["computer vision", "image processing"]'
        )
        
        expert3 = User(
            id="expert3",
            username="finance_expert",
            email="expert3@example.com",
            hashed_password="hash",
            role=UserRole.EXPERT,
            reputation_score=6.0,
            expertise_domains='["finance", "trading"]'
        )
        
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [expert1, expert2, expert3]
        mock_db_session.execute.return_value = mock_result
        
        # Test with NLP opportunity
        experts = await user_service.get_experts_for_opportunity(
            mock_db_session,
            ai_solution_types=["nlp", "text analysis"],
            target_industries=["healthcare"]
        )
        
        # Should return expert1 (has NLP expertise)
        assert len(experts) == 1
        assert experts[0].username == "ml_expert"
    
    @pytest.mark.asyncio
    async def test_update_user_reputation(self, user_service, mock_db_session):
        """Test user reputation update."""
        user = User(
            id="user123",
            email="test@example.com",
            username="testuser",
            hashed_password="hash",
            created_at=datetime.utcnow() - timedelta(days=30)
        )
        
        # Mock validation statistics
        mock_stats = AsyncMock()
        mock_stats.first.return_value = AsyncMock(
            validation_count=10,
            avg_score=8.5,
            helpful_votes=15,
            unhelpful_votes=2
        )
        mock_db_session.execute.return_value = mock_stats
        
        with patch.object(user_service, 'get_user_by_id', return_value=user), \
             patch.object(user_service, '_clear_user_cache', return_value=None):
            
            updated_user = await user_service.update_user_reputation(
                mock_db_session, "user123", recalculate=True
            )
            
            assert updated_user is not None
            assert updated_user.reputation_score > 0
            assert updated_user.validation_count == 10