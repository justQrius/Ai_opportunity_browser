#!/usr/bin/env python3
"""
Event Bus System Demo

This script demonstrates the key features of the AI Opportunity Browser
event bus system including publishing, subscribing, and event replay.
"""

import asyncio
import os
import sys
import logging
from datetime import datetime, timezone, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.event_bus import EventType, EventHandler
from shared.event_publishers import (
    OpportunityEventPublisher,
    UserEventPublisher,
    AgentEventPublisher,
    MarketSignalEventPublisher,
    SystemEventPublisher,
    event_publishing_context,
    batch_event_publishing_context
)
from shared.event_config import get_event_bus_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DemoEventHandler(EventHandler):
    """Demo event handler that logs all received events."""
    
    def __init__(self, handler_name: str):
        super().__init__(handler_name)
        self.received_events = []
    
    async def handle(self, event) -> None:
        """Handle received events."""
        self.received_events.append(event)
        self.logger.info(
            f"📨 Received {event.event_type} event (ID: {event.id[:8]}...)"
        )
        
        # Log some payload details based on event type
        if event.event_type == EventType.OPPORTUNITY_CREATED:
            title = event.payload.get('title', 'Unknown')
            self.logger.info(f"   📋 Opportunity: {title}")
        elif event.event_type == EventType.USER_REGISTERED:
            email = event.payload.get('email', 'Unknown')
            self.logger.info(f"   👤 User: {email}")
        elif event.event_type == EventType.AGENT_TASK_COMPLETED:
            task_type = event.payload.get('task_type', 'Unknown')
            duration = event.payload.get('duration_seconds', 0)
            self.logger.info(f"   🤖 Task: {task_type} ({duration:.2f}s)")
        elif event.event_type == EventType.SIGNAL_DETECTED:
            source = event.payload.get('source', 'Unknown')
            confidence = event.payload.get('confidence', 0)
            self.logger.info(f"   📡 Signal from {source} (confidence: {confidence:.2f})")


async def demo_basic_publishing():
    """Demonstrate basic event publishing."""
    logger.info("🚀 Demo 1: Basic Event Publishing")
    
    # Create event publishers
    opp_publisher = OpportunityEventPublisher()
    user_publisher = UserEventPublisher()
    agent_publisher = AgentEventPublisher()
    signal_publisher = MarketSignalEventPublisher()
    system_publisher = SystemEventPublisher()
    
    # Publish various events
    logger.info("📤 Publishing opportunity event...")
    await opp_publisher.opportunity_created(
        opportunity_id="demo-opp-1",
        title="AI-Powered Code Review Assistant",
        description="Automated code review using machine learning",
        ai_solution_type="nlp",
        market_size_estimate=2500000.0,
        created_by="demo-user"
    )
    
    logger.info("📤 Publishing user event...")
    await user_publisher.user_registered(
        user_id="demo-user-1",
        email="demo@example.com",
        username="demouser",
        user_type="developer"
    )
    
    logger.info("📤 Publishing agent event...")
    await agent_publisher.agent_task_completed(
        agent_id="demo-agent-1",
        task_id="demo-task-1",
        task_type="market_analysis",
        duration_seconds=15.5,
        success=True,
        result={"opportunities_found": 3, "signals_processed": 25}
    )
    
    logger.info("📤 Publishing signal event...")
    await signal_publisher.signal_detected(
        signal_id="demo-signal-1",
        source="reddit",
        signal_type="pain_point",
        content="Developers struggling with manual code reviews",
        confidence=0.87,
        engagement_metrics={"upvotes": 45, "comments": 12}
    )
    
    logger.info("📤 Publishing system event...")
    await system_publisher.health_check(
        component="event_bus",
        status="healthy",
        response_time_ms=12.3,
        details={"active_consumers": 3, "queue_size": 0}
    )
    
    logger.info("✅ Basic publishing demo completed\n")


async def demo_event_subscription():
    """Demonstrate event subscription and handling."""
    logger.info("🎯 Demo 2: Event Subscription and Handling")
    
    # Get event bus manager
    manager = await get_event_bus_manager()
    event_bus = manager.event_bus
    
    # Create demo handler
    handler = DemoEventHandler("demo_handler")
    
    # Subscribe to multiple event types
    await event_bus.subscribe_to_events([
        EventType.OPPORTUNITY_CREATED,
        EventType.USER_REGISTERED,
        EventType.AGENT_TASK_COMPLETED,
        EventType.SIGNAL_DETECTED
    ], handler)
    
    logger.info("👂 Subscribed to events, publishing test events...")
    
    # Wait a moment for subscription to be ready
    await asyncio.sleep(1)
    
    # Publish some test events
    async with event_publishing_context("demo_subscription") as publisher:
        await publisher.publish(
            EventType.OPPORTUNITY_CREATED,
            {
                "opportunity_id": "sub-demo-opp-1",
                "title": "Smart Document Summarizer",
                "description": "AI-powered document summarization tool"
            }
        )
        
        await publisher.publish(
            EventType.USER_REGISTERED,
            {
                "user_id": "sub-demo-user-1",
                "email": "subscriber@example.com",
                "username": "subscriber"
            }
        )
    
    # Wait for events to be processed
    await asyncio.sleep(2)
    
    logger.info(f"📊 Handler received {len(handler.received_events)} events")
    logger.info("✅ Event subscription demo completed\n")


async def demo_batch_publishing():
    """Demonstrate batch event publishing."""
    logger.info("📦 Demo 3: Batch Event Publishing")
    
    async with batch_event_publishing_context("demo_batch") as batch_publisher:
        logger.info("📤 Adding events to batch...")
        
        # Add multiple events to batch
        for i in range(5):
            await batch_publisher.add_event(
                EventType.SIGNAL_DETECTED,
                {
                    "signal_id": f"batch-signal-{i}",
                    "source": "github",
                    "signal_type": "feature_request",
                    "content": f"Feature request #{i} from GitHub issues",
                    "confidence": 0.75 + (i * 0.05)
                }
            )
        
        # Add different event type
        await batch_publisher.add_event(
            EventType.OPPORTUNITY_VALIDATED,
            {
                "opportunity_id": "batch-opp-1",
                "validation_id": "batch-val-1",
                "validator_id": "batch-validator-1",
                "validation_score": 8.5,
                "validation_type": "technical_feasibility"
            }
        )
        
        logger.info("📦 Batch will be automatically flushed when exiting context...")
    
    logger.info("✅ Batch publishing demo completed\n")


async def demo_event_replay():
    """Demonstrate event replay functionality."""
    logger.info("⏪ Demo 4: Event Replay")
    
    # Get event bus
    manager = await get_event_bus_manager()
    event_bus = manager.event_bus
    
    # Replay events from the last hour
    from_time = datetime.now(timezone.utc) - timedelta(hours=1)
    
    logger.info(f"🔍 Replaying OPPORTUNITY_CREATED events from {from_time.strftime('%H:%M:%S')}...")
    
    replay_count = 0
    async for event in event_bus.replay_events(
        EventType.OPPORTUNITY_CREATED,
        from_time
    ):
        replay_count += 1
        title = event.payload.get('title', 'Unknown')
        timestamp = event.timestamp.strftime('%H:%M:%S')
        logger.info(f"   ⏪ [{timestamp}] {title} (ID: {event.id[:8]}...)")
        
        # Limit output for demo
        if replay_count >= 5:
            break
    
    if replay_count == 0:
        logger.info("   📭 No events found in replay window")
    else:
        logger.info(f"📊 Replayed {replay_count} events")
    
    logger.info("✅ Event replay demo completed\n")


async def demo_event_statistics():
    """Demonstrate event bus statistics."""
    logger.info("📈 Demo 5: Event Bus Statistics")
    
    # Get event bus manager
    manager = await get_event_bus_manager()
    
    # Get comprehensive stats
    stats = await manager.get_stats()
    
    logger.info("📊 Event Bus Statistics:")
    logger.info(f"   📈 Total events: {stats.get('total_events', 0)}")
    logger.info(f"   🎯 Active subscribers: {stats.get('active_subscribers', 0)}")
    logger.info(f"   🔧 Registered handlers: {len(stats.get('registered_handlers', []))}")
    
    # Show events by type
    events_by_type = stats.get('events_by_type', {})
    if events_by_type:
        logger.info("   📋 Events by type:")
        for event_type, count in events_by_type.items():
            logger.info(f"      • {event_type}: {count}")
    
    # Show configuration
    config = stats.get('config', {})
    if config:
        logger.info("   ⚙️  Configuration:")
        logger.info(f"      • Handlers enabled: {config.get('handlers_enabled', False)}")
        logger.info(f"      • Enabled handlers: {config.get('enabled_handlers', [])}")
    
    logger.info("✅ Statistics demo completed\n")


async def main():
    """Run all event bus demos."""
    logger.info("🎪 AI Opportunity Browser - Event Bus System Demo")
    logger.info("=" * 60)
    
    try:
        # Run all demos
        await demo_basic_publishing()
        await demo_event_subscription()
        await demo_batch_publishing()
        await demo_event_replay()
        await demo_event_statistics()
        
        logger.info("🎉 All demos completed successfully!")
        logger.info("=" * 60)
        
        # Final summary
        logger.info("📝 Demo Summary:")
        logger.info("   ✅ Basic event publishing")
        logger.info("   ✅ Event subscription and handling")
        logger.info("   ✅ Batch event publishing")
        logger.info("   ✅ Event replay functionality")
        logger.info("   ✅ Event bus statistics")
        logger.info("\n💡 The event bus system is ready for production use!")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())