"""
Comprehensive observability module integrating logging, tracing, and monitoring.

This module provides:
- Unified observability setup
- Performance tracking with automatic instrumentation
- Health check integration with logging
- Custom metrics and traces for business logic
"""

import time
import asyncio
from typing import Dict, Any, Optional, List, Callable, Union
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
from opentelemetry.metrics import get_meter

from shared.logging_config import (
    get_logger,
    with_tracing,
    with_correlation,
    CorrelationContext,
    RequestContext
)
from shared.monitoring import (
    get_metrics_collector,
    get_health_monitor,
    get_performance_tracker,
    HealthStatus,
    HealthCheck
)

logger = get_logger(__name__)


@dataclass
class ObservabilityConfig:
    """Configuration for observability setup."""
    service_name: str = "ai-opportunity-browser"
    service_version: str = "1.0.0"
    log_level: str = "INFO"
    enable_tracing: bool = True
    enable_metrics: bool = True
    enable_health_checks: bool = True
    jaeger_endpoint: Optional[str] = None
    otlp_endpoint: Optional[str] = None
    metrics_port: int = 8000
    health_check_interval: int = 30


class ObservabilityManager:
    """Central manager for all observability concerns."""
    
    def __init__(self, config: ObservabilityConfig):
        """Initialize observability manager."""
        self.config = config
        self.tracer = trace.get_tracer(config.service_name)
        self.meter = get_meter(config.service_name)
        self.metrics_collector = get_metrics_collector()
        self.health_monitor = get_health_monitor()
        self.performance_tracker = get_performance_tracker()
        
        # Custom metrics
        self._setup_custom_metrics()
        
        # Health checks
        self._setup_health_checks()
    
    def _setup_custom_metrics(self):
        """Setup custom OpenTelemetry metrics."""
        # Business metrics
        self.opportunities_processed = self.meter.create_counter(
            name="opportunities_processed_total",
            description="Total number of opportunities processed",
            unit="1"
        )
        
        self.validations_completed = self.meter.create_counter(
            name="validations_completed_total",
            description="Total number of validations completed",
            unit="1"
        )
        
        self.agent_operations = self.meter.create_counter(
            name="agent_operations_total",
            description="Total number of agent operations",
            unit="1"
        )
        
        self.data_ingestion_events = self.meter.create_counter(
            name="data_ingestion_events_total",
            description="Total number of data ingestion events",
            unit="1"
        )
        
        # Performance metrics
        self.operation_duration = self.meter.create_histogram(
            name="operation_duration_seconds",
            description="Duration of operations in seconds",
            unit="s"
        )
        
        self.queue_size = self.meter.create_up_down_counter(
            name="queue_size",
            description="Current queue size",
            unit="1"
        )
    
    def _setup_health_checks(self):
        """Setup standard health checks."""
        # Database health check
        async def check_database():
            """Check database connectivity."""
            try:
                from shared.database import get_db_session
                async with get_db_session() as session:
                    await session.execute("SELECT 1")
                return HealthCheck(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message="Database connection successful"
                )
            except Exception as e:
                return HealthCheck(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Database connection failed: {str(e)}"
                )
        
        # Redis health check
        async def check_redis():
            """Check Redis connectivity."""
            try:
                from shared.cache import get_redis_client
                redis_client = await get_redis_client()
                await redis_client.ping()
                return HealthCheck(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    message="Redis connection successful"
                )
            except Exception as e:
                return HealthCheck(
                    name="redis",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Redis connection failed: {str(e)}"
                )
        
        # Vector database health check
        async def check_vector_db():
            """Check vector database connectivity."""
            try:
                from shared.vector_db import get_vector_db
                vector_db = get_vector_db()
                # Simple connectivity test
                await vector_db.describe_index()
                return HealthCheck(
                    name="vector_db",
                    status=HealthStatus.HEALTHY,
                    message="Vector database connection successful"
                )
            except Exception as e:
                return HealthCheck(
                    name="vector_db",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Vector database connection failed: {str(e)}"
                )
        
        # Register health checks
        self.health_monitor.register_check("database", check_database)
        self.health_monitor.register_check("redis", check_redis)
        self.health_monitor.register_check("vector_db", check_vector_db)
    
    @asynccontextmanager
    async def trace_operation(
        self,
        operation_name: str,
        attributes: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        """
        Context manager for tracing operations with automatic logging.
        
        Args:
            operation_name: Name of the operation
            attributes: Additional attributes to add to the span
            correlation_id: Optional correlation ID
        """
        with self.tracer.start_as_current_span(operation_name) as span:
            start_time = time.time()
            
            # Add attributes to span
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))
            
            # Set up correlation context if provided
            context_manager = CorrelationContext(correlation_id) if correlation_id else None
            
            try:
                if context_manager:
                    with context_manager:
                        logger.info(f"Starting operation: {operation_name}", **attributes or {})
                        yield span
                else:
                    logger.info(f"Starting operation: {operation_name}", **attributes or {})
                    yield span
                
                # Record success
                duration = time.time() - start_time
                span.set_status(Status(StatusCode.OK))
                span.set_attribute("duration_seconds", duration)
                
                # Record custom metrics
                self.operation_duration.record(
                    duration,
                    attributes={"operation": operation_name, "status": "success"}
                )
                
                logger.info(
                    f"Operation completed successfully: {operation_name}",
                    duration_seconds=duration,
                    **attributes or {}
                )
                
            except Exception as e:
                # Record error
                duration = time.time() - start_time
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.set_attribute("duration_seconds", duration)
                
                # Record error metrics
                self.operation_duration.record(
                    duration,
                    attributes={"operation": operation_name, "status": "error"}
                )
                
                logger.error(
                    f"Operation failed: {operation_name}",
                    error=str(e),
                    duration_seconds=duration,
                    exc_info=True,
                    **attributes or {}
                )
                
                raise
    
    @contextmanager
    def trace_sync_operation(
        self,
        operation_name: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for tracing synchronous operations.
        
        Args:
            operation_name: Name of the operation
            attributes: Additional attributes to add to the span
        """
        with self.tracer.start_as_current_span(operation_name) as span:
            start_time = time.time()
            
            # Add attributes to span
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))
            
            try:
                logger.info(f"Starting operation: {operation_name}", **attributes or {})
                yield span
                
                # Record success
                duration = time.time() - start_time
                span.set_status(Status(StatusCode.OK))
                span.set_attribute("duration_seconds", duration)
                
                # Record custom metrics
                self.operation_duration.record(
                    duration,
                    attributes={"operation": operation_name, "status": "success"}
                )
                
                logger.info(
                    f"Operation completed successfully: {operation_name}",
                    duration_seconds=duration,
                    **attributes or {}
                )
                
            except Exception as e:
                # Record error
                duration = time.time() - start_time
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.set_attribute("duration_seconds", duration)
                
                # Record error metrics
                self.operation_duration.record(
                    duration,
                    attributes={"operation": operation_name, "status": "error"}
                )
                
                logger.error(
                    f"Operation failed: {operation_name}",
                    error=str(e),
                    duration_seconds=duration,
                    exc_info=True,
                    **attributes or {}
                )
                
                raise
    
    def record_business_metric(
        self,
        metric_name: str,
        value: Union[int, float] = 1,
        attributes: Optional[Dict[str, str]] = None
    ):
        """
        Record a business metric.
        
        Args:
            metric_name: Name of the metric
            value: Value to record
            attributes: Additional attributes
        """
        attrs = attributes or {}
        
        if metric_name == "opportunity_processed":
            self.opportunities_processed.add(value, attrs)
        elif metric_name == "validation_completed":
            self.validations_completed.add(value, attrs)
        elif metric_name == "agent_operation":
            self.agent_operations.add(value, attrs)
        elif metric_name == "data_ingestion_event":
            self.data_ingestion_events.add(value, attrs)
        elif metric_name == "queue_size_change":
            self.queue_size.add(value, attrs)
        
        # Also record in Prometheus metrics
        if metric_name == "opportunity_processed":
            self.metrics_collector.record_opportunity_created()
        elif metric_name == "validation_completed":
            validation_type = attrs.get("type", "unknown")
            self.metrics_collector.record_validation_submitted(validation_type)
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        health_results = await self.health_monitor.run_all_checks()
        overall_status = self.health_monitor.get_overall_status(health_results)
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.config.service_name,
            "version": self.config.service_version,
            "checks": {
                name: {
                    "status": check.status.value,
                    "message": check.message,
                    "duration_ms": check.duration_ms,
                    "timestamp": check.timestamp.isoformat(),
                    "details": check.details
                }
                for name, check in health_results.items()
            }
        }
    
    def get_metrics(self) -> str:
        """Get Prometheus metrics."""
        return self.metrics_collector.get_metrics()


# Global observability manager instance
_observability_manager: Optional[ObservabilityManager] = None


def setup_observability(config: ObservabilityConfig) -> ObservabilityManager:
    """Setup global observability manager."""
    global _observability_manager
    
    # Setup logging and tracing
    from shared.logging_config import setup_logging, setup_tracing
    
    setup_logging(
        log_level=config.log_level,
        service_name=config.service_name,
        service_version=config.service_version
    )
    
    if config.enable_tracing:
        setup_tracing(
            service_name=config.service_name,
            jaeger_endpoint=config.jaeger_endpoint,
            otlp_endpoint=config.otlp_endpoint
        )
    
    # Create observability manager
    _observability_manager = ObservabilityManager(config)
    
    logger.info(
        "Observability setup completed",
        service_name=config.service_name,
        service_version=config.service_version,
        tracing_enabled=config.enable_tracing,
        metrics_enabled=config.enable_metrics
    )
    
    return _observability_manager


def get_observability_manager() -> ObservabilityManager:
    """Get the global observability manager."""
    if _observability_manager is None:
        raise RuntimeError("Observability manager not initialized. Call setup_observability() first.")
    return _observability_manager


# Convenience functions
async def trace_async_operation(
    operation_name: str,
    attributes: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
):
    """Decorator/context manager for async operations."""
    manager = get_observability_manager()
    return manager.trace_operation(operation_name, attributes, correlation_id)


def trace_sync_operation(
    operation_name: str,
    attributes: Optional[Dict[str, Any]] = None
):
    """Decorator/context manager for sync operations."""
    manager = get_observability_manager()
    return manager.trace_sync_operation(operation_name, attributes)


def record_metric(
    metric_name: str,
    value: Union[int, float] = 1,
    attributes: Optional[Dict[str, str]] = None
):
    """Record a business metric."""
    manager = get_observability_manager()
    manager.record_business_metric(metric_name, value, attributes)


async def get_health() -> Dict[str, Any]:
    """Get system health status."""
    manager = get_observability_manager()
    return await manager.get_health_status()


def get_prometheus_metrics() -> str:
    """Get Prometheus metrics."""
    manager = get_observability_manager()
    return manager.get_metrics()