"""
Tests for the Event Bus System.

This module contains comprehensive tests for the event bus system including
event publishing, subscription, replay, and handler functionality.
"""

import asyncio
import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from shared.event_bus import (
    EventBus, Event, EventHandler, EventType,
    get_event_bus, publish_event, subscribe_to_events
)
from shared.event_config import (
    EventBusConfig, EventBusManager, get_event_bus_manager,
    publish_opportunity_created, publish_user_registered,
    publish_agent_task_completed, publish_system_health_check,
    publish_signal_detected
)
from shared.event_handlers import (
    OpportunityEventHandler, UserEventHandler, AgentEventHandler,
    SystemEventHandler, MarketSignalEventHandler
)


class TestEventHandler(EventHandler):
    """Test event handler for testing purposes."""
    
    def __init__(self, handler_id: str = "test_handler"):
        super().__init__(handler_id)
        self.handled_events: List[Event] = []
        self.errors: List[Exception] = []
    
    async def handle(self, event: Event) -> None:
        """Handle test events."""
        self.handled_events.append(event)
    
    async def on_error(self, event: Event, error: Exception) -> None:
        """Handle test errors."""
        self.errors.append(error)
        await super().on_error(event, error)


@pytest.fixture
async def redis_mock():
    """Mock Redis client for testing."""
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.publish.return_value = 1
    mock_redis.setex.return_value = True
    mock_redis.zadd.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.zrangebyscore.return_value = ["event1", "event2"]
    mock_redis.get.return_value = json.dumps({
        "id": "event1",
        "event_type": "test.event",
        "payload": {"test": "data"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "test",
        "correlation_id": None,
        "metadata": {}
    })
    mock_redis.zcard.return_value = 5
    mock_redis.close.return_value = None
    
    # Mock pubsub
    mock_pubsub = AsyncMock()
    mock_pubsub.subscribe.return_value = None
    mock_pubsub.listen.return_value = iter([
        {"type": "subscribe", "channel": "events:test.event"},
        {
            "type": "message",
            "channel": "events:test.event",
            "data": json.dumps({
                "id": "event1",
                "event_type": "test.event",
                "payload": {"test": "data"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "test",
                "correlation_id": None,
                "metadata": {}
            })
        }
    ])
    mock_pubsub.close.return_value = None
    mock_redis.pubsub.return_value = mock_pubsub
    
    return mock_redis


@pytest.fixture
async def event_bus(redis_mock):
    """Create event bus instance for testing."""
    with patch('redis.asyncio.from_url', return_value=redis_mock):
        bus = EventBus(redis_url="redis://localhost:6379/0")
        await bus.initialize()
        yield bus
        await bus.shutdown()


@pytest.fixture
def sample_event():
    """Create a sample event for testing."""
    return Event(
        id="test-event-1",
        event_type=EventType.OPPORTUNITY_CREATED,
        payload={"opportunity_id": "opp-123", "title": "Test Opportunity"},
        timestamp=datetime.now(timezone.utc),
        source="test_service",
        correlation_id="corr-123",
        metadata={"test": True}
    )


class TestEvent:
    """Test Event class functionality."""
    
    def test_event_creation(self, sample_event):
        """Test event creation and properties."""
        assert sample_event.id == "test-event-1"
        assert sample_event.event_type == EventType.OPPORTUNITY_CREATED
        assert sample_event.payload["opportunity_id"] == "opp-123"
        assert sample_event.source == "test_service"
        assert sample_event.correlation_id == "corr-123"
        assert sample_event.metadata["test"] is True
    
    def test_event_to_dict(self, sample_event):
        """Test event serialization to dictionary."""
        event_dict = sample_event.to_dict()
        
        assert event_dict["id"] == "test-event-1"
        assert event_dict["event_type"] == EventType.OPPORTUNITY_CREATED
        assert event_dict["payload"]["opportunity_id"] == "opp-123"
        assert event_dict["source"] == "test_service"
        assert "timestamp" in event_dict
        assert isinstance(event_dict["timestamp"], str)
    
    def test_event_from_dict(self, sample_event):
        """Test event deserialization from dictionary."""
        event_dict = sample_event.to_dict()
        reconstructed_event = Event.from_dict(event_dict)
        
        assert reconstructed_event.id == sample_event.id
        assert reconstructed_event.event_type == sample_event.event_type
        assert reconstructed_event.payload == sample_event.payload
        assert reconstructed_event.source == sample_event.source
        assert reconstructed_event.correlation_id == sample_event.correlation_id


class TestEventBus:
    """Test EventBus functionality."""
    
    @pytest.mark.asyncio
    async def test_event_bus_initialization(self, redis_mock):
        """Test event bus initialization."""
        with patch('redis.asyncio.from_url', return_value=redis_mock):
            bus = EventBus()
            await bus.initialize()
            
            assert bus._redis_client is not None
            redis_mock.ping.assert_called_once()
            
            await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_publish_event(self, event_bus, redis_mock):
        """Test event publishing."""
        event_id = await event_bus.publish_event(
            event_type=EventType.OPPORTUNITY_CREATED,
            payload={"opportunity_id": "opp-123", "title": "Test Opportunity"},
            source="test_service",
            correlation_id="corr-123",
            metadata={"test": True}
        )
        
        assert event_id is not None
        assert isinstance(event_id, str)
        
        # Verify Redis calls
        redis_mock.publish.assert_called_once()
        redis_mock.setex.assert_called_once()
        redis_mock.zadd.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_subscribe_to_events(self, event_bus):
        """Test event subscription."""
        handler = TestEventHandler()
        
        await event_bus.subscribe_to_events(
            [EventType.OPPORTUNITY_CREATED],
            handler
        )
        
        assert EventType.OPPORTUNITY_CREATED in event_bus._subscribers
        assert handler in event_bus._subscribers[EventType.OPPORTUNITY_CREATED]
    
    @pytest.mark.asyncio
    async def test_event_replay(self, event_bus, redis_mock):
        """Test event replay functionality."""
        from_timestamp = datetime.now(timezone.utc) - timedelta(hours=1)
        
        events = []
        async for event in event_bus.replay_events(
            EventType.OPPORTUNITY_CREATED,
            from_timestamp
        ):
            events.append(event)
        
        assert len(events) > 0
        redis_mock.zrangebyscore.assert_called_once()
        redis_mock.get.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_event_stats(self, event_bus, redis_mock):
        """Test event statistics retrieval."""
        stats = await event_bus.get_event_stats()
        
        assert "total_events" in stats
        assert "events_by_type" in stats
        assert "active_subscribers" in stats
        assert "subscription_tasks" in stats
        
        # Verify Redis calls for stats
        assert redis_mock.zcard.call_count > 0


class TestEventHandlers:
    """Test event handler functionality."""
    
    @pytest.mark.asyncio
    async def test_opportunity_event_handler(self):
        """Test opportunity event handler."""
        handler = OpportunityEventHandler()
        
        event = Event(
            id="test-1",
            event_type=EventType.OPPORTUNITY_CREATED,
            payload={"opportunity_id": "opp-123", "title": "Test Opportunity"},
            timestamp=datetime.now(timezone.utc),
            source="test"
        )
        
        # Should not raise an exception
        await handler.handle(event)
    
    @pytest.mark.asyncio
    async def test_user_event_handler(self):
        """Test user event handler."""
        handler = UserEventHandler()
        
        event = Event(
            id="test-1",
            event_type=EventType.USER_REGISTERED,
            payload={"user_id": "user-123", "email": "test@example.com"},
            timestamp=datetime.now(timezone.utc),
            source="test"
        )
        
        # Should not raise an exception
        await handler.handle(event)
    
    @pytest.mark.asyncio
    async def test_agent_event_handler(self):
        """Test agent event handler."""
        handler = AgentEventHandler()
        
        event = Event(
            id="test-1",
            event_type=EventType.AGENT_TASK_COMPLETED,
            payload={
                "agent_id": "agent-123",
                "task_id": "task-456",
                "task_type": "analysis",
                "duration_seconds": 5.2
            },
            timestamp=datetime.now(timezone.utc),
            source="test"
        )
        
        # Should not raise an exception
        await handler.handle(event)
    
    @pytest.mark.asyncio
    async def test_system_event_handler(self):
        """Test system event handler."""
        handler = SystemEventHandler()
        
        event = Event(
            id="test-1",
            event_type=EventType.SYSTEM_HEALTH_CHECK,
            payload={"component": "database", "status": "healthy"},
            timestamp=datetime.now(timezone.utc),
            source="test"
        )
        
        # Should not raise an exception
        await handler.handle(event)
    
    @pytest.mark.asyncio
    async def test_market_signal_event_handler(self):
        """Test market signal event handler."""
        handler = MarketSignalEventHandler()
        
        event = Event(
            id="test-1",
            event_type=EventType.SIGNAL_DETECTED,
            payload={
                "signal_id": "signal-123",
                "source": "reddit",
                "signal_type": "pain_point",
                "confidence": 0.85
            },
            timestamp=datetime.now(timezone.utc),
            source="test"
        )
        
        # Should not raise an exception
        await handler.handle(event)


class TestEventBusConfig:
    """Test event bus configuration."""
    
    def test_event_bus_config_defaults(self):
        """Test default configuration values."""
        config = EventBusConfig()
        
        assert config.redis_url == "redis://localhost:6379/0"
        assert config.event_ttl == 604800  # 7 days
        assert config.max_retries == 3
        assert config.enable_event_handlers is True
        assert "opportunity" in config.enabled_handlers
    
    @patch.dict('os.environ', {
        'REDIS_URL': 'redis://custom:6379/1',
        'EVENT_TTL_SECONDS': '86400',
        'ENABLED_EVENT_HANDLERS': 'opportunity,user'
    })
    def test_event_bus_config_from_env(self):
        """Test configuration from environment variables."""
        config = EventBusConfig()
        
        assert config.redis_url == "redis://custom:6379/1"
        assert config.event_ttl == 86400
        assert config.enabled_handlers == ["opportunity", "user"]


class TestEventBusManager:
    """Test event bus manager functionality."""
    
    @pytest.mark.asyncio
    async def test_event_bus_manager_initialization(self, redis_mock):
        """Test event bus manager initialization."""
        with patch('redis.asyncio.from_url', return_value=redis_mock):
            manager = EventBusManager()
            await manager.initialize()
            
            assert manager._initialized is True
            assert manager.event_bus is not None
            
            await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_event_bus_manager_stats(self, redis_mock):
        """Test event bus manager statistics."""
        with patch('redis.asyncio.from_url', return_value=redis_mock):
            manager = EventBusManager()
            await manager.initialize()
            
            stats = await manager.get_stats()
            
            assert "total_events" in stats
            assert "registered_handlers" in stats
            assert "config" in stats
            
            await manager.shutdown()


class TestConvenienceFunctions:
    """Test convenience functions for event publishing."""
    
    @pytest.mark.asyncio
    async def test_publish_opportunity_created(self, redis_mock):
        """Test opportunity created event publishing."""
        with patch('redis.asyncio.from_url', return_value=redis_mock):
            event_id = await publish_opportunity_created(
                opportunity_id="opp-123",
                title="Test Opportunity",
                description="Test description"
            )
            
            assert event_id is not None
            redis_mock.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_user_registered(self, redis_mock):
        """Test user registered event publishing."""
        with patch('redis.asyncio.from_url', return_value=redis_mock):
            event_id = await publish_user_registered(
                user_id="user-123",
                email="test@example.com"
            )
            
            assert event_id is not None
            redis_mock.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_agent_task_completed(self, redis_mock):
        """Test agent task completed event publishing."""
        with patch('redis.asyncio.from_url', return_value=redis_mock):
            event_id = await publish_agent_task_completed(
                agent_id="agent-123",
                task_id="task-456",
                task_type="analysis",
                duration_seconds=5.2
            )
            
            assert event_id is not None
            redis_mock.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_system_health_check(self, redis_mock):
        """Test system health check event publishing."""
        with patch('redis.asyncio.from_url', return_value=redis_mock):
            event_id = await publish_system_health_check(
                component="database",
                status="healthy"
            )
            
            assert event_id is not None
            redis_mock.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_signal_detected(self, redis_mock):
        """Test signal detected event publishing."""
        with patch('redis.asyncio.from_url', return_value=redis_mock):
            event_id = await publish_signal_detected(
                signal_id="signal-123",
                source="reddit",
                signal_type="pain_point",
                confidence=0.85
            )
            
            assert event_id is not None
            redis_mock.publish.assert_called_once()


class TestEventBusIntegration:
    """Test event bus integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_event_flow(self, redis_mock):
        """Test complete event flow from publish to handling."""
        with patch('redis.asyncio.from_url', return_value=redis_mock):
            # Initialize event bus
            bus = EventBus()
            await bus.initialize()
            
            # Create test handler
            handler = TestEventHandler()
            
            # Subscribe to events
            await bus.subscribe_to_events([EventType.OPPORTUNITY_CREATED], handler)
            
            # Publish event
            event_id = await bus.publish_event(
                event_type=EventType.OPPORTUNITY_CREATED,
                payload={"opportunity_id": "opp-123", "title": "Test"},
                source="test"
            )
            
            assert event_id is not None
            
            # Verify Redis interactions
            redis_mock.publish.assert_called()
            redis_mock.setex.assert_called()
            
            await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_event_processing(self, redis_mock):
        """Test error handling during event processing."""
        
        class ErrorHandler(EventHandler):
            def __init__(self):
                super().__init__("error_handler")
                self.errors = []
            
            async def handle(self, event: Event) -> None:
                raise ValueError("Test error")
            
            async def on_error(self, event: Event, error: Exception) -> None:
                self.errors.append(error)
        
        with patch('redis.asyncio.from_url', return_value=redis_mock):
            bus = EventBus()
            await bus.initialize()
            
            handler = ErrorHandler()
            await bus.subscribe_to_events([EventType.OPPORTUNITY_CREATED], handler)
            
            # This should not raise an exception
            await bus.publish_event(
                event_type=EventType.OPPORTUNITY_CREATED,
                payload={"test": "data"},
                source="test"
            )
            
            await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_multiple_handlers_same_event(self, redis_mock):
        """Test multiple handlers for the same event type."""
        with patch('redis.asyncio.from_url', return_value=redis_mock):
            bus = EventBus()
            await bus.initialize()
            
            handler1 = TestEventHandler("handler1")
            handler2 = TestEventHandler("handler2")
            
            await bus.subscribe_to_events([EventType.OPPORTUNITY_CREATED], handler1)
            await bus.subscribe_to_events([EventType.OPPORTUNITY_CREATED], handler2)
            
            # Both handlers should be registered
            assert len(bus._subscribers[EventType.OPPORTUNITY_CREATED]) == 2
            
            await bus.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])