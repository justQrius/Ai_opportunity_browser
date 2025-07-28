"""
Security monitoring and management endpoints.

This module provides endpoints for security monitoring, threat detection,
and security configuration management.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import datetime, timedelta

from api.core.dependencies import (
    require_admin,
    require_moderator,
    get_security_principal,
    validate_zero_trust_request
)
from shared.security.monitoring import (
    get_security_monitor,
    SecurityEvent,
    SecurityAlert,
    SecurityEventType,
    SecuritySeverity
)
from shared.security.zero_trust import (
    get_zero_trust_manager,
    SecurityContext
)
from shared.security.service_config import get_service_registry
from shared.models.user import User
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/security/status", response_model=Dict[str, Any])
async def get_security_status(
    request: Request,
    current_user: User = Depends(require_moderator())
):
    """
    Get overall security status and monitoring summary.
    
    Requires moderator or admin role.
    """
    # Validate zero trust request
    await validate_zero_trust_request(
        request,
        "security:status",
        "read",
        SecurityContext.ADMIN
    )
    
    try:
        security_monitor = get_security_monitor()
        summary = security_monitor.get_security_summary()
        
        # Add additional security status information
        zt_manager = get_zero_trust_manager()
        service_registry = get_service_registry()
        
        summary.update({
            "zero_trust_enabled": True,
            "registered_services": len(service_registry.get_all_services()),
            "enabled_services": len([
                s for s in service_registry.get_all_services().values()
                if s.enabled
            ])
        })
        
        logger.info(
            "Security status requested",
            user_id=current_user.id,
            username=current_user.username
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting security status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security status"
        )


@router.get("/security/events", response_model=List[Dict[str, Any]])
async def get_security_events(
    request: Request,
    hours: int = 24,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(require_moderator())
):
    """
    Get recent security events.
    
    Args:
        hours: Number of hours to look back (default: 24)
        event_type: Filter by event type
        severity: Filter by severity level
        limit: Maximum number of events to return
    
    Requires moderator or admin role.
    """
    # Validate zero trust request
    await validate_zero_trust_request(
        request,
        "security:events",
        "read",
        SecurityContext.ADMIN
    )
    
    try:
        security_monitor = get_security_monitor()
        
        # Parse filters
        event_types = None
        if event_type:
            try:
                event_types = [SecurityEventType(event_type)]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event type: {event_type}"
                )
        
        severity_filter = None
        if severity:
            try:
                severity_filter = SecuritySeverity(severity)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid severity: {severity}"
                )
        
        # Get events
        events = security_monitor.get_recent_events(
            hours=hours,
            event_types=event_types,
            severity=severity_filter
        )
        
        # Limit results
        events = events[:limit]
        
        # Convert to dict format
        event_dicts = []
        for event in events:
            event_dict = {
                "event_type": event.event_type.value,
                "severity": event.severity.value,
                "principal_id": event.principal_id,
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "resource": event.resource,
                "action": event.action,
                "message": event.message,
                "timestamp": event.timestamp.isoformat(),
                "metadata": event.metadata,
                "correlation_id": event.correlation_id
            }
            event_dicts.append(event_dict)
        
        logger.info(
            "Security events requested",
            user_id=current_user.id,
            username=current_user.username,
            hours=hours,
            event_count=len(events)
        )
        
        return event_dicts
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting security events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security events"
        )


@router.get("/security/alerts", response_model=List[Dict[str, Any]])
async def get_security_alerts(
    request: Request,
    active_only: bool = True,
    current_user: User = Depends(require_moderator())
):
    """
    Get security alerts.
    
    Args:
        active_only: Only return active (unresolved) alerts
    
    Requires moderator or admin role.
    """
    # Validate zero trust request
    await validate_zero_trust_request(
        request,
        "security:alerts",
        "read",
        SecurityContext.ADMIN
    )
    
    try:
        security_monitor = get_security_monitor()
        
        if active_only:
            alerts = security_monitor.get_active_alerts()
        else:
            alerts = list(security_monitor.alerts.values())
        
        # Convert to dict format
        alert_dicts = []
        for alert in alerts:
            alert_dict = {
                "alert_id": alert.alert_id,
                "title": alert.title,
                "description": alert.description,
                "severity": alert.severity.value,
                "created_at": alert.created_at.isoformat(),
                "acknowledged": alert.acknowledged,
                "resolved": alert.resolved,
                "event_count": len(alert.events),
                "metadata": alert.metadata
            }
            alert_dicts.append(alert_dict)
        
        # Sort by creation time (newest first)
        alert_dicts.sort(key=lambda a: a["created_at"], reverse=True)
        
        logger.info(
            "Security alerts requested",
            user_id=current_user.id,
            username=current_user.username,
            alert_count=len(alert_dicts),
            active_only=active_only
        )
        
        return alert_dicts
        
    except Exception as e:
        logger.error(f"Error getting security alerts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security alerts"
        )


@router.post("/security/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    request: Request,
    current_user: User = Depends(require_moderator())
):
    """
    Acknowledge a security alert.
    
    Requires moderator or admin role.
    """
    # Validate zero trust request
    await validate_zero_trust_request(
        request,
        "security:alerts",
        "write",
        SecurityContext.ADMIN
    )
    
    try:
        security_monitor = get_security_monitor()
        
        if alert_id not in security_monitor.alerts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        security_monitor.acknowledge_alert(alert_id)
        
        logger.info(
            "Security alert acknowledged",
            alert_id=alert_id,
            user_id=current_user.id,
            username=current_user.username
        )
        
        return {"message": "Alert acknowledged", "alert_id": alert_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to acknowledge alert"
        )


@router.post("/security/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    request: Request,
    current_user: User = Depends(require_moderator())
):
    """
    Resolve a security alert.
    
    Requires moderator or admin role.
    """
    # Validate zero trust request
    await validate_zero_trust_request(
        request,
        "security:alerts",
        "write",
        SecurityContext.ADMIN
    )
    
    try:
        security_monitor = get_security_monitor()
        
        if alert_id not in security_monitor.alerts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        security_monitor.resolve_alert(alert_id)
        
        logger.info(
            "Security alert resolved",
            alert_id=alert_id,
            user_id=current_user.id,
            username=current_user.username
        )
        
        return {"message": "Alert resolved", "alert_id": alert_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve alert"
        )


@router.get("/security/services", response_model=Dict[str, Any])
async def get_service_registry(
    request: Request,
    current_user: User = Depends(require_admin())
):
    """
    Get service registry information.
    
    Requires admin role.
    """
    # Validate zero trust request
    await validate_zero_trust_request(
        request,
        "security:services",
        "read",
        SecurityContext.ADMIN
    )
    
    try:
        service_registry = get_service_registry()
        services = service_registry.get_all_services()
        
        # Convert to safe format (without secrets)
        service_info = {}
        for name, config in services.items():
            service_info[name] = {
                "name": config.name,
                "description": config.description,
                "permissions": config.permissions,
                "enabled": config.enabled
            }
        
        logger.info(
            "Service registry requested",
            user_id=current_user.id,
            username=current_user.username,
            service_count=len(services)
        )
        
        return {
            "services": service_info,
            "total_services": len(services),
            "enabled_services": len([s for s in services.values() if s.enabled])
        }
        
    except Exception as e:
        logger.error(f"Error getting service registry: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get service registry"
        )


@router.post("/security/services/{service_name}/rotate-secret")
async def rotate_service_secret(
    service_name: str,
    request: Request,
    current_user: User = Depends(require_admin())
):
    """
    Rotate a service secret.
    
    Requires admin role.
    """
    # Validate zero trust request
    await validate_zero_trust_request(
        request,
        "security:services",
        "write",
        SecurityContext.ADMIN
    )
    
    try:
        service_registry = get_service_registry()
        
        if not service_registry.get_service(service_name):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )
        
        new_secret = service_registry.rotate_service_secret(service_name)
        
        logger.warning(
            "Service secret rotated",
            service_name=service_name,
            user_id=current_user.id,
            username=current_user.username
        )
        
        return {
            "message": "Service secret rotated",
            "service_name": service_name,
            "new_secret": new_secret  # In production, this should be delivered securely
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rotating service secret: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate service secret"
        )