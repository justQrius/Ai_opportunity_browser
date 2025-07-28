"""
Distributed tracing configuration for the AI Opportunity Browser API.

This module sets up OpenTelemetry distributed tracing with proper
instrumentation for FastAPI, SQLAlchemy, Redis, and external HTTP calls.
"""

import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry import propagate

from api.core.config import get_settings

settings = get_settings()


def setup_tracing() -> None:
    """Configure OpenTelemetry distributed tracing."""
    
    # Skip tracing setup if disabled
    if not getattr(settings, 'ENABLE_TRACING', True):
        return
    
    # Create resource with service information
    resource = Resource.create({
        "service.name": "ai-opportunity-browser",
        "service.version": getattr(settings, 'VERSION', '1.0.0'),
        "service.environment": getattr(settings, 'ENVIRONMENT', 'development'),
        "service.instance.id": os.environ.get('HOSTNAME', 'localhost'),
    })
    
    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # Configure span processors and exporters
    _configure_exporters(tracer_provider)
    
    # Set up propagators for distributed tracing
    propagate.set_global_textmap(B3MultiFormat())
    
    # Instrument libraries
    _instrument_libraries()


def _configure_exporters(tracer_provider: TracerProvider) -> None:
    """Configure span exporters based on environment settings."""
    
    # Console exporter for development
    if settings.DEBUG or getattr(settings, 'ENABLE_CONSOLE_TRACING', False):
        console_exporter = ConsoleSpanExporter()
        console_processor = BatchSpanProcessor(console_exporter)
        tracer_provider.add_span_processor(console_processor)
    
    # Jaeger exporter
    jaeger_endpoint = getattr(settings, 'JAEGER_ENDPOINT', None)
    if jaeger_endpoint:
        jaeger_exporter = JaegerExporter(
            agent_host_name=getattr(settings, 'JAEGER_AGENT_HOST', 'localhost'),
            agent_port=getattr(settings, 'JAEGER_AGENT_PORT', 6831),
            collector_endpoint=jaeger_endpoint,
        )
        jaeger_processor = BatchSpanProcessor(jaeger_exporter)
        tracer_provider.add_span_processor(jaeger_processor)
    
    # OTLP exporter (for services like Honeycomb, Datadog, etc.)
    otlp_endpoint = getattr(settings, 'OTLP_ENDPOINT', None)
    if otlp_endpoint:
        otlp_headers = {}
        
        # Add authentication headers if provided
        otlp_api_key = getattr(settings, 'OTLP_API_KEY', None)
        if otlp_api_key:
            otlp_headers['x-honeycomb-team'] = otlp_api_key
        
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers=otlp_headers,
        )
        otlp_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(otlp_processor)


def _instrument_libraries() -> None:
    """Instrument common libraries for automatic tracing."""
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument()
    
    # Instrument SQLAlchemy
    SQLAlchemyInstrumentor.instrument()
    
    # Instrument Redis
    RedisInstrumentor.instrument()
    
    # Instrument HTTP clients
    RequestsInstrumentor.instrument()
    AioHttpClientInstrumentor.instrument()


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance for the given name."""
    return trace.get_tracer(name)


def create_span(
    name: str,
    tracer: Optional[trace.Tracer] = None,
    attributes: Optional[dict] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL
) -> trace.Span:
    """Create a new span with optional attributes."""
    if tracer is None:
        tracer = trace.get_tracer(__name__)
    
    span = tracer.start_span(name, kind=kind)
    
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)
    
    return span


def add_span_attributes(span: trace.Span, attributes: dict) -> None:
    """Add attributes to an existing span."""
    for key, value in attributes.items():
        span.set_attribute(key, value)


def record_exception(span: trace.Span, exception: Exception) -> None:
    """Record an exception in the current span."""
    span.record_exception(exception)
    span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))


class TracingContextManager:
    """Context manager for creating and managing spans."""
    
    def __init__(
        self,
        name: str,
        tracer: Optional[trace.Tracer] = None,
        attributes: Optional[dict] = None,
        kind: trace.SpanKind = trace.SpanKind.INTERNAL
    ):
        self.name = name
        self.tracer = tracer or trace.get_tracer(__name__)
        self.attributes = attributes or {}
        self.kind = kind
        self.span: Optional[trace.Span] = None
    
    def __enter__(self) -> trace.Span:
        """Start the span."""
        self.span = self.tracer.start_span(self.name, kind=self.kind)
        
        # Add attributes
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)
        
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End the span and record any exceptions."""
        if self.span:
            if exc_val:
                self.span.record_exception(exc_val)
                self.span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc_val)))
            else:
                self.span.set_status(trace.Status(trace.StatusCode.OK))
            
            self.span.end()


def trace_async_function(name: Optional[str] = None, attributes: Optional[dict] = None):
    """Decorator for tracing async functions."""
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            span_name = name or f"{func.__module__}.{func.__name__}"
            tracer = trace.get_tracer(func.__module__)
            
            with tracer.start_as_current_span(span_name) as span:
                # Add function attributes
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
        
        return wrapper
    return decorator


def trace_function(name: Optional[str] = None, attributes: Optional[dict] = None):
    """Decorator for tracing synchronous functions."""
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            span_name = name or f"{func.__module__}.{func.__name__}"
            tracer = trace.get_tracer(func.__module__)
            
            with tracer.start_as_current_span(span_name) as span:
                # Add function attributes
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                try:
                    result = func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
        
        return wrapper
    return decorator