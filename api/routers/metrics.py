"""
Metrics and monitoring API endpoints.

This module provides endpoints for:
- Prometheus metrics exposure
- Health checks and system status
- Alert management and configuration
- Real-time metrics streaming
- Custom dashboard data
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
import json
import asyncio
import structlog

from shared.monitoring import get_health_monitor, get_metrics_collector
from shared.custom_metrics import get_business_metrics_collector, get_metric_aggregator, get_metrics_streamer
from shared.alerting import get_alert_manager, Alert, AlertRule, NotificationConfig, AlertSeverity, NotificationChannel
from shared.auth import get_current_user
from shared.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/prometheus", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """
    Get Prometheus metrics in text format.
    
    This endpoint exposes all application metrics in Prometheus format
    for scraping by Prometheus server.
    """
    try:
        # Get metrics from both collectors
        base_metrics = get_metrics_collector().get_metrics()
        business_metrics = get_business_metrics_collector().registry
        
        # Combine metrics (simplified - in production you'd properly merge registries)
        from prometheus_client import generate_latest
        business_metrics_text = generate_latest(business_metrics).decode('utf-8')
        
        combined_metrics = base_metrics + "\n" + business_metrics_text
        
        return PlainTextResponse(
            content=combined_metrics,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
        
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate metrics")


@router.get("/health")
async def get_health_status():
    """
    Get comprehensive health status of all system components.
    
    Returns:
        Dict containing overall health status and individual component checks
    """
    try:
        health_monitor = get_health_monitor()
        health_results = await health_monitor.run_all_checks()
        overall_status = health_monitor.get_overall_status(health_results)
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                name: {
                    "status": check.status.value,
                    "message": check.message,
                    "duration_ms": check.duration_ms,
                    "timestamp": check.timestamp.isoformat(),
                    "details": check.details
                }
                for name, check in health_results.items()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health status")


@router.get("/health/{component}")
async def get_component_health(component: str):
    """
    Get health status for a specific component.
    
    Args:
        component: Name of the component to check
        
    Returns:
        Health status for the specified component
    """
    try:
        health_monitor = get_health_monitor()
        health_result = await health_monitor.run_check(component)
        
        return {
            "component": component,
            "status": health_result.status.value,
            "message": health_result.message,
            "duration_ms": health_result.duration_ms,
            "timestamp": health_result.timestamp.isoformat(),
            "details": health_result.details
        }
        
    except Exception as e:
        logger.error(f"Error getting health status for {component}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get health status for {component}")


@router.get("/dashboard")
async def get_dashboard_metrics(
    time_window: int = Query(3600, description="Time window in seconds"),
    current_user: User = Depends(get_current_user)
):
    """
    Get aggregated metrics for dashboard display.
    
    Args:
        time_window: Time window in seconds for metric aggregation
        current_user: Current authenticated user
        
    Returns:
        Dashboard metrics data
    """
    try:
        aggregator = get_metric_aggregator()
        window = timedelta(seconds=time_window)
        
        # Get key metrics for dashboard
        dashboard_data = {
            "overview": {
                "api_requests_per_minute": aggregator.get_aggregated_metric(
                    "api_requests", "avg", window
                ) or 0,
                "error_rate": aggregator.get_aggregated_metric(
                    "error_rate", "avg", window
                ) or 0,
                "response_time_p95": aggregator.get_aggregated_metric(
                    "response_time_p95", "avg", window
                ) or 0,
                "active_users": aggregator.get_aggregated_metric(
                    "active_users", "max", window
                ) or 0
            },
            "business": {
                "opportunities_created_today": aggregator.get_aggregated_metric(
                    "opportunities_created", "sum", timedelta(days=1)
                ) or 0,
                "validations_completed_today": aggregator.get_aggregated_metric(
                    "validations_completed", "sum", timedelta(days=1)
                ) or 0,
                "user_engagement_rate": aggregator.get_aggregated_metric(
                    "user_engagement", "avg", window
                ) or 0
            },
            "agents": {
                "agent_queue_size": aggregator.get_aggregated_metric(
                    "agent_queue_size", "avg", window
                ) or 0,
                "agent_success_rate": aggregator.get_aggregated_metric(
                    "agent_success_rate", "avg", window
                ) or 0,
                "agent_processing_time": aggregator.get_aggregated_metric(
                    "agent_processing_time", "avg", window
                ) or 0
            },
            "system": {
                "memory_usage": aggregator.get_aggregated_metric(
                    "memory_usage", "avg", window
                ) or 0,
                "cpu_usage": aggregator.get_aggregated_metric(
                    "cpu_usage", "avg", window
                ) or 0,
                "db_connections": aggregator.get_aggregated_metric(
                    "db_connections", "avg", window
                ) or 0
            }
        }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard metrics")


@router.get("/trends/{metric_name}")
async def get_metric_trend(
    metric_name: str,
    time_window: int = Query(3600, description="Time window in seconds"),
    current_user: User = Depends(get_current_user)
):
    """
    Get trend analysis for a specific metric.
    
    Args:
        metric_name: Name of the metric to analyze
        time_window: Time window in seconds for trend analysis
        current_user: Current authenticated user
        
    Returns:
        Trend analysis data
    """
    try:
        aggregator = get_metric_aggregator()
        window = timedelta(seconds=time_window)
        
        trend_data = aggregator.get_metric_trend(metric_name, window)
        
        if not trend_data:
            raise HTTPException(status_code=404, detail=f"Metric '{metric_name}' not found or no data available")
        
        return {
            "metric_name": metric_name,
            "time_window_seconds": time_window,
            "trend": trend_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trend for metric {metric_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metric trend")


@router.websocket("/stream")
async def stream_metrics(websocket: WebSocket):
    """
    WebSocket endpoint for real-time metrics streaming.
    
    Streams metrics data in real-time for dashboard updates.
    """
    await websocket.accept()
    
    try:
        streamer = get_metrics_streamer()
        
        # Subscribe to all metrics
        async def send_metrics(metrics_data: Dict[str, Any]):
            try:
                await websocket.send_text(json.dumps({
                    "type": "metrics_update",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": metrics_data
                }))
            except Exception as e:
                logger.error(f"Error sending metrics via WebSocket: {e}")
        
        streamer.subscribe("*", send_metrics)
        
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client message or timeout
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Handle client requests
                try:
                    request = json.loads(message)
                    if request.get("type") == "subscribe":
                        pattern = request.get("pattern", "*")
                        streamer.subscribe(pattern, send_metrics)
                    elif request.get("type") == "unsubscribe":
                        pattern = request.get("pattern", "*")
                        streamer.unsubscribe(pattern, send_metrics)
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON message"
                    }))
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_text(json.dumps({
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }))
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from metrics stream")
    except Exception as e:
        logger.error(f"Error in metrics WebSocket: {e}")
        await websocket.close(code=1011, reason="Internal server error")
    finally:
        # Clean up subscription
        try:
            streamer.unsubscribe("*", send_metrics)
        except:
            pass


# Alert management endpoints
@router.get("/alerts")
async def get_active_alerts(current_user: User = Depends(get_current_user)):
    """
    Get all active alerts.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        List of active alerts
    """
    try:
        alert_manager = get_alert_manager()
        active_alerts = await alert_manager.get_active_alerts()
        
        return {
            "alerts": [
                {
                    "rule_name": alert.rule_name,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "message": alert.message,
                    "labels": alert.labels,
                    "annotations": alert.annotations,
                    "started_at": alert.started_at.isoformat(),
                    "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                    "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                    "fingerprint": alert.fingerprint,
                    "notification_count": alert.notification_count,
                    "escalated": alert.escalated
                }
                for alert in active_alerts
            ],
            "count": len(active_alerts)
        }
        
    except Exception as e:
        logger.error(f"Error getting active alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get active alerts")


@router.post("/alerts/{fingerprint}/acknowledge")
async def acknowledge_alert(
    fingerprint: str,
    current_user: User = Depends(get_current_user)
):
    """
    Acknowledge an alert.
    
    Args:
        fingerprint: Alert fingerprint
        current_user: Current authenticated user
        
    Returns:
        Acknowledgment status
    """
    try:
        alert_manager = get_alert_manager()
        success = await alert_manager.acknowledge_alert(fingerprint, current_user.email)
        
        if success:
            return {"message": "Alert acknowledged successfully", "fingerprint": fingerprint}
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert {fingerprint}: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.get("/alerts/history")
async def get_alert_history(
    hours: int = Query(24, description="Hours of history to retrieve"),
    current_user: User = Depends(get_current_user)
):
    """
    Get alert history.
    
    Args:
        hours: Number of hours of history to retrieve
        current_user: Current authenticated user
        
    Returns:
        Alert history data
    """
    try:
        alert_manager = get_alert_manager()
        history = await alert_manager.get_alert_history(hours)
        
        return {
            "history": history,
            "time_window_hours": hours
        }
        
    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alert history")


@router.get("/alerts/rules")
async def get_alert_rules(current_user: User = Depends(get_current_user)):
    """
    Get all configured alert rules.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        List of alert rules
    """
    try:
        alert_manager = get_alert_manager()
        
        return {
            "rules": [
                {
                    "name": rule.name,
                    "description": rule.description,
                    "severity": rule.severity.value,
                    "condition": rule.condition,
                    "duration": rule.duration.total_seconds(),
                    "labels": rule.labels,
                    "annotations": rule.annotations,
                    "enabled": rule.enabled,
                    "notification_channels": [channel.value for channel in rule.notification_channels]
                }
                for rule in alert_manager.rules.values()
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting alert rules: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alert rules")


@router.get("/system/status")
async def get_system_status():
    """
    Get overall system status summary.
    
    Returns:
        System status summary
    """
    try:
        # Get health status
        health_monitor = get_health_monitor()
        health_results = await health_monitor.run_all_checks()
        overall_health = health_monitor.get_overall_status(health_results)
        
        # Get active alerts
        alert_manager = get_alert_manager()
        active_alerts = await alert_manager.get_active_alerts()
        
        # Count alerts by severity
        alert_counts = {
            "critical": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
            "high": len([a for a in active_alerts if a.severity == AlertSeverity.HIGH]),
            "medium": len([a for a in active_alerts if a.severity == AlertSeverity.MEDIUM]),
            "low": len([a for a in active_alerts if a.severity == AlertSeverity.LOW]),
            "info": len([a for a in active_alerts if a.severity == AlertSeverity.INFO])
        }
        
        # Get key metrics
        aggregator = get_metric_aggregator()
        window = timedelta(minutes=5)
        
        return {
            "overall_status": overall_health.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health": {
                "status": overall_health.value,
                "healthy_components": len([c for c in health_results.values() if c.status.value == "healthy"]),
                "total_components": len(health_results)
            },
            "alerts": {
                "total_active": len(active_alerts),
                "by_severity": alert_counts
            },
            "performance": {
                "response_time_avg": aggregator.get_aggregated_metric("response_time_avg", "avg", window) or 0,
                "error_rate": aggregator.get_aggregated_metric("error_rate", "avg", window) or 0,
                "throughput": aggregator.get_aggregated_metric("throughput", "avg", window) or 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")