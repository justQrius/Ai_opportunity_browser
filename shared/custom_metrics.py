"""
Custom metrics collection for business and application-specific metrics.

This module extends the base monitoring system with:
- Business-specific metrics (opportunities, validations, user engagement)
- Application performance metrics (agent performance, data ingestion rates)
- Custom dashboards and metric aggregations
- Real-time metric streaming and alerts
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import json
import structlog

from prometheus_client import Counter, Histogram, Gauge, Summary, Info, CollectorRegistry
from shared.monitoring import get_metrics_collector
from shared.cache import cache_manager

logger = structlog.get_logger(__name__)


class MetricType(Enum):
    """Types of custom metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    INFO = "info"


@dataclass
class MetricDefinition:
    """Definition of a custom metric."""
    name: str
    description: str
    metric_type: MetricType
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None  # For histograms
    objectives: Optional[Dict[float, float]] = None  # For summaries


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: Union[int, float]
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BusinessMetricsCollector:
    """Collector for business-specific metrics."""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self._setup_business_metrics()
        self._setup_performance_metrics()
        self._setup_user_metrics()
        self._setup_agent_metrics()
        self._setup_data_metrics()
    
    def _setup_business_metrics(self):
        """Setup business-related metrics."""
        # Opportunity metrics
        self.opportunities_created = Counter(
            'opportunities_created_total',
            'Total opportunities created',
            ['source', 'category', 'ai_type'],
            registry=self.registry
        )
        
        self.opportunities_validated = Counter(
            'opportunities_validated_total',
            'Total opportunities validated',
            ['validation_type', 'result'],
            registry=self.registry
        )
        
        self.opportunity_score_distribution = Histogram(
            'opportunity_score_distribution',
            'Distribution of opportunity scores',
            ['category'],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        # Validation metrics
        self.validations_submitted = Counter(
            'validations_submitted_total',
            'Total validations submitted',
            ['validator_type', 'expertise_area'],
            registry=self.registry
        )
        
        self.validation_consensus_score = Histogram(
            'validation_consensus_score',
            'Consensus scores for validations',
            ['opportunity_category'],
            buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            registry=self.registry
        )
        
        # Market signal metrics
        self.market_signals_processed = Counter(
            'market_signals_processed_total',
            'Total market signals processed',
            ['source', 'signal_type', 'relevance'],
            registry=self.registry
        )
        
        self.signal_quality_score = Histogram(
            'signal_quality_score',
            'Quality scores of market signals',
            ['source'],
            buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            registry=self.registry
        )
    
    def _setup_performance_metrics(self):
        """Setup performance-related metrics."""
        # API performance
        self.api_request_duration = Histogram(
            'api_request_duration_seconds',
            'API request duration',
            ['method', 'endpoint', 'status_class'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        self.api_concurrent_requests = Gauge(
            'api_concurrent_requests',
            'Number of concurrent API requests',
            registry=self.registry
        )
        
        # Database performance
        self.db_query_duration = Histogram(
            'db_query_duration_seconds',
            'Database query duration',
            ['operation', 'table'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
            registry=self.registry
        )
        
        self.db_connection_pool_size = Gauge(
            'db_connection_pool_size',
            'Database connection pool size',
            ['pool_type'],
            registry=self.registry
        )
        
        # Cache performance
        self.cache_operations = Counter(
            'cache_operations_total',
            'Total cache operations',
            ['operation', 'result'],
            registry=self.registry
        )
        
        self.cache_hit_ratio = Gauge(
            'cache_hit_ratio',
            'Cache hit ratio',
            ['cache_type'],
            registry=self.registry
        )
    
    def _setup_user_metrics(self):
        """Setup user engagement metrics."""
        # User activity
        self.user_sessions = Counter(
            'user_sessions_total',
            'Total user sessions',
            ['user_type'],
            registry=self.registry
        )
        
        self.user_actions = Counter(
            'user_actions_total',
            'Total user actions',
            ['action_type', 'user_type'],
            registry=self.registry
        )
        
        self.session_duration = Histogram(
            'session_duration_seconds',
            'User session duration',
            ['user_type'],
            buckets=[60, 300, 900, 1800, 3600, 7200, 14400],
            registry=self.registry
        )
        
        # User engagement
        self.opportunities_viewed = Counter(
            'opportunities_viewed_total',
            'Total opportunities viewed',
            ['user_type', 'category'],
            registry=self.registry
        )
        
        self.user_bookmarks = Counter(
            'user_bookmarks_total',
            'Total bookmarks created',
            ['user_type'],
            registry=self.registry
        )
        
        self.user_searches = Counter(
            'user_searches_total',
            'Total searches performed',
            ['search_type', 'user_type'],
            registry=self.registry
        )
    
    def _setup_agent_metrics(self):
        """Setup AI agent metrics."""
        # Agent performance
        self.agent_task_duration = Histogram(
            'agent_task_duration_seconds',
            'Agent task processing duration',
            ['agent_type', 'task_type'],
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800],
            registry=self.registry
        )
        
        self.agent_task_success_rate = Gauge(
            'agent_task_success_rate',
            'Agent task success rate',
            ['agent_type'],
            registry=self.registry
        )
        
        self.agent_queue_size = Gauge(
            'agent_queue_size',
            'Agent task queue size',
            ['agent_type'],
            registry=self.registry
        )
        
        # Agent resource usage
        self.agent_memory_usage = Gauge(
            'agent_memory_usage_bytes',
            'Agent memory usage',
            ['agent_type'],
            registry=self.registry
        )
        
        self.agent_cpu_usage = Gauge(
            'agent_cpu_usage_percent',
            'Agent CPU usage percentage',
            ['agent_type'],
            registry=self.registry
        )
        
        # AI model metrics
        self.ai_model_requests = Counter(
            'ai_model_requests_total',
            'Total AI model requests',
            ['provider', 'model', 'operation'],
            registry=self.registry
        )
        
        self.ai_model_latency = Histogram(
            'ai_model_latency_seconds',
            'AI model request latency',
            ['provider', 'model'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        self.ai_model_tokens = Histogram(
            'ai_model_tokens',
            'AI model token usage',
            ['provider', 'model', 'token_type'],
            buckets=[10, 50, 100, 500, 1000, 2000, 5000, 10000],
            registry=self.registry
        )
    
    def _setup_data_metrics(self):
        """Setup data ingestion and processing metrics."""
        # Data ingestion
        self.data_ingestion_rate = Counter(
            'data_ingestion_rate_total',
            'Data ingestion rate',
            ['source', 'data_type'],
            registry=self.registry
        )
        
        self.data_processing_duration = Histogram(
            'data_processing_duration_seconds',
            'Data processing duration',
            ['stage', 'data_type'],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        self.data_quality_score = Histogram(
            'data_quality_score',
            'Data quality scores',
            ['source', 'data_type'],
            buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            registry=self.registry
        )
        
        # Vector database metrics
        self.vector_operations = Counter(
            'vector_operations_total',
            'Vector database operations',
            ['operation', 'result'],
            registry=self.registry
        )
        
        self.vector_search_latency = Histogram(
            'vector_search_latency_seconds',
            'Vector search latency',
            ['index_type'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
            registry=self.registry
        )
    
    # Business metric recording methods
    def record_opportunity_created(self, source: str, category: str, ai_type: str):
        """Record opportunity creation."""
        self.opportunities_created.labels(
            source=source,
            category=category,
            ai_type=ai_type
        ).inc()
    
    def record_opportunity_validated(self, validation_type: str, result: str):
        """Record opportunity validation."""
        self.opportunities_validated.labels(
            validation_type=validation_type,
            result=result
        ).inc()
    
    def record_opportunity_score(self, category: str, score: float):
        """Record opportunity score."""
        self.opportunity_score_distribution.labels(category=category).observe(score)
    
    def record_validation_submitted(self, validator_type: str, expertise_area: str):
        """Record validation submission."""
        self.validations_submitted.labels(
            validator_type=validator_type,
            expertise_area=expertise_area
        ).inc()
    
    def record_validation_consensus(self, opportunity_category: str, consensus_score: float):
        """Record validation consensus score."""
        self.validation_consensus_score.labels(
            opportunity_category=opportunity_category
        ).observe(consensus_score)
    
    def record_market_signal(self, source: str, signal_type: str, relevance: str):
        """Record market signal processing."""
        self.market_signals_processed.labels(
            source=source,
            signal_type=signal_type,
            relevance=relevance
        ).inc()
    
    def record_signal_quality(self, source: str, quality_score: float):
        """Record signal quality score."""
        self.signal_quality_score.labels(source=source).observe(quality_score)
    
    # Performance metric recording methods
    def record_api_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record API request metrics."""
        status_class = f"{status_code // 100}xx"
        self.api_request_duration.labels(
            method=method,
            endpoint=endpoint,
            status_class=status_class
        ).observe(duration)
    
    def set_concurrent_requests(self, count: int):
        """Set concurrent request count."""
        self.api_concurrent_requests.set(count)
    
    def record_db_query(self, operation: str, table: str, duration: float):
        """Record database query metrics."""
        self.db_query_duration.labels(
            operation=operation,
            table=table
        ).observe(duration)
    
    def set_db_pool_size(self, pool_type: str, size: int):
        """Set database pool size."""
        self.db_connection_pool_size.labels(pool_type=pool_type).set(size)
    
    def record_cache_operation(self, operation: str, result: str):
        """Record cache operation."""
        self.cache_operations.labels(
            operation=operation,
            result=result
        ).inc()
    
    def set_cache_hit_ratio(self, cache_type: str, ratio: float):
        """Set cache hit ratio."""
        self.cache_hit_ratio.labels(cache_type=cache_type).set(ratio)
    
    # User metric recording methods
    def record_user_session(self, user_type: str):
        """Record user session start."""
        self.user_sessions.labels(user_type=user_type).inc()
    
    def record_user_action(self, action_type: str, user_type: str):
        """Record user action."""
        self.user_actions.labels(
            action_type=action_type,
            user_type=user_type
        ).inc()
    
    def record_session_duration(self, user_type: str, duration: float):
        """Record session duration."""
        self.session_duration.labels(user_type=user_type).observe(duration)
    
    def record_opportunity_view(self, user_type: str, category: str):
        """Record opportunity view."""
        self.opportunities_viewed.labels(
            user_type=user_type,
            category=category
        ).inc()
    
    def record_user_bookmark(self, user_type: str):
        """Record user bookmark creation."""
        self.user_bookmarks.labels(user_type=user_type).inc()
    
    def record_user_search(self, search_type: str, user_type: str):
        """Record user search."""
        self.user_searches.labels(
            search_type=search_type,
            user_type=user_type
        ).inc()
    
    # Agent metric recording methods
    def record_agent_task(self, agent_type: str, task_type: str, duration: float):
        """Record agent task completion."""
        self.agent_task_duration.labels(
            agent_type=agent_type,
            task_type=task_type
        ).observe(duration)
    
    def set_agent_success_rate(self, agent_type: str, rate: float):
        """Set agent success rate."""
        self.agent_task_success_rate.labels(agent_type=agent_type).set(rate)
    
    def set_agent_queue_size(self, agent_type: str, size: int):
        """Set agent queue size."""
        self.agent_queue_size.labels(agent_type=agent_type).set(size)
    
    def set_agent_memory_usage(self, agent_type: str, bytes_used: int):
        """Set agent memory usage."""
        self.agent_memory_usage.labels(agent_type=agent_type).set(bytes_used)
    
    def set_agent_cpu_usage(self, agent_type: str, percent: float):
        """Set agent CPU usage."""
        self.agent_cpu_usage.labels(agent_type=agent_type).set(percent)
    
    def record_ai_model_request(self, provider: str, model: str, operation: str):
        """Record AI model request."""
        self.ai_model_requests.labels(
            provider=provider,
            model=model,
            operation=operation
        ).inc()
    
    def record_ai_model_latency(self, provider: str, model: str, latency: float):
        """Record AI model latency."""
        self.ai_model_latency.labels(
            provider=provider,
            model=model
        ).observe(latency)
    
    def record_ai_model_tokens(self, provider: str, model: str, token_type: str, count: int):
        """Record AI model token usage."""
        self.ai_model_tokens.labels(
            provider=provider,
            model=model,
            token_type=token_type
        ).observe(count)
    
    # Data metric recording methods
    def record_data_ingestion(self, source: str, data_type: str):
        """Record data ingestion."""
        self.data_ingestion_rate.labels(
            source=source,
            data_type=data_type
        ).inc()
    
    def record_data_processing(self, stage: str, data_type: str, duration: float):
        """Record data processing duration."""
        self.data_processing_duration.labels(
            stage=stage,
            data_type=data_type
        ).observe(duration)
    
    def record_data_quality(self, source: str, data_type: str, quality_score: float):
        """Record data quality score."""
        self.data_quality_score.labels(
            source=source,
            data_type=data_type
        ).observe(quality_score)
    
    def record_vector_operation(self, operation: str, result: str):
        """Record vector database operation."""
        self.vector_operations.labels(
            operation=operation,
            result=result
        ).inc()
    
    def record_vector_search_latency(self, index_type: str, latency: float):
        """Record vector search latency."""
        self.vector_search_latency.labels(index_type=index_type).observe(latency)


class MetricAggregator:
    """Aggregates and processes metrics for dashboards and alerts."""
    
    def __init__(self):
        self.time_series_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.aggregation_functions: Dict[str, Callable] = {
            'avg': lambda x: sum(x) / len(x) if x else 0,
            'sum': sum,
            'min': min,
            'max': max,
            'count': len,
            'p50': lambda x: sorted(x)[len(x)//2] if x else 0,
            'p95': lambda x: sorted(x)[int(len(x)*0.95)] if x else 0,
            'p99': lambda x: sorted(x)[int(len(x)*0.99)] if x else 0
        }
    
    def add_metric_point(self, metric_name: str, value: float, timestamp: datetime = None):
        """Add a metric point to the time series."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        self.time_series_data[metric_name].append({
            'value': value,
            'timestamp': timestamp
        })
    
    def get_aggregated_metric(self, metric_name: str, aggregation: str, 
                            time_window: timedelta = None) -> Optional[float]:
        """Get aggregated metric value."""
        if metric_name not in self.time_series_data:
            return None
        
        data = list(self.time_series_data[metric_name])
        
        # Filter by time window if specified
        if time_window:
            cutoff_time = datetime.now(timezone.utc) - time_window
            data = [point for point in data if point['timestamp'] >= cutoff_time]
        
        if not data:
            return None
        
        values = [point['value'] for point in data]
        
        if aggregation in self.aggregation_functions:
            return self.aggregation_functions[aggregation](values)
        else:
            logger.warning(f"Unknown aggregation function: {aggregation}")
            return None
    
    def get_metric_trend(self, metric_name: str, time_window: timedelta) -> Dict[str, Any]:
        """Get metric trend analysis."""
        if metric_name not in self.time_series_data:
            return {}
        
        cutoff_time = datetime.now(timezone.utc) - time_window
        data = [
            point for point in self.time_series_data[metric_name]
            if point['timestamp'] >= cutoff_time
        ]
        
        if len(data) < 2:
            return {}
        
        values = [point['value'] for point in data]
        
        # Calculate trend
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        trend_direction = "increasing" if second_avg > first_avg else "decreasing"
        trend_magnitude = abs(second_avg - first_avg) / first_avg if first_avg != 0 else 0
        
        return {
            'direction': trend_direction,
            'magnitude': trend_magnitude,
            'current_value': values[-1],
            'average_value': sum(values) / len(values),
            'min_value': min(values),
            'max_value': max(values),
            'data_points': len(values)
        }


class RealTimeMetricsStreamer:
    """Streams metrics in real-time for dashboards."""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.streaming = False
        self.stream_task: Optional[asyncio.Task] = None
    
    def subscribe(self, metric_pattern: str, callback: Callable):
        """Subscribe to metric updates."""
        self.subscribers[metric_pattern].append(callback)
    
    def unsubscribe(self, metric_pattern: str, callback: Callable):
        """Unsubscribe from metric updates."""
        if metric_pattern in self.subscribers:
            self.subscribers[metric_pattern].remove(callback)
    
    async def start_streaming(self):
        """Start real-time metric streaming."""
        if self.streaming:
            return
        
        self.streaming = True
        self.stream_task = asyncio.create_task(self._stream_loop())
        logger.info("Real-time metrics streaming started")
    
    async def stop_streaming(self):
        """Stop real-time metric streaming."""
        self.streaming = False
        
        if self.stream_task:
            self.stream_task.cancel()
            try:
                await self.stream_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Real-time metrics streaming stopped")
    
    async def _stream_loop(self):
        """Main streaming loop."""
        while self.streaming:
            try:
                # Get current metrics
                metrics_data = await self._collect_current_metrics()
                
                # Send to subscribers
                for pattern, callbacks in self.subscribers.items():
                    matching_metrics = self._filter_metrics(metrics_data, pattern)
                    
                    for callback in callbacks:
                        try:
                            await callback(matching_metrics)
                        except Exception as e:
                            logger.error(f"Error in metric callback: {e}")
                
                await asyncio.sleep(1)  # Stream every second
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in streaming loop: {e}")
                await asyncio.sleep(5)
    
    async def _collect_current_metrics(self) -> Dict[str, Any]:
        """Collect current metric values."""
        # This would collect from various sources
        # For now, return mock data
        return {
            'api_requests_per_second': 45.2,
            'response_time_avg': 0.234,
            'error_rate': 0.012,
            'active_users': 127,
            'opportunities_created_today': 23,
            'validations_pending': 8,
            'agent_queue_size': 156,
            'db_connections': 12,
            'memory_usage_percent': 67.8,
            'cpu_usage_percent': 43.2
        }
    
    def _filter_metrics(self, metrics: Dict[str, Any], pattern: str) -> Dict[str, Any]:
        """Filter metrics by pattern."""
        if pattern == "*":
            return metrics
        
        # Simple pattern matching
        filtered = {}
        for key, value in metrics.items():
            if pattern in key:
                filtered[key] = value
        
        return filtered


# Global instances
_business_metrics_collector: Optional[BusinessMetricsCollector] = None
_metric_aggregator: Optional[MetricAggregator] = None
_metrics_streamer: Optional[RealTimeMetricsStreamer] = None


def get_business_metrics_collector() -> BusinessMetricsCollector:
    """Get the global business metrics collector."""
    global _business_metrics_collector
    if _business_metrics_collector is None:
        _business_metrics_collector = BusinessMetricsCollector()
    return _business_metrics_collector


def get_metric_aggregator() -> MetricAggregator:
    """Get the global metric aggregator."""
    global _metric_aggregator
    if _metric_aggregator is None:
        _metric_aggregator = MetricAggregator()
    return _metric_aggregator


def get_metrics_streamer() -> RealTimeMetricsStreamer:
    """Get the global metrics streamer."""
    global _metrics_streamer
    if _metrics_streamer is None:
        _metrics_streamer = RealTimeMetricsStreamer()
    return _metrics_streamer


# Convenience functions
def record_business_metric(metric_name: str, *args, **kwargs):
    """Record a business metric."""
    collector = get_business_metrics_collector()
    
    # Map metric names to methods
    method_map = {
        'opportunity_created': collector.record_opportunity_created,
        'opportunity_validated': collector.record_opportunity_validated,
        'opportunity_score': collector.record_opportunity_score,
        'validation_submitted': collector.record_validation_submitted,
        'validation_consensus': collector.record_validation_consensus,
        'market_signal': collector.record_market_signal,
        'signal_quality': collector.record_signal_quality,
        'api_request': collector.record_api_request,
        'db_query': collector.record_db_query,
        'cache_operation': collector.record_cache_operation,
        'user_session': collector.record_user_session,
        'user_action': collector.record_user_action,
        'session_duration': collector.record_session_duration,
        'opportunity_view': collector.record_opportunity_view,
        'user_bookmark': collector.record_user_bookmark,
        'user_search': collector.record_user_search,
        'agent_task': collector.record_agent_task,
        'ai_model_request': collector.record_ai_model_request,
        'ai_model_latency': collector.record_ai_model_latency,
        'ai_model_tokens': collector.record_ai_model_tokens,
        'data_ingestion': collector.record_data_ingestion,
        'data_processing': collector.record_data_processing,
        'data_quality': collector.record_data_quality,
        'vector_operation': collector.record_vector_operation,
        'vector_search_latency': collector.record_vector_search_latency
    }
    
    if metric_name in method_map:
        method_map[metric_name](*args, **kwargs)
    else:
        logger.warning(f"Unknown business metric: {metric_name}")


async def setup_custom_metrics():
    """Setup custom metrics collection system."""
    # Initialize collectors
    business_collector = get_business_metrics_collector()
    aggregator = get_metric_aggregator()
    streamer = get_metrics_streamer()
    
    # Start real-time streaming
    await streamer.start_streaming()
    
    logger.info("Custom metrics system setup completed")