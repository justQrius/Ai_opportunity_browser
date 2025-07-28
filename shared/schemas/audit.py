"""
Pydantic schemas for audit and compliance functionality.

This module provides schemas for API requests and responses related to
audit logging, compliance reporting, and PII detection.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

from ..models.audit import AuditEventType, AuditSeverity, PIIType


class AuditEventTypeEnum(str, Enum):
    """Pydantic enum for audit event types."""
    
    # Authentication events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_LOGIN_FAILED = "user_login_failed"
    USER_REGISTER = "user_register"
    USER_PASSWORD_RESET = "user_password_reset"
    USER_PASSWORD_CHANGE = "user_password_change"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_BLACKLIST = "token_blacklist"
    MFA_ENABLE = "mfa_enable"
    MFA_DISABLE = "mfa_disable"
    MFA_VERIFY_SUCCESS = "mfa_verify_success" 
    MFA_VERIFY_FAILED = "mfa_verify_failed"
    
    # Data access events
    DATA_READ = "data_read"
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    
    # User actions
    OPPORTUNITY_VIEW = "opportunity_view"
    OPPORTUNITY_CREATE = "opportunity_create"
    OPPORTUNITY_UPDATE = "opportunity_update"
    OPPORTUNITY_DELETE = "opportunity_delete"
    VALIDATION_SUBMIT = "validation_submit"
    VALIDATION_UPDATE = "validation_update"
    VALIDATION_DELETE = "validation_delete"
    SEARCH_QUERY = "search_query"
    RECOMMENDATION_REQUEST = "recommendation_request"
    
    # Admin actions
    ADMIN_USER_UPDATE = "admin_user_update"
    ADMIN_USER_DELETE = "admin_user_delete"
    ADMIN_USER_ROLE_CHANGE = "admin_user_role_change"
    ADMIN_SYSTEM_CONFIG = "admin_system_config"
    ADMIN_BULK_OPERATION = "admin_bulk_operation"
    
    # Security events
    SECURITY_SUSPICIOUS_ACTIVITY = "security_suspicious_activity"
    SECURITY_RATE_LIMIT_HIT = "security_rate_limit_hit"
    SECURITY_UNAUTHORIZED_ACCESS = "security_unauthorized_access"
    SECURITY_DATA_BREACH_DETECTED = "security_data_breach_detected"
    SECURITY_POLICY_VIOLATION = "security_policy_violation"
    
    # System events
    SYSTEM_ERROR = "system_error"
    SYSTEM_PERFORMANCE_ISSUE = "system_performance_issue"
    SYSTEM_MAINTENANCE = "system_maintenance"
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_RESTORE = "system_restore"
    
    # Privacy and compliance
    PRIVACY_DATA_REQUEST = "privacy_data_request"
    PRIVACY_DATA_DELETION = "privacy_data_deletion"
    PRIVACY_CONSENT_UPDATE = "privacy_consent_update"
    COMPLIANCE_REPORT_GENERATED = "compliance_report_generated"
    COMPLIANCE_POLICY_UPDATE = "compliance_policy_update"


class AuditSeverityEnum(str, Enum):
    """Pydantic enum for audit severity levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PIITypeEnum(str, Enum):
    """Pydantic enum for PII types."""
    
    EMAIL = "email"
    PHONE = "phone"
    IP_ADDRESS = "ip_address"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    NAME = "name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    DRIVER_LICENSE = "driver_license"
    PASSPORT = "passport"
    BANK_ACCOUNT = "bank_account"
    CUSTOM = "custom"


class BaseAuditSchema(BaseModel):
    """Base schema for audit-related models."""
    
    model_config = ConfigDict(from_attributes=True)


class PIIDetectionSchema(BaseAuditSchema):
    """Schema for PII detection information."""
    
    id: str
    audit_log_id: str
    pii_type: PIITypeEnum
    field_name: str
    detection_method: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    context: Optional[str] = None
    masked_value: Optional[str] = None
    action_taken: str
    created_at: datetime
    updated_at: datetime


class AuditLogSchema(BaseAuditSchema):
    """Schema for audit log entries."""
    
    id: str
    event_type: AuditEventTypeEnum
    severity: AuditSeverityEnum
    description: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    username: Optional[str] = None
    user_role: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    response_time_ms: Optional[int] = None
    status_code: Optional[int] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    contains_pii: bool = False
    is_sensitive: bool = False
    retention_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    pii_detections: List[PIIDetectionSchema] = []


class CreateAuditLogRequest(BaseModel):
    """Request schema for creating audit log entries."""
    
    event_type: AuditEventTypeEnum
    severity: AuditSeverityEnum = AuditSeverityEnum.LOW
    description: str = Field(..., max_length=5000)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    username: Optional[str] = None
    user_role: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    response_time_ms: Optional[int] = Field(None, ge=0)
    status_code: Optional[int] = Field(None, ge=100, le=599)
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    is_sensitive: bool = False


class AuditLogQueryParams(BaseModel):
    """Query parameters for audit log search."""
    
    event_type: Optional[AuditEventTypeEnum] = None
    severity: Optional[AuditSeverityEnum] = None
    user_id: Optional[str] = None
    username: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    contains_pii: Optional[bool] = None
    is_sensitive: Optional[bool] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)
    order_by: str = Field("created_at", pattern="^(created_at|event_type|severity|user_id)$")
    order_dir: str = Field("desc", pattern="^(asc|desc)$")


class ComplianceReportSchema(BaseAuditSchema):
    """Schema for compliance reports."""
    
    id: str
    report_type: str
    title: str
    description: Optional[str] = None
    period_start: datetime
    period_end: datetime
    report_data: Dict[str, Any]
    summary: Optional[Dict[str, Any]] = None
    generated_by: str
    generation_method: str
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    file_path: Optional[str] = None
    file_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CreateComplianceReportRequest(BaseModel):
    """Request schema for creating compliance reports."""
    
    report_type: str = Field(..., max_length=100)
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    period_start: datetime
    period_end: datetime
    generation_method: str = Field("automated", pattern="^(automated|manual)$")


class DataRetentionPolicySchema(BaseAuditSchema):
    """Schema for data retention policies."""
    
    id: str
    name: str
    description: Optional[str] = None
    data_type: str
    table_name: Optional[str] = None
    retention_days: int
    archive_after_days: Optional[int] = None
    conditions: Optional[Dict[str, Any]] = None
    is_active: bool
    last_applied: Optional[datetime] = None
    legal_basis: Optional[str] = None
    compliance_framework: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CreateDataRetentionPolicyRequest(BaseModel):
    """Request schema for creating data retention policies."""
    
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    data_type: str = Field(..., max_length=100)
    table_name: Optional[str] = None
    retention_days: int = Field(..., gt=0)
    archive_after_days: Optional[int] = Field(None, gt=0)
    conditions: Optional[Dict[str, Any]] = None
    legal_basis: Optional[str] = None
    compliance_framework: Optional[str] = None


class AuditConfigurationSchema(BaseAuditSchema):
    """Schema for audit system configuration."""
    
    id: str
    name: str
    description: Optional[str] = None
    config_data: Dict[str, Any]
    version: int
    is_active: bool
    changed_by: str
    change_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UpdateAuditConfigurationRequest(BaseModel):
    """Request schema for updating audit configuration."""
    
    config_data: Dict[str, Any]
    change_reason: Optional[str] = None


class AuditStatisticsResponse(BaseModel):
    """Response schema for audit statistics."""
    
    total_events: int
    events_by_type: Dict[str, int]
    events_by_severity: Dict[str, int]
    unique_users: int
    pii_detections: int
    security_events: int
    period_start: datetime
    period_end: datetime


class PIIDetectionSummary(BaseModel):
    """Summary of PII detections."""
    
    total_detections: int
    detections_by_type: Dict[str, int]
    high_confidence_detections: int
    actions_taken: Dict[str, int]
    recent_detections: List[PIIDetectionSchema]


class SecurityEventSummary(BaseModel):
    """Summary of security events."""
    
    total_events: int
    events_by_severity: Dict[str, int]
    unique_ips: int
    top_event_types: List[Dict[str, Any]]
    recent_critical_events: List[AuditLogSchema]


class ComplianceStatus(BaseModel):
    """Overall compliance status."""
    
    gdpr_compliant: bool
    ccpa_compliant: bool
    data_retention_current: bool
    audit_coverage: float = Field(..., ge=0.0, le=1.0)
    last_assessment: datetime
    recommendations: List[str]
    
    
class AuditDashboardResponse(BaseModel):
    """Response schema for audit dashboard data."""
    
    statistics: AuditStatisticsResponse
    pii_summary: PIIDetectionSummary
    security_summary: SecurityEventSummary
    compliance_status: ComplianceStatus
    recent_reports: List[ComplianceReportSchema]