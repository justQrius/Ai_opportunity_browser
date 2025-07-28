"""
Logging configuration for the AI Opportunity Browser API.

This module sets up structured logging with proper formatting,
correlation IDs, and distributed tracing integration.
"""

import json
import logging
import sys
import time
from contextvars import ContextVar
from typing import Dict, Any, Optional
from uuid import uuid4

import structlog
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from api.core.config import get_settings

settings = get_settings()

# Context variables for correlation tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class CorrelationIDProcessor:
    """Structlog processor to add correlation IDs to log records."""
    
    def __call__(self, logger, method_name, event_dict):
        """Add correlation context to log events."""
        # Add correlation ID
        correlation_id = correlation_id_var.get()
        if correlation_id:
            event_dict['correlation_id'] = correlation_id
        
        # Add request ID
        request_id = request_id_var.get()
        if request_id:
            event_dict['request_id'] = request_id
        
        # Add user ID
        user_id = user_id_var.get()
        if user_id:
            event_dict['user_id'] = user_id
        
        # Add trace context from OpenTelemetry
        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            event_dict['trace_id'] = format(span_context.trace_id, '032x')
            event_dict['span_id'] = format(span_context.span_id, '016x')
        
        return event_dict


class TimestampProcessor:
    """Add ISO timestamp to log records."""
    
    def __call__(self, logger, method_name, event_dict):
        """Add timestamp to log events."""
        event_dict['timestamp'] = time.time()
        event_dict['iso_timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%S.%fZ', time.gmtime())
        return event_dict


class ServiceInfoProcessor:
    """Add service information to log records."""
    
    def __call__(self, logger, method_name, event_dict):
        """Add service context to log events."""
        event_dict['service'] = 'ai-opportunity-browser'
        event_dict['version'] = getattr(settings, 'VERSION', '1.0.0')
        event_dict['environment'] = getattr(settings, 'ENVIRONMENT', 'development')
        return event_dict


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging with JSON output."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            'timestamp': time.time(),
            'iso_timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.%fZ', time.gmtime()),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'service': 'ai-opportunity-browser',
            'version': getattr(settings, 'VERSION', '1.0.0'),
            'environment': getattr(settings, 'ENVIRONMENT', 'development'),
        }
        
        # Add correlation context
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data['correlation_id'] = correlation_id
        
        request_id = request_id_var.get()
        if request_id:
            log_data['request_id'] = request_id
        
        user_id = user_id_var.get()
        if user_id:
            log_data['user_id'] = user_id
        
        # Add trace context
        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            log_data['trace_id'] = format(span_context.trace_id, '032x')
            log_data['span_id'] = format(span_context.span_id, '016x')
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


def setup_logging() -> None:
    """Configure application logging with structured logging and correlation IDs."""
    
    # Set log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            ServiceInfoProcessor(),
            CorrelationIDProcessor(),
            TimestampProcessor(),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.JSONRenderer() if getattr(settings, 'ENABLE_STRUCTURED_LOGGING', True) 
            else structlog.dev.ConsoleRenderer(colors=True)
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    formatter = StructuredFormatter() if getattr(settings, 'ENABLE_STRUCTURED_LOGGING', True) else logging.Formatter(
        fmt=settings.LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    configure_logger("uvicorn", log_level)
    configure_logger("uvicorn.access", log_level)
    configure_logger("fastapi", log_level)
    configure_logger("sqlalchemy.engine", logging.WARNING)  # Reduce SQL noise
    configure_logger("opentelemetry", logging.WARNING)  # Reduce OpenTelemetry noise
    
    # Configure application loggers
    configure_logger("api", log_level)
    configure_logger("agents", log_level)
    configure_logger("shared", log_level)
    configure_logger("data-ingestion", log_level)


def configure_logger(name: str, level: int) -> None:
    """Configure a specific logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with proper configuration."""
    return logging.getLogger(name)