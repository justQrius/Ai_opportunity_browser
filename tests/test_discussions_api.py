"""Tests for discussions API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from api.main import app
from shared.models.discussion import Discussion, Comment, DiscussionVote, CommentVote, DiscussionType, VoteType
from shared.models.user import User, UserRole
from shared.models.opportunity import Opportunity
from shared.schemas.discussion import DiscussionCreate, CommentCreate


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=AsyncSession)


@pytest.fixture
def mock_user():
    """Mock user fixture."""
    user = Mock(spec=User)
    user.id = "user123"
    user.username = "testuser"
    user.role = UserRole.USER
    user.reputation_score = 5.0
    return user


@pytest.fixture
def mock_opportunity():
    """Mock opportunity fixture."""
    opportunity = Mock(spec=Opportunity)
    opportunity.id = "opp123"
    opportunity.title = "Test Opportunity"
    return opportunity


@pytest.fixture
def mock_discussion():
    """Mock discussion fixture."""
    discussion = Mock(spec=Discussion)
    discussion.id = "disc123"
    discussion.title = "Test Discussion"
    discussion.content = "This is a test discussion"
    discussion.discussion_type = DiscussionType.GENERAL
    discussion.opportunity_id = "opp123"
    discussion.author_id = "user123"
    discussion.upvotes = 0
    discussion.downvotes = 0
    discussion.view_count = 0
    discussion.comment_count = 0
    discussion.is_flagged = False
    discussion.flag_count = 0
    discussion.moderator_reviewed = False
    discussion.created_at = datetime.utcnow()
    discussion.updated_at = datetime.utcnow()
    discussion.last_activity_at = datetime.utcnow()
    discussion.author = Mock()
    discussion.author.username = "testuser"
    discussion.author.reputation_score = 5.0
    return discussion


class TestDiscussionsAPI:
    """Test cases for discussions API."""
    
    @patch('shared.database.get_db')
    @patch('api.core.dependencies.get_current_user')
    @patch('shared.services.discussion_service.get_discussion_service')
    def test_create_discussion_success(self, mock_service_factory, mock_get_user, mock_get_db, client, mock_user, mock_discussion):
        """Test successful discussion creation."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = Mock(spec=AsyncSession)
        
        mock_service = Mock()
        mock_service.create_discussion = AsyncMock(return_value=mock_discussion)
        mock_service_factory.return_value = mock_service
        
        # Test data
        discussion_data = {
            "title": "Test Discussion",
            "content": "This is a test discussion",
            "discussion_type": "general",
            "opportunity_id": "opp123"
        }
        
        # Make request
        response = client.post("/api/v1/discussions/", json=discussion_data)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == "Test Discussion"
        assert data["data"]["content"] == "This is a test discussion"
        assert data["data"]["discussion_type"] == "general"
        assert data["data"]["opportunity_id"] == "opp123"
        assert data["data"]["author_id"] == "user123"
        
        # Verify service was called correctly
        mock_service.create_discussion.assert_called_once()
        call_args = mock_service.create_discussion.call_args[0]
        assert call_args[1] == mock_user.id  # user_id
    
    @patch('shared.database.get_db')
    @patch('api.core.dependencies.get_current_user')
    @patch('shared.services.discussion_service.get_discussion_service')
    def test_create_discussion_invalid_opportunity(self, mock_service_factory, mock_get_user, mock_get_db, client, mock_user):
        """Test discussion creation with invalid opportunity."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = Mock(spec=AsyncSession)
        
        mock_service = Mock()
        mock_service.create_discussion = AsyncMock(side_effect=ValueError("Opportunity not found"))
        mock_service_factory.return_value = mock_service
        
        # Test data
        discussion_data = {
            "title": "Test Discussion",
            "content": "This is a test discussion",
            "discussion_type": "general",
            "opportunity_id": "invalid_opp"
        }
        
        # Make request
        response = client.post("/api/v1/discussions/", json=discussion_data)
        
        # Assert response
        assert response.status_code == 400
        assert "Opportunity not found" in response.json()["detail"]
    
    @patch('shared.database.get_db')
    @patch('api.core.dependencies.get_optional_user')
    @patch('shared.services.discussion_service.get_discussion_service')
    def test_list_discussions_success(self, mock_service_factory, mock_get_user, mock_get_db, client, mock_discussion):
        """Test successful discussion listing."""
        # Setup mocks
        mock_get_user.return_value = None  # Anonymous user
        mock_get_db.return_value = Mock(spec=AsyncSession)
        
        mock_service = Mock()
        mock_service.search_discussions = AsyncMock(return_value=([mock_discussion], 1))
        mock_service.get_user_votes = AsyncMock(return_value={})
        mock_service_factory.return_value = mock_service
        
        # Make request
        response = client.get("/api/v1/discussions/")
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Test Discussion"
        assert data["total_count"] == 1
    
    @patch('shared.database.get_db')
    @patch('api.core.dependencies.get_optional_user')
    @patch('shared.services.discussion_service.get_discussion_service')
    def test_get_discussion_success(self, mock_service_factory, mock_get_user, mock_get_db, client, mock_discussion):
        """Test successful discussion retrieval."""
        # Setup mocks
        mock_get_user.return_value = None
        mock_get_db.return_value = Mock(spec=AsyncSession)
        
        mock_service = Mock()
        mock_service.get_discussion = AsyncMock(return_value=mock_discussion)
        mock_service.get_user_votes = AsyncMock(return_value={})
        mock_service_factory.return_value = mock_service
        
        # Make request
        response = client.get(f"/api/v1/discussions/{mock_discussion.id}")
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == mock_discussion.id
        assert data["data"]["title"] == mock_discussion.title
    
    @patch('shared.database.get_db')
    @patch('api.core.dependencies.get_optional_user')
    @patch('shared.services.discussion_service.get_discussion_service')
    def test_get_discussion_not_found(self, mock_service_factory, mock_get_user, mock_get_db, client):
        """Test discussion retrieval when discussion doesn't exist."""
        # Setup mocks
        mock_get_user.return_value = None
        mock_get_db.return_value = Mock(spec=AsyncSession)
        
        mock_service = Mock()
        mock_service.get_discussion = AsyncMock(return_value=None)
        mock_service_factory.return_value = mock_service
        
        # Make request
        response = client.get("/api/v1/discussions/nonexistent")
        
        # Assert response
        assert response.status_code == 404
        assert "Discussion not found" in response.json()["detail"]
    
    @patch('shared.database.get_db')
    @patch('api.core.dependencies.get_current_user')
    @patch('shared.services.discussion_service.get_discussion_service')
    def test_vote_on_discussion_success(self, mock_service_factory, mock_get_user, mock_get_db, client, mock_user):
        """Test successful discussion voting."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = Mock(spec=AsyncSession)
        
        mock_service = Mock()
        mock_service.vote_on_discussion = AsyncMock(return_value={
            "success": True,
            "new_vote": VoteType.UPVOTE,
            "upvotes": 1,
            "downvotes": 0
        })
        mock_service_factory.return_value = mock_service
        
        # Test data
        vote_data = {"vote_type": "upvote"}
        
        # Make request
        response = client.post("/api/v1/discussions/disc123/vote", json=vote_data)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success"] is True
        assert data["data"]["new_vote"] == "upvote"
        assert data["data"]["upvotes"] == 1
        assert data["data"]["downvotes"] == 0
    
    @patch('shared.database.get_db')
    @patch('api.core.dependencies.get_current_user')
    @patch('shared.services.discussion_service.get_discussion_service')
    def test_create_comment_success(self, mock_service_factory, mock_get_user, mock_get_db, client, mock_user):
        """Test successful comment creation."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = Mock(spec=AsyncSession)
        
        mock_comment = Mock(spec=Comment)
        mock_comment.id = "comment123"
        mock_comment.content = "This is a test comment"
        mock_comment.discussion_id = "disc123"
        mock_comment.author_id = "user123"
        mock_comment.parent_id = None
        mock_comment.upvotes = 0
        mock_comment.downvotes = 0
        mock_comment.depth = 0
        mock_comment.reply_count = 0
        mock_comment.is_flagged = False
        mock_comment.flag_count = 0
        mock_comment.moderator_reviewed = False
        mock_comment.is_deleted = False
        mock_comment.created_at = datetime.utcnow()
        mock_comment.updated_at = datetime.utcnow()
        
        mock_service = Mock()
        mock_service.create_comment = AsyncMock(return_value=mock_comment)
        mock_service_factory.return_value = mock_service
        
        # Test data
        comment_data = {
            "content": "This is a test comment",
            "discussion_id": "disc123"
        }
        
        # Make request
        response = client.post("/api/v1/discussions/disc123/comments", json=comment_data)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["content"] == "This is a test comment"
        assert data["data"]["discussion_id"] == "disc123"
        assert data["data"]["author_id"] == "user123"
        assert data["data"]["depth"] == 0
    
    @patch('shared.database.get_db')
    @patch('api.core.dependencies.get_optional_user')
    @patch('shared.services.discussion_service.get_discussion_service')
    def test_get_comments_success(self, mock_service_factory, mock_get_user, mock_get_db, client):
        """Test successful comment retrieval."""
        # Setup mocks
        mock_get_user.return_value = None
        mock_get_db.return_value = Mock(spec=AsyncSession)
        
        mock_comment = Mock(spec=Comment)
        mock_comment.id = "comment123"
        mock_comment.content = "Test comment"
        mock_comment.discussion_id = "disc123"
        mock_comment.author_id = "user123"
        mock_comment.parent_id = None
        mock_comment.upvotes = 0
        mock_comment.downvotes = 0
        mock_comment.depth = 0
        mock_comment.reply_count = 0
        mock_comment.is_flagged = False
        mock_comment.flag_count = 0
        mock_comment.moderator_reviewed = False
        mock_comment.is_deleted = False
        mock_comment.created_at = datetime.utcnow()
        mock_comment.updated_at = datetime.utcnow()
        mock_comment.author = Mock()
        mock_comment.author.username = "testuser"
        mock_comment.author.reputation_score = 5.0
        
        mock_service = Mock()
        mock_service.get_comments = AsyncMock(return_value=([mock_comment], 1))
        mock_service.get_user_votes = AsyncMock(return_value={})
        mock_service_factory.return_value = mock_service
        
        # Make request
        response = client.get("/api/v1/discussions/disc123/comments")
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["content"] == "Test comment"
        assert data["total_count"] == 1
    
    @patch('shared.database.get_db')
    @patch('api.core.dependencies.get_current_user')
    @patch('shared.services.discussion_service.get_discussion_service')
    def test_vote_on_comment_success(self, mock_service_factory, mock_get_user, mock_get_db, client, mock_user):
        """Test successful comment voting."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = Mock(spec=AsyncSession)
        
        mock_service = Mock()
        mock_service.vote_on_comment = AsyncMock(return_value={
            "success": True,
            "new_vote": VoteType.DOWNVOTE,
            "upvotes": 0,
            "downvotes": 1
        })
        mock_service_factory.return_value = mock_service
        
        # Test data
        vote_data = {"vote_type": "downvote"}
        
        # Make request
        response = client.post("/api/v1/discussions/comments/comment123/vote", json=vote_data)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success"] is True
        assert data["data"]["new_vote"] == "downvote"
        assert data["data"]["upvotes"] == 0
        assert data["data"]["downvotes"] == 1
    
    @patch('shared.database.get_db')
    @patch('shared.services.discussion_service.get_discussion_service')
    def test_get_discussion_stats(self, mock_service_factory, mock_get_db, client):
        """Test discussion statistics retrieval."""
        # Setup mocks
        mock_get_db.return_value = Mock(spec=AsyncSession)
        
        mock_service = Mock()
        mock_service.get_discussion_stats = AsyncMock(return_value={
            "total_discussions": 10,
            "discussions_by_type": {"general": 5, "technical": 3, "business_model": 2},
            "total_comments": 50,
            "total_participants": 15
        })
        mock_service_factory.return_value = mock_service
        
        # Make request
        response = client.get("/api/v1/discussions/stats")
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_discussions"] == 10
        assert data["data"]["total_comments"] == 50
        assert data["data"]["total_participants"] == 15
        assert "general" in data["data"]["discussions_by_type"]
    
    def test_create_discussion_validation_errors(self, client):
        """Test discussion creation validation errors."""
        # Test missing required fields
        response = client.post("/api/v1/discussions/", json={})
        assert response.status_code == 422  # Unprocessable Entity
        
        # Test invalid discussion type
        response = client.post("/api/v1/discussions/", json={
            "title": "Test",
            "content": "Test content",
            "discussion_type": "invalid_type",
            "opportunity_id": "opp123"
        })
        assert response.status_code == 422
        
        # Test title too short
        response = client.post("/api/v1/discussions/", json={
            "title": "Te",  # Too short (min 3)
            "content": "Test content that is long enough",
            "discussion_type": "general",
            "opportunity_id": "opp123"
        })
        assert response.status_code == 422
        
        # Test content too short
        response = client.post("/api/v1/discussions/", json={
            "title": "Test Title",
            "content": "Short",  # Too short (min 10)
            "discussion_type": "general",
            "opportunity_id": "opp123"
        })
        assert response.status_code == 422
    
    def test_create_comment_validation_errors(self, client):
        """Test comment creation validation errors."""
        # Test missing content
        response = client.post("/api/v1/discussions/disc123/comments", json={})
        assert response.status_code == 422
        
        # Test empty content
        response = client.post("/api/v1/discussions/disc123/comments", json={
            "content": "",
            "discussion_id": "disc123"
        })
        assert response.status_code == 422