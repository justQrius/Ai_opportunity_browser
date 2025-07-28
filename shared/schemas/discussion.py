"""Discussion-related Pydantic schemas."""

from typing import Optional, List
from datetime import datetime
from pydantic import Field
from .base import BaseSchema, TimestampSchema, UUIDSchema
from shared.models.discussion import DiscussionType, DiscussionStatus, VoteType


class DiscussionBase(BaseSchema):
    """Base discussion schema."""
    
    title: str = Field(..., min_length=3, max_length=255, description="Discussion title")
    content: str = Field(..., min_length=10, max_length=10000, description="Discussion content")
    discussion_type: DiscussionType = Field(DiscussionType.GENERAL, description="Type of discussion")


class DiscussionCreate(DiscussionBase):
    """Schema for creating discussions.
    
    Supports Requirements 6.3.2 (Community features API).
    """
    
    opportunity_id: str = Field(..., description="Opportunity this discussion is about")


class DiscussionUpdate(BaseSchema):
    """Schema for updating discussions."""
    
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    content: Optional[str] = Field(None, min_length=10, max_length=10000)
    discussion_type: Optional[DiscussionType] = None


class DiscussionResponse(DiscussionBase, UUIDSchema, TimestampSchema):
    """Schema for discussion responses.
    
    Supports Requirements 4.1-4.5 (Community discussion and feedback).
    """
    
    opportunity_id: str
    author_id: str
    status: DiscussionStatus
    is_pinned: bool
    is_locked: bool
    
    # Community engagement metrics
    upvotes: int
    downvotes: int
    view_count: int
    comment_count: int
    last_activity_at: datetime
    
    # Moderation fields
    is_flagged: bool
    flag_count: int
    moderator_reviewed: bool
    
    # Author information (from relationship)
    author_username: Optional[str] = None
    author_reputation: Optional[float] = None
    
    # User's vote on this discussion (if authenticated)
    user_vote: Optional[VoteType] = None


class CommentBase(BaseSchema):
    """Base comment schema."""
    
    content: str = Field(..., min_length=1, max_length=2000, description="Comment content")


class CommentCreate(CommentBase):
    """Schema for creating comments.
    
    Supports Requirements 6.3.2 (Discussion and comment endpoints).
    """
    
    discussion_id: str = Field(..., description="Discussion this comment belongs to")
    parent_id: Optional[str] = Field(None, description="Parent comment for threaded replies")


class CommentUpdate(BaseSchema):
    """Schema for updating comments."""
    
    content: str = Field(..., min_length=1, max_length=2000)


class CommentResponse(CommentBase, UUIDSchema, TimestampSchema):
    """Schema for comment responses.
    
    Supports Requirements 4.1-4.5 (Community discussion and feedback).
    """
    
    discussion_id: str
    author_id: str
    parent_id: Optional[str]
    
    # Community engagement metrics
    upvotes: int
    downvotes: int
    
    # Threading support
    depth: int
    reply_count: int
    
    # Moderation fields
    is_flagged: bool
    flag_count: int
    moderator_reviewed: bool
    is_deleted: bool
    
    # Author information (from relationship)
    author_username: Optional[str] = None
    author_reputation: Optional[float] = None
    
    # User's vote on this comment (if authenticated)
    user_vote: Optional[VoteType] = None
    
    # Nested replies (for threaded display)
    replies: Optional[List["CommentResponse"]] = None


class VoteRequest(BaseSchema):
    """Schema for voting on discussions or comments."""
    
    vote_type: VoteType = Field(..., description="Type of vote (upvote/downvote)")


class VoteResponse(BaseSchema):
    """Schema for vote responses."""
    
    success: bool
    new_vote: Optional[VoteType] = None  # None if vote was removed
    upvotes: int
    downvotes: int


class DiscussionFlag(BaseSchema):
    """Schema for flagging inappropriate discussions."""
    
    reason: str = Field(..., max_length=255, description="Reason for flagging")
    details: Optional[str] = Field(None, max_length=1000, description="Additional details")


class CommentFlag(BaseSchema):
    """Schema for flagging inappropriate comments."""
    
    reason: str = Field(..., max_length=255, description="Reason for flagging")
    details: Optional[str] = Field(None, max_length=1000, description="Additional details")


class DiscussionStats(BaseSchema):
    """Schema for discussion statistics."""
    
    total_discussions: int
    discussions_by_type: dict
    total_comments: int
    total_participants: int
    most_active_discussions: List[dict]
    recent_activity: List[dict]


class DiscussionList(BaseSchema):
    """Schema for listing discussions with pagination."""
    
    discussions: List[DiscussionResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class DiscussionSearch(BaseSchema):
    """Schema for searching discussions."""
    
    query: Optional[str] = Field(None, description="Search query")
    discussion_type: Optional[DiscussionType] = Field(None, description="Filter by discussion type")
    status: Optional[DiscussionStatus] = Field(None, description="Filter by status")
    author_id: Optional[str] = Field(None, description="Filter by author")
    is_pinned: Optional[bool] = Field(None, description="Filter pinned discussions")
    sort_by: str = Field("last_activity_at", description="Sort field")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Page size")


# Enable forward references for recursive CommentResponse
CommentResponse.model_rebuild()