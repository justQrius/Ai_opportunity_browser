"""
Event Sourcing Implementation for AI Opportunity Browser

This module implements event sourcing capabilities including audit trails,
event replay, versioning, and migration support for the event bus system.

Event sourcing provides:
- Immutable audit trail of all system changes
- Ability to reconstruct system state from events
- Event versioning and schema evolution
- Event migration and replay capabilities
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional, Union, Callable, Type
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod

from .event_bus import Event, EventType
from .event_bus_factory import get_global_event_bus
from .database import get_db_session
from .models.base import Base

logger = logging.getLogger(__name__)


class EventVersion(str, Enum):
    """Event schema versions."""
    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


class EventSourceError(Exception):
    """Base exception for event sourcing errors."""
    pass


class EventMigrationError(EventSourceError):
    """Exception raised during event migration."""
    pass


class EventReplayError(EventSourceError):
    """Exception raised during event replay."""
    pass


@dataclass
class EventMetadata:
    """Extended metadata for event sourcing."""
    
    version: str = EventVersion.V1_0
    schema_hash: Optional[str] = None
    migration_applied: Optional[str] = None
    replay_id: Optional[str] = None
    checkpoint_id: Optional[str] = None
    aggregate_id: Optional[str] = None
    aggregate_version: Optional[int] = None
    causation_id: Optional[str] = None
    command_id: Optional[str] = None


@dataclass
class EventSnapshot:
    """Snapshot of aggregate state at a point in time."""
    
    aggregate_id: str
    aggregate_type: str
    version: int
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EventCheckpoint:
    """Checkpoint for event replay tracking."""
    
    id: str
    name: str
    timestamp: datetime
    last_event_id: str
    event_count: int
    metadata: Optional[Dict[str, Any]] = None


class EventMigrator(ABC):
    """Abstract base class for event migrations."""
    
    @abstractmethod
    def can_migrate(self, event: Event) -> bool:
        """Check if this migrator can handle the event."""
        pass
    
    @abstractmethod
    async def migrate(self, event: Event) -> Event:
        """Migrate event to current version."""
        pass
    
    @property
    @abstractmethod
    def from_version(self) -> str:
        """Source version this migrator handles."""
        pass
    
    @property
    @abstractmethod
    def to_version(self) -> str:
        """Target version this migrator produces."""
        pass


class EventStore:
    """
    Event store implementation for event sourcing.
    
    Provides persistent storage for events with support for:
    - Immutable event storage
    - Event retrieval by aggregate or time range
    - Snapshot management
    - Event migration and versioning
    """
    
    def __init__(self, table_prefix: str = "event_store"):
        self.table_prefix = table_prefix
        self.migrators: List[EventMigrator] = []
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the event store."""
        if self._initialized:
            return
        
        # Create database tables if they don't exist
        await self._create_tables()
        self._initialized = True
        logger.info("Event store initialized")
    
    async def _create_tables(self) -> None:
        """Create event store database tables."""
        async with get_db_session() as session:
            # Create events table
            await session.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_prefix}_events (
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
            """)
            
            # Create snapshots table
            await session.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_prefix}_snapshots (
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
            """)
            
            # Create checkpoints table
            await session.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_prefix}_checkpoints (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    last_event_id VARCHAR(36) NOT NULL,
                    event_count INTEGER NOT NULL DEFAULT 0,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # Create indexes
            await session.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}_events_aggregate 
                ON {self.table_prefix}_events(aggregate_id, aggregate_version);
            """)
            
            await session.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}_events_type_time 
                ON {self.table_prefix}_events(event_type, timestamp);
            """)
            
            await session.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}_events_correlation 
                ON {self.table_prefix}_events(correlation_id);
            """)
            
            await session.commit()
    
    def register_migrator(self, migrator: EventMigrator) -> None:
        """Register an event migrator."""
        self.migrators.append(migrator)
        logger.info(f"Registered event migrator: {migrator.from_version} -> {migrator.to_version}")
    
    async def store_event(
        self,
        event: Event,
        aggregate_id: Optional[str] = None,
        aggregate_type: Optional[str] = None,
        aggregate_version: Optional[int] = None,
        causation_id: Optional[str] = None,
        command_id: Optional[str] = None
    ) -> None:
        """
        Store an event in the event store.
        
        Args:
            event: Event to store
            aggregate_id: ID of the aggregate this event belongs to
            aggregate_type: Type of the aggregate
            aggregate_version: Version of the aggregate after this event
            causation_id: ID of the event that caused this event
            command_id: ID of the command that generated this event
        """
        if not self._initialized:
            await self.initialize()
        
        async with get_db_session() as session:
            # Extract metadata
            metadata = event.metadata or {}
            version = metadata.get('version', EventVersion.V1_0)
            
            # Insert event
            await session.execute(f"""
                INSERT INTO {self.table_prefix}_events (
                    id, event_type, aggregate_id, aggregate_type, aggregate_version,
                    version, timestamp, payload, metadata, source, correlation_id,
                    causation_id, command_id
                ) VALUES (
                    :id, :event_type, :aggregate_id, :aggregate_type, :aggregate_version,
                    :version, :timestamp, :payload, :metadata, :source, :correlation_id,
                    :causation_id, :command_id
                )
            """, {
                'id': event.id,
                'event_type': event.event_type,
                'aggregate_id': aggregate_id,
                'aggregate_type': aggregate_type,
                'aggregate_version': aggregate_version,
                'version': version,
                'timestamp': event.timestamp,
                'payload': json.dumps(event.payload),
                'metadata': json.dumps(metadata),
                'source': event.source,
                'correlation_id': event.correlation_id,
                'causation_id': causation_id,
                'command_id': command_id
            })
            
            await session.commit()
            logger.debug(f"Stored event {event.id} in event store")
    
    async def get_events_by_aggregate(
        self,
        aggregate_id: str,
        from_version: Optional[int] = None,
        to_version: Optional[int] = None,
        apply_migrations: bool = True
    ) -> List[Event]:
        """
        Get events for a specific aggregate.
        
        Args:
            aggregate_id: ID of the aggregate
            from_version: Minimum aggregate version (inclusive)
            to_version: Maximum aggregate version (inclusive)
            apply_migrations: Whether to apply event migrations
            
        Returns:
            List of events ordered by aggregate version
        """
        if not self._initialized:
            await self.initialize()
        
        async with get_db_session() as session:
            query = f"""
                SELECT id, event_type, aggregate_id, aggregate_type, aggregate_version,
                       version, timestamp, payload, metadata, source, correlation_id,
                       causation_id, command_id
                FROM {self.table_prefix}_events
                WHERE aggregate_id = :aggregate_id
            """
            
            params = {'aggregate_id': aggregate_id}
            
            if from_version is not None:
                query += " AND aggregate_version >= :from_version"
                params['from_version'] = from_version
            
            if to_version is not None:
                query += " AND aggregate_version <= :to_version"
                params['to_version'] = to_version
            
            query += " ORDER BY aggregate_version ASC"
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            events = []
            for row in rows:
                event = Event(
                    id=row.id,
                    event_type=row.event_type,
                    payload=json.loads(row.payload),
                    timestamp=row.timestamp,
                    source=row.source,
                    correlation_id=row.correlation_id,
                    metadata=json.loads(row.metadata) if row.metadata else {}
                )
                
                if apply_migrations:
                    event = await self._apply_migrations(event)
                
                events.append(event)
            
            return events
    
    async def get_events_by_type(
        self,
        event_type: Union[str, EventType],
        from_timestamp: Optional[datetime] = None,
        to_timestamp: Optional[datetime] = None,
        limit: Optional[int] = None,
        apply_migrations: bool = True
    ) -> List[Event]:
        """
        Get events by type within a time range.
        
        Args:
            event_type: Type of events to retrieve
            from_timestamp: Start timestamp (inclusive)
            to_timestamp: End timestamp (inclusive)
            limit: Maximum number of events to return
            apply_migrations: Whether to apply event migrations
            
        Returns:
            List of events ordered by timestamp
        """
        if not self._initialized:
            await self.initialize()
        
        async with get_db_session() as session:
            query = f"""
                SELECT id, event_type, aggregate_id, aggregate_type, aggregate_version,
                       version, timestamp, payload, metadata, source, correlation_id,
                       causation_id, command_id
                FROM {self.table_prefix}_events
                WHERE event_type = :event_type
            """
            
            params = {'event_type': str(event_type)}
            
            if from_timestamp:
                query += " AND timestamp >= :from_timestamp"
                params['from_timestamp'] = from_timestamp
            
            if to_timestamp:
                query += " AND timestamp <= :to_timestamp"
                params['to_timestamp'] = to_timestamp
            
            query += " ORDER BY timestamp ASC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            events = []
            for row in rows:
                event = Event(
                    id=row.id,
                    event_type=row.event_type,
                    payload=json.loads(row.payload),
                    timestamp=row.timestamp,
                    source=row.source,
                    correlation_id=row.correlation_id,
                    metadata=json.loads(row.metadata) if row.metadata else {}
                )
                
                if apply_migrations:
                    event = await self._apply_migrations(event)
                
                events.append(event)
            
            return events
    
    async def _apply_migrations(self, event: Event) -> Event:
        """Apply migrations to bring event to current version."""
        current_event = event
        
        for migrator in self.migrators:
            if migrator.can_migrate(current_event):
                try:
                    current_event = await migrator.migrate(current_event)
                    logger.debug(f"Applied migration {migrator.from_version} -> {migrator.to_version} to event {event.id}")
                except Exception as e:
                    logger.error(f"Failed to migrate event {event.id}: {e}")
                    raise EventMigrationError(f"Migration failed for event {event.id}: {e}")
        
        return current_event
    
    async def store_snapshot(self, snapshot: EventSnapshot) -> None:
        """Store an aggregate snapshot."""
        if not self._initialized:
            await self.initialize()
        
        async with get_db_session() as session:
            await session.execute(f"""
                INSERT INTO {self.table_prefix}_snapshots (
                    id, aggregate_id, aggregate_type, version, timestamp, data, metadata
                ) VALUES (
                    :id, :aggregate_id, :aggregate_type, :version, :timestamp, :data, :metadata
                )
                ON CONFLICT (aggregate_id, version) DO UPDATE SET
                    timestamp = EXCLUDED.timestamp,
                    data = EXCLUDED.data,
                    metadata = EXCLUDED.metadata
            """, {
                'id': str(uuid.uuid4()),
                'aggregate_id': snapshot.aggregate_id,
                'aggregate_type': snapshot.aggregate_type,
                'version': snapshot.version,
                'timestamp': snapshot.timestamp,
                'data': json.dumps(snapshot.data),
                'metadata': json.dumps(snapshot.metadata or {})
            })
            
            await session.commit()
            logger.debug(f"Stored snapshot for aggregate {snapshot.aggregate_id} version {snapshot.version}")
    
    async def get_latest_snapshot(
        self,
        aggregate_id: str,
        max_version: Optional[int] = None
    ) -> Optional[EventSnapshot]:
        """Get the latest snapshot for an aggregate."""
        if not self._initialized:
            await self.initialize()
        
        async with get_db_session() as session:
            query = f"""
                SELECT aggregate_id, aggregate_type, version, timestamp, data, metadata
                FROM {self.table_prefix}_snapshots
                WHERE aggregate_id = :aggregate_id
            """
            
            params = {'aggregate_id': aggregate_id}
            
            if max_version is not None:
                query += " AND version <= :max_version"
                params['max_version'] = max_version
            
            query += " ORDER BY version DESC LIMIT 1"
            
            result = await session.execute(query, params)
            row = result.fetchone()
            
            if row:
                return EventSnapshot(
                    aggregate_id=row.aggregate_id,
                    aggregate_type=row.aggregate_type,
                    version=row.version,
                    timestamp=row.timestamp,
                    data=json.loads(row.data),
                    metadata=json.loads(row.metadata) if row.metadata else None
                )
            
            return None
    
    async def create_checkpoint(self, checkpoint: EventCheckpoint) -> None:
        """Create or update a checkpoint."""
        if not self._initialized:
            await self.initialize()
        
        async with get_db_session() as session:
            await session.execute(f"""
                INSERT INTO {self.table_prefix}_checkpoints (
                    id, name, timestamp, last_event_id, event_count, metadata
                ) VALUES (
                    :id, :name, :timestamp, :last_event_id, :event_count, :metadata
                )
                ON CONFLICT (name) DO UPDATE SET
                    timestamp = EXCLUDED.timestamp,
                    last_event_id = EXCLUDED.last_event_id,
                    event_count = EXCLUDED.event_count,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
            """, {
                'id': checkpoint.id,
                'name': checkpoint.name,
                'timestamp': checkpoint.timestamp,
                'last_event_id': checkpoint.last_event_id,
                'event_count': checkpoint.event_count,
                'metadata': json.dumps(checkpoint.metadata or {})
            })
            
            await session.commit()
            logger.info(f"Created/updated checkpoint: {checkpoint.name}")
    
    async def get_checkpoint(self, name: str) -> Optional[EventCheckpoint]:
        """Get a checkpoint by name."""
        if not self._initialized:
            await self.initialize()
        
        async with get_db_session() as session:
            result = await session.execute(f"""
                SELECT id, name, timestamp, last_event_id, event_count, metadata
                FROM {self.table_prefix}_checkpoints
                WHERE name = :name
            """, {'name': name})
            
            row = result.fetchone()
            if row:
                return EventCheckpoint(
                    id=row.id,
                    name=row.name,
                    timestamp=row.timestamp,
                    last_event_id=row.last_event_id,
                    event_count=row.event_count,
                    metadata=json.loads(row.metadata) if row.metadata else None
                )
            
            return None


class EventSourcingService:
    """
    Main service for event sourcing functionality.
    
    Provides high-level interface for:
    - Event storage and retrieval
    - Event replay and reconstruction
    - Snapshot management
    - Migration handling
    """
    
    def __init__(self, event_store: Optional[EventStore] = None):
        self.event_store = event_store or EventStore()
        self.event_bus = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the event sourcing service."""
        if self._initialized:
            return
        
        await self.event_store.initialize()
        self.event_bus = await get_global_event_bus()
        
        # Subscribe to all events for automatic storage
        await self._setup_event_storage()
        
        self._initialized = True
        logger.info("Event sourcing service initialized")
    
    async def _setup_event_storage(self) -> None:
        """Set up automatic event storage from event bus."""
        from .event_bus import EventHandler
        
        class EventStorageHandler(EventHandler):
            def __init__(self, event_store: EventStore):
                super().__init__("event_storage_handler")
                self.event_store = event_store
            
            async def handle(self, event: Event) -> None:
                """Store event in event store."""
                try:
                    # Extract aggregate information from metadata
                    metadata = event.metadata or {}
                    aggregate_id = metadata.get('aggregate_id')
                    aggregate_type = metadata.get('aggregate_type')
                    aggregate_version = metadata.get('aggregate_version')
                    causation_id = metadata.get('causation_id')
                    command_id = metadata.get('command_id')
                    
                    await self.event_store.store_event(
                        event,
                        aggregate_id=aggregate_id,
                        aggregate_type=aggregate_type,
                        aggregate_version=aggregate_version,
                        causation_id=causation_id,
                        command_id=command_id
                    )
                except Exception as e:
                    self.logger.error(f"Failed to store event {event.id}: {e}")
        
        # Subscribe to all event types
        handler = EventStorageHandler(self.event_store)
        await self.event_bus.subscribe_to_events(list(EventType), handler)
    
    async def replay_events(
        self,
        replay_handler: Callable[[Event], None],
        from_timestamp: Optional[datetime] = None,
        to_timestamp: Optional[datetime] = None,
        event_types: Optional[List[Union[str, EventType]]] = None,
        checkpoint_name: Optional[str] = None,
        batch_size: int = 100
    ) -> str:
        """
        Replay events with a custom handler.
        
        Args:
            replay_handler: Function to handle each replayed event
            from_timestamp: Start timestamp for replay
            to_timestamp: End timestamp for replay
            event_types: Specific event types to replay
            checkpoint_name: Name of checkpoint to track progress
            batch_size: Number of events to process in each batch
            
        Returns:
            Replay ID for tracking
        """
        if not self._initialized:
            await self.initialize()
        
        replay_id = str(uuid.uuid4())
        logger.info(f"Starting event replay {replay_id}")
        
        try:
            # Get checkpoint if specified
            checkpoint = None
            if checkpoint_name:
                checkpoint = await self.event_store.get_checkpoint(checkpoint_name)
                if checkpoint:
                    from_timestamp = checkpoint.timestamp
                    logger.info(f"Resuming replay from checkpoint {checkpoint_name}")
            
            # Determine event types to replay
            types_to_replay = event_types or list(EventType)
            
            total_events = 0
            last_event_id = None
            
            # Replay events for each type
            for event_type in types_to_replay:
                events = await self.event_store.get_events_by_type(
                    event_type,
                    from_timestamp=from_timestamp,
                    to_timestamp=to_timestamp,
                    apply_migrations=True
                )
                
                # Process events in batches
                for i in range(0, len(events), batch_size):
                    batch = events[i:i + batch_size]
                    
                    for event in batch:
                        try:
                            # Add replay metadata
                            event.metadata = event.metadata or {}
                            event.metadata['replay_id'] = replay_id
                            
                            await replay_handler(event)
                            last_event_id = event.id
                            total_events += 1
                            
                        except Exception as e:
                            logger.error(f"Error replaying event {event.id}: {e}")
                            raise EventReplayError(f"Replay failed at event {event.id}: {e}")
                    
                    # Update checkpoint after each batch
                    if checkpoint_name and last_event_id:
                        checkpoint = EventCheckpoint(
                            id=str(uuid.uuid4()),
                            name=checkpoint_name,
                            timestamp=datetime.now(timezone.utc),
                            last_event_id=last_event_id,
                            event_count=total_events,
                            metadata={'replay_id': replay_id}
                        )
                        await self.event_store.create_checkpoint(checkpoint)
            
            logger.info(f"Event replay {replay_id} completed: {total_events} events processed")
            return replay_id
            
        except Exception as e:
            logger.error(f"Event replay {replay_id} failed: {e}")
            raise
    
    async def rebuild_aggregate(
        self,
        aggregate_id: str,
        aggregate_builder: Callable[[List[Event]], Any],
        use_snapshots: bool = True
    ) -> Any:
        """
        Rebuild an aggregate from its event history.
        
        Args:
            aggregate_id: ID of the aggregate to rebuild
            aggregate_builder: Function that builds aggregate from events
            use_snapshots: Whether to use snapshots for optimization
            
        Returns:
            Rebuilt aggregate
        """
        if not self._initialized:
            await self.initialize()
        
        start_version = 0
        base_state = None
        
        # Try to get latest snapshot if enabled
        if use_snapshots:
            snapshot = await self.event_store.get_latest_snapshot(aggregate_id)
            if snapshot:
                start_version = snapshot.version + 1
                base_state = snapshot.data
                logger.debug(f"Using snapshot at version {snapshot.version} for aggregate {aggregate_id}")
        
        # Get events since snapshot
        events = await self.event_store.get_events_by_aggregate(
            aggregate_id,
            from_version=start_version,
            apply_migrations=True
        )
        
        # Build aggregate
        if base_state and events:
            # Combine snapshot with events
            aggregate = aggregate_builder(events, base_state)
        elif events:
            # Build from events only
            aggregate = aggregate_builder(events)
        else:
            # No events found
            logger.warning(f"No events found for aggregate {aggregate_id}")
            return None
        
        logger.info(f"Rebuilt aggregate {aggregate_id} from {len(events)} events")
        return aggregate
    
    async def create_snapshot(
        self,
        aggregate_id: str,
        aggregate_type: str,
        version: int,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create a snapshot of an aggregate."""
        snapshot = EventSnapshot(
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            version=version,
            timestamp=datetime.now(timezone.utc),
            data=data,
            metadata=metadata
        )
        
        await self.event_store.store_snapshot(snapshot)
        logger.info(f"Created snapshot for aggregate {aggregate_id} at version {version}")
    
    def register_migrator(self, migrator: EventMigrator) -> None:
        """Register an event migrator."""
        self.event_store.register_migrator(migrator)
    
    async def get_audit_trail(
        self,
        aggregate_id: Optional[str] = None,
        event_type: Optional[Union[str, EventType]] = None,
        from_timestamp: Optional[datetime] = None,
        to_timestamp: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Event]:
        """
        Get audit trail of events based on various criteria.
        
        Args:
            aggregate_id: Filter by aggregate ID
            event_type: Filter by event type
            from_timestamp: Start timestamp
            to_timestamp: End timestamp
            correlation_id: Filter by correlation ID
            limit: Maximum number of events
            
        Returns:
            List of events matching criteria
        """
        if not self._initialized:
            await self.initialize()
        
        if aggregate_id:
            return await self.event_store.get_events_by_aggregate(
                aggregate_id,
                apply_migrations=True
            )
        elif event_type:
            return await self.event_store.get_events_by_type(
                event_type,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                limit=limit,
                apply_migrations=True
            )
        else:
            # Get all events (implement if needed)
            logger.warning("Getting all events not implemented - use specific filters")
            return []


# Global event sourcing service instance
_event_sourcing_service: Optional[EventSourcingService] = None


async def get_event_sourcing_service() -> EventSourcingService:
    """Get the global event sourcing service instance."""
    global _event_sourcing_service
    if _event_sourcing_service is None:
        _event_sourcing_service = EventSourcingService()
        await _event_sourcing_service.initialize()
    return _event_sourcing_service