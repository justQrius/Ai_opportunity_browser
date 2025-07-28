"""
Comprehensive audit service for the AI Opportunity Browser.

This service provides functionality for audit logging, compliance reporting,
and security event tracking with automated PII detection.
"""

import re
import json
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Union, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from dataclasses import dataclass

from ..models.audit import (
    AuditLog, PIIDetection, ComplianceReport, DataRetentionPolicy,
    AuditConfiguration, AuditEventType, AuditSeverity, PIIType
)
from ..models.user import User
from ..schemas.audit import (
    AuditLogQueryParams, CreateAuditLogRequest, AuditStatisticsResponse,
    PIIDetectionSummary, SecurityEventSummary, ComplianceStatus
)
from ..database import get_db_session

logger = logging.getLogger(__name__)


@dataclass
class PIIDetectionResult:
    """Result of PII detection analysis."""
    
    pii_type: PIIType
    field_name: str
    detection_method: str
    confidence_score: float
    context: Optional[str] = None
    masked_value: Optional[str] = None
    action_taken: str = "logged"


class PIIDetector:
    """Automated PII detection system."""
    
    def __init__(self):
        self.patterns = {
            PIIType.EMAIL: [
                (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 0.95),
            ],
            PIIType.PHONE: [
                (r'\b(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?)?[0-9]{3}[-.\s]?[0-9]{4}\b', 0.85),
                (r'\b\d{3}-\d{3}-\d{4}\b', 0.90),
                (r'\b\(\d{3}\)\s*\d{3}-\d{4}\b', 0.90),
            ],
            PIIType.SSN: [
                (r'\b\d{3}-\d{2}-\d{4}\b', 0.95),
                (r'\b\d{3}\d{2}\d{4}\b', 0.85),
            ],
            PIIType.CREDIT_CARD: [
                (r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b', 0.90),
            ],
            PIIType.IP_ADDRESS: [
                (r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', 0.80),
                (r'\b(?:[a-fA-F0-9]{1,4}:){7}[a-fA-F0-9]{1,4}\b', 0.85),  # IPv6
            ],
            PIIType.NAME: [
                (r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', 0.60),  # Simple first last name pattern
            ],
            PIIType.ADDRESS: [
                (r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)\b', 0.70),
            ],
        }
        
    def detect_pii(self, text: str, field_name: str = "unknown") -> List[PIIDetectionResult]:
        """
        Detect PII in the given text.
        
        Args:
            text: Text to analyze for PII
            field_name: Name of the field being analyzed
            
        Returns:
            List of PII detection results
        """
        if not text or not isinstance(text, str):
            return []
            
        detections = []
        
        for pii_type, patterns in self.patterns.items():
            for pattern, base_confidence in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    matched_text = match.group()
                    
                    # Adjust confidence based on context
                    confidence = self._adjust_confidence(
                        base_confidence, pii_type, matched_text, field_name
                    )
                    
                    if confidence >= 0.5:  # Minimum confidence threshold
                        detection = PIIDetectionResult(
                            pii_type=pii_type,
                            field_name=field_name,
                            detection_method="regex",
                            confidence_score=confidence,
                            context=f"Found in position {match.start()}-{match.end()}",
                            masked_value=self._mask_value(matched_text, pii_type),
                            action_taken="logged"
                        )
                        detections.append(detection)
        
        return detections
    
    def _adjust_confidence(
        self, 
        base_confidence: float, 
        pii_type: PIIType, 
        matched_text: str, 
        field_name: str
    ) -> float:
        """Adjust confidence score based on context."""
        
        confidence = base_confidence
        
        # Boost confidence if field name suggests PII
        field_name_lower = field_name.lower()
        if pii_type == PIIType.EMAIL and 'email' in field_name_lower:
            confidence = min(1.0, confidence + 0.1)
        elif pii_type == PIIType.PHONE and 'phone' in field_name_lower:
            confidence = min(1.0, confidence + 0.1)
        elif pii_type == PIIType.NAME and 'name' in field_name_lower:
            confidence = min(1.0, confidence + 0.2)
            
        # Reduce confidence for common false positives
        if pii_type == PIIType.NAME:
            # Common non-name patterns that match name regex
            common_false_positives = ['Test User', 'John Doe', 'Jane Doe']
            if matched_text in common_false_positives:
                confidence *= 0.3
                
        return confidence
    
    def _mask_value(self, value: str, pii_type: PIIType) -> str:
        """Create a masked version of the PII value."""
        
        if pii_type == PIIType.EMAIL:
            parts = value.split('@')
            if len(parts) == 2:
                username = parts[0]
                domain = parts[1]
                masked_username = username[0] + '*' * (len(username) - 2) + username[-1] if len(username) > 2 else '*' * len(username)
                return f"{masked_username}@{domain}"
                
        elif pii_type == PIIType.PHONE:
            if len(value) >= 4:
                return '*' * (len(value) - 4) + value[-4:]
                
        elif pii_type == PIIType.SSN:
            return '***-**-' + value[-4:] if len(value) >= 4 else '*' * len(value)
            
        elif pii_type == PIIType.CREDIT_CARD:
            return '*' * (len(value) - 4) + value[-4:] if len(value) >= 4 else '*' * len(value)
            
        elif pii_type == PIIType.NAME:
            parts = value.split()
            if len(parts) >= 2:
                return parts[0][0] + '*' * (len(parts[0]) - 1) + ' ' + parts[-1][0] + '*' * (len(parts[-1]) - 1)
                
        # Default masking
        if len(value) <= 2:
            return '*' * len(value)
        elif len(value) <= 4:
            return value[0] + '*' * (len(value) - 2) + value[-1]
        else:
            return value[0] + '*' * (len(value) - 4) + value[-3:]


class AuditService:
    """Main audit service for logging and compliance."""
    
    def __init__(self):
        self.pii_detector = PIIDetector()
        
    def log_event(
        self,
        event_type: AuditEventType,
        description: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.LOW,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_context: Optional[Dict[str, Any]] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> AuditLog:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event being logged
            description: Human-readable description of the event
            user_id: ID of the user who triggered the event
            session_id: Session ID if applicable
            severity: Severity level of the event
            resource_type: Type of resource being acted upon
            resource_id: ID of the resource being acted upon
            metadata: Additional metadata about the event
            request_context: HTTP request context (IP, user agent, etc.)
            old_values: Previous values for update/delete operations
            new_values: New values for create/update operations
            db: Database session
            
        Returns:
            Created audit log entry
        """
        
        if db is None:
            db = next(get_db_session())
            
        try:
            # Get user information if user_id provided
            username = None
            user_role = None
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    username = user.username
                    user_role = user.role.value if user.role else None
            
            # Extract request context
            ip_address = None
            user_agent = None
            endpoint = None
            method = None
            response_time_ms = None
            status_code = None
            request_id = None
            
            if request_context:
                ip_address = request_context.get('ip_address')
                user_agent = request_context.get('user_agent')
                endpoint = request_context.get('endpoint')
                method = request_context.get('method')
                response_time_ms = request_context.get('response_time_ms')
                status_code = request_context.get('status_code')
                request_id = request_context.get('request_id')
            
            # Create audit log entry
            audit_log = AuditLog(
                event_type=event_type,
                severity=severity,
                description=description,
                user_id=user_id,
                session_id=session_id,
                username=username,
                user_role=user_role,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata=metadata,
                endpoint=endpoint,
                method=method,
                response_time_ms=response_time_ms,
                status_code=status_code,
                old_values=old_values,
                new_values=new_values,
                is_sensitive=self._is_sensitive_event(event_type),
                retention_date=self._calculate_retention_date(event_type)
            )
            
            # Detect PII in the audit data
            pii_detections = self._detect_pii_in_audit_data(audit_log)
            
            if pii_detections:
                audit_log.contains_pii = True
            
            # Save audit log
            db.add(audit_log)
            db.flush()  # Get the ID
            
            # Save PII detections
            for detection in pii_detections:
                pii_record = PIIDetection(
                    audit_log_id=audit_log.id,
                    pii_type=detection.pii_type,
                    field_name=detection.field_name,
                    detection_method=detection.detection_method,
                    confidence_score=detection.confidence_score,
                    context=detection.context,
                    masked_value=detection.masked_value,
                    action_taken=detection.action_taken
                )
                db.add(pii_record)
            
            db.commit()
            
            logger.info(f"Audit event logged: {event_type.value} for user {username or 'anonymous'}")
            
            return audit_log
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to log audit event: {e}")
            raise
    
    def _detect_pii_in_audit_data(self, audit_log: AuditLog) -> List[PIIDetectionResult]:
        """Detect PII in audit log data."""
        
        detections = []
        
        # Check description
        detections.extend(self.pii_detector.detect_pii(audit_log.description, "description"))
        
        # Check metadata
        if audit_log.metadata:
            for key, value in audit_log.metadata.items():
                if isinstance(value, str):
                    detections.extend(self.pii_detector.detect_pii(value, f"metadata.{key}"))
        
        # Check old_values
        if audit_log.old_values:
            for key, value in audit_log.old_values.items():
                if isinstance(value, str):
                    detections.extend(self.pii_detector.detect_pii(value, f"old_values.{key}"))
        
        # Check new_values
        if audit_log.new_values:
            for key, value in audit_log.new_values.items():
                if isinstance(value, str):
                    detections.extend(self.pii_detector.detect_pii(value, f"new_values.{key}"))
        
        return detections
    
    def _is_sensitive_event(self, event_type: AuditEventType) -> bool:
        """Determine if an event type is considered sensitive."""
        
        sensitive_events = {
            AuditEventType.USER_PASSWORD_RESET,
            AuditEventType.USER_PASSWORD_CHANGE,
            AuditEventType.ADMIN_USER_DELETE,
            AuditEventType.ADMIN_USER_ROLE_CHANGE,
            AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY,
            AuditEventType.SECURITY_DATA_BREACH_DETECTED,
            AuditEventType.SECURITY_POLICY_VIOLATION,
            AuditEventType.PRIVACY_DATA_REQUEST,
            AuditEventType.PRIVACY_DATA_DELETION,
        }
        
        return event_type in sensitive_events
    
    def _calculate_retention_date(self, event_type: AuditEventType) -> Optional[datetime]:
        """Calculate retention date based on event type and policies."""
        
        # Default retention periods (in days)
        retention_periods = {
            AuditEventType.USER_LOGIN: 90,
            AuditEventType.USER_LOGOUT: 90,
            AuditEventType.DATA_READ: 30,
            AuditEventType.DATA_CREATE: 2555,  # 7 years
            AuditEventType.DATA_UPDATE: 2555,  # 7 years
            AuditEventType.DATA_DELETE: 2555,  # 7 years
            AuditEventType.ADMIN_USER_UPDATE: 2555,  # 7 years
            AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY: 2555,  # 7 years
        }
        
        days = retention_periods.get(event_type, 365)  # Default 1 year
        return datetime.now(timezone.utc) + timedelta(days=days)
    
    def query_audit_logs(
        self,
        params: AuditLogQueryParams,
        db: Optional[Session] = None
    ) -> Tuple[List[AuditLog], int]:
        """
        Query audit logs with filtering and pagination.
        
        Args:
            params: Query parameters
            db: Database session
            
        Returns:
            Tuple of (audit logs, total count)
        """
        
        if db is None:
            db = next(get_db_session())
        
        query = db.query(AuditLog)
        
        # Apply filters
        if params.event_type:
            query = query.filter(AuditLog.event_type == params.event_type.value)
            
        if params.severity:
            query = query.filter(AuditLog.severity == params.severity.value)
            
        if params.user_id:
            query = query.filter(AuditLog.user_id == params.user_id)
            
        if params.username:
            query = query.filter(AuditLog.username.ilike(f"%{params.username}%"))
            
        if params.resource_type:
            query = query.filter(AuditLog.resource_type == params.resource_type)
            
        if params.resource_id:
            query = query.filter(AuditLog.resource_id == params.resource_id)
            
        if params.ip_address:
            query = query.filter(AuditLog.ip_address == params.ip_address)
            
        if params.start_date:
            query = query.filter(AuditLog.created_at >= params.start_date)
            
        if params.end_date:
            query = query.filter(AuditLog.created_at <= params.end_date)
            
        if params.contains_pii is not None:
            query = query.filter(AuditLog.contains_pii == params.contains_pii)
            
        if params.is_sensitive is not None:
            query = query.filter(AuditLog.is_sensitive == params.is_sensitive)
        
        # Get total count
        total_count = query.count()
        
        # Apply ordering
        if params.order_by == "created_at":
            order_column = AuditLog.created_at
        elif params.order_by == "event_type":
            order_column = AuditLog.event_type
        elif params.order_by == "severity":
            order_column = AuditLog.severity
        elif params.order_by == "user_id":
            order_column = AuditLog.user_id
        else:
            order_column = AuditLog.created_at
            
        if params.order_dir == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        # Apply pagination
        query = query.offset(params.offset).limit(params.limit)
        
        audit_logs = query.all()
        
        return audit_logs, total_count
    
    def get_audit_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
        db: Optional[Session] = None
    ) -> AuditStatisticsResponse:
        """Get audit statistics for a time period."""
        
        if db is None:
            db = next(get_db_session())
        
        # Base query for time period
        base_query = db.query(AuditLog).filter(
            and_(
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date
            )
        )
        
        # Total events
        total_events = base_query.count()
        
        # Events by type
        events_by_type = {}
        type_counts = (
            base_query
            .with_entities(AuditLog.event_type, func.count(AuditLog.id))
            .group_by(AuditLog.event_type)
            .all()
        )
        for event_type, count in type_counts:
            events_by_type[event_type.value] = count
        
        # Events by severity
        events_by_severity = {}
        severity_counts = (
            base_query
            .with_entities(AuditLog.severity, func.count(AuditLog.id))
            .group_by(AuditLog.severity)
            .all()
        )
        for severity, count in severity_counts:
            events_by_severity[severity.value] = count
        
        # Unique users
        unique_users = (
            base_query
            .with_entities(AuditLog.user_id)
            .filter(AuditLog.user_id.isnot(None))
            .distinct()
            .count()
        )
        
        # PII detections
        pii_detections = (
            db.query(PIIDetection)
            .join(AuditLog)
            .filter(
                and_(
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date
                )
            )
            .count()
        )
        
        # Security events
        security_events = (
            base_query
            .filter(
                AuditLog.event_type.in_([
                    AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY,
                    AuditEventType.SECURITY_RATE_LIMIT_HIT,
                    AuditEventType.SECURITY_UNAUTHORIZED_ACCESS,
                    AuditEventType.SECURITY_DATA_BREACH_DETECTED,
                    AuditEventType.SECURITY_POLICY_VIOLATION,
                ])
            )
            .count()
        )
        
        return AuditStatisticsResponse(
            total_events=total_events,
            events_by_type=events_by_type,
            events_by_severity=events_by_severity,
            unique_users=unique_users,
            pii_detections=pii_detections,
            security_events=security_events,
            period_start=start_date,
            period_end=end_date
        )
    
    def apply_retention_policies(self, db: Optional[Session] = None) -> Dict[str, int]:
        """Apply data retention policies and clean up old data."""
        
        if db is None:
            db = next(get_db_session())
        
        results = {}
        
        try:
            # Get active retention policies
            policies = (
                db.query(DataRetentionPolicy)
                .filter(DataRetentionPolicy.is_active == True)
                .all()
            )
            
            for policy in policies:
                if policy.table_name == "audit_logs":
                    # Calculate cutoff date
                    cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
                    
                    # Delete old audit logs
                    deleted_count = (
                        db.query(AuditLog)
                        .filter(AuditLog.created_at < cutoff_date)
                        .delete()
                    )
                    
                    results[f"audit_logs_{policy.name}"] = deleted_count
                    
                    # Update policy last applied
                    policy.last_applied = datetime.now(timezone.utc)
            
            db.commit()
            logger.info(f"Applied retention policies: {results}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to apply retention policies: {e}")
            raise
        
        return results


# Global audit service instance
audit_service = AuditService()