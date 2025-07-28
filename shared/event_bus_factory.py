"""
Event Bus Factory for AI Opportunity Browser

This module provides a factory for creating event bus instances
based on configuration, supporting both Redis and Kafka backends.
"""

import os
import logging
from typing import Optional, Union
from enum import Enum

from .event_bus import EventBus
from .event_bus_kafka import KafkaEventBus

logger = logging.getLogger(__name__)


class EventBusType(str, Enum):
    """Supported event bus types."""
    REDIS = "redis"
    KAFKA = "kafka"


class EventBusFactory:
    """Factory for creating event bus instances."""
    
    @staticmethod
    def create_event_bus(
        bus_type: Optional[Union[str, EventBusType]] = None,
        **kwargs
    ) -> Union[EventBus, KafkaEventBus]:
        """
        Create an event bus instance based on configuration.
        
        Args:
            bus_type: Type of event bus to create (redis/kafka)
            **kwargs: Additional configuration parameters
            
        Returns:
            Event bus instance
        """
        # Determine bus type from environment or parameter
        if bus_type is None:
            bus_type = os.getenv("EVENT_BUS_TYPE", "redis").lower()
        
        bus_type_str = str(bus_type).lower()
        
        if bus_type_str == "redis":
            return EventBusFactory._create_redis_event_bus(**kwargs)
        elif bus_type_str == "kafka":
            return EventBusFactory._create_kafka_event_bus(**kwargs)
        else:
            raise ValueError(f"Unsupported event bus type: {bus_type_str}")
    
    @staticmethod
    def _create_redis_event_bus(**kwargs) -> EventBus:
        """Create a Redis-based event bus."""
        config = {
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            "event_ttl": int(os.getenv("EVENT_TTL_SECONDS", "604800")),  # 7 days
            "max_retries": int(os.getenv("EVENT_MAX_RETRIES", "3"))
        }
        config.update(kwargs)
        
        logger.info("Creating Redis event bus with config: %s", 
                   {k: v for k, v in config.items() if 'url' not in k.lower()})
        
        return EventBus(**config)
    
    @staticmethod
    def _create_kafka_event_bus(**kwargs) -> KafkaEventBus:
        """Create a Kafka-based event bus."""
        config = {
            "bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            "topic_prefix": os.getenv("KAFKA_TOPIC_PREFIX", "ai-opportunity"),
            "consumer_group": os.getenv("KAFKA_CONSUMER_GROUP", "ai-opportunity-consumers"),
            "max_retries": int(os.getenv("EVENT_MAX_RETRIES", "3")),
            "retention_ms": int(os.getenv("KAFKA_RETENTION_MS", "604800000")),  # 7 days
            "partitions": int(os.getenv("KAFKA_PARTITIONS", "3")),
            "replication_factor": int(os.getenv("KAFKA_REPLICATION_FACTOR", "1"))
        }
        config.update(kwargs)
        
        logger.info("Creating Kafka event bus with config: %s",
                   {k: v for k, v in config.items() if 'servers' not in k.lower()})
        
        return KafkaEventBus(**config)


# Global event bus instance
_global_event_bus: Optional[Union[EventBus, KafkaEventBus]] = None


async def get_global_event_bus() -> Union[EventBus, KafkaEventBus]:
    """Get the global event bus instance."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBusFactory.create_event_bus()
        await _global_event_bus.initialize()
    return _global_event_bus


async def shutdown_global_event_bus() -> None:
    """Shutdown the global event bus instance."""
    global _global_event_bus
    if _global_event_bus is not None:
        await _global_event_bus.shutdown()
        _global_event_bus = None


class EventBusConfig:
    """Configuration class for event bus settings."""
    
    def __init__(self):
        self.bus_type = os.getenv("EVENT_BUS_TYPE", "redis").lower()
        self.enable_event_sourcing = os.getenv("ENABLE_EVENT_SOURCING", "true").lower() == "true"
        self.enable_event_replay = os.getenv("ENABLE_EVENT_REPLAY", "true").lower() == "true"
        self.event_batch_size = int(os.getenv("EVENT_BATCH_SIZE", "100"))
        self.event_flush_interval = int(os.getenv("EVENT_FLUSH_INTERVAL_MS", "1000"))
        
        # Redis-specific config
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_event_ttl = int(os.getenv("EVENT_TTL_SECONDS", "604800"))
        
        # Kafka-specific config
        self.kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.kafka_topic_prefix = os.getenv("KAFKA_TOPIC_PREFIX", "ai-opportunity")
        self.kafka_consumer_group = os.getenv("KAFKA_CONSUMER_GROUP", "ai-opportunity-consumers")
        self.kafka_retention_ms = int(os.getenv("KAFKA_RETENTION_MS", "604800000"))
        self.kafka_partitions = int(os.getenv("KAFKA_PARTITIONS", "3"))
        self.kafka_replication_factor = int(os.getenv("KAFKA_REPLICATION_FACTOR", "1"))
        
        # Common config
        self.max_retries = int(os.getenv("EVENT_MAX_RETRIES", "3"))
        self.enable_compression = os.getenv("ENABLE_EVENT_COMPRESSION", "true").lower() == "true"
        self.enable_encryption = os.getenv("ENABLE_EVENT_ENCRYPTION", "false").lower() == "true"
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            attr: getattr(self, attr)
            for attr in dir(self)
            if not attr.startswith('_') and not callable(getattr(self, attr))
        }
    
    def get_event_bus_config(self) -> dict:
        """Get configuration specific to the selected event bus type."""
        if self.bus_type == "redis":
            return {
                "redis_url": self.redis_url,
                "event_ttl": self.redis_event_ttl,
                "max_retries": self.max_retries
            }
        elif self.bus_type == "kafka":
            return {
                "bootstrap_servers": self.kafka_bootstrap_servers,
                "topic_prefix": self.kafka_topic_prefix,
                "consumer_group": self.kafka_consumer_group,
                "max_retries": self.max_retries,
                "retention_ms": self.kafka_retention_ms,
                "partitions": self.kafka_partitions,
                "replication_factor": self.kafka_replication_factor
            }
        else:
            raise ValueError(f"Unsupported event bus type: {self.bus_type}")


def validate_event_bus_config() -> bool:
    """Validate event bus configuration."""
    config = EventBusConfig()
    
    try:
        if config.bus_type == "redis":
            # Validate Redis configuration
            if not config.redis_url:
                logger.error("Redis URL not configured")
                return False
                
        elif config.bus_type == "kafka":
            # Validate Kafka configuration
            if not config.kafka_bootstrap_servers:
                logger.error("Kafka bootstrap servers not configured")
                return False
                
            if config.kafka_partitions < 1:
                logger.error("Kafka partitions must be >= 1")
                return False
                
            if config.kafka_replication_factor < 1:
                logger.error("Kafka replication factor must be >= 1")
                return False
        else:
            logger.error(f"Invalid event bus type: {config.bus_type}")
            return False
        
        logger.info(f"Event bus configuration validated for type: {config.bus_type}")
        return True
        
    except Exception as e:
        logger.error(f"Error validating event bus configuration: {e}")
        return False