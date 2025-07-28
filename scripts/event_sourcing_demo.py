"""
Event Sourcing System Demo

This script demonstrates the event sourcing capabilities including:
- Event storage and retrieval
- Event replay functionality
- Event versioning and migration
- Snapshot management
- Audit trail generation
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from shared.event_bus import Event, EventType
from shared.event_sourcing import (
    get_event_sourcing_service, EventSnapshot, EventCheckpoint,
    EventVersion
)
from shared.event_migrations import register_all_migrators
from shared.event_publishers import (
    OpportunityEventPublisher, UserEventPublisher, AgentEventPublisher
)


class OpportunityAggregate:
    """Example aggregate for demonstration."""
    
    def __init__(self, opportunity_id: str):
        self.id = opportunity_id
        self.title = ""
        self.description = ""
        self.ai_solution_type = ""
        self.market_size_estimate = 0.0
        self.validation_score = 0.0
        self.version = 0
        self.created_at = None
        self.updated_at = None
        self.validations = []
    
    def apply_event(self, event: Event) -> None:
        """Apply an event to update the aggregate state."""
        if event.event_type == EventType.OPPORTUNITY_CREATED:
            self._apply_opportunity_created(event)
        elif event.event_type == EventType.OPPORTUNITY_UPDATED:
            self._apply_opportunity_updated(event)
        elif event.event_type == EventType.OPPORTUNITY_VALIDATED:
            self._apply_opportunity_validated(event)
        
        self.version += 1
        self.updated_at = event.timestamp
    
    def _apply_opportunity_created(self, event: Event) -> None:
        """Apply opportunity created event."""
        payload = event.payload
        self.title = payload.get('title', '')
        self.description = payload.get('description', '')
        self.ai_solution_type = payload.get('ai_solution_type', '')
        self.market_size_estimate = payload.get('market_size_estimate', 0.0)
        self.created_at = event.timestamp
    
    def _apply_opportunity_updated(self, event: Event) -> None:
        """Apply opportunity updated event."""
        changes = event.payload.get('changes', {})
        
        for field, value in changes.items():
            if hasattr(self, field):
                setattr(self, field, value)
    
    def _apply_opportunity_validated(self, event: Event) -> None:
        """Apply opportunity validated event."""
        validation = {
            'validation_id': event.payload.get('validation_id'),
            'validator_id': event.payload.get('validator_id'),
            'validation_score': event.payload.get('validation_score'),
            'validation_type': event.payload.get('validation_type'),
            'timestamp': event.timestamp
        }
        self.validations.append(validation)
        
        # Update overall validation score (simple average)
        if self.validations:
            total_score = sum(v['validation_score'] for v in self.validations)
            self.validation_score = total_score / len(self.validations)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert aggregate to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'ai_solution_type': self.ai_solution_type,
            'market_size_estimate': self.market_size_estimate,
            'validation_score': self.validation_score,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'validations': self.validations
        }


async def demonstrate_event_storage():
    """Demonstrate event storage and retrieval."""
    print("\n=== Event Storage Demo ===")
    
    # Get event sourcing service
    service = await get_event_sourcing_service()
    
    # Register migrators
    await register_all_migrators(service)
    
    # Create some sample events
    opportunity_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    
    # Create opportunity
    publisher = OpportunityEventPublisher(correlation_id)
    
    event_id_1 = await publisher.opportunity_created(
        opportunity_id=opportunity_id,
        title="AI-Powered Customer Support Chatbot",
        description="Intelligent chatbot for customer service automation",
        ai_solution_type="natural_language_processing",
        market_size_estimate=50000000.0,
        created_by="demo_user"
    )
    print(f"Published opportunity created event: {event_id_1}")
    
    # Update opportunity
    event_id_2 = await publisher.opportunity_updated(
        opportunity_id=opportunity_id,
        changes={
            "description": "Advanced AI chatbot with sentiment analysis",
            "market_size_estimate": 75000000.0
        },
        updated_by="demo_user"
    )
    print(f"Published opportunity updated event: {event_id_2}")
    
    # Validate opportunity
    event_id_3 = await publisher.opportunity_validated(
        opportunity_id=opportunity_id,
        validation_id=str(uuid.uuid4()),
        validator_id="expert_user",
        validation_score=8.5,
        validation_type="market_demand",
        comments="Strong market demand for AI customer support solutions"
    )
    print(f"Published opportunity validated event: {event_id_3}")
    
    # Wait a moment for events to be processed
    await asyncio.sleep(1)
    
    # Retrieve audit trail
    audit_trail = await service.get_audit_trail(aggregate_id=opportunity_id)
    print(f"\nRetrieved {len(audit_trail)} events from audit trail:")
    
    for event in audit_trail:
        print(f"  - {event.event_type} at {event.timestamp}")
        print(f"    Payload: {event.payload}")
    
    return opportunity_id, audit_trail


async def demonstrate_aggregate_rebuilding(opportunity_id: str):
    """Demonstrate rebuilding aggregates from events."""
    print("\n=== Aggregate Rebuilding Demo ===")
    
    service = await get_event_sourcing_service()
    
    def build_opportunity_aggregate(events: List[Event], base_state: Dict = None) -> OpportunityAggregate:
        """Build opportunity aggregate from events."""
        if base_state:
            # Restore from snapshot
            aggregate = OpportunityAggregate(base_state['id'])
            aggregate.title = base_state['title']
            aggregate.description = base_state['description']
            aggregate.ai_solution_type = base_state['ai_solution_type']
            aggregate.market_size_estimate = base_state['market_size_estimate']
            aggregate.validation_score = base_state['validation_score']
            aggregate.version = base_state['version']
            aggregate.validations = base_state.get('validations', [])
            if base_state.get('created_at'):
                aggregate.created_at = datetime.fromisoformat(base_state['created_at'])
            if base_state.get('updated_at'):
                aggregate.updated_at = datetime.fromisoformat(base_state['updated_at'])
        else:
            # Build from scratch
            aggregate = OpportunityAggregate(opportunity_id)
        
        # Apply events
        for event in events:
            aggregate.apply_event(event)
        
        return aggregate
    
    # Rebuild aggregate from events
    aggregate = await service.rebuild_aggregate(
        aggregate_id=opportunity_id,
        aggregate_builder=build_opportunity_aggregate,
        use_snapshots=False
    )
    
    if aggregate:
        print("Rebuilt opportunity aggregate:")
        print(f"  ID: {aggregate.id}")
        print(f"  Title: {aggregate.title}")
        print(f"  Description: {aggregate.description}")
        print(f"  AI Solution Type: {aggregate.ai_solution_type}")
        print(f"  Market Size: ${aggregate.market_size_estimate:,.2f}")
        print(f"  Validation Score: {aggregate.validation_score:.1f}")
        print(f"  Version: {aggregate.version}")
        print(f"  Validations: {len(aggregate.validations)}")
        
        # Create a snapshot
        await service.create_snapshot(
            aggregate_id=opportunity_id,
            aggregate_type="opportunity",
            version=aggregate.version,
            data=aggregate.to_dict(),
            metadata={"created_by": "demo", "snapshot_reason": "demo"}
        )
        print(f"\nCreated snapshot at version {aggregate.version}")
        
        return aggregate
    else:
        print("No aggregate found")
        return None


async def demonstrate_event_replay():
    """Demonstrate event replay functionality."""
    print("\n=== Event Replay Demo ===")
    
    service = await get_event_sourcing_service()
    
    # Create a replay handler that collects events
    replayed_events = []
    
    async def replay_handler(event: Event):
        """Handle replayed events."""
        replayed_events.append(event)
        print(f"Replayed: {event.event_type} at {event.timestamp}")
        print(f"  Replay ID: {event.metadata.get('replay_id')}")
    
    # Replay events from the last hour
    from_timestamp = datetime.now(timezone.utc) - timedelta(hours=1)
    
    replay_id = await service.replay_events(
        replay_handler=replay_handler,
        from_timestamp=from_timestamp,
        event_types=[EventType.OPPORTUNITY_CREATED, EventType.OPPORTUNITY_UPDATED, EventType.OPPORTUNITY_VALIDATED],
        checkpoint_name="demo_replay_checkpoint",
        batch_size=10
    )
    
    print(f"\nReplay completed with ID: {replay_id}")
    print(f"Total events replayed: {len(replayed_events)}")


async def demonstrate_event_migration():
    """Demonstrate event migration functionality."""
    print("\n=== Event Migration Demo ===")
    
    # Create a v1.0 event that needs migration
    old_event = Event(
        id=str(uuid.uuid4()),
        event_type=EventType.OPPORTUNITY_CREATED,
        payload={
            "opportunity_id": str(uuid.uuid4()),
            "title": "Legacy Opportunity",
            "ai_solution_type": "nlp",
            "market_size": 1000000  # Old field name
        },
        timestamp=datetime.now(timezone.utc),
        source="legacy_system",
        correlation_id=str(uuid.uuid4()),
        metadata={"version": EventVersion.V1_0}
    )
    
    print("Original v1.0 event:")
    print(f"  Version: {old_event.metadata.get('version')}")
    print(f"  Payload: {old_event.payload}")
    
    # Get migrator and apply migration
    from shared.event_migrations import OpportunityEventV1ToV2Migrator
    
    migrator = OpportunityEventV1ToV2Migrator()
    
    if migrator.can_migrate(old_event):
        migrated_event = await migrator.migrate(old_event)
        
        print("\nMigrated v2.0 event:")
        print(f"  Version: {migrated_event.metadata.get('version')}")
        print(f"  Migration Applied: {migrated_event.metadata.get('migration_applied')}")
        print(f"  Payload: {migrated_event.payload}")
        
        # Show specific changes
        print("\nMigration changes:")
        print(f"  - 'market_size' → 'market_size_estimate': {migrated_event.payload.get('market_size_estimate')}")
        print(f"  - Added 'ai_solution_category': {migrated_event.payload.get('ai_solution_category')}")
        print(f"  - Added 'confidence_score': {migrated_event.payload.get('confidence_score')}")
    else:
        print("Event cannot be migrated by this migrator")


async def demonstrate_checkpoint_management():
    """Demonstrate checkpoint management."""
    print("\n=== Checkpoint Management Demo ===")
    
    service = await get_event_sourcing_service()
    
    # Create a checkpoint
    checkpoint = EventCheckpoint(
        id=str(uuid.uuid4()),
        name="demo_checkpoint",
        timestamp=datetime.now(timezone.utc),
        last_event_id=str(uuid.uuid4()),
        event_count=150,
        metadata={
            "created_by": "demo",
            "purpose": "demonstration",
            "batch_size": 50
        }
    )
    
    await service.event_store.create_checkpoint(checkpoint)
    print(f"Created checkpoint: {checkpoint.name}")
    print(f"  Event count: {checkpoint.event_count}")
    print(f"  Timestamp: {checkpoint.timestamp}")
    
    # Retrieve checkpoint
    retrieved = await service.event_store.get_checkpoint("demo_checkpoint")
    if retrieved:
        print(f"\nRetrieved checkpoint: {retrieved.name}")
        print(f"  ID: {retrieved.id}")
        print(f"  Last event ID: {retrieved.last_event_id}")
        print(f"  Metadata: {retrieved.metadata}")
    else:
        print("Checkpoint not found")


async def main():
    """Run all demonstrations."""
    print("Event Sourcing System Demonstration")
    print("=" * 50)
    
    try:
        # Demonstrate event storage
        opportunity_id, audit_trail = await demonstrate_event_storage()
        
        # Demonstrate aggregate rebuilding
        aggregate = await demonstrate_aggregate_rebuilding(opportunity_id)
        
        # Demonstrate event replay
        await demonstrate_event_replay()
        
        # Demonstrate event migration
        await demonstrate_event_migration()
        
        # Demonstrate checkpoint management
        await demonstrate_checkpoint_management()
        
        print("\n" + "=" * 50)
        print("Event Sourcing Demo Completed Successfully!")
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())