#!/usr/bin/env python3
"""
Configuration Initialization Script

This script initializes the configuration service with default schemas
and environment-specific configurations.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.config_service import get_config_service, ConfigScope
from shared.config_schemas import (
    ALL_CONFIG_SCHEMAS,
    ENVIRONMENT_OVERRIDES,
    get_environment_overrides
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def initialize_configuration_schemas():
    """Initialize all configuration schemas."""
    logger.info("Initializing configuration schemas...")
    
    config_service = await get_config_service()
    
    # Register all configuration schemas
    for key, metadata in ALL_CONFIG_SCHEMAS.items():
        await config_service.register_config_schema(key, metadata)
        logger.debug(f"Registered schema for: {key}")
    
    logger.info(f"Registered {len(ALL_CONFIG_SCHEMAS)} configuration schemas")


async def initialize_default_configurations():
    """Initialize default configurations from schemas."""
    logger.info("Initializing default configurations...")
    
    config_service = await get_config_service()
    
    # Set default values for all configurations
    for key, metadata in ALL_CONFIG_SCHEMAS.items():
        if metadata.default_value is not None:
            # Check if configuration already exists
            existing = await config_service.get_config_entry(key)
            if not existing:
                await config_service.set_config(
                    key=key,
                    value=metadata.default_value,
                    scope=ConfigScope.GLOBAL,
                    updated_by="initialization_script"
                )
                logger.debug(f"Set default configuration: {key} = {metadata.default_value}")
    
    logger.info("Default configurations initialized")


async def initialize_environment_configurations():
    """Initialize environment-specific configurations."""
    environments = ["development", "staging", "production", "testing"]
    
    config_service = await get_config_service()
    
    for environment in environments:
        logger.info(f"Initializing configurations for environment: {environment}")
        
        overrides = get_environment_overrides(environment)
        
        for key, value in overrides.items():
            await config_service.set_config(
                key=key,
                value=value,
                scope=ConfigScope.ENVIRONMENT,
                environment=environment,
                updated_by="initialization_script"
            )
            logger.debug(f"Set {environment} configuration: {key} = {value}")
        
        logger.info(f"Initialized {len(overrides)} configurations for {environment}")


async def load_environment_variables():
    """Load configuration from environment variables."""
    logger.info("Loading configuration from environment variables...")
    
    config_service = await get_config_service()
    loaded_count = 0
    
    for key, metadata in ALL_CONFIG_SCHEMAS.items():
        env_value = os.getenv(key)
        if env_value is not None:
            # Convert environment variable to appropriate type
            if metadata.config_type.value == "boolean":
                value = env_value.lower() in ('true', '1', 'yes', 'on')
            elif metadata.config_type.value == "integer":
                try:
                    value = int(env_value)
                except ValueError:
                    logger.warning(f"Invalid integer value for {key}: {env_value}")
                    continue
            elif metadata.config_type.value == "float":
                try:
                    value = float(env_value)
                except ValueError:
                    logger.warning(f"Invalid float value for {key}: {env_value}")
                    continue
            elif metadata.config_type.value == "list":
                value = [item.strip() for item in env_value.split(',')]
            elif metadata.config_type.value == "json":
                import json
                try:
                    value = json.loads(env_value)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON value for {key}: {env_value}")
                    continue
            else:
                value = env_value
            
            await config_service.set_config(
                key=key,
                value=value,
                scope=ConfigScope.GLOBAL,
                updated_by="environment_variables"
            )
            loaded_count += 1
            logger.debug(f"Loaded from environment: {key}")
    
    logger.info(f"Loaded {loaded_count} configurations from environment variables")


async def validate_required_configurations():
    """Validate that all required configurations are set."""
    logger.info("Validating required configurations...")
    
    config_service = await get_config_service()
    missing_configs = []
    
    for key, metadata in ALL_CONFIG_SCHEMAS.items():
        if metadata.required:
            value = await config_service.get_config(key)
            if value is None:
                missing_configs.append(key)
    
    if missing_configs:
        logger.error(f"Missing required configurations: {missing_configs}")
        return False
    
    logger.info("All required configurations are present")
    return True


async def display_configuration_summary():
    """Display a summary of current configuration."""
    logger.info("Configuration Summary:")
    
    config_service = await get_config_service()
    
    # Get configurations by environment
    environments = ["development", "staging", "production", "testing"]
    
    for environment in environments:
        configs = await config_service.get_environment_configs(environment)
        if configs:
            logger.info(f"  {environment.upper()}: {len(configs)} configurations")
    
    # Get global configurations
    global_configs = await config_service.list_configs(scope=ConfigScope.GLOBAL)
    logger.info(f"  GLOBAL: {len(global_configs)} configurations")
    
    # Count sensitive configurations
    sensitive_count = sum(
        1 for metadata in ALL_CONFIG_SCHEMAS.values()
        if metadata.sensitive
    )
    logger.info(f"  SENSITIVE: {sensitive_count} configurations")


async def export_configuration_template():
    """Export configuration template for documentation."""
    logger.info("Exporting configuration template...")
    
    template_path = project_root / "config_template.md"
    
    with open(template_path, 'w') as f:
        f.write("# AI Opportunity Browser Configuration Reference\n\n")
        f.write("This document describes all available configuration options.\n\n")
        
        # Group by category
        categories = {
            "Application": ["APP_NAME", "VERSION", "ENVIRONMENT", "DEBUG", "HOST", "PORT"],
            "Security": [k for k in ALL_CONFIG_SCHEMAS.keys() if k.startswith(("SECRET", "ALGORITHM", "ACCESS", "PASSWORD", "MAX_LOGIN", "ACCOUNT"))],
            "Database": [k for k in ALL_CONFIG_SCHEMAS.keys() if k.startswith("DATABASE")],
            "Redis": [k for k in ALL_CONFIG_SCHEMAS.keys() if k.startswith("REDIS")],
            "Vector Database": [k for k in ALL_CONFIG_SCHEMAS.keys() if k.startswith(("PINECONE", "VECTOR"))],
            "Rate Limiting": [k for k in ALL_CONFIG_SCHEMAS.keys() if k.startswith("RATE_LIMIT")],
            "External APIs": [k for k in ALL_CONFIG_SCHEMAS.keys() if k.endswith(("_API_KEY", "_CLIENT_ID", "_CLIENT_SECRET", "_TOKEN"))],
            "AI/ML": [k for k in ALL_CONFIG_SCHEMAS.keys() if k.startswith(("DEFAULT_AI", "DEFAULT_EMBEDDING", "DEFAULT_CHAT", "MAX_TOKENS", "AI_"))],
            "Event Bus": [k for k in ALL_CONFIG_SCHEMAS.keys() if k.startswith("EVENT")],
            "Agents": [k for k in ALL_CONFIG_SCHEMAS.keys() if k.startswith("AGENT")],
            "Data Ingestion": [k for k in ALL_CONFIG_SCHEMAS.keys() if k.startswith(("INGESTION", "MAX_SIGNAL", "DUPLICATE", "QUALITY"))],
            "Logging": [k for k in ALL_CONFIG_SCHEMAS.keys() if k.startswith("LOG")],
            "CORS": [k for k in ALL_CONFIG_SCHEMAS.keys() if k.startswith("ALLOW")]
        }
        
        for category, keys in categories.items():
            if not keys:
                continue
                
            f.write(f"## {category}\n\n")
            
            for key in keys:
                if key in ALL_CONFIG_SCHEMAS:
                    metadata = ALL_CONFIG_SCHEMAS[key]
                    f.write(f"### {key}\n\n")
                    f.write(f"- **Description**: {metadata.description}\n")
                    f.write(f"- **Type**: {metadata.config_type.value}\n")
                    f.write(f"- **Default**: {metadata.default_value}\n")
                    f.write(f"- **Required**: {'Yes' if metadata.required else 'No'}\n")
                    if metadata.sensitive:
                        f.write(f"- **Sensitive**: Yes\n")
                    if metadata.allowed_values:
                        f.write(f"- **Allowed Values**: {', '.join(map(str, metadata.allowed_values))}\n")
                    if metadata.min_value is not None:
                        f.write(f"- **Minimum**: {metadata.min_value}\n")
                    if metadata.max_value is not None:
                        f.write(f"- **Maximum**: {metadata.max_value}\n")
                    f.write("\n")
        
        # Environment overrides
        f.write("## Environment-Specific Overrides\n\n")
        for environment, overrides in ENVIRONMENT_OVERRIDES.items():
            f.write(f"### {environment.upper()}\n\n")
            for key, value in overrides.items():
                f.write(f"- **{key}**: {value}\n")
            f.write("\n")
    
    logger.info(f"Configuration template exported to: {template_path}")


async def main():
    """Main initialization function."""
    logger.info("Starting configuration initialization...")
    
    try:
        # Initialize configuration service
        await initialize_configuration_schemas()
        await initialize_default_configurations()
        await initialize_environment_configurations()
        await load_environment_variables()
        
        # Validate configuration
        if not await validate_required_configurations():
            logger.error("Configuration validation failed")
            return 1
        
        # Display summary
        await display_configuration_summary()
        
        # Export template
        await export_configuration_template()
        
        logger.info("Configuration initialization completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Configuration initialization failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)