# Event Bus System Documentation

## Overview

The AI Opportunity Browser implements a comprehensive event-driven architecture using both Redis and Apache Kafka as event bus backends. This system enables decoupled service communication, event sourcing capabilities, audit trails, and real-time streaming analytics.

## Architecture

### Event Bus Types

The system supports two event bus implementations:

1. **Redis Event Bus** (Default)
   - Fast, lightweight pub/sub messaging
   - Built-in event persistence and replay
   - Suitable for development and moderate-scale production

2. **Kafka Event Bus** (Production Scale)
   - High-throughput, durable event streaming
   - Partitioned topics for scalability
   - Built-in replication and fault tolerance
   - Suitable for high-scale production environments

### Key Components

- **Event Bus Factory**: Creates appropriate event bus instances based on configuration
- **Event Publishers**: High-level utilities for publishing domain-specific events
- **Event Handlers**: Concrete handlers for processing different event types
- **Event Manager**: Lifecycle management and handler registration
- **Batch Publishing**: Efficient batch event publishing capabilities

## Configuration

### Environment Variables

```bash
# Event Bus Configuration
EVENT_BUS_TYPE=redis                    # or "kafka"
ENABLE_EVENT_SOURCING=true
ENABLE_EVENT_REPLAY=true
EVENT_BATCH_SIZE=100
EVENT_FLUSH_INTERVAL_MS=1000

# Redis Configuration (when using Redis event bus)
REDIS_URL=redis://localhost:6379/0
EVENT_TTL_SECONDS=604800               # 7 days

# Kafka Configuration (when using Kafka event bus)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_PREFIX=ai-opportunity
KAFKA_CONSUMER_GROUP=ai-opportunity-consumers
KAFKA_RETENTION_MS=604800000           # 7 days
KAFKA_PARTITIONS=3
KAFKA_REPLICATION_FACTOR=1

# Event Handler Configuration
ENABLE_EVENT_HANDLERS=true
ENABLED_EVENT_HANDLERS=all             # or comma-separated list: "opportunity,user,agent"
```

### Docker Compose Setup

#### Redis Only (Default)
```bash
docker-compose up -d postgres redis
```

#### With Kafka
```bash
docker-compose --profile kafka up -d
```

This starts:
- PostgreSQL database
- Redis cache
- Apache Kafka with Zookeeper
- Kafka UI (accessible at http://localhost:8080)

## Event Types

The system defines standard event types for different domains:

### Opportunity Events
- `opportunity.created`
- `opportunity.updated`
- `opportunity.deleted`
- `opportunity.validated`

### User Events
- `user.registered`
- `user.profile_updated`
- `user.reputation_changed`

### Agent Events
- `agent.started`
- `agent.stopped`
- `agent.error`
- `agent.task_completed`

### Market Signal Events
- `signal.detected`
- `signal.processed`
- `signal.clustered`

### System Events
- `system.health_check`
- `system.error`
- `system.maintenance`

## Usage Examples

### Basic Event Publishing

```python
from shared.event_bus import EventType, publish_event

# Publish an event
event_id = await publish_event(
    EventType.OPPORTUNITY_CREATED,
    {
        "opportunity_id": "opp-123",
        "title": "AI-Powered Customer Service",
        "description": "Automated customer support using NLP"
    },
    source="opportunity_service",
    correlation_id="req-456"
)
```

### Using Event Publishers

```python
from shared.event_publishers import OpportunityEventPublisher

# Create publisher
publisher = OpportunityEventPublisher()

# Publish opportunity created event
event_id = await publisher.opportunity_created(
    opportunity_id="opp-123",
    title="AI-Powered Customer Service",
    description="Automated customer support using NLP",
    ai_solution_type="nlp",
    market_size_estimate=5000000.0,
    created_by="user-456"
)
```

### Event Subscription and Handling

```python
from shared.event_bus import EventType, EventHandler, subscribe_to_events

class CustomEventHandler(EventHandler):
    def __init__(self):
        super().__init__("custom_handler")
    
    async def handle(self, event):
        self.logger.info(f"Processing event: {event.event_type}")
        # Custom processing logic here
        
    async def on_error(self, event, error):
        self.logger.error(f"Error processing event {event.id}: {error}")

# Subscribe to events
handler = CustomEventHandler()
await subscribe_to_events([
    EventType.OPPORTUNITY_CREATED,
    EventType.USER_REGISTERED
], handler)
```

### Batch Event Publishing

```python
from shared.event_publishers import batch_event_publishing_context

async with batch_event_publishing_context("batch_service") as batch_publisher:
    # Add multiple events to batch
    for i in range(100):
        await batch_publisher.add_event(
            EventType.SIGNAL_DETECTED,
            {
                "signal_id": f"signal-{i}",
                "source": "reddit",
                "content": f"Market signal {i}"
            }
        )
    # Events are automatically flushed when exiting context
```

### Event Replay

```python
from shared.event_bus import get_event_bus
from datetime import datetime, timezone, timedelta

event_bus = await get_event_bus()

# Replay events from the last hour
from_time = datetime.now(timezone.utc) - timedelta(hours=1)

async for event in event_bus.replay_events(
    EventType.OPPORTUNITY_CREATED,
    from_time
):
    print(f"Replayed event: {event.id} - {event.payload}")
```

## Event Bus Management

### Initialization

```python
from shared.event_config import get_event_bus_manager

# Initialize event bus with handlers
manager = await get_event_bus_manager()

# Get statistics
stats = await manager.get_stats()
print(f"Total events: {stats['total_events']}")
print(f"Active handlers: {stats['registered_handlers']}")
```

### Lifecycle Management

```python
from shared.event_config import event_bus_lifespan

# Use context manager for automatic lifecycle management
async with event_bus_lifespan() as manager:
    # Event bus is initialized and handlers are registered
    # Your application logic here
    pass
# Event bus is automatically shut down
```

## Testing

### Running Event Bus Tests

```bash
# Test both Redis and Kafka event buses
python scripts/test_event_bus_system.py

# Run unit tests
pytest tests/test_event_bus.py -v
```

### Test Results

The test script validates:
- Redis event bus functionality
- Kafka event bus functionality (if Kafka is running)
- Event publishers and handlers
- Batch publishing
- Event replay capabilities
- Error handling

## Monitoring and Observability

### Event Statistics

```python
from shared.event_bus import get_event_bus

event_bus = await get_event_bus()
stats = await event_bus.get_event_stats()

print(f"Total events: {stats['total_events']}")
print(f"Events by type: {stats['events_by_type']}")
print(f"Active subscribers: {stats['active_subscribers']}")
```

### Kafka UI

When using Kafka, access the Kafka UI at http://localhost:8080 to monitor:
- Topics and partitions
- Consumer groups
- Message throughput
- Cluster health

### Health Checks

The system includes built-in health checks for:
- Event bus connectivity
- Consumer group status
- Topic availability
- Message processing rates

## Best Practices

### Event Design

1. **Use structured payloads**: Include all necessary data in event payloads
2. **Include correlation IDs**: For request tracing across services
3. **Add metadata**: Include timestamps, source information, and context
4. **Version events**: Plan for event schema evolution

### Performance

1. **Use batch publishing**: For high-volume event scenarios
2. **Configure partitioning**: Use partition keys for Kafka scalability
3. **Monitor consumer lag**: Ensure consumers keep up with producers
4. **Set appropriate retention**: Balance storage costs with replay needs

### Error Handling

1. **Implement error handlers**: Handle processing failures gracefully
2. **Use dead letter queues**: For failed message processing
3. **Add retry logic**: With exponential backoff for transient failures
4. **Monitor error rates**: Set up alerts for high error rates

### Security

1. **Validate event payloads**: Sanitize and validate all event data
2. **Use authentication**: Secure Kafka clusters in production
3. **Encrypt sensitive data**: Don't include PII in event payloads
4. **Audit event access**: Log event publishing and consumption

## Troubleshooting

### Common Issues

1. **Kafka connection failures**
   - Ensure Kafka is running: `docker-compose ps kafka`
   - Check network connectivity
   - Verify bootstrap servers configuration

2. **Redis connection issues**
   - Ensure Redis is running: `docker-compose ps redis`
   - Check Redis URL configuration
   - Verify Redis authentication if enabled

3. **Consumer lag**
   - Monitor consumer group status
   - Scale consumer instances
   - Optimize event processing logic

4. **Topic creation failures**
   - Check Kafka auto-create settings
   - Verify permissions for topic creation
   - Manually create topics if needed

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger('shared.event_bus').setLevel(logging.DEBUG)
logging.getLogger('aiokafka').setLevel(logging.INFO)
```

## Migration Guide

### From Redis to Kafka

1. Update environment variables:
   ```bash
   EVENT_BUS_TYPE=kafka
   KAFKA_BOOTSTRAP_SERVERS=localhost:9092
   ```

2. Start Kafka services:
   ```bash
   docker-compose --profile kafka up -d
   ```

3. Test the migration:
   ```bash
   python scripts/test_event_bus_system.py
   ```

4. Monitor consumer groups and topic creation

### Scaling Considerations

- **Redis**: Suitable for up to ~10K events/second
- **Kafka**: Suitable for 100K+ events/second with proper configuration
- **Partitioning**: Use meaningful partition keys for Kafka scaling
- **Consumer Groups**: Scale consumers based on partition count

## Integration with AI Agents

The event bus system is integrated with the AI agent system:

```python
from agents.base import BaseAgent
from shared.event_publishers import AgentEventPublisher

class CustomAgent(BaseAgent):
    async def initialize(self):
        self.event_publisher = AgentEventPublisher()
        await super().initialize()
    
    async def execute_task(self, task):
        # Publish task started event
        await self.event_publisher.agent_task_started(
            agent_id=self.agent_id,
            task_id=task.id,
            task_type=task.type
        )
        
        try:
            result = await self.process_task(task)
            
            # Publish task completed event
            await self.event_publisher.agent_task_completed(
                agent_id=self.agent_id,
                task_id=task.id,
                task_type=task.type,
                duration_seconds=task.duration,
                success=True,
                result=result
            )
            
        except Exception as e:
            # Publish error event
            await self.event_publisher.agent_error(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=str(e)
            )
            raise
```

This integration enables:
- Real-time agent monitoring
- Task execution tracking
- Error detection and alerting
- Performance analytics
- Workflow coordination

## Conclusion

The event bus system provides a robust foundation for event-driven architecture in the AI Opportunity Browser. It supports both development and production scenarios with Redis and Kafka backends, comprehensive event handling, and extensive monitoring capabilities.

For questions or issues, refer to the test scripts and example implementations in the codebase.