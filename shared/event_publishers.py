"""
Event Publishing Utilities for AI Opportunity Browser

This module provides high-level utilities for publishing events
with standardized payloads and automatic correlation tracking.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

from .event_bus import EventType
from .event_bus_factory import get_global_event_bus

logger = logging.getLogger(__name__)


class EventPublisher:
    """High-level event publisher with convenience methods."""
    
    def __init__(self, source: str, correlation_id: Optional[str] = None):
        self.source = source
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self._event_bus = None
    
    async def _get_event_bus(self):
        """Get event bus instance."""
        if self._event_bus is None:
            self._event_bus = await get_global_event_bus()
        return self._event_bus
    
    async def publish(
        self,
        event_type: Union[str, EventType],
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        partition_key: Optional[str] = None
    ) -> str:
        """
        Publish an event with automatic correlation tracking.
        
        Args:
            event_type: Type of event to publish
            payload: Event data payload
            metadata: Optional additional metadata
            partition_key: Optional partitioning key for Kafka
            
        Returns:
            Event ID
        """
        event_bus = await self._get_event_bus()
        
        # Add standard metadata
        enhanced_metadata = {
            "publisher_source": self.source,
            "published_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {})
        }
        
        # Handle Kafka-specific parameters
        publish_kwargs = {
            "event_type": event_type,
            "payload": payload,
            "source": self.source,
            "correlation_id": self.correlation_id,
            "metadata": enhanced_metadata
        }
        
        # Add partition key for Kafka
        if hasattr(event_bus, 'publish_event') and partition_key:
            # Check if it's KafkaEventBus by checking method signature
            import inspect
            sig = inspect.signature(event_bus.publish_event)
            if 'partition_key' in sig.parameters:
                publish_kwargs['partition_key'] = partition_key
        
        return await event_bus.publish_event(**publish_kwargs)


class OpportunityEventPublisher(EventPublisher):
    """Publisher for opportunity-related events."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__("opportunity_service", correlation_id)
    
    async def opportunity_created(
        self,
        opportunity_id: str,
        title: str,
        description: str,
        ai_solution_type: str,
        market_size_estimate: Optional[float] = None,
        created_by: Optional[str] = None,
        **kwargs
    ) -> str:
        """Publish opportunity created event."""
        payload = {
            "opportunity_id": opportunity_id,
            "title": title,
            "description": description,
            "ai_solution_type": ai_solution_type,
            "market_size_estimate": market_size_estimate,
            "created_by": created_by,
            **kwargs
        }
        
        return await self.publish(
            EventType.OPPORTUNITY_CREATED,
            payload,
            partition_key=opportunity_id
        )
    
    async def opportunity_updated(
        self,
        opportunity_id: str,
        changes: Dict[str, Any],
        updated_by: Optional[str] = None,
        **kwargs
    ) -> str:
        """Publish opportunity updated event."""
        payload = {
            "opportunity_id": opportunity_id,
            "changes": changes,
            "updated_by": updated_by,
            "change_count": len(changes),
            **kwargs
        }
        
        return await self.publish(
            EventType.OPPORTUNITY_UPDATED,
            payload,
            partition_key=opportunity_id
        )
    
    async def opportunity_validated(
        self,
        opportunity_id: str,
        validation_id: str,
        validator_id: str,
        validation_score: float,
        validation_type: str,
        comments: Optional[str] = None,
        **kwargs
    ) -> str:
        """Publish opportunity validation event."""
        payload = {
            "opportunity_id": opportunity_id,
            "validation_id": validation_id,
            "validator_id": validator_id,
            "validation_score": validation_score,
            "validation_type": validation_type,
            "comments": comments,
            **kwargs
        }
        
        return await self.publish(
            EventType.OPPORTUNITY_VALIDATED,
            payload,
            partition_key=opportunity_id
        )
    
    async def opportunity_deleted(
        self,
        opportunity_id: str,
        deleted_by: str,
        reason: Optional[str] = None,
        **kwargs
    ) -> str:
        """Publish opportunity deleted event."""
        payload = {
            "opportunity_id": opportunity_id,
            "deleted_by": deleted_by,
            "reason": reason,
            **kwargs
        }
        
        return await self.publish(
            EventType.OPPORTUNITY_DELETED,
            payload,
            partition_key=opportunity_id
        )


class UserEventPublisher(EventPublisher):
    """Publisher for user-related events."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__("user_service", correlation_id)
    
    async def user_registered(
        self,
        user_id: str,
        email: str,
        username: Optional[str] = None,
        user_type: str = "user",
        **kwargs
    ) -> str:
        """Publish user registration event."""
        payload = {
            "user_id": user_id,
            "email": email,
            "username": username,
            "user_type": user_type,
            **kwargs
        }
        
        return await self.publish(
            EventType.USER_REGISTERED,
            payload,
            partition_key=user_id
        )
    
    async def user_profile_updated(
        self,
        user_id: str,
        changes: Dict[str, Any],
        **kwargs
    ) -> str:
        """Publish user profile update event."""
        payload = {
            "user_id": user_id,
            "changes": changes,
            "change_count": len(changes),
            **kwargs
        }
        
        return await self.publish(
            EventType.USER_PROFILE_UPDATED,
            payload,
            partition_key=user_id
        )
    
    async def user_reputation_changed(
        self,
        user_id: str,
        old_score: float,
        new_score: float,
        reason: str,
        change_amount: Optional[float] = None,
        **kwargs
    ) -> str:
        """Publish user reputation change event."""
        payload = {
            "user_id": user_id,
            "old_score": old_score,
            "new_score": new_score,
            "reason": reason,
            "change_amount": change_amount or (new_score - old_score),
            **kwargs
        }
        
        return await self.publish(
            EventType.USER_REPUTATION_CHANGED,
            payload,
            partition_key=user_id
        )


class AgentEventPublisher(EventPublisher):
    """Publisher for AI agent events."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__("agent_orchestrator", correlation_id)
    
    async def agent_started(
        self,
        agent_id: str,
        agent_type: str,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Publish agent started event."""
        payload = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "config": config,
            **kwargs
        }
        
        return await self.publish(
            EventType.AGENT_STARTED,
            payload,
            partition_key=agent_id
        )
    
    async def agent_stopped(
        self,
        agent_id: str,
        agent_type: str,
        reason: str,
        uptime_seconds: Optional[float] = None,
        **kwargs
    ) -> str:
        """Publish agent stopped event."""
        payload = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "reason": reason,
            "uptime_seconds": uptime_seconds,
            **kwargs
        }
        
        return await self.publish(
            EventType.AGENT_STOPPED,
            payload,
            partition_key=agent_id
        )
    
    async def agent_error(
        self,
        agent_id: str,
        agent_type: str,
        error_message: str,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None,
        **kwargs
    ) -> str:
        """Publish agent error event."""
        payload = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "error_message": error_message,
            "error_type": error_type,
            "stack_trace": stack_trace,
            **kwargs
        }
        
        return await self.publish(
            EventType.AGENT_ERROR,
            payload,
            partition_key=agent_id
        )
    
    async def agent_task_completed(
        self,
        agent_id: str,
        task_id: str,
        task_type: str,
        duration_seconds: float,
        success: bool = True,
        result: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Publish agent task completion event."""
        payload = {
            "agent_id": agent_id,
            "task_id": task_id,
            "task_type": task_type,
            "duration_seconds": duration_seconds,
            "success": success,
            "result": result,
            **kwargs
        }
        
        return await self.publish(
            EventType.AGENT_TASK_COMPLETED,
            payload,
            partition_key=agent_id
        )


class MarketSignalEventPublisher(EventPublisher):
    """Publisher for market signal events."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__("monitoring_agent", correlation_id)
    
    async def signal_detected(
        self,
        signal_id: str,
        source: str,
        signal_type: str,
        content: str,
        confidence: float,
        engagement_metrics: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Publish market signal detected event."""
        payload = {
            "signal_id": signal_id,
            "source": source,
            "signal_type": signal_type,
            "content": content,
            "confidence": confidence,
            "engagement_metrics": engagement_metrics,
            **kwargs
        }
        
        return await self.publish(
            EventType.SIGNAL_DETECTED,
            payload,
            partition_key=signal_id
        )
    
    async def signal_processed(
        self,
        signal_id: str,
        processing_result: str,
        quality_score: Optional[float] = None,
        extracted_keywords: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Publish signal processing completion event."""
        payload = {
            "signal_id": signal_id,
            "processing_result": processing_result,
            "quality_score": quality_score,
            "extracted_keywords": extracted_keywords,
            **kwargs
        }
        
        return await self.publish(
            EventType.SIGNAL_PROCESSED,
            payload,
            partition_key=signal_id
        )
    
    async def signal_clustered(
        self,
        cluster_id: str,
        signal_ids: List[str],
        cluster_theme: str,
        signal_count: Optional[int] = None,
        **kwargs
    ) -> str:
        """Publish signal clustering event."""
        payload = {
            "cluster_id": cluster_id,
            "signal_ids": signal_ids,
            "cluster_theme": cluster_theme,
            "signal_count": signal_count or len(signal_ids),
            **kwargs
        }
        
        return await self.publish(
            EventType.SIGNAL_CLUSTERED,
            payload,
            partition_key=cluster_id
        )


class SystemEventPublisher(EventPublisher):
    """Publisher for system-wide events."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__("system", correlation_id)
    
    async def health_check(
        self,
        component: str,
        status: str,
        response_time_ms: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Publish system health check event."""
        payload = {
            "component": component,
            "status": status,
            "response_time_ms": response_time_ms,
            "details": details,
            **kwargs
        }
        
        return await self.publish(
            EventType.SYSTEM_HEALTH_CHECK,
            payload,
            partition_key=component
        )
    
    async def system_error(
        self,
        component: str,
        error_message: str,
        severity: str = "medium",
        error_code: Optional[str] = None,
        **kwargs
    ) -> str:
        """Publish system error event."""
        payload = {
            "component": component,
            "error_message": error_message,
            "severity": severity,
            "error_code": error_code,
            **kwargs
        }
        
        return await self.publish(
            EventType.SYSTEM_ERROR,
            payload,
            partition_key=component
        )
    
    async def maintenance_scheduled(
        self,
        maintenance_type: str,
        start_time: datetime,
        estimated_duration: str,
        affected_components: List[str],
        **kwargs
    ) -> str:
        """Publish system maintenance event."""
        payload = {
            "maintenance_type": maintenance_type,
            "start_time": start_time.isoformat(),
            "estimated_duration": estimated_duration,
            "affected_components": affected_components,
            **kwargs
        }
        
        return await self.publish(
            EventType.SYSTEM_MAINTENANCE,
            payload
        )


class BatchEventPublisher:
    """Publisher for batch event operations."""
    
    def __init__(self, source: str, correlation_id: Optional[str] = None):
        self.source = source
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self._events_buffer: List[Dict[str, Any]] = []
        self._max_batch_size = 100
        self._flush_interval = 5.0  # seconds
        self._last_flush = datetime.now()
    
    async def add_event(
        self,
        event_type: Union[str, EventType],
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        partition_key: Optional[str] = None
    ) -> None:
        """Add event to batch buffer."""
        event_data = {
            "event_type": event_type,
            "payload": payload,
            "metadata": metadata,
            "partition_key": partition_key
        }
        
        self._events_buffer.append(event_data)
        
        # Auto-flush if buffer is full or time interval exceeded
        if (len(self._events_buffer) >= self._max_batch_size or
            (datetime.now() - self._last_flush).total_seconds() >= self._flush_interval):
            await self.flush()
    
    async def flush(self) -> List[str]:
        """Flush all buffered events."""
        if not self._events_buffer:
            return []
        
        event_bus = await get_global_event_bus()
        event_ids = []
        
        # Publish all events
        for event_data in self._events_buffer:
            try:
                publish_kwargs = {
                    "event_type": event_data["event_type"],
                    "payload": event_data["payload"],
                    "source": self.source,
                    "correlation_id": self.correlation_id,
                    "metadata": event_data.get("metadata")
                }
                
                # Add partition key for Kafka
                if hasattr(event_bus, 'publish_event') and event_data.get("partition_key"):
                    import inspect
                    sig = inspect.signature(event_bus.publish_event)
                    if 'partition_key' in sig.parameters:
                        publish_kwargs['partition_key'] = event_data["partition_key"]
                
                event_id = await event_bus.publish_event(**publish_kwargs)
                event_ids.append(event_id)
                
            except Exception as e:
                logger.error(f"Failed to publish batched event: {e}")
        
        # Clear buffer
        self._events_buffer.clear()
        self._last_flush = datetime.now()
        
        logger.info(f"Flushed {len(event_ids)} events from batch")
        return event_ids
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - flush remaining events."""
        await self.flush()


@asynccontextmanager
async def event_publishing_context(source: str, correlation_id: Optional[str] = None):
    """Context manager for event publishing with automatic correlation tracking."""
    publisher = EventPublisher(source, correlation_id)
    try:
        yield publisher
    finally:
        # Cleanup if needed
        pass


@asynccontextmanager
async def batch_event_publishing_context(source: str, correlation_id: Optional[str] = None):
    """Context manager for batch event publishing."""
    async with BatchEventPublisher(source, correlation_id) as publisher:
        yield publisher


# Convenience functions for quick event publishing
async def publish_opportunity_created(opportunity_id: str, title: str, **kwargs) -> str:
    """Quick publish opportunity created event."""
    publisher = OpportunityEventPublisher()
    return await publisher.opportunity_created(opportunity_id, title, **kwargs)


async def publish_user_registered(user_id: str, email: str, **kwargs) -> str:
    """Quick publish user registered event."""
    publisher = UserEventPublisher()
    return await publisher.user_registered(user_id, email, **kwargs)


async def publish_agent_task_completed(agent_id: str, task_id: str, task_type: str, duration: float, **kwargs) -> str:
    """Quick publish agent task completed event."""
    publisher = AgentEventPublisher()
    return await publisher.agent_task_completed(agent_id, task_id, task_type, duration, **kwargs)


async def publish_signal_detected(signal_id: str, source: str, signal_type: str, confidence: float, **kwargs) -> str:
    """Quick publish signal detected event."""
    publisher = MarketSignalEventPublisher()
    return await publisher.signal_detected(signal_id, source, signal_type, "", confidence, **kwargs)


async def publish_system_health_check(component: str, status: str, **kwargs) -> str:
    """Quick publish system health check event."""
    publisher = SystemEventPublisher()
    return await publisher.health_check(component, status, **kwargs)