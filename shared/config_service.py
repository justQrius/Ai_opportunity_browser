"""
Configuration Service for AI Opportunity Browser

This module provides a centralized configuration service with support for:
- Dynamic configuration updates without restarts
- Environment-specific configuration management
- Configuration versioning and rollback
- Real-time configuration change notifications
- Configuration validation and type safety
- Secrets management integration
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import asynccontextmanager

import redis.asyncio as redis
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

from .event_bus import publish_event
from .database import get_redis_client

logger = logging.getLogger(__name__)


class ConfigScope(str, Enum):
    """Configuration scope levels."""
    GLOBAL = "global"
    ENVIRONMENT = "environment"
    SERVICE = "service"
    USER = "user"


class ConfigType(str, Enum):
    """Configuration value types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    LIST = "list"
    SECRET = "secret"


@dataclass
class ConfigChange:
    """Represents a configuration change event."""
    key: str
    old_value: Any
    new_value: Any
    scope: ConfigScope
    environment: str
    changed_by: str
    timestamp: datetime
    change_id: str


@dataclass
class ConfigMetadata:
    """Metadata for configuration entries."""
    description: str
    config_type: ConfigType
    default_value: Any
    required: bool = False
    sensitive: bool = False
    validation_pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None


class ConfigEntry(BaseModel):
    """Configuration entry with metadata and validation."""
    key: str
    value: Any
    scope: ConfigScope
    environment: str
    metadata: ConfigMetadata
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: str = "system"
    
    @validator('value')
    def validate_value(cls, v, values):
        """Validate configuration value based on metadata."""
        if 'metadata' not in values:
            return v
        
        metadata = values['metadata']
        
        # Type validation
        if metadata.config_type == ConfigType.INTEGER:
            if not isinstance(v, int):
                try:
                    v = int(v)
                except (ValueError, TypeError):
                    raise ValueError(f"Value must be an integer")
        elif metadata.config_type == ConfigType.FLOAT:
            if not isinstance(v, (int, float)):
                try:
                    v = float(v)
                except (ValueError, TypeError):
                    raise ValueError(f"Value must be a number")
        elif metadata.config_type == ConfigType.BOOLEAN:
            if not isinstance(v, bool):
                if isinstance(v, str):
                    v = v.lower() in ('true', '1', 'yes', 'on')
                else:
                    v = bool(v)
        elif metadata.config_type == ConfigType.JSON:
            if isinstance(v, str):
                try:
                    v = json.loads(v)
                except json.JSONDecodeError:
                    raise ValueError(f"Value must be valid JSON")
        elif metadata.config_type == ConfigType.LIST:
            if not isinstance(v, list):
                if isinstance(v, str):
                    v = [item.strip() for item in v.split(',')]
                else:
                    raise ValueError(f"Value must be a list")
        
        # Range validation
        if metadata.min_value is not None and isinstance(v, (int, float)):
            if v < metadata.min_value:
                raise ValueError(f"Value must be >= {metadata.min_value}")
        
        if metadata.max_value is not None and isinstance(v, (int, float)):
            if v > metadata.max_value:
                raise ValueError(f"Value must be <= {metadata.max_value}")
        
        # Allowed values validation
        if metadata.allowed_values and v not in metadata.allowed_values:
            raise ValueError(f"Value must be one of: {metadata.allowed_values}")
        
        return v


class ConfigurationService:
    """
    Centralized configuration service with dynamic updates and environment support.
    
    Features:
    - Dynamic configuration updates without service restarts
    - Environment-specific configuration management
    - Configuration change notifications via event bus
    - Configuration versioning and rollback capabilities
    - Type-safe configuration with validation
    - Secrets management integration
    """
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        default_environment: str = "development",
        enable_notifications: bool = True
    ):
        self.redis_client = redis_client
        self.default_environment = default_environment
        self.enable_notifications = enable_notifications
        
        # Configuration cache
        self._config_cache: Dict[str, ConfigEntry] = {}
        self._watchers: Dict[str, List[Callable]] = {}
        self._watch_tasks: List[asyncio.Task] = []
        self._initialized = False
        
        # Configuration schema registry
        self._schema_registry: Dict[str, ConfigMetadata] = {}
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> None:
        """Initialize the configuration service."""
        if self._initialized:
            return
        
        try:
            # Initialize Redis client if not provided
            if self.redis_client is None:
                self.redis_client = await get_redis_client()
            
            # Load configuration schema
            await self._load_schema()
            
            # Load existing configuration
            await self._load_configuration()
            
            # Start configuration watcher
            if self.enable_notifications:
                await self._start_config_watcher()
            
            self._initialized = True
            self.logger.info("Configuration service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize configuration service: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the configuration service."""
        if not self._initialized:
            return
        
        try:
            # Cancel watch tasks
            for task in self._watch_tasks:
                task.cancel()
            
            if self._watch_tasks:
                await asyncio.gather(*self._watch_tasks, return_exceptions=True)
            
            self._config_cache.clear()
            self._watchers.clear()
            self._initialized = False
            
            self.logger.info("Configuration service shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during configuration service shutdown: {e}")
    
    async def register_config_schema(
        self,
        key: str,
        metadata: ConfigMetadata
    ) -> None:
        """Register configuration schema for validation."""
        self._schema_registry[key] = metadata
        
        # Store schema in Redis for persistence
        schema_key = f"config:schema:{key}"
        schema_data = {
            "description": metadata.description,
            "config_type": metadata.config_type.value,
            "default_value": metadata.default_value,
            "required": metadata.required,
            "sensitive": metadata.sensitive,
            "validation_pattern": metadata.validation_pattern,
            "allowed_values": metadata.allowed_values,
            "min_value": metadata.min_value,
            "max_value": metadata.max_value
        }
        
        await self.redis_client.set(
            schema_key,
            json.dumps(schema_data, default=str),
            ex=86400 * 30  # 30 days
        )
        
        self.logger.debug(f"Registered configuration schema for key: {key}")
    
    async def set_config(
        self,
        key: str,
        value: Any,
        scope: ConfigScope = ConfigScope.GLOBAL,
        environment: Optional[str] = None,
        updated_by: str = "system"
    ) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
            scope: Configuration scope
            environment: Target environment (defaults to current)
            updated_by: User/system making the change
        """
        if not self._initialized:
            await self.initialize()
        
        environment = environment or self.default_environment
        config_key = self._build_config_key(key, scope, environment)
        
        # Get existing configuration
        old_entry = self._config_cache.get(config_key)
        old_value = old_entry.value if old_entry else None
        
        # Get or create metadata
        metadata = self._schema_registry.get(key)
        if not metadata:
            # Create default metadata
            metadata = ConfigMetadata(
                description=f"Configuration for {key}",
                config_type=self._infer_config_type(value),
                default_value=value
            )
        
        # Validate value before creating entry
        validated_value = self._validate_config_value(value, metadata)
        
        # Create new configuration entry
        new_entry = ConfigEntry(
            key=key,
            value=validated_value,
            scope=scope,
            environment=environment,
            metadata=metadata,
            version=(old_entry.version + 1) if old_entry else 1,
            updated_by=updated_by
        )
        
        # Store in Redis
        await self._store_config_entry(config_key, new_entry)
        
        # Update cache
        self._config_cache[config_key] = new_entry
        
        # Publish change event
        if self.enable_notifications and old_value != value:
            await self._publish_config_change(
                key, old_value, value, scope, environment, updated_by
            )
        
        # Notify watchers
        await self._notify_watchers(key, old_value, value)
        
        self.logger.info(f"Configuration updated: {key} = {value} (scope: {scope}, env: {environment})")
    
    async def get_config(
        self,
        key: str,
        scope: ConfigScope = ConfigScope.GLOBAL,
        environment: Optional[str] = None,
        default: Any = None
    ) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            scope: Configuration scope
            environment: Target environment (defaults to current)
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        if not self._initialized:
            await self.initialize()
        
        environment = environment or self.default_environment
        
        # Try to get from cache first
        config_key = self._build_config_key(key, scope, environment)
        entry = self._config_cache.get(config_key)
        
        if entry:
            return entry.value
        
        # Try to load from Redis
        entry = await self._load_config_entry(config_key)
        if entry:
            self._config_cache[config_key] = entry
            return entry.value
        
        # Try environment variable fallback
        env_value = os.getenv(key.upper())
        if env_value is not None:
            return self._convert_env_value(env_value, key)
        
        # Return default from schema or provided default
        metadata = self._schema_registry.get(key)
        if metadata and metadata.default_value is not None:
            return metadata.default_value
        
        return default
    
    async def get_config_entry(
        self,
        key: str,
        scope: ConfigScope = ConfigScope.GLOBAL,
        environment: Optional[str] = None
    ) -> Optional[ConfigEntry]:
        """Get full configuration entry with metadata."""
        if not self._initialized:
            await self.initialize()
        
        environment = environment or self.default_environment
        config_key = self._build_config_key(key, scope, environment)
        
        # Try cache first
        entry = self._config_cache.get(config_key)
        if entry:
            return entry
        
        # Load from Redis
        return await self._load_config_entry(config_key)
    
    async def delete_config(
        self,
        key: str,
        scope: ConfigScope = ConfigScope.GLOBAL,
        environment: Optional[str] = None,
        updated_by: str = "system"
    ) -> bool:
        """
        Delete a configuration entry.
        
        Returns:
            True if deleted, False if not found
        """
        if not self._initialized:
            await self.initialize()
        
        environment = environment or self.default_environment
        config_key = self._build_config_key(key, scope, environment)
        
        # Get existing value for change notification
        old_entry = self._config_cache.get(config_key)
        old_value = old_entry.value if old_entry else None
        
        # Delete from Redis
        deleted = await self.redis_client.delete(config_key) > 0
        
        if deleted:
            # Remove from cache
            self._config_cache.pop(config_key, None)
            
            # Publish change event
            if self.enable_notifications and old_value is not None:
                await self._publish_config_change(
                    key, old_value, None, scope, environment, updated_by
                )
            
            # Notify watchers
            await self._notify_watchers(key, old_value, None)
            
            self.logger.info(f"Configuration deleted: {key} (scope: {scope}, env: {environment})")
        
        return deleted
    
    async def list_configs(
        self,
        scope: Optional[ConfigScope] = None,
        environment: Optional[str] = None,
        pattern: Optional[str] = None
    ) -> List[ConfigEntry]:
        """
        List configuration entries matching criteria.
        
        Args:
            scope: Filter by scope (optional)
            environment: Filter by environment (optional)
            pattern: Key pattern to match (optional)
            
        Returns:
            List of matching configuration entries
        """
        if not self._initialized:
            await self.initialize()
        
        # Build search pattern
        search_pattern = "config:"
        if scope:
            search_pattern += f"{scope.value}:"
        else:
            search_pattern += "*:"
        
        if environment:
            search_pattern += f"{environment}:"
        else:
            search_pattern += "*:"
        
        if pattern:
            search_pattern += pattern
        else:
            search_pattern += "*"
        
        # Get matching keys from Redis
        keys = await self.redis_client.keys(search_pattern)
        
        # Filter out non-config keys (schema, history, timeline keys)
        config_keys = [
            key for key in keys 
            if not key.startswith(('config:schema:', 'config:history:', 'timeline:', 'event:'))
        ]
        
        # Load configuration entries
        entries = []
        for key in config_keys:
            try:
                entry = await self._load_config_entry(key)
                if entry:
                    entries.append(entry)
            except Exception as e:
                # Skip keys that can't be loaded as config entries
                self.logger.debug(f"Skipping key {key}: {e}")
                continue
        
        return sorted(entries, key=lambda x: x.key)
    
    async def watch_config_changes(
        self,
        keys: List[str],
        callback: Callable[[str, Any, Any], None]
    ) -> None:
        """
        Watch for configuration changes on specific keys.
        
        Args:
            keys: List of configuration keys to watch
            callback: Callback function called on changes (key, old_value, new_value)
        """
        for key in keys:
            if key not in self._watchers:
                self._watchers[key] = []
            self._watchers[key].append(callback)
        
        self.logger.info(f"Added watcher for configuration keys: {keys}")
    
    async def get_environment_configs(self, environment: str) -> Dict[str, Any]:
        """Get all configurations for a specific environment."""
        entries = await self.list_configs(environment=environment)
        return {entry.key: entry.value for entry in entries}
    
    async def export_configuration(
        self,
        environment: Optional[str] = None,
        include_sensitive: bool = False
    ) -> Dict[str, Any]:
        """
        Export configuration as a dictionary.
        
        Args:
            environment: Target environment (optional)
            include_sensitive: Include sensitive values
            
        Returns:
            Configuration dictionary
        """
        entries = await self.list_configs(environment=environment)
        
        config_dict = {}
        for entry in entries:
            if entry.metadata.sensitive and not include_sensitive:
                config_dict[entry.key] = "***REDACTED***"
            else:
                config_dict[entry.key] = entry.value
        
        return config_dict
    
    async def import_configuration(
        self,
        config_dict: Dict[str, Any],
        environment: Optional[str] = None,
        updated_by: str = "import"
    ) -> None:
        """
        Import configuration from a dictionary.
        
        Args:
            config_dict: Configuration dictionary
            environment: Target environment
            updated_by: User/system performing import
        """
        environment = environment or self.default_environment
        
        for key, value in config_dict.items():
            await self.set_config(
                key=key,
                value=value,
                environment=environment,
                updated_by=updated_by
            )
        
        self.logger.info(f"Imported {len(config_dict)} configuration entries for environment: {environment}")
    
    async def get_config_history(
        self,
        key: str,
        scope: ConfigScope = ConfigScope.GLOBAL,
        environment: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get configuration change history for a key."""
        environment = environment or self.default_environment
        history_key = f"config:history:{scope.value}:{environment}:{key}"
        
        # Get history from Redis sorted set
        history_data = await self.redis_client.zrevrange(
            history_key, 0, limit - 1, withscores=True
        )
        
        history = []
        for data, timestamp in history_data:
            try:
                entry = json.loads(data)
                entry['timestamp'] = datetime.fromtimestamp(timestamp, timezone.utc)
                history.append(entry)
            except json.JSONDecodeError:
                continue
        
        return history
    
    def _build_config_key(self, key: str, scope: ConfigScope, environment: str) -> str:
        """Build Redis key for configuration entry."""
        return f"config:{scope.value}:{environment}:{key}"
    
    def _infer_config_type(self, value: Any) -> ConfigType:
        """Infer configuration type from value."""
        if isinstance(value, bool):
            return ConfigType.BOOLEAN
        elif isinstance(value, int):
            return ConfigType.INTEGER
        elif isinstance(value, float):
            return ConfigType.FLOAT
        elif isinstance(value, list):
            return ConfigType.LIST
        elif isinstance(value, (dict, tuple)):
            return ConfigType.JSON
        else:
            return ConfigType.STRING
    
    def _validate_config_value(self, value: Any, metadata: ConfigMetadata) -> Any:
        """Validate configuration value based on metadata."""
        # Type validation
        if metadata.config_type == ConfigType.INTEGER:
            if not isinstance(value, int):
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Value must be an integer")
        elif metadata.config_type == ConfigType.FLOAT:
            if not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Value must be a number")
        elif metadata.config_type == ConfigType.BOOLEAN:
            if not isinstance(value, bool):
                if isinstance(value, str):
                    value = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    value = bool(value)
        elif metadata.config_type == ConfigType.JSON:
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    raise ValueError(f"Value must be valid JSON")
        elif metadata.config_type == ConfigType.LIST:
            if not isinstance(value, list):
                if isinstance(value, str):
                    value = [item.strip() for item in value.split(',')]
                else:
                    raise ValueError(f"Value must be a list")
        
        # Range validation
        if metadata.min_value is not None and isinstance(value, (int, float)):
            if value < metadata.min_value:
                raise ValueError(f"Value must be >= {metadata.min_value}")
        
        if metadata.max_value is not None and isinstance(value, (int, float)):
            if value > metadata.max_value:
                raise ValueError(f"Value must be <= {metadata.max_value}")
        
        # Allowed values validation
        if metadata.allowed_values and value not in metadata.allowed_values:
            raise ValueError(f"Value must be one of: {metadata.allowed_values}")
        
        return value
    
    def _convert_env_value(self, value: str, key: str) -> Any:
        """Convert environment variable value to appropriate type."""
        # Try to infer type from schema
        metadata = self._schema_registry.get(key)
        if metadata:
            if metadata.config_type == ConfigType.BOOLEAN:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif metadata.config_type == ConfigType.INTEGER:
                try:
                    return int(value)
                except ValueError:
                    pass
            elif metadata.config_type == ConfigType.FLOAT:
                try:
                    return float(value)
                except ValueError:
                    pass
            elif metadata.config_type == ConfigType.JSON:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    pass
            elif metadata.config_type == ConfigType.LIST:
                return [item.strip() for item in value.split(',')]
        
        return value
    
    async def _store_config_entry(self, config_key: str, entry: ConfigEntry) -> None:
        """Store configuration entry in Redis."""
        # Store main entry
        entry_data = entry.dict()
        entry_data['created_at'] = entry.created_at.isoformat()
        entry_data['updated_at'] = entry.updated_at.isoformat()
        entry_data['metadata'] = asdict(entry.metadata)
        
        await self.redis_client.set(
            config_key,
            json.dumps(entry_data, default=str),
            ex=86400 * 365  # 1 year
        )
        
        # Store in history
        history_key = f"config:history:{entry.scope.value}:{entry.environment}:{entry.key}"
        history_entry = {
            'value': entry.value,
            'version': entry.version,
            'updated_by': entry.updated_by,
            'change_id': f"{entry.key}_{entry.version}_{int(entry.updated_at.timestamp())}"
        }
        
        await self.redis_client.zadd(
            history_key,
            {json.dumps(history_entry, default=str): entry.updated_at.timestamp()}
        )
        
        # Keep only last 100 history entries
        await self.redis_client.zremrangebyrank(history_key, 0, -101)
        await self.redis_client.expire(history_key, 86400 * 90)  # 90 days
    
    async def _load_config_entry(self, config_key: str) -> Optional[ConfigEntry]:
        """Load configuration entry from Redis."""
        try:
            data = await self.redis_client.get(config_key)
            if not data:
                return None
            
            entry_data = json.loads(data)
            
            # Convert datetime strings back to datetime objects
            entry_data['created_at'] = datetime.fromisoformat(entry_data['created_at'])
            entry_data['updated_at'] = datetime.fromisoformat(entry_data['updated_at'])
            
            # Convert metadata dict back to ConfigMetadata
            metadata_data = entry_data['metadata']
            metadata = ConfigMetadata(
                description=metadata_data['description'],
                config_type=ConfigType(metadata_data['config_type']),
                default_value=metadata_data['default_value'],
                required=metadata_data.get('required', False),
                sensitive=metadata_data.get('sensitive', False),
                validation_pattern=metadata_data.get('validation_pattern'),
                allowed_values=metadata_data.get('allowed_values'),
                min_value=metadata_data.get('min_value'),
                max_value=metadata_data.get('max_value')
            )
            entry_data['metadata'] = metadata
            
            return ConfigEntry(**entry_data)
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Error loading configuration entry {config_key}: {e}")
            return None
    
    async def _load_configuration(self) -> None:
        """Load all configuration from Redis into cache."""
        try:
            keys = await self.redis_client.keys("config:*")
            
            for key in keys:
                if ":schema:" in key or ":history:" in key:
                    continue
                
                entry = await self._load_config_entry(key)
                if entry:
                    self._config_cache[key] = entry
            
            self.logger.info(f"Loaded {len(self._config_cache)} configuration entries")
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
    
    async def _load_schema(self) -> None:
        """Load configuration schema from Redis."""
        try:
            schema_keys = await self.redis_client.keys("config:schema:*")
            
            for schema_key in schema_keys:
                key = schema_key.replace("config:schema:", "")
                data = await self.redis_client.get(schema_key)
                
                if data:
                    schema_data = json.loads(data)
                    metadata = ConfigMetadata(
                        description=schema_data['description'],
                        config_type=ConfigType(schema_data['config_type']),
                        default_value=schema_data['default_value'],
                        required=schema_data.get('required', False),
                        sensitive=schema_data.get('sensitive', False),
                        validation_pattern=schema_data.get('validation_pattern'),
                        allowed_values=schema_data.get('allowed_values'),
                        min_value=schema_data.get('min_value'),
                        max_value=schema_data.get('max_value')
                    )
                    self._schema_registry[key] = metadata
            
            self.logger.info(f"Loaded {len(self._schema_registry)} configuration schemas")
            
        except Exception as e:
            self.logger.error(f"Error loading configuration schema: {e}")
    
    async def _start_config_watcher(self) -> None:
        """Start configuration change watcher."""
        task = asyncio.create_task(self._config_watch_loop())
        self._watch_tasks.append(task)
    
    async def _config_watch_loop(self) -> None:
        """Configuration change watch loop."""
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.psubscribe("__keyspace@0__:config:*")
            
            self.logger.info("Started configuration change watcher")
            
            async for message in pubsub.listen():
                if message['type'] == 'pmessage':
                    await self._handle_config_change_notification(message)
                    
        except asyncio.CancelledError:
            self.logger.info("Configuration watcher cancelled")
        except Exception as e:
            self.logger.error(f"Error in configuration watcher: {e}")
        finally:
            if 'pubsub' in locals():
                await pubsub.close()
    
    async def _handle_config_change_notification(self, message: Dict[str, Any]) -> None:
        """Handle Redis keyspace notification for configuration changes."""
        try:
            key = message['channel'].decode().replace('__keyspace@0__:', '')
            operation = message['data'].decode()
            
            if operation in ('set', 'del') and key.startswith('config:'):
                # Reload configuration entry
                if operation == 'set':
                    entry = await self._load_config_entry(key)
                    if entry:
                        old_entry = self._config_cache.get(key)
                        old_value = old_entry.value if old_entry else None
                        
                        self._config_cache[key] = entry
                        
                        # Notify watchers
                        await self._notify_watchers(entry.key, old_value, entry.value)
                elif operation == 'del':
                    old_entry = self._config_cache.pop(key, None)
                    if old_entry:
                        await self._notify_watchers(old_entry.key, old_entry.value, None)
                        
        except Exception as e:
            self.logger.error(f"Error handling configuration change notification: {e}")
    
    async def _notify_watchers(self, key: str, old_value: Any, new_value: Any) -> None:
        """Notify configuration watchers of changes."""
        watchers = self._watchers.get(key, [])
        
        for callback in watchers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(key, old_value, new_value)
                else:
                    callback(key, old_value, new_value)
            except Exception as e:
                self.logger.error(f"Error in configuration watcher callback: {e}")
    
    async def _publish_config_change(
        self,
        key: str,
        old_value: Any,
        new_value: Any,
        scope: ConfigScope,
        environment: str,
        updated_by: str
    ) -> None:
        """Publish configuration change event."""
        try:
            timestamp = datetime.now(timezone.utc)
            change = ConfigChange(
                key=key,
                old_value=old_value,
                new_value=new_value,
                scope=scope,
                environment=environment,
                changed_by=updated_by,
                timestamp=timestamp,
                change_id=f"{key}_{int(timestamp.timestamp())}"
            )
            
            # Convert to dict and handle datetime serialization
            change_dict = asdict(change)
            change_dict['timestamp'] = timestamp.isoformat()
            
            await publish_event(
                event_type="configuration.changed",
                payload=change_dict,
                source="configuration_service",
                correlation_id=change.change_id
            )
            
        except Exception as e:
            self.logger.error(f"Error publishing configuration change event: {e}")


# Global configuration service instance
_config_service: Optional[ConfigurationService] = None


async def get_config_service() -> ConfigurationService:
    """Get the global configuration service instance."""
    global _config_service
    if _config_service is None:
        _config_service = ConfigurationService()
        await _config_service.initialize()
    return _config_service


@asynccontextmanager
async def config_service_lifespan():
    """Context manager for configuration service lifecycle."""
    service = None
    try:
        service = await get_config_service()
        yield service
    finally:
        if service:
            await service.shutdown()


# Convenience functions
async def get_config(
    key: str,
    scope: ConfigScope = ConfigScope.GLOBAL,
    environment: Optional[str] = None,
    default: Any = None
) -> Any:
    """Convenience function to get configuration value."""
    service = await get_config_service()
    return await service.get_config(key, scope, environment, default)


async def set_config(
    key: str,
    value: Any,
    scope: ConfigScope = ConfigScope.GLOBAL,
    environment: Optional[str] = None,
    updated_by: str = "system"
) -> None:
    """Convenience function to set configuration value."""
    service = await get_config_service()
    await service.set_config(key, value, scope, environment, updated_by)


async def watch_config_changes(
    keys: List[str],
    callback: Callable[[str, Any, Any], None]
) -> None:
    """Convenience function to watch configuration changes."""
    service = await get_config_service()
    await service.watch_config_changes(keys, callback)