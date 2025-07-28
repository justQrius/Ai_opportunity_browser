# Logging and Monitoring Configuration

This document describes the configuration options for the comprehensive logging, tracing, and monitoring system in the AI Opportunity Browser.

## Environment Variables

### Logging Configuration

```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Service identification
SERVICE_NAME=ai-opportunity-browser
SERVICE_VERSION=1.0.0

# Console output (true/false)
LOG_CONSOLE=true

# Optional log file path
LOG_FILE_PATH=/var/log/ai-opportunity-browser/app.log
```

### Distributed Tracing Configuration

```bash
# Enable/disable tracing
ENABLE_TRACING=true

# Jaeger configuration
JAEGER_ENDPOINT=localhost:14268
JAEGER_AGENT_HOST=localhost
JAEGER_AGENT_PORT=6831

# OTLP (OpenTelemetry Protocol) configuration
OTLP_ENDPOINT=http://localhost:4317

# Trace sampling rate (0.0 to 1.0)
TRACE_SAMPLE_RATE=1.0

# Trace propagation format (b3, jaeger, tracecontext)
TRACE_PROPAGATOR=b3
```

### Metrics Configuration

```bash
# Enable/disable metrics collection
ENABLE_METRICS=true

# Prometheus metrics endpoint port
METRICS_PORT=8000

# Metrics collection interval (seconds)
METRICS_INTERVAL=15

# Custom metrics labels
METRICS_ENVIRONMENT=production
METRICS_REGION=us-west-2
```

### Health Check Configuration

```bash
# Enable/disable health checks
ENABLE_HEALTH_CHECKS=true

# Health check interval (seconds)
HEALTH_CHECK_INTERVAL=30

# Health check timeout (seconds)
HEALTH_CHECK_TIMEOUT=10

# Critical services for readiness probe
CRITICAL_SERVICES=database,redis,vector_db
```

## Docker Compose Configuration

Add the following services to your `docker-compose.yml` for local development:

```yaml
version: '3.8'

services:
  # Jaeger for distributed tracing
  jaeger:
    image: jaegertracing/all-in-one:1.50
    ports:
      - "16686:16686"  # Jaeger UI
      - "14268:14268"  # Jaeger collector HTTP
      - "6831:6831/udp"  # Jaeger agent UDP
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    networks:
      - ai-opportunity-browser

  # Prometheus for metrics collection
  prometheus:
    image: prom/prometheus:v2.47.0
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    networks:
      - ai-opportunity-browser

  # Grafana for metrics visualization
  grafana:
    image: grafana/grafana:10.1.0
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    networks:
      - ai-opportunity-browser

volumes:
  grafana-storage:

networks:
  ai-opportunity-browser:
    driver: bridge
```

## Prometheus Configuration

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'ai-opportunity-browser'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

## Grafana Dashboard Configuration

Create `monitoring/grafana/datasources/prometheus.yml`:

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

Create `monitoring/grafana/dashboards/dashboard.yml`:

```yaml
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
```

## Application Integration

### FastAPI Middleware Setup

The logging and monitoring system is automatically integrated through middleware:

```python
from api.middleware.logging_middleware import LoggingMiddleware
from api.middleware.metrics import MetricsMiddleware
from shared.observability import setup_observability, ObservabilityConfig

# Setup observability
config = ObservabilityConfig(
    service_name="ai-opportunity-browser-api",
    service_version="1.0.0",
    enable_tracing=True,
    enable_metrics=True
)
setup_observability(config)

# Add middleware to FastAPI app
app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware)
```

### Manual Instrumentation

For custom operations, use the observability utilities:

```python
from shared.observability import trace_async_operation, record_metric
from shared.logging_config import get_logger, CorrelationContext

logger = get_logger(__name__)

async def process_opportunity(opportunity_data):
    async with trace_async_operation("process_opportunity", {"opportunity_id": opportunity_data.id}):
        logger.info("Processing opportunity", opportunity_id=opportunity_data.id)
        
        # Your business logic here
        result = await analyze_opportunity(opportunity_data)
        
        # Record business metrics
        record_metric("opportunity_processed", 1, {"type": "ai_automation"})
        
        logger.info("Opportunity processed successfully", 
                   opportunity_id=opportunity_data.id, 
                   score=result.score)
        
        return result
```

## Monitoring Endpoints

The application exposes several monitoring endpoints:

- `GET /metrics` - Prometheus metrics in text format
- `GET /health` - Basic health check for load balancers
- `GET /health/detailed` - Detailed health status with service checks
- `GET /health/live` - Kubernetes liveness probe
- `GET /health/ready` - Kubernetes readiness probe

## Key Metrics

### HTTP Metrics
- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - HTTP request duration histogram

### Database Metrics
- `db_connections_active` - Active database connections
- `db_query_duration_seconds` - Database query duration histogram

### Agent Metrics
- `agent_tasks_total` - Total agent tasks by type and status
- `agent_task_duration_seconds` - Agent task duration histogram

### Business Metrics
- `opportunities_created_total` - Total opportunities created
- `validations_submitted_total` - Total validations submitted by type
- `cache_hits_total` / `cache_misses_total` - Cache performance

### Custom Metrics
- `opportunities_processed_total` - Business-specific opportunity processing
- `validations_completed_total` - Business-specific validation completion
- `agent_operations_total` - Agent operation counts
- `data_ingestion_events_total` - Data ingestion event counts

## Log Structure

All logs are structured in JSON format with the following fields:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "message": "Request completed successfully",
  "service": "ai-opportunity-browser",
  "version": "1.0.0",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "request_id": "req_123456789",
  "user_id": "user_789",
  "trace_id": "1234567890abcdef1234567890abcdef",
  "span_id": "abcdef1234567890",
  "method": "GET",
  "path": "/api/v1/opportunities",
  "status_code": 200,
  "duration_ms": 245.67,
  "additional_context": "value"
}
```

## Troubleshooting

### Common Issues

1. **Tracing not working**
   - Check `ENABLE_TRACING=true`
   - Verify Jaeger/OTLP endpoint configuration
   - Check network connectivity to tracing backend

2. **Metrics not appearing**
   - Verify `/metrics` endpoint is accessible
   - Check Prometheus scrape configuration
   - Ensure `ENABLE_METRICS=true`

3. **Health checks failing**
   - Check database connectivity
   - Verify Redis connection
   - Check vector database configuration

4. **High log volume**
   - Adjust `LOG_LEVEL` to `WARNING` or `ERROR`
   - Configure log rotation
   - Use sampling for high-frequency operations

### Performance Considerations

- Tracing adds ~1-5ms overhead per operation
- Metrics collection is lightweight (~0.1ms per metric)
- Structured logging adds ~0.5ms per log entry
- Health checks run every 30 seconds by default

### Security Considerations

- Logs may contain sensitive data - configure log scrubbing
- Metrics endpoints should be protected in production
- Tracing data may contain business logic - secure tracing backend
- Health check endpoints may reveal system architecture

## Production Deployment

For production deployment:

1. Use external tracing backend (Jaeger, Zipkin, or cloud provider)
2. Configure log aggregation (ELK stack, Fluentd, or cloud logging)
3. Set up alerting based on metrics and health checks
4. Implement log rotation and retention policies
5. Secure monitoring endpoints with authentication
6. Configure appropriate sampling rates for tracing
7. Set up dashboards for key business and technical metrics