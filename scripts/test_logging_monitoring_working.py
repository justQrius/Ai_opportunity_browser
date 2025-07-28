#!/usr/bin/env python3
"""
Working demonstration of logging and monitoring system.

This script demonstrates the implemented logging, metrics, and monitoring
capabilities that are currently working in the AI Opportunity Browser.
"""

import asyncio
import time
import uuid
import random
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.logging_config import (
    get_logger,
    setup_logging,
    CorrelationContext,
    RequestContext,
    with_correlation,
    generate_correlation_id
)
from shared.monitoring import (
    get_metrics_collector,
    get_health_monitor,
    HealthStatus,
    HealthCheck
)

# Setup logging
setup_logging(
    log_level="INFO",
    service_name="demo-service",
    enable_console_output=True
)

logger = get_logger(__name__)


async def demo_structured_logging():
    """Demonstrate structured logging capabilities."""
    print("\n=== Structured Logging Demo ===")
    
    logger.info("Starting structured logging demonstration")
    
    # Basic structured logging
    logger.info("User action", 
                user_id="user_123", 
                action="view_opportunities", 
                timestamp=time.time())
    
    logger.warning("Performance warning", 
                   response_time_ms=1500, 
                   threshold_ms=1000,
                   endpoint="/api/v1/opportunities")
    
    logger.error("Service error", 
                 error_type="DatabaseConnectionError",
                 error_message="Connection timeout after 30s",
                 retry_count=3,
                 service="postgresql")
    
    # Business event logging
    logger.info("Opportunity created",
                opportunity_id="opp_789",
                title="AI-powered inventory management",
                market_size_usd=1500000000,
                validation_score=8.7,
                ai_technologies=["machine_learning", "computer_vision"],
                created_by="user_456")
    
    print("✅ Structured logging completed")


async def demo_correlation_tracking():
    """Demonstrate correlation ID tracking across operations."""
    print("\n=== Correlation Tracking Demo ===")
    
    correlation_id = generate_correlation_id()
    user_id = "user_demo_789"
    
    logger.info("Starting request processing without correlation")
    
    # Use correlation context
    with CorrelationContext(correlation_id, user_id):
        logger.info("Processing request with correlation tracking")
        
        # Simulate nested operations that maintain correlation
        await simulate_authentication()
        await simulate_database_query()
        await simulate_ai_processing()
        
        logger.info("Request processing completed successfully")
    
    logger.info("Back to no correlation context")
    print("✅ Correlation tracking completed")


async def simulate_authentication():
    """Simulate authentication with logging."""
    logger.info("Authenticating user", operation="auth", step="token_validation")
    await asyncio.sleep(0.02)  # Simulate auth latency
    logger.info("User authenticated successfully", operation="auth", duration_ms=20)


async def simulate_database_query():
    """Simulate database operations with logging."""
    logger.info("Executing database query", 
                operation="db_query", 
                table="opportunities", 
                query_type="SELECT")
    await asyncio.sleep(0.1)  # Simulate DB latency
    logger.info("Database query completed", 
                operation="db_query", 
                rows_returned=42, 
                duration_ms=100)


async def simulate_ai_processing():
    """Simulate AI agent processing with logging."""
    logger.info("Starting AI analysis", 
                operation="ai_processing", 
                agent_type="opportunity_analyzer",
                model="gpt-4")
    await asyncio.sleep(0.2)  # Simulate AI processing
    logger.info("AI analysis completed", 
                operation="ai_processing", 
                confidence_score=0.94,
                processing_time_ms=200)


@with_correlation()
async def demo_correlation_decorator():
    """Demonstrate automatic correlation tracking with decorator."""
    print("\n=== Correlation Decorator Demo ===")
    
    logger.info("Function with automatic correlation tracking")
    await simulate_database_query()
    print("✅ Correlation decorator completed")


async def demo_metrics_collection():
    """Demonstrate comprehensive metrics collection."""
    print("\n=== Metrics Collection Demo ===")
    
    collector = get_metrics_collector()
    
    # Simulate various HTTP requests
    endpoints = ["/api/v1/opportunities", "/api/v1/validations", "/api/v1/users", "/api/v1/discussions"]
    methods = ["GET", "POST", "PUT", "DELETE"]
    status_codes = [200, 201, 400, 404, 500]
    
    print("Recording HTTP request metrics...")
    for i in range(10):
        method = random.choice(methods)
        endpoint = random.choice(endpoints)
        status_code = random.choice(status_codes)
        duration = random.uniform(0.05, 2.0)
        
        collector.record_http_request(method, endpoint, status_code, duration)
        logger.info(f"HTTP request recorded", 
                   method=method, 
                   endpoint=endpoint, 
                   status_code=status_code,
                   duration_ms=round(duration * 1000, 2))
    
    # Simulate database operations
    print("Recording database metrics...")
    db_operations = ["SELECT", "INSERT", "UPDATE", "DELETE"]
    for i in range(5):
        operation = random.choice(db_operations)
        duration = random.uniform(0.01, 0.5)
        collector.record_db_query(operation, duration)
        logger.info(f"Database operation recorded", 
                   operation=operation, 
                   duration_ms=round(duration * 1000, 2))
    
    # Simulate agent tasks
    print("Recording agent metrics...")
    agent_types = ["monitoring", "analysis", "research", "trend", "capability"]
    statuses = ["success", "error"]
    for i in range(8):
        agent_type = random.choice(agent_types)
        status = random.choice(statuses)
        duration = random.uniform(0.5, 5.0)
        collector.record_agent_task(agent_type, status, duration)
        logger.info(f"Agent task recorded", 
                   agent_type=agent_type, 
                   status=status,
                   duration_ms=round(duration * 1000, 2))
    
    # Simulate business events
    print("Recording business metrics...")
    for i in range(3):
        collector.record_opportunity_created()
        logger.info("Opportunity creation recorded")
    
    validation_types = ["market_demand", "technical_feasibility", "business_viability"]
    for i in range(5):
        validation_type = random.choice(validation_types)
        collector.record_validation_submitted(validation_type)
        logger.info(f"Validation recorded", validation_type=validation_type)
    
    # Cache metrics
    cache_types = ["redis", "memory"]
    for i in range(6):
        cache_type = random.choice(cache_types)
        if random.random() > 0.3:
            collector.record_cache_hit(cache_type)
            logger.info(f"Cache hit recorded", cache_type=cache_type)
        else:
            collector.record_cache_miss(cache_type)
            logger.info(f"Cache miss recorded", cache_type=cache_type)
    
    # Display sample metrics
    print("\nSample Prometheus Metrics Output:")
    print("=" * 50)
    metrics_text = collector.get_metrics()
    lines = metrics_text.split('\n')
    
    # Show key metrics
    key_metrics = [
        'http_requests_total',
        'http_request_duration_seconds',
        'db_query_duration_seconds',
        'agent_tasks_total',
        'opportunities_created_total',
        'validations_submitted_total'
    ]
    
    for line in lines:
        if any(metric in line for metric in key_metrics) and not line.startswith('#'):
            print(line)
    
    print("✅ Metrics collection completed")


async def demo_health_monitoring():
    """Demonstrate health monitoring system."""
    print("\n=== Health Monitoring Demo ===")
    
    monitor = get_health_monitor()
    
    # Register demo health checks
    def healthy_service():
        return HealthCheck(
            name="api_service",
            status=HealthStatus.HEALTHY,
            message="API service is running normally",
            details={"uptime_seconds": 3600, "memory_usage_mb": 256}
        )
    
    def degraded_service():
        return HealthCheck(
            name="cache_service",
            status=HealthStatus.DEGRADED,
            message="Cache service is slow but functional",
            details={"response_time_ms": 1500, "threshold_ms": 1000, "hit_rate": 0.75}
        )
    
    async def async_service():
        await asyncio.sleep(0.05)  # Simulate async health check
        return HealthCheck(
            name="ai_service",
            status=HealthStatus.HEALTHY,
            message="AI service is operational",
            details={"model_loaded": True, "queue_size": 3}
        )
    
    def intermittent_service():
        # Randomly succeed or fail
        if random.random() > 0.3:
            return HealthCheck(
                name="external_api",
                status=HealthStatus.HEALTHY,
                message="External API is accessible"
            )
        else:
            raise Exception("External API timeout")
    
    # Register health checks
    monitor.register_check("api_service", healthy_service)
    monitor.register_check("cache_service", degraded_service)
    monitor.register_check("ai_service", async_service)
    monitor.register_check("external_api", intermittent_service)
    
    print("Running individual health checks:")
    for service_name in ["api_service", "cache_service", "ai_service", "external_api"]:
        result = await monitor.run_check(service_name)
        status_icon = "✅" if result.status == HealthStatus.HEALTHY else "⚠️" if result.status == HealthStatus.DEGRADED else "❌"
        print(f"  {status_icon} {service_name}: {result.status.value} - {result.message}")
        if result.duration_ms:
            print(f"    Duration: {result.duration_ms:.2f}ms")
        if result.details:
            print(f"    Details: {result.details}")
    
    print("\nRunning all health checks concurrently:")
    all_results = await monitor.run_all_checks()
    overall_status = monitor.get_overall_status(all_results)
    
    print(f"Overall System Status: {overall_status.value.upper()}")
    
    print("✅ Health monitoring completed")


async def demo_request_lifecycle():
    """Demonstrate complete request lifecycle with full observability."""
    print("\n=== Complete Request Lifecycle Demo ===")
    
    request_id = generate_correlation_id()
    correlation_id = generate_correlation_id()
    user_id = "user_lifecycle_demo"
    
    collector = get_metrics_collector()
    
    with RequestContext(request_id, correlation_id, user_id):
        start_time = time.time()
        
        logger.info("Incoming HTTP request",
                   method="GET",
                   path="/api/v1/opportunities",
                   client_ip="192.168.1.100",
                   user_agent="Mozilla/5.0 (Demo Browser)")
        
        try:
            # Authentication phase
            logger.info("Authentication phase started")
            await asyncio.sleep(0.02)
            logger.info("Authentication successful")
            
            # Authorization phase
            logger.info("Authorization check started")
            await asyncio.sleep(0.01)
            logger.info("Authorization granted", permissions=["read:opportunities"])
            
            # Business logic phase
            logger.info("Business logic execution started")
            await asyncio.sleep(0.15)
            
            # Database queries
            logger.info("Database queries started")
            await asyncio.sleep(0.08)
            logger.info("Database queries completed", queries_executed=3)
            
            # AI processing
            logger.info("AI processing started")
            await asyncio.sleep(0.3)
            logger.info("AI processing completed", opportunities_analyzed=25)
            
            # Response preparation
            logger.info("Response preparation started")
            await asyncio.sleep(0.02)
            
            duration = time.time() - start_time
            
            # Record successful request metrics
            collector.record_http_request("GET", "/api/v1/opportunities", 200, duration)
            
            logger.info("Request completed successfully",
                       status_code=200,
                       duration_ms=round(duration * 1000, 2),
                       response_size_bytes=15420,
                       opportunities_returned=25)
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record error metrics
            collector.record_http_request("GET", "/api/v1/opportunities", 500, duration)
            
            logger.error("Request failed",
                        error_type=type(e).__name__,
                        error_message=str(e),
                        duration_ms=round(duration * 1000, 2),
                        exc_info=True)
    
    print("✅ Request lifecycle completed")


async def main():
    """Run all demonstrations."""
    print("🚀 AI Opportunity Browser - Working Logging & Monitoring Demo")
    print("=" * 70)
    print("This demo shows the currently implemented and working features:")
    print("- Structured JSON logging with contextual information")
    print("- Correlation ID tracking across operations")
    print("- Prometheus metrics collection")
    print("- Health monitoring system")
    print("- Request lifecycle observability")
    print("=" * 70)
    
    try:
        await demo_structured_logging()
        await demo_correlation_tracking()
        await demo_correlation_decorator()
        await demo_metrics_collection()
        await demo_health_monitoring()
        await demo_request_lifecycle()
        
        print("\n" + "=" * 70)
        print("✅ ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
        print("\n🎯 Key Features Demonstrated:")
        print("  ✅ Structured JSON logging with correlation IDs")
        print("  ✅ Context-aware logging across async operations")
        print("  ✅ Comprehensive Prometheus metrics collection")
        print("  ✅ Health monitoring with async checks")
        print("  ✅ Request lifecycle tracking")
        print("  ✅ Error handling and logging")
        print("  ✅ Business metrics recording")
        print("\n📊 Metrics Available:")
        print("  - HTTP request rates and latencies")
        print("  - Database operation metrics")
        print("  - AI agent task metrics")
        print("  - Business event counters")
        print("  - Cache performance metrics")
        print("  - Health check results")
        print("\n🔍 Observability Features:")
        print("  - Correlation ID propagation")
        print("  - Structured log fields")
        print("  - Performance timing")
        print("  - Error tracking")
        print("  - Service health monitoring")
        
        print(f"\n📈 Note: Distributed tracing is configured but requires OpenTelemetry")
        print("         exporters to be installed for full functionality.")
        print("=" * 70)
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"\n❌ Demo failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)