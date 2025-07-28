"""
Comprehensive alerting system for the AI Opportunity Browser.

This module provides:
- Alert rule definitions and evaluation
- Multi-channel notification system (email, Slack, webhook)
- Alert aggregation and deduplication
- Escalation policies and alert routing
- Integration with monitoring metrics
"""

import asyncio
import json
import smtplib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiohttp
import structlog

from shared.monitoring import get_metrics_collector, HealthStatus
from shared.cache import cache_manager

logger = structlog.get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(Enum):
    """Alert status."""
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"


class NotificationChannel(Enum):
    """Notification channel types."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PAGERDUTY = "pagerduty"


@dataclass
class AlertRule:
    """Alert rule definition."""
    name: str
    description: str
    severity: AlertSeverity
    condition: str  # Metric condition (e.g., "http_errors_rate > 0.05")
    duration: timedelta  # How long condition must be true
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    
    # Evaluation settings
    evaluation_interval: timedelta = field(default_factory=lambda: timedelta(minutes=1))
    
    # Notification settings
    notification_channels: List[NotificationChannel] = field(default_factory=list)
    escalation_delay: Optional[timedelta] = None
    
    # Suppression settings
    suppress_during_maintenance: bool = True
    suppress_on_weekends: bool = False


@dataclass
class Alert:
    """Active alert instance."""
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    # Timestamps
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    last_notification_at: Optional[datetime] = None
    
    # Metadata
    fingerprint: str = ""
    notification_count: int = 0
    escalated: bool = False
    
    def __post_init__(self):
        """Generate fingerprint for deduplication."""
        if not self.fingerprint:
            fingerprint_data = f"{self.rule_name}:{self.labels}"
            self.fingerprint = str(hash(fingerprint_data))


@dataclass
class NotificationConfig:
    """Notification configuration."""
    channel: NotificationChannel
    config: Dict[str, Any]
    enabled: bool = True
    
    # Rate limiting
    rate_limit_window: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    max_notifications_per_window: int = 3
    
    # Retry settings
    max_retries: int = 3
    retry_delay: timedelta = field(default_factory=lambda: timedelta(minutes=1))


class MetricEvaluator:
    """Evaluates metric conditions for alerting."""
    
    def __init__(self):
        self.metrics_collector = get_metrics_collector()
    
    async def evaluate_condition(self, condition: str, labels: Dict[str, str] = None) -> bool:
        """
        Evaluate a metric condition.
        
        Args:
            condition: Condition string (e.g., "http_errors_rate > 0.05")
            labels: Optional label filters
            
        Returns:
            True if condition is met
        """
        try:
            # Parse condition
            parts = condition.split()
            if len(parts) != 3:
                logger.error(f"Invalid condition format: {condition}")
                return False
            
            metric_name, operator, threshold_str = parts
            threshold = float(threshold_str)
            
            # Get metric value
            metric_value = await self._get_metric_value(metric_name, labels)
            
            # Evaluate condition
            if operator == ">":
                return metric_value > threshold
            elif operator == ">=":
                return metric_value >= threshold
            elif operator == "<":
                return metric_value < threshold
            elif operator == "<=":
                return metric_value <= threshold
            elif operator == "==":
                return metric_value == threshold
            elif operator == "!=":
                return metric_value != threshold
            else:
                logger.error(f"Unsupported operator: {operator}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return False
    
    async def _get_metric_value(self, metric_name: str, labels: Dict[str, str] = None) -> float:
        """Get current value of a metric."""
        # This is a simplified implementation
        # In a real system, you'd query Prometheus or your metrics backend
        
        if metric_name == "http_errors_rate":
            # Calculate error rate from Prometheus metrics
            return await self._calculate_error_rate()
        elif metric_name == "response_time_p95":
            return await self._get_response_time_percentile(95)
        elif metric_name == "db_connections_active":
            return await self._get_db_connections()
        elif metric_name == "agent_failure_rate":
            return await self._calculate_agent_failure_rate()
        elif metric_name == "queue_size":
            return await self._get_queue_size()
        elif metric_name == "memory_usage_percent":
            return await self._get_memory_usage()
        elif metric_name == "cpu_usage_percent":
            return await self._get_cpu_usage()
        else:
            logger.warning(f"Unknown metric: {metric_name}")
            return 0.0
    
    async def _calculate_error_rate(self) -> float:
        """Calculate HTTP error rate."""
        # Mock implementation - would query actual metrics
        return 0.02  # 2% error rate
    
    async def _get_response_time_percentile(self, percentile: int) -> float:
        """Get response time percentile."""
        # Mock implementation
        return 0.5  # 500ms
    
    async def _get_db_connections(self) -> float:
        """Get active database connections."""
        # Mock implementation
        return 10.0
    
    async def _calculate_agent_failure_rate(self) -> float:
        """Calculate agent failure rate."""
        # Mock implementation
        return 0.01  # 1% failure rate
    
    async def _get_queue_size(self) -> float:
        """Get current queue size."""
        # Mock implementation
        return 50.0
    
    async def _get_memory_usage(self) -> float:
        """Get memory usage percentage."""
        # Mock implementation
        return 75.0  # 75%
    
    async def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage."""
        # Mock implementation
        return 60.0  # 60%


class NotificationManager:
    """Manages alert notifications across multiple channels."""
    
    def __init__(self):
        self.channels: Dict[NotificationChannel, NotificationConfig] = {}
        self.notification_history: Dict[str, List[datetime]] = {}
    
    def configure_channel(self, config: NotificationConfig):
        """Configure a notification channel."""
        self.channels[config.channel] = config
        logger.info(f"Configured notification channel: {config.channel.value}")
    
    async def send_notification(self, alert: Alert, channels: List[NotificationChannel] = None):
        """Send alert notification to specified channels."""
        if not channels:
            channels = list(self.channels.keys())
        
        for channel in channels:
            if channel not in self.channels:
                logger.warning(f"Channel {channel.value} not configured")
                continue
            
            config = self.channels[channel]
            if not config.enabled:
                continue
            
            # Check rate limiting
            if not await self._check_rate_limit(alert.fingerprint, channel, config):
                logger.info(f"Rate limit exceeded for alert {alert.fingerprint} on {channel.value}")
                continue
            
            # Send notification
            try:
                await self._send_to_channel(alert, channel, config)
                alert.notification_count += 1
                alert.last_notification_at = datetime.now(timezone.utc)
                
                # Record notification
                await self._record_notification(alert.fingerprint, channel)
                
                logger.info(
                    f"Sent notification for alert {alert.rule_name}",
                    channel=channel.value,
                    severity=alert.severity.value
                )
                
            except Exception as e:
                logger.error(
                    f"Failed to send notification to {channel.value}",
                    error=str(e),
                    alert=alert.rule_name
                )
    
    async def _check_rate_limit(self, fingerprint: str, channel: NotificationChannel, 
                               config: NotificationConfig) -> bool:
        """Check if notification is within rate limits."""
        key = f"notification_rate_limit:{fingerprint}:{channel.value}"
        
        try:
            await cache_manager.initialize()
            redis_client = cache_manager.redis_client
            
            # Get recent notifications
            now = datetime.now(timezone.utc)
            window_start = now - config.rate_limit_window
            
            # Use Redis sorted set to track notifications
            await redis_client.zremrangebyscore(key, 0, window_start.timestamp())
            count = await redis_client.zcard(key)
            
            if count >= config.max_notifications_per_window:
                return False
            
            # Add current notification
            await redis_client.zadd(key, {str(now.timestamp()): now.timestamp()})
            await redis_client.expire(key, int(config.rate_limit_window.total_seconds()))
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow notification on error
    
    async def _send_to_channel(self, alert: Alert, channel: NotificationChannel, 
                              config: NotificationConfig):
        """Send notification to specific channel."""
        if channel == NotificationChannel.EMAIL:
            await self._send_email(alert, config.config)
        elif channel == NotificationChannel.SLACK:
            await self._send_slack(alert, config.config)
        elif channel == NotificationChannel.WEBHOOK:
            await self._send_webhook(alert, config.config)
        elif channel == NotificationChannel.SMS:
            await self._send_sms(alert, config.config)
        elif channel == NotificationChannel.PAGERDUTY:
            await self._send_pagerduty(alert, config.config)
        else:
            logger.warning(f"Unsupported notification channel: {channel.value}")
    
    async def _send_email(self, alert: Alert, config: Dict[str, Any]):
        """Send email notification."""
        try:
            smtp_server = config.get("smtp_server", "localhost")
            smtp_port = config.get("smtp_port", 587)
            username = config.get("username")
            password = config.get("password")
            from_email = config.get("from_email")
            to_emails = config.get("to_emails", [])
            
            if not to_emails:
                logger.warning("No email recipients configured")
                return
            
            # Create message
            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = ", ".join(to_emails)
            msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.rule_name}"
            
            # Email body
            body = f"""
Alert: {alert.rule_name}
Severity: {alert.severity.value}
Status: {alert.status.value}
Message: {alert.message}
Started: {alert.started_at.isoformat()}

Labels:
{json.dumps(alert.labels, indent=2)}

Annotations:
{json.dumps(alert.annotations, indent=2)}
"""
            
            msg.attach(MIMEText(body, "plain"))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if username and password:
                    server.starttls()
                    server.login(username, password)
                server.send_message(msg)
                
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            raise
    
    async def _send_slack(self, alert: Alert, config: Dict[str, Any]):
        """Send Slack notification."""
        try:
            webhook_url = config.get("webhook_url")
            channel = config.get("channel", "#alerts")
            username = config.get("username", "AlertBot")
            
            if not webhook_url:
                logger.warning("Slack webhook URL not configured")
                return
            
            # Color based on severity
            color_map = {
                AlertSeverity.CRITICAL: "danger",
                AlertSeverity.HIGH: "warning",
                AlertSeverity.MEDIUM: "warning",
                AlertSeverity.LOW: "good",
                AlertSeverity.INFO: "good"
            }
            
            # Create Slack message
            payload = {
                "channel": channel,
                "username": username,
                "attachments": [{
                    "color": color_map.get(alert.severity, "warning"),
                    "title": f"{alert.rule_name}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Severity", "value": alert.severity.value, "short": True},
                        {"title": "Status", "value": alert.status.value, "short": True},
                        {"title": "Started", "value": alert.started_at.isoformat(), "short": True}
                    ],
                    "footer": "AI Opportunity Browser",
                    "ts": int(alert.started_at.timestamp())
                }]
            }
            
            # Send to Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status != 200:
                        raise Exception(f"Slack API returned {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            raise
    
    async def _send_webhook(self, alert: Alert, config: Dict[str, Any]):
        """Send webhook notification."""
        try:
            url = config.get("url")
            headers = config.get("headers", {})
            
            if not url:
                logger.warning("Webhook URL not configured")
                return
            
            # Create webhook payload
            payload = {
                "alert": {
                    "rule_name": alert.rule_name,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "message": alert.message,
                    "labels": alert.labels,
                    "annotations": alert.annotations,
                    "started_at": alert.started_at.isoformat(),
                    "fingerprint": alert.fingerprint
                }
            }
            
            # Send webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status not in [200, 201, 202]:
                        raise Exception(f"Webhook returned {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            raise
    
    async def _send_sms(self, alert: Alert, config: Dict[str, Any]):
        """Send SMS notification (placeholder)."""
        # This would integrate with SMS providers like Twilio
        logger.info("SMS notification would be sent here")
    
    async def _send_pagerduty(self, alert: Alert, config: Dict[str, Any]):
        """Send PagerDuty notification (placeholder)."""
        # This would integrate with PagerDuty API
        logger.info("PagerDuty notification would be sent here")
    
    async def _record_notification(self, fingerprint: str, channel: NotificationChannel):
        """Record notification in history."""
        key = f"notification_history:{fingerprint}:{channel.value}"
        
        try:
            await cache_manager.initialize()
            redis_client = cache_manager.redis_client
            now = datetime.now(timezone.utc)
            
            # Add to history
            await redis_client.lpush(key, now.isoformat())
            await redis_client.ltrim(key, 0, 99)  # Keep last 100 notifications
            await redis_client.expire(key, 86400 * 7)  # Expire after 7 days
            
        except Exception as e:
            logger.error(f"Error recording notification: {e}")


class AlertManager:
    """Main alert management system."""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.evaluator = MetricEvaluator()
        self.notification_manager = NotificationManager()
        self.running = False
        self.evaluation_task: Optional[asyncio.Task] = None
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove an alert rule."""
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info(f"Removed alert rule: {rule_name}")
    
    def configure_notifications(self, config: NotificationConfig):
        """Configure notification channel."""
        self.notification_manager.configure_channel(config)
    
    async def start(self):
        """Start the alert manager."""
        if self.running:
            return
        
        self.running = True
        self.evaluation_task = asyncio.create_task(self._evaluation_loop())
        logger.info("Alert manager started")
    
    async def stop(self):
        """Stop the alert manager."""
        self.running = False
        
        if self.evaluation_task:
            self.evaluation_task.cancel()
            try:
                await self.evaluation_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Alert manager stopped")
    
    async def _evaluation_loop(self):
        """Main evaluation loop."""
        while self.running:
            try:
                await self._evaluate_rules()
                await asyncio.sleep(30)  # Evaluate every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in evaluation loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _evaluate_rules(self):
        """Evaluate all alert rules."""
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            try:
                await self._evaluate_rule(rule)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule_name}: {e}")
    
    async def _evaluate_rule(self, rule: AlertRule):
        """Evaluate a single alert rule."""
        # Check if condition is met
        condition_met = await self.evaluator.evaluate_condition(rule.condition, rule.labels)
        
        alert_key = f"{rule.name}:{rule.labels}"
        existing_alert = self.active_alerts.get(alert_key)
        
        if condition_met:
            if existing_alert:
                # Alert already exists, check if it should be escalated
                if (not existing_alert.escalated and 
                    rule.escalation_delay and 
                    datetime.now(timezone.utc) - existing_alert.started_at > rule.escalation_delay):
                    
                    existing_alert.escalated = True
                    await self._escalate_alert(existing_alert, rule)
            else:
                # Create new alert
                alert = Alert(
                    rule_name=rule.name,
                    severity=rule.severity,
                    status=AlertStatus.FIRING,
                    message=rule.description,
                    labels=rule.labels.copy(),
                    annotations=rule.annotations.copy()
                )
                
                self.active_alerts[alert_key] = alert
                
                # Send notification
                await self.notification_manager.send_notification(
                    alert, 
                    rule.notification_channels
                )
                
                logger.warning(
                    f"Alert fired: {rule.name}",
                    severity=rule.severity.value,
                    condition=rule.condition
                )
        else:
            # Condition not met, resolve alert if it exists
            if existing_alert and existing_alert.status == AlertStatus.FIRING:
                existing_alert.status = AlertStatus.RESOLVED
                existing_alert.resolved_at = datetime.now(timezone.utc)
                
                # Send resolution notification
                await self.notification_manager.send_notification(
                    existing_alert,
                    rule.notification_channels
                )
                
                # Remove from active alerts
                del self.active_alerts[alert_key]
                
                logger.info(f"Alert resolved: {rule.name}")
    
    async def _escalate_alert(self, alert: Alert, rule: AlertRule):
        """Escalate an alert."""
        alert.severity = AlertSeverity.CRITICAL  # Escalate to critical
        
        # Send escalation notification
        await self.notification_manager.send_notification(alert, rule.notification_channels)
        
        logger.error(f"Alert escalated: {rule.name}")
    
    async def acknowledge_alert(self, fingerprint: str, user: str = "system"):
        """Acknowledge an alert."""
        for alert in self.active_alerts.values():
            if alert.fingerprint == fingerprint:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now(timezone.utc)
                
                logger.info(f"Alert acknowledged: {alert.rule_name}", user=user)
                return True
        
        return False
    
    async def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())
    
    async def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history."""
        # This would query from persistent storage
        # For now, return empty list
        return []


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def setup_default_alert_rules():
    """Setup default alert rules for the AI Opportunity Browser."""
    alert_manager = get_alert_manager()
    
    # High error rate alert
    alert_manager.add_rule(AlertRule(
        name="high_error_rate",
        description="HTTP error rate is above 5%",
        severity=AlertSeverity.HIGH,
        condition="http_errors_rate > 0.05",
        duration=timedelta(minutes=5),
        notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
        labels={"service": "api"},
        annotations={"runbook": "https://docs.example.com/runbooks/high-error-rate"}
    ))
    
    # High response time alert
    alert_manager.add_rule(AlertRule(
        name="high_response_time",
        description="95th percentile response time is above 2 seconds",
        severity=AlertSeverity.MEDIUM,
        condition="response_time_p95 > 2.0",
        duration=timedelta(minutes=10),
        notification_channels=[NotificationChannel.SLACK],
        labels={"service": "api"}
    ))
    
    # Database connection alert
    alert_manager.add_rule(AlertRule(
        name="high_db_connections",
        description="Database connections are above 80% of limit",
        severity=AlertSeverity.MEDIUM,
        condition="db_connections_active > 80",
        duration=timedelta(minutes=5),
        notification_channels=[NotificationChannel.EMAIL],
        labels={"service": "database"}
    ))
    
    # Agent failure rate alert
    alert_manager.add_rule(AlertRule(
        name="agent_failure_rate",
        description="Agent failure rate is above 10%",
        severity=AlertSeverity.HIGH,
        condition="agent_failure_rate > 0.10",
        duration=timedelta(minutes=15),
        notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
        labels={"service": "agents"}
    ))
    
    # Queue size alert
    alert_manager.add_rule(AlertRule(
        name="large_queue_size",
        description="Task queue size is above 1000",
        severity=AlertSeverity.MEDIUM,
        condition="queue_size > 1000",
        duration=timedelta(minutes=10),
        notification_channels=[NotificationChannel.SLACK],
        labels={"service": "queue"}
    ))
    
    # Memory usage alert
    alert_manager.add_rule(AlertRule(
        name="high_memory_usage",
        description="Memory usage is above 90%",
        severity=AlertSeverity.HIGH,
        condition="memory_usage_percent > 90",
        duration=timedelta(minutes=5),
        notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
        labels={"service": "system"}
    ))
    
    # CPU usage alert
    alert_manager.add_rule(AlertRule(
        name="high_cpu_usage",
        description="CPU usage is above 85%",
        severity=AlertSeverity.MEDIUM,
        condition="cpu_usage_percent > 85",
        duration=timedelta(minutes=10),
        notification_channels=[NotificationChannel.SLACK],
        labels={"service": "system"}
    ))


async def setup_alerting_system():
    """Setup the complete alerting system."""
    alert_manager = get_alert_manager()
    
    # Setup default rules
    setup_default_alert_rules()
    
    # Configure notification channels (example configurations)
    # Email configuration
    alert_manager.configure_notifications(NotificationConfig(
        channel=NotificationChannel.EMAIL,
        config={
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "alerts@example.com",
            "password": "app_password",
            "from_email": "alerts@example.com",
            "to_emails": ["admin@example.com", "ops@example.com"]
        }
    ))
    
    # Slack configuration
    alert_manager.configure_notifications(NotificationConfig(
        channel=NotificationChannel.SLACK,
        config={
            "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
            "channel": "#alerts",
            "username": "AlertBot"
        }
    ))
    
    # Webhook configuration
    alert_manager.configure_notifications(NotificationConfig(
        channel=NotificationChannel.WEBHOOK,
        config={
            "url": "https://your-webhook-endpoint.com/alerts",
            "headers": {
                "Authorization": "Bearer your-token",
                "Content-Type": "application/json"
            }
        }
    ))
    
    # Start the alert manager
    await alert_manager.start()
    
    logger.info("Alerting system setup completed")