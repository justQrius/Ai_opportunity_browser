#!/usr/bin/env python3
"""
Demonstration script for the metrics and alerting system.

This script demonstrates:
- Custom metrics collection
- Alert rule configuration
- Notification system setup
- Real-time metrics streaming
- Dashboard data aggregation
"""

import asyncio
import time
import random
from datetime import datetime, timezone, timedelta
import structlog

from shared.custom_metrics import (
    get_business_metrics_collector,
    get_metric_aggregator,
    get_metrics_streamer,
    record_business_metric,
    setup_custom_metrics
)
from shared.alerting import (
    get_alert_manager,
    setup_alerting_system,
    setup_default_alert_rules,
    AlertRule,
    AlertSeverity,
    NotificationChannel,
    NotificationConfig
)
from shared.monitoring import get_metrics_collector, get_health_monitor
from shared.observability import setup_observability, ObservabilityConfig

logger = structlog.get_logger(__name__)


async def demonstrate_metrics_collection():
    """Demonstrate custom metrics collection."""
    print("\n=== Demonstrating Metrics Collection ===")
    
    # Get collectors
    business_collector = get_business_metrics_collector()
    base_collector = get_metrics_collector()
    aggregator = get_metric_aggregator()
    
    print("Recording business metrics...")
    
    # Simulate business activity
    for i in range(10):
        # Record opportunity creation
        sources = ["reddit", "github", "twitter", "linkedin"]
        categories = ["ai_tools", "automation", "data_analysis", "nlp"]
        ai_types = ["ml", "nlp", "computer_vision", "automation"]
        
        business_collector.record_opportunity_created(
            random.choice(sources),
            random.choice(categories),
            random.choice(ai_types)
        )
        
        # Record validation submission
        validator_types = ["expert", "community", "automated"]
        expertise_areas = ["machine_learning", "software_engineering", "business_analysis"]
        
        business_collector.record_validation_submitted(
            random.choice(validator_types),
            random.choice(expertise_areas)
        )
        
        # Record API requests
        methods = ["GET", "POST", "PUT", "DELETE"]
        endpoints = ["/opportunities", "/validations", "/users", "/search"]
        status_codes = [200, 201, 400, 404, 500]
        
        business_collector.record_api_request(
            random.choice(methods),
            random.choice(endpoints),
            random.choice(status_codes),
            random.uniform(0.1, 2.0)
        )
        
        # Record agent tasks
        agent_types = ["monitoring", "analysis", "research", "trend", "capability"]
        task_types = ["scan_data", "analyze_signal", "research_market", "detect_trend", "assess_feasibility"]
        
        business_collector.record_agent_task(
            random.choice(agent_types),
            random.choice(task_types),
            random.uniform(5.0, 120.0)
        )
        
        # Record user activity
        user_types = ["entrepreneur", "investor", "researcher", "developer"]
        action_types = ["view_opportunity", "submit_validation", "bookmark", "search"]
        
        business_collector.record_user_action(
            random.choice(action_types),
            random.choice(user_types)
        )
        
        # Add to aggregator for trend analysis
        aggregator.add_metric_point("api_requests_per_minute", random.uniform(40, 60))
        aggregator.add_metric_point("error_rate", random.uniform(0.01, 0.05))
        aggregator.add_metric_point("response_time_avg", random.uniform(0.2, 0.8))
        
        await asyncio.sleep(0.1)  # Small delay
    
    print("✓ Recorded 10 sets of business metrics")
    
    # Demonstrate metric aggregation
    print("\nDemonstrating metric aggregation...")
    
    avg_requests = aggregator.get_aggregated_metric("api_requests_per_minute", "avg")
    max_response_time = aggregator.get_aggregated_metric("response_time_avg", "max")
    avg_error_rate = aggregator.get_aggregated_metric("error_rate", "avg")
    
    print(f"✓ Average API requests per minute: {avg_requests:.2f}")
    print(f"✓ Max response time: {max_response_time:.3f}s")
    print(f"✓ Average error rate: {avg_error_rate:.3f}")
    
    # Demonstrate trend analysis
    trend = aggregator.get_metric_trend("api_requests_per_minute", timedelta(minutes=1))
    if trend:
        print(f"✓ API requests trend: {trend['direction']} (magnitude: {trend['magnitude']:.3f})")


async def demonstrate_alerting_system():
    """Demonstrate alert management system."""
    print("\n=== Demonstrating Alerting System ===")
    
    # Get alert manager
    alert_manager = get_alert_manager()
    
    # Configure test notification channels
    print("Configuring notification channels...")
    
    # Email configuration (mock)
    email_config = NotificationConfig(
        channel=NotificationChannel.EMAIL,
        config={
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "from_email": "alerts@ai-opportunity-browser.com",
            "to_emails": ["ops@example.com", "admin@example.com"]
        }
    )
    alert_manager.configure_notifications(email_config)
    
    # Slack configuration (mock)
    slack_config = NotificationConfig(
        channel=NotificationChannel.SLACK,
        config={
            "webhook_url": "https://hooks.slack.com/services/MOCK/WEBHOOK/URL",
            "channel": "#alerts",
            "username": "AlertBot"
        }
    )
    alert_manager.configure_notifications(slack_config)
    
    print("✓ Configured email and Slack notification channels")
    
    # Add custom alert rules
    print("Adding custom alert rules...")
    
    # High API error rate alert
    high_error_rule = AlertRule(
        name="demo_high_error_rate",
        description="Demo: API error rate is above 3%",
        severity=AlertSeverity.HIGH,
        condition="error_rate > 0.03",
        duration=timedelta(seconds=30),
        notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
        labels={"service": "api", "demo": "true"},
        annotations={"runbook": "https://docs.example.com/runbooks/high-error-rate"}
    )
    alert_manager.add_rule(high_error_rule)
    
    # Low opportunity creation rate
    low_opportunity_rule = AlertRule(
        name="demo_low_opportunity_rate",
        description="Demo: Opportunity creation rate is too low",
        severity=AlertSeverity.MEDIUM,
        condition="opportunity_creation_rate < 5.0",
        duration=timedelta(seconds=20),
        notification_channels=[NotificationChannel.SLACK],
        labels={"service": "business", "demo": "true"}
    )
    alert_manager.add_rule(low_opportunity_rule)
    
    print("✓ Added 2 custom alert rules")
    
    # Start alert manager
    print("Starting alert manager...")
    await alert_manager.start()
    print("✓ Alert manager started")
    
    # Simulate some alert conditions
    print("Simulating alert conditions...")
    
    # Mock the metric evaluator to trigger alerts
    original_evaluate = alert_manager.evaluator.evaluate_condition
    
    async def mock_evaluate_condition(condition, labels=None):
        if "error_rate > 0.03" in condition:
            return True  # Trigger high error rate alert
        elif "opportunity_creation_rate < 5.0" in condition:
            return True  # Trigger low opportunity rate alert
        return await original_evaluate(condition, labels)
    
    alert_manager.evaluator.evaluate_condition = mock_evaluate_condition
    
    # Wait for alerts to be evaluated and fired
    print("Waiting for alert evaluation...")
    await asyncio.sleep(35)  # Wait longer than alert duration
    
    # Check active alerts
    active_alerts = await alert_manager.get_active_alerts()
    print(f"✓ {len(active_alerts)} alerts are currently active")
    
    for alert in active_alerts:
        print(f"  - {alert.rule_name}: {alert.message} (severity: {alert.severity.value})")
    
    # Demonstrate alert acknowledgment
    if active_alerts:
        first_alert = active_alerts[0]
        success = await alert_manager.acknowledge_alert(first_alert.fingerprint, "demo_user")
        if success:
            print(f"✓ Acknowledged alert: {first_alert.rule_name}")
    
    # Stop alert manager
    await alert_manager.stop()
    print("✓ Alert manager stopped")


async def demonstrate_real_time_streaming():
    """Demonstrate real-time metrics streaming."""
    print("\n=== Demonstrating Real-Time Metrics Streaming ===")
    
    # Get metrics streamer
    streamer = get_metrics_streamer()
    
    # Create a callback to receive metrics
    received_metrics = []
    
    async def metrics_callback(metrics_data):
        received_metrics.append(metrics_data)
        print(f"Received metrics update: {len(metrics_data)} metrics")
        
        # Show some key metrics
        if "api_requests_per_second" in metrics_data:
            print(f"  API requests/sec: {metrics_data['api_requests_per_second']}")
        if "error_rate" in metrics_data:
            print(f"  Error rate: {metrics_data['error_rate']:.3f}")
        if "active_users" in metrics_data:
            print(f"  Active users: {metrics_data['active_users']}")
    
    # Subscribe to all metrics
    streamer.subscribe("*", metrics_callback)
    print("✓ Subscribed to real-time metrics stream")
    
    # Start streaming
    await streamer.start_streaming()
    print("✓ Started real-time metrics streaming")
    
    # Let it stream for a few seconds
    print("Streaming metrics for 5 seconds...")
    await asyncio.sleep(5)
    
    # Stop streaming
    await streamer.stop_streaming()
    print("✓ Stopped metrics streaming")
    
    print(f"✓ Received {len(received_metrics)} metric updates during streaming")


async def demonstrate_health_monitoring():
    """Demonstrate health monitoring integration."""
    print("\n=== Demonstrating Health Monitoring ===")
    
    health_monitor = get_health_monitor()
    
    # Register custom health checks
    def custom_service_check():
        """Mock custom service health check."""
        return random.choice([True, True, True, False])  # 75% healthy
    
    async def async_service_check():
        """Mock async service health check."""
        await asyncio.sleep(0.1)  # Simulate async operation
        return {
            "status": "healthy",
            "connections": 15,
            "response_time": 0.234
        }
    
    health_monitor.register_check("custom_service", custom_service_check)
    health_monitor.register_check("async_service", async_service_check)
    
    print("✓ Registered custom health checks")
    
    # Run all health checks
    print("Running health checks...")
    health_results = await health_monitor.run_all_checks()
    
    overall_status = health_monitor.get_overall_status(health_results)
    print(f"✓ Overall health status: {overall_status.value}")
    
    for name, result in health_results.items():
        status_icon = "✓" if result.status.value == "healthy" else "✗"
        duration = f"({result.duration_ms:.1f}ms)" if result.duration_ms else ""
        print(f"  {status_icon} {name}: {result.status.value} - {result.message} {duration}")


async def demonstrate_prometheus_integration():
    """Demonstrate Prometheus metrics integration."""
    print("\n=== Demonstrating Prometheus Integration ===")
    
    # Get metrics in Prometheus format
    base_collector = get_metrics_collector()
    business_collector = get_business_metrics_collector()
    
    # Generate some activity to create metrics
    base_collector.record_http_request("GET", "/demo", 200, 0.5)
    base_collector.record_db_query("SELECT", 0.1)
    base_collector.record_opportunity_created()
    
    business_collector.record_opportunity_created("demo", "test", "ml")
    business_collector.record_api_request("GET", "/demo", 200, 0.5)
    
    # Get Prometheus metrics
    prometheus_metrics = base_collector.get_metrics()
    
    print("✓ Generated Prometheus metrics")
    print(f"✓ Metrics size: {len(prometheus_metrics)} characters")
    
    # Show sample metrics
    lines = prometheus_metrics.split('\n')
    metric_lines = [line for line in lines if line and not line.startswith('#')][:5]
    
    print("Sample metrics:")
    for line in metric_lines:
        if line.strip():
            print(f"  {line}")


async def run_comprehensive_demo():
    """Run comprehensive demonstration of metrics and alerting system."""
    print("🚀 AI Opportunity Browser - Metrics & Alerting System Demo")
    print("=" * 60)
    
    try:
        # Setup observability
        config = ObservabilityConfig(
            service_name="ai-opportunity-browser-demo",
            log_level="INFO",
            enable_tracing=False,  # Disable for demo
            enable_metrics=True
        )
        setup_observability(config)
        
        # Setup custom metrics
        await setup_custom_metrics()
        
        # Setup alerting system (without starting)
        setup_default_alert_rules()
        
        print("✓ Initialized observability, metrics, and alerting systems")
        
        # Run demonstrations
        await demonstrate_metrics_collection()
        await demonstrate_health_monitoring()
        await demonstrate_alerting_system()
        await demonstrate_real_time_streaming()
        await demonstrate_prometheus_integration()
        
        print("\n" + "=" * 60)
        print("🎉 Demo completed successfully!")
        print("\nKey features demonstrated:")
        print("  ✓ Custom business metrics collection")
        print("  ✓ Metric aggregation and trend analysis")
        print("  ✓ Alert rule configuration and evaluation")
        print("  ✓ Multi-channel notification system")
        print("  ✓ Real-time metrics streaming")
        print("  ✓ Health monitoring integration")
        print("  ✓ Prometheus metrics export")
        
        print("\nNext steps:")
        print("  • Configure real notification channels (email, Slack, PagerDuty)")
        print("  • Set up Prometheus and Grafana for visualization")
        print("  • Deploy Alertmanager for production alerting")
        print("  • Create custom dashboards for business metrics")
        print("  • Implement additional health checks for all services")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"\n❌ Demo failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    
    # Run the demo
    exit_code = asyncio.run(run_comprehensive_demo())
    sys.exit(exit_code)