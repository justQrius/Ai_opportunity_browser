#!/usr/bin/env python3
"""
Demonstration script for logging and monitoring system.

This script demonstrates the comprehensive logging, tracing, and monitoring
capabilities of the AI Opportunity Browser platform.
"""

import asyncio
import time
import uuid
import random
from typing import Dict, Any

# Import our logging and monitoring components
from shared.logging_config import (
    get_logger,
    setup_logging,
    setup_tracing,
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
    record_metric
)

# Setup logging and tracing
logger = get_logger(__name__)


async def demo_basic_logging():
    """Demonstrate basic structured logging."""
    print("\n=== Basic Logging Demo ===")
    
    logger.info("Starting logging demonstration")
    logger.info("Processing user request", user_id="user_123", action="view_opportunities")
    logger.warning("Rate limit approaching", current_requests=95, limit=100)
    logger.error("Database connection failed", error="Connection timeout", retry_count=3)
    
    # Demonstrate logging with extra context
    logger.info(
        "Opportunity created successfully",
        opportunity_id="opp_456",
        title="AI-powered customer service",
        market_size="$2.5B",
        validation_score=8.5
    )


async def demo_correlation_tracking():
    """Demonstrate correlation ID tracking."""
    print("\n=== Correlation Tracking Demo ===")
    
    correlation_id = str(uuid.uuid4())
    
    logger.info("Starting request without correlation ID")
    
    with CorrelationContext(correlation_id, user_id="user_789"):
        logger.info("Processing request with correlation ID")
        
        # Simulate nested operations
        await simulate_database_operation()
        await simulate_ai_agent_operation()
        
        logger.info("Request completed successfully")
    
    logger.info("Back to no correlation context")


async def simulate_database_operation():
    """Simulate a database operation with logging."""
    logger.info("Starting database query", operation="SELECT", table="opportunities")
    await asyncio.sleep(0.1)  # Simulate DB latency
    logger.info("Database query completed", rows_returned=25, duration_ms=100)


async def simulate_ai_agent_operation():
    """Simulate an AI agent operation with logging."""
    logger.info("Starting AI agent task", agent_type="analysis", task="opportunity_scoring")
    await asyncio.sleep(0.2)  # Simulate AI processing
    logger.info("AI agent task completed", score=7.8, confidence=0.92)


@with_correlation()
async def demo_correlation_decorator():
    """Demonstrate correlation decorator."""
    print("\n=== Correlation Decorator Demo ===")
    
    logger.info("Function with automatic correlation tracking")
    await simulate_database_operation()


@with_tracing("demo_tracing_operation")
async def demo_tracing_decorator():
    """Demonstrate tracing decorator."""
    print("\n=== Tracing Decorator Demo ===")
    
    logger.info("Function with automatic tracing")
    await asyncio.sleep(0.05)
    return {"result": "success", "processing_time": 0.05}


async def demo_metrics_collection():
    """Demonstrate metrics collection."""
    print("\n=== Metrics Collection Demo ===")
    
    collector = get_metrics_collector()
    
    # Simulate various operations and record metrics
    for i in range(5):
        # HTTP requests
        method = random.choice(["GET", "POST", "PUT"])
        endpoint = random.choice(["/api/v1/opportunities", "/api/v1/validations", "/api/v1/users"])
        status_code = random.choice([200, 201, 400, 404, 500])
        duration = random.uniform(0.1, 2.0)
        
        collector.record_http_request(method, endpoint, status_code, duration)
        logger.info(f"Recorded HTTP request metric: {method} {endpoint} -> {status_code}")
        
        # Database operations
        db_operation = random.choice(["SELECT", "INSERT", "UPDATE", "DELETE"])
        db_duration = random.uniform(0.01, 0.5)
        collector.record_db_query(db_operation, db_duration)
        logger.info(f"Recorded DB metric: {db_operation} ({db_duration:.3f}s)")
        
        # Agent operations
        agent_type = random.choice(["monitoring", "analysis", "research", "trend"])
        agent_status = random.choice(["success", "error"])
        agent_duration = random.uniform(0.5, 5.0)
        collector.record_agent_task(agent_type, agent_status, agent_duration)
        logger.info(f"Recorded agent metric: {agent_type} -> {agent_status}")
        
        # Business metrics
        if random.random() > 0.5:
            collector.record_opportunity_created()
            logger.info("Recorded opportunity creation")
        
        if random.random() > 0.3:
            validation_type = random.choice(["market_demand", "technical_feasibility", "business_viability"])
            collector.record_validation_submitted(validation_type)
            logger.info(f"Recorded validation: {validation_type}")
        
        await asyncio.sleep(0.1)
    
    # Display current metrics
    print("\nCurrent Prometheus Metrics:")
    print("=" * 50)
    metrics_text = collector.get_metrics()
    # Show just a sample of the metrics
    lines = metrics_text.split('\n')
    for line in lines[:20]:  # Show first 20 lines
        if line.strip() and not line.startswith('#'):
            print(line)
    print("... (truncated)")


async def demo_health_monitoring():
    """Demonstrate health monitoring."""
    print("\n=== Health Monitoring Demo ===")
    
    monitor = get_health_monitor()
    
    # Register some demo health checks
    def healthy_service():
        return HealthCheck(
            name="demo_service_1",
            status=HealthStatus.HEALTHY,
            message="Service is running normally"
        )
    
    def degraded_service():
        return HealthCheck(
            name="demo_service_2",
            status=HealthStatus.DEGRADED,
            message="Service is slow but functional",
            details={"response_time_ms": 2500, "threshold_ms": 1000}
        )
    
    async def async_service():
        await asyncio.sleep(0.05)  # Simulate async check
        if random.random() > 0.3:
            return HealthCheck(
                name="demo_async_service",
                status=HealthStatus.HEALTHY,
                message="Async service check passed"
            )
        else:
            return HealthCheck(
                name="demo_async_service",
                status=HealthStatus.UNHEALTHY,
                message="Async service check failed"
            )
    
    def failing_service():
        raise Exception("Service is completely down")
    
    # Register health checks
    monitor.register_check("healthy_service", healthy_service)
    monitor.register_check("degraded_service", degraded_service)
    monitor.register_check("async_service", async_service)
    monitor.register_check("failing_service", failing_service)
    
    # Run individual health checks
    print("Running individual health checks:")
    for service_name in ["healthy_service", "degraded_service", "async_service", "failing_service"]:
        result = await monitor.run_check(service_name)
        print(f"  {service_name}: {result.status.value} - {result.message}")
        if result.duration_ms:
            print(f"    Duration: {result.duration_ms:.2f}ms")
    
    # Run all health checks
    print("\nRunning all health checks:")
    all_results = await monitor.run_all_checks()
    overall_status = monitor.get_overall_status(all_results)
    
    print(f"Overall Status: {overall_status.value}")
    for name, result in all_results.items():
        status_icon = "✅" if result.status == HealthStatus.HEALTHY else "⚠️" if result.status == HealthStatus.DEGRADED else "❌"
        print(f"  {status_icon} {name}: {result.message}")


async def demo_observability_integration():
    """Demonstrate integrated observability."""
    print("\n=== Observability Integration Demo ===")
    
    # Setup observability
    config = ObservabilityConfig(
        service_name="demo-service",
        service_version="1.0.0",
        log_level="INFO",
        enable_tracing=True,
        enable_metrics=True
    )
    
    try:
        manager = setup_observability(config)
        logger.info("Observability system initialized")
        
        # Demonstrate traced operations
        async with manager.trace_operation("demo_business_operation", {"operation_type": "opportunity_analysis"}):
            logger.info("Performing business operation")
            
            # Simulate some work
            await asyncio.sleep(0.1)
            
            # Record business metrics
            record_metric("opportunity_processed", 1, {"type": "ai_automation"})
            record_metric("validation_completed", 1, {"type": "market_demand"})
            
            logger.info("Business operation completed")
        
        # Get health status
        health_status = await manager.get_health_status()
        print(f"\nSystem Health: {health_status['status']}")
        print(f"Service: {health_status['service']} v{health_status['version']}")
        
        if health_status['checks']:
            print("Health Checks:")
            for name, check in health_status['checks'].items():
                status_icon = "✅" if check['status'] == "healthy" else "⚠️" if check['status'] == "degraded" else "❌"
                print(f"  {status_icon} {name}: {check['message']}")
        
    except Exception as e:
        logger.error(f"Observability demo failed: {e}")


async def demo_request_simulation():
    """Simulate a complete request with full observability."""
    print("\n=== Complete Request Simulation ===")
    
    request_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    user_id = "user_demo_123"
    
    with RequestContext(request_id, correlation_id, user_id):
        logger.info("Incoming HTTP request", method="GET", path="/api/v1/opportunities", client_ip="192.168.1.100")
        
        start_time = time.time()
        
        try:
            # Simulate authentication
            logger.info("Authenticating user")
            await asyncio.sleep(0.02)
            
            # Simulate database query
            logger.info("Querying opportunities from database")
            await asyncio.sleep(0.15)
            
            # Simulate AI processing
            logger.info("Running AI analysis on opportunities")
            await asyncio.sleep(0.3)
            
            # Simulate response preparation
            logger.info("Preparing response")
            await asyncio.sleep(0.05)
            
            duration = time.time() - start_time
            
            # Record metrics
            collector = get_metrics_collector()
            collector.record_http_request("GET", "/api/v1/opportunities", 200, duration)
            
            logger.info(
                "Request completed successfully",
                status_code=200,
                duration_ms=round(duration * 1000, 2),
                opportunities_returned=25
            )
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record error metrics
            collector = get_metrics_collector()
            collector.record_http_request("GET", "/api/v1/opportunities", 500, duration)
            
            logger.error(
                "Request failed",
                error=str(e),
                duration_ms=round(duration * 1000, 2),
                exc_info=True
            )


async def main():
    """Run all demonstrations."""
    print("🚀 AI Opportunity Browser - Logging & Monitoring Demo")
    print("=" * 60)
    
    # Setup basic logging
    setup_logging(
        log_level="INFO",
        service_name="demo-service",
        enable_console_output=True
    )
    
    try:
        await demo_basic_logging()
        await demo_correlation_tracking()
        await demo_correlation_decorator()
        await demo_tracing_decorator()
        await demo_metrics_collection()
        await demo_health_monitoring()
        await demo_observability_integration()
        await demo_request_simulation()
        
        print("\n✅ All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("- Structured JSON logging with correlation IDs")
        print("- Distributed tracing with OpenTelemetry")
        print("- Prometheus metrics collection")
        print("- Health monitoring and checks")
        print("- Integrated observability management")
        print("- Request/response lifecycle tracking")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"\n❌ Demo failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())