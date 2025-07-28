"""
Security monitoring and alerting system for zero trust architecture.

This module provides comprehensive security monitoring, threat detection,
and automated alerting capabilities.
"""

import time
import asyncio
from typing import Dict, Any, List, Optional, Set, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import structlog

from shared.security.zero_trust import SecurityPrincipal, TrustLevel
from shared.monitoring import get_metrics_collector

logger = structlog.get_logger(__name__)


class SecurityEventType(Enum):
    """Types of security events."""
    AUTHENTICATION_SUCCESS = "auth_success"
    AUTHENTICATION_FAILURE = "auth_failure"
    AUTHORIZATION_DENIED = "authz_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    BLOCKED_REQUEST = "blocked_request"
    TOKEN_EXPIRED = "token_expired"
    INVALID_TOKEN = "invalid_token"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_ACCESS_VIOLATION = "data_access_violation"
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"


class SecuritySeverity(Enum):
    """Security event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Represents a security event."""
    event_type: SecurityEventType
    severity: SecuritySeverity
    principal_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource: Optional[str]
    action: Optional[str]
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None


@dataclass
class SecurityAlert:
    """Represents a security alert."""
    alert_id: str
    title: str
    description: str
    severity: SecuritySeverity
    events: List[SecurityEvent]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class ThreatDetector:
    """Detects security threats based on event patterns."""
    
    def __init__(self):
        """Initialize threat detector."""
        self.event_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.failed_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self.suspicious_ips: Set[str] = set()
        self.blocked_ips: Set[str] = set()
        
        # Threat detection thresholds
        self.brute_force_threshold = 5  # Failed attempts
        self.brute_force_window = 300  # 5 minutes
        self.rate_limit_threshold = 100  # Requests per minute
        self.anomaly_threshold = 0.8  # Anomaly score threshold
    
    def analyze_event(self, event: SecurityEvent) -> List[SecurityAlert]:
        """
        Analyze a security event for threats.
        
        Args:
            event: Security event to analyze
            
        Returns:
            List of security alerts generated
        """
        alerts = []
        
        # Store event in history
        key = f"{event.principal_id}:{event.ip_address}"
        self.event_history[key].append(event)
        
        # Detect brute force attacks
        if event.event_type == SecurityEventType.AUTHENTICATION_FAILURE:
            brute_force_alert = self._detect_brute_force(event)
            if brute_force_alert:
                alerts.append(brute_force_alert)
        
        # Detect privilege escalation attempts
        if event.event_type == SecurityEventType.AUTHORIZATION_DENIED:
            privilege_alert = self._detect_privilege_escalation(event)
            if privilege_alert:
                alerts.append(privilege_alert)
        
        # Detect anomalous behavior
        anomaly_alert = self._detect_anomalous_behavior(event)
        if anomaly_alert:
            alerts.append(anomaly_alert)
        
        # Detect suspicious IP patterns
        ip_alert = self._detect_suspicious_ip_activity(event)
        if ip_alert:
            alerts.append(ip_alert)
        
        return alerts
    
    def _detect_brute_force(self, event: SecurityEvent) -> Optional[SecurityAlert]:
        """Detect brute force attacks."""
        if not event.ip_address:
            return None
        
        # Track failed attempts by IP
        now = datetime.now(timezone.utc)
        self.failed_attempts[event.ip_address].append(now)
        
        # Clean old attempts
        cutoff = now - timedelta(seconds=self.brute_force_window)
        self.failed_attempts[event.ip_address] = [
            attempt for attempt in self.failed_attempts[event.ip_address]
            if attempt > cutoff
        ]
        
        # Check threshold
        recent_failures = len(self.failed_attempts[event.ip_address])
        
        if recent_failures >= self.brute_force_threshold:
            # Add to suspicious IPs
            self.suspicious_ips.add(event.ip_address)
            
            return SecurityAlert(
                alert_id=f"brute_force_{event.ip_address}_{int(now.timestamp())}",
                title="Brute Force Attack Detected",
                description=f"Multiple failed authentication attempts from IP {event.ip_address}",
                severity=SecuritySeverity.HIGH,
                events=[event],
                metadata={
                    "ip_address": event.ip_address,
                    "failed_attempts": recent_failures,
                    "time_window": self.brute_force_window
                }
            )
        
        return None
    
    def _detect_privilege_escalation(self, event: SecurityEvent) -> Optional[SecurityAlert]:
        """Detect privilege escalation attempts."""
        if not event.principal_id:
            return None
        
        # Look for patterns of authorization denials
        key = f"{event.principal_id}:{event.ip_address}"
        recent_events = list(self.event_history[key])
        
        # Count recent authorization denials
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=10)
        
        recent_denials = [
            e for e in recent_events
            if (e.event_type == SecurityEventType.AUTHORIZATION_DENIED and
                e.timestamp > cutoff)
        ]
        
        if len(recent_denials) >= 3:
            return SecurityAlert(
                alert_id=f"privilege_escalation_{event.principal_id}_{int(now.timestamp())}",
                title="Privilege Escalation Attempt",
                description=f"Multiple authorization denials for user {event.principal_id}",
                severity=SecuritySeverity.MEDIUM,
                events=recent_denials,
                metadata={
                    "principal_id": event.principal_id,
                    "denial_count": len(recent_denials),
                    "resources_attempted": list(set(e.resource for e in recent_denials if e.resource))
                }
            )
        
        return None
    
    def _detect_anomalous_behavior(self, event: SecurityEvent) -> Optional[SecurityAlert]:
        """Detect anomalous behavior patterns."""
        if not event.principal_id:
            return None
        
        # Simple anomaly detection based on request patterns
        key = f"{event.principal_id}:{event.ip_address}"
        recent_events = list(self.event_history[key])
        
        if len(recent_events) < 10:
            return None  # Need more data
        
        # Check for unusual request patterns
        now = datetime.now(timezone.utc)
        last_hour = now - timedelta(hours=1)
        
        recent_hour_events = [
            e for e in recent_events
            if e.timestamp > last_hour
        ]
        
        # Check for high request rate
        if len(recent_hour_events) > 200:  # More than 200 requests per hour
            return SecurityAlert(
                alert_id=f"anomaly_{event.principal_id}_{int(now.timestamp())}",
                title="Anomalous Behavior Detected",
                description=f"Unusually high activity from user {event.principal_id}",
                severity=SecuritySeverity.MEDIUM,
                events=[event],
                metadata={
                    "principal_id": event.principal_id,
                    "request_count": len(recent_hour_events),
                    "time_window": "1 hour"
                }
            )
        
        return None
    
    def _detect_suspicious_ip_activity(self, event: SecurityEvent) -> Optional[SecurityAlert]:
        """Detect suspicious IP activity."""
        if not event.ip_address:
            return None
        
        # Check if IP is already flagged as suspicious
        if event.ip_address in self.suspicious_ips:
            # Count recent events from this IP
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=30)
            
            ip_events = []
            for events in self.event_history.values():
                ip_events.extend([
                    e for e in events
                    if e.ip_address == event.ip_address and e.timestamp > cutoff
                ])
            
            if len(ip_events) > 50:  # High activity from suspicious IP
                return SecurityAlert(
                    alert_id=f"suspicious_ip_{event.ip_address}_{int(now.timestamp())}",
                    title="Suspicious IP Activity",
                    description=f"High activity from suspicious IP {event.ip_address}",
                    severity=SecuritySeverity.HIGH,
                    events=[event],
                    metadata={
                        "ip_address": event.ip_address,
                        "event_count": len(ip_events),
                        "time_window": "30 minutes"
                    }
                )
        
        return None


class SecurityMonitor:
    """Main security monitoring system."""
    
    def __init__(self):
        """Initialize security monitor."""
        self.threat_detector = ThreatDetector()
        self.alert_handlers: List[Callable[[SecurityAlert], None]] = []
        self.metrics_collector = get_metrics_collector()
        
        # Alert storage (in production, use persistent storage)
        self.alerts: Dict[str, SecurityAlert] = {}
        self.event_log: List[SecurityEvent] = []
    
    def add_alert_handler(self, handler: Callable[[SecurityAlert], None]):
        """Add an alert handler function."""
        self.alert_handlers.append(handler)
    
    def log_security_event(self, event: SecurityEvent):
        """
        Log a security event and analyze for threats.
        
        Args:
            event: Security event to log
        """
        # Store event
        self.event_log.append(event)
        
        # Log to structured logger
        logger.info(
            "Security event",
            event_type=event.event_type.value,
            severity=event.severity.value,
            principal_id=event.principal_id,
            ip_address=event.ip_address,
            resource=event.resource,
            action=event.action,
            message=event.message,
            correlation_id=event.correlation_id,
            **event.metadata
        )
        
        # Update metrics
        self._update_security_metrics(event)
        
        # Analyze for threats
        alerts = self.threat_detector.analyze_event(event)
        
        # Process any generated alerts
        for alert in alerts:
            self._handle_alert(alert)
    
    def _update_security_metrics(self, event: SecurityEvent):
        """Update security metrics."""
        # Record security event metrics
        if hasattr(self.metrics_collector, 'security_events_total'):
            self.metrics_collector.security_events_total.labels(
                event_type=event.event_type.value,
                severity=event.severity.value
            ).inc()
        
        # Record specific event types
        if event.event_type == SecurityEventType.AUTHENTICATION_FAILURE:
            if hasattr(self.metrics_collector, 'auth_failures_total'):
                self.metrics_collector.auth_failures_total.inc()
        
        elif event.event_type == SecurityEventType.AUTHORIZATION_DENIED:
            if hasattr(self.metrics_collector, 'authz_denials_total'):
                self.metrics_collector.authz_denials_total.inc()
    
    def _handle_alert(self, alert: SecurityAlert):
        """Handle a security alert."""
        # Store alert
        self.alerts[alert.alert_id] = alert
        
        # Log alert
        logger.warning(
            "Security alert generated",
            alert_id=alert.alert_id,
            title=alert.title,
            severity=alert.severity.value,
            event_count=len(alert.events),
            **alert.metadata
        )
        
        # Call alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}", exc_info=True)
    
    def get_recent_events(
        self,
        hours: int = 24,
        event_types: Optional[List[SecurityEventType]] = None,
        severity: Optional[SecuritySeverity] = None
    ) -> List[SecurityEvent]:
        """Get recent security events."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        events = [
            event for event in self.event_log
            if event.timestamp > cutoff
        ]
        
        if event_types:
            events = [e for e in events if e.event_type in event_types]
        
        if severity:
            events = [e for e in events if e.severity == severity]
        
        return sorted(events, key=lambda e: e.timestamp, reverse=True)
    
    def get_active_alerts(self) -> List[SecurityAlert]:
        """Get active (unresolved) security alerts."""
        return [
            alert for alert in self.alerts.values()
            if not alert.resolved
        ]
    
    def acknowledge_alert(self, alert_id: str):
        """Acknowledge a security alert."""
        if alert_id in self.alerts:
            self.alerts[alert_id].acknowledged = True
            logger.info(f"Security alert acknowledged: {alert_id}")
    
    def resolve_alert(self, alert_id: str):
        """Resolve a security alert."""
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
            logger.info(f"Security alert resolved: {alert_id}")
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security monitoring summary."""
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        
        recent_events = [
            event for event in self.event_log
            if event.timestamp > last_24h
        ]
        
        # Count events by type
        event_counts = defaultdict(int)
        for event in recent_events:
            event_counts[event.event_type.value] += 1
        
        # Count events by severity
        severity_counts = defaultdict(int)
        for event in recent_events:
            severity_counts[event.severity.value] += 1
        
        # Active alerts
        active_alerts = self.get_active_alerts()
        
        return {
            "timestamp": now.isoformat(),
            "events_24h": len(recent_events),
            "events_by_type": dict(event_counts),
            "events_by_severity": dict(severity_counts),
            "active_alerts": len(active_alerts),
            "critical_alerts": len([a for a in active_alerts if a.severity == SecuritySeverity.CRITICAL]),
            "high_alerts": len([a for a in active_alerts if a.severity == SecuritySeverity.HIGH]),
            "suspicious_ips": len(self.threat_detector.suspicious_ips),
            "blocked_ips": len(self.threat_detector.blocked_ips)
        }


# Global security monitor instance
_security_monitor: Optional[SecurityMonitor] = None


def get_security_monitor() -> SecurityMonitor:
    """Get the global security monitor instance."""
    global _security_monitor
    if _security_monitor is None:
        _security_monitor = SecurityMonitor()
    return _security_monitor


def setup_security_monitoring() -> SecurityMonitor:
    """Setup security monitoring system."""
    global _security_monitor
    _security_monitor = SecurityMonitor()
    
    # Add default alert handlers
    def log_alert_handler(alert: SecurityAlert):
        """Default alert handler that logs to structured logger."""
        logger.warning(
            "SECURITY ALERT",
            alert_id=alert.alert_id,
            title=alert.title,
            description=alert.description,
            severity=alert.severity.value,
            event_count=len(alert.events)
        )
    
    _security_monitor.add_alert_handler(log_alert_handler)
    
    logger.info("Security monitoring system initialized")
    return _security_monitor


# Convenience functions for logging security events
def log_authentication_success(principal_id: str, ip_address: str, **metadata):
    """Log successful authentication."""
    monitor = get_security_monitor()
    event = SecurityEvent(
        event_type=SecurityEventType.AUTHENTICATION_SUCCESS,
        severity=SecuritySeverity.LOW,
        principal_id=principal_id,
        ip_address=ip_address,
        message=f"Authentication successful for {principal_id}",
        metadata=metadata
    )
    monitor.log_security_event(event)


def log_authentication_failure(ip_address: str, reason: str, **metadata):
    """Log failed authentication."""
    monitor = get_security_monitor()
    event = SecurityEvent(
        event_type=SecurityEventType.AUTHENTICATION_FAILURE,
        severity=SecuritySeverity.MEDIUM,
        ip_address=ip_address,
        message=f"Authentication failed: {reason}",
        metadata=metadata
    )
    monitor.log_security_event(event)


def log_authorization_denied(principal_id: str, resource: str, action: str, **metadata):
    """Log authorization denial."""
    monitor = get_security_monitor()
    event = SecurityEvent(
        event_type=SecurityEventType.AUTHORIZATION_DENIED,
        severity=SecuritySeverity.MEDIUM,
        principal_id=principal_id,
        resource=resource,
        action=action,
        message=f"Authorization denied for {principal_id} on {resource}:{action}",
        metadata=metadata
    )
    monitor.log_security_event(event)


def log_suspicious_activity(principal_id: str, activity: str, severity: SecuritySeverity = SecuritySeverity.MEDIUM, **metadata):
    """Log suspicious activity."""
    monitor = get_security_monitor()
    event = SecurityEvent(
        event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
        severity=severity,
        principal_id=principal_id,
        message=f"Suspicious activity: {activity}",
        metadata=metadata
    )
    monitor.log_security_event(event)