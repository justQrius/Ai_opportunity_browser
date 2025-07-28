"""
Discussions API endpoints for the AI Opportunity Browser.

This module provides REST API endpoints for managing community discussions,
comments, and voting mechanisms.

Supports Requirements 6.3.2 (Community features API) and 4.1-4.5 (Community Engagement).
"""

from fastapi import APIRouter, HTTPException, Query, Depends, status, Path
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.schemas.discussion import (
    DiscussionCreate, DiscussionUpdate, DiscussionResponse,
    CommentCreate, CommentUpdate, CommentResponse,
    VoteRequest, VoteResponse, DiscussionFlag, CommentFlag,
    DiscussionStats, DiscussionSearch
)
from shared.schemas.base import APIResponse, PaginatedResponse, PaginationResponse
from shared.services.discussion_service import get_discussion_service
from shared.models.discussion import DiscussionType, DiscussionStatus, VoteType
from shared.models.user import User
from api.core.dependencies import get_current_user, get_optional_user
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=APIResponse[DiscussionResponse])
async def create_discussion(
    discussion_data: DiscussionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new discussion.
    
    Supports Requirements 6.3.2 (Discussion endpoints) and 4.1 (Community engagement).
    """
    try:
        discussion_service = get_discussion_service(db)
        discussion = await discussion_service.create_discussion(
            discussion_data, current_user.id
        )
        
        # Convert to response format
        discussion_response = DiscussionResponse(
            id=discussion.id,
            title=discussion.title,
            content=discussion.content,
            discussion_type=discussion.discussion_type,
            opportunity_id=discussion.opportunity_id,
            author_id=discussion.author_id,
            status=discussion.status,
            is_pinned=discussion.is_pinned,
            is_locked=discussion.is_locked,
            upvotes=discussion.upvotes,
            downvotes=discussion.downvotes,
            view_count=discussion.view_count,
            comment_count=discussion.comment_count,
            last_activity_at=discussion.last_activity_at,
            is_flagged=discussion.is_flagged,
            flag_count=discussion.flag_count,
            moderator_reviewed=discussion.moderator_reviewed,
            created_at=discussion.created_at,
            updated_at=discussion.updated_at,
            author_username=current_user.username,
            author_reputation=current_user.reputation_score
        )
        
        logger.info(
            "Discussion created successfully",
            discussion_id=discussion.id,
            user_id=current_user.id
        )
        
        return APIResponse(
            success=True,
            data=discussion_response,
            message="Discussion created successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error creating discussion", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create discussion"
        )


@router.get("/", response_model=PaginatedResponse)
async def list_discussions(
    query: Optional[str] = Query(None, description="Search query"),
    discussion_type: Optional[DiscussionType] = Query(None, description="Filter by type"),
    status: Optional[DiscussionStatus] = Query(None, description="Filter by status"),
    opportunity_id: Optional[str] = Query(None, description="Filter by opportunity"),
    author_id: Optional[str] = Query(None, description="Filter by author"),
    is_pinned: Optional[bool] = Query(None, description="Filter pinned discussions"),
    sort_by: str = Query("last_activity_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    List discussions with filtering and pagination.
    
    Supports Requirements 6.3.2 (Discussion endpoints) and 4.2 (Community filtering).
    """
    try:
        discussion_service = get_discussion_service(db)
        
        # Create search criteria
        search_data = DiscussionSearch(
            query=query,
            discussion_type=discussion_type,
            status=status,
            author_id=author_id,
            is_pinned=is_pinned,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )
        
        discussions, total_count = await discussion_service.search_discussions(
            search_data, current_user.id if current_user else None
        )
        
        # Get user votes if authenticated
        user_votes = {}
        if current_user:
            discussion_ids = [d.id for d in discussions]
            user_votes = await discussion_service.get_user_votes(
                current_user.id, discussion_ids=discussion_ids
            )
        
        # Convert to response format
        discussion_responses = []
        for discussion in discussions:
            discussion_response = DiscussionResponse(
                id=discussion.id,
                title=discussion.title,
                content=discussion.content,
                discussion_type=discussion.discussion_type,
                opportunity_id=discussion.opportunity_id,
                author_id=discussion.author_id,
                status=discussion.status,
                is_pinned=discussion.is_pinned,
                is_locked=discussion.is_locked,
                upvotes=discussion.upvotes,
                downvotes=discussion.downvotes,
                view_count=discussion.view_count,
                comment_count=discussion.comment_count,
                last_activity_at=discussion.last_activity_at,
                is_flagged=discussion.is_flagged,
                flag_count=discussion.flag_count,
                moderator_reviewed=discussion.moderator_reviewed,
                created_at=discussion.created_at,
                updated_at=discussion.updated_at,
                author_username=discussion.author.username if discussion.author else None,
                author_reputation=discussion.author.reputation_score if discussion.author else None,
                user_vote=user_votes.get(f"discussion_{discussion.id}")
            )
            discussion_responses.append(discussion_response)
        
        # Create pagination response
        pagination = PaginationResponse.create(
            page=page,
            page_size=page_size,
            total_count=total_count
        )
        
        logger.info(
            "Discussions listed",
            total_count=total_count,
            returned_count=len(discussion_responses),
            user_id=current_user.id if current_user else None
        )
        
        return PaginatedResponse(
            items=discussion_responses,
            pagination=pagination,
            total_count=total_count
        )
        
    except Exception as e:
        logger.error("Error listing discussions", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list discussions"
        )


@router.get("/{discussion_id}", response_model=APIResponse[DiscussionResponse])
async def get_discussion(
    discussion_id: str = Path(..., description="Discussion ID"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get a specific discussion by ID.
    
    Supports Requirements 6.3.2 (Discussion endpoints).
    """
    try:
        discussion_service = get_discussion_service(db)
        discussion = await discussion_service.get_discussion(
            discussion_id, current_user.id if current_user else None
        )
        
        if not discussion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discussion not found"
            )
        
        # Get user vote if authenticated
        user_vote = None
        if current_user:
            user_votes = await discussion_service.get_user_votes(
                current_user.id, discussion_ids=[discussion_id]
            )
            user_vote = user_votes.get(f"discussion_{discussion_id}")
        
        # Convert to response format
        discussion_response = DiscussionResponse(
            id=discussion.id,
            title=discussion.title,
            content=discussion.content,
            discussion_type=discussion.discussion_type,
            opportunity_id=discussion.opportunity_id,
            author_id=discussion.author_id,
            status=discussion.status,
            is_pinned=discussion.is_pinned,
            is_locked=discussion.is_locked,
            upvotes=discussion.upvotes,
            downvotes=discussion.downvotes,
            view_count=discussion.view_count,
            comment_count=discussion.comment_count,
            last_activity_at=discussion.last_activity_at,
            is_flagged=discussion.is_flagged,
            flag_count=discussion.flag_count,
            moderator_reviewed=discussion.moderator_reviewed,
            created_at=discussion.created_at,
            updated_at=discussion.updated_at,
            author_username=discussion.author.username if discussion.author else None,
            author_reputation=discussion.author.reputation_score if discussion.author else None,
            user_vote=user_vote
        )
        
        return APIResponse(
            success=True,
            data=discussion_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting discussion", discussion_id=discussion_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get discussion"
        )


@router.put("/{discussion_id}", response_model=APIResponse[DiscussionResponse])
async def update_discussion(
    discussion_id: str = Path(..., description="Discussion ID"),
    discussion_data: DiscussionUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a discussion.
    
    Supports Requirements 6.3.2 (Discussion endpoints).
    """
    try:
        discussion_service = get_discussion_service(db)
        discussion = await discussion_service.update_discussion(
            discussion_id, discussion_data, current_user.id
        )
        
        if not discussion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discussion not found or unauthorized"
            )
        
        # Convert to response format
        discussion_response = DiscussionResponse(
            id=discussion.id,
            title=discussion.title,
            content=discussion.content,
            discussion_type=discussion.discussion_type,
            opportunity_id=discussion.opportunity_id,
            author_id=discussion.author_id,
            status=discussion.status,
            is_pinned=discussion.is_pinned,
            is_locked=discussion.is_locked,
            upvotes=discussion.upvotes,
            downvotes=discussion.downvotes,
            view_count=discussion.view_count,
            comment_count=discussion.comment_count,
            last_activity_at=discussion.last_activity_at,
            is_flagged=discussion.is_flagged,
            flag_count=discussion.flag_count,
            moderator_reviewed=discussion.moderator_reviewed,
            created_at=discussion.created_at,
            updated_at=discussion.updated_at,
            author_username=current_user.username,
            author_reputation=current_user.reputation_score
        )
        
        logger.info(
            "Discussion updated successfully",
            discussion_id=discussion_id,
            user_id=current_user.id
        )
        
        return APIResponse(
            success=True,
            data=discussion_response,
            message="Discussion updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating discussion", discussion_id=discussion_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update discussion"
        )


@router.delete("/{discussion_id}", response_model=APIResponse[dict])
async def delete_discussion(
    discussion_id: str = Path(..., description="Discussion ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a discussion.
    
    Supports Requirements 6.3.2 (Discussion endpoints).
    """
    try:
        discussion_service = get_discussion_service(db)
        success = await discussion_service.delete_discussion(discussion_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discussion not found or unauthorized"
            )
        
        logger.info(
            "Discussion deleted successfully",
            discussion_id=discussion_id,
            user_id=current_user.id
        )
        
        return APIResponse(
            success=True,
            data={"deleted": True},
            message="Discussion deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting discussion", discussion_id=discussion_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete discussion"
        )


@router.post("/{discussion_id}/vote", response_model=APIResponse[VoteResponse])
async def vote_on_discussion(
    discussion_id: str = Path(..., description="Discussion ID"),
    vote_data: VoteRequest = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Vote on a discussion.
    
    Supports Requirements 6.3.2 (Voting mechanisms).
    """
    try:
        discussion_service = get_discussion_service(db)
        result = await discussion_service.vote_on_discussion(
            discussion_id, current_user.id, vote_data.vote_type
        )
        
        vote_response = VoteResponse(
            success=result["success"],
            new_vote=result["new_vote"],
            upvotes=result["upvotes"],
            downvotes=result["downvotes"]
        )
        
        logger.info(
            "Discussion vote recorded",
            discussion_id=discussion_id,
            user_id=current_user.id,
            vote_type=vote_data.vote_type
        )
        
        return APIResponse(
            success=True,
            data=vote_response,
            message="Vote recorded successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error voting on discussion", discussion_id=discussion_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record vote"
        )


@router.post("/{discussion_id}/comments", response_model=APIResponse[CommentResponse])
async def create_comment(
    discussion_id: str = Path(..., description="Discussion ID"),
    comment_data: CommentCreate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a comment on a discussion.
    
    Supports Requirements 6.3.2 (Comment endpoints).
    """
    try:
        # Ensure discussion_id matches the path parameter
        comment_data.discussion_id = discussion_id
        
        discussion_service = get_discussion_service(db)
        comment = await discussion_service.create_comment(comment_data, current_user.id)
        
        # Convert to response format
        comment_response = CommentResponse(
            id=comment.id,
            content=comment.content,
            discussion_id=comment.discussion_id,
            author_id=comment.author_id,
            parent_id=comment.parent_id,
            upvotes=comment.upvotes,
            downvotes=comment.downvotes,
            depth=comment.depth,
            reply_count=comment.reply_count,
            is_flagged=comment.is_flagged,
            flag_count=comment.flag_count,
            moderator_reviewed=comment.moderator_reviewed,
            is_deleted=comment.is_deleted,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            author_username=current_user.username,
            author_reputation=current_user.reputation_score
        )
        
        logger.info(
            "Comment created successfully",
            comment_id=comment.id,
            discussion_id=discussion_id,
            user_id=current_user.id
        )
        
        return APIResponse(
            success=True,
            data=comment_response,
            message="Comment created successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error creating comment", discussion_id=discussion_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create comment"
        )


@router.get("/{discussion_id}/comments", response_model=PaginatedResponse)
async def get_comments(
    discussion_id: str = Path(..., description="Discussion ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    sort_by: str = Query("created_at", description="Sort field"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get comments for a discussion.
    
    Supports Requirements 6.3.2 (Comment endpoints).
    """
    try:
        discussion_service = get_discussion_service(db)
        comments, total_count = await discussion_service.get_comments(
            discussion_id, page, page_size, sort_by
        )
        
        # Get user votes if authenticated
        user_votes = {}
        if current_user:
            comment_ids = [c.id for c in comments]
            user_votes = await discussion_service.get_user_votes(
                current_user.id, comment_ids=comment_ids
            )
        
        # Convert to response format
        comment_responses = []
        for comment in comments:
            comment_response = CommentResponse(
                id=comment.id,
                content=comment.content,
                discussion_id=comment.discussion_id,
                author_id=comment.author_id,
                parent_id=comment.parent_id,
                upvotes=comment.upvotes,
                downvotes=comment.downvotes,
                depth=comment.depth,
                reply_count=comment.reply_count,
                is_flagged=comment.is_flagged,
                flag_count=comment.flag_count,
                moderator_reviewed=comment.moderator_reviewed,
                is_deleted=comment.is_deleted,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                author_username=comment.author.username if comment.author else None,
                author_reputation=comment.author.reputation_score if comment.author else None,
                user_vote=user_votes.get(f"comment_{comment.id}")
            )
            comment_responses.append(comment_response)
        
        # Create pagination response
        pagination = PaginationResponse.create(
            page=page,
            page_size=page_size,
            total_count=total_count
        )
        
        logger.info(
            "Comments retrieved",
            discussion_id=discussion_id,
            total_count=total_count,
            returned_count=len(comment_responses)
        )
        
        return PaginatedResponse(
            items=comment_responses,
            pagination=pagination,
            total_count=total_count
        )
        
    except Exception as e:
        logger.error("Error getting comments", discussion_id=discussion_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get comments"
        )


@router.post("/comments/{comment_id}/vote", response_model=APIResponse[VoteResponse])
async def vote_on_comment(
    comment_id: str = Path(..., description="Comment ID"),
    vote_data: VoteRequest = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Vote on a comment.
    
    Supports Requirements 6.3.2 (Voting mechanisms).
    """
    try:
        discussion_service = get_discussion_service(db)
        result = await discussion_service.vote_on_comment(
            comment_id, current_user.id, vote_data.vote_type
        )
        
        vote_response = VoteResponse(
            success=result["success"],
            new_vote=result["new_vote"],
            upvotes=result["upvotes"],
            downvotes=result["downvotes"]
        )
        
        logger.info(
            "Comment vote recorded",
            comment_id=comment_id,
            user_id=current_user.id,
            vote_type=vote_data.vote_type
        )
        
        return APIResponse(
            success=True,
            data=vote_response,
            message="Vote recorded successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error voting on comment", comment_id=comment_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record vote"
        )


@router.put("/comments/{comment_id}", response_model=APIResponse[CommentResponse])
async def update_comment(
    comment_id: str = Path(..., description="Comment ID"),
    comment_data: CommentUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a comment.
    
    Supports Requirements 6.3.2 (Comment endpoints).
    """
    try:
        discussion_service = get_discussion_service(db)
        comment = await discussion_service.update_comment(
            comment_id, comment_data, current_user.id
        )
        
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found or unauthorized"
            )
        
        # Convert to response format
        comment_response = CommentResponse(
            id=comment.id,
            content=comment.content,
            discussion_id=comment.discussion_id,
            author_id=comment.author_id,
            parent_id=comment.parent_id,
            upvotes=comment.upvotes,
            downvotes=comment.downvotes,
            depth=comment.depth,
            reply_count=comment.reply_count,
            is_flagged=comment.is_flagged,
            flag_count=comment.flag_count,
            moderator_reviewed=comment.moderator_reviewed,
            is_deleted=comment.is_deleted,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            author_username=current_user.username,
            author_reputation=current_user.reputation_score
        )
        
        logger.info(
            "Comment updated successfully",
            comment_id=comment_id,
            user_id=current_user.id
        )
        
        return APIResponse(
            success=True,
            data=comment_response,
            message="Comment updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating comment", comment_id=comment_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update comment"
        )


@router.delete("/comments/{comment_id}", response_model=APIResponse[dict])
async def delete_comment(
    comment_id: str = Path(..., description="Comment ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a comment.
    
    Supports Requirements 6.3.2 (Comment endpoints).
    """
    try:
        discussion_service = get_discussion_service(db)
        success = await discussion_service.delete_comment(comment_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found or unauthorized"
            )
        
        logger.info(
            "Comment deleted successfully",
            comment_id=comment_id,
            user_id=current_user.id
        )
        
        return APIResponse(
            success=True,
            data={"deleted": True},
            message="Comment deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting comment", comment_id=comment_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete comment"
        )


@router.get("/stats", response_model=APIResponse[DiscussionStats])
async def get_discussion_stats(
    opportunity_id: Optional[str] = Query(None, description="Filter by opportunity ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get discussion statistics.
    
    Supports Requirements 6.3.2 (Community analytics).
    """
    try:
        discussion_service = get_discussion_service(db)
        stats = await discussion_service.get_discussion_stats(opportunity_id)
        
        stats_response = DiscussionStats(
            total_discussions=stats["total_discussions"],
            discussions_by_type=stats["discussions_by_type"],
            total_comments=stats["total_comments"],
            total_participants=stats["total_participants"],
            most_active_discussions=[],  # TODO: Implement if needed
            recent_activity=[]  # TODO: Implement if needed
        )
        
        return APIResponse(
            success=True,
            data=stats_response
        )
        
    except Exception as e:
        logger.error("Error getting discussion stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get discussion stats"
        )