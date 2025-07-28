"""
Configuration Management API Endpoints

This module provides REST API endpoints for managing application configuration
with support for dynamic updates, environment-specific settings, and validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from shared.config_service import (
    get_config_service,
    ConfigurationService,
    ConfigScope,
    ConfigEntry,
    ConfigChange
)
from shared.config_schemas import ALL_CONFIG_SCHEMAS, get_sensitive_configs
from api.core.dependencies import get_current_user, require_admin
from shared.models.user import User

router = APIRouter(prefix="/config", tags=["configuration"])


# Request/Response Models
class ConfigValueRequest(BaseModel):
    """Request model for setting configuration values."""
    key: str = Field(..., description="Configuration key")
    value: Any = Field(..., description="Configuration value")
    scope: ConfigScope = Field(ConfigScope.GLOBAL, description="Configuration scope")
    environment: Optional[str] = Field(None, description="Target environment")


class ConfigValueResponse(BaseModel):
    """Response model for configuration values."""
    key: str
    value: Any
    scope: ConfigScope
    environment: str
    version: int
    created_at: datetime
    updated_at: datetime
    updated_by: str
    metadata: Dict[str, Any]


class ConfigListResponse(BaseModel):
    """Response model for configuration lists."""
    configurations: List[ConfigValueResponse]
    total_count: int
    filtered_count: int


class ConfigHistoryResponse(BaseModel):
    """Response model for configuration history."""
    key: str
    history: List[Dict[str, Any]]


class ConfigStatsResponse(BaseModel):
    """Response model for configuration statistics."""
    total_configurations: int
    configurations_by_scope: Dict[str, int]
    configurations_by_environment: Dict[str, int]
    sensitive_configurations: int
    required_configurations: int
    schema_count: int


@router.get("/", response_model=ConfigListResponse)
async def list_configurations(
    scope: Optional[ConfigScope] = Query(None, description="Filter by scope"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    pattern: Optional[str] = Query(None, description="Key pattern to match"),
    include_sensitive: bool = Query(False, description="Include sensitive values"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(get_current_user),
    config_service: ConfigurationService = Depends(get_config_service)
):
    """
    List configuration entries with optional filtering.
    
    Requires authentication. Sensitive values are redacted unless user is admin
    and explicitly requests them.
    """
    try:
        # Get all matching configurations
        entries = await config_service.list_configs(scope, environment, pattern)
        
        # Check if user can view sensitive configurations
        can_view_sensitive = (
            current_user.is_admin and include_sensitive
        )
        
        # Get sensitive configuration keys
        sensitive_keys = set(get_sensitive_configs())
        
        # Convert to response format
        configurations = []
        for entry in entries[offset:offset + limit]:
            # Redact sensitive values if necessary
            value = entry.value
            if entry.key in sensitive_keys and not can_view_sensitive:
                value = "***REDACTED***"
            
            config_response = ConfigValueResponse(
                key=entry.key,
                value=value,
                scope=entry.scope,
                environment=entry.environment,
                version=entry.version,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
                updated_by=entry.updated_by,
                metadata={
                    "description": entry.metadata.description,
                    "config_type": entry.metadata.config_type.value,
                    "required": entry.metadata.required,
                    "sensitive": entry.metadata.sensitive
                }
            )
            configurations.append(config_response)
        
        return ConfigListResponse(
            configurations=configurations,
            total_count=len(entries),
            filtered_count=len(configurations)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list configurations: {str(e)}"
        )


@router.get("/{key}", response_model=ConfigValueResponse)
async def get_configuration(
    key: str,
    scope: ConfigScope = Query(ConfigScope.GLOBAL, description="Configuration scope"),
    environment: Optional[str] = Query(None, description="Target environment"),
    include_sensitive: bool = Query(False, description="Include sensitive value"),
    current_user: User = Depends(get_current_user),
    config_service: ConfigurationService = Depends(get_config_service)
):
    """
    Get a specific configuration value.
    
    Requires authentication. Sensitive values are redacted unless user is admin
    and explicitly requests them.
    """
    try:
        entry = await config_service.get_config_entry(key, scope, environment)
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration not found: {key}"
            )
        
        # Check if user can view sensitive configurations
        can_view_sensitive = (
            current_user.is_admin and include_sensitive
        )
        
        # Get sensitive configuration keys
        sensitive_keys = set(get_sensitive_configs())
        
        # Redact sensitive values if necessary
        value = entry.value
        if entry.key in sensitive_keys and not can_view_sensitive:
            value = "***REDACTED***"
        
        return ConfigValueResponse(
            key=entry.key,
            value=value,
            scope=entry.scope,
            environment=entry.environment,
            version=entry.version,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
            updated_by=entry.updated_by,
            metadata={
                "description": entry.metadata.description,
                "config_type": entry.metadata.config_type.value,
                "required": entry.metadata.required,
                "sensitive": entry.metadata.sensitive
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration: {str(e)}"
        )


@router.post("/", response_model=ConfigValueResponse)
async def set_configuration(
    request: ConfigValueRequest,
    current_user: User = Depends(require_admin),
    config_service: ConfigurationService = Depends(get_config_service)
):
    """
    Set a configuration value.
    
    Requires admin privileges. Validates the configuration against registered schema.
    """
    try:
        await config_service.set_config(
            key=request.key,
            value=request.value,
            scope=request.scope,
            environment=request.environment,
            updated_by=current_user.username
        )
        
        # Return the updated configuration
        entry = await config_service.get_config_entry(
            request.key, request.scope, request.environment
        )
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Configuration was set but could not be retrieved"
            )
        
        return ConfigValueResponse(
            key=entry.key,
            value=entry.value,
            scope=entry.scope,
            environment=entry.environment,
            version=entry.version,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
            updated_by=entry.updated_by,
            metadata={
                "description": entry.metadata.description,
                "config_type": entry.metadata.config_type.value,
                "required": entry.metadata.required,
                "sensitive": entry.metadata.sensitive
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration value: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set configuration: {str(e)}"
        )


@router.put("/{key}", response_model=ConfigValueResponse)
async def update_configuration(
    key: str,
    value: Any,
    scope: ConfigScope = Query(ConfigScope.GLOBAL, description="Configuration scope"),
    environment: Optional[str] = Query(None, description="Target environment"),
    current_user: User = Depends(require_admin),
    config_service: ConfigurationService = Depends(get_config_service)
):
    """
    Update a specific configuration value.
    
    Requires admin privileges. Validates the configuration against registered schema.
    """
    try:
        await config_service.set_config(
            key=key,
            value=value,
            scope=scope,
            environment=environment,
            updated_by=current_user.username
        )
        
        # Return the updated configuration
        entry = await config_service.get_config_entry(key, scope, environment)
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Configuration was updated but could not be retrieved"
            )
        
        return ConfigValueResponse(
            key=entry.key,
            value=entry.value,
            scope=entry.scope,
            environment=entry.environment,
            version=entry.version,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
            updated_by=entry.updated_by,
            metadata={
                "description": entry.metadata.description,
                "config_type": entry.metadata.config_type.value,
                "required": entry.metadata.required,
                "sensitive": entry.metadata.sensitive
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration value: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


@router.delete("/{key}")
async def delete_configuration(
    key: str,
    scope: ConfigScope = Query(ConfigScope.GLOBAL, description="Configuration scope"),
    environment: Optional[str] = Query(None, description="Target environment"),
    current_user: User = Depends(require_admin),
    config_service: ConfigurationService = Depends(get_config_service)
):
    """
    Delete a configuration entry.
    
    Requires admin privileges. Cannot delete required configurations.
    """
    try:
        # Check if configuration is required
        if key in ALL_CONFIG_SCHEMAS:
            metadata = ALL_CONFIG_SCHEMAS[key]
            if metadata.required:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot delete required configuration: {key}"
                )
        
        deleted = await config_service.delete_config(
            key=key,
            scope=scope,
            environment=environment,
            updated_by=current_user.username
        )
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration not found: {key}"
            )
        
        return {"message": f"Configuration deleted: {key}"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete configuration: {str(e)}"
        )


@router.get("/{key}/history", response_model=ConfigHistoryResponse)
async def get_configuration_history(
    key: str,
    scope: ConfigScope = Query(ConfigScope.GLOBAL, description="Configuration scope"),
    environment: Optional[str] = Query(None, description="Target environment"),
    limit: int = Query(10, ge=1, le=100, description="Maximum history entries"),
    current_user: User = Depends(get_current_user),
    config_service: ConfigurationService = Depends(get_config_service)
):
    """
    Get configuration change history for a specific key.
    
    Requires authentication. Sensitive values are redacted unless user is admin.
    """
    try:
        history = await config_service.get_config_history(
            key=key,
            scope=scope,
            environment=environment,
            limit=limit
        )
        
        # Check if user can view sensitive configurations
        can_view_sensitive = current_user.is_admin
        sensitive_keys = set(get_sensitive_configs())
        
        # Redact sensitive values if necessary
        if key in sensitive_keys and not can_view_sensitive:
            for entry in history:
                if 'value' in entry:
                    entry['value'] = "***REDACTED***"
        
        return ConfigHistoryResponse(
            key=key,
            history=history
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration history: {str(e)}"
        )


@router.get("/environments/{environment}/export")
async def export_environment_configuration(
    environment: str,
    include_sensitive: bool = Query(False, description="Include sensitive values"),
    current_user: User = Depends(require_admin),
    config_service: ConfigurationService = Depends(get_config_service)
):
    """
    Export all configurations for a specific environment.
    
    Requires admin privileges. Returns configuration as JSON.
    """
    try:
        config_dict = await config_service.export_configuration(
            environment=environment,
            include_sensitive=include_sensitive
        )
        
        return {
            "environment": environment,
            "configuration": config_dict,
            "exported_at": datetime.utcnow().isoformat(),
            "exported_by": current_user.username,
            "include_sensitive": include_sensitive
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export configuration: {str(e)}"
        )


@router.post("/environments/{environment}/import")
async def import_environment_configuration(
    environment: str,
    configuration: Dict[str, Any],
    current_user: User = Depends(require_admin),
    config_service: ConfigurationService = Depends(get_config_service)
):
    """
    Import configurations for a specific environment.
    
    Requires admin privileges. Validates all configurations before import.
    """
    try:
        await config_service.import_configuration(
            config_dict=configuration,
            environment=environment,
            updated_by=current_user.username
        )
        
        return {
            "message": f"Successfully imported {len(configuration)} configurations",
            "environment": environment,
            "imported_at": datetime.utcnow().isoformat(),
            "imported_by": current_user.username
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration data: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import configuration: {str(e)}"
        )


@router.get("/stats", response_model=ConfigStatsResponse)
async def get_configuration_stats(
    current_user: User = Depends(get_current_user),
    config_service: ConfigurationService = Depends(get_config_service)
):
    """
    Get configuration statistics and summary.
    
    Requires authentication.
    """
    try:
        # Get all configurations
        all_configs = await config_service.list_configs()
        
        # Count by scope
        scope_counts = {}
        for config in all_configs:
            scope = config.scope.value
            scope_counts[scope] = scope_counts.get(scope, 0) + 1
        
        # Count by environment
        env_counts = {}
        for config in all_configs:
            env = config.environment
            env_counts[env] = env_counts.get(env, 0) + 1
        
        # Count sensitive and required configurations
        sensitive_count = len(get_sensitive_configs())
        required_count = sum(
            1 for metadata in ALL_CONFIG_SCHEMAS.values()
            if metadata.required
        )
        
        return ConfigStatsResponse(
            total_configurations=len(all_configs),
            configurations_by_scope=scope_counts,
            configurations_by_environment=env_counts,
            sensitive_configurations=sensitive_count,
            required_configurations=required_count,
            schema_count=len(ALL_CONFIG_SCHEMAS)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration stats: {str(e)}"
        )


@router.get("/schema", response_model=Dict[str, Any])
async def get_configuration_schema(
    current_user: User = Depends(get_current_user)
):
    """
    Get the complete configuration schema.
    
    Requires authentication. Returns schema definitions for all configuration keys.
    """
    try:
        schema_dict = {}
        
        for key, metadata in ALL_CONFIG_SCHEMAS.items():
            schema_dict[key] = {
                "description": metadata.description,
                "type": metadata.config_type.value,
                "default_value": metadata.default_value,
                "required": metadata.required,
                "sensitive": metadata.sensitive,
                "validation_pattern": metadata.validation_pattern,
                "allowed_values": metadata.allowed_values,
                "min_value": metadata.min_value,
                "max_value": metadata.max_value
            }
        
        return {
            "schema": schema_dict,
            "total_keys": len(schema_dict),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration schema: {str(e)}"
        )