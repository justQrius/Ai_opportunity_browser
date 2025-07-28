"""
Structured logging configuration with correlation IDs and distributed tracing.

This module provides comprehensive logging setup with:
- Structured JSON logging using structlog
- Correlation ID tracking across requests
- OpenTelemetry distributed tracing integration
- Context-aware logging with trace information
"""

import os
import sys
import uuid
import logging
import structlog
from typing import Dict, Any, Optional
from contextvars import ContextVar
from datetime import datetime, timezone

# OpenTelemetry imports with graceful fallback
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.jaeger import JaegerExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.b3 import B3MultiFormat
    TRACING_AVAILABLE = True
except ImportError as e:
    # Create mock objects for when OpenTelemetry is not available
    class MockTrace:
        def get_current_span(self):
            return MockSpan()
        def get_tracer(self, name):
            return MockTracer()
    
    class MockSpan:
        def is_recording(self):
            return False
        def get_span_context(self):
            return MockSpanContext()
    
    class MockSpanContext:
        def __init__(self):
            self.trace_id = 0
            self.span_id = 0
    
    class MockTracer:
        def start_span(self, name):
            return MockSpan()
        def start_as_current_span(self, name):
            return MockSpanContextManager()
    
    class MockSpanContextManager:
        def __enter__(self):
            return MockSpan()
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
    
    trace = MockTrace()
    TRACING_AVAILABLE = False
    print(f"Warning: OpenTelemetry not available: {e}")
    print("Tracing functionality will be disabled.")


# Context variables for correlation tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class CorrelationIDProcessor:
    """Structlog processor to add correlation ID to log entries."""
    
    def __call__(self, logger, method_name, event_dict):
        """Add correlation context to log entries."""
        # Add correlation ID
        correlation_id = correlation_id_var.get()
        if correlation_id:
            event_dict['correlation_id'] = correlation_id
        
        # Add user ID if available
        user_id = user_id_var.get()
        if user_id:
            event_dict['user_id'] = user_id
        
        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            event_dict['request_id'] = request_id
        
        # Add trace information if available
        if TRACING_AVAILABLE:
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                span_context = current_span.get_span_context()
                event_dict['trace_id'] = format(span_context.trace_id, '032x')
                event_dict['span_id'] = format(span_context.span_id, '016x')
        
        return event_dict


class TimestampProcessor:
    """Structlog processor to add ISO timestamp."""
    
    def __call__(self, logger, method_name, event_dict):
        """Add ISO timestamp to log entries."""
        event_dict['timestamp'] = datetime.now(timezone.utc).isoformat()
        return event_dict


class ServiceInfoProcessor:
    """Structlog processor to add service information."""
    
    def __init__(self, service_name: str = "ai-opportunity-browser", version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version
    
    def __call__(self, logger, method_name, event_dict):
        """Add service information to log entries."""
        event_dict['service'] = self.service_name
        event_dict['version'] = self.version
        return event_dict


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return correlation_id_var.get()


def set_user_id(user_id: str) -> None:
    """Set the user ID for the current context."""
    user_id_var.set(user_id)


def get_user_id() -> Optional[str]:
    """Get the current user ID."""
    return user_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set the request ID for the current context."""
    request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """Get the current request ID."""
    return request_id_var.get()


def setup_tracing(
    service_name: str = "ai-opportunity-browser",
    jaeger_endpoint: Optional[str] = None,
    otlp_endpoint: Optional[str] = None,
    sample_rate: float = 1.0
) -> None:
    """
    Setup OpenTelemetry distributed tracing.
    
    Args:
        service_name: Name of the service
        jaeger_endpoint: Jaeger collector endpoint
        otlp_endpoint: OTLP collector endpoint
        sample_rate: Sampling rate (0.0 to 1.0)
    """
    if not TRACING_AVAILABLE:
        print("Warning: Tracing setup skipped - OpenTelemetry not available")
        return
    
    try:
        # Create tracer provider
        tracer_provider = TracerProvider(
            resource=trace.Resource.create({
                "service.name": service_name,
                "service.version": "1.0.0"
            })
        )
        
        # Set up exporters
        exporters = []
        
        # Jaeger exporter
        if jaeger_endpoint:
            jaeger_exporter = JaegerExporter(
                agent_host_name=jaeger_endpoint.split(':')[0] if ':' in jaeger_endpoint else jaeger_endpoint,
                agent_port=int(jaeger_endpoint.split(':')[1]) if ':' in jaeger_endpoint else 14268,
            )
            exporters.append(jaeger_exporter)
        
        # OTLP exporter
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            exporters.append(otlp_exporter)
        
        # Add span processors
        for exporter in exporters:
            span_processor = BatchSpanProcessor(exporter)
            tracer_provider.add_span_processor(span_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)
        
        # Set up propagators
        set_global_textmap(B3MultiFormat())
        
        # Auto-instrument libraries
        FastAPIInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()
        RedisInstrumentor().instrument()
        RequestsInstrumentor().instrument()
        AioHttpClientInstrumentor().instrument()
        
    except Exception as e:
        print(f"Warning: Tracing setup failed: {e}")
        print("Continuing without distributed tracing")


def setup_logging(
    log_level: str = "INFO",
    service_name: str = "ai-opportunity-browser",
    service_version: str = "1.0.0",
    enable_console_output: bool = True,
    log_file_path: Optional[str] = None
) -> None:
    """
    Setup structured logging with correlation IDs.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service_name: Name of the service
        service_version: Version of the service
        enable_console_output: Whether to output logs to console
        log_file_path: Optional file path for log output
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout if enable_console_output else None,
        level=getattr(logging, log_level.upper())
    )
    
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        CorrelationIDProcessor(),
        TimestampProcessor(),
        ServiceInfoProcessor(service_name, service_version),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    
    # Add JSON renderer for production or file output
    if not enable_console_output or log_file_path:
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Use colored console output for development
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Set up file logging if specified
    if log_file_path:
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(file_handler)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def configure_from_environment() -> None:
    """Configure logging and tracing from environment variables."""
    # Logging configuration
    log_level = os.getenv("LOG_LEVEL", "INFO")
    service_name = os.getenv("SERVICE_NAME", "ai-opportunity-browser")
    service_version = os.getenv("SERVICE_VERSION", "1.0.0")
    enable_console = os.getenv("LOG_CONSOLE", "true").lower() == "true"
    log_file = os.getenv("LOG_FILE_PATH")
    
    # Tracing configuration
    jaeger_endpoint = os.getenv("JAEGER_ENDPOINT")
    otlp_endpoint = os.getenv("OTLP_ENDPOINT")
    sample_rate = float(os.getenv("TRACE_SAMPLE_RATE", "1.0"))
    
    # Setup logging
    setup_logging(
        log_level=log_level,
        service_name=service_name,
        service_version=service_version,
        enable_console_output=enable_console,
        log_file_path=log_file
    )
    
    # Setup tracing
    setup_tracing(
        service_name=service_name,
        jaeger_endpoint=jaeger_endpoint,
        otlp_endpoint=otlp_endpoint,
        sample_rate=sample_rate
    )


# Context managers for correlation tracking
class CorrelationContext:
    """Context manager for correlation ID tracking."""
    
    def __init__(self, correlation_id: Optional[str] = None, user_id: Optional[str] = None):
        self.correlation_id = correlation_id or generate_correlation_id()
        self.user_id = user_id
        self.previous_correlation_id = None
        self.previous_user_id = None
    
    def __enter__(self):
        """Enter correlation context."""
        self.previous_correlation_id = correlation_id_var.get()
        self.previous_user_id = user_id_var.get()
        
        set_correlation_id(self.correlation_id)
        if self.user_id:
            set_user_id(self.user_id)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit correlation context."""
        if self.previous_correlation_id:
            set_correlation_id(self.previous_correlation_id)
        else:
            correlation_id_var.set(None)
        
        if self.previous_user_id:
            set_user_id(self.previous_user_id)
        else:
            user_id_var.set(None)


class RequestContext:
    """Context manager for request tracking."""
    
    def __init__(self, request_id: Optional[str] = None, correlation_id: Optional[str] = None, 
                 user_id: Optional[str] = None):
        self.request_id = request_id or generate_correlation_id()
        self.correlation_id = correlation_id or generate_correlation_id()
        self.user_id = user_id
        self.previous_request_id = None
        self.previous_correlation_id = None
        self.previous_user_id = None
    
    def __enter__(self):
        """Enter request context."""
        self.previous_request_id = request_id_var.get()
        self.previous_correlation_id = correlation_id_var.get()
        self.previous_user_id = user_id_var.get()
        
        set_request_id(self.request_id)
        set_correlation_id(self.correlation_id)
        if self.user_id:
            set_user_id(self.user_id)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit request context."""
        if self.previous_request_id:
            set_request_id(self.previous_request_id)
        else:
            request_id_var.set(None)
        
        if self.previous_correlation_id:
            set_correlation_id(self.previous_correlation_id)
        else:
            correlation_id_var.set(None)
        
        if self.previous_user_id:
            set_user_id(self.previous_user_id)
        else:
            user_id_var.set(None)


# Decorators for automatic correlation tracking
def with_correlation(correlation_id: Optional[str] = None, user_id: Optional[str] = None):
    """Decorator to automatically set correlation context for functions."""
    def decorator(func):
        if hasattr(func, '__call__'):
            async def async_wrapper(*args, **kwargs):
                with CorrelationContext(correlation_id, user_id):
                    return await func(*args, **kwargs)
            
            def sync_wrapper(*args, **kwargs):
                with CorrelationContext(correlation_id, user_id):
                    return func(*args, **kwargs)
            
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        return func
    return decorator


def with_tracing(operation_name: Optional[str] = None):
    """Decorator to automatically create spans for functions."""
    def decorator(func):
        if not TRACING_AVAILABLE:
            return func  # Return original function if tracing not available
        
        tracer = trace.get_tracer(__name__)
        span_name = operation_name or f"{func.__module__}.{func.__name__}"
        
        if hasattr(func, '__call__'):
            async def async_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name) as span:
                    try:
                        result = await func(*args, **kwargs)
                        if hasattr(span, 'set_status'):
                            span.set_status(trace.Status(trace.StatusCode.OK))
                        return result
                    except Exception as e:
                        if hasattr(span, 'record_exception'):
                            span.record_exception(e)
                        if hasattr(span, 'set_status'):
                            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                        raise
            
            def sync_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name) as span:
                    try:
                        result = func(*args, **kwargs)
                        if hasattr(span, 'set_status'):
                            span.set_status(trace.Status(trace.StatusCode.OK))
                        return result
                    except Exception as e:
                        if hasattr(span, 'record_exception'):
                            span.record_exception(e)
                        if hasattr(span, 'set_status'):
                            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                        raise
            
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        return func
    return decorator