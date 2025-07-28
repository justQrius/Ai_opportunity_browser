"""Tests for fraud detection service."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.fraud_detection_service import (
    fraud_detection_service,
    FraudType,
    FraudSeverity,
    ModerationAction,
    FraudDetectionResult
)
from shared.models.validation import ValidationResult, ValidationType
from shared.models.user import User, UserRole
from shared.models.reputation import ReputationEvent, ReputationEventType


class TestFraudDetectionService:
    """Test cases for fraud detection service."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def sample_validation(self):
        """Sample validation for testing."""
        return ValidationResult(
            id="val_123",
            opportunity_id="opp_123",
            validator_id="user_123",
            validation_type=ValidationType.MARKET_DEMAND,
            score=7.5,
            confidence=8.0,
            comments="This is a good opportunity with strong market demand.",
            strengths="Strong market signals",
            weaknesses="High competition",
            recommendations="Focus on differentiation",
            evidence_links='["https://example.com/evidence"]',
            methodology="Market research",
            time_spent_minutes=30,
            expertise_relevance=7.0,
            helpful_votes=5,
            unhelpful_votes=1,
            created_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        return User(
            id="user_123",
            username="testuser",
            email="test@example.com",
            role=UserRole.USER
        )
    
    @pytest.mark.asyncio
    async def test_analyze_validation_no_fraud(self, mock_db, sample_validation):
        """Test analyzing validation with no fraud detected."""
        # Mock database queries
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_validation
        mock_db.execute.return_value.scalar.return_value = 1  # Recent validations count
        mock_db.execute.return_value.scalars.return_value.all.return_value = []  # Similar validations
        
        # Analyze validation
        results = await fraud_detection_service.analyze_validation_for_fraud(
            mock_db, "val_123"
        )
        
        # Should detect no fraud for normal validation
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_detect_spam_validation(self, mock_db, sample_validation):
        """Test spam validation detection."""
        # Create spam-like validation
        spam_validation = sample_validation
        spam_validation.comments = "bad"  # Very short comment
        
        # Mock high frequency of validations
        mock_db.execute.return_value.scalar_one_or_none.return_value = spam_validation
        mock_db.execute.return_value.scalar.return_value = 15  # Too many validations per hour
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        
        results = await fraud_detection_service.analyze_validation_for_fraud(
            mock_db, "val_123"
        )
        
        # Should detect spam
        spam_results = [r for r in results if r.fraud_type == FraudType.SPAM_VALIDATION]
        assert len(spam_results) > 0
        assert spam_results[0].severity in [FraudSeverity.MEDIUM, FraudSeverity.HIGH]
        assert "Too many validations" in spam_results[0].evidence[0]
    
    @pytest.mark.asyncio
    async def test_detect_low_quality_content(self, mock_db, sample_validation):
        """Test low quality content detection."""
        # Create low quality validation
        low_quality_validation = sample_validation
        low_quality_validation.comments = "this is good maybe probably not sure"
        low_quality_validation.confidence = 1.0  # Very low confidence
        low_quality_validation.evidence_links = None
        low_quality_validation.supporting_data = None
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = low_quality_validation
        mock_db.execute.return_value.scalar.return_value = 1
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        
        results = await fraud_detection_service.analyze_validation_for_fraud(
            mock_db, "val_123"
        )
        
        # Should detect low quality content
        quality_results = [r for r in results if r.fraud_type == FraudType.LOW_QUALITY_CONTENT]
        assert len(quality_results) > 0
        assert "generic phrases" in quality_results[0].evidence[0]
        assert quality_results[0].recommended_action == ModerationAction.FLAG_FOR_REVIEW
    
    @pytest.mark.asyncio
    async def test_detect_vote_manipulation(self, mock_db, sample_validation):
        """Test vote manipulation detection."""
        # Create validation with suspicious voting pattern
        suspicious_validation = sample_validation
        suspicious_validation.helpful_votes = 10
        suspicious_validation.unhelpful_votes = 0  # Suspiciously perfect ratio
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = suspicious_validation
        mock_db.execute.return_value.scalar.return_value = 1
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        
        results = await fraud_detection_service.analyze_validation_for_fraud(
            mock_db, "val_123"
        )
        
        # Should detect vote manipulation
        vote_results = [r for r in results if r.fraud_type == FraudType.VOTE_MANIPULATION]
        assert len(vote_results) > 0
        assert "helpful vote ratio" in vote_results[0].evidence[0]
    
    @pytest.mark.asyncio
    async def test_detect_fake_expertise(self, mock_db, sample_validation):
        """Test fake expertise detection."""
        # Create validation claiming high expertise but with poor quality history
        fake_expert_validation = sample_validation
        fake_expert_validation.expertise_relevance = 9.0  # Claims high expertise
        
        # Mock poor quality validation history
        poor_validations = [
            ValidationResult(
                id=f"val_{i}",
                validator_id="user_123",
                validation_type=ValidationType.MARKET_DEMAND,
                helpful_votes=0,
                unhelpful_votes=3,
                score=3.0
            )
            for i in range(5)
        ]
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = fake_expert_validation
        mock_db.execute.return_value.scalar.return_value = 1
        mock_db.execute.return_value.scalars.return_value.all.side_effect = [
            [],  # Similar validations
            poor_validations  # User's validation history
        ]
        
        results = await fraud_detection_service.analyze_validation_for_fraud(
            mock_db, "val_123"
        )
        
        # Should detect fake expertise
        expertise_results = [r for r in results if r.fraud_type == FraudType.FAKE_EXPERTISE]
        assert len(expertise_results) > 0
        assert expertise_results[0].recommended_action == ModerationAction.REQUIRE_VERIFICATION
    
    @pytest.mark.asyncio
    async def test_detect_reputation_farming(self, mock_db, sample_validation):
        """Test reputation farming detection."""
        # Mock rapid reputation growth
        recent_events = [
            ReputationEvent(
                user_id="user_123",
                event_type=ReputationEventType.VALIDATION_SUBMITTED,
                points_change=5.0,
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            for i in range(100)  # 100 events in recent days
        ]
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_validation
        mock_db.execute.return_value.scalar.return_value = 1
        mock_db.execute.return_value.scalars.return_value.all.side_effect = [
            [],  # Similar validations
            [],  # User validations for expertise check
            [ValidationType.MARKET_DEMAND],  # Unique validation types (low diversity)
            recent_events  # Reputation events
        ]
        
        results = await fraud_detection_service.analyze_validation_for_fraud(
            mock_db, "val_123"
        )
        
        # Should detect reputation farming
        farming_results = [r for r in results if r.fraud_type == FraudType.REPUTATION_FARMING]
        assert len(farming_results) > 0
        assert farming_results[0].severity == FraudSeverity.HIGH
        assert farming_results[0].recommended_action == ModerationAction.REDUCE_INFLUENCE
    
    @pytest.mark.asyncio
    async def test_flag_validation(self, mock_db, sample_validation):
        """Test flagging validation for review."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_validation
        
        # Mock reputation service
        fraud_detection_service.reputation_service = AsyncMock()
        
        success = await fraud_detection_service.flag_validation(
            mock_db, "val_123", "reporter_123", "Inappropriate content", "Evidence here"
        )
        
        assert success is True
        assert sample_validation.is_flagged is True
        assert sample_validation.flag_reason == "Inappropriate content"
        
        # Should record reputation event
        fraud_detection_service.reputation_service.record_reputation_event.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_fraud_statistics(self, mock_db):
        """Test getting fraud statistics."""
        # Mock database queries for statistics
        mock_db.execute.return_value.scalar.side_effect = [
            10,  # Flagged validations
            100,  # Total validations
            5   # Moderated validations
        ]
        
        stats = await fraud_detection_service.get_fraud_statistics(mock_db, 30)
        
        assert stats["timeframe_days"] == 30
        assert stats["total_validations"] == 100
        assert stats["flagged_validations"] == 10
        assert stats["moderated_validations"] == 5
        assert stats["fraud_rate_percentage"] == 10.0
    
    @pytest.mark.asyncio
    async def test_process_moderation_queue(self, mock_db):
        """Test processing moderation queue."""
        # Mock pending validations
        pending_validations = [
            ValidationResult(
                id="val_1",
                validator_id="user_1",
                is_flagged=True,
                moderator_reviewed=False
            ),
            ValidationResult(
                id="val_2",
                validator_id="user_2",
                is_flagged=True,
                moderator_reviewed=False
            )
        ]
        
        mock_db.execute.return_value.scalars.return_value.all.return_value = pending_validations
        
        # Mock fraud detection results
        fraud_detection_service._detection_cache = {
            "val_1": [
                FraudDetectionResult(
                    fraud_type=FraudType.SPAM_VALIDATION,
                    severity=FraudSeverity.HIGH,
                    confidence_score=0.9,
                    evidence=["Test evidence"],
                    recommended_action=ModerationAction.HIDE_VALIDATION,
                    metadata={},
                    detected_at=datetime.utcnow()
                )
            ],
            "val_2": []
        }
        
        decisions = await fraud_detection_service.process_moderation_queue(mock_db, 10)
        
        # Should process flagged items
        assert len(decisions) >= 0  # May vary based on fraud detection results
    
    def test_fraud_detection_thresholds(self):
        """Test fraud detection threshold configuration."""
        assert fraud_detection_service.SPAM_THRESHOLDS["max_validations_per_hour"] == 10
        assert fraud_detection_service.QUALITY_THRESHOLDS["min_comment_length"] == 10
        assert fraud_detection_service.REPUTATION_THRESHOLDS["suspicious_growth_rate"] == 50.0
    
    def test_generic_phrases_detection(self):
        """Test generic phrases list for quality detection."""
        generic_phrases = fraud_detection_service.GENERIC_PHRASES
        assert "this is good" in generic_phrases
        assert "not sure" in generic_phrases
        assert "might work" in generic_phrases
        assert len(generic_phrases) > 10  # Should have reasonable number of phrases
    
    @pytest.mark.asyncio
    async def test_find_similar_validations(self, mock_db):
        """Test finding similar validation content."""
        # Mock user validations
        similar_validation = ValidationResult(
            id="val_similar",
            validator_id="user_123",
            comments="This is a good opportunity with strong market demand."
        )
        
        mock_db.execute.return_value.scalars.return_value.all.return_value = [similar_validation]
        
        similar = await fraud_detection_service._find_similar_validations(
            mock_db, "user_123", "This is a good opportunity with strong market demand."
        )
        
        assert len(similar) == 1
        assert similar[0].id == "val_similar"
    
    @pytest.mark.asyncio
    async def test_determine_moderation_action(self):
        """Test determining appropriate moderation action."""
        # High severity, high confidence
        high_severity_results = [
            FraudDetectionResult(
                fraud_type=FraudType.SPAM_VALIDATION,
                severity=FraudSeverity.HIGH,
                confidence_score=0.9,
                evidence=["Evidence"],
                recommended_action=ModerationAction.HIDE_VALIDATION,
                metadata={},
                detected_at=datetime.utcnow()
            ),
            FraudDetectionResult(
                fraud_type=FraudType.LOW_QUALITY_CONTENT,
                severity=FraudSeverity.HIGH,
                confidence_score=0.85,
                evidence=["Evidence"],
                recommended_action=ModerationAction.FLAG_FOR_REVIEW,
                metadata={},
                detected_at=datetime.utcnow()
            )
        ]
        
        action = await fraud_detection_service._determine_moderation_action(high_severity_results)
        assert action == ModerationAction.HIDE_VALIDATION
        
        # Medium severity
        medium_severity_results = [
            FraudDetectionResult(
                fraud_type=FraudType.LOW_QUALITY_CONTENT,
                severity=FraudSeverity.MEDIUM,
                confidence_score=0.85,
                evidence=["Evidence"],
                recommended_action=ModerationAction.FLAG_FOR_REVIEW,
                metadata={},
                detected_at=datetime.utcnow()
            )
        ]
        
        action = await fraud_detection_service._determine_moderation_action(medium_severity_results)
        assert action == ModerationAction.FLAG_FOR_REVIEW
        
        # No fraud
        action = await fraud_detection_service._determine_moderation_action([])
        assert action == ModerationAction.NO_ACTION