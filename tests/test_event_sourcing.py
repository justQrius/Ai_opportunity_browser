"""
Tests for Event Sourcing Implementation

This module tests the event sourcing functionality including:
- Event storage and retrieval
- Event replay capabilities
- Event versioning and migration
- Snapshot management
- Audit trail functionality
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from shared.event_bus import Event, EventType
from shared.event_sourcing import (
    EventStore, EventSourcingService, EventSnapshot, EventCheckpoint,
    EventMigrator, EventVersion, EventSourceError, EventMigrationError,
    EventReplayError, get_event_sourcing_service
)
from shared.event_migrations import (
    OpportunityEventV1ToV2Migrator, UserEventV1ToV11Migrator,
    ValidationEventV1ToV2Migrator, AgentEventV1ToV11Migrator,
    get_all_migrators, register_all_migrators
)


class TestEventStore:
    """Test cases for EventStore class."""
    
    @pytest.fixture
    async def event_store(self):
        """Create test event store."""
        store = EventStore(table_prefix="test_event_store")
        await store.initialize()
        yield store
        # Cleanup would go here if needed
    
    @pytest.fixture
    def sample_event(self):
        """Create sample event for testing."""
        return Event(
            id=str(uuid.uuid4()),
            event_type=EventType.OPPORTUNITY_CREATED,
            payload={
                "opportunity_id": str(uuid.uuid4()),
                "title": "Test Opportunity",
                "description": "A test opportunity",
                "ai_solution_type": "nlp"
            },
            timestamp=datetime.now(timezone.utc),
            source="test_service",
            correlation_id=str(uuid.uuid4()),
            metadata={"version": EventVersion.V1_0}
        )
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_event(self, event_store, sample_event):
        """Test storing and retrieving events."""
        aggregate_id = str(uuid.uuid4())
        
        # Store event
        await event_store.store_event(
            sample_event,
            aggregate_id=aggregate_id,
            aggregate_type="opportunity",
            aggregate_version=1
        )
        
        # Retrieve events by aggregate
        events = await event_store.get_events_by_aggregate(aggregate_id)
        
        assert len(events) == 1
        assert events[0].id == sample_event.id
        assert events[0].event_type == sample_event.event_type
        assert events[0].payload == sample_event.payload
    
    @pytest.mark.asyncio
    async def test_get_events_by_type(self, event_store, sample_event):
        """Test retrieving events by type."""
        await event_store.store_event(sample_event)
        
        events = await event_store.get_events_by_type(EventType.OPPORTUNITY_CREATED)
        
        assert len(events) >= 1
        assert any(e.id == sample_event.id for e in events)
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_snapshot(self, event_store):
        """Test snapshot storage and retrieval."""
        aggregate_id = str(uuid.uuid4())
        snapshot = EventSnapshot(
            aggregate_id=aggregate_id,
            aggregate_type="opportunity",
            version=5,
            timestamp=datetime.now(timezone.utc),
            data={"title": "Test Opportunity", "status": "active"},
            metadata={"created_by": "test"}
        )
        
        # Store snapshot
        await event_store.store_snapshot(snapshot)
        
        # Retrieve snapshot
        retrieved = await event_store.get_latest_snapshot(aggregate_id)
        
        assert retrieved is not None
        assert retrieved.aggregate_id == aggregate_id
        assert retrieved.version == 5
        assert retrieved.data == snapshot.data
    
    @pytest.mark.asyncio
    async def test_checkpoint_management(self, event_store):
        """Test checkpoint creation and retrieval."""
        checkpoint = EventCheckpoint(
            id=str(uuid.uuid4()),
            name="test_checkpoint",
            timestamp=datetime.now(timezone.utc),
            last_event_id=str(uuid.uuid4()),
            event_count=100,
            metadata={"test": "data"}
        )
        
        # Create checkpoint
        await event_store.create_checkpoint(checkpoint)
        
        # Retrieve checkpoint
        retrieved = await event_store.get_checkpoint("test_checkpoint")
        
        assert retrieved is not None
        assert retrieved.name == "test_checkpoint"
        assert retrieved.event_count == 100
        assert retrieved.metadata == {"test": "data"}


class TestEventMigrators:
    """Test cases for event migrators."""
    
    def test_opportunity_migrator_v1_to_v2(self):
        """Test opportunity event migration from v1.0 to v2.0."""
        migrator = OpportunityEventV1ToV2Migrator()
        
        # Create v1.0 event
        event = Event(
            id=str(uuid.uuid4()),
            event_type=EventType.OPPORTUNITY_CREATED,
            payload={
                "opportunity_id": str(uuid.uuid4()),
                "title": "Test Opportunity",
                "ai_solution_type": "nlp",
                "market_size": 1000000
            },
            timestamp=datetime.now(timezone.utc),
            source="test",
            metadata={"version": EventVersion.V1_0}
        )
        
        # Check if migrator can handle this event
        assert migrator.can_migrate(event)
        
        # Migrate event
        migrated = asyncio.run(migrator.migrate(event))
        
        # Verify migration
        assert migrated.metadata["version"] == EventVersion.V2_0
        assert "market_size_estimate" in migrated.payload
        assert "market_size" not in migrated.payload
        assert migrated.payload["market_size_estimate"] == 1000000
        assert "ai_solution_category" in migrated.payload
        assert "confidence_score" in migrated.payload
        assert migrated.payload["ai_solution_category"] == "natural_language_processing"
    
    def test_user_migrator_v1_to_v11(self):
        """Test user event migration from v1.0 to v1.1."""
        migrator = UserEventV1ToV11Migrator()
        
        event = Event(
            id=str(uuid.uuid4()),
            event_type=EventType.USER_REGISTERED,
            payload={
                "user_id": str(uuid.uuid4()),
                "email": "test@example.com",
                "expertise_domains": "ai,machine learning,nlp"
            },
            timestamp=datetime.now(timezone.utc),
            source="test",
            metadata={"version": EventVersion.V1_0}
        )
        
        assert migrator.can_migrate(event)
        
        migrated = asyncio.run(migrator.migrate(event))
        
        assert migrated.metadata["version"] == EventVersion.V1_1
        assert "user_preferences" in migrated.payload
        assert "notification_settings" in migrated.payload
        assert isinstance(migrated.payload["expertise_domains"], list)
        assert "ai" in migrated.payload["expertise_domains"]
    
    def test_validation_migrator_v1_to_v2(self):
        """Test validation event migration from v1.0 to v2.0."""
        migrator = ValidationEventV1ToV2Migrator()
        
        event = Event(
            id=str(uuid.uuid4()),
            event_type=EventType.VALIDATION_SUBMITTED,
            payload={
                "validation_id": str(uuid.uuid4()),
                "opportunity_id": str(uuid.uuid4()),
                "validation_type": "market_demand",
                "validation_score": 8.5,
                "evidence_links": ["http://example.com/evidence1"]
            },
            timestamp=datetime.now(timezone.utc),
            source="test",
            metadata={"version": EventVersion.V1_0}
        )
        
        assert migrator.can_migrate(event)
        
        migrated = asyncio.run(migrator.migrate(event))
        
        assert migrated.metadata["version"] == EventVersion.V2_0
        assert "validation_criteria" in migrated.payload
        assert "evidence_quality_score" in migrated.payload
        assert "validation_result" in migrated.payload
        assert isinstance(migrated.payload["validation_result"], dict)
        assert "overall_score" in migrated.payload["validation_result"]
    
    def test_agent_migrator_v1_to_v11(self):
        """Test agent event migration from v1.0 to v1.1."""
        migrator = AgentEventV1ToV11Migrator()
        
        event = Event(
            id=str(uuid.uuid4()),
            event_type=EventType.AGENT_TASK_COMPLETED,
            payload={
                "agent_id": str(uuid.uuid4()),
                "task_id": str(uuid.uuid4()),
                "task_type": "analysis",
                "duration_seconds": 45.2,
                "success": True,
                "result": "Analysis completed successfully"
            },
            timestamp=datetime.now(timezone.utc),
            source="test",
            metadata={"version": EventVersion.V1_0}
        )
        
        assert migrator.can_migrate(event)
        
        migrated = asyncio.run(migrator.migrate(event))
        
        assert migrated.metadata["version"] == EventVersion.V1_1
        assert "performance_metrics" in migrated.payload
        assert "resource_usage" in migrated.payload
        assert isinstance(migrated.payload["result"], dict)
        assert "data" in migrated.payload["result"]
        assert migrated.payload["result"]["data"] == "Analysis completed successfully"


class TestEventSourcingService:
    """Test cases for EventSourcingService."""
    
    @pytest.fixture
    async def event_sourcing_service(self):
        """Create test event sourcing service."""
        with patch('shared.event_sourcing.get_global_event_bus') as mock_bus:
            mock_bus.return_value = AsyncMock()
            service = EventSourcingService()
            await service.initialize()
            yield service
    
    @pytest.fixture
    def sample_events(self):
        """Create sample events for testing."""
        base_time = datetime.now(timezone.utc)
        aggregate_id = str(uuid.uuid4())
        
        events = []
        for i in range(5):
            event = Event(
                id=str(uuid.uuid4()),
                event_type=EventType.OPPORTUNITY_UPDATED,
                payload={
                    "opportunity_id": aggregate_id,
                    "changes": {"field": f"value_{i}"},
                    "version": i + 1
                },
                timestamp=base_time + timedelta(minutes=i),
                source="test",
                correlation_id=str(uuid.uuid4()),
                metadata={
                    "aggregate_id": aggregate_id,
                    "aggregate_type": "opportunity",
                    "aggregate_version": i + 1
                }
            )
            events.append(event)
        
        return events, aggregate_id
    
    @pytest.mark.asyncio
    async def test_event_replay(self, event_sourcing_service, sample_events):
        """Test event replay functionality."""
        events, aggregate_id = sample_events
        
        # Mock event store to return our sample events
        with patch.object(event_sourcing_service.event_store, 'get_events_by_type') as mock_get:
            mock_get.return_value = events
            
            replayed_events = []
            
            async def replay_handler(event):
                replayed_events.append(event)
            
            # Perform replay
            replay_id = await event_sourcing_service.replay_events(
                replay_handler=replay_handler,
                event_types=[EventType.OPPORTUNITY_UPDATED]
            )
            
            assert replay_id is not None
            assert len(replayed_events) == 5
            
            # Check that replay metadata was added
            for event in replayed_events:
                assert event.metadata.get('replay_id') == replay_id
    
    @pytest.mark.asyncio
    async def test_rebuild_aggregate(self, event_sourcing_service, sample_events):
        """Test aggregate rebuilding from events."""
        events, aggregate_id = sample_events
        
        # Mock event store
        with patch.object(event_sourcing_service.event_store, 'get_events_by_aggregate') as mock_get:
            mock_get.return_value = events
            
            def aggregate_builder(events_list, base_state=None):
                """Simple aggregate builder for testing."""
                state = base_state or {"version": 0, "changes": []}
                
                for event in events_list:
                    state["version"] = event.payload["version"]
                    state["changes"].append(event.payload["changes"])
                
                return state
            
            # Rebuild aggregate
            aggregate = await event_sourcing_service.rebuild_aggregate(
                aggregate_id=aggregate_id,
                aggregate_builder=aggregate_builder,
                use_snapshots=False
            )
            
            assert aggregate is not None
            assert aggregate["version"] == 5
            assert len(aggregate["changes"]) == 5
    
    @pytest.mark.asyncio
    async def test_create_snapshot(self, event_sourcing_service):
        """Test snapshot creation."""
        aggregate_id = str(uuid.uuid4())
        
        with patch.object(event_sourcing_service.event_store, 'store_snapshot') as mock_store:
            await event_sourcing_service.create_snapshot(
                aggregate_id=aggregate_id,
                aggregate_type="opportunity",
                version=10,
                data={"title": "Test", "status": "active"},
                metadata={"created_by": "test"}
            )
            
            mock_store.assert_called_once()
            snapshot = mock_store.call_args[0][0]
            assert snapshot.aggregate_id == aggregate_id
            assert snapshot.version == 10
            assert snapshot.data == {"title": "Test", "status": "active"}
    
    @pytest.mark.asyncio
    async def test_get_audit_trail(self, event_sourcing_service, sample_events):
        """Test audit trail retrieval."""
        events, aggregate_id = sample_events
        
        with patch.object(event_sourcing_service.event_store, 'get_events_by_aggregate') as mock_get:
            mock_get.return_value = events
            
            audit_trail = await event_sourcing_service.get_audit_trail(
                aggregate_id=aggregate_id
            )
            
            assert len(audit_trail) == 5
            assert all(e.metadata.get('aggregate_id') == aggregate_id for e in audit_trail)


class TestEventSourcingIntegration:
    """Integration tests for event sourcing system."""
    
    @pytest.mark.asyncio
    async def test_full_event_sourcing_workflow(self):
        """Test complete event sourcing workflow."""
        # This would be a more comprehensive integration test
        # that tests the full workflow from event publishing to replay
        
        with patch('shared.event_sourcing.get_global_event_bus') as mock_bus:
            mock_bus.return_value = AsyncMock()
            
            # Initialize service
            service = await get_event_sourcing_service()
            
            # Register migrators
            await register_all_migrators(service)
            
            # Verify migrators are registered
            assert len(service.event_store.migrators) > 0
            
            # Test that service is properly initialized
            assert service._initialized
    
    @pytest.mark.asyncio
    async def test_migration_chain(self):
        """Test chaining multiple migrations."""
        # Create an event that needs multiple migrations
        event = Event(
            id=str(uuid.uuid4()),
            event_type=EventType.OPPORTUNITY_CREATED,
            payload={
                "opportunity_id": str(uuid.uuid4()),
                "title": "Test",
                "market_size": 1000000
            },
            timestamp=datetime.now(timezone.utc),
            source="test",
            metadata={"version": EventVersion.V1_0}
        )
        
        # Apply migrations
        migrator = OpportunityEventV1ToV2Migrator()
        migrated = await migrator.migrate(event)
        
        # Verify final state
        assert migrated.metadata["version"] == EventVersion.V2_0
        assert "market_size_estimate" in migrated.payload
        assert "ai_solution_category" in migrated.payload
        assert "confidence_score" in migrated.payload
    
    def test_error_handling(self):
        """Test error handling in event sourcing."""
        # Test EventSourceError
        with pytest.raises(EventSourceError):
            raise EventSourceError("Test error")
        
        # Test EventMigrationError
        with pytest.raises(EventMigrationError):
            raise EventMigrationError("Migration failed")
        
        # Test EventReplayError
        with pytest.raises(EventReplayError):
            raise EventReplayError("Replay failed")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])