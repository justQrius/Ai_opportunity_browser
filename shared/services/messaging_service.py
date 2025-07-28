"""Messaging service for user-to-user communication and collaboration tracking.

Supports Requirements 9.1-9.2 (Marketplace and Networking Features):
- User-to-user communication system
- Collaboration tracking and management
- Message threading and conversation management
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, text
from sqlalchemy.orm import selectinload, joinedload

from shared.models.message import (
    Message, MessageType, MessageStatus,
    Conversation, Collaboration, CollaborationStatus,
    CollaborationInvitation, MessageReaction
)
from shared.models.user import User
from shared.models.opportunity import Opportunity
from shared.schemas.message import (
    MessageCreate, MessageUpdate, MessageResponse,
    ConversationCreate, ConversationResponse,
    CollaborationCreate, CollaborationUpdate, CollaborationResponse,
    CollaborationInvitationCreate, CollaborationInvitationResponse,
    MessageStatistics, CollaborationStatistics
)
from shared.cache import cache_manager, CacheKeys
import structlog

logger = structlog.get_logger(__name__)


class MessagingService:
    """Service for managing user messages and conversations."""
    
    async def send_message(
        self,
        db: AsyncSession,
        sender_id: str,
        message_data: MessageCreate
    ) -> MessageResponse:
        """Send a message to another user.
        
        Args:
            db: Database session
            sender_id: ID of the message sender
            message_data: Message creation data
            
        Returns:
            Created message response
        """
        # Validate recipient exists
        recipient_query = select(User).where(User.id == message_data.recipient_id)
        recipient_result = await db.execute(recipient_query)
        recipient = recipient_result.scalar_one_or_none()
        
        if not recipient:
            raise ValueError(f"Recipient with ID {message_data.recipient_id} not found")
        
        if not recipient.is_active:
            raise ValueError("Cannot send message to inactive user")
        
        # Create conversation if needed
        conversation_id = await self._get_or_create_conversation(
            db, [sender_id, message_data.recipient_id], 
            message_data.opportunity_id, message_data.collaboration_id
        )
        
        # Create message
        message = Message(
            sender_id=sender_id,
            recipient_id=message_data.recipient_id,
            subject=message_data.subject,
            content=message_data.content,
            message_type=message_data.message_type,
            conversation_id=conversation_id,
            reply_to_id=message_data.reply_to_id,
            opportunity_id=message_data.opportunity_id,
            collaboration_id=message_data.collaboration_id,
            attachments=message_data.attachments,
            metadata=message_data.metadata
        )
        
        db.add(message)
        await db.flush()
        
        # Update conversation
        await self._update_conversation_stats(db, conversation_id)
        
        # Clear relevant caches
        await self._clear_message_caches(sender_id, message_data.recipient_id)
        
        await db.commit()
        
        # Load message with relationships for response
        message_query = select(Message).options(
            selectinload(Message.sender),
            selectinload(Message.recipient)
        ).where(Message.id == message.id)
        
        result = await db.execute(message_query)
        created_message = result.scalar_one()
        
        logger.info(
            "Message sent",
            message_id=message.id,
            sender_id=sender_id,
            recipient_id=message_data.recipient_id,
            message_type=message_data.message_type
        )
        
        return await self._message_to_response(created_message)
    
    async def get_messages(
        self,
        db: AsyncSession,
        user_id: str,
        conversation_id: Optional[str] = None,
        message_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[MessageResponse], int]:
        """Get messages for a user with filtering and pagination.
        
        Args:
            db: Database session
            user_id: ID of the user
            conversation_id: Optional conversation filter
            message_type: Optional message type filter
            status: Optional status filter
            page: Page number
            per_page: Items per page
            
        Returns:
            Tuple of (messages, total_count)
        """
        # Build query conditions
        conditions = [
            or_(Message.sender_id == user_id, Message.recipient_id == user_id)
        ]
        
        if conversation_id:
            conditions.append(Message.conversation_id == conversation_id)
        
        if message_type:
            conditions.append(Message.message_type == message_type)
        
        if status:
            conditions.append(Message.status == status)
        
        # Get total count
        count_query = select(func.count(Message.id)).where(and_(*conditions))
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Get messages with pagination
        offset = (page - 1) * per_page
        messages_query = select(Message).options(
            selectinload(Message.sender),
            selectinload(Message.recipient),
            selectinload(Message.opportunity),
            selectinload(Message.collaboration)
        ).where(
            and_(*conditions)
        ).order_by(desc(Message.created_at)).offset(offset).limit(per_page)
        
        result = await db.execute(messages_query)
        messages = result.scalars().all()
        
        # Convert to response objects
        message_responses = []
        for message in messages:
            response = await self._message_to_response(message)
            message_responses.append(response)
        
        return message_responses, total
    
    async def mark_message_as_read(
        self,
        db: AsyncSession,
        message_id: str,
        user_id: str
    ) -> MessageResponse:
        """Mark a message as read.
        
        Args:
            db: Database session
            message_id: ID of the message
            user_id: ID of the user marking as read
            
        Returns:
            Updated message response
        """
        # Get message
        message_query = select(Message).options(
            selectinload(Message.sender),
            selectinload(Message.recipient)
        ).where(Message.id == message_id)
        
        result = await db.execute(message_query)
        message = result.scalar_one_or_none()
        
        if not message:
            raise ValueError(f"Message with ID {message_id} not found")
        
        # Verify user is recipient
        if message.recipient_id != user_id:
            raise ValueError("Only message recipient can mark message as read")
        
        # Update status
        if message.status != MessageStatus.READ:
            message.status = MessageStatus.READ
            message.read_at = datetime.utcnow()
            
            await db.commit()
            
            # Clear caches
            await self._clear_message_caches(message.sender_id, user_id)
        
        return await self._message_to_response(message)
    
    async def get_conversations(
        self,
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[ConversationResponse], int]:
        """Get conversations for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            page: Page number
            per_page: Items per page
            
        Returns:
            Tuple of (conversations, total_count)
        """
        # Get conversations where user is participant
        conditions = [
            func.json_array_length(Conversation.participant_ids) > 0,
            text(f"JSON_CONTAINS(participant_ids, '\"{user_id}\"')")
        ]
        
        # Get total count
        count_query = select(func.count(Conversation.id)).where(and_(*conditions))
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Get conversations with pagination
        offset = (page - 1) * per_page
        conversations_query = select(Conversation).options(
            selectinload(Conversation.opportunity),
            selectinload(Conversation.collaboration)
        ).where(
            and_(*conditions)
        ).order_by(desc(Conversation.last_message_at)).offset(offset).limit(per_page)
        
        result = await db.execute(conversations_query)
        conversations = result.scalars().all()
        
        # Convert to response objects
        conversation_responses = []
        for conversation in conversations:
            response = await self._conversation_to_response(db, conversation, user_id)
            conversation_responses.append(response)
        
        return conversation_responses, total
    
    async def _get_or_create_conversation(
        self,
        db: AsyncSession,
        participant_ids: List[str],
        opportunity_id: Optional[str] = None,
        collaboration_id: Optional[str] = None
    ) -> str:
        """Get existing conversation or create new one."""
        
        # Sort participant IDs for consistent lookup
        sorted_participants = sorted(participant_ids)
        
        # Try to find existing conversation
        existing_query = select(Conversation).where(
            Conversation.participant_ids == json.dumps(sorted_participants)
        )
        
        if opportunity_id:
            existing_query = existing_query.where(Conversation.opportunity_id == opportunity_id)
        if collaboration_id:
            existing_query = existing_query.where(Conversation.collaboration_id == collaboration_id)
        
        result = await db.execute(existing_query)
        existing = result.scalar_one_or_none()
        
        if existing:
            return existing.id
        
        # Create new conversation
        conversation = Conversation(
            participant_ids=sorted_participants,
            opportunity_id=opportunity_id,
            collaboration_id=collaboration_id
        )
        
        db.add(conversation)
        await db.flush()
        
        return conversation.id
    
    async def _update_conversation_stats(
        self,
        db: AsyncSession,
        conversation_id: str
    ) -> None:
        """Update conversation statistics."""
        
        # Get message count
        count_query = select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
        count_result = await db.execute(count_query)
        message_count = count_result.scalar()
        
        # Get last message time
        last_message_query = select(func.max(Message.created_at)).where(
            Message.conversation_id == conversation_id
        )
        last_message_result = await db.execute(last_message_query)
        last_message_at = last_message_result.scalar()
        
        # Update conversation
        conversation_query = select(Conversation).where(Conversation.id == conversation_id)
        result = await db.execute(conversation_query)
        conversation = result.scalar_one()
        
        conversation.message_count = message_count
        if last_message_at:
            conversation.last_message_at = last_message_at
    
    async def _message_to_response(self, message: Message) -> MessageResponse:
        """Convert Message model to response schema."""
        
        # Get reply count
        reply_count = 0  # Could be calculated if needed
        
        return MessageResponse(
            id=message.id,
            sender_id=message.sender_id,
            recipient_id=message.recipient_id,
            subject=message.subject,
            content=message.content,
            message_type=message.message_type,
            status=message.status,
            read_at=message.read_at,
            conversation_id=message.conversation_id,
            reply_to_id=message.reply_to_id,
            opportunity_id=message.opportunity_id,
            collaboration_id=message.collaboration_id,
            attachments=message.attachments,
            metadata=message.metadata,
            created_at=message.created_at,
            updated_at=message.updated_at,
            sender_username=message.sender.username if message.sender else None,
            recipient_username=message.recipient.username if message.recipient else None,
            reply_count=reply_count
        )
    
    async def _conversation_to_response(
        self,
        db: AsyncSession,
        conversation: Conversation,
        user_id: str
    ) -> ConversationResponse:
        """Convert Conversation model to response schema."""
        
        # Get participant usernames
        participant_usernames = []
        if conversation.participant_ids:
            users_query = select(User.username).where(
                User.id.in_(conversation.participant_ids)
            )
            result = await db.execute(users_query)
            participant_usernames = [row[0] for row in result.fetchall()]
        
        # Get last message preview
        last_message_query = select(Message.content).where(
            Message.conversation_id == conversation.id
        ).order_by(desc(Message.created_at)).limit(1)
        
        result = await db.execute(last_message_query)
        last_message = result.scalar_one_or_none()
        last_message_preview = None
        if last_message:
            # Truncate for preview
            last_message_preview = last_message[:100] + "..." if len(last_message) > 100 else last_message
        
        # Get unread count for this user
        unread_query = select(func.count(Message.id)).where(
            and_(
                Message.conversation_id == conversation.id,
                Message.recipient_id == user_id,
                Message.status != MessageStatus.READ
            )
        )
        unread_result = await db.execute(unread_query)
        unread_count = unread_result.scalar()
        
        return ConversationResponse(
            id=conversation.id,
            participant_ids=conversation.participant_ids,
            title=conversation.title,
            last_message_at=conversation.last_message_at,
            message_count=conversation.message_count,
            opportunity_id=conversation.opportunity_id,
            collaboration_id=conversation.collaboration_id,
            is_archived=conversation.is_archived,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            participant_usernames=participant_usernames,
            last_message_preview=last_message_preview,
            unread_count=unread_count
        )
    
    async def _clear_message_caches(self, user1_id: str, user2_id: str) -> None:
        """Clear message-related caches for users."""
        if cache_manager is not None:
            try:
                # Clear conversation caches
                cache_keys = [
                    CacheKeys.format_key(CacheKeys.USER_CONVERSATIONS, user_id=user1_id),
                    CacheKeys.format_key(CacheKeys.USER_CONVERSATIONS, user_id=user2_id),
                    CacheKeys.format_key(CacheKeys.USER_MESSAGES, user_id=user1_id),
                    CacheKeys.format_key(CacheKeys.USER_MESSAGES, user_id=user2_id)
                ]
                
                for key in cache_keys:
                    await cache_manager.delete(key)
                    
            except Exception as e:
                logger.warning("Failed to clear message caches", error=str(e))


class CollaborationService:
    """Service for managing collaborations and tracking outcomes."""
    
    async def create_collaboration(
        self,
        db: AsyncSession,
        initiator_id: str,
        collaboration_data: CollaborationCreate
    ) -> CollaborationResponse:
        """Create a new collaboration.
        
        Args:
            db: Database session
            initiator_id: ID of the collaboration initiator
            collaboration_data: Collaboration creation data
            
        Returns:
            Created collaboration response
        """
        # Validate participants exist
        all_participants = [initiator_id] + collaboration_data.participant_ids
        unique_participants = list(set(all_participants))
        
        users_query = select(User).where(User.id.in_(unique_participants))
        result = await db.execute(users_query)
        users = result.scalars().all()
        
        if len(users) != len(unique_participants):
            raise ValueError("One or more participants not found")
        
        # Validate opportunity if provided
        if collaboration_data.opportunity_id:
            opp_query = select(Opportunity).where(Opportunity.id == collaboration_data.opportunity_id)
            opp_result = await db.execute(opp_query)
            opportunity = opp_result.scalar_one_or_none()
            if not opportunity:
                raise ValueError(f"Opportunity with ID {collaboration_data.opportunity_id} not found")
        
        # Create collaboration
        collaboration = Collaboration(
            title=collaboration_data.title,
            description=collaboration_data.description,
            initiator_id=initiator_id,
            participant_ids=unique_participants,
            opportunity_id=collaboration_data.opportunity_id,
            goals=collaboration_data.goals,
            deadline=collaboration_data.deadline,
            is_public=collaboration_data.is_public
        )
        
        db.add(collaboration)
        await db.flush()
        
        # Send invitations to other participants
        for participant_id in collaboration_data.participant_ids:
            if participant_id != initiator_id:
                invitation = CollaborationInvitation(
                    collaboration_id=collaboration.id,
                    inviter_id=initiator_id,
                    invitee_id=participant_id,
                    message=f"You've been invited to collaborate on: {collaboration.title}",
                    expires_at=datetime.utcnow() + timedelta(days=7)  # 7-day expiration
                )
                db.add(invitation)
        
        await db.commit()
        
        logger.info(
            "Collaboration created",
            collaboration_id=collaboration.id,
            initiator_id=initiator_id,
            participant_count=len(unique_participants)
        )
        
        # Load with relationships for response
        collab_query = select(Collaboration).options(
            selectinload(Collaboration.initiator),
            selectinload(Collaboration.opportunity)
        ).where(Collaboration.id == collaboration.id)
        
        result = await db.execute(collab_query)
        created_collaboration = result.scalar_one()
        
        return await self._collaboration_to_response(db, created_collaboration)
    
    async def update_collaboration(
        self,
        db: AsyncSession,
        collaboration_id: str,
        user_id: str,
        update_data: CollaborationUpdate
    ) -> CollaborationResponse:
        """Update a collaboration.
        
        Args:
            db: Database session
            collaboration_id: ID of the collaboration
            user_id: ID of the user making the update
            update_data: Update data
            
        Returns:
            Updated collaboration response
        """
        # Get collaboration
        collab_query = select(Collaboration).where(Collaboration.id == collaboration_id)
        result = await db.execute(collab_query)
        collaboration = result.scalar_one_or_none()
        
        if not collaboration:
            raise ValueError(f"Collaboration with ID {collaboration_id} not found")
        
        # Verify user is participant
        if user_id not in collaboration.participant_ids:
            raise ValueError("Only collaboration participants can update collaboration")
        
        # Update fields
        if update_data.title is not None:
            collaboration.title = update_data.title
        if update_data.description is not None:
            collaboration.description = update_data.description
        if update_data.status is not None:
            old_status = collaboration.status
            collaboration.status = update_data.status
            
            # Update timestamps based on status changes
            if old_status != update_data.status:
                if update_data.status == CollaborationStatus.IN_PROGRESS and not collaboration.started_at:
                    collaboration.started_at = datetime.utcnow()
                elif update_data.status == CollaborationStatus.COMPLETED and not collaboration.completed_at:
                    collaboration.completed_at = datetime.utcnow()
        
        if update_data.goals is not None:
            collaboration.goals = update_data.goals
        if update_data.milestones is not None:
            collaboration.milestones = update_data.milestones
        if update_data.resources is not None:
            collaboration.resources = update_data.resources
        if update_data.deadline is not None:
            collaboration.deadline = update_data.deadline
        if update_data.outcome_status is not None:
            collaboration.outcome_status = update_data.outcome_status
        if update_data.outcome_description is not None:
            collaboration.outcome_description = update_data.outcome_description
        if update_data.outcome_metrics is not None:
            collaboration.outcome_metrics = update_data.outcome_metrics
        
        await db.commit()
        
        logger.info(
            "Collaboration updated",
            collaboration_id=collaboration_id,
            user_id=user_id,
            status=collaboration.status
        )
        
        # Load with relationships for response
        collab_query = select(Collaboration).options(
            selectinload(Collaboration.initiator),
            selectinload(Collaboration.opportunity)
        ).where(Collaboration.id == collaboration_id)
        
        result = await db.execute(collab_query)
        updated_collaboration = result.scalar_one()
        
        return await self._collaboration_to_response(db, updated_collaboration)
    
    async def get_user_collaborations(
        self,
        db: AsyncSession,
        user_id: str,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[CollaborationResponse], int]:
        """Get collaborations for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            status: Optional status filter
            page: Page number
            per_page: Items per page
            
        Returns:
            Tuple of (collaborations, total_count)
        """
        # Build conditions
        conditions = [
            text(f"JSON_CONTAINS(participant_ids, '\"{user_id}\"')")
        ]
        
        if status:
            conditions.append(Collaboration.status == status)
        
        # Get total count
        count_query = select(func.count(Collaboration.id)).where(and_(*conditions))
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Get collaborations with pagination
        offset = (page - 1) * per_page
        collabs_query = select(Collaboration).options(
            selectinload(Collaboration.initiator),
            selectinload(Collaboration.opportunity)
        ).where(
            and_(*conditions)
        ).order_by(desc(Collaboration.created_at)).offset(offset).limit(per_page)
        
        result = await db.execute(collabs_query)
        collaborations = result.scalars().all()
        
        # Convert to response objects
        collaboration_responses = []
        for collaboration in collaborations:
            response = await self._collaboration_to_response(db, collaboration)
            collaboration_responses.append(response)
        
        return collaboration_responses, total
    
    async def _collaboration_to_response(
        self,
        db: AsyncSession,
        collaboration: Collaboration
    ) -> CollaborationResponse:
        """Convert Collaboration model to response schema."""
        
        # Get participant usernames
        participant_usernames = []
        if collaboration.participant_ids:
            users_query = select(User.username).where(
                User.id.in_(collaboration.participant_ids)
            )
            result = await db.execute(users_query)
            participant_usernames = [row[0] for row in result.fetchall()]
        
        # Calculate progress percentage
        progress_percentage = 0.0
        if collaboration.milestones:
            completed_milestones = sum(
                1 for milestone in collaboration.milestones 
                if milestone.get('status') == 'completed'
            )
            progress_percentage = (completed_milestones / len(collaboration.milestones)) * 100
        
        # Count active participants (those who have interacted recently)
        active_participants = len(collaboration.participant_ids)  # Simplified
        
        return CollaborationResponse(
            id=collaboration.id,
            title=collaboration.title,
            description=collaboration.description,
            status=collaboration.status,
            initiator_id=collaboration.initiator_id,
            participant_ids=collaboration.participant_ids,
            opportunity_id=collaboration.opportunity_id,
            proposed_at=collaboration.proposed_at,
            started_at=collaboration.started_at,
            completed_at=collaboration.completed_at,
            deadline=collaboration.deadline,
            goals=collaboration.goals,
            milestones=collaboration.milestones,
            resources=collaboration.resources,
            outcome_status=collaboration.outcome_status,
            outcome_description=collaboration.outcome_description,
            outcome_metrics=collaboration.outcome_metrics,
            is_public=collaboration.is_public,
            created_at=collaboration.created_at,
            updated_at=collaboration.updated_at,
            initiator_username=collaboration.initiator.username if collaboration.initiator else None,
            participant_usernames=participant_usernames,
            opportunity_title=collaboration.opportunity.title if collaboration.opportunity else None,
            progress_percentage=progress_percentage,
            active_participants=active_participants
        )