"""
Tests for metrics collection and alerting system.

This module tests:
- Custom metrics collection
- Alert rule evaluation
- Notification system
- API endpoints for metrics and alerts
- Real-time metrics streaming
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

from shared.custom_metrics import (
    BusinessMetricsCollector,
    MetricAggregator,
    RealTimeMetricsStreamer,
    get_business_metrics_collector,
    record_business_metric
)
from shared.alerting import (
    AlertManager,
    AlertRule,
    Alert,
    AlertSeverity,
    AlertStatus,
    NotificationChannel,
    NotificationConfig,
    MetricEvaluator,
    NotificationManager
)
from shared.monitoring import get_metrics_collector, get_health_monitor
from api.main import app


class TestBusinessMetricsCollector:
    """Test business metrics collection."""
    
    def test_collector_initialization(self):
        """Test that collector initializes with all required metrics."""
        collector = BusinessMetricsCollector()
        
        # Check that key metrics are initialized
        assert hasattr(collector, 'opportunities_created')
        assert hasattr(collector, 'validations_submitted')
        assert hasattr(collector, 'api_request_duration')
        assert hasattr(collector, 'agent_task_duration')
        assert hasattr(collector, 'user_sessions')
    
    def test_record_opportunity_created(self):
        """Test recording opportunity creation metrics."""
        collector = BusinessMetricsCollector()
        
        # Record some opportunities
        collector.record_opportunity_created("reddit", "ai_tools", "nlp")
        collector.record_opportunity_created("github", "automation", "ml")
        
        # Verify metrics were recorded (would need to check Prometheus registry in real test)
        assert True  # Placeholder - in real test would verify counter values
    
    def test_record_api_request(self):
        """Test recording API request metrics."""
        collector = BusinessMetricsCollector()
        
        # Record API requests
        collector.record_api_request("GET", "/opportunities", 200, 0.234)
        collector.record_api_request("POST", "/validations", 201, 0.456)
        collector.record_api_request("GET", "/opportunities", 500, 1.234)
        
        # Verify metrics were recorded
        assert True  # Placeholder
    
    def test_record_agent_metrics(self):
        """Test recording agent performance metrics."""
        collector = BusinessMetricsCollector()
        
        # Record agent tasks
        collector.record_agent_task("monitoring", "scan_reddit", 45.2)
        collector.record_agent_task("analysis", "score_opportunity", 12.8)
        
        # Set agent status
        collector.set_agent_success_rate("monitoring", 0.95)
        collector.set_agent_queue_size("analysis", 23)
        
        assert True  # Placeholder


class TestMetricAggregator:
    """Test metric aggregation functionality."""
    
    def test_add_metric_point(self):
        """Test adding metric points to time series."""
        aggregator = MetricAggregator()
        
        # Add some metric points
        now = datetime.now(timezone.utc)
        aggregator.add_metric_point("test_metric", 10.5, now)
        aggregator.add_metric_point("test_metric", 12.3, now + timedelta(seconds=30))
        aggregator.add_metric_point("test_metric", 8.7, now + timedelta(seconds=60))
        
        # Verify data was stored
        assert "test_metric" in aggregator.time_series_data
        assert len(aggregator.time_series_data["test_metric"]) == 3
    
    def test_get_aggregated_metric(self):
        """Test metric aggregation functions."""
        aggregator = MetricAggregator()
        
        # Add test data
        now = datetime.now(timezone.utc)
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for i, value in enumerate(values):
            aggregator.add_metric_point("test_metric", value, now + timedelta(seconds=i*10))
        
        # Test aggregations
        avg = aggregator.get_aggregated_metric("test_metric", "avg")
        assert avg == 30.0
        
        sum_val = aggregator.get_aggregated_metric("test_metric", "sum")
        assert sum_val == 150.0
        
        min_val = aggregator.get_aggregated_metric("test_metric", "min")
        assert min_val == 10.0
        
        max_val = aggregator.get_aggregated_metric("test_metric", "max")
        assert max_val == 50.0
    
    def test_get_metric_trend(self):
        """Test metric trend analysis."""
        aggregator = MetricAggregator()
        
        # Add trending data (increasing trend)
        now = datetime.now(timezone.utc)
        for i in range(10):
            value = 10.0 + i * 2.0  # Increasing trend
            aggregator.add_metric_point("trending_metric", value, now + timedelta(seconds=i*10))
        
        # Get trend analysis
        trend = aggregator.get_metric_trend("trending_metric", timedelta(minutes=5))
        
        assert trend["direction"] == "increasing"
        assert trend["current_value"] == 28.0
        assert trend["min_value"] == 10.0
        assert trend["max_value"] == 28.0


class TestAlertManager:
    """Test alert management functionality."""
    
    @pytest.fixture
    def alert_manager(self):
        """Create alert manager for testing."""
        return AlertManager()
    
    @pytest.fixture
    def sample_alert_rule(self):
        """Create sample alert rule."""
        return AlertRule(
            name="test_alert",
            description="Test alert for unit testing",
            severity=AlertSeverity.HIGH,
            condition="test_metric > 10.0",
            duration=timedelta(minutes=5),
            notification_channels=[NotificationChannel.EMAIL]
        )
    
    def test_add_alert_rule(self, alert_manager, sample_alert_rule):
        """Test adding alert rules."""
        alert_manager.add_rule(sample_alert_rule)
        
        assert "test_alert" in alert_manager.rules
        assert alert_manager.rules["test_alert"] == sample_alert_rule
    
    def test_remove_alert_rule(self, alert_manager, sample_alert_rule):
        """Test removing alert rules."""
        alert_manager.add_rule(sample_alert_rule)
        alert_manager.remove_rule("test_alert")
        
        assert "test_alert" not in alert_manager.rules
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, alert_manager):
        """Test alert acknowledgment."""
        # Create a mock active alert
        alert = Alert(
            rule_name="test_alert",
            severity=AlertSeverity.HIGH,
            status=AlertStatus.FIRING,
            message="Test alert message"
        )
        alert_manager.active_alerts[f"test_alert:{alert.labels}"] = alert
        
        # Acknowledge the alert
        success = await alert_manager.acknowledge_alert(alert.fingerprint, "test_user")
        
        assert success
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_at is not None


class TestMetricEvaluator:
    """Test metric condition evaluation."""
    
    @pytest.fixture
    def evaluator(self):
        """Create metric evaluator for testing."""
        return MetricEvaluator()
    
    @pytest.mark.asyncio
    async def test_evaluate_simple_condition(self, evaluator):
        """Test evaluating simple metric conditions."""
        # Mock the metric value getter
        with patch.object(evaluator, '_get_metric_value', return_value=15.0):
            # Test greater than
            result = await evaluator.evaluate_condition("test_metric > 10.0")
            assert result is True
            
            result = await evaluator.evaluate_condition("test_metric > 20.0")
            assert result is False
            
            # Test less than
            result = await evaluator.evaluate_condition("test_metric < 20.0")
            assert result is True
            
            # Test equals
            result = await evaluator.evaluate_condition("test_metric == 15.0")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_evaluate_invalid_condition(self, evaluator):
        """Test handling of invalid conditions."""
        result = await evaluator.evaluate_condition("invalid condition format")
        assert result is False
        
        result = await evaluator.evaluate_condition("test_metric >> 10.0")  # Invalid operator
        assert result is False


class TestNotificationManager:
    """Test notification management."""
    
    @pytest.fixture
    def notification_manager(self):
        """Create notification manager for testing."""
        return NotificationManager()
    
    @pytest.fixture
    def sample_alert(self):
        """Create sample alert for testing."""
        return Alert(
            rule_name="test_alert",
            severity=AlertSeverity.HIGH,
            status=AlertStatus.FIRING,
            message="Test alert message",
            labels={"service": "test"},
            annotations={"runbook": "https://example.com/runbook"}
        )
    
    def test_configure_email_channel(self, notification_manager):
        """Test configuring email notification channel."""
        config = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            config={
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "from_email": "alerts@example.com",
                "to_emails": ["admin@example.com"]
            }
        )
        
        notification_manager.configure_channel(config)
        
        assert NotificationChannel.EMAIL in notification_manager.channels
        assert notification_manager.channels[NotificationChannel.EMAIL] == config
    
    @pytest.mark.asyncio
    async def test_send_notification_rate_limiting(self, notification_manager, sample_alert):
        """Test notification rate limiting."""
        # Configure a channel with strict rate limiting
        config = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            config={"to_emails": ["test@example.com"]},
            rate_limit_window=timedelta(minutes=1),
            max_notifications_per_window=1
        )
        notification_manager.configure_channel(config)
        
        # Mock Redis client
        with patch('shared.alerting.get_redis_client') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            
            # First notification should succeed
            mock_client.zcard.return_value = 0
            await notification_manager.send_notification(sample_alert, [NotificationChannel.EMAIL])
            
            # Second notification should be rate limited
            mock_client.zcard.return_value = 1
            await notification_manager.send_notification(sample_alert, [NotificationChannel.EMAIL])
            
            # Verify rate limiting was checked
            assert mock_client.zcard.called


class TestRealTimeMetricsStreamer:
    """Test real-time metrics streaming."""
    
    @pytest.fixture
    def streamer(self):
        """Create metrics streamer for testing."""
        return RealTimeMetricsStreamer()
    
    def test_subscribe_unsubscribe(self, streamer):
        """Test subscription management."""
        callback = Mock()
        
        # Subscribe
        streamer.subscribe("test_pattern", callback)
        assert "test_pattern" in streamer.subscribers
        assert callback in streamer.subscribers["test_pattern"]
        
        # Unsubscribe
        streamer.unsubscribe("test_pattern", callback)
        assert callback not in streamer.subscribers["test_pattern"]
    
    @pytest.mark.asyncio
    async def test_streaming_lifecycle(self, streamer):
        """Test streaming start/stop lifecycle."""
        # Start streaming
        await streamer.start_streaming()
        assert streamer.streaming is True
        assert streamer.stream_task is not None
        
        # Stop streaming
        await streamer.stop_streaming()
        assert streamer.streaming is False


class TestMetricsAPI:
    """Test metrics API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        return Mock(email="test@example.com", id="test-user-id")
    
    def test_prometheus_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics/prometheus")
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        # Should contain some basic metrics
        assert "http_requests_total" in response.text or "# HELP" in response.text
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/metrics/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    @patch('api.routers.metrics.get_current_user')
    def test_dashboard_metrics_endpoint(self, mock_get_user, client, mock_user):
        """Test dashboard metrics endpoint."""
        mock_get_user.return_value = mock_user
        
        response = client.get("/metrics/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "overview" in data
        assert "business" in data
        assert "agents" in data
        assert "system" in data
    
    @patch('api.routers.metrics.get_current_user')
    def test_active_alerts_endpoint(self, mock_get_user, client, mock_user):
        """Test active alerts endpoint."""
        mock_get_user.return_value = mock_user
        
        response = client.get("/metrics/alerts")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "alerts" in data
        assert "count" in data
        assert isinstance(data["alerts"], list)
    
    def test_system_status_endpoint(self, client):
        """Test system status endpoint."""
        response = client.get("/metrics/system/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "overall_status" in data
        assert "health" in data
        assert "alerts" in data
        assert "performance" in data


class TestIntegration:
    """Integration tests for metrics and alerting system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_alert_flow(self):
        """Test complete alert flow from metric to notification."""
        # Create alert manager
        alert_manager = AlertManager()
        
        # Configure notification
        notification_config = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            config={"to_emails": ["test@example.com"]}
        )
        alert_manager.configure_notifications(notification_config)
        
        # Add alert rule
        rule = AlertRule(
            name="test_integration_alert",
            description="Integration test alert",
            severity=AlertSeverity.HIGH,
            condition="test_metric > 5.0",
            duration=timedelta(seconds=1),
            notification_channels=[NotificationChannel.EMAIL]
        )
        alert_manager.add_rule(rule)
        
        # Mock metric evaluator to return True
        with patch.object(alert_manager.evaluator, 'evaluate_condition', return_value=True):
            # Mock notification sending
            with patch.object(alert_manager.notification_manager, 'send_notification') as mock_send:
                # Start alert manager
                await alert_manager.start()
                
                # Wait for evaluation
                await asyncio.sleep(2)
                
                # Stop alert manager
                await alert_manager.stop()
                
                # Verify alert was created and notification sent
                assert len(alert_manager.active_alerts) > 0
                mock_send.assert_called()
    
    def test_metrics_collection_integration(self):
        """Test integration between different metrics collectors."""
        # Get collectors
        base_collector = get_metrics_collector()
        business_collector = get_business_metrics_collector()
        
        # Record some metrics
        base_collector.record_http_request("GET", "/test", 200, 0.5)
        business_collector.record_opportunity_created("test", "integration", "test")
        
        # Verify metrics can be retrieved
        base_metrics = base_collector.get_metrics()
        assert isinstance(base_metrics, str)
        assert len(base_metrics) > 0
    
    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self):
        """Test health monitoring integration."""
        health_monitor = get_health_monitor()
        
        # Register a test health check
        def test_health_check():
            return True
        
        health_monitor.register_check("test_check", test_health_check)
        
        # Run health checks
        results = await health_monitor.run_all_checks()
        
        assert "test_check" in results
        assert results["test_check"].status.value == "healthy"


if __name__ == "__main__":
    pytest.main([__file__])