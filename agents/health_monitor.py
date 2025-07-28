"""
Agent Health Monitoring System for the AI Opportunity Browser.
Provides comprehensive health checks, restart mechanisms, performance monitoring and alerting.

This module implements:
- Real-time health monitoring for all agents
- Automatic restart mechanisms for failed agents
- Performance metrics collection and analysis
- Alert generation and notification system
- Health dashboard data aggregation
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
import json
import statistics

from .base import BaseAgent, AgentState, AgentMetrics

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthMetric:
    """Individual health metric"""
    name: str
    value: float
    threshold_warning: float
    threshold_critical: float
    unit: str = ""
    description: str = ""
    
    def get_status(self) -> HealthStatus:
        """Determine health status based on thresholds"""
        if self.value >= self.threshold_critical:
            return HealthStatus.CRITICAL
        elif self.value >= self.threshold_warning:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY


@dataclass
class HealthAlert:
    """Health alert notification"""
    alert_id: str
    agent_id: str
    severity: AlertSeverity
    title: str
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    created_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "agent_id": self.agent_id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged": self.acknowledged
        }


@dataclass
class AgentHealthReport:
    """Comprehensive health report for an agent"""
    agent_id: str
    agent_name: str
    overall_status: HealthStatus
    metrics: List[HealthMetric]
    active_alerts: List[HealthAlert]
    last_check: datetime
    uptime: float
    performance_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "overall_status": self.overall_status.value,
            "metrics": [asdict(m) for m in self.metrics],
            "active_alerts": [alert.to_dict() for alert in self.active_alerts],
            "last_check": self.last_check.isoformat(),
            "uptime": self.uptime,
            "performance_score": self.performance_score
        }


class HealthMonitor:
    """
    Comprehensive health monitoring system for AI agents.
    Monitors performance, detects issues, and triggers recovery actions.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.agents: Dict[str, BaseAgent] = {}
        self.health_reports: Dict[str, AgentHealthReport] = {}
        self.active_alerts: Dict[str, HealthAlert] = {}
        self.alert_history: List[HealthAlert] = []
        
        # Monitoring configuration
        self.check_interval = self.config.get("check_interval", 30)  # seconds
        self.alert_cooldown = self.config.get("alert_cooldown", 300)  # 5 minutes
        self.auto_restart_enabled = self.config.get("auto_restart", True)
        self.max_restart_attempts = self.config.get("max_restart_attempts", 3)
        
        # Alert callbacks
        self.alert_callbacks: List[Callable[[HealthAlert], None]] = []
        
        # Control
        self._shutdown_event = asyncio.Event()
        self._monitor_task: Optional[asyncio.Task] = None
        self._restart_attempts: Dict[str, int] = {}
        self._last_alert_time: Dict[str, datetime] = {}
        
        logger.info("HealthMonitor initialized")
    
    async def start(self) -> None:
        """Start the health monitoring system"""
        logger.info("Starting HealthMonitor")
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("HealthMonitor started")
    
    async def stop(self) -> None:
        """Stop the health monitoring system"""
        logger.info("Stopping HealthMonitor")
        self._shutdown_event.set()
        
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("HealthMonitor stopped")
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent for monitoring"""
        self.agents[agent.agent_id] = agent
        self._restart_attempts[agent.agent_id] = 0
        logger.info(f"Registered agent {agent.agent_id} for health monitoring")
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from monitoring"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            if agent_id in self.health_reports:
                del self.health_reports[agent_id]
            if agent_id in self._restart_attempts:
                del self._restart_attempts[agent_id]
            logger.info(f"Unregistered agent {agent_id} from health monitoring")
    
    def add_alert_callback(self, callback: Callable[[HealthAlert], None]) -> None:
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        total_agents = len(self.agents)
        healthy_agents = len([r for r in self.health_reports.values() 
                            if r.overall_status == HealthStatus.HEALTHY])
        warning_agents = len([r for r in self.health_reports.values() 
                            if r.overall_status == HealthStatus.WARNING])
        critical_agents = len([r for r in self.health_reports.values() 
                             if r.overall_status == HealthStatus.CRITICAL])
        
        # Calculate overall system status
        if critical_agents > 0:
            system_status = HealthStatus.CRITICAL
        elif warning_agents > total_agents * 0.3:  # More than 30% in warning
            system_status = HealthStatus.WARNING
        else:
            system_status = HealthStatus.HEALTHY
        
        # Calculate average performance score
        performance_scores = [r.performance_score for r in self.health_reports.values()]
        avg_performance = statistics.mean(performance_scores) if performance_scores else 0.0
        
        return {
            "system_status": system_status.value,
            "total_agents": total_agents,
            "healthy_agents": healthy_agents,
            "warning_agents": warning_agents,
            "critical_agents": critical_agents,
            "active_alerts": len(self.active_alerts),
            "average_performance": avg_performance,
            "last_check": datetime.utcnow().isoformat()
        }
    
    async def get_agent_health(self, agent_id: str) -> Optional[AgentHealthReport]:
        """Get health report for specific agent"""
        return self.health_reports.get(agent_id)
    
    async def get_all_health_reports(self) -> List[AgentHealthReport]:
        """Get health reports for all agents"""
        return list(self.health_reports.values())
    
    async def get_active_alerts(self) -> List[HealthAlert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            logger.info(f"Alert {alert_id} acknowledged")
            return True
        return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved_at = datetime.utcnow()
            self.alert_history.append(alert)
            del self.active_alerts[alert_id]
            logger.info(f"Alert {alert_id} resolved")
            return True
        return False
    
    async def restart_agent(self, agent_id: str) -> bool:
        """Manually restart an agent"""
        if agent_id not in self.agents:
            logger.error(f"Agent {agent_id} not found for restart")
            return False
        
        try:
            agent = self.agents[agent_id]
            logger.info(f"Manually restarting agent {agent_id}")
            
            await agent.stop()
            await asyncio.sleep(2)  # Brief pause
            await agent.start()
            
            self._restart_attempts[agent_id] += 1
            logger.info(f"Agent {agent_id} restarted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restart agent {agent_id}: {e}")
            return False
    
    # Private methods
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        logger.debug("Health monitoring loop started")
        
        while not self._shutdown_event.is_set():
            try:
                # Check health of all registered agents
                for agent_id, agent in self.agents.items():
                    await self._check_agent_health(agent_id, agent)
                
                # Clean up resolved alerts
                await self._cleanup_old_alerts()
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
        
        logger.debug("Health monitoring loop stopped")
    
    async def _check_agent_health(self, agent_id: str, agent: BaseAgent) -> None:
        """Check health of a specific agent"""
        try:
            # Get agent status and health check
            agent_status = await agent.get_status()
            agent_health = await agent.health_check()
            
            # Calculate health metrics
            metrics = await self._calculate_health_metrics(agent_id, agent, agent_status, agent_health)
            
            # Determine overall health status
            overall_status = self._determine_overall_status(metrics)
            
            # Calculate performance score
            performance_score = self._calculate_performance_score(agent, agent_status)
            
            # Calculate uptime
            uptime = self._calculate_uptime(agent)
            
            # Create health report
            health_report = AgentHealthReport(
                agent_id=agent_id,
                agent_name=agent.name,
                overall_status=overall_status,
                metrics=metrics,
                active_alerts=[alert for alert in self.active_alerts.values() 
                             if alert.agent_id == agent_id],
                last_check=datetime.utcnow(),
                uptime=uptime,
                performance_score=performance_score
            )
            
            self.health_reports[agent_id] = health_report
            
            # Check for alerts
            await self._check_for_alerts(agent_id, metrics)
            
            # Auto-restart if needed
            if (overall_status == HealthStatus.CRITICAL and 
                self.auto_restart_enabled and
                self._restart_attempts.get(agent_id, 0) < self.max_restart_attempts):
                await self._auto_restart_agent(agent_id, agent)
            
        except Exception as e:
            logger.error(f"Failed to check health for agent {agent_id}: {e}")
    
    async def _calculate_health_metrics(
        self, 
        agent_id: str, 
        agent: BaseAgent, 
        agent_status: Dict[str, Any],
        agent_health: Dict[str, Any]
    ) -> List[HealthMetric]:
        """Calculate health metrics for an agent"""
        metrics = []
        
        # Success rate metric
        success_rate = agent_status.get("metrics", {}).get("success_rate", 0)
        metrics.append(HealthMetric(
            name="success_rate",
            value=success_rate,
            threshold_warning=70.0,
            threshold_critical=50.0,
            unit="%",
            description="Task success rate"
        ))
        
        # Error count metric
        error_count = agent_status.get("metrics", {}).get("error_count", 0)
        metrics.append(HealthMetric(
            name="error_count",
            value=error_count,
            threshold_warning=5.0,
            threshold_critical=10.0,
            unit="errors",
            description="Number of errors"
        ))
        
        # Queue size metric
        queue_size = agent_status.get("queue_size", 0)
        metrics.append(HealthMetric(
            name="queue_size",
            value=queue_size,
            threshold_warning=50.0,
            threshold_critical=100.0,
            unit="tasks",
            description="Task queue size"
        ))
        
        # Active tasks metric
        active_tasks = agent_status.get("active_tasks", 0)
        max_concurrent = getattr(agent, 'max_concurrent_tasks', 5)
        task_utilization = (active_tasks / max_concurrent) * 100
        metrics.append(HealthMetric(
            name="task_utilization",
            value=task_utilization,
            threshold_warning=80.0,
            threshold_critical=95.0,
            unit="%",
            description="Task utilization percentage"
        ))
        
        # Memory usage (if available)
        if "memory_usage" in agent_health:
            metrics.append(HealthMetric(
                name="memory_usage",
                value=agent_health["memory_usage"],
                threshold_warning=80.0,
                threshold_critical=90.0,
                unit="%",
                description="Memory usage percentage"
            ))
        
        return metrics
    
    def _determine_overall_status(self, metrics: List[HealthMetric]) -> HealthStatus:
        """Determine overall health status from metrics"""
        critical_count = sum(1 for m in metrics if m.get_status() == HealthStatus.CRITICAL)
        warning_count = sum(1 for m in metrics if m.get_status() == HealthStatus.WARNING)
        
        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif warning_count > 0:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def _calculate_performance_score(self, agent: BaseAgent, agent_status: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)"""
        metrics = agent_status.get("metrics", {})
        
        # Base score from success rate
        success_rate = metrics.get("success_rate", 0)
        score = success_rate
        
        # Penalty for errors
        error_count = metrics.get("error_count", 0)
        error_penalty = min(error_count * 2, 20)  # Max 20 point penalty
        score -= error_penalty
        
        # Penalty for high queue size
        queue_size = agent_status.get("queue_size", 0)
        if queue_size > 20:
            queue_penalty = min((queue_size - 20) * 0.5, 10)  # Max 10 point penalty
            score -= queue_penalty
        
        # Ensure score is between 0 and 100
        return max(0, min(100, score))
    
    def _calculate_uptime(self, agent: BaseAgent) -> float:
        """Calculate agent uptime in seconds"""
        if hasattr(agent, 'metrics') and agent.metrics.last_activity:
            # Simple uptime calculation - in real implementation, track start time
            return (datetime.utcnow() - agent.metrics.last_activity).total_seconds()
        return 0.0
    
    async def _check_for_alerts(self, agent_id: str, metrics: List[HealthMetric]) -> None:
        """Check metrics for alert conditions"""
        for metric in metrics:
            status = metric.get_status()
            
            if status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
                # Check if we should create an alert (cooldown period)
                alert_key = f"{agent_id}_{metric.name}"
                last_alert = self._last_alert_time.get(alert_key)
                
                if (not last_alert or 
                    (datetime.utcnow() - last_alert).total_seconds() > self.alert_cooldown):
                    
                    await self._create_alert(agent_id, metric, status)
                    self._last_alert_time[alert_key] = datetime.utcnow()
            else:
                # Resolve existing alerts for this metric
                await self._resolve_metric_alerts(agent_id, metric.name)
    
    async def _create_alert(self, agent_id: str, metric: HealthMetric, status: HealthStatus) -> None:
        """Create a new health alert"""
        severity = AlertSeverity.CRITICAL if status == HealthStatus.CRITICAL else AlertSeverity.WARNING
        threshold = metric.threshold_critical if status == HealthStatus.CRITICAL else metric.threshold_warning
        
        alert = HealthAlert(
            alert_id=f"{agent_id}_{metric.name}_{datetime.utcnow().timestamp()}",
            agent_id=agent_id,
            severity=severity,
            title=f"Agent {agent_id} - {metric.name} {status.value}",
            message=f"{metric.description} is {metric.value}{metric.unit}, exceeding {status.value} threshold of {threshold}{metric.unit}",
            metric_name=metric.name,
            metric_value=metric.value,
            threshold=threshold,
            created_at=datetime.utcnow()
        )
        
        self.active_alerts[alert.alert_id] = alert
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
        
        logger.warning(f"Created alert: {alert.title}")
    
    async def _resolve_metric_alerts(self, agent_id: str, metric_name: str) -> None:
        """Resolve alerts for a specific metric"""
        alerts_to_resolve = [
            alert_id for alert_id, alert in self.active_alerts.items()
            if alert.agent_id == agent_id and alert.metric_name == metric_name
        ]
        
        for alert_id in alerts_to_resolve:
            await self.resolve_alert(alert_id)
    
    async def _auto_restart_agent(self, agent_id: str, agent: BaseAgent) -> None:
        """Automatically restart a failed agent"""
        try:
            logger.warning(f"Auto-restarting critical agent {agent_id}")
            
            await agent.stop()
            await asyncio.sleep(5)  # Wait before restart
            await agent.start()
            
            self._restart_attempts[agent_id] += 1
            logger.info(f"Agent {agent_id} auto-restarted (attempt {self._restart_attempts[agent_id]})")
            
        except Exception as e:
            logger.error(f"Auto-restart failed for agent {agent_id}: {e}")
    
    async def _cleanup_old_alerts(self) -> None:
        """Clean up old resolved alerts"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        self.alert_history = [
            alert for alert in self.alert_history
            if alert.resolved_at and alert.resolved_at > cutoff_time
        ]