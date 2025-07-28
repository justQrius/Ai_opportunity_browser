"""Testing framework and utilities for data source plugins."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, AsyncIterator
from unittest.mock import AsyncMock, MagicMock

from .base import (
    DataSourcePlugin,
    PluginMetadata,
    PluginConfig,
    PluginStatus,
    RawData,
    DataSourceType
)


class MockDataSourcePlugin(DataSourcePlugin):
    """Mock plugin for testing purposes."""
    
    def __init__(self, config: PluginConfig, mock_data: Optional[List[RawData]] = None):
        super().__init__(config)
        self.mock_data = mock_data or []
        self.initialize_called = False
        self.shutdown_called = False
        self.health_check_result = True
        self.fetch_data_calls = []
        
    async def initialize(self) -> None:
        """Mock initialization."""
        self.initialize_called = True
        await self.set_status(PluginStatus.ACTIVE)
    
    async def shutdown(self) -> None:
        """Mock shutdown."""
        self.shutdown_called = True
        await self.set_status(PluginStatus.INACTIVE)
    
    async def health_check(self) -> bool:
        """Mock health check."""
        return self.health_check_result
    
    async def fetch_data(self, params: Dict[str, Any]) -> AsyncIterator[RawData]:
        """Mock data fetching."""
        self.fetch_data_calls.append(params)
        for data in self.mock_data:
            yield data
    
    def get_metadata(self) -> PluginMetadata:
        """Mock metadata."""
        return PluginMetadata(
            name="mock_plugin",
            version="1.0.0",
            description="Mock plugin for testing",
            author="Test Suite",
            source_type=DataSourceType.REDDIT,
            supported_signal_types=["pain_point", "feature_request"],
            rate_limit_per_hour=1000,
            requires_auth=False,
            config_schema={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Mock config validation."""
        return True


class PluginTestCase:
    """Base test case for plugin testing."""
    
    def __init__(self, plugin_class: type, config: PluginConfig):
        self.plugin_class = plugin_class
        self.config = config
        self.plugin: Optional[DataSourcePlugin] = None
    
    async def setup(self) -> None:
        """Set up test environment."""
        self.plugin = self.plugin_class(self.config)
        await self.plugin.initialize()
    
    async def teardown(self) -> None:
        """Clean up test environment."""
        if self.plugin:
            await self.plugin.shutdown()
    
    async def test_initialization(self) -> bool:
        """Test plugin initialization."""
        try:
            await self.setup()
            return self.plugin.status == PluginStatus.ACTIVE
        except Exception:
            return False
        finally:
            await self.teardown()
    
    async def test_health_check(self) -> bool:
        """Test plugin health check."""
        try:
            await self.setup()
            return await self.plugin.health_check()
        except Exception:
            return False
        finally:
            await self.teardown()
    
    async def test_data_fetching(self, params: Dict[str, Any]) -> bool:
        """Test data fetching functionality."""
        try:
            await self.setup()
            data_count = 0
            async for data in self.plugin.fetch_data(params):
                if not isinstance(data, RawData):
                    return False
                data_count += 1
                if data_count > 100:  # Prevent infinite loops
                    break
            return True
        except Exception:
            return False
        finally:
            await self.teardown()
    
    async def test_metadata(self) -> bool:
        """Test plugin metadata."""
        try:
            await self.setup()
            metadata = self.plugin.get_metadata()
            return isinstance(metadata, PluginMetadata)
        except Exception:
            return False
        finally:
            await self.teardown()
    
    async def test_config_validation(self, test_configs: List[Dict[str, Any]]) -> bool:
        """Test configuration validation."""
        try:
            await self.setup()
            for config in test_configs:
                if not isinstance(self.plugin.validate_config(config), bool):
                    return False
            return True
        except Exception:
            return False
        finally:
            await self.teardown()


class PluginTestSuite:
    """Test suite for running comprehensive plugin tests."""
    
    def __init__(self):
        self.test_results: Dict[str, Dict[str, bool]] = {}
    
    async def run_plugin_tests(
        self, 
        plugin_class: type, 
        config: PluginConfig,
        test_params: Optional[Dict[str, Any]] = None,
        test_configs: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, bool]:
        """Run all tests for a plugin."""
        test_case = PluginTestCase(plugin_class, config)
        
        results = {
            "initialization": await test_case.test_initialization(),
            "health_check": await test_case.test_health_check(),
            "metadata": await test_case.test_metadata(),
        }
        
        if test_params:
            results["data_fetching"] = await test_case.test_data_fetching(test_params)
        
        if test_configs:
            results["config_validation"] = await test_case.test_config_validation(test_configs)
        
        plugin_name = plugin_class.__name__
        self.test_results[plugin_name] = results
        
        return results
    
    async def run_integration_tests(
        self,
        plugin_classes: List[type],
        configs: List[PluginConfig]
    ) -> Dict[str, bool]:
        """Run integration tests across multiple plugins."""
        results = {}
        
        # Test plugin manager integration
        from ..plugin_manager import PluginManager
        
        manager = PluginManager()
        await manager.initialize()
        
        try:
            # Register and load plugins
            for i, plugin_class in enumerate(plugin_classes):
                plugin_name = plugin_class.__name__.lower()
                manager.register_plugin(plugin_name, plugin_class)
                
                config = configs[i] if i < len(configs) else PluginConfig()
                load_success = await manager.load_plugin(plugin_name, config)
                results[f"{plugin_name}_load"] = load_success
            
            # Test plugin listing
            loaded_plugins = manager.list_loaded_plugins()
            results["plugin_listing"] = len(loaded_plugins) == len(plugin_classes)
            
            # Test status retrieval
            status = await manager.get_all_plugin_status()
            results["status_retrieval"] = len(status) == len(loaded_plugins)
            
            # Test data fetching from all plugins
            try:
                data = await manager.fetch_data_from_all_plugins({})
                results["multi_plugin_fetch"] = isinstance(data, dict)
            except Exception:
                results["multi_plugin_fetch"] = False
            
        finally:
            await manager.shutdown()
        
        return results
    
    def generate_test_report(self) -> str:
        """Generate a comprehensive test report."""
        report = ["Plugin Test Report", "=" * 50, ""]
        
        for plugin_name, results in self.test_results.items():
            report.append(f"Plugin: {plugin_name}")
            report.append("-" * 30)
            
            passed = sum(1 for result in results.values() if result)
            total = len(results)
            
            report.append(f"Overall: {passed}/{total} tests passed")
            report.append("")
            
            for test_name, result in results.items():
                status = "PASS" if result else "FAIL"
                report.append(f"  {test_name}: {status}")
            
            report.append("")
        
        return "\n".join(report)


def create_sample_raw_data(source: str, count: int = 5) -> List[RawData]:
    """Create sample raw data for testing."""
    data = []
    for i in range(count):
        data.append(RawData(
            source=source,
            source_id=f"test_id_{i}",
            source_url=f"https://example.com/{i}",
            title=f"Test Title {i}",
            content=f"Test content for item {i}. This is a sample pain point or feature request.",
            raw_content=f"Raw test content {i}",
            author=f"test_user_{i}",
            author_reputation=float(i * 10),
            upvotes=i * 5,
            downvotes=i,
            comments_count=i * 2,
            extracted_at=datetime.now(),
            metadata={"test": True, "index": i}
        ))
    return data


async def run_mock_plugin_test() -> bool:
    """Run a quick test with the mock plugin."""
    config = PluginConfig()
    mock_data = create_sample_raw_data("test_source", 3)
    
    plugin = MockDataSourcePlugin(config, mock_data)
    
    try:
        await plugin.initialize()
        
        # Test health check
        if not await plugin.health_check():
            return False
        
        # Test data fetching
        fetched_data = []
        async for data in plugin.fetch_data({"test": "params"}):
            fetched_data.append(data)
        
        if len(fetched_data) != 3:
            return False
        
        # Test metadata
        metadata = plugin.get_metadata()
        if not isinstance(metadata, PluginMetadata):
            return False
        
        await plugin.shutdown()
        return True
        
    except Exception:
        return False


# Utility functions for testing
def create_test_config(**kwargs) -> PluginConfig:
    """Create a test configuration with custom parameters."""
    defaults = {
        "enabled": True,
        "rate_limit_per_hour": 100,
        "max_retries": 2,
        "timeout_seconds": 10,
        "batch_size": 10
    }
    defaults.update(kwargs)
    return PluginConfig(**defaults)


async def simulate_rate_limiting(plugin: DataSourcePlugin, requests: int) -> bool:
    """Simulate rate limiting behavior."""
    for _ in range(requests):
        if not await plugin._check_rate_limit():
            return False
        await plugin._increment_request_count()
    return True