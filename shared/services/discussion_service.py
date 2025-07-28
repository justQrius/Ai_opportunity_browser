"""Discussion service for managing community discussions and comments."""

from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.future import select

from shared.models.discussion import (
    Discussion, Comment, DiscussionVote, CommentVote,
    DiscussionType, DiscussionStatus, VoteType
)
from shared.models.user import User
from shared.models.opportunity import Opportunity
from shared.schemas.discussion import (
    DiscussionCreate, DiscussionUpdate, CommentCreate, CommentUpdate,
    DiscussionSearch
)
from shared.cache import get_cache_key, cache_get, cache_set
import structlog

logger = structlog.get_logger(__name__)


class DiscussionService:
    """Service for managing discussions and comments.
    
    Supports Requirements 6.3.2 (Community features API) and 4.1-4.5 (Community Engagement).
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_discussion(
        self,
        discussion_data: DiscussionCreate,
        user_id: str
    ) -> Discussion:
        """Create a new discussion.
        
        Args:
            discussion_data: Discussion creation data
            user_id: ID of the user creating the discussion
            
        Returns:
            Created discussion
            
        Raises:
            ValueError: If opportunity doesn't exist or user lacks permissions
        """
        # Verify opportunity exists
        opportunity = await self.db.get(Opportunity, discussion_data.opportunity_id)
        if not opportunity:
            raise ValueError("Opportunity not found")
        
        # Create discussion
        discussion = Discussion(
            **discussion_data.model_dump(),
            author_id=user_id,
            last_activity_at=datetime.utcnow()
        )
        
        self.db.add(discussion)
        await self.db.commit()
        await self.db.refresh(discussion)
        
        logger.info(
            "Discussion created",
            discussion_id=discussion.id,
            opportunity_id=discussion_data.opportunity_id,
            author_id=user_id
        )
        
        return discussion
    
    async def get_discussion(self, discussion_id: str, user_id: Optional[str] = None) -> Optional[Discussion]:
        """Get a discussion by ID.
        
        Args:
            discussion_id: Discussion ID
            user_id: Optional user ID for vote information
            
        Returns:
            Discussion if found, None otherwise
        """
        query = select(Discussion).where(Discussion.id == discussion_id).options(
            selectinload(Discussion.author),
            selectinload(Discussion.opportunity),
            selectinload(Discussion.votes)
        )
        
        result = await self.db.execute(query)
        discussion = result.scalar_one_or_none()
        
        if discussion:
            # Increment view count
            discussion.view_count += 1
            await self.db.commit()
        
        return discussion
    
    async def update_discussion(
        self,
        discussion_id: str,
        discussion_data: DiscussionUpdate,
        user_id: str
    ) -> Optional[Discussion]:
        """Update a discussion.
        
        Args:
            discussion_id: Discussion ID
            discussion_data: Updated discussion data
            user_id: ID of user updating the discussion
            
        Returns:
            Updated discussion if successful, None if not found or unauthorized
        """
        discussion = await self.db.get(Discussion, discussion_id)
        if not discussion or discussion.author_id != user_id:
            return None
        
        # Update fields
        update_data = discussion_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(discussion, field, value)
        
        discussion.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(discussion)
        
        logger.info(
            "Discussion updated",
            discussion_id=discussion_id,
            user_id=user_id
        )
        
        return discussion
    
    async def delete_discussion(self, discussion_id: str, user_id: str) -> bool:
        """Delete a discussion.
        
        Args:
            discussion_id: Discussion ID
            user_id: ID of user deleting the discussion
            
        Returns:
            True if deleted successfully, False otherwise
        """
        discussion = await self.db.get(Discussion, discussion_id)
        if not discussion or discussion.author_id != user_id:
            return False
        
        discussion.status = DiscussionStatus.DELETED
        await self.db.commit()
        
        logger.info(
            "Discussion deleted",
            discussion_id=discussion_id,
            user_id=user_id
        )
        
        return True
    
    async def search_discussions(
        self,
        search_data: DiscussionSearch,
        user_id: Optional[str] = None
    ) -> Tuple[List[Discussion], int]:
        """Search discussions with filtering and pagination.
        
        Args:
            search_data: Search criteria
            user_id: Optional user ID for personalization
            
        Returns:
            Tuple of (discussions, total_count)
        """
        query = select(Discussion).options(
            selectinload(Discussion.author),
            selectinload(Discussion.opportunity)
        )
        
        # Apply filters
        conditions = []
        
        if search_data.query:
            search_term = f"%{search_data.query}%"
            conditions.append(
                or_(
                    Discussion.title.ilike(search_term),
                    Discussion.content.ilike(search_term)
                )
            )
        
        if search_data.discussion_type:
            conditions.append(Discussion.discussion_type == search_data.discussion_type)
        
        if search_data.status:
            conditions.append(Discussion.status == search_data.status)
        else:
            # Default to active discussions
            conditions.append(Discussion.status == DiscussionStatus.ACTIVE)
        
        if search_data.author_id:
            conditions.append(Discussion.author_id == search_data.author_id)
        
        if search_data.is_pinned is not None:
            conditions.append(Discussion.is_pinned == search_data.is_pinned)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count(Discussion.id)).where(query.whereclause)
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar()
        
        # Apply sorting
        if search_data.sort_by == "created_at":
            sort_col = Discussion.created_at
        elif search_data.sort_by == "upvotes":
            sort_col = Discussion.upvotes
        elif search_data.sort_by == "comment_count":
            sort_col = Discussion.comment_count
        else:  # default to last_activity_at
            sort_col = Discussion.last_activity_at
        
        if search_data.sort_order == "asc":
            query = query.order_by(asc(sort_col))
        else:
            query = query.order_by(desc(sort_col))
        
        # Apply pagination
        offset = (search_data.page - 1) * search_data.page_size
        query = query.offset(offset).limit(search_data.page_size)
        
        # Execute query
        result = await self.db.execute(query)
        discussions = result.scalars().all()
        
        return list(discussions), total_count
    
    async def create_comment(
        self,
        comment_data: CommentCreate,
        user_id: str
    ) -> Comment:
        """Create a new comment.
        
        Args:
            comment_data: Comment creation data
            user_id: ID of the user creating the comment
            
        Returns:
            Created comment
            
        Raises:
            ValueError: If discussion doesn't exist or parent comment is invalid
        """
        # Verify discussion exists
        discussion = await self.db.get(Discussion, comment_data.discussion_id)
        if not discussion:
            raise ValueError("Discussion not found")
        
        if discussion.is_locked:
            raise ValueError("Discussion is locked")
        
        # Calculate depth and verify parent
        depth = 0
        if comment_data.parent_id:
            parent = await self.db.get(Comment, comment_data.parent_id)
            if not parent or parent.discussion_id != comment_data.discussion_id:
                raise ValueError("Invalid parent comment")
            depth = parent.depth + 1
            if depth > 5:  # Limit nesting depth
                raise ValueError("Maximum comment depth exceeded")
        
        # Create comment
        comment = Comment(
            **comment_data.model_dump(),
            author_id=user_id,
            depth=depth
        )
        
        self.db.add(comment)
        
        # Update discussion stats
        discussion.comment_count += 1
        discussion.last_activity_at = datetime.utcnow()
        
        # Update parent comment stats
        if comment_data.parent_id:
            parent = await self.db.get(Comment, comment_data.parent_id)
            if parent:
                parent.reply_count += 1
        
        await self.db.commit()
        await self.db.refresh(comment)
        
        logger.info(
            "Comment created",
            comment_id=comment.id,
            discussion_id=comment_data.discussion_id,
            author_id=user_id,
            depth=depth
        )
        
        return comment
    
    async def get_comments(
        self,
        discussion_id: str,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "created_at"
    ) -> Tuple[List[Comment], int]:
        """Get comments for a discussion.
        
        Args:
            discussion_id: Discussion ID
            page: Page number
            page_size: Page size
            sort_by: Sort field (created_at, upvotes)
            
        Returns:
            Tuple of (comments, total_count)
        """
        # Get top-level comments only (depth = 0)
        query = select(Comment).where(
            and_(
                Comment.discussion_id == discussion_id,
                Comment.depth == 0,
                Comment.is_deleted == False
            )
        ).options(
            selectinload(Comment.author),
            selectinload(Comment.replies)
        )
        
        # Apply sorting
        if sort_by == "upvotes":
            query = query.order_by(desc(Comment.upvotes))
        else:
            query = query.order_by(Comment.created_at)
        
        # Get total count
        count_query = select(func.count(Comment.id)).where(
            and_(
                Comment.discussion_id == discussion_id,
                Comment.depth == 0,
                Comment.is_deleted == False
            )
        )
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        result = await self.db.execute(query)
        comments = result.scalars().all()
        
        return list(comments), total_count
    
    async def update_comment(
        self,
        comment_id: str,
        comment_data: CommentUpdate,
        user_id: str
    ) -> Optional[Comment]:
        """Update a comment.
        
        Args:
            comment_id: Comment ID
            comment_data: Updated comment data
            user_id: ID of user updating the comment
            
        Returns:
            Updated comment if successful, None if not found or unauthorized
        """
        comment = await self.db.get(Comment, comment_id)
        if not comment or comment.author_id != user_id or comment.is_deleted:
            return None
        
        comment.content = comment_data.content
        comment.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(comment)
        
        logger.info(
            "Comment updated",
            comment_id=comment_id,
            user_id=user_id
        )
        
        return comment
    
    async def delete_comment(self, comment_id: str, user_id: str) -> bool:
        """Delete a comment (soft delete).
        
        Args:
            comment_id: Comment ID
            user_id: ID of user deleting the comment
            
        Returns:
            True if deleted successfully, False otherwise
        """
        comment = await self.db.get(Comment, comment_id)
        if not comment or comment.author_id != user_id:
            return False
        
        comment.is_deleted = True
        comment.updated_at = datetime.utcnow()
        
        # Update discussion comment count
        discussion = await self.db.get(Discussion, comment.discussion_id)
        if discussion:
            discussion.comment_count -= 1
        
        await self.db.commit()
        
        logger.info(
            "Comment deleted",
            comment_id=comment_id,
            user_id=user_id
        )
        
        return True
    
    async def vote_on_discussion(
        self,
        discussion_id: str,
        user_id: str,
        vote_type: VoteType
    ) -> Dict[str, Any]:
        """Vote on a discussion.
        
        Args:
            discussion_id: Discussion ID
            user_id: User ID
            vote_type: Type of vote
            
        Returns:
            Dictionary with vote result and updated counts
        """
        discussion = await self.db.get(Discussion, discussion_id)
        if not discussion:
            raise ValueError("Discussion not found")
        
        # Check for existing vote
        existing_vote_query = select(DiscussionVote).where(
            and_(
                DiscussionVote.discussion_id == discussion_id,
                DiscussionVote.user_id == user_id
            )
        )
        result = await self.db.execute(existing_vote_query)
        existing_vote = result.scalar_one_or_none()
        
        new_vote = None
        
        if existing_vote:
            if existing_vote.vote_type == vote_type:
                # Remove vote if same type
                await self.db.delete(existing_vote)
                if vote_type == VoteType.UPVOTE:
                    discussion.upvotes -= 1
                else:
                    discussion.downvotes -= 1
            else:
                # Change vote type
                existing_vote.vote_type = vote_type
                existing_vote.updated_at = datetime.utcnow()
                new_vote = vote_type
                
                # Update counts
                if vote_type == VoteType.UPVOTE:
                    discussion.upvotes += 1
                    discussion.downvotes -= 1
                else:
                    discussion.downvotes += 1
                    discussion.upvotes -= 1
        else:
            # Create new vote
            vote = DiscussionVote(
                discussion_id=discussion_id,
                user_id=user_id,
                vote_type=vote_type
            )
            self.db.add(vote)
            new_vote = vote_type
            
            # Update counts
            if vote_type == VoteType.UPVOTE:
                discussion.upvotes += 1
            else:
                discussion.downvotes += 1
        
        await self.db.commit()
        await self.db.refresh(discussion)
        
        return {
            "success": True,
            "new_vote": new_vote,
            "upvotes": discussion.upvotes,
            "downvotes": discussion.downvotes
        }
    
    async def vote_on_comment(
        self,
        comment_id: str,
        user_id: str,
        vote_type: VoteType
    ) -> Dict[str, Any]:
        """Vote on a comment.
        
        Args:
            comment_id: Comment ID
            user_id: User ID
            vote_type: Type of vote
            
        Returns:
            Dictionary with vote result and updated counts
        """
        comment = await self.db.get(Comment, comment_id)
        if not comment:
            raise ValueError("Comment not found")
        
        # Check for existing vote
        existing_vote_query = select(CommentVote).where(
            and_(
                CommentVote.comment_id == comment_id,
                CommentVote.user_id == user_id
            )
        )
        result = await self.db.execute(existing_vote_query)
        existing_vote = result.scalar_one_or_none()
        
        new_vote = None
        
        if existing_vote:
            if existing_vote.vote_type == vote_type:
                # Remove vote if same type
                await self.db.delete(existing_vote)
                if vote_type == VoteType.UPVOTE:
                    comment.upvotes -= 1
                else:
                    comment.downvotes -= 1
            else:
                # Change vote type
                existing_vote.vote_type = vote_type
                existing_vote.updated_at = datetime.utcnow()
                new_vote = vote_type
                
                # Update counts
                if vote_type == VoteType.UPVOTE:
                    comment.upvotes += 1
                    comment.downvotes -= 1
                else:
                    comment.downvotes += 1
                    comment.upvotes -= 1
        else:
            # Create new vote
            vote = CommentVote(
                comment_id=comment_id,
                user_id=user_id,
                vote_type=vote_type
            )
            self.db.add(vote)
            new_vote = vote_type
            
            # Update counts
            if vote_type == VoteType.UPVOTE:
                comment.upvotes += 1
            else:
                comment.downvotes += 1
        
        await self.db.commit()
        await self.db.refresh(comment)
        
        return {
            "success": True,
            "new_vote": new_vote,
            "upvotes": comment.upvotes,
            "downvotes": comment.downvotes
        }
    
    async def get_user_votes(
        self,
        user_id: str,
        discussion_ids: Optional[List[str]] = None,
        comment_ids: Optional[List[str]] = None
    ) -> Dict[str, VoteType]:
        """Get user votes for discussions and comments.
        
        Args:
            user_id: User ID
            discussion_ids: Optional list of discussion IDs
            comment_ids: Optional list of comment IDs
            
        Returns:
            Dictionary mapping item IDs to vote types
        """
        votes = {}
        
        if discussion_ids:
            query = select(DiscussionVote).where(
                and_(
                    DiscussionVote.user_id == user_id,
                    DiscussionVote.discussion_id.in_(discussion_ids)
                )
            )
            result = await self.db.execute(query)
            for vote in result.scalars():
                votes[f"discussion_{vote.discussion_id}"] = vote.vote_type
        
        if comment_ids:
            query = select(CommentVote).where(
                and_(
                    CommentVote.user_id == user_id,
                    CommentVote.comment_id.in_(comment_ids)
                )
            )
            result = await self.db.execute(query)
            for vote in result.scalars():
                votes[f"comment_{vote.comment_id}"] = vote.vote_type
        
        return votes
    
    async def get_discussion_stats(self, opportunity_id: Optional[str] = None) -> Dict[str, Any]:
        """Get discussion statistics.
        
        Args:
            opportunity_id: Optional opportunity ID to filter stats
            
        Returns:
            Dictionary with discussion statistics
        """
        # Base query
        query = select(Discussion)
        if opportunity_id:
            query = query.where(Discussion.opportunity_id == opportunity_id)
        
        # Total discussions
        total_result = await self.db.execute(
            select(func.count(Discussion.id)).where(query.whereclause)
        )
        total_discussions = total_result.scalar()
        
        # Discussions by type
        type_query = select(
            Discussion.discussion_type,
            func.count(Discussion.id)
        ).group_by(Discussion.discussion_type)
        if opportunity_id:
            type_query = type_query.where(Discussion.opportunity_id == opportunity_id)
        
        type_result = await self.db.execute(type_query)
        discussions_by_type = {row[0]: row[1] for row in type_result}
        
        # Total comments
        comment_query = select(func.sum(Discussion.comment_count))
        if opportunity_id:
            comment_query = comment_query.where(Discussion.opportunity_id == opportunity_id)
        
        comment_result = await self.db.execute(comment_query)
        total_comments = comment_result.scalar() or 0
        
        # Total participants (unique authors)
        participant_query = select(func.count(func.distinct(Discussion.author_id)))
        if opportunity_id:
            participant_query = participant_query.where(Discussion.opportunity_id == opportunity_id)
        
        participant_result = await self.db.execute(participant_query)
        total_participants = participant_result.scalar()
        
        return {
            "total_discussions": total_discussions,
            "discussions_by_type": discussions_by_type,
            "total_comments": total_comments,
            "total_participants": total_participants
        }


def get_discussion_service(db: AsyncSession) -> DiscussionService:
    """Get discussion service instance."""
    return DiscussionService(db)