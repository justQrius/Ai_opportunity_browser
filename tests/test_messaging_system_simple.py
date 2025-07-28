"""Simple tests for the messaging system implementation.

Tests Requirements 9.1-9.2 (Marketplace and Networking Features):
- User-to-user communication
- Collaboration tracking
"""

import pytest
from shared.models.message import MessageType, MessageStatus, CollaborationStatus
from shared.schemas.message import MessageCreate, CollaborationCreate
from shared.services.messaging_service import MessagingService, CollaborationService


class TestMessagingSystemComponents:
    """Test messaging system components without database dependencies."""
    
    def test_messaging_service_exists(self):
        """Test that MessagingService can be instantiated."""
        service = MessagingService()
        assert service is not None
        assert hasattr(service, 'send_message')
        assert hasattr(service, 'get_messages')
        assert hasattr(service, 'mark_message_as_read')
    
    def test_collaboration_service_exists(self):
        """Test that CollaborationService can be instantiated."""
        service = CollaborationService()
        assert service is not None
        assert hasattr(service, 'create_collaboration')
        assert hasattr(service, 'update_collaboration')
        assert hasattr(service, 'get_user_collaborations')
    
    def test_message_enums(self):
        """Test message enums are properly defined."""
        # Test MessageType enum
        assert MessageType.DIRECT == "direct"
        assert MessageType.COLLABORATION_REQUEST == "collaboration_request"
        assert MessageType.COLLABORATION_RESPONSE == "collaboration_response"
        assert MessageType.PROJECT_UPDATE == "project_update"
        assert MessageType.SYSTEM == "system"
        
        # Test MessageStatus enum
        assert MessageStatus.SENT == "sent"
        assert MessageStatus.DELIVERED == "delivered"
        assert MessageStatus.READ == "read"
        assert MessageStatus.ARCHIVED == "archived"
        
        # Test CollaborationStatus enum
        assert CollaborationStatus.PROPOSED == "proposed"
        assert CollaborationStatus.ACCEPTED == "accepted"
        assert CollaborationStatus.IN_PROGRESS == "in_progress"
        assert CollaborationStatus.COMPLETED == "completed"
        assert CollaborationStatus.CANCELLED == "cancelled"
        assert CollaborationStatus.ON_HOLD == "on_hold"
    
    def test_message_create_schema(self):
        """Test MessageCreate schema validation."""
        message_data = MessageCreate(
            recipient_id="user2",
            content="Test message",
            message_type=MessageType.DIRECT
        )
        
        assert message_data.recipient_id == "user2"
        assert message_data.content == "Test message"
        assert message_data.message_type == MessageType.DIRECT
        assert message_data.subject is None
        assert message_data.opportunity_id is None
        assert message_data.collaboration_id is None
    
    def test_message_create_schema_with_optional_fields(self):
        """Test MessageCreate schema with optional fields."""
        message_data = MessageCreate(
            recipient_id="user2",
            subject="Test Subject",
            content="Test message with subject",
            message_type=MessageType.COLLABORATION_REQUEST,
            opportunity_id="opp123",
            collaboration_id="collab456",
            reply_to_id="msg789"
        )
        
        assert message_data.recipient_id == "user2"
        assert message_data.subject == "Test Subject"
        assert message_data.content == "Test message with subject"
        assert message_data.message_type == MessageType.COLLABORATION_REQUEST
        assert message_data.opportunity_id == "opp123"
        assert message_data.collaboration_id == "collab456"
        assert message_data.reply_to_id == "msg789"
    
    def test_collaboration_create_schema(self):
        """Test CollaborationCreate schema validation."""
        collaboration_data = CollaborationCreate(
            title="Test Collaboration",
            participant_ids=["user2", "user3"],
            is_public=False
        )
        
        assert collaboration_data.title == "Test Collaboration"
        assert collaboration_data.participant_ids == ["user2", "user3"]
        assert collaboration_data.is_public == False
        assert collaboration_data.description is None
        assert collaboration_data.opportunity_id is None
        assert collaboration_data.goals is None
        assert collaboration_data.deadline is None
    
    def test_collaboration_create_schema_with_optional_fields(self):
        """Test CollaborationCreate schema with optional fields."""
        from datetime import datetime, timedelta
        
        deadline = datetime.utcnow() + timedelta(days=30)
        collaboration_data = CollaborationCreate(
            title="Advanced Collaboration",
            description="A detailed collaboration project",
            participant_ids=["user2", "user3", "user4"],
            opportunity_id="opp123",
            goals=["Goal 1", "Goal 2", "Goal 3"],
            deadline=deadline,
            is_public=True
        )
        
        assert collaboration_data.title == "Advanced Collaboration"
        assert collaboration_data.description == "A detailed collaboration project"
        assert collaboration_data.participant_ids == ["user2", "user3", "user4"]
        assert collaboration_data.opportunity_id == "opp123"
        assert collaboration_data.goals == ["Goal 1", "Goal 2", "Goal 3"]
        assert collaboration_data.deadline == deadline
        assert collaboration_data.is_public == True
    
    def test_message_create_validation_errors(self):
        """Test MessageCreate schema validation errors."""
        # Test missing required fields
        with pytest.raises(ValueError):
            MessageCreate()  # Missing recipient_id and content
        
        # Test empty content
        with pytest.raises(ValueError):
            MessageCreate(
                recipient_id="user2",
                content=""  # Empty content should fail
            )
    
    def test_collaboration_create_validation_errors(self):
        """Test CollaborationCreate schema validation errors."""
        # Test missing required fields
        with pytest.raises(ValueError):
            CollaborationCreate()  # Missing title and participant_ids
        
        # Test empty participant list
        with pytest.raises(ValueError):
            CollaborationCreate(
                title="Test",
                participant_ids=[]  # Empty list should fail
            )


class TestMessagingSystemIntegration:
    """Test messaging system integration points."""
    
    def test_messaging_service_methods_exist(self):
        """Test that all required messaging service methods exist."""
        service = MessagingService()
        
        # Core messaging methods
        assert callable(getattr(service, 'send_message', None))
        assert callable(getattr(service, 'get_messages', None))
        assert callable(getattr(service, 'mark_message_as_read', None))
        assert callable(getattr(service, 'get_conversations', None))
        
        # Private helper methods
        assert callable(getattr(service, '_get_or_create_conversation', None))
        assert callable(getattr(service, '_update_conversation_stats', None))
        assert callable(getattr(service, '_message_to_response', None))
        assert callable(getattr(service, '_conversation_to_response', None))
        assert callable(getattr(service, '_clear_message_caches', None))
    
    def test_collaboration_service_methods_exist(self):
        """Test that all required collaboration service methods exist."""
        service = CollaborationService()
        
        # Core collaboration methods
        assert callable(getattr(service, 'create_collaboration', None))
        assert callable(getattr(service, 'update_collaboration', None))
        assert callable(getattr(service, 'get_user_collaborations', None))
        
        # Private helper methods
        assert callable(getattr(service, '_collaboration_to_response', None))
    
    def test_api_router_imports(self):
        """Test that API router can be imported successfully."""
        try:
            from api.routers.messaging import router
            assert router is not None
            assert hasattr(router, 'prefix')
            assert router.prefix == "/messaging"
        except ImportError as e:
            pytest.fail(f"Failed to import messaging router: {e}")
    
    def test_cache_keys_exist(self):
        """Test that messaging cache keys are defined."""
        from shared.cache import CacheKeys
        
        # Check that messaging-related cache keys exist
        assert hasattr(CacheKeys, 'USER_MESSAGES')
        assert hasattr(CacheKeys, 'USER_CONVERSATIONS')
        assert hasattr(CacheKeys, 'MESSAGE_THREAD')
        assert hasattr(CacheKeys, 'COLLABORATION_DETAILS')
        assert hasattr(CacheKeys, 'USER_COLLABORATIONS')
        
        # Test cache key formatting
        user_messages_key = CacheKeys.format_key(CacheKeys.USER_MESSAGES, user_id="test123", page=1)
        assert "test123" in user_messages_key
        assert "page" in user_messages_key


if __name__ == "__main__":
    pytest.main([__file__])