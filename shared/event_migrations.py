"""
Event Migrations for AI Opportunity Browser

This module contains concrete event migrators for handling schema evolution
and version upgrades in the event sourcing system.
"""

import logging
from typing import Dict, Any
from datetime import datetime, timezone

from .event_bus import Event, EventType
from .event_sourcing import EventMigrator, EventVersion

logger = logging.getLogger(__name__)


class OpportunityEventV1ToV2Migrator(EventMigrator):
    """
    Migrator for opportunity events from version 1.0 to 2.0.
    
    Changes in v2.0:
    - Added 'ai_solution_category' field
    - Renamed 'market_size' to 'market_size_estimate'
    - Added 'confidence_score' field
    """
    
    @property
    def from_version(self) -> str:
        return EventVersion.V1_0
    
    @property
    def to_version(self) -> str:
        return EventVersion.V2_0
    
    def can_migrate(self, event: Event) -> bool:
        """Check if this migrator can handle the event."""
        metadata = event.metadata or {}
        version = metadata.get('version', EventVersion.V1_0)
        
        return (
            version == self.from_version and
            event.event_type in [
                EventType.OPPORTUNITY_CREATED,
                EventType.OPPORTUNITY_UPDATED,
                EventType.OPPORTUNITY_VALIDATED
            ]
        )
    
    async def migrate(self, event: Event) -> Event:
        """Migrate opportunity event from v1.0 to v2.0."""
        logger.debug(f"Migrating opportunity event {event.id} from v1.0 to v2.0")
        
        # Create new payload with migrated fields
        new_payload = event.payload.copy()
        
        # Migrate market_size to market_size_estimate
        if 'market_size' in new_payload:
            new_payload['market_size_estimate'] = new_payload.pop('market_size')
        
        # Add default ai_solution_category if not present
        if 'ai_solution_category' not in new_payload:
            # Infer category from ai_solution_type if available
            ai_solution_type = new_payload.get('ai_solution_type', '')
            new_payload['ai_solution_category'] = self._infer_solution_category(ai_solution_type)
        
        # Add default confidence_score
        if 'confidence_score' not in new_payload:
            new_payload['confidence_score'] = 0.7  # Default confidence
        
        # Update metadata
        new_metadata = event.metadata.copy() if event.metadata else {}
        new_metadata['version'] = self.to_version
        new_metadata['migration_applied'] = f"{self.from_version}_to_{self.to_version}"
        new_metadata['migrated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Create migrated event
        migrated_event = Event(
            id=event.id,
            event_type=event.event_type,
            payload=new_payload,
            timestamp=event.timestamp,
            source=event.source,
            correlation_id=event.correlation_id,
            metadata=new_metadata
        )
        
        return migrated_event
    
    def _infer_solution_category(self, ai_solution_type: str) -> str:
        """Infer solution category from solution type."""
        type_lower = ai_solution_type.lower()
        
        if any(term in type_lower for term in ['nlp', 'text', 'language', 'chat', 'sentiment']):
            return 'natural_language_processing'
        elif any(term in type_lower for term in ['vision', 'image', 'video', 'ocr', 'detection']):
            return 'computer_vision'
        elif any(term in type_lower for term in ['recommend', 'suggest', 'personalization']):
            return 'recommendation_systems'
        elif any(term in type_lower for term in ['predict', 'forecast', 'analytics']):
            return 'predictive_analytics'
        elif any(term in type_lower for term in ['automat', 'workflow', 'process']):
            return 'automation'
        elif any(term in type_lower for term in ['optimiz', 'efficiency', 'resource']):
            return 'optimization'
        else:
            return 'machine_learning'


class UserEventV1ToV11Migrator(EventMigrator):
    """
    Migrator for user events from version 1.0 to 1.1.
    
    Changes in v1.1:
    - Added 'user_preferences' field
    - Added 'notification_settings' field
    - Standardized 'expertise_domains' format
    """
    
    @property
    def from_version(self) -> str:
        return EventVersion.V1_0
    
    @property
    def to_version(self) -> str:
        return EventVersion.V1_1
    
    def can_migrate(self, event: Event) -> bool:
        """Check if this migrator can handle the event."""
        metadata = event.metadata or {}
        version = metadata.get('version', EventVersion.V1_0)
        
        return (
            version == self.from_version and
            event.event_type in [
                EventType.USER_REGISTERED,
                EventType.USER_PROFILE_UPDATED,
                EventType.USER_REPUTATION_CHANGED
            ]
        )
    
    async def migrate(self, event: Event) -> Event:
        """Migrate user event from v1.0 to v1.1."""
        logger.debug(f"Migrating user event {event.id} from v1.0 to v1.1")
        
        new_payload = event.payload.copy()
        
        # Add default user_preferences
        if 'user_preferences' not in new_payload:
            new_payload['user_preferences'] = {
                'email_notifications': True,
                'push_notifications': True,
                'weekly_digest': True,
                'opportunity_alerts': True
            }
        
        # Add default notification_settings
        if 'notification_settings' not in new_payload:
            new_payload['notification_settings'] = {
                'frequency': 'immediate',
                'channels': ['email'],
                'quiet_hours': {
                    'enabled': False,
                    'start': '22:00',
                    'end': '08:00'
                }
            }
        
        # Standardize expertise_domains format
        if 'expertise_domains' in new_payload:
            domains = new_payload['expertise_domains']
            if isinstance(domains, str):
                # Convert comma-separated string to list
                new_payload['expertise_domains'] = [d.strip() for d in domains.split(',')]
            elif isinstance(domains, list):
                # Ensure all items are strings and trimmed
                new_payload['expertise_domains'] = [str(d).strip() for d in domains]
        
        # Update metadata
        new_metadata = event.metadata.copy() if event.metadata else {}
        new_metadata['version'] = self.to_version
        new_metadata['migration_applied'] = f"{self.from_version}_to_{self.to_version}"
        new_metadata['migrated_at'] = datetime.now(timezone.utc).isoformat()
        
        migrated_event = Event(
            id=event.id,
            event_type=event.event_type,
            payload=new_payload,
            timestamp=event.timestamp,
            source=event.source,
            correlation_id=event.correlation_id,
            metadata=new_metadata
        )
        
        return migrated_event


class ValidationEventV1ToV2Migrator(EventMigrator):
    """
    Migrator for validation events from version 1.0 to 2.0.
    
    Changes in v2.0:
    - Added 'validation_criteria' field with structured criteria
    - Added 'evidence_quality_score' field
    - Restructured 'validation_result' to include sub-scores
    """
    
    @property
    def from_version(self) -> str:
        return EventVersion.V1_0
    
    @property
    def to_version(self) -> str:
        return EventVersion.V2_0
    
    def can_migrate(self, event: Event) -> bool:
        """Check if this migrator can handle the event."""
        metadata = event.metadata or {}
        version = metadata.get('version', EventVersion.V1_0)
        
        return (
            version == self.from_version and
            event.event_type in [
                EventType.VALIDATION_SUBMITTED,
                EventType.VALIDATION_APPROVED,
                EventType.VALIDATION_REJECTED
            ]
        )
    
    async def migrate(self, event: Event) -> Event:
        """Migrate validation event from v1.0 to v2.0."""
        logger.debug(f"Migrating validation event {event.id} from v1.0 to v2.0")
        
        new_payload = event.payload.copy()
        
        # Add structured validation_criteria
        if 'validation_criteria' not in new_payload:
            validation_type = new_payload.get('validation_type', 'general')
            new_payload['validation_criteria'] = self._get_default_criteria(validation_type)
        
        # Add evidence_quality_score
        if 'evidence_quality_score' not in new_payload:
            # Infer from existing evidence or set default
            evidence_links = new_payload.get('evidence_links', [])
            new_payload['evidence_quality_score'] = min(len(evidence_links) * 0.2, 1.0)
        
        # Restructure validation_result if it's a simple score
        if 'validation_score' in new_payload and 'validation_result' not in new_payload:
            score = new_payload['validation_score']
            new_payload['validation_result'] = {
                'overall_score': score,
                'market_demand_score': score,
                'technical_feasibility_score': score,
                'business_viability_score': score,
                'ai_suitability_score': score
            }
        
        # Update metadata
        new_metadata = event.metadata.copy() if event.metadata else {}
        new_metadata['version'] = self.to_version
        new_metadata['migration_applied'] = f"{self.from_version}_to_{self.to_version}"
        new_metadata['migrated_at'] = datetime.now(timezone.utc).isoformat()
        
        migrated_event = Event(
            id=event.id,
            event_type=event.event_type,
            payload=new_payload,
            timestamp=event.timestamp,
            source=event.source,
            correlation_id=event.correlation_id,
            metadata=new_metadata
        )
        
        return migrated_event
    
    def _get_default_criteria(self, validation_type: str) -> Dict[str, Any]:
        """Get default validation criteria based on type."""
        base_criteria = {
            'market_demand': {
                'weight': 0.3,
                'description': 'Evidence of market demand for this solution'
            },
            'technical_feasibility': {
                'weight': 0.25,
                'description': 'Technical feasibility with current AI capabilities'
            },
            'business_viability': {
                'weight': 0.25,
                'description': 'Business model and revenue potential'
            },
            'ai_suitability': {
                'weight': 0.2,
                'description': 'Suitability for AI-based solution'
            }
        }
        
        if validation_type == 'technical_feasibility':
            base_criteria['technical_feasibility']['weight'] = 0.5
            base_criteria['market_demand']['weight'] = 0.2
            base_criteria['business_viability']['weight'] = 0.2
            base_criteria['ai_suitability']['weight'] = 0.1
        elif validation_type == 'market_demand':
            base_criteria['market_demand']['weight'] = 0.5
            base_criteria['technical_feasibility']['weight'] = 0.2
            base_criteria['business_viability']['weight'] = 0.2
            base_criteria['ai_suitability']['weight'] = 0.1
        
        return base_criteria


class AgentEventV1ToV11Migrator(EventMigrator):
    """
    Migrator for agent events from version 1.0 to 1.1.
    
    Changes in v1.1:
    - Added 'performance_metrics' field
    - Added 'resource_usage' field
    - Standardized 'task_result' format
    """
    
    @property
    def from_version(self) -> str:
        return EventVersion.V1_0
    
    @property
    def to_version(self) -> str:
        return EventVersion.V1_1
    
    def can_migrate(self, event: Event) -> bool:
        """Check if this migrator can handle the event."""
        metadata = event.metadata or {}
        version = metadata.get('version', EventVersion.V1_0)
        
        return (
            version == self.from_version and
            event.event_type in [
                EventType.AGENT_STARTED,
                EventType.AGENT_STOPPED,
                EventType.AGENT_ERROR,
                EventType.AGENT_TASK_COMPLETED
            ]
        )
    
    async def migrate(self, event: Event) -> Event:
        """Migrate agent event from v1.0 to v1.1."""
        logger.debug(f"Migrating agent event {event.id} from v1.0 to v1.1")
        
        new_payload = event.payload.copy()
        
        # Add performance_metrics for task completion events
        if (event.event_type == EventType.AGENT_TASK_COMPLETED and 
            'performance_metrics' not in new_payload):
            duration = new_payload.get('duration_seconds', 0)
            success = new_payload.get('success', True)
            
            new_payload['performance_metrics'] = {
                'execution_time_seconds': duration,
                'success_rate': 1.0 if success else 0.0,
                'throughput_items_per_second': 1.0 / max(duration, 0.1),
                'error_count': 0 if success else 1
            }
        
        # Add resource_usage
        if 'resource_usage' not in new_payload:
            new_payload['resource_usage'] = {
                'cpu_usage_percent': 0.0,
                'memory_usage_mb': 0.0,
                'network_io_kb': 0.0,
                'disk_io_kb': 0.0
            }
        
        # Standardize task_result format
        if 'result' in new_payload and event.event_type == EventType.AGENT_TASK_COMPLETED:
            result = new_payload['result']
            if not isinstance(result, dict):
                new_payload['result'] = {
                    'data': result,
                    'status': 'completed',
                    'message': 'Task completed successfully'
                }
        
        # Update metadata
        new_metadata = event.metadata.copy() if event.metadata else {}
        new_metadata['version'] = self.to_version
        new_metadata['migration_applied'] = f"{self.from_version}_to_{self.to_version}"
        new_metadata['migrated_at'] = datetime.now(timezone.utc).isoformat()
        
        migrated_event = Event(
            id=event.id,
            event_type=event.event_type,
            payload=new_payload,
            timestamp=event.timestamp,
            source=event.source,
            correlation_id=event.correlation_id,
            metadata=new_metadata
        )
        
        return migrated_event


def get_all_migrators() -> list[EventMigrator]:
    """Get all available event migrators."""
    return [
        OpportunityEventV1ToV2Migrator(),
        UserEventV1ToV11Migrator(),
        ValidationEventV1ToV2Migrator(),
        AgentEventV1ToV11Migrator()
    ]


async def register_all_migrators(event_sourcing_service) -> None:
    """Register all migrators with the event sourcing service."""
    migrators = get_all_migrators()
    
    for migrator in migrators:
        event_sourcing_service.register_migrator(migrator)
    
    logger.info(f"Registered {len(migrators)} event migrators")