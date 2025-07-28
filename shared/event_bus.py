"""
Event Bus System for AI Opportunity Browser

This module implements an event-driven architecture using Redis pub/sub
to enable decoupled service communication, event sourcing, and real-time
streaming analytics.

Features:
- Event publishing and subscription
- Event replay capabilities
- Event persistence for audit trails
- Type-safe event handling
- Async/await support
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Standard event types for the AI Opportunity Browser platform."""
    
    # Opportunity Events
    OPPORTUNITY_CREATED = "opportunity.created"
    OPPORTUNITY_UPDATED = "opportunity.updated"
    OPPORTUNITY_DELETED = "opportunity.deleted"
    OPPORTUNITY_VALIDATED = "opportunity.validated"
    
    # User Events
    USER_REGISTERED = "user.registered"
    USER_PROFILE_UPDATED = "user.profile_updated"
    USER_REPUTATION_CHANGED = "user.reputation_changed"
    
    # Validation Events
    VALIDATION_SUBMITTED = "validation.submitted"
    VALIDATION_APPROVED = "validation.approved"
    VALIDATION_REJECTED = "validation.rejected"
    
    # Agent Events
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"
    AGENT_TASK_COMPLETED = "agent.task_completed"
    
    # Market Signal Events
    SIGNAL_DETECTED = "signal.detected"
    SIGNAL_PROCESSED = "signal.processed"
    SIGNAL_CLUSTERED = "signal.clustered"
    
    # System Events
    SYSTEM_HEALTH_CHECK = "system.health_check"
    SYSTEM_ERROR = "system.error"
    SYSTEM_MAINTENANCE = "system.maintenance"


@dataclass
class Event:
    """Base event structure for all platform events."""
    
    id: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    source: str
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class EventHandler:
    """Base class for event handlers."""
    
    def __init__(self, handler_id: str):
        self.handler_id = handler_id
        self.logger = logging.getLogger(f"{__name__}.{handler_id}")
    
    async def handle(self, event: Event) -> None:
        """Handle an event. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement handle method")
    
    async def on_error(self, event: Event, error: Exception) -> None:
        """Handle errors during event processing."""
        self.logger.error(
            f"Error handling event {event.id} of type {event.event_type}: {error}",
            exc_info=True
        )


class EventBus:
    """
    Redis-based event bus for decoupled service communication.
    
    Provides event publishing, subscription, and replay capabilities
    with support for event persistence and audit trails.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        event_ttl: int = 86400 * 7,  # 7 days
        max_retries: int = 3
    ):
        self.redis_url = redis_url
        self.event_ttl = event_ttl
        self.max_retries = max_retries
        self._redis_client: Optional[redis.Redis] = None
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._subscription_tasks: List[asyncio.Task] = []
        self._running = False
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> None:
        """Initialize the event bus and Redis connection."""
        try:
            self._redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            # Test connection
            await self._redis_client.ping()
            self.logger.info("Event bus initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize event bus: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the event bus and cleanup resources."""
        self._running = False
        
        # Cancel subscription tasks
        for task in self._subscription_tasks:
            task.cancel()
        
        if self._subscription_tasks:
            await asyncio.gather(*self._subscription_tasks, return_exceptions=True)
        
        # Close Redis connection
        if self._redis_client:
            await self._redis_client.close()
        
        self.logger.info("Event bus shutdown completed")
    
    async def publish_event(
        self,
        event_type: Union[str, EventType],
        payload: Dict[str, Any],
        source: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Publish an event to the event bus.
        
        Args:
            event_type: Type of event to publish
            payload: Event data payload
            source: Source service/component publishing the event
            correlation_id: Optional correlation ID for request tracing
            metadata: Optional additional metadata
            
        Returns:
            Event ID for tracking
        """
        if not self._redis_client:
            raise RuntimeError("Event bus not initialized")
        
        event_id = str(uuid.uuid4())
        event = Event(
            id=event_id,
            event_type=str(event_type),
            payload=payload,
            timestamp=datetime.now(timezone.utc),
            source=source,
            correlation_id=correlation_id,
            metadata=metadata or {}
        )
        
        try:
            # Serialize event
            event_data = json.dumps(event.to_dict())
            
            # Publish to Redis pub/sub
            channel = f"events:{event_type}"
            await self._redis_client.publish(channel, event_data)
            
            # Store event for replay capability
            event_key = f"event:{event_id}"
            await self._redis_client.setex(event_key, self.event_ttl, event_data)
            
            # Add to event timeline
            timeline_key = f"timeline:{event_type}"
            await self._redis_client.zadd(
                timeline_key,
                {event_id: event.timestamp.timestamp()}
            )
            await self._redis_client.expire(timeline_key, self.event_ttl)
            
            self.logger.debug(f"Published event {event_id} of type {event_type}")
            return event_id
            
        except Exception as e:
            self.logger.error(f"Failed to publish event: {e}")
            raise
    
    async def subscribe_to_events(
        self,
        event_types: List[Union[str, EventType]],
        handler: EventHandler
    ) -> None:
        """
        Subscribe to specific event types with a handler.
        
        Args:
            event_types: List of event types to subscribe to
            handler: Event handler to process events
        """
        if not self._redis_client:
            raise RuntimeError("Event bus not initialized")
        
        # Register handler for event types
        for event_type in event_types:
            event_type_str = str(event_type)
            if event_type_str not in self._subscribers:
                self._subscribers[event_type_str] = []
            self._subscribers[event_type_str].append(handler)
        
        # Start subscription task if not already running
        if not self._running:
            self._running = True
            task = asyncio.create_task(self._subscription_loop())
            self._subscription_tasks.append(task)
        
        self.logger.info(
            f"Subscribed handler {handler.handler_id} to events: {event_types}"
        )
    
    async def _subscription_loop(self) -> None:
        """Main subscription loop for processing events."""
        try:
            pubsub = self._redis_client.pubsub()
            
            # Subscribe to all event channels
            channels = [f"events:{event_type}" for event_type in self._subscribers.keys()]
            if channels:
                await pubsub.subscribe(*channels)
            
            self.logger.info(f"Started subscription loop for channels: {channels}")
            
            async for message in pubsub.listen():
                if not self._running:
                    break
                
                if message['type'] == 'message':
                    await self._process_message(message)
                    
        except asyncio.CancelledError:
            self.logger.info("Subscription loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in subscription loop: {e}")
        finally:
            if 'pubsub' in locals():
                await pubsub.close()
    
    async def _process_message(self, message: Dict[str, Any]) -> None:
        """Process a received message from Redis pub/sub."""
        try:
            # Parse event data
            event_data = json.loads(message['data'])
            event = Event.from_dict(event_data)
            
            # Get handlers for this event type
            handlers = self._subscribers.get(event.event_type, [])
            
            # Process event with each handler
            for handler in handlers:
                try:
                    await handler.handle(event)
                except Exception as e:
                    await handler.on_error(event, e)
                    
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    async def replay_events(
        self,
        event_type: Union[str, EventType],
        from_timestamp: datetime,
        to_timestamp: Optional[datetime] = None
    ) -> AsyncIterator[Event]:
        """
        Replay events of a specific type from a given timestamp.
        
        Args:
            event_type: Type of events to replay
            from_timestamp: Start timestamp for replay
            to_timestamp: End timestamp for replay (optional)
            
        Yields:
            Event objects in chronological order
        """
        if not self._redis_client:
            raise RuntimeError("Event bus not initialized")
        
        timeline_key = f"timeline:{event_type}"
        min_score = from_timestamp.timestamp()
        max_score = to_timestamp.timestamp() if to_timestamp else "+inf"
        
        try:
            # Get event IDs in time range
            event_ids = await self._redis_client.zrangebyscore(
                timeline_key, min_score, max_score
            )
            
            # Fetch and yield events
            for event_id in event_ids:
                event_key = f"event:{event_id}"
                event_data = await self._redis_client.get(event_key)
                
                if event_data:
                    event_dict = json.loads(event_data)
                    event = Event.from_dict(event_dict)
                    yield event
                    
        except Exception as e:
            self.logger.error(f"Error replaying events: {e}")
            raise
    
    async def get_event_stats(self) -> Dict[str, Any]:
        """Get statistics about events in the system."""
        if not self._redis_client:
            raise RuntimeError("Event bus not initialized")
        
        stats = {
            "total_events": 0,
            "events_by_type": {},
            "active_subscribers": len(self._subscribers),
            "subscription_tasks": len(self._subscription_tasks)
        }
        
        try:
            # Count events by type
            for event_type in EventType:
                timeline_key = f"timeline:{event_type}"
                count = await self._redis_client.zcard(timeline_key)
                if count > 0:
                    stats["events_by_type"][str(event_type)] = count
                    stats["total_events"] += count
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting event stats: {e}")
            return stats


# Global event bus instance
_event_bus: Optional[EventBus] = None


async def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        await _event_bus.initialize()
    return _event_bus


async def publish_event(
    event_type: Union[str, EventType],
    payload: Dict[str, Any],
    source: str,
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Convenience function to publish an event."""
    event_bus = await get_event_bus()
    return await event_bus.publish_event(
        event_type, payload, source, correlation_id, metadata
    )


async def subscribe_to_events(
    event_types: List[Union[str, EventType]],
    handler: EventHandler
) -> None:
    """Convenience function to subscribe to events."""
    event_bus = await get_event_bus()
    await event_bus.subscribe_to_events(event_types, handler)


# Event sourcing integration
async def publish_event_with_sourcing(
    event_type: Union[str, EventType],
    payload: Dict[str, Any],
    source: str,
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    aggregate_id: Optional[str] = None,
    aggregate_type: Optional[str] = None,
    aggregate_version: Optional[int] = None,
    causation_id: Optional[str] = None,
    command_id: Optional[str] = None
) -> str:
    """
    Publish an event with event sourcing metadata.
    
    This function publishes an event to the event bus and automatically
    includes metadata needed for event sourcing.
    """
    # Enhance metadata with event sourcing information
    enhanced_metadata = metadata or {}
    enhanced_metadata.update({
        'aggregate_id': aggregate_id,
        'aggregate_type': aggregate_type,
        'aggregate_version': aggregate_version,
        'causation_id': causation_id,
        'command_id': command_id,
        'version': enhanced_metadata.get('version', '1.0')
    })
    
    return await publish_event(
        event_type=event_type,
        payload=payload,
        source=source,
        correlation_id=correlation_id,
        metadata=enhanced_metadata
    )