"""
Kafka-based Event Bus Implementation for AI Opportunity Browser

This module provides a Kafka-based event bus implementation as an alternative
to the Redis-based event bus, offering better scalability and durability
for high-throughput event streaming scenarios.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from dataclasses import asdict

try:
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
    from aiokafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    AIOKafkaProducer = None
    AIOKafkaConsumer = None
    KafkaError = Exception

from .event_bus import Event, EventHandler, EventType

logger = logging.getLogger(__name__)


class KafkaEventBus:
    """
    Kafka-based event bus for high-throughput, durable event streaming.
    
    Provides event publishing, subscription, and replay capabilities
    with Kafka's built-in durability and partitioning features.
    """
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic_prefix: str = "ai-opportunity",
        consumer_group: str = "ai-opportunity-consumers",
        max_retries: int = 3,
        retention_ms: int = 604800000,  # 7 days
        partitions: int = 3,
        replication_factor: int = 1
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic_prefix = topic_prefix
        self.consumer_group = consumer_group
        self.max_retries = max_retries
        self.retention_ms = retention_ms
        self.partitions = partitions
        self.replication_factor = replication_factor
        
        self._producer: Optional[AIOKafkaProducer] = None
        self._consumers: Dict[str, AIOKafkaConsumer] = {}
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._consumer_tasks: List[asyncio.Task] = []
        self._running = False
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> None:
        """Initialize the Kafka event bus and create producer."""
        if not KAFKA_AVAILABLE:
            raise RuntimeError("Kafka dependencies not available. Install with: pip install aiokafka kafka-python")
        
        try:
            # Initialize producer
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                retry_backoff_ms=1000,
                request_timeout_ms=30000,
                max_request_size=1048576,  # 1MB
                compression_type='gzip'
            )
            
            await self._producer.start()
            
            # Create topics for all event types
            await self._create_topics()
            
            self.logger.info("Kafka event bus initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Kafka event bus: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the Kafka event bus and cleanup resources."""
        self._running = False
        
        # Cancel consumer tasks
        for task in self._consumer_tasks:
            task.cancel()
        
        if self._consumer_tasks:
            await asyncio.gather(*self._consumer_tasks, return_exceptions=True)
        
        # Stop consumers
        for consumer in self._consumers.values():
            await consumer.stop()
        
        # Stop producer
        if self._producer:
            await self._producer.stop()
        
        self.logger.info("Kafka event bus shutdown completed")
    
    async def _create_topics(self) -> None:
        """Create Kafka topics for all event types."""
        try:
            try:
                from kafka.admin import KafkaAdminClient, NewTopic
                from kafka.errors import TopicAlreadyExistsError
            except ImportError:
                self.logger.warning("kafka-python not available, skipping topic creation")
                return
            
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                client_id='ai-opportunity-admin'
            )
            
            topics = []
            for event_type in EventType:
                topic_name = self._get_topic_name(str(event_type))
                topic = NewTopic(
                    name=topic_name,
                    num_partitions=self.partitions,
                    replication_factor=self.replication_factor,
                    topic_configs={
                        'retention.ms': str(self.retention_ms),
                        'cleanup.policy': 'delete',
                        'compression.type': 'gzip'
                    }
                )
                topics.append(topic)
            
            try:
                admin_client.create_topics(topics, validate_only=False)
                self.logger.info(f"Created {len(topics)} Kafka topics")
            except TopicAlreadyExistsError:
                self.logger.info("Kafka topics already exist")
            
            admin_client.close()
            
        except Exception as e:
            self.logger.warning(f"Could not create Kafka topics: {e}")
    
    def _get_topic_name(self, event_type: str) -> str:
        """Get Kafka topic name for an event type."""
        return f"{self.topic_prefix}.{event_type.replace('.', '-')}"
    
    async def publish_event(
        self,
        event_type: Union[str, EventType],
        payload: Dict[str, Any],
        source: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        partition_key: Optional[str] = None
    ) -> str:
        """
        Publish an event to Kafka.
        
        Args:
            event_type: Type of event to publish
            payload: Event data payload
            source: Source service/component publishing the event
            correlation_id: Optional correlation ID for request tracing
            metadata: Optional additional metadata
            partition_key: Optional key for partitioning (defaults to event_id)
            
        Returns:
            Event ID for tracking
        """
        if not self._producer:
            raise RuntimeError("Kafka event bus not initialized")
        
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
            topic_name = self._get_topic_name(str(event_type))
            key = partition_key or event_id
            
            # Send to Kafka
            await self._producer.send_and_wait(
                topic_name,
                value=event.to_dict(),
                key=key
            )
            
            self.logger.debug(f"Published event {event_id} to topic {topic_name}")
            return event_id
            
        except Exception as e:
            self.logger.error(f"Failed to publish event to Kafka: {e}")
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
        if not self._producer:
            raise RuntimeError("Kafka event bus not initialized")
        
        # Register handler for event types
        for event_type in event_types:
            event_type_str = str(event_type)
            if event_type_str not in self._subscribers:
                self._subscribers[event_type_str] = []
            self._subscribers[event_type_str].append(handler)
        
        # Create consumer for these event types if not exists
        topics = [self._get_topic_name(str(et)) for et in event_types]
        consumer_key = f"{handler.handler_id}_{hash(tuple(sorted(topics)))}"
        
        if consumer_key not in self._consumers:
            consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=f"{self.consumer_group}-{handler.handler_id}",
                auto_offset_reset='latest',
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                consumer_timeout_ms=1000
            )
            
            await consumer.start()
            self._consumers[consumer_key] = consumer
            
            # Start consumer task
            if not self._running:
                self._running = True
            
            task = asyncio.create_task(
                self._consumer_loop(consumer, consumer_key)
            )
            self._consumer_tasks.append(task)
        
        self.logger.info(
            f"Subscribed handler {handler.handler_id} to Kafka topics: {topics}"
        )
    
    async def _consumer_loop(self, consumer: AIOKafkaConsumer, consumer_key: str) -> None:
        """Consumer loop for processing Kafka messages."""
        try:
            self.logger.info(f"Started Kafka consumer loop: {consumer_key}")
            
            async for message in consumer:
                if not self._running:
                    break
                
                try:
                    # Parse event data
                    event_data = message.value
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
                    self.logger.error(f"Error processing Kafka message: {e}")
                    
        except asyncio.CancelledError:
            self.logger.info(f"Kafka consumer loop cancelled: {consumer_key}")
        except Exception as e:
            self.logger.error(f"Error in Kafka consumer loop {consumer_key}: {e}")
    
    async def replay_events(
        self,
        event_type: Union[str, EventType],
        from_timestamp: datetime,
        to_timestamp: Optional[datetime] = None,
        partition: Optional[int] = None
    ) -> AsyncIterator[Event]:
        """
        Replay events from Kafka topic based on timestamp.
        
        Args:
            event_type: Type of events to replay
            from_timestamp: Start timestamp for replay
            to_timestamp: End timestamp for replay (optional)
            partition: Specific partition to replay from (optional)
            
        Yields:
            Event objects in order
        """
        topic_name = self._get_topic_name(str(event_type))
        
        try:
            # Create a dedicated consumer for replay
            consumer = AIOKafkaConsumer(
                topic_name,
                bootstrap_servers=self.bootstrap_servers,
                group_id=f"replay-{uuid.uuid4()}",
                auto_offset_reset='earliest',
                enable_auto_commit=False,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            
            await consumer.start()
            
            try:
                # Get topic partitions
                partitions = consumer.partitions_for_topic(topic_name)
                if not partitions:
                    self.logger.warning(f"No partitions found for topic {topic_name}")
                    return
                
                # Seek to timestamp
                from_ts_ms = int(from_timestamp.timestamp() * 1000)
                to_ts_ms = int(to_timestamp.timestamp() * 1000) if to_timestamp else None
                
                target_partitions = [partition] if partition is not None else list(partitions)
                
                for part in target_partitions:
                    tp = (topic_name, part)
                    
                    # Get offset for timestamp
                    offsets = await consumer.offsets_for_times({tp: from_ts_ms})
                    if tp in offsets and offsets[tp]:
                        consumer.seek(tp, offsets[tp].offset)
                
                # Read messages
                async for message in consumer:
                    try:
                        event_data = message.value
                        event = Event.from_dict(event_data)
                        
                        # Check timestamp bounds
                        if event.timestamp < from_timestamp:
                            continue
                        
                        if to_timestamp and event.timestamp > to_timestamp:
                            break
                        
                        yield event
                        
                    except Exception as e:
                        self.logger.error(f"Error parsing replayed event: {e}")
                        continue
            
            finally:
                await consumer.stop()
                
        except Exception as e:
            self.logger.error(f"Error replaying events from Kafka: {e}")
            raise
    
    async def get_event_stats(self) -> Dict[str, Any]:
        """Get statistics about Kafka topics and consumers."""
        try:
            try:
                from kafka import KafkaConsumer
                from kafka.structs import TopicPartition
            except ImportError:
                return {
                    "error": "kafka-python not available",
                    "active_consumers": len(self._consumers),
                    "consumer_tasks": len(self._consumer_tasks),
                    "registered_handlers": len(self._subscribers)
                }
            
            # Create a simple consumer to get metadata
            consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                consumer_timeout_ms=1000
            )
            
            stats = {
                "total_topics": 0,
                "topics": {},
                "active_consumers": len(self._consumers),
                "consumer_tasks": len(self._consumer_tasks),
                "registered_handlers": len(self._subscribers)
            }
            
            # Get topic metadata
            metadata = consumer.list_consumer_groups()
            topics = consumer.topics()
            
            for topic in topics:
                if topic.startswith(self.topic_prefix):
                    partitions = consumer.partitions_for_topic(topic)
                    if partitions:
                        stats["topics"][topic] = {
                            "partitions": len(partitions),
                            "partition_ids": list(partitions)
                        }
                        stats["total_topics"] += 1
            
            consumer.close()
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting Kafka stats: {e}")
            return {
                "error": str(e),
                "active_consumers": len(self._consumers),
                "consumer_tasks": len(self._consumer_tasks),
                "registered_handlers": len(self._subscribers)
            }