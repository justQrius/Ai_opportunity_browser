# Event Sourcing System Documentation

## Overview

The AI Opportunity Browser implements a comprehensive event sourcing system that provides:

- **Immutable Audit Trail**: All system changes are stored as events
- **Event Replay**: Ability to reconstruct system state from events
- **Event Versioning**: Support for schema evolution and migration
- **Snapshot Management**: Performance optimization through state snapshots
- **Checkpoint Tracking**: Progress tracking for event replay operations

## Architecture

### Core Components

```mermaid
graph TB
    subgraph "Event Bus Layer"
        EB[Event Bus]
        EP[Event Publishers]
        EH[Event Handlers]
    end
    
    subgraph "Event Sourcing Layer"
        ES[Event Store]
        ESS[Event Sourcing Service]
        EM[Event Migrators]
    end
    
    subgraph "Storage Layer"
        PG[(PostgreSQL)]
        REDIS[(Redis)]
        KAFKA[(Kafka)]
    end
    
    subgraph "Application Layer"
        AGG[Aggregates]
        SNAP[Snapshots]
        AUDIT[Audit Trail]
    end
    
    EP --> EB
    EB --> EH
    EH --> ES
    ES --> ESS
    ESS --> EM
    
    ES --> PG
    EB --> REDIS
    EB --> KAFKA
    
    ESS --> AGG
    ESS --> SNAP
    ESS --> AUDIT
```

### Event Store Schema

The event store uses PostgreSQL tables to persist events:

```sql
-- Events table
CREATE TABLE event_store_events (
    id VARCHAR(36) PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    aggregate_id VARCHAR(36),
    aggregate_type VARCHAR(50),
    aggregate_version INTEGER,
    version VARCHAR(10) NOT NULL DEFAULT '1.0',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    payload JSONB NOT NULL,
    metadata JSONB,
    source VARCHAR(100) NOT NULL,
    correlation_id VARCHAR(36),
    causation_id VARCHAR(36),
    command_id VARCHAR(36),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Snapshots table
CREATE TABLE event_store_snapshots (
    id VARCHAR(36) PRIMARY KEY,
    aggregate_id VARCHAR(36) NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    data JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(aggregate_id, version)
);

-- Checkpoints table
CREATE TABLE event_store_checkpoints (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    last_event_id VARCHAR(36) NOT NULL,
    event_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Usage Guide

### Basic Event Sourcing

```python
from shared.event_sourcing import get_event_sourcing_service
from shared.event_bus import EventType

# Get the event sourcing service
service = await get_event_sourcing_service()

# Retrieve audit trail for an aggregate
audit_trail = await service.get_audit_trail(
    aggregate_id="opportunity-123",
    from_timestamp=datetime.now() - timedelta(days=7)
)

# Rebuild an aggregate from events
def build_opportunity(events, base_state=None):
    opportunity = Opportunity(base_state) if base_state else Opportunity()
    for event in events:
        opportunity.apply_event(event)
    return opportunity

opportunity = await service.rebuild_aggregate(
    aggregate_id="opportunity-123",
    aggregate_builder=build_opportunity,
    use_snapshots=True
)
```

### Event Replay

```python
# Define replay handler
async def replay_handler(event):
    print(f"Replaying: {event.event_type}")
    # Process the event
    await process_event(event)

# Replay events from a specific time
replay_id = await service.replay_events(
    replay_handler=replay_handler,
    from_timestamp=datetime.now() - timedelta(hours=24),
    event_types=[EventType.OPPORTUNITY_CREATED, EventType.OPPORTUNITY_UPDATED],
    checkpoint_name="daily_replay",
    batch_size=100
)
```

### Snapshot Management

```python
# Create a snapshot
await service.create_snapshot(
    aggregate_id="opportunity-123",
    aggregate_type="opportunity",
    version=15,
    data=opportunity.to_dict(),
    metadata={"created_by": "system", "reason": "periodic_snapshot"}
)

# Snapshots are automatically used during aggregate rebuilding
# when use_snapshots=True (default)
```

### Event Migration

```python
from shared.event_sourcing import EventMigrator
from shared.event_bus import Event

class MyEventMigrator(EventMigrator):
    @property
    def from_version(self) -> str:
        return "1.0"
    
    @property
    def to_version(self) -> str:
        return "2.0"
    
    def can_migrate(self, event: Event) -> bool:
        return (event.metadata.get('version') == self.from_version and
                event.event_type == EventType.MY_EVENT)
    
    async def migrate(self, event: Event) -> Event:
        # Transform event payload and metadata
        new_payload = self.transform_payload(event.payload)
        new_metadata = event.metadata.copy()
        new_metadata['version'] = self.to_version
        new_metadata['migration_applied'] = f"{self.from_version}_to_{self.to_version}"
        
        return Event(
            id=event.id,
            event_type=event.event_type,
            payload=new_payload,
            timestamp=event.timestamp,
            source=event.source,
            correlation_id=event.correlation_id,
            metadata=new_metadata
        )

# Register the migrator
service.register_migrator(MyEventMigrator())
```

## Event Versioning

### Version Strategy

The system uses semantic versioning for events:

- **Major version** (e.g., 1.0 → 2.0): Breaking changes requiring migration
- **Minor version** (e.g., 1.0 → 1.1): Backward-compatible additions
- **Patch version** (e.g., 1.1.0 → 1.1.1): Bug fixes and clarifications

### Migration Examples

#### Opportunity Events v1.0 → v2.0

**Changes:**
- `market_size` → `market_size_estimate`
- Added `ai_solution_category`
- Added `confidence_score`

```python
# Before (v1.0)
{
    "opportunity_id": "123",
    "title": "AI Chatbot",
    "ai_solution_type": "nlp",
    "market_size": 1000000
}

# After (v2.0)
{
    "opportunity_id": "123",
    "title": "AI Chatbot",
    "ai_solution_type": "nlp",
    "market_size_estimate": 1000000,
    "ai_solution_category": "natural_language_processing",
    "confidence_score": 0.7
}
```

#### User Events v1.0 → v1.1

**Changes:**
- Added `user_preferences`
- Added `notification_settings`
- Standardized `expertise_domains` format

```python
# Before (v1.0)
{
    "user_id": "456",
    "email": "user@example.com",
    "expertise_domains": "ai,machine learning,nlp"
}

# After (v1.1)
{
    "user_id": "456",
    "email": "user@example.com",
    "expertise_domains": ["ai", "machine learning", "nlp"],
    "user_preferences": {
        "email_notifications": true,
        "push_notifications": true,
        "weekly_digest": true
    },
    "notification_settings": {
        "frequency": "immediate",
        "channels": ["email"],
        "quiet_hours": {"enabled": false}
    }
}
```

## Performance Considerations

### Snapshot Strategy

- **Frequency**: Create snapshots every 10-20 events
- **Retention**: Keep last 3 snapshots per aggregate
- **Async Creation**: Generate snapshots asynchronously

### Event Replay Optimization

- **Batch Processing**: Process events in batches of 100-1000
- **Checkpointing**: Use checkpoints for long-running replays
- **Parallel Processing**: Replay independent aggregates in parallel

### Database Optimization

```sql
-- Essential indexes
CREATE INDEX idx_events_aggregate ON event_store_events(aggregate_id, aggregate_version);
CREATE INDEX idx_events_type_time ON event_store_events(event_type, timestamp);
CREATE INDEX idx_events_correlation ON event_store_events(correlation_id);
CREATE INDEX idx_snapshots_aggregate ON event_store_snapshots(aggregate_id, version DESC);
```

## Monitoring and Observability

### Key Metrics

- **Event Storage Rate**: Events stored per second
- **Replay Performance**: Time to replay N events
- **Migration Success Rate**: Percentage of successful migrations
- **Snapshot Hit Rate**: Percentage of rebuilds using snapshots

### Health Checks

```python
async def check_event_sourcing_health():
    service = await get_event_sourcing_service()
    
    # Check event store connectivity
    try:
        await service.event_store.initialize()
        store_healthy = True
    except Exception:
        store_healthy = False
    
    # Check recent event activity
    recent_events = await service.get_audit_trail(
        from_timestamp=datetime.now() - timedelta(minutes=5),
        limit=1
    )
    recent_activity = len(recent_events) > 0
    
    return {
        "event_store_healthy": store_healthy,
        "recent_activity": recent_activity,
        "migrators_registered": len(service.event_store.migrators)
    }
```

## Best Practices

### Event Design

1. **Immutable Events**: Never modify published events
2. **Rich Metadata**: Include correlation IDs, causation IDs, and command IDs
3. **Versioning**: Always include version information in metadata
4. **Idempotency**: Design events to be safely replayed

### Aggregate Design

1. **Single Responsibility**: One aggregate per business entity
2. **Event Application**: Implement `apply_event()` methods
3. **State Validation**: Validate state after applying events
4. **Snapshot Serialization**: Ensure aggregates can be serialized/deserialized

### Migration Strategy

1. **Backward Compatibility**: Maintain compatibility when possible
2. **Gradual Migration**: Migrate events lazily during replay
3. **Testing**: Thoroughly test migrations with real data
4. **Rollback Plan**: Have a plan for rolling back migrations

### Error Handling

1. **Graceful Degradation**: Continue processing when possible
2. **Dead Letter Queue**: Handle failed events appropriately
3. **Monitoring**: Monitor migration failures and replay errors
4. **Alerting**: Alert on critical event sourcing failures

## Configuration

### Environment Variables

```bash
# Event sourcing configuration
ENABLE_EVENT_SOURCING=true
EVENT_STORE_TABLE_PREFIX=event_store
EVENT_BATCH_SIZE=100
EVENT_REPLAY_TIMEOUT=300

# Database configuration
DATABASE_URL=postgresql://user:pass@localhost/ai_opportunity_browser

# Event bus configuration
EVENT_BUS_TYPE=redis  # or kafka
REDIS_URL=redis://localhost:6379/0
```

### Service Configuration

```python
from shared.event_sourcing import EventSourcingService, EventStore

# Custom event store configuration
event_store = EventStore(table_prefix="custom_events")
service = EventSourcingService(event_store=event_store)

# Register custom migrators
service.register_migrator(MyCustomMigrator())

await service.initialize()
```

## Troubleshooting

### Common Issues

1. **Migration Failures**
   - Check event payload structure
   - Verify migrator logic
   - Test with sample events

2. **Replay Performance**
   - Use snapshots to reduce event count
   - Increase batch size
   - Add database indexes

3. **Storage Growth**
   - Implement event archiving
   - Clean up old snapshots
   - Monitor disk usage

### Debug Tools

```python
# Check event store statistics
stats = await service.event_store.get_stats()
print(f"Total events: {stats['total_events']}")
print(f"Events by type: {stats['events_by_type']}")

# Validate event migrations
from shared.event_migrations import get_all_migrators

migrators = get_all_migrators()
for migrator in migrators:
    print(f"Migrator: {migrator.from_version} → {migrator.to_version}")
```

## Future Enhancements

### Planned Features

1. **Event Encryption**: Encrypt sensitive event data
2. **Event Compression**: Compress event payloads for storage efficiency
3. **Distributed Replay**: Distribute replay across multiple workers
4. **Event Validation**: Schema validation for event payloads
5. **Temporal Queries**: Query events by business time vs. system time

### Integration Opportunities

1. **CQRS Integration**: Separate command and query models
2. **Saga Pattern**: Long-running business processes
3. **Event Streaming**: Real-time event processing
4. **Analytics Integration**: Feed events to analytics systems