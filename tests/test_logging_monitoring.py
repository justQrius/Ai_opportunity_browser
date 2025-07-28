"""
Tests for logging and monitoring system.

This module tests the comprehensive logging, tracing, and monitoring
infrastructure to ensure proper observability across the application.
"""

import pytest
import asyncio
import time
import uuid
from unittest.mock import Mock, patch, AsyncMock
from contextlib import asynccontextmanager

from shared.logging_config import (
    get_logger,
    set_correlation_id,
    get_correlation_id,
    CorrelationContext,
    RequestContext,
    with_correlation,
    with_tracing
)
from shared.monitoring import (
    get_metrics_collector,
    get_health_monitor,
    HealthStatus,
    HealthCheck
)
from shared.observability import (
    ObservabilityManager,
    ObservabilityConfig,
    setup_observability,
    get_observability_manager,
    record_metric
)


class TestLoggingConfiguration:
    """Test logging configuration and correlation tracking."""
    
    def test_logger_creation(self):
        """Test logger creation and basic functionality."""
        logger = get_logger(__name__)
        assert logger is not None
        
        # Test basic logging (should not raise exceptions)
        logger.info("Test log message")
        logger.error("Test error message")
    
    def test_correlation_id_context(self):
        """Test correlation ID context management."""
        test_correlation_id = str(uuid.uuid4())
        
        # Initially no correlation ID
        assert get_correlation_id() is None
        
        # Set correlation ID
        with CorrelationContext(test_correlation_id):
            assert get_correlation_id() == test_correlation_id
        
        # Should be cleared after context
        assert get_correlation_id() is None
    
    def test_request_context(self):
        """Test request context management."""
        test_request_id = str(uuid.uuid4())
        test_correlation_id = str(uuid.uuid4())
        test_user_id = "test_user_123"
        
        with RequestContext(test_request_id, test_correlation_id, test_user_id):
            assert get_correlation_id() == test_correlation_id
            # Additional assertions would require accessing request_id_var and user_id_var
    
    def test_correlation_decorator(self):
        """Test correlation decorator functionality."""
        test_correlation_id = str(uuid.uuid4())
        
        @with_correlation(correlation_id=test_correlation_id)
        def test_function():
            return get_correlation_id()
        
        result = test_function()
        assert result == test_correlation_id
    
    @pytest.mark.asyncio
    async def test_async_correlation_decorator(self):
        """Test correlation decorator with async functions."""
        test_correlation_id = str(uuid.uuid4())
        
        @with_correlation(correlation_id=test_correlation_id)
        async def test_async_function():
            return get_correlation_id()
        
        result = await test_async_function()
        assert result == test_correlation_id


class TestMetricsCollection:
    """Test metrics collection functionality."""
    
    def test_metrics_collector_creation(self):
        """Test metrics collector initialization."""
        collector = get_metrics_collector()
        assert collector is not None
        assert hasattr(collector, 'http_requests_total')
        assert hasattr(collector, 'http_request_duration')
    
    def test_http_request_metrics(self):
        """Test HTTP request metrics recording."""
        collector = get_metrics_collector()
        
        # Record a test HTTP request
        collector.record_http_request(
            method="GET",
            endpoint="/api/v1/opportunities",
            status_code=200,
            duration=0.123
        )
        
        # Verify metrics were recorded (basic check)
        metrics_text = collector.get_metrics()
        assert "http_requests_total" in metrics_text
        assert "http_request_duration_seconds" in metrics_text
    
    def test_database_metrics(self):
        """Test database metrics recording."""
        collector = get_metrics_collector()
        
        # Record database query
        collector.record_db_query("SELECT", 0.045)
        
        # Set connection count
        collector.set_db_connections(5)
        
        # Verify metrics
        metrics_text = collector.get_metrics()
        assert "db_query_duration_seconds" in metrics_text
        assert "db_connections_active" in metrics_text
    
    def test_agent_metrics(self):
        """Test agent metrics recording."""
        collector = get_metrics_collector()
        
        # Record agent task
        collector.record_agent_task("monitoring", "success", 1.234)
        collector.record_agent_task("analysis", "error", 0.567)
        
        # Verify metrics
        metrics_text = collector.get_metrics()
        assert "agent_tasks_total" in metrics_text
        assert "agent_task_duration_seconds" in metrics_text
    
    def test_business_metrics(self):
        """Test business-specific metrics."""
        collector = get_metrics_collector()
        
        # Record business events
        collector.record_opportunity_created()
        collector.record_validation_submitted("market_demand")
        collector.record_cache_hit("redis")
        collector.record_cache_miss("redis")
        
        # Verify metrics
        metrics_text = collector.get_metrics()
        assert "opportunities_created_total" in metrics_text
        assert "validations_submitted_total" in metrics_text
        assert "cache_hits_total" in metrics_text
        assert "cache_misses_total" in metrics_text


class TestHealthMonitoring:
    """Test health monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_health_monitor_creation(self):
        """Test health monitor initialization."""
        monitor = get_health_monitor()
        assert monitor is not None
        assert hasattr(monitor, 'checks')
        assert hasattr(monitor, 'last_results')
    
    @pytest.mark.asyncio
    async def test_health_check_registration(self):
        """Test health check registration."""
        monitor = get_health_monitor()
        
        def test_check():
            return True
        
        monitor.register_check("test_service", test_check)
        assert "test_service" in monitor.checks
    
    @pytest.mark.asyncio
    async def test_successful_health_check(self):
        """Test successful health check execution."""
        monitor = get_health_monitor()
        
        def healthy_check():
            return HealthCheck(
                name="test_healthy",
                status=HealthStatus.HEALTHY,
                message="Service is healthy"
            )
        
        monitor.register_check("test_healthy", healthy_check)
        result = await monitor.run_check("test_healthy")
        
        assert result.name == "test_healthy"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Service is healthy"
        assert result.duration_ms is not None
    
    @pytest.mark.asyncio
    async def test_failing_health_check(self):
        """Test failing health check execution."""
        monitor = get_health_monitor()
        
        def failing_check():
            raise Exception("Service is down")
        
        monitor.register_check("test_failing", failing_check)
        result = await monitor.run_check("test_failing")
        
        assert result.name == "test_failing"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Service is down" in result.message
    
    @pytest.mark.asyncio
    async def test_async_health_check(self):
        """Test async health check execution."""
        monitor = get_health_monitor()
        
        async def async_check():
            await asyncio.sleep(0.01)  # Simulate async work
            return True
        
        monitor.register_check("test_async", async_check)
        result = await monitor.run_check("test_async")
        
        assert result.status == HealthStatus.HEALTHY
        assert result.duration_ms > 0
    
    @pytest.mark.asyncio
    async def test_overall_status_calculation(self):
        """Test overall health status calculation."""
        monitor = get_health_monitor()
        
        # All healthy
        healthy_results = {
            "service1": HealthCheck("service1", HealthStatus.HEALTHY, "OK"),
            "service2": HealthCheck("service2", HealthStatus.HEALTHY, "OK")
        }
        assert monitor.get_overall_status(healthy_results) == HealthStatus.HEALTHY
        
        # One degraded
        degraded_results = {
            "service1": HealthCheck("service1", HealthStatus.HEALTHY, "OK"),
            "service2": HealthCheck("service2", HealthStatus.DEGRADED, "Slow")
        }
        assert monitor.get_overall_status(degraded_results) == HealthStatus.DEGRADED
        
        # One unhealthy
        unhealthy_results = {
            "service1": HealthCheck("service1", HealthStatus.HEALTHY, "OK"),
            "service2": HealthCheck("service2", HealthStatus.UNHEALTHY, "Down")
        }
        assert monitor.get_overall_status(unhealthy_results) == HealthStatus.UNHEALTHY


class TestObservabilityIntegration:
    """Test integrated observability functionality."""
    
    def test_observability_config(self):
        """Test observability configuration."""
        config = ObservabilityConfig(
            service_name="test-service",
            service_version="1.0.0",
            log_level="DEBUG",
            enable_tracing=True,
            enable_metrics=True
        )
        
        assert config.service_name == "test-service"
        assert config.service_version == "1.0.0"
        assert config.log_level == "DEBUG"
        assert config.enable_tracing is True
        assert config.enable_metrics is True
    
    @pytest.mark.asyncio
    async def test_observability_manager_creation(self):
        """Test observability manager creation."""
        config = ObservabilityConfig(service_name="test-service")
        
        # Mock the setup to avoid actual tracing setup
        with patch('shared.observability.setup_logging'), \
             patch('shared.observability.setup_tracing'):
            manager = ObservabilityManager(config)
            
            assert manager.config == config
            assert manager.tracer is not None
            assert manager.meter is not None
            assert manager.metrics_collector is not None
            assert manager.health_monitor is not None
    
    @pytest.mark.asyncio
    async def test_trace_operation_success(self):
        """Test successful operation tracing."""
        config = ObservabilityConfig(service_name="test-service")
        
        with patch('shared.observability.setup_logging'), \
             patch('shared.observability.setup_tracing'):
            manager = ObservabilityManager(config)
            
            # Mock tracer
            mock_span = Mock()
            mock_span.set_attribute = Mock()
            mock_span.set_status = Mock()
            manager.tracer.start_as_current_span = Mock()
            manager.tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
            manager.tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=None)
            
            async with manager.trace_operation("test_operation", {"key": "value"}):
                pass  # Simulate successful operation
            
            # Verify span was configured correctly
            mock_span.set_attribute.assert_called()
            mock_span.set_status.assert_called()
    
    @pytest.mark.asyncio
    async def test_trace_operation_error(self):
        """Test error handling in operation tracing."""
        config = ObservabilityConfig(service_name="test-service")
        
        with patch('shared.observability.setup_logging'), \
             patch('shared.observability.setup_tracing'):
            manager = ObservabilityManager(config)
            
            # Mock tracer
            mock_span = Mock()
            mock_span.record_exception = Mock()
            mock_span.set_status = Mock()
            mock_span.set_attribute = Mock()
            manager.tracer.start_as_current_span = Mock()
            manager.tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
            manager.tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=None)
            
            with pytest.raises(ValueError):
                async with manager.trace_operation("test_operation"):
                    raise ValueError("Test error")
            
            # Verify error was recorded
            mock_span.record_exception.assert_called()
            mock_span.set_status.assert_called()
    
    def test_business_metric_recording(self):
        """Test business metric recording."""
        config = ObservabilityConfig(service_name="test-service")
        
        with patch('shared.observability.setup_logging'), \
             patch('shared.observability.setup_tracing'):
            manager = ObservabilityManager(config)
            
            # Mock metrics
            manager.opportunities_processed = Mock()
            manager.validations_completed = Mock()
            
            # Record metrics
            manager.record_business_metric("opportunity_processed", 1, {"type": "ai"})
            manager.record_business_metric("validation_completed", 1, {"type": "market_demand"})
            
            # Verify metrics were recorded
            manager.opportunities_processed.add.assert_called_with(1, {"type": "ai"})
            manager.validations_completed.add.assert_called_with(1, {"type": "market_demand"})


class TestTracingDecorators:
    """Test tracing decorators and utilities."""
    
    def test_tracing_decorator_sync(self):
        """Test tracing decorator for synchronous functions."""
        @with_tracing("test_operation")
        def test_function():
            return "success"
        
        # Should not raise exceptions
        result = test_function()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_tracing_decorator_async(self):
        """Test tracing decorator for asynchronous functions."""
        @with_tracing("test_async_operation")
        async def test_async_function():
            await asyncio.sleep(0.01)
            return "async_success"
        
        # Should not raise exceptions
        result = await test_async_function()
        assert result == "async_success"
    
    def test_tracing_decorator_error_handling(self):
        """Test tracing decorator error handling."""
        @with_tracing("test_error_operation")
        def test_error_function():
            raise ValueError("Test error")
        
        # Should propagate the exception
        with pytest.raises(ValueError, match="Test error"):
            test_error_function()


@pytest.mark.integration
class TestEndToEndObservability:
    """Integration tests for complete observability flow."""
    
    @pytest.mark.asyncio
    async def test_complete_request_flow(self):
        """Test complete request flow with logging, tracing, and metrics."""
        # This would be an integration test that exercises the full middleware stack
        # For now, we'll test the components work together
        
        correlation_id = str(uuid.uuid4())
        
        with CorrelationContext(correlation_id):
            logger = get_logger(__name__)
            collector = get_metrics_collector()
            
            # Simulate request processing
            start_time = time.time()
            
            logger.info("Processing request", endpoint="/api/v1/opportunities")
            
            # Simulate some work
            await asyncio.sleep(0.01)
            
            duration = time.time() - start_time
            
            # Record metrics
            collector.record_http_request("GET", "/api/v1/opportunities", 200, duration)
            
            logger.info("Request completed", duration=duration)
            
            # Verify correlation ID is maintained
            assert get_correlation_id() == correlation_id
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        """Test health check integration with monitoring."""
        monitor = get_health_monitor()
        
        # Register a test health check
        async def test_service_check():
            return HealthCheck(
                name="test_service",
                status=HealthStatus.HEALTHY,
                message="Test service is healthy"
            )
        
        monitor.register_check("test_service", test_service_check)
        
        # Run health checks
        results = await monitor.run_all_checks()
        
        assert "test_service" in results
        assert results["test_service"].status == HealthStatus.HEALTHY
        
        # Test overall status
        overall_status = monitor.get_overall_status(results)
        assert overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]


if __name__ == "__main__":
    pytest.main([__file__])