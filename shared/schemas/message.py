"""Pydantic schemas for messaging and collaboration features.

Supports Requirements 9.1-9.2 (Marketplace and Networking Features):
- Message request/response schemas
- Collaboration tracking schemas
- API validation and serialization
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from shared.models.message import MessageType, MessageStatus, CollaborationStatus


class MessageTypeEnum(str, Enum):
    """Message type enumeration for API."""
    DIRECT = "direct"
    COLLABORATION_REQUEST = "collaboration_request"
    COLLABORATION_RESPONSE = "collaboration_response"
    PROJECT_UPDATE = "project_update"
    SYSTEM = "system"


class MessageStatusEnum(str, Enum):
    """Message status enumeration for API."""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    ARCHIVED = "archived"


class CollaborationStatusEnum(str, Enum):
    """Collaboration status enumeration for API."""
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


# Message Schemas

class MessageCreate(BaseModel):
    """Schema for creating a new message."""
    recipient_id: str = Field(..., description="ID of the message recipient")
    subject: Optional[str] = Field(None, max_length=200, description="Message subject")
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    message_type: MessageTypeEnum = Field(MessageTypeEnum.DIRECT, description="Type of message")
    opportunity_id: Optional[str] = Field(None, description="Related opportunity ID")
    collaboration_id: Optional[str] = Field(None, description="Related collaboration ID")
    reply_to_id: Optional[str] = Field(None, description="ID of message being replied to")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="Message attachments")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional message metadata")


class MessageUpdate(BaseModel):
    """Schema for updating message status."""
    status: Optional[MessageStatusEnum] = Field(None, description="New message status")


class MessageResponse(BaseModel):
    """Schema for message response."""
    id: str
    sender_id: str
    recipient_id: str
    subject: Optional[str]
    content: str
    message_type: str
    status: str
    read_at: Optional[datetime]
    conversation_id: Optional[str]
    reply_to_id: Optional[str]
    opportunity_id: Optional[str]
    collaboration_id: Optional[str]
    attachments: Optional[List[Dict[str, Any]]]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    # Nested objects
    sender_username: Optional[str] = None
    recipient_username: Optional[str] = None
    reply_count: int = 0

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Schema for paginated message list."""
    messages: List[MessageResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


# Conversation Schemas

class ConversationCreate(BaseModel):
    """Schema for creating a conversation."""
    participant_ids: List[str] = Field(..., min_items=2, description="List of participant user IDs")
    title: Optional[str] = Field(None, max_length=200, description="Conversation title")
    opportunity_id: Optional[str] = Field(None, description="Related opportunity ID")
    collaboration_id: Optional[str] = Field(None, description="Related collaboration ID")


class ConversationResponse(BaseModel):
    """Schema for conversation response."""
    id: str
    participant_ids: List[str]
    title: Optional[str]
    last_message_at: datetime
    message_count: int
    opportunity_id: Optional[str]
    collaboration_id: Optional[str]
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    
    # Additional fields
    participant_usernames: List[str] = []
    last_message_preview: Optional[str] = None
    unread_count: int = 0

    class Config:
        from_attributes = True


# Collaboration Schemas

class CollaborationCreate(BaseModel):
    """Schema for creating a collaboration."""
    title: str = Field(..., min_length=1, max_length=200, description="Collaboration title")
    description: Optional[str] = Field(None, max_length=5000, description="Collaboration description")
    participant_ids: List[str] = Field(..., min_items=1, description="List of participant user IDs")
    opportunity_id: Optional[str] = Field(None, description="Related opportunity ID")
    goals: Optional[List[str]] = Field(None, description="Collaboration goals")
    deadline: Optional[datetime] = Field(None, description="Collaboration deadline")
    is_public: bool = Field(False, description="Whether collaboration is publicly visible")


class CollaborationUpdate(BaseModel):
    """Schema for updating a collaboration."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[CollaborationStatusEnum] = None
    goals: Optional[List[str]] = None
    milestones: Optional[List[Dict[str, Any]]] = None
    resources: Optional[List[Dict[str, Any]]] = None
    deadline: Optional[datetime] = None
    outcome_status: Optional[str] = None
    outcome_description: Optional[str] = None
    outcome_metrics: Optional[Dict[str, Any]] = None


class MilestoneCreate(BaseModel):
    """Schema for creating a milestone."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None  # User ID
    priority: str = Field("medium", pattern="^(low|medium|high|critical)$")


class CollaborationResponse(BaseModel):
    """Schema for collaboration response."""
    id: str
    title: str
    description: Optional[str]
    status: str
    initiator_id: str
    participant_ids: List[str]
    opportunity_id: Optional[str]
    proposed_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    deadline: Optional[datetime]
    goals: Optional[List[str]]
    milestones: Optional[List[Dict[str, Any]]]
    resources: Optional[List[Dict[str, Any]]]
    outcome_status: Optional[str]
    outcome_description: Optional[str]
    outcome_metrics: Optional[Dict[str, Any]]
    is_public: bool
    created_at: datetime
    updated_at: datetime
    
    # Additional fields
    initiator_username: Optional[str] = None
    participant_usernames: List[str] = []
    opportunity_title: Optional[str] = None
    progress_percentage: float = 0.0
    active_participants: int = 0

    class Config:
        from_attributes = True


# Collaboration Invitation Schemas

class CollaborationInvitationCreate(BaseModel):
    """Schema for creating a collaboration invitation."""
    collaboration_id: str = Field(..., description="Collaboration ID")
    invitee_id: str = Field(..., description="User ID of invitee")
    message: Optional[str] = Field(None, max_length=1000, description="Invitation message")
    proposed_role: Optional[str] = Field(None, max_length=100, description="Proposed role")
    proposed_contribution: Optional[str] = Field(None, max_length=1000, description="Proposed contribution")
    expires_at: Optional[datetime] = Field(None, description="Invitation expiration")


class CollaborationInvitationResponse(BaseModel):
    """Schema for responding to a collaboration invitation."""
    status: str = Field(..., pattern="^(accepted|declined)$", description="Response status")
    response_message: Optional[str] = Field(None, max_length=1000, description="Response message")


class CollaborationInvitationDetail(BaseModel):
    """Schema for collaboration invitation details."""
    id: str
    collaboration_id: str
    inviter_id: str
    invitee_id: str
    message: Optional[str]
    proposed_role: Optional[str]
    proposed_contribution: Optional[str]
    status: str
    responded_at: Optional[datetime]
    response_message: Optional[str]
    expires_at: Optional[datetime]
    created_at: datetime
    
    # Additional fields
    inviter_username: Optional[str] = None
    invitee_username: Optional[str] = None
    collaboration_title: Optional[str] = None
    is_expired: bool = False

    class Config:
        from_attributes = True


# Message Reaction Schemas

class MessageReactionCreate(BaseModel):
    """Schema for creating a message reaction."""
    reaction_type: str = Field(..., pattern="^(like|helpful|agree|disagree|celebrate|concern)$")


class MessageReactionResponse(BaseModel):
    """Schema for message reaction response."""
    id: str
    message_id: str
    user_id: str
    reaction_type: str
    created_at: datetime
    
    # Additional fields
    username: Optional[str] = None

    class Config:
        from_attributes = True


# Statistics and Analytics Schemas

class MessageStatistics(BaseModel):
    """Schema for message statistics."""
    total_messages: int
    unread_messages: int
    conversations: int
    active_collaborations: int
    completed_collaborations: int
    response_rate: float
    average_response_time_hours: float


class CollaborationStatistics(BaseModel):
    """Schema for collaboration statistics."""
    total_collaborations: int
    active_collaborations: int
    completed_collaborations: int
    success_rate: float
    average_duration_days: float
    most_common_outcomes: List[Dict[str, Any]]


# Search and Filter Schemas

class MessageSearchRequest(BaseModel):
    """Schema for message search requests."""
    query: Optional[str] = Field(None, min_length=1, max_length=200)
    message_type: Optional[MessageTypeEnum] = None
    status: Optional[MessageStatusEnum] = None
    sender_id: Optional[str] = None
    recipient_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    collaboration_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


class CollaborationSearchRequest(BaseModel):
    """Schema for collaboration search requests."""
    query: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[CollaborationStatusEnum] = None
    participant_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    is_public: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)