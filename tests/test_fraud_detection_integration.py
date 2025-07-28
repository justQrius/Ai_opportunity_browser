"""Integration tests for fraud detection and moderation systems."""

import pytest
import asyncio
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.main import app
from shared.database import get_db
from shared.models.validation import ValidationResult, ValidationType
from shared.models.user import User, UserRole
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.services.fraud_detection_service import fraud_detection_service, FraudType
from shared.services.moderation_service import moderation_service, ModerationStatus
from shared.services.user_service import user_service
from shared.services.opportunity_service import opportunity_service
from shared.services.validation_service import validation_service
from shared.auth import create_access_token


class TestFraudDetectionIntegration:
    """Integration tests for fraud detection system."""
    
    @pytest.fixture
    def client(self):
        """Test client."""
        return TestClient(app)
    
    @pytest.fixture
    async def test_data(self, db_session):
        """Setup test data."""
        # Create test users
        regular_user = await user_service.create_user(
            db_session,
            username="testuser",
            email="test@example.com",
            password="testpass123",
            role=UserRole.USER
        )
        
        moderator_user = await user_service.create_user(
            db_session,
            username="moderator",
            email="mod@example.com",
            password="modpass123",
            role=UserRole.MODERATOR
        )
        
        spam_user = await user_service.create_user(
            db_session,
            username="spammer",
            email="spam@example.com",
            password="spampass123",
            role=UserRole.USER
        )
        
        # Create test opportunity
        opportunity = await opportunity_service.create_opportunity(
            db_session,
            title="Test AI Opportunity",
            description="Test opportunity for fraud detection",
            market_size_estimate=1000000,
            confidence_score=7.5,
            ai_relevance_score=8.0,
            implementation_complexity=5,
            market_validation_score=7.0,
            status=OpportunityStatus.VALIDATING
        )
        
        return {
            "regular_user": regular_user,
            "moderator_user": moderator_user,
            "spam_user": spam_user,
            "opportunity": opportunity
        }
    
    @pytest.mark.asyncio
    async def test_fraud_detection_workflow(self, db_session, test_data):
        """Test complete fraud detection workflow."""
        spam_user = test_data["spam_user"]
        opportunity = test_data["opportunity"]
        
        # Create spam-like validation
        validation = await validation_service.create_validation(
            db_session,
            opportunity_id=opportunity.id,
            validator_id=spam_user.id,
            validation_type=ValidationType.MARKET_DEMAND,
            score=5.0,
            confidence=2.0,
            comments="bad",  # Very short
            methodology="quick"
        )
        
        # Simulate multiple rapid validations
        for i in range(10):
            await validation_service.create_validation(
                db_session,
                opportunity_id=opportunity.id,
                validator_id=spam_user.id,
                validation_type=ValidationType.MARKET_DEMAND,
                score=5.0 + i * 0.1,
                confidence=3.0,
                comments=f"short {i}",
                methodology="rapid"
            )
        
        # Run fraud detection
        fraud_results = await fraud_detection_service.analyze_validation_for_fraud(
            db_session, validation.id
        )
        
        # Should detect spam
        assert len(fraud_results) > 0
        spam_detected = any(r.fraud_type == FraudType.SPAM_VALIDATION for r in fraud_results)
        assert spam_detected
        
        # Process through moderation
        moderation_item = await moderation_service.process_validation_for_moderation(
            db_session, validation.id
        )
        
        # Should be added to moderation queue
        assert moderation_item is not None
        assert moderation_item.status == ModerationStatus.PENDING
        assert len(moderation_item.fraud_results) > 0
    
    @pytest.mark.asyncio
    async def test_community_flagging_workflow(self, db_session, test_data):
        """Test community flagging workflow."""
        regular_user = test_data["regular_user"]
        spam_user = test_data["spam_user"]
        opportunity = test_data["opportunity"]
        
        # Create validation to be flagged
        validation = await validation_service.create_validation(
            db_session,
            opportunity_id=opportunity.id,
            validator_id=spam_user.id,
            validation_type=ValidationType.TECHNICAL_FEASIBILITY,
            score=8.0,
            confidence=9.0,
            comments="This is definitely feasible with current AI technology.",
            methodology="expert_analysis"
        )
        
        # Flag the validation
        success = await fraud_detection_service.flag_validation(
            db_session,
            validation.id,
            regular_user.id,
            "Misleading information about AI capabilities",
            "Claims are not supported by current technology"
        )
        
        assert success is True
        
        # Check validation is flagged
        await db_session.refresh(validation)
        assert validation.is_flagged is True
        assert "Misleading information" in validation.flag_reason
    
    @pytest.mark.asyncio
    async def test_moderation_assignment_and_decision(self, db_session, test_data):
        """Test moderator assignment and decision making."""
        moderator = test_data["moderator_user"]
        spam_user = test_data["spam_user"]
        opportunity = test_data["opportunity"]
        
        # Create problematic validation
        validation = await validation_service.create_validation(
            db_session,
            opportunity_id=opportunity.id,
            validator_id=spam_user.id,
            validation_type=ValidationType.BUSINESS_VIABILITY,
            score=3.0,
            confidence=1.0,
            comments="not sure maybe",
            methodology="guess"
        )
        
        # Process through moderation
        moderation_item = await moderation_service.process_validation_for_moderation(
            db_session, validation.id
        )
        
        if moderation_item:
            # Assign to moderator
            success = await moderation_service.assign_moderation_item(
                validation.id, moderator.id
            )
            assert success is True
            
            # Make moderation decision
            from shared.services.fraud_detection_service import ModerationAction
            success = await moderation_service.moderate_validation(
                db_session,
                validation.id,
                moderator.id,
                ModerationAction.HIDE_VALIDATION,
                "Low quality validation with insufficient evidence",
                "Validation lacks proper methodology and evidence"
            )
            assert success is True
    
    @pytest.mark.asyncio
    async def test_appeal_system_workflow(self, db_session, test_data):
        """Test appeal system workflow."""
        spam_user = test_data["spam_user"]
        moderator = test_data["moderator_user"]
        opportunity = test_data["opportunity"]
        
        # Create validation and add to moderation queue
        validation = await validation_service.create_validation(
            db_session,
            opportunity_id=opportunity.id,
            validator_id=spam_user.id,
            validation_type=ValidationType.MARKET_DEMAND,
            score=6.0,
            confidence=5.0,
            comments="Market demand exists based on my research.",
            methodology="survey"
        )
        
        # Simulate moderation decision
        moderation_item = await moderation_service.process_validation_for_moderation(
            db_session, validation.id
        )
        
        if moderation_item:
            # Submit appeal
            appeal = await moderation_service.submit_appeal(
                db_session,
                validation.id,
                spam_user.id,
                "I believe my validation was accurate and well-researched",
                "I have additional evidence to support my claims"
            )
            
            assert appeal.user_id == spam_user.id
            assert appeal.validation_id == validation.id
            assert "accurate and well-researched" in appeal.appeal_reason
            
            # Process appeal (deny)
            success = await moderation_service.process_appeal(
                db_session,
                validation.id,
                moderator.id,
                approved=False,
                resolution="Original decision upheld due to lack of supporting evidence"
            )
            assert success is True
    
    def test_fraud_detection_api_endpoints(self, client, test_data):
        """Test fraud detection API endpoints."""
        moderator = test_data["moderator_user"]
        
        # Create access token for moderator
        token = create_access_token(data={"sub": moderator.id})
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test fraud statistics endpoint
        response = client.get("/api/v1/moderation/fraud-stats", headers=headers)
        assert response.status_code == 200
        
        stats = response.json()
        assert "total_validations" in stats
        assert "flagged_validations" in stats
        assert "fraud_rate_percentage" in stats
    
    def test_moderation_queue_api_endpoints(self, client, test_data):
        """Test moderation queue API endpoints."""
        moderator = test_data["moderator_user"]
        
        # Create access token for moderator
        token = create_access_token(data={"sub": moderator.id})
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test moderation queue endpoint
        response = client.get("/api/v1/moderation/queue", headers=headers)
        assert response.status_code == 200
        
        queue = response.json()
        assert isinstance(queue, list)
        
        # Test moderation statistics endpoint
        response = client.get("/api/v1/moderation/stats", headers=headers)
        assert response.status_code == 200
        
        stats = response.json()
        assert "queue_size" in stats
        assert "pending_items" in stats
    
    def test_community_flagging_api_endpoint(self, client, test_data):
        """Test community flagging API endpoint."""
        regular_user = test_data["regular_user"]
        
        # Create access token for regular user
        token = create_access_token(data={"sub": regular_user.id})
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test flagging endpoint (would need actual validation ID)
        flag_data = {
            "reason": "Inappropriate content",
            "evidence": "Contains misleading information"
        }
        
        # This would fail with 404 since validation doesn't exist in API context
        # but tests the endpoint structure
        response = client.post(
            "/api/v1/moderation/flag/nonexistent_id",
            json=flag_data,
            headers=headers
        )
        # Expect 404 or 500, not 401/403 (authentication works)
        assert response.status_code in [404, 500]
    
    def test_unauthorized_access_to_moderation_endpoints(self, client, test_data):
        """Test that regular users can't access moderator-only endpoints."""
        regular_user = test_data["regular_user"]
        
        # Create access token for regular user
        token = create_access_token(data={"sub": regular_user.id})
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test moderator-only endpoints
        moderator_endpoints = [
            "/api/v1/moderation/analyze/test_id",
            "/api/v1/moderation/queue",
            "/api/v1/moderation/stats",
            "/api/v1/moderation/process-queue"
        ]
        
        for endpoint in moderator_endpoints:
            response = client.get(endpoint, headers=headers)
            # Should be forbidden (403) for regular users
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_fraud_detection_performance(self, db_session, test_data):
        """Test fraud detection system performance with multiple validations."""
        spam_user = test_data["spam_user"]
        opportunity = test_data["opportunity"]
        
        # Create multiple validations
        validations = []
        for i in range(20):
            validation = await validation_service.create_validation(
                db_session,
                opportunity_id=opportunity.id,
                validator_id=spam_user.id,
                validation_type=ValidationType.MARKET_DEMAND,
                score=5.0 + (i % 5),
                confidence=3.0 + (i % 3),
                comments=f"Validation comment {i} with some content",
                methodology="standard"
            )
            validations.append(validation)
        
        # Measure fraud detection performance
        start_time = datetime.utcnow()
        
        fraud_results_list = []
        for validation in validations[:10]:  # Test first 10
            results = await fraud_detection_service.analyze_validation_for_fraud(
                db_session, validation.id
            )
            fraud_results_list.append(results)
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        # Should process 10 validations in reasonable time (< 5 seconds)
        assert processing_time < 5.0
        
        # Should have analyzed all validations
        assert len(fraud_results_list) == 10
    
    @pytest.mark.asyncio
    async def test_fraud_detection_accuracy(self, db_session, test_data):
        """Test fraud detection accuracy with known good and bad validations."""
        regular_user = test_data["regular_user"]
        spam_user = test_data["spam_user"]
        opportunity = test_data["opportunity"]
        
        # Create good validation
        good_validation = await validation_service.create_validation(
            db_session,
            opportunity_id=opportunity.id,
            validator_id=regular_user.id,
            validation_type=ValidationType.MARKET_DEMAND,
            score=8.0,
            confidence=8.5,
            comments="This opportunity shows strong market demand based on comprehensive research including surveys, market analysis, and competitor evaluation.",
            strengths="Strong market signals, clear customer need, growing market",
            weaknesses="High competition, regulatory challenges",
            recommendations="Focus on differentiation and regulatory compliance",
            evidence_links='["https://example.com/research1", "https://example.com/research2"]',
            methodology="comprehensive_analysis",
            time_spent_minutes=120,
            expertise_relevance=7.5
        )
        
        # Create bad validation
        bad_validation = await validation_service.create_validation(
            db_session,
            opportunity_id=opportunity.id,
            validator_id=spam_user.id,
            validation_type=ValidationType.MARKET_DEMAND,
            score=3.0,
            confidence=1.0,
            comments="bad maybe not sure",
            methodology="guess",
            time_spent_minutes=2
        )
        
        # Analyze both validations
        good_results = await fraud_detection_service.analyze_validation_for_fraud(
            db_session, good_validation.id
        )
        bad_results = await fraud_detection_service.analyze_validation_for_fraud(
            db_session, bad_validation.id
        )
        
        # Good validation should have fewer/less severe fraud indicators
        good_fraud_count = len(good_results)
        bad_fraud_count = len(bad_results)
        
        # Bad validation should trigger more fraud detection
        assert bad_fraud_count >= good_fraud_count
        
        # If fraud detected in bad validation, should include quality issues
        if bad_results:
            quality_detected = any(r.fraud_type == FraudType.LOW_QUALITY_CONTENT for r in bad_results)
            assert quality_detected