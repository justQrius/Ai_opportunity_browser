"""Tests for discussion service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.discussion_service import DiscussionService
from shared.models.discussion import (
    Discussion, Comment, DiscussionVote, CommentVote,
    DiscussionType, DiscussionStatus, VoteType
)
from shared.models.user import User
from shared.models.opportunity import Opportunity
from shared.schemas.discussion import DiscussionCreate, CommentCreate, DiscussionSearch


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=AsyncSession)


@pytest.fixture
def discussion_service(mock_db):
    """Discussion service fixture."""
    return DiscussionService(mock_db)


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
    discussion.status = DiscussionStatus.ACTIVE
    discussion.is_pinned = False
    discussion.is_locked = False
    discussion.upvotes = 0
    discussion.downvotes = 0
    discussion.view_count = 0
    discussion.comment_count = 0
    discussion.is_flagged = False
    discussion.flag_count = 0
    discussion.moderator_reviewed = False
    discussion.last_activity_at = datetime.utcnow()
    return discussion


class TestDiscussionService:
    """Test cases for discussion service."""
    
    @pytest.mark.asyncio
    async def test_create_discussion_success(self, discussion_service, mock_db, mock_opportunity):
        """Test successful discussion creation."""
        # Setup mocks
        mock_db.get = AsyncMock(return_value=mock_opportunity)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Test data
        discussion_data = DiscussionCreate(
            title="Test Discussion",
            content="This is a test discussion",
            discussion_type=DiscussionType.GENERAL,
            opportunity_id="opp123"
        )
        
        # Call service
        with patch('shared.services.discussion_service.Discussion') as mock_discussion_class:
            mock_discussion = Mock()
            mock_discussion_class.return_value = mock_discussion
            
            result = await discussion_service.create_discussion(discussion_data, "user123")
            
            # Verify database interactions
            mock_db.get.assert_called_once_with(Opportunity, "opp123")
            mock_db.add.assert_called_once_with(mock_discussion)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_discussion)
            
            assert result == mock_discussion
    
    @pytest.mark.asyncio
    async def test_create_discussion_opportunity_not_found(self, discussion_service, mock_db):
        """Test discussion creation when opportunity doesn't exist."""
        # Setup mocks
        mock_db.get = AsyncMock(return_value=None)
        
        # Test data
        discussion_data = DiscussionCreate(
            title="Test Discussion",
            content="This is a test discussion",
            discussion_type=DiscussionType.GENERAL,
            opportunity_id="invalid_opp"
        )
        
        # Call service and expect exception
        with pytest.raises(ValueError, match="Opportunity not found"):
            await discussion_service.create_discussion(discussion_data, "user123")
        
        # Verify database interactions
        mock_db.get.assert_called_once_with(Opportunity, "invalid_opp")
    
    @pytest.mark.asyncio
    async def test_get_discussion_success(self, discussion_service, mock_db, mock_discussion):
        """Test successful discussion retrieval."""
        # Setup mocks
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_discussion)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        
        # Call service
        result = await discussion_service.get_discussion("disc123", "user123")
        
        # Verify result
        assert result == mock_discussion
        assert mock_discussion.view_count == 1  # View count should be incremented
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_discussion_not_found(self, discussion_service, mock_db):
        """Test discussion retrieval when discussion doesn't exist."""
        # Setup mocks
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call service
        result = await discussion_service.get_discussion("nonexistent", "user123")
        
        # Verify result
        assert result is None
    
    @pytest.mark.asyncio
    async def test_create_comment_success(self, discussion_service, mock_db, mock_discussion):
        """Test successful comment creation."""
        # Setup mocks
        mock_db.get.side_effect = [mock_discussion, None]  # discussion exists, no parent
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Test data
        comment_data = CommentCreate(
            content="This is a test comment",
            discussion_id="disc123",
            parent_id=None
        )
        
        # Call service
        with patch('shared.services.discussion_service.Comment') as mock_comment_class:
            mock_comment = Mock()
            mock_comment_class.return_value = mock_comment
            
            result = await discussion_service.create_comment(comment_data, "user123")
            
            # Verify database interactions
            assert mock_db.get.call_count == 1  # Only discussion lookup
            mock_db.add.assert_called_once_with(mock_comment)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_comment)
            
            # Verify discussion stats updated
            assert mock_discussion.comment_count == 1
            
            assert result == mock_comment
    
    @pytest.mark.asyncio
    async def test_create_comment_discussion_not_found(self, discussion_service, mock_db):
        """Test comment creation when discussion doesn't exist."""
        # Setup mocks
        mock_db.get = AsyncMock(return_value=None)
        
        # Test data
        comment_data = CommentCreate(
            content="This is a test comment",
            discussion_id="invalid_disc",
            parent_id=None
        )
        
        # Call service and expect exception
        with pytest.raises(ValueError, match="Discussion not found"):
            await discussion_service.create_comment(comment_data, "user123")
    
    @pytest.mark.asyncio
    async def test_create_comment_discussion_locked(self, discussion_service, mock_db, mock_discussion):
        """Test comment creation on locked discussion."""
        # Setup mocks
        mock_discussion.is_locked = True
        mock_db.get = AsyncMock(return_value=mock_discussion)
        
        # Test data
        comment_data = CommentCreate(
            content="This is a test comment",
            discussion_id="disc123",
            parent_id=None
        )
        
        # Call service and expect exception
        with pytest.raises(ValueError, match="Discussion is locked"):
            await discussion_service.create_comment(comment_data, "user123")
    
    @pytest.mark.asyncio
    async def test_vote_on_discussion_new_upvote(self, discussion_service, mock_db, mock_discussion):
        """Test voting on discussion with new upvote."""
        # Setup mocks
        mock_db.get = AsyncMock(return_value=mock_discussion)
        
        # No existing vote
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Call service
        result = await discussion_service.vote_on_discussion("disc123", "user123", VoteType.UPVOTE)
        
        # Verify result
        assert result["success"] is True
        assert result["new_vote"] == VoteType.UPVOTE
        assert result["upvotes"] == 1
        assert result["downvotes"] == 0
        
        # Verify database interactions
        mock_db.get.assert_called_once_with(Discussion, "disc123")
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_vote_on_discussion_change_vote(self, discussion_service, mock_db, mock_discussion):
        """Test changing vote on discussion."""
        # Setup mocks
        mock_db.get = AsyncMock(return_value=mock_discussion)
        mock_discussion.upvotes = 0
        mock_discussion.downvotes = 1
        
        # Existing downvote
        mock_existing_vote = Mock()
        mock_existing_vote.vote_type = VoteType.DOWNVOTE
        mock_existing_vote.updated_at = None
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_existing_vote)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Call service (change from downvote to upvote)
        result = await discussion_service.vote_on_discussion("disc123", "user123", VoteType.UPVOTE)
        
        # Verify result
        assert result["success"] is True
        assert result["new_vote"] == VoteType.UPVOTE
        assert result["upvotes"] == 1
        assert result["downvotes"] == 0
        
        # Verify vote was changed
        assert mock_existing_vote.vote_type == VoteType.UPVOTE
        assert mock_existing_vote.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_vote_on_discussion_remove_vote(self, discussion_service, mock_db, mock_discussion):
        """Test removing vote on discussion."""
        # Setup mocks
        mock_db.get = AsyncMock(return_value=mock_discussion)
        mock_discussion.upvotes = 1
        mock_discussion.downvotes = 0
        
        # Existing upvote
        mock_existing_vote = Mock()
        mock_existing_vote.vote_type = VoteType.UPVOTE
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_existing_vote)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Call service (same vote type to remove)
        result = await discussion_service.vote_on_discussion("disc123", "user123", VoteType.UPVOTE)
        
        # Verify result
        assert result["success"] is True
        assert result["new_vote"] is None
        assert result["upvotes"] == 0
        assert result["downvotes"] == 0
        
        # Verify vote was removed
        mock_db.delete.assert_called_once_with(mock_existing_vote)
    
    @pytest.mark.asyncio
    async def test_search_discussions_with_filters(self, discussion_service, mock_db, mock_discussion):
        """Test searching discussions with filters."""
        # Setup mocks
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock())
        mock_result.scalars.return_value.all = Mock(return_value=[mock_discussion])
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar = Mock(return_value=1)
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        # Test data
        search_data = DiscussionSearch(
            query="test",
            discussion_type=DiscussionType.GENERAL,
            page=1,
            page_size=20
        )
        
        # Call service
        discussions, total_count = await discussion_service.search_discussions(search_data, "user123")
        
        # Verify result
        assert len(discussions) == 1
        assert discussions[0] == mock_discussion
        assert total_count == 1
        
        # Verify database was called twice (count + select)
        assert mock_db.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_discussion_stats(self, discussion_service, mock_db):
        """Test getting discussion statistics."""
        # Setup mocks - multiple database calls for different stats
        mock_db.execute = AsyncMock()
        
        # Mock results for different queries
        mock_results = [
            Mock(scalar=Mock(return_value=10)),  # total discussions
            [("general", 5), ("technical", 3), ("business_model", 2)],  # by type
            Mock(scalar=Mock(return_value=50)),  # total comments
            Mock(scalar=Mock(return_value=15))   # total participants
        ]
        
        mock_db.execute.side_effect = [
            Mock(scalar=Mock(return_value=10)),
            Mock(__iter__=lambda self: iter([("general", 5), ("technical", 3), ("business_model", 2)])),
            Mock(scalar=Mock(return_value=50)),
            Mock(scalar=Mock(return_value=15))
        ]
        
        # Call service
        stats = await discussion_service.get_discussion_stats()
        
        # Verify result
        assert stats["total_discussions"] == 10
        assert stats["total_comments"] == 50
        assert stats["total_participants"] == 15
        assert stats["discussions_by_type"]["general"] == 5
        assert stats["discussions_by_type"]["technical"] == 3
        
        # Verify database was called for all stats
        assert mock_db.execute.call_count == 4
    
    @pytest.mark.asyncio
    async def test_get_user_votes(self, discussion_service, mock_db):
        """Test getting user votes for discussions and comments."""
        # Setup mocks
        mock_discussion_vote = Mock()
        mock_discussion_vote.discussion_id = "disc123"
        mock_discussion_vote.vote_type = VoteType.UPVOTE
        
        mock_comment_vote = Mock()
        mock_comment_vote.comment_id = "comment123"
        mock_comment_vote.vote_type = VoteType.DOWNVOTE
        
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [
            Mock(scalars=Mock(return_value=[mock_discussion_vote])),
            Mock(scalars=Mock(return_value=[mock_comment_vote]))
        ]
        
        # Call service
        votes = await discussion_service.get_user_votes(
            "user123",
            discussion_ids=["disc123"],
            comment_ids=["comment123"]
        )
        
        # Verify result
        assert votes["discussion_disc123"] == VoteType.UPVOTE
        assert votes["comment_comment123"] == VoteType.DOWNVOTE
        
        # Verify database was called twice
        assert mock_db.execute.call_count == 2