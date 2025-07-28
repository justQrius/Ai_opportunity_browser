#!/usr/bin/env python3
"""
Configuration Service Test Script

This script tests the configuration service functionality including:
- Dynamic configuration updates
- Environment-specific handling
- Configuration validation
- Change notifications
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.config_service import (
    get_config_service,
    ConfigScope,
    ConfigMetadata,
    ConfigType
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_basic_configuration():
    """Test basic configuration operations."""
    logger.info("Testing basic configuration operations...")
    
    config_service = await get_config_service()
    
    # Test setting and getting configuration
    await config_service.set_config(
        key="TEST_STRING",
        value="Hello World",
        updated_by="test_script"
    )
    
    value = await config_service.get_config("TEST_STRING")
    assert value == "Hello World", f"Expected 'Hello World', got {value}"
    logger.info("✅ Basic string configuration test passed")
    
    # Test different data types
    await config_service.set_config("TEST_INTEGER", 42, updated_by="test_script")
    await config_service.set_config("TEST_BOOLEAN", True, updated_by="test_script")
    await config_service.set_config("TEST_LIST", ["a", "b", "c"], updated_by="test_script")
    await config_service.set_config("TEST_DICT", {"key": "value"}, updated_by="test_script")
    
    assert await config_service.get_config("TEST_INTEGER") == 42
    assert await config_service.get_config("TEST_BOOLEAN") is True
    assert await config_service.get_config("TEST_LIST") == ["a", "b", "c"]
    assert await config_service.get_config("TEST_DICT") == {"key": "value"}
    
    logger.info("✅ Data type configuration tests passed")


async def test_environment_specific_configuration():
    """Test environment-specific configuration handling."""
    logger.info("Testing environment-specific configuration...")
    
    config_service = await get_config_service()
    
    # Set different values for different environments
    await config_service.set_config(
        key="TEST_ENV_CONFIG",
        value="development_value",
        scope=ConfigScope.ENVIRONMENT,
        environment="development",
        updated_by="test_script"
    )
    
    await config_service.set_config(
        key="TEST_ENV_CONFIG",
        value="production_value",
        scope=ConfigScope.ENVIRONMENT,
        environment="production",
        updated_by="test_script"
    )
    
    # Test retrieval from different environments
    dev_value = await config_service.get_config(
        "TEST_ENV_CONFIG",
        scope=ConfigScope.ENVIRONMENT,
        environment="development"
    )
    prod_value = await config_service.get_config(
        "TEST_ENV_CONFIG",
        scope=ConfigScope.ENVIRONMENT,
        environment="production"
    )
    
    assert dev_value == "development_value"
    assert prod_value == "production_value"
    
    logger.info("✅ Environment-specific configuration test passed")


async def test_configuration_validation():
    """Test configuration validation with schemas."""
    logger.info("Testing configuration validation...")
    
    config_service = await get_config_service()
    
    # Register a test schema
    test_metadata = ConfigMetadata(
        description="Test configuration with validation",
        config_type=ConfigType.INTEGER,
        default_value=10,
        required=True,
        min_value=1,
        max_value=100
    )
    
    await config_service.register_config_schema("TEST_VALIDATED_CONFIG", test_metadata)
    
    # Test valid value
    await config_service.set_config(
        key="TEST_VALIDATED_CONFIG",
        value=50,
        updated_by="test_script"
    )
    
    value = await config_service.get_config("TEST_VALIDATED_CONFIG")
    assert value == 50
    
    # Test invalid value (should raise exception)
    try:
        await config_service.set_config(
            key="TEST_VALIDATED_CONFIG",
            value=150,  # Exceeds max_value
            updated_by="test_script"
        )
        assert False, "Should have raised validation error"
    except ValueError:
        logger.info("✅ Validation correctly rejected invalid value")
    
    # Test type conversion
    await config_service.set_config(
        key="TEST_VALIDATED_CONFIG",
        value="25",  # String that can be converted to int
        updated_by="test_script"
    )
    
    value = await config_service.get_config("TEST_VALIDATED_CONFIG")
    assert value == 25 and isinstance(value, int)
    
    logger.info("✅ Configuration validation tests passed")


async def test_configuration_history():
    """Test configuration change history."""
    logger.info("Testing configuration history...")
    
    config_service = await get_config_service()
    
    # Make several changes to track history
    key = "TEST_HISTORY_CONFIG"
    
    await config_service.set_config(key, "value1", updated_by="test_script")
    await asyncio.sleep(0.1)  # Small delay to ensure different timestamps
    
    await config_service.set_config(key, "value2", updated_by="test_script")
    await asyncio.sleep(0.1)
    
    await config_service.set_config(key, "value3", updated_by="test_script")
    
    # Get history
    history = await config_service.get_config_history(key, limit=5)
    
    assert len(history) >= 3, f"Expected at least 3 history entries, got {len(history)}"
    
    # History should be in reverse chronological order (newest first)
    assert history[0]['value'] == "value3"
    
    logger.info("✅ Configuration history test passed")


async def test_configuration_watchers():
    """Test configuration change watchers."""
    logger.info("Testing configuration watchers...")
    
    config_service = await get_config_service()
    
    # Track changes with a watcher
    changes = []
    
    def change_callback(key, old_value, new_value):
        changes.append({
            'key': key,
            'old_value': old_value,
            'new_value': new_value
        })
    
    # Register watcher
    await config_service.watch_config_changes(["TEST_WATCHER_CONFIG"], change_callback)
    
    # Make changes
    await config_service.set_config("TEST_WATCHER_CONFIG", "initial", updated_by="test_script")
    await asyncio.sleep(0.1)  # Allow time for notification
    
    await config_service.set_config("TEST_WATCHER_CONFIG", "updated", updated_by="test_script")
    await asyncio.sleep(0.1)
    
    # Check that changes were captured
    assert len(changes) >= 1, f"Expected at least 1 change notification, got {len(changes)}"
    
    logger.info("✅ Configuration watcher test passed")


async def test_configuration_export_import():
    """Test configuration export and import."""
    logger.info("Testing configuration export/import...")
    
    config_service = await get_config_service()
    
    # Set up test configurations
    test_configs = {
        "EXPORT_TEST_1": "value1",
        "EXPORT_TEST_2": 42,
        "EXPORT_TEST_3": True
    }
    
    for key, value in test_configs.items():
        await config_service.set_config(
            key=key,
            value=value,
            environment="test_env",
            updated_by="test_script"
        )
    
    # Export configuration
    exported = await config_service.export_configuration(environment="test_env")
    
    # Verify exported data
    for key, expected_value in test_configs.items():
        assert key in exported, f"Key {key} not found in exported configuration"
        assert exported[key] == expected_value, f"Value mismatch for {key}"
    
    # Test import to different environment
    await config_service.import_configuration(
        config_dict=test_configs,
        environment="imported_env",
        updated_by="test_script"
    )
    
    # Verify imported configuration
    for key, expected_value in test_configs.items():
        value = await config_service.get_config(key, environment="imported_env")
        assert value == expected_value, f"Imported value mismatch for {key}"
    
    logger.info("✅ Configuration export/import test passed")


async def test_configuration_list_and_filter():
    """Test configuration listing and filtering."""
    logger.info("Testing configuration listing and filtering...")
    
    config_service = await get_config_service()
    
    # Set up test configurations with different scopes and environments
    test_data = [
        ("FILTER_GLOBAL_1", "global1", ConfigScope.GLOBAL, "development"),
        ("FILTER_GLOBAL_2", "global2", ConfigScope.GLOBAL, "production"),
        ("FILTER_ENV_1", "env1", ConfigScope.ENVIRONMENT, "development"),
        ("FILTER_ENV_2", "env2", ConfigScope.ENVIRONMENT, "production"),
    ]
    
    for key, value, scope, environment in test_data:
        await config_service.set_config(
            key=key,
            value=value,
            scope=scope,
            environment=environment,
            updated_by="test_script"
        )
    
    # Test filtering by scope
    global_configs = await config_service.list_configs(scope=ConfigScope.GLOBAL)
    global_keys = [config.key for config in global_configs]
    assert "FILTER_GLOBAL_1" in global_keys
    assert "FILTER_GLOBAL_2" in global_keys
    
    # Test filtering by environment
    dev_configs = await config_service.list_configs(environment="development")
    dev_keys = [config.key for config in dev_configs]
    assert "FILTER_GLOBAL_1" in dev_keys
    assert "FILTER_ENV_1" in dev_keys
    
    # Test pattern matching
    filter_configs = await config_service.list_configs(pattern="FILTER_*")
    filter_keys = [config.key for config in filter_configs]
    assert len([k for k in filter_keys if k.startswith("FILTER_")]) >= 4
    
    logger.info("✅ Configuration listing and filtering test passed")


async def test_configuration_deletion():
    """Test configuration deletion."""
    logger.info("Testing configuration deletion...")
    
    config_service = await get_config_service()
    
    # Set a configuration to delete
    await config_service.set_config("DELETE_TEST", "to_be_deleted", updated_by="test_script")
    
    # Verify it exists
    value = await config_service.get_config("DELETE_TEST")
    assert value == "to_be_deleted"
    
    # Delete it
    deleted = await config_service.delete_config("DELETE_TEST", updated_by="test_script")
    assert deleted is True
    
    # Verify it's gone
    value = await config_service.get_config("DELETE_TEST")
    assert value is None
    
    # Try to delete non-existent configuration
    deleted = await config_service.delete_config("NON_EXISTENT", updated_by="test_script")
    assert deleted is False
    
    logger.info("✅ Configuration deletion test passed")


async def run_all_tests():
    """Run all configuration service tests."""
    logger.info("🧪 Starting Configuration Service Tests")
    
    try:
        await test_basic_configuration()
        await test_environment_specific_configuration()
        await test_configuration_validation()
        await test_configuration_history()
        await test_configuration_watchers()
        await test_configuration_export_import()
        await test_configuration_list_and_filter()
        await test_configuration_deletion()
        
        logger.info("🎉 All configuration service tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def cleanup_test_data():
    """Clean up test data."""
    logger.info("🧹 Cleaning up test data...")
    
    config_service = await get_config_service()
    
    # List of test keys to clean up
    test_keys = [
        "TEST_STRING", "TEST_INTEGER", "TEST_BOOLEAN", "TEST_LIST", "TEST_DICT",
        "TEST_ENV_CONFIG", "TEST_VALIDATED_CONFIG", "TEST_HISTORY_CONFIG",
        "TEST_WATCHER_CONFIG", "EXPORT_TEST_1", "EXPORT_TEST_2", "EXPORT_TEST_3",
        "FILTER_GLOBAL_1", "FILTER_GLOBAL_2", "FILTER_ENV_1", "FILTER_ENV_2",
        "DELETE_TEST"
    ]
    
    for key in test_keys:
        try:
            # Try to delete from different scopes and environments
            await config_service.delete_config(key, updated_by="cleanup")
            await config_service.delete_config(
                key, scope=ConfigScope.ENVIRONMENT, 
                environment="development", updated_by="cleanup"
            )
            await config_service.delete_config(
                key, scope=ConfigScope.ENVIRONMENT, 
                environment="production", updated_by="cleanup"
            )
            await config_service.delete_config(
                key, scope=ConfigScope.ENVIRONMENT, 
                environment="test_env", updated_by="cleanup"
            )
            await config_service.delete_config(
                key, scope=ConfigScope.ENVIRONMENT, 
                environment="imported_env", updated_by="cleanup"
            )
        except Exception:
            pass  # Ignore errors during cleanup
    
    logger.info("✅ Test data cleanup completed")


async def main():
    """Main test function."""
    try:
        # Run tests
        success = await run_all_tests()
        
        # Cleanup
        await cleanup_test_data()
        
        if success:
            logger.info("✅ Configuration service tests completed successfully")
            return 0
        else:
            logger.error("❌ Configuration service tests failed")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)