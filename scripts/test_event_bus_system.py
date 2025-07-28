#!/usr/bin/env python3
"""
Test script for the Event Bus System

This script tests both Redis and Kafka event bus implementations
to ensure they work correctly with the AI Opportunity Browser.
"""

import asyncio
import os
import sys
import logging
from datetime import datetime, timezone
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.event_bus import EventType, EventHandler
from shared.event_bus_factory import EventBusFactory, EventBusType, validate_event_bus_config
from shared.event_publishers import (
    OpportunityEventPublisher,
    UserEventPublisher,
    AgentEventPublisher,
    MarketSignalEventPublisher,
    SystemEventPublisher,
    BatchEventPublisher,
    event_publishing_context,
    batch_event_publishing_context
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestEventHandler(EventHandler):
    """Test event handler for verification."""
    
    def __init__(self, handler_id: str):
        super().__init__(handler_id)
        self.received_events = []
    
    async def handle(self, event) -> None:
        """Handle received events."""
        self.received_events.append(event)
        self.logger.info(f"Received event: {event.event_type} (ID: {event.id})")


async def test_redis_event_bus():
    """Test Redis-based event bus."""
    logger.info("=== Testing Redis Event Bus ===")
    
    try:
        # Create Redis event bus
        event_bus = EventBusFactory.create_event_bus("redis")
        await event_bus.initialize()
        
        # Create test handler
        handler = TestEventHandler("redis_test_handler")
        
        # Subscribe to events
        await event_bus.subscribe_to_events([
            EventType.OPPORTUNITY_CREATED,
            EventType.USER_REGISTERED,
            EventType.AGENT_STARTED
        ], handler)
        
        # Wait a moment for subscription to be ready
        await asyncio.sleep(1)
        
        # Publish test events
        event_ids = []
        
        # Test opportunity event
        event_id = await event_bus.publish_event(
            EventType.OPPORTUNITY_CREATED,
            {
                "opportunity_id": "test-opp-1",
                "title": "Test AI Opportunity",
                "description": "A test opportunity for Redis event bus"
            },
            source="test_script"
        )
        event_ids.append(event_id)
        
        # Test user event
        event_id = await event_bus.publish_event(
            EventType.USER_REGISTERED,
            {
                "user_id": "test-user-1",
                "email": "test@example.com",
                "username": "testuser"
            },
            source="test_script"
        )
        event_ids.append(event_id)
        
        # Test agent event
        event_id = await event_bus.publish_event(
            EventType.AGENT_STARTED,
            {
                "agent_id": "test-agent-1",
                "agent_type": "monitoring_agent",
                "config": {"test": True}
            },
            source="test_script"
        )
        event_ids.append(event_id)
        
        # Wait for events to be processed
        await asyncio.sleep(2)
        
        # Verify events were received
        logger.info(f"Published {len(event_ids)} events")
        logger.info(f"Received {len(handler.received_events)} events")
        
        # Test event replay
        logger.info("Testing event replay...")
        replay_count = 0
        async for event in event_bus.replay_events(
            EventType.OPPORTUNITY_CREATED,
            datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        ):
            replay_count += 1
            logger.info(f"Replayed event: {event.event_type} (ID: {event.id})")
        
        logger.info(f"Replayed {replay_count} events")
        
        # Get statistics
        stats = await event_bus.get_event_stats()
        logger.info(f"Event bus stats: {stats}")
        
        await event_bus.shutdown()
        logger.info("Redis event bus test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Redis event bus test failed: {e}")
        return False


async def test_kafka_event_bus():
    """Test Kafka-based event bus."""
    logger.info("=== Testing Kafka Event Bus ===")
    
    try:
        # Check if Kafka dependencies are available
        try:
            from shared.event_bus_kafka import KAFKA_AVAILABLE
            if not KAFKA_AVAILABLE:
                logger.warning("Kafka dependencies not available, skipping Kafka test")
                return False
        except ImportError:
            logger.warning("Kafka module not available, skipping Kafka test")
            return False
        
        # Check if Kafka is available
        kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        logger.info(f"Attempting to connect to Kafka at: {kafka_servers}")
        
        # Create Kafka event bus
        event_bus = EventBusFactory.create_event_bus(
            "kafka",
            bootstrap_servers=kafka_servers
        )
        await event_bus.initialize()
        
        # Create test handler
        handler = TestEventHandler("kafka_test_handler")
        
        # Subscribe to events
        await event_bus.subscribe_to_events([
            EventType.OPPORTUNITY_CREATED,
            EventType.USER_REGISTERED,
            EventType.AGENT_STARTED
        ], handler)
        
        # Wait a moment for subscription to be ready
        await asyncio.sleep(2)
        
        # Publish test events with partition keys
        event_ids = []
        
        # Test opportunity event
        event_id = await event_bus.publish_event(
            EventType.OPPORTUNITY_CREATED,
            {
                "opportunity_id": "test-opp-kafka-1",
                "title": "Test AI Opportunity (Kafka)",
                "description": "A test opportunity for Kafka event bus"
            },
            source="test_script",
            partition_key="test-opp-kafka-1"
        )
        event_ids.append(event_id)
        
        # Test user event
        event_id = await event_bus.publish_event(
            EventType.USER_REGISTERED,
            {
                "user_id": "test-user-kafka-1",
                "email": "kafka-test@example.com",
                "username": "kafkatestuser"
            },
            source="test_script",
            partition_key="test-user-kafka-1"
        )
        event_ids.append(event_id)
        
        # Test agent event
        event_id = await event_bus.publish_event(
            EventType.AGENT_STARTED,
            {
                "agent_id": "test-agent-kafka-1",
                "agent_type": "monitoring_agent",
                "config": {"test": True, "backend": "kafka"}
            },
            source="test_script",
            partition_key="test-agent-kafka-1"
        )
        event_ids.append(event_id)
        
        # Wait for events to be processed
        await asyncio.sleep(3)
        
        # Verify events were received
        logger.info(f"Published {len(event_ids)} events to Kafka")
        logger.info(f"Received {len(handler.received_events)} events from Kafka")
        
        # Get statistics
        stats = await event_bus.get_event_stats()
        logger.info(f"Kafka event bus stats: {stats}")
        
        await event_bus.shutdown()
        logger.info("Kafka event bus test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Kafka event bus test failed: {e}")
        logger.info("This is expected if Kafka is not running")
        return False


async def test_event_publishers():
    """Test high-level event publishers."""
    logger.info("=== Testing Event Publishers ===")
    
    try:
        # Test opportunity publisher
        opp_publisher = OpportunityEventPublisher()
        event_id = await opp_publisher.opportunity_created(
            opportunity_id="test-opp-pub-1",
            title="Test Opportunity via Publisher",
            description="Testing the opportunity event publisher",
            ai_solution_type="nlp",
            market_size_estimate=1000000.0,
            created_by="test-user"
        )
        logger.info(f"Published opportunity event: {event_id}")
        
        # Test user publisher
        user_publisher = UserEventPublisher()
        event_id = await user_publisher.user_registered(
            user_id="test-user-pub-1",
            email="publisher-test@example.com",
            username="publishertest",
            user_type="expert"
        )
        logger.info(f"Published user event: {event_id}")
        
        # Test agent publisher
        agent_publisher = AgentEventPublisher()
        event_id = await agent_publisher.agent_task_completed(
            agent_id="test-agent-pub-1",
            task_id="test-task-1",
            task_type="signal_analysis",
            duration_seconds=5.5,
            success=True,
            result={"signals_processed": 10, "opportunities_found": 2}
        )
        logger.info(f"Published agent event: {event_id}")
        
        # Test market signal publisher
        signal_publisher = MarketSignalEventPublisher()
        event_id = await signal_publisher.signal_detected(
            signal_id="test-signal-pub-1",
            source="reddit",
            signal_type="pain_point",
            content="Users complaining about manual data entry",
            confidence=0.85,
            engagement_metrics={"upvotes": 50, "comments": 15}
        )
        logger.info(f"Published signal event: {event_id}")
        
        # Test system publisher
        system_publisher = SystemEventPublisher()
        event_id = await system_publisher.health_check(
            component="event_bus",
            status="healthy",
            response_time_ms=25.5,
            details={"connections": 5, "queue_size": 0}
        )
        logger.info(f"Published system event: {event_id}")
        
        logger.info("Event publishers test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Event publishers test failed: {e}")
        return False


async def test_batch_publishing():
    """Test batch event publishing."""
    logger.info("=== Testing Batch Event Publishing ===")
    
    try:
        async with batch_event_publishing_context("test_batch_script") as batch_publisher:
            # Add multiple events to batch
            for i in range(5):
                await batch_publisher.add_event(
                    EventType.OPPORTUNITY_CREATED,
                    {
                        "opportunity_id": f"batch-opp-{i}",
                        "title": f"Batch Opportunity {i}",
                        "description": f"Test batch opportunity number {i}"
                    },
                    partition_key=f"batch-opp-{i}"
                )
            
            # Add different event types
            await batch_publisher.add_event(
                EventType.USER_REGISTERED,
                {
                    "user_id": "batch-user-1",
                    "email": "batch@example.com",
                    "username": "batchuser"
                },
                partition_key="batch-user-1"
            )
            
            # Events will be automatically flushed when exiting context
        
        logger.info("Batch publishing test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Batch publishing test failed: {e}")
        return False


async def test_event_publishing_context():
    """Test event publishing context manager."""
    logger.info("=== Testing Event Publishing Context ===")
    
    try:
        async with event_publishing_context("test_context_script", "ctx-correlation-123") as publisher:
            # Publish events with automatic correlation tracking
            event_id = await publisher.publish(
                EventType.OPPORTUNITY_VALIDATED,
                {
                    "opportunity_id": "ctx-opp-1",
                    "validation_id": "ctx-val-1",
                    "validator_id": "ctx-validator-1",
                    "validation_score": 8.5,
                    "validation_type": "market_demand"
                },
                metadata={"test_context": True},
                partition_key="ctx-opp-1"
            )
            logger.info(f"Published context event: {event_id}")
        
        logger.info("Event publishing context test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Event publishing context test failed: {e}")
        return False


async def main():
    """Run all event bus tests."""
    logger.info("Starting Event Bus System Tests")
    
    # Validate configuration
    if not validate_event_bus_config():
        logger.error("Event bus configuration validation failed")
        return False
    
    results = []
    
    # Test Redis event bus
    results.append(await test_redis_event_bus())
    
    # Test Kafka event bus (may fail if Kafka not available)
    results.append(await test_kafka_event_bus())
    
    # Test event publishers
    results.append(await test_event_publishers())
    
    # Test batch publishing
    results.append(await test_batch_publishing())
    
    # Test publishing context
    results.append(await test_event_publishing_context())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    logger.info(f"\n=== Test Summary ===")
    logger.info(f"Passed: {passed}/{total}")
    logger.info(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        logger.info("All event bus tests passed!")
        return True
    else:
        logger.warning("Some event bus tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)