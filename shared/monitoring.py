"""
Monitoring and observability utilities for the AI Opportunity Browser.

This module provides utilities for metrics collection, health monitoring,
and performance tracking across the application.
"""

import time
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
import structlog
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest

logger = structlog.get_logger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MetricsCollector:
    """Prometheus metrics collector for application metrics."""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # HTTP metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Database metrics
        self.db_connections_active = Gauge(
            'db_connections_active',
            'Active database connections',
            registry=self.registry
        )
        
        self.db_query_duration = Histogram(
            'db_query_duration_seconds',
            'Database query duration',
            ['operation'],
            registry=self.registry
        )
        
        # Agent metrics
        self.agent_tasks_total = Counter(
            'agent_tasks_total',
            'Total agent tasks processed',
            ['agent_type', 'status'],
            registry=self.registry
        )
        
        self.agent_task_duration = Histogram(
            'agent_task_duration_seconds',
            'Agent task processing duration',
            ['agent_type'],
            registry=self.registry
        )
        
        # Opportunity metrics
        self.opportunities_created_total = Counter(
            'opportunities_created_total',
            'Total opportunities created',
            registry=self.registry
        )
        
        self.validations_submitted_total = Counter(
            'validations_submitted_total',
            'Total validations submitted',
            ['validation_type'],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_hits_total = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_misses_total = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['cache_type'],
            registry=self.registry
        )
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_db_query(self, operation: str, duration: float):
        """Record database query metrics."""
        self.db_query_duration.labels(operation=operation).observe(duration)
    
    def set_db_connections(self, count: int):
        """Set active database connections count."""
        self.db_connections_active.set(count)
    
    def record_agent_task(self, agent_type: str, status: str, duration: float):
        """Record agent task metrics."""
        self.agent_tasks_total.labels(
            agent_type=agent_type,
            status=status
        ).inc()
        
        self.agent_task_duration.labels(agent_type=agent_type).observe(duration)
    
    def record_opportunity_created(self):
        """Record opportunity creation."""
        self.opportunities_created_total.inc()
    
    def record_validation_submitted(self, validation_type: str):
        """Record validation submission."""
        self.validations_submitted_total.labels(validation_type=validation_type).inc()
    
    def record_cache_hit(self, cache_type: str):
        """Record cache hit."""
        self.cache_hits_total.labels(cache_type=cache_type).inc()
    
    def record_cache_miss(self, cache_type: str):
        """Record cache miss."""
        self.cache_misses_total.labels(cache_type=cache_type).inc()
    
    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format."""
        return generate_latest(self.registry).decode('utf-8')


class HealthMonitor:
    """Health monitoring service."""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.last_results: Dict[str, HealthCheck] = {}
    
    def register_check(self, name: str, check_func: Callable):
        """Register a health check function."""
        self.checks[name] = check_func
        logger.info(f"Registered health check: {name}")
    
    async def run_check(self, name: str) -> HealthCheck:
        """Run a specific health check."""
        if name not in self.checks:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check '{name}' not found"
            )
        
        start_time = time.time()
        
        try:
            check_func = self.checks[name]
            
            # Handle both sync and async functions
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            duration_ms = (time.time() - start_time) * 1000
            
            if isinstance(result, HealthCheck):
                result.duration_ms = duration_ms
                self.last_results[name] = result
                return result
            elif isinstance(result, bool):
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                message = "OK" if result else "Check failed"
                health_check = HealthCheck(
                    name=name,
                    status=status,
                    message=message,
                    duration_ms=duration_ms
                )
                self.last_results[name] = health_check
                return health_check
            else:
                # Assume success if no exception was raised
                health_check = HealthCheck(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    message="OK",
                    duration_ms=duration_ms,
                    details=result if isinstance(result, dict) else {}
                )
                self.last_results[name] = health_check
                return health_check
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            health_check = HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=duration_ms
            )
            self.last_results[name] = health_check
            logger.error(f"Health check '{name}' failed", error=str(e))
            return health_check
    
    async def run_all_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks."""
        results = {}
        
        # Run checks concurrently
        tasks = [self.run_check(name) for name in self.checks.keys()]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(check_results):
            name = list(self.checks.keys())[i]
            if isinstance(result, Exception):
                results[name] = HealthCheck(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(result)
                )
            else:
                results[name] = result
        
        return results
    
    def get_overall_status(self, results: Dict[str, HealthCheck]) -> HealthStatus:
        """Determine overall health status from individual checks."""
        if not results:
            return HealthStatus.UNHEALTHY
        
        statuses = [check.status for check in results.values()]
        
        if all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        elif any(status == HealthStatus.UNHEALTHY for status in statuses):
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.DEGRADED


class PerformanceTracker:
    """Performance tracking utilities."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.tracer = trace.get_tracer(__name__)
    
    def track_operation(self, operation_name: str, labels: Optional[Dict[str, str]] = None):
        """Context manager for tracking operation performance."""
        return OperationTracker(operation_name, self.metrics, self.tracer, labels or {})


class OperationTracker:
    """Context manager for tracking individual operations."""
    
    def __init__(self, operation_name: str, metrics_collector: MetricsCollector, 
                 tracer: trace.Tracer, labels: Dict[str, str]):
        self.operation_name = operation_name
        self.metrics = metrics_collector
        self.tracer = tracer
        self.labels = labels
        self.start_time = None
        self.span = None
    
    def __enter__(self):
        """Start tracking the operation."""
        self.start_time = time.time()
        self.span = self.tracer.start_span(self.operation_name)
        
        # Add labels as span attributes
        for key, value in self.labels.items():
            self.span.set_attribute(key, value)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End tracking and record metrics."""
        duration = time.time() - self.start_time
        
        if self.span:
            if exc_val:
                self.span.record_exception(exc_val)
                self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
            else:
                self.span.set_status(Status(StatusCode.OK))
            
            self.span.set_attribute("duration_seconds", duration)
            self.span.end()
        
        # Record custom metrics based on operation type
        if "db" in self.operation_name.lower():
            self.metrics.record_db_query(self.operation_name, duration)
        elif "agent" in self.operation_name.lower():
            status = "error" if exc_val else "success"
            agent_type = self.labels.get("agent_type", "unknown")
            self.metrics.record_agent_task(agent_type, status, duration)


# Global instances
metrics_collector = MetricsCollector()
health_monitor = HealthMonitor()
performance_tracker = PerformanceTracker(metrics_collector)


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return metrics_collector


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance."""
    return health_monitor


def get_performance_tracker() -> PerformanceTracker:
    """Get the global performance tracker instance."""
    return performance_tracker