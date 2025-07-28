"""
Event Bus Configuration for AI Opportunity Browser

This module provides configuration and initialization utilities for the event bus system.
"""

import os
import asyncio
import logging
from typing import List, Optional
from contextlib import asynccontextmanager

from .event_bus import EventType
from .event_bus_factory import get_global_event_bus, EventBusConfig, validate_event_bus_config
from .event_handlers import (
    OpportunityEventHandler,
    UserEventHandler,
    AgentEventHandler,
    SystemEventHandler,
    MarketSignalEventHandler
)

logger = logging.getLogger(__name__)


class EventBusManagerConfig:
    """Configuration for the event bus manager."""
    
    def __init__(self):
        self.enable_event_handlers = os.getenv("ENABLE_EVENT_HANDLERS", "true").lower() == "true"
        
        # Event handler configuration
        self.enabled_handlers = self._parse_enabled_handlers()
    
    def _parse_enabled_handlers(self) -> List[str]:
        """Parse enabled event handlers from environment."""
        handlers_env = os.getenv("ENABLED_EVENT_HANDLERS", "all")
        
        if handlers_env.lower() == "all":
            return ["opportunity", "user", "agent", "system", "market_signal"]
        
        return [h.strip() for h in handlers_env.split(",") if h.strip()]


class EventBusManager:
    """Manager for event bus initialization and lifecycle."""
    
    def __init__(self, config: Optional[EventBusManagerConfig] = None):
        self.config = config or EventBusManagerConfig()
        self.event_bus = None
        self.handlers = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the event bus and register handlers."""
        if self._initialized:
            logger.warning("Event bus already initialized")
            return
        
        try:
            # Initialize event bus using factory
            self.event_bus = await get_global_event_bus()
            
            # Register event handlers if enabled
            if self.config.enable_event_handlers:
                await self._register_handlers()
            
            self._initialized = True
            logger.info("Event bus manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize event bus manager: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the event bus and cleanup resources."""
        if not self._initialized:
            return
        
        try:
            if self.event_bus:
                await self.event_bus.shutdown()
            
            self.handlers.clear()
            self._initialized = False
            logger.info("Event bus manager shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during event bus shutdown: {e}")
    
    async def _register_handlers(self) -> None:
        """Register event handlers based on configuration."""
        handler_configs = {
            "opportunity": {
                "handler": OpportunityEventHandler(),
                "events": [
                    EventType.OPPORTUNITY_CREATED,
                    EventType.OPPORTUNITY_UPDATED,
                    EventType.OPPORTUNITY_DELETED,
                    EventType.OPPORTUNITY_VALIDATED
                ]
            },
            "user": {
                "handler": UserEventHandler(),
                "events": [
                    EventType.USER_REGISTERED,
                    EventType.USER_PROFILE_UPDATED,
                    EventType.USER_REPUTATION_CHANGED
                ]
            },
            "agent": {
                "handler": AgentEventHandler(),
                "events": [
                    EventType.AGENT_STARTED,
                    EventType.AGENT_STOPPED,
                    EventType.AGENT_ERROR,
                    EventType.AGENT_TASK_COMPLETED
                ]
            },
            "system": {
                "handler": SystemEventHandler(),
                "events": [
                    EventType.SYSTEM_HEALTH_CHECK,
                    EventType.SYSTEM_ERROR,
                    EventType.SYSTEM_MAINTENANCE
                ]
            },
            "market_signal": {
                "handler": MarketSignalEventHandler(),
                "events": [
                    EventType.SIGNAL_DETECTED,
                    EventType.SIGNAL_PROCESSED,
                    EventType.SIGNAL_CLUSTERED
                ]
            }
        }
        
        for handler_name in self.config.enabled_handlers:
            if handler_name in handler_configs:
                config = handler_configs[handler_name]
                handler = config["handler"]
                events = config["events"]
                
                await self.event_bus.subscribe_to_events(events, handler)
                self.handlers[handler_name] = handler
                
                logger.info(f"Registered {handler_name} event handler for {len(events)} event types")
            else:
                logger.warning(f"Unknown event handler: {handler_name}")
    
    async def get_stats(self) -> dict:
        """Get event bus statistics."""
        if not self.event_bus:
            return {"error": "Event bus not initialized"}
        
        stats = await self.event_bus.get_event_stats()
        stats["registered_handlers"] = list(self.handlers.keys())
        stats["config"] = {
            "handlers_enabled": self.config.enable_event_handlers,
            "enabled_handlers": self.config.enabled_handlers
        }
        
        return stats


# Global event bus manager instance
_event_bus_manager: Optional[EventBusManager] = None


async def get_event_bus_manager() -> EventBusManager:
    """Get the global event bus manager instance."""
    global _event_bus_manager
    if _event_bus_manager is None:
        _event_bus_manager = EventBusManager()
        await _event_bus_manager.initialize()
    return _event_bus_manager


@asynccontextmanager
async def event_bus_lifespan():
    """Context manager for event bus lifecycle management."""
    manager = None
    try:
        manager = await get_event_bus_manager()
        yield manager
    finally:
        if manager:
            await manager.shutdown()


# Convenience functions for common operations
# Import convenience functions from event_publishers
from .event_publishers import (
    publish_opportunity_created,
    publish_user_registered,
    publish_agent_task_completed,
    publish_system_health_check,
    publish_signal_detected
)