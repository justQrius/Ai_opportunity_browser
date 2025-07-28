"""
Service authentication configuration for zero trust architecture.

This module manages service-to-service authentication secrets and configuration.
"""

import os
import secrets
from typing import Dict, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ServiceConfig:
    """Configuration for a service."""
    name: str
    secret: str
    description: str
    permissions: list
    enabled: bool = True


class ServiceRegistry:
    """Registry for managing service configurations."""
    
    def __init__(self):
        """Initialize service registry."""
        self.services: Dict[str, ServiceConfig] = {}
        self._load_default_services()
    
    def _load_default_services(self):
        """Load default service configurations."""
        # Core services
        self.register_service(
            "ai-opportunity-browser-api",
            self._get_or_generate_secret("API_SERVICE_SECRET"),
            "Main API service",
            ["*"]  # Full permissions
        )
        
        self.register_service(
            "data-ingestion-service",
            self._get_or_generate_secret("DATA_INGESTION_SECRET"),
            "Data ingestion service",
            ["create:market_signals", "read:opportunities", "write:opportunities"]
        )
        
        self.register_service(
            "agent-orchestrator",
            self._get_or_generate_secret("AGENT_ORCHESTRATOR_SECRET"),
            "AI agent orchestrator",
            ["read:market_signals", "write:opportunities", "read:analytics"]
        )
        
        self.register_service(
            "monitoring-service",
            self._get_or_generate_secret("MONITORING_SERVICE_SECRET"),
            "Monitoring and health service",
            ["read:health", "read:metrics", "write:alerts"]
        )
        
        self.register_service(
            "validation-service",
            self._get_or_generate_secret("VALIDATION_SERVICE_SECRET"),
            "Community validation service",
            ["read:validations", "write:validations", "read:opportunities"]
        )
        
        self.register_service(
            "analytics-service",
            self._get_or_generate_secret("ANALYTICS_SERVICE_SECRET"),
            "Business intelligence service",
            ["read:opportunities", "read:validations", "read:analytics", "write:analytics"]
        )
    
    def register_service(
        self,
        name: str,
        secret: str,
        description: str,
        permissions: list,
        enabled: bool = True
    ):
        """
        Register a service.
        
        Args:
            name: Service name
            secret: Service secret key
            description: Service description
            permissions: List of permissions
            enabled: Whether service is enabled
        """
        self.services[name] = ServiceConfig(
            name=name,
            secret=secret,
            description=description,
            permissions=permissions,
            enabled=enabled
        )
        
        logger.info(
            "Service registered",
            service_name=name,
            description=description,
            permissions_count=len(permissions),
            enabled=enabled
        )
    
    def get_service(self, name: str) -> Optional[ServiceConfig]:
        """Get service configuration by name."""
        return self.services.get(name)
    
    def get_service_secret(self, name: str) -> Optional[str]:
        """Get service secret by name."""
        service = self.services.get(name)
        return service.secret if service and service.enabled else None
    
    def get_all_services(self) -> Dict[str, ServiceConfig]:
        """Get all registered services."""
        return self.services.copy()
    
    def get_service_secrets(self) -> Dict[str, str]:
        """Get all service secrets for authentication."""
        return {
            name: config.secret
            for name, config in self.services.items()
            if config.enabled
        }
    
    def disable_service(self, name: str):
        """Disable a service."""
        if name in self.services:
            self.services[name].enabled = False
            logger.warning("Service disabled", service_name=name)
    
    def enable_service(self, name: str):
        """Enable a service."""
        if name in self.services:
            self.services[name].enabled = True
            logger.info("Service enabled", service_name=name)
    
    def rotate_service_secret(self, name: str) -> str:
        """
        Rotate a service secret.
        
        Args:
            name: Service name
            
        Returns:
            New secret
        """
        if name not in self.services:
            raise ValueError(f"Service not found: {name}")
        
        new_secret = self._generate_secret()
        self.services[name].secret = new_secret
        
        logger.warning(
            "Service secret rotated",
            service_name=name,
            # Don't log the actual secret
        )
        
        return new_secret
    
    def _get_or_generate_secret(self, env_var: str) -> str:
        """Get secret from environment or generate new one."""
        secret = os.getenv(env_var)
        if not secret:
            secret = self._generate_secret()
            logger.warning(
                "Generated new service secret",
                env_var=env_var,
                message=f"Set {env_var} environment variable for production"
            )
        return secret
    
    def _generate_secret(self) -> str:
        """Generate a secure random secret."""
        return secrets.token_urlsafe(32)


# Global service registry
_service_registry: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry."""
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry()
    return _service_registry


def setup_service_registry() -> ServiceRegistry:
    """Setup and return the service registry."""
    global _service_registry
    _service_registry = ServiceRegistry()
    logger.info("Service registry initialized")
    return _service_registry