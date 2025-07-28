"""
Audit and compliance API endpoints.

This module provides REST API endpoints for audit logging, compliance reporting,
and security monitoring functionality.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.dependencies import (
    get_current_user, require_admin, require_moderator, get_db,
    PaginationParams, get_pagination_params
)
from shared.models.user import User
from shared.models.audit import AuditEventType, AuditSeverity
from shared.schemas.audit import (
    AuditLogSchema, AuditLogQueryParams, CreateAuditLogRequest,
    AuditStatisticsResponse, PIIDetectionSummary, SecurityEventSummary,
    ComplianceStatus, AuditDashboardResponse, ComplianceReportSchema,
    CreateComplianceReportRequest, DataRetentionPolicySchema,
    CreateDataRetentionPolicyRequest, AuditConfigurationSchema,
    UpdateAuditConfigurationRequest
)
from shared.services.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("/logs", response_model=AuditLogSchema)
async def create_audit_log(
    request_data: CreateAuditLogRequest,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new audit log entry.
    
    This endpoint allows administrators to manually create audit log entries.
    Most audit logs are created automatically by the system.
    """
    try:
        # Extract request context
        request_context = {
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "endpoint": str(request.url),
            "method": request.method,
            "request_id": getattr(request.state, "request_id", None)
        }
        
        # Create audit log
        audit_log = audit_service.log_event(
            event_type=AuditEventType(request_data.event_type),
            description=request_data.description,
            user_id=request_data.user_id or current_user.id,
            severity=AuditSeverity(request_data.severity),
            resource_type=request_data.resource_type,
            resource_id=request_data.resource_id,
            metadata=request_data.metadata,
            request_context=request_context,
            old_values=request_data.old_values,
            new_values=request_data.new_values,
            db=db
        )
        
        return AuditLogSchema.model_validate(audit_log)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create audit log: {str(e)}"
        )


@router.get("/logs", response_model=List[AuditLogSchema])
async def get_audit_logs(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    username: Optional[str] = Query(None, description="Filter by username"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    contains_pii: Optional[bool] = Query(None, description="Filter by PII presence"),
    is_sensitive: Optional[bool] = Query(None, description="Filter by sensitivity"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_dir: str = Query("desc", regex="^(asc|desc)$", description="Order direction"),
    current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit logs with optional filtering and pagination.
    
    Requires moderator or admin role. Returns audit logs matching the specified filters.
    """
    try:
        # Build query parameters
        query_params = AuditLogQueryParams(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            start_date=start_date,
            end_date=end_date,
            contains_pii=contains_pii,
            is_sensitive=is_sensitive,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir
        )
        
        # Query audit logs
        audit_logs, total_count = audit_service.query_audit_logs(query_params, db)
        
        # Convert to schemas
        result = [AuditLogSchema.model_validate(log) for log in audit_logs]
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit logs: {str(e)}"
        )


@router.get("/logs/{audit_log_id}", response_model=AuditLogSchema)
async def get_audit_log(
    audit_log_id: str,
    current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific audit log entry by ID.
    
    Requires moderator or admin role.
    """
    try:
        from shared.models.audit import AuditLog
        
        audit_log = db.query(AuditLog).filter(AuditLog.id == audit_log_id).first()
        
        if not audit_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audit log not found"
            )
        
        return AuditLogSchema.model_validate(audit_log)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit log: {str(e)}"
        )


@router.get("/statistics", response_model=AuditStatisticsResponse)
async def get_audit_statistics(
    start_date: Optional[datetime] = Query(None, description="Statistics start date"),
    end_date: Optional[datetime] = Query(None, description="Statistics end date"),
    current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit statistics for a time period.
    
    Requires moderator or admin role. If no dates are provided, returns statistics
    for the last 30 days.
    """
    try:
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get statistics
        statistics = audit_service.get_audit_statistics(start_date, end_date, db)
        
        return statistics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit statistics: {str(e)}"
        )


@router.get("/dashboard", response_model=AuditDashboardResponse)
async def get_audit_dashboard(
    current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive audit dashboard data.
    
    Requires moderator or admin role. Returns statistics, PII summary,
    security events, compliance status, and recent reports.
    """
    try:
        # Get data for last 30 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        # Get basic statistics
        statistics = audit_service.get_audit_statistics(start_date, end_date, db)
        
        # TODO: Implement additional dashboard data
        # For now, return basic structure with mock data
        
        from shared.schemas.audit import PIIDetectionSummary, SecurityEventSummary, ComplianceStatus
        
        pii_summary = PIIDetectionSummary(
            total_detections=statistics.pii_detections,
            detections_by_type={"email": 10, "phone": 5, "ssn": 2},
            high_confidence_detections=15,
            actions_taken={"logged": 17},
            recent_detections=[]
        )
        
        security_summary = SecurityEventSummary(
            total_events=statistics.security_events,
            events_by_severity={"high": 2, "medium": 5, "low": 10},
            unique_ips=25,
            top_event_types=[
                {"type": "suspicious_activity", "count": 8},
                {"type": "rate_limit_hit", "count": 5}
            ],
            recent_critical_events=[]
        )
        
        compliance_status = ComplianceStatus(
            gdpr_compliant=True,
            ccpa_compliant=True,
            data_retention_current=True,
            audit_coverage=0.95,
            last_assessment=datetime.utcnow() - timedelta(days=7),
            recommendations=[
                "Review PII detection rules",
                "Update retention policies for new data types"
            ]
        )
        
        return AuditDashboardResponse(
            statistics=statistics,
            pii_summary=pii_summary,
            security_summary=security_summary,
            compliance_status=compliance_status,
            recent_reports=[]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit dashboard: {str(e)}"
        )


@router.post("/reports", response_model=ComplianceReportSchema)
async def create_compliance_report(
    request_data: CreateComplianceReportRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new compliance report.
    
    Requires admin role. Generates a compliance report for the specified time period.
    """
    try:
        from shared.models.audit import ComplianceReport
        
        # Generate report data (simplified implementation)
        statistics = audit_service.get_audit_statistics(
            request_data.period_start, 
            request_data.period_end, 
            db
        )
        
        report_data = {
            "statistics": statistics.dict(),
            "generated_at": datetime.utcnow().isoformat(),
            "report_type": request_data.report_type
        }
        
        summary = {
            "total_events": statistics.total_events,
            "pii_detections": statistics.pii_detections,
            "security_events": statistics.security_events,
            "unique_users": statistics.unique_users
        }
        
        # Create report
        report = ComplianceReport(
            report_type=request_data.report_type,
            title=request_data.title,
            description=request_data.description,
            period_start=request_data.period_start,
            period_end=request_data.period_end,
            report_data=report_data,
            summary=summary,
            generated_by=current_user.id,
            generation_method=request_data.generation_method
        )
        
        db.add(report)
        await db.commit()
        await db.refresh(report)
        
        return ComplianceReportSchema.model_validate(report)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create compliance report: {str(e)}"
        )


@router.get("/reports", response_model=List[ComplianceReportSchema])
async def get_compliance_reports(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_moderator),
    db: AsyncSession = Depends(get_db)
):
    """
    Get compliance reports with optional filtering and pagination.
    
    Requires moderator or admin role.
    """
    try:
        from shared.models.audit import ComplianceReport
        
        query = db.query(ComplianceReport)
        
        if report_type:
            query = query.filter(ComplianceReport.report_type == report_type)
            
        if status_filter:
            query = query.filter(ComplianceReport.status == status_filter)
        
        # Apply pagination
        offset = (page - 1) * size
        reports = query.order_by(ComplianceReport.created_at.desc()).offset(offset).limit(size).all()
        
        return [ComplianceReportSchema.model_validate(report) for report in reports]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve compliance reports: {str(e)}"
        )


@router.post("/retention/apply")
async def apply_retention_policies(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Apply data retention policies and clean up old data.
    
    Requires admin role. This endpoint triggers the cleanup of old audit data
    based on configured retention policies.
    """
    try:
        # Apply retention policies
        results = audit_service.apply_retention_policies(db)
        
        # Log the retention policy application
        audit_service.log_event(
            event_type=AuditEventType.ADMIN_SYSTEM_CONFIG,
            description="Data retention policies applied",
            user_id=current_user.id,
            severity=AuditSeverity.MEDIUM,
            metadata={
                "action": "apply_retention_policies",
                "results": results
            },
            db=db
        )
        
        return {
            "success": True,
            "message": "Retention policies applied successfully",
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply retention policies: {str(e)}"
        )


@router.get("/export")
async def export_audit_logs(
    format: str = Query("csv", regex="^(csv|json)$", description="Export format"),
    start_date: Optional[datetime] = Query(None, description="Export start date"),
    end_date: Optional[datetime] = Query(None, description="Export end date"),
    event_types: Optional[List[str]] = Query(None, description="Filter by event types"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Export audit logs in specified format.
    
    Requires admin role. Exports audit logs matching the specified criteria
    in CSV or JSON format.
    """
    try:
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Build query parameters
        query_params = AuditLogQueryParams(
            start_date=start_date,
            end_date=end_date,
            limit=10000,  # Large limit for export
            offset=0
        )
        
        # Query audit logs
        audit_logs, total_count = audit_service.query_audit_logs(query_params, db)
        
        # Log the export activity
        audit_service.log_event(
            event_type=AuditEventType.DATA_EXPORT,
            description=f"Audit logs exported in {format} format",
            user_id=current_user.id,
            severity=AuditSeverity.MEDIUM,
            metadata={
                "export_format": format,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "records_exported": len(audit_logs)
            },
            db=db
        )
        
        if format == "json":
            from fastapi.responses import JSONResponse
            
            export_data = [AuditLogSchema.model_validate(log).dict() for log in audit_logs]
            
            return JSONResponse(
                content={
                    "metadata": {
                        "export_date": datetime.utcnow().isoformat(),
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "total_records": len(export_data)
                    },
                    "data": export_data
                },
                headers={
                    "Content-Disposition": f"attachment; filename=audit_logs_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.json"
                }
            )
        
        else:  # CSV format
            import io
            import csv
            from fastapi.responses import StreamingResponse
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "ID", "Event Type", "Severity", "Description", "User ID", "Username",
                "IP Address", "Resource Type", "Resource ID", "Contains PII", 
                "Is Sensitive", "Created At"
            ])
            
            # Write data
            for log in audit_logs:
                writer.writerow([
                    log.id, log.event_type.value, log.severity.value, log.description,
                    log.user_id, log.username, log.ip_address, log.resource_type,
                    log.resource_id, log.contains_pii, log.is_sensitive, log.created_at
                ])
            
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=audit_logs_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
                }
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export audit logs: {str(e)}"
        )