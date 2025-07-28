"""
Events API router for AI Opportunity Browser.

This module provides endpoints for managing and monitoring the event bus system.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field

from shared.event_bus import EventType, Event
from shared.event_config import get_event_bus_manager, EventBusManager
from api.core.dependencies import get_current_user, require_admin
from shared.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class EventStatsResponse(BaseModel):
    """Response model for event statistics."""
    total_events: int = Field(..., description="Total number of events")
    events_by_type: Dict[str, int] = Field(..., description="Event counts by type")
    active_subscribers: int = Field(..., description="Number of active subscribers")
    subscription_tasks: int = Field(..., description="Number of subscription tasks")
    registered_handlers: List[str] = Field(..., description="List of registered handlers")
    config: Dict[str, Any] = Field(..., description="Event bus configuration")


class EventPublishRequest(BaseModel):
    """Request model for publishing events."""
    event_type: str = Field(..., description="Type of event to publish")
    payload: Dict[str, Any] = Field(..., description="Event payload data")
    source: str = Field(..., description="Source of the event")
    correlation_id: Optional[str] = Field(None, description="Optional correlation ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class EventPublishResponse(BaseModel):
    """Response model for event publishing."""
    event_id: str = Field(..., description="ID of the published event")
    event_type: str = Field(..., description="Type of event published")
    timestamp: datetime = Field(..., description="Event timestamp")
    success: bool = Field(..., description="Whether the event was published successfully")


class EventReplayRequest(BaseModel):
    """Request model for event replay."""
    event_type: str = Field(..., description="Type of events to replay")
    from_timestamp: datetime = Field(..., description="Start timestamp for replay")
    to_timestamp: Optional[datetime] = Field(None, description="End timestamp for replay")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of events to return")


class EventResponse(BaseModel):
    """Response model for individual events."""
    id: str = Field(..., description="Event ID")
    event_type: str = Field(..., description="Event type")
    payload: Dict[str, Any] = Field(..., description="Event payload")
    timestamp: datetime = Field(..., description="Event timestamp")
    source: str = Field(..., description="Event source")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Event metadata")


async def get_event_manager(request: Request) -> EventBusManager:
    """Get the event bus manager from app state."""
    if not hasattr(request.app.state, 'event_manager'):
        raise HTTPException(
            status_code=503,
            detail="Event bus system not available"
        )
    return request.app.state.event_manager


@router.get("/stats", response_model=EventStatsResponse)
async def get_event_stats(
    event_manager: EventBusManager = Depends(get_event_manager),
    current_user: User = Depends(get_current_user)
):
    """
    Get event bus statistics.
    
    Returns comprehensive statistics about the event bus system including
    event counts, active subscribers, and configuration details.
    """
    try:
        stats = await event_manager.get_stats()
        return EventStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting event stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve event statistics"
        )


@router.get("/types", response_model=List[str])
async def get_event_types(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of available event types.
    
    Returns all available event types that can be published or subscribed to.
    """
    return [event_type.value for event_type in EventType]


@router.post("/publish", response_model=EventPublishResponse)
async def publish_event(
    request: EventPublishRequest,
    event_manager: EventBusManager = Depends(get_event_manager),
    current_user: User = Depends(require_admin())
):
    """
    Publish an event to the event bus.
    
    Allows administrators to manually publish events for testing or
    administrative purposes.
    """
    try:
        if not event_manager.event_bus:
            raise HTTPException(
                status_code=503,
                detail="Event bus not initialized"
            )
        
        # Validate event type
        valid_types = [event_type.value for event_type in EventType]
        if request.event_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event type. Must be one of: {valid_types}"
            )
        
        # Publish the event
        event_id = await event_manager.event_bus.publish_event(
            event_type=request.event_type,
            payload=request.payload,
            source=request.source,
            correlation_id=request.correlation_id,
            metadata=request.metadata
        )
        
        return EventPublishResponse(
            event_id=event_id,
            event_type=request.event_type,
            timestamp=datetime.now(timezone.utc),
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing event: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to publish event"
        )


@router.post("/replay", response_model=List[EventResponse])
async def replay_events(
    request: EventReplayRequest,
    event_manager: EventBusManager = Depends(get_event_manager),
    current_user: User = Depends(require_admin())
):
    """
    Replay events from the event bus.
    
    Allows administrators to replay events for debugging, auditing,
    or recovery purposes.
    """
    try:
        if not event_manager.event_bus:
            raise HTTPException(
                status_code=503,
                detail="Event bus not initialized"
            )
        
        # Validate event type
        valid_types = [event_type.value for event_type in EventType]
        if request.event_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event type. Must be one of: {valid_types}"
            )
        
        # Replay events
        events = []
        count = 0
        
        async for event in event_manager.event_bus.replay_events(
            event_type=request.event_type,
            from_timestamp=request.from_timestamp,
            to_timestamp=request.to_timestamp
        ):
            if count >= request.limit:
                break
            
            events.append(EventResponse(
                id=event.id,
                event_type=event.event_type,
                payload=event.payload,
                timestamp=event.timestamp,
                source=event.source,
                correlation_id=event.correlation_id,
                metadata=event.metadata
            ))
            count += 1
        
        return events
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replaying events: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to replay events"
        )


@router.get("/health")
async def get_event_bus_health(
    event_manager: EventBusManager = Depends(get_event_manager),
    current_user: User = Depends(get_current_user)
):
    """
    Get event bus health status.
    
    Returns the health status of the event bus system including
    Redis connectivity and handler status.
    """
    try:
        health_status = {
            "status": "healthy",
            "initialized": event_manager._initialized,
            "redis_connected": False,
            "handlers_count": len(event_manager.handlers),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Test Redis connection
        if event_manager.event_bus and event_manager.event_bus._redis_client:
            try:
                await event_manager.event_bus._redis_client.ping()
                health_status["redis_connected"] = True
            except Exception as e:
                health_status["status"] = "degraded"
                health_status["redis_error"] = str(e)
        else:
            health_status["status"] = "degraded"
            health_status["redis_error"] = "Redis client not initialized"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error checking event bus health: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.delete("/handlers/{handler_name}")
async def remove_event_handler(
    handler_name: str,
    event_manager: EventBusManager = Depends(get_event_manager),
    current_user: User = Depends(require_admin())
):
    """
    Remove an event handler.
    
    Allows administrators to remove event handlers for maintenance
    or troubleshooting purposes.
    """
    try:
        if handler_name not in event_manager.handlers:
            raise HTTPException(
                status_code=404,
                detail=f"Handler '{handler_name}' not found"
            )
        
        # Remove handler
        del event_manager.handlers[handler_name]
        
        return {
            "message": f"Handler '{handler_name}' removed successfully",
            "remaining_handlers": list(event_manager.handlers.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing event handler: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to remove event handler"
        )


@router.get("/recent", response_model=List[EventResponse])
async def get_recent_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of events"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    event_manager: EventBusManager = Depends(get_event_manager),
    current_user: User = Depends(get_current_user)
):
    """
    Get recent events from the event bus.
    
    Returns recent events, optionally filtered by type and time range.
    """
    try:
        if not event_manager.event_bus:
            raise HTTPException(
                status_code=503,
                detail="Event bus not initialized"
            )
        
        # Calculate time range
        to_timestamp = datetime.now(timezone.utc)
        from_timestamp = to_timestamp - timedelta(hours=hours)
        
        # If no event type specified, get events for all types
        event_types_to_query = []
        if event_type:
            # Validate event type
            valid_types = [et.value for et in EventType]
            if event_type not in valid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid event type. Must be one of: {valid_types}"
                )
            event_types_to_query = [event_type]
        else:
            event_types_to_query = [et.value for et in EventType]
        
        # Collect events from all types
        all_events = []
        
        for et in event_types_to_query:
            count = 0
            async for event in event_manager.event_bus.replay_events(
                event_type=et,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp
            ):
                if len(all_events) >= limit:
                    break
                
                all_events.append(EventResponse(
                    id=event.id,
                    event_type=event.event_type,
                    payload=event.payload,
                    timestamp=event.timestamp,
                    source=event.source,
                    correlation_id=event.correlation_id,
                    metadata=event.metadata
                ))
        
        # Sort by timestamp (most recent first) and limit
        all_events.sort(key=lambda x: x.timestamp, reverse=True)
        return all_events[:limit]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recent events: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve recent events"
        )