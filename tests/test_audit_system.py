"""
Tests for the audit and compliance system.

This module contains comprehensive tests for audit logging, PII detection,
compliance reporting, and the audit API endpoints.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from shared.models.audit import (
    AuditLog, PIIDetection, ComplianceReport, DataRetentionPolicy,
    AuditEventType, AuditSeverity, PIIType
)
from shared.models.user import User, UserRole
from shared.services.audit_service import AuditService, PIIDetector, PIIDetectionResult
from shared.schemas.audit import AuditLogQueryParams
from api.main import app


class TestPIIDetector:
    """Test cases for the PII detection system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = PIIDetector()
    
    def test_detect_email(self):
        """Test email detection."""
        text = "Please contact us at support@example.com for help."
        detections = self.detector.detect_pii(text, "message")
        
        assert len(detections) == 1
        assert detections[0].pii_type == PIIType.EMAIL
        assert detections[0].confidence_score >= 0.9
        assert "support@example.com" in detections[0].masked_value
    
    def test_detect_phone_numbers(self):
        """Test phone number detection."""
        test_cases = [
            "Call me at 555-123-4567",
            "My number is (555) 123-4567",
            "Contact: +1-555-123-4567"
        ]
        
        for text in test_cases:
            detections = self.detector.detect_pii(text, "contact")
            assert len(detections) >= 1
            assert any(d.pii_type == PIIType.PHONE for d in detections)
    
    def test_detect_ssn(self):
        """Test SSN detection."""
        text = "My SSN is 123-45-6789"
        detections = self.detector.detect_pii(text, "ssn_field")
        
        assert len(detections) == 1
        assert detections[0].pii_type == PIIType.SSN
        assert detections[0].confidence_score >= 0.9
        assert "***-**-6789" in detections[0].masked_value
    
    def test_detect_credit_card(self):
        """Test credit card number detection."""
        text = "My card number is 4111111111111111"
        detections = self.detector.detect_pii(text, "payment")
        
        assert len(detections) == 1
        assert detections[0].pii_type == PIIType.CREDIT_CARD
        assert detections[0].confidence_score >= 0.9
        assert "1111" in detections[0].masked_value
    
    def test_detect_ip_address(self):
        """Test IP address detection."""
        text = "Server IP is 192.168.1.100"
        detections = self.detector.detect_pii(text, "server_config")
        
        assert len(detections) == 1
        assert detections[0].pii_type == PIIType.IP_ADDRESS
        assert detections[0].confidence_score >= 0.8
    
    def test_confidence_adjustment(self):
        """Test confidence score adjustment based on field names."""
        # Email in email field should have higher confidence
        email_detections = self.detector.detect_pii(
            "user@example.com", "email_address"
        )
        
        # Email in random field should have lower confidence
        random_detections = self.detector.detect_pii(
            "user@example.com", "random_field"
        )
        
        assert email_detections[0].confidence_score > random_detections[0].confidence_score
    
    def test_no_pii_in_clean_text(self):
        """Test that clean text produces no PII detections."""
        text = "This is a clean message with no personal information."
        detections = self.detector.detect_pii(text, "message")
        
        assert len(detections) == 0
    
    def test_multiple_pii_types(self):
        """Test detection of multiple PII types in same text."""
        text = "Contact John Doe at john@example.com or call 555-123-4567"
        detections = self.detector.detect_pii(text, "contact_info")
        
        # Should detect email and phone
        pii_types = {d.pii_type for d in detections}
        assert PIIType.EMAIL in pii_types
        assert PIIType.PHONE in pii_types
        assert len(detections) >= 2


class TestAuditService:
    """Test cases for the audit service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = AuditService()
        self.mock_db = Mock(spec=Session)
    
    def test_log_event_basic(self):
        """Test basic event logging."""
        # Mock user lookup
        mock_user = Mock()
        mock_user.username = "testuser"
        mock_user.role = UserRole.USER
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Log an event
        result = self.service.log_event(
            event_type=AuditEventType.USER_LOGIN,
            description="User logged in successfully",
            user_id="user123",
            db=self.mock_db
        )
        
        # Verify database operations
        self.mock_db.add.assert_called()
        self.mock_db.flush.assert_called()
        self.mock_db.commit.assert_called()
    
    def test_log_event_with_pii(self):
        """Test event logging with PII detection."""
        # Mock user lookup
        mock_user = Mock()
        mock_user.username = "testuser"
        mock_user.role = UserRole.USER
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Log event with PII in description
        self.service.log_event(
            event_type=AuditEventType.DATA_UPDATE,
            description="Updated user email to john@example.com",
            user_id="user123",
            metadata={"old_email": "old@example.com"},
            db=self.mock_db
        )
        
        # Should have detected PII and set contains_pii flag
        add_calls = self.mock_db.add.call_args_list
        audit_log_call = add_calls[0][0][0]  # First call, first argument
        
        assert audit_log_call.contains_pii == True
    
    def test_log_event_security_incident(self):
        """Test logging of security incidents with high severity."""
        result = self.service.log_event(
            event_type=AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY,
            description="Multiple failed login attempts from same IP",
            severity=AuditSeverity.HIGH,
            request_context={"ip_address": "192.168.1.100"},
            db=self.mock_db
        )
        
        # Verify sensitive flag is set
        add_calls = self.mock_db.add.call_args_list
        audit_log_call = add_calls[0][0][0]
        
        assert audit_log_call.is_sensitive == True
        assert audit_log_call.severity == AuditSeverity.SECURITY_SUSPICIOUS_ACTIVITY
    
    def test_query_audit_logs_with_filters(self):
        """Test querying audit logs with various filters."""
        # Mock query results
        mock_logs = [Mock(), Mock(), Mock()]
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 3
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_logs
        
        self.mock_db.query.return_value = mock_query
        
        # Test with filters
        params = AuditLogQueryParams(
            event_type="user_login",
            severity="high",
            user_id="user123",
            limit=10,
            offset=0
        )
        
        logs, count = self.service.query_audit_logs(params, self.mock_db)
        
        assert len(logs) == 3
        assert count == 3
        
        # Verify filters were applied
        assert mock_query.filter.call_count >= 3  # Should have applied multiple filters
    
    def test_get_audit_statistics(self):
        """Test audit statistics generation."""
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        # Mock database queries
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 100
        mock_query.with_entities.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.all.return_value = [
            (AuditEventType.USER_LOGIN, 50),
            (AuditEventType.DATA_UPDATE, 30),
            (AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY, 5)
        ]
        mock_query.distinct.return_value = mock_query
        
        self.mock_db.query.return_value = mock_query
        
        # Get statistics
        stats = self.service.get_audit_statistics(start_date, end_date, self.mock_db)
        
        assert stats.total_events == 100
        assert len(stats.events_by_type) > 0
        assert stats.period_start == start_date
        assert stats.period_end == end_date
    
    def test_retention_date_calculation(self):
        """Test retention date calculation for different event types."""
        # Test with different event types
        login_date = self.service._calculate_retention_date(AuditEventType.USER_LOGIN)
        data_create_date = self.service._calculate_retention_date(AuditEventType.DATA_CREATE)
        
        # Login events should have shorter retention than data creation
        assert login_date < data_create_date
        
        # Both should be future dates
        now = datetime.now(timezone.utc)
        assert login_date > now
        assert data_create_date > now
    
    def test_sensitive_event_detection(self):
        """Test detection of sensitive events."""
        # Test sensitive events
        sensitive_events = [
            AuditEventType.USER_PASSWORD_RESET,
            AuditEventType.SECURITY_DATA_BREACH_DETECTED,
            AuditEventType.PRIVACY_DATA_DELETION
        ]
        
        for event_type in sensitive_events:
            assert self.service._is_sensitive_event(event_type) == True
        
        # Test non-sensitive events
        non_sensitive_events = [
            AuditEventType.USER_LOGIN,
            AuditEventType.DATA_READ,
            AuditEventType.SEARCH_QUERY
        ]
        
        for event_type in non_sensitive_events:
            assert self.service._is_sensitive_event(event_type) == False


class TestAuditAPI:
    """Test cases for audit API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        self.admin_token = "test_admin_token"
        self.moderator_token = "test_moderator_token"
    
    @patch('api.core.dependencies.get_current_user')
    @patch('shared.services.audit_service.audit_service.log_event')
    def test_create_audit_log(self, mock_log_event, mock_get_user):
        """Test creating audit log via API."""
        # Mock admin user
        mock_user = Mock()
        mock_user.id = "admin123"
        mock_user.role = UserRole.ADMIN
        mock_get_user.return_value = mock_user
        
        # Mock audit log creation
        mock_audit_log = Mock()
        mock_audit_log.id = "audit123"
        mock_audit_log.event_type = AuditEventType.ADMIN_SYSTEM_CONFIG
        mock_log_event.return_value = mock_audit_log
        
        # Make request
        response = self.client.post(
            "/api/v1/audit/logs",
            json={
                "event_type": "admin_system_config",
                "description": "System configuration updated",
                "severity": "medium"
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        assert response.status_code == 200
        mock_log_event.assert_called_once()
    
    @patch('api.core.dependencies.get_current_user')
    @patch('shared.services.audit_service.audit_service.query_audit_logs')
    def test_get_audit_logs(self, mock_query_logs, mock_get_user):
        """Test retrieving audit logs via API."""
        # Mock moderator user
        mock_user = Mock()
        mock_user.id = "mod123"
        mock_user.role = UserRole.MODERATOR
        mock_get_user.return_value = mock_user
        
        # Mock audit logs
        mock_logs = [Mock(), Mock()]
        mock_query_logs.return_value = (mock_logs, 2)
        
        # Make request
        response = self.client.get(
            "/api/v1/audit/logs?event_type=user_login&limit=10",
            headers={"Authorization": f"Bearer {self.moderator_token}"}
        )
        
        assert response.status_code == 200
        mock_query_logs.assert_called_once()
    
    @patch('api.core.dependencies.get_current_user')
    @patch('shared.services.audit_service.audit_service.get_audit_statistics')
    def test_get_audit_statistics(self, mock_get_stats, mock_get_user):
        """Test retrieving audit statistics via API."""
        # Mock moderator user
        mock_user = Mock()
        mock_user.id = "mod123"
        mock_user.role = UserRole.MODERATOR
        mock_get_user.return_value = mock_user
        
        # Mock statistics
        from shared.schemas.audit import AuditStatisticsResponse
        mock_stats = AuditStatisticsResponse(
            total_events=100,
            events_by_type={"user_login": 50},
            events_by_severity={"low": 80, "medium": 15, "high": 5},
            unique_users=25,
            pii_detections=10,
            security_events=5,
            period_start=datetime.now(timezone.utc) - timedelta(days=30),
            period_end=datetime.now(timezone.utc)
        )
        mock_get_stats.return_value = mock_stats
        
        # Make request
        response = self.client.get(
            "/api/v1/audit/statistics",
            headers={"Authorization": f"Bearer {self.moderator_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 100
        assert data["unique_users"] == 25
    
    @patch('api.core.dependencies.get_current_user')
    def test_get_audit_dashboard(self, mock_get_user):
        """Test retrieving audit dashboard via API."""
        # Mock moderator user
        mock_user = Mock()
        mock_user.id = "mod123"
        mock_user.role = UserRole.MODERATOR
        mock_get_user.return_value = mock_user
        
        with patch('shared.services.audit_service.audit_service.get_audit_statistics') as mock_stats:
            from shared.schemas.audit import AuditStatisticsResponse
            mock_stats.return_value = AuditStatisticsResponse(
                total_events=100,
                events_by_type={},
                events_by_severity={},
                unique_users=25,
                pii_detections=10,
                security_events=5,
                period_start=datetime.now(timezone.utc) - timedelta(days=30),
                period_end=datetime.now(timezone.utc)
            )
            
            response = self.client.get(
                "/api/v1/audit/dashboard",
                headers={"Authorization": f"Bearer {self.moderator_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "statistics" in data
            assert "pii_summary" in data
            assert "security_summary" in data
            assert "compliance_status" in data
    
    def test_unauthorized_access(self):
        """Test that unauthorized users cannot access audit endpoints."""
        # No token
        response = self.client.get("/api/v1/audit/logs")
        assert response.status_code == 401
        
        # Invalid token
        response = self.client.get(
            "/api/v1/audit/logs",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
    
    @patch('api.core.dependencies.get_current_user')
    def test_insufficient_permissions(self, mock_get_user):
        """Test that regular users cannot access admin audit endpoints."""
        # Mock regular user
        mock_user = Mock()
        mock_user.id = "user123"
        mock_user.role = UserRole.USER
        mock_get_user.return_value = mock_user
        
        # Try to create audit log (admin only)
        response = self.client.post(
            "/api/v1/audit/logs",
            json={
                "event_type": "user_login",
                "description": "Test event"
            },
            headers={"Authorization": "Bearer user_token"}
        )
        
        assert response.status_code == 403


class TestAuditModels:
    """Test cases for audit database models."""
    
    def test_audit_log_creation(self):
        """Test AuditLog model creation."""
        audit_log = AuditLog(
            event_type=AuditEventType.USER_LOGIN,
            severity=AuditSeverity.LOW,
            description="User logged in",
            user_id="user123",
            ip_address="192.168.1.100"
        )
        
        assert audit_log.event_type == AuditEventType.USER_LOGIN
        assert audit_log.severity == AuditSeverity.LOW
        assert audit_log.description == "User logged in"
        assert audit_log.contains_pii == False
        assert audit_log.is_sensitive == False
    
    def test_pii_detection_creation(self):
        """Test PIIDetection model creation."""
        pii_detection = PIIDetection(
            audit_log_id="audit123",
            pii_type=PIIType.EMAIL,
            field_name="description",
            detection_method="regex",
            confidence_score=0.95,
            masked_value="u***@example.com",
            action_taken="logged"
        )
        
        assert pii_detection.pii_type == PIIType.EMAIL
        assert pii_detection.confidence_score == 0.95
        assert pii_detection.action_taken == "logged"
    
    def test_compliance_report_creation(self):
        """Test ComplianceReport model creation."""
        report = ComplianceReport(
            report_type="gdpr",
            title="GDPR Compliance Report Q1 2024",
            period_start=datetime.now(timezone.utc) - timedelta(days=90),
            period_end=datetime.now(timezone.utc),
            report_data={"total_events": 1000},
            generated_by="admin123",
            generation_method="automated"
        )
        
        assert report.report_type == "gdpr"
        assert report.generation_method == "automated"
        assert report.status == "draft"  # Default status
    
    def test_data_retention_policy_creation(self):
        """Test DataRetentionPolicy model creation."""
        policy = DataRetentionPolicy(
            name="Audit Log Retention",
            data_type="audit_logs",
            retention_days=365,
            archive_after_days=90,
            is_active=True,
            legal_basis="Legal requirement for audit trail"
        )
        
        assert policy.name == "Audit Log Retention"
        assert policy.retention_days == 365
        assert policy.is_active == True


if __name__ == "__main__":
    pytest.main([__file__])