"""Plugin manager for dynamic loading and management of data source plugins."""

import asyncio
import importlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
from datetime import datetime, timedelta

try:
    from .plugins.base import (
        DataSourcePlugin, 
        PluginMetadata, 
        PluginStatus, 
        PluginError,
        PluginConfig,
        RawData
    )
except ImportError:
    # Fallback for direct execution
    from plugins.base import (
        DataSourcePlugin, 
        PluginMetadata, 
        PluginStatus, 
        PluginError,
        PluginConfig,
        RawData
    )


logger = logging.getLogger(__name__)


class PluginManager:
    """Manages data source plugins with dynamic loading and lifecycle management."""
    
    def __init__(self):
        self._plugins: Dict[str, DataSourcePlugin] = {}
        self._plugin_configs: Dict[str, PluginConfig] = {}
        self._plugin_classes: Dict[str, Type[DataSourcePlugin]] = {}
        self._health_check_interval = 300  # 5 minutes
        self._health_check_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the plugin manager."""
        logger.info("Initializing Plugin Manager")
        await self._discover_plugins()
        await self._start_health_monitoring()
        
    async def shutdown(self) -> None:
        """Shutdown all plugins and cleanup."""
        logger.info("Shutting down Plugin Manager")
        
        # Cancel health monitoring
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown all plugins
        for plugin_name, plugin in self._plugins.items():
            try:
                await plugin.shutdown()
                logger.info(f"Plugin {plugin_name} shut down successfully")
            except Exception as e:
                logger.error(f"Error shutting down plugin {plugin_name}: {e}")
    
    async def load_plugin(self, plugin_name: str, config: PluginConfig) -> bool:
        """Load and initialize a specific plugin."""
        try:
            if plugin_name in self._plugins:
                logger.warning(f"Plugin {plugin_name} already loaded")
                return True
            
            if plugin_name not in self._plugin_classes:
                logger.error(f"Plugin class {plugin_name} not found")
                return False
            
            # Create plugin instance
            plugin_class = self._plugin_classes[plugin_name]
            plugin = plugin_class(config)
            
            # Initialize plugin
            await plugin.initialize()
            await plugin.set_status(PluginStatus.ACTIVE)
            
            # Store plugin and config
            self._plugins[plugin_name] = plugin
            self._plugin_configs[plugin_name] = config
            
            logger.info(f"Plugin {plugin_name} loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            return False
    
    async def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a specific plugin."""
        try:
            if plugin_name not in self._plugins:
                logger.warning(f"Plugin {plugin_name} not loaded")
                return True
            
            plugin = self._plugins[plugin_name]
            await plugin.shutdown()
            
            del self._plugins[plugin_name]
            del self._plugin_configs[plugin_name]
            
            logger.info(f"Plugin {plugin_name} unloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            return False
    
    async def reload_plugin(self, plugin_name: str, config: Optional[PluginConfig] = None) -> bool:
        """Reload a plugin with optional new configuration."""
        try:
            # Use existing config if none provided
            if config is None and plugin_name in self._plugin_configs:
                config = self._plugin_configs[plugin_name]
            elif config is None:
                logger.error(f"No configuration available for plugin {plugin_name}")
                return False
            
            # Unload and reload
            await self.unload_plugin(plugin_name)
            return await self.load_plugin(plugin_name, config)
            
        except Exception as e:
            logger.error(f"Failed to reload plugin {plugin_name}: {e}")
            return False
    
    def register_plugin(self, plugin_name: str, plugin_class: Type[DataSourcePlugin]) -> None:
        """Register a plugin class for dynamic loading."""
        self._plugin_classes[plugin_name] = plugin_class
        logger.info(f"Registered plugin class: {plugin_name}")
    
    def get_plugin(self, plugin_name: str) -> Optional[DataSourcePlugin]:
        """Get a loaded plugin by name."""
        return self._plugins.get(plugin_name)
    
    def list_loaded_plugins(self) -> List[str]:
        """List all currently loaded plugins."""
        return list(self._plugins.keys())
    
    def list_available_plugins(self) -> List[str]:
        """List all available plugin classes."""
        return list(self._plugin_classes.keys())
    
    async def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get metadata for a plugin."""
        if plugin_name in self._plugins:
            return self._plugins[plugin_name].get_metadata()
        elif plugin_name in self._plugin_classes:
            # Create temporary instance to get metadata
            temp_config = PluginConfig()
            temp_plugin = self._plugin_classes[plugin_name](temp_config)
            return temp_plugin.get_metadata()
        return None
    
    async def get_plugin_status(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get status information for a plugin."""
        if plugin_name in self._plugins:
            return self._plugins[plugin_name].get_status()
        return None
    
    async def get_all_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all loaded plugins."""
        status = {}
        for plugin_name, plugin in self._plugins.items():
            status[plugin_name] = plugin.get_status()
        return status
    
    async def fetch_data_from_plugin(
        self, 
        plugin_name: str, 
        params: Dict[str, Any]
    ) -> List[RawData]:
        """Fetch data from a specific plugin."""
        if plugin_name not in self._plugins:
            raise PluginError(f"Plugin {plugin_name} not loaded")
        
        plugin = self._plugins[plugin_name]
        
        if plugin.status != PluginStatus.ACTIVE:
            raise PluginError(f"Plugin {plugin_name} is not active (status: {plugin.status})")
        
        try:
            data = []
            async for item in plugin.fetch_data(params):
                data.append(item)
            return data
        except Exception as e:
            await plugin.set_status(PluginStatus.ERROR, str(e))
            raise PluginError(f"Error fetching data from {plugin_name}: {e}")
    
    async def fetch_data_from_all_plugins(self, params: Dict[str, Any]) -> Dict[str, List[RawData]]:
        """Fetch data from all active plugins."""
        results = {}
        
        for plugin_name, plugin in self._plugins.items():
            if plugin.status == PluginStatus.ACTIVE:
                try:
                    results[plugin_name] = await self.fetch_data_from_plugin(plugin_name, params)
                except Exception as e:
                    logger.error(f"Error fetching from plugin {plugin_name}: {e}")
                    results[plugin_name] = []
        
        return results
    
    async def _discover_plugins(self) -> None:
        """Discover and register available plugins."""
        plugins_dir = Path(__file__).parent / "plugins"
        
        if not plugins_dir.exists():
            logger.warning("Plugins directory not found")
            return
        
        for plugin_file in plugins_dir.glob("*_plugin.py"):
            try:
                module_name = f"data-ingestion.plugins.{plugin_file.stem}"
                module = importlib.import_module(module_name)
                
                # Look for plugin classes
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, DataSourcePlugin) and 
                        attr != DataSourcePlugin):
                        
                        plugin_name = attr_name.lower().replace("plugin", "")
                        self.register_plugin(plugin_name, attr)
                        
            except Exception as e:
                logger.error(f"Failed to load plugin from {plugin_file}: {e}")
    
    async def _start_health_monitoring(self) -> None:
        """Start background health monitoring for all plugins."""
        self._health_check_task = asyncio.create_task(self._health_monitor_loop())
    
    async def _health_monitor_loop(self) -> None:
        """Background loop for monitoring plugin health."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._check_all_plugin_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
    
    async def _check_all_plugin_health(self) -> None:
        """Check health of all loaded plugins."""
        for plugin_name, plugin in self._plugins.items():
            try:
                is_healthy = await plugin.health_check()
                if not is_healthy and plugin.status == PluginStatus.ACTIVE:
                    await plugin.set_status(PluginStatus.ERROR, "Health check failed")
                    logger.warning(f"Plugin {plugin_name} failed health check")
                elif is_healthy and plugin.status == PluginStatus.ERROR:
                    await plugin.set_status(PluginStatus.ACTIVE)
                    logger.info(f"Plugin {plugin_name} recovered from error state")
            except Exception as e:
                await plugin.set_status(PluginStatus.ERROR, f"Health check error: {e}")
                logger.error(f"Health check error for plugin {plugin_name}: {e}")


# Global plugin manager instance
plugin_manager = PluginManager()