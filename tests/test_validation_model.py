"""Tests for ValidationResult model and service."""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, Mock

from shared.models.validation import ValidationResult, ValidationType
from shared.models.user import User, UserRole
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.schemas.validation import ValidationCreate, ValidationUpdate, ValidationVote, ValidationFlag
from shared.services.validation_service import ValidationService


class TestValidationModel:
    """Test ValidationResult model functionality."""
    
    def test_validation_model_creation(self):
        """Test ValidationResult model instance creation."""
        validation = ValidationResult(
            opportunity_id="opp-123",
            validator_id="user-456",
            validation_type=ValidationType.MARKET_DEMAND,
            score=8.5,
            confidence=7.0,
            comments="Strong market demand based on user feedback"
        )
        
        assert validation.opportunity_id == "opp-123"
        assert validation.validator_id == "user-456"
        assert validation.validation_type == ValidationType.MARKET_DEMAND
        assert validation.score == 8.5
        assert validation.confidence == 7.0
        assert validation.helpful_votes == 0  # Default value
        assert validation.is_flagged is False  # Default value
    
    def test_validation_type_enum(self):
        """Test validation type enumeration."""
        assert ValidationType.MARKET_DEMAND == "market_demand"
        assert ValidationType.TECHNICAL_FEASIBILITY == "technical_feasibility"
        assert ValidationType.BUSINESS_VIABILITY == "business_viability"
        assert ValidationType.COMPETITIVE_ANALYSIS == "competitive_analysis"
        assert ValidationType.IMPLEMENTATION_COMPLEXITY == "implementation_complexity"
    
    def test_validation_repr(self):
        """Test ValidationResult string representation."""
        validation = ValidationResult(
            id="test-id",
            opportunity_id="opp-123",
            validator_id="user-456",
            validation_type=ValidationType.TECHNICAL_FEASIBILITY,
            score=7.5
        )
        
        repr_str = repr(validation)
        assert "technical_feasibility" in repr_str
        assert "7.5" in repr_str


class TestValidationService:
    """Test ValidationService functionality."""
    
    @pytest.fixture
    def validation_service(self):
        """Create ValidationService instance."""
        return ValidationService()
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def sample_validation_create(self):
        """Sample validation creation data."""
        return ValidationCreate(
            opportunity_id="opp-123",
            validation_type=ValidationType.MARKET_DEMAND,
            score=8.5,
            confidence=7.5,
            comments="Strong market demand evidenced by high engagement on social media and forums",
            strengths="Clear pain point, large addressable market, existing user demand",
            weaknesses="Competitive landscape, implementation complexity",
            recommendations="Focus on MVP, validate with pilot customers",
            evidence_links=["https://reddit.com/r/MachineLearning/post1", "https://github.com/issues/123"],
            methodology="Social media analysis and expert interviews",
            time_spent_minutes=45,
            supporting_data={"engagement_metrics": {"upvotes": 150, "comments": 45}}
        )
    
    @pytest.fixture
    def mock_opportunity(self):
        """Mock opportunity."""
        return Opportunity(
            id="opp-123",
            title="AI-Powered Document Analysis",
            description="Automated document processing",
            ai_solution_types='["nlp", "computer_vision"]',
            target_industries='["legal", "healthcare"]',
            status=OpportunityStatus.VALIDATING
        )
    
    @pytest.fixture
    def mock_validator(self):
        """Mock validator user."""
        return User(
            id="user-456",
            username="expert_validator",
            email="expert@example.com",
            hashed_password="hash",
            role=UserRole.EXPERT,
            is_active=True,
            reputation_score=8.5,
            expertise_domains='["nlp", "legal_tech", "document_processing"]'
        )
    
    @pytest.mark.asyncio
    async def test_create_validation(self, validation_service, mock_db_session, sample_validation_create, mock_opportunity, mock_validator):
        """Test validation creation."""
        # Mock database operations
        mock_db_session.add = AsyncMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        
        with patch('shared.services.validation_service.opportunity_service') as mock_opp_service, \
             patch('shared.services.validation_service.user_service') as mock_user_service, \
             patch.object(validation_service, '_get_existing_validation', return_value=None), \
             patch.object(validation_service, '_calculate_expertise_relevance', return_value=9.0), \
             patch.object(validation_service, '_clear_validation_caches', return_value=None):
            
            mock_opp_service.get_opportunity_by_id.return_value = mock_opportunity
            mock_user_service.get_user_by_id.return_value = mock_validator
            mock_opp_service.update_validation_scores = AsyncMock()
            mock_user_service.update_user_reputation = AsyncMock()
            
            validation = await validation_service.create_validation(
                mock_db_session, sample_validation_create, "user-456"
            )
            
            assert validation.opportunity_id == sample_validation_create.opportunity_id
            assert validation.validator_id == "user-456"
            assert validation.validation_type == sample_validation_create.validation_type
            assert validation.score == sample_validation_create.score
            assert validation.expertise_relevance == 9.0
            
            # Verify JSON fields are properly serialized
            assert validation.evidence_links is not None
            assert validation.supporting_data is not None
            
            # Verify downstream updates were triggered
            mock_opp_service.update_validation_scores.assert_called_once()
            mock_user_service.update_user_reputation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_validation_duplicate_prevention(self, validation_service, mock_db_session, sample_validation_create, mock_opportunity, mock_validator):
        """Test prevention of duplicate validations."""
        # Mock existing validation
        existing_validation = ValidationResult(
            id="existing-123",
            opportunity_id="opp-123",
            validator_id="user-456",
            validation_type=ValidationType.MARKET_DEMAND,
            score=7.0
        )
        
        with patch('shared.services.validation_service.opportunity_service') as mock_opp_service, \
             patch('shared.services.validation_service.user_service') as mock_user_service, \
             patch.object(validation_service, '_get_existing_validation', return_value=existing_validation):
            
            mock_opp_service.get_opportunity_by_id.return_value = mock_opportunity
            mock_user_service.get_user_by_id.return_value = mock_validator
            
            with pytest.raises(ValueError, match="already provided"):
                await validation_service.create_validation(
                    mock_db_session, sample_validation_create, "user-456"
                )
    
    @pytest.mark.asyncio
    async def test_get_validation_by_id(self, validation_service, mock_db_session):
        """Test getting validation by ID."""
        validation_id = "validation-123"
        
        # Mock database result
        mock_validation = ValidationResult(
            id=validation_id,
            opportunity_id="opp-123",
            validator_id="user-456",
            validation_type=ValidationType.TECHNICAL_FEASIBILITY,
            score=7.5
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_validation
        mock_db_session.execute.return_value = mock_result
        
        validation = await validation_service.get_validation_by_id(mock_db_session, validation_id)
        
        assert validation is not None
        assert validation.id == validation_id
        assert validation.validation_type == ValidationType.TECHNICAL_FEASIBILITY
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_validation(self, validation_service, mock_db_session):
        """Test validation update."""
        validation_id = "validation-123"
        validator_id = "user-456"
        
        # Mock existing validation
        existing_validation = ValidationResult(
            id=validation_id,
            opportunity_id="opp-123",
            validator_id=validator_id,
            validation_type=ValidationType.MARKET_DEMAND,
            score=7.0,
            comments="Original comments"
        )
        
        update_data = ValidationUpdate(
            score=8.5,
            comments="Updated comments with more evidence",
            evidence_links=["https://newevidence.com/link1"],
            supporting_data={"updated": "data"}
        )
        
        with patch.object(validation_service, 'get_validation_by_id', return_value=existing_validation), \
             patch.object(validation_service, '_clear_validation_caches', return_value=None), \
             patch('shared.services.validation_service.opportunity_service') as mock_opp_service:
            
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()
            mock_opp_service.update_validation_scores = AsyncMock()
            
            updated_validation = await validation_service.update_validation(
                mock_db_session, validation_id, update_data, validator_id
            )
            
            assert updated_validation is not None
            assert updated_validation.score == 8.5
            assert updated_validation.comments == "Updated comments with more evidence"
            mock_opp_service.update_validation_scores.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_validation_unauthorized(self, validation_service, mock_db_session):
        """Test validation update by unauthorized user."""
        validation_id = "validation-123"
        
        # Mock existing validation with different validator
        existing_validation = ValidationResult(
            id=validation_id,
            opportunity_id="opp-123",
            validator_id="original-validator",
            validation_type=ValidationType.MARKET_DEMAND,
            score=7.0
        )
        
        update_data = ValidationUpdate(score=8.5)
        
        with patch.object(validation_service, 'get_validation_by_id', return_value=existing_validation):
            with pytest.raises(ValueError, match="Only the original validator"):
                await validation_service.update_validation(
                    mock_db_session, validation_id, update_data, "different-user"
                )
    
    @pytest.mark.asyncio
    async def test_get_opportunity_validations(self, validation_service, mock_db_session):
        """Test getting all validations for an opportunity."""
        opportunity_id = "opp-123"
        
        # Mock validations
        mock_validations = [
            ValidationResult(
                id="val1",
                opportunity_id=opportunity_id,
                validator_id="user1",
                validation_type=ValidationType.MARKET_DEMAND,
                score=8.5
            ),
            ValidationResult(
                id="val2",
                opportunity_id=opportunity_id,
                validator_id="user2",
                validation_type=ValidationType.TECHNICAL_FEASIBILITY,
                score=7.0
            )
        ]
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_validations
        mock_db_session.execute.return_value = mock_result
        
        validations = await validation_service.get_opportunity_validations(
            mock_db_session, opportunity_id
        )
        
        assert len(validations) == 2
        assert validations[0].validation_type == ValidationType.MARKET_DEMAND
        assert validations[1].score == 7.0
    
    @pytest.mark.asyncio
    async def test_vote_on_validation(self, validation_service, mock_db_session):
        """Test voting on validation helpfulness."""
        validation_id = "validation-123"
        voter_id = "voter-456"
        
        # Mock validation
        mock_validation = ValidationResult(
            id=validation_id,
            opportunity_id="opp-123",
            validator_id="different-user",  # Different from voter
            validation_type=ValidationType.MARKET_DEMAND,
            score=8.0,
            helpful_votes=5,
            unhelpful_votes=1
        )
        
        vote_data = ValidationVote(
            validation_id=validation_id,
            is_helpful=True
        )
        
        with patch.object(validation_service, 'get_validation_by_id', return_value=mock_validation), \
             patch('shared.services.validation_service.user_service') as mock_user_service:
            
            mock_db_session.commit = AsyncMock()
            mock_user_service.update_user_reputation = AsyncMock()
            
            result = await validation_service.vote_on_validation(
                mock_db_session, vote_data, voter_id
            )
            
            assert result is True
            assert mock_validation.helpful_votes == 6  # Incremented
            assert mock_validation.unhelpful_votes == 1  # Unchanged
            mock_user_service.update_user_reputation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_vote_on_own_validation_prevented(self, validation_service, mock_db_session):
        """Test prevention of self-voting."""
        validation_id = "validation-123"
        validator_id = "user-456"
        
        # Mock validation where validator and voter are the same
        mock_validation = ValidationResult(
            id=validation_id,
            opportunity_id="opp-123",
            validator_id=validator_id,  # Same as voter
            validation_type=ValidationType.MARKET_DEMAND,
            score=8.0
        )
        
        vote_data = ValidationVote(
            validation_id=validation_id,
            is_helpful=True
        )
        
        with patch.object(validation_service, 'get_validation_by_id', return_value=mock_validation):
            with pytest.raises(ValueError, match="Cannot vote on your own validation"):
                await validation_service.vote_on_validation(
                    mock_db_session, vote_data, validator_id
                )
    
    @pytest.mark.asyncio
    async def test_flag_validation(self, validation_service, mock_db_session):
        """Test flagging validation for quality issues."""
        validation_id = "validation-123"
        flagger_id = "flagger-456"
        
        # Mock validation
        mock_validation = ValidationResult(
            id=validation_id,
            opportunity_id="opp-123",
            validator_id="validator-789",
            validation_type=ValidationType.MARKET_DEMAND,
            score=8.0,
            is_flagged=False
        )
        
        # Mock flagger with sufficient reputation
        mock_flagger = User(
            id=flagger_id,
            username="flagger",
            email="flagger@example.com",
            hashed_password="hash",
            reputation_score=5.0  # Above 2.0 threshold
        )
        
        flag_data = ValidationFlag(
            validation_id=validation_id,
            reason="Inappropriate content",
            details="Contains offensive language"
        )
        
        with patch.object(validation_service, 'get_validation_by_id', return_value=mock_validation), \
             patch('shared.services.validation_service.user_service') as mock_user_service:
            
            mock_user_service.get_user_by_id.return_value = mock_flagger
            mock_db_session.commit = AsyncMock()
            
            result = await validation_service.flag_validation(
                mock_db_session, flag_data, flagger_id
            )
            
            assert result is True
            assert mock_validation.is_flagged is True
            assert mock_validation.flag_reason == "Inappropriate content"
    
    @pytest.mark.asyncio
    async def test_flag_validation_insufficient_reputation(self, validation_service, mock_db_session):
        """Test flagging prevention for low reputation users."""
        validation_id = "validation-123"
        flagger_id = "flagger-456"
        
        # Mock validation
        mock_validation = ValidationResult(
            id=validation_id,
            opportunity_id="opp-123",
            validator_id="validator-789",
            validation_type=ValidationType.MARKET_DEMAND,
            score=8.0
        )
        
        # Mock flagger with insufficient reputation
        mock_flagger = User(
            id=flagger_id,
            username="flagger",
            email="flagger@example.com",
            hashed_password="hash",
            reputation_score=1.5  # Below 2.0 threshold
        )
        
        flag_data = ValidationFlag(
            validation_id=validation_id,
            reason="Inappropriate content"
        )
        
        with patch.object(validation_service, 'get_validation_by_id', return_value=mock_validation), \
             patch('shared.services.validation_service.user_service') as mock_user_service:
            
            mock_user_service.get_user_by_id.return_value = mock_flagger
            
            with pytest.raises(ValueError, match="Insufficient reputation"):
                await validation_service.flag_validation(
                    mock_db_session, flag_data, flagger_id
                )
    
    @pytest.mark.asyncio
    async def test_get_validation_summary(self, validation_service, mock_db_session):
        """Test comprehensive validation summary generation."""
        opportunity_id = "opp-123"
        
        # Mock validations
        mock_validations = [
            ValidationResult(
                id="val1",
                opportunity_id=opportunity_id,
                validator_id="user1",
                validation_type=ValidationType.MARKET_DEMAND,
                score=8.5,
                strengths="Strong market demand",
                weaknesses="High competition",
                recommendations="Focus on niche market",
                evidence_links='["https://evidence1.com"]',
                helpful_votes=10,
                unhelpful_votes=1
            ),
            ValidationResult(
                id="val2",
                opportunity_id=opportunity_id,
                validator_id="user2",
                validation_type=ValidationType.TECHNICAL_FEASIBILITY,
                score=7.0,
                strengths="Feasible with current tech",
                weaknesses="Requires significant resources",
                recommendations="Start with MVP",
                helpful_votes=5,
                unhelpful_votes=2
            )
        ]
        
        with patch.object(validation_service, 'get_opportunity_validations', return_value=mock_validations), \
             patch('shared.services.validation_service.user_service') as mock_user_service:
            
            # Mock user influence weights
            mock_user_service.get_user_influence_weight.side_effect = [1.2, 1.0]
            
            summary = await validation_service.get_validation_summary(
                mock_db_session, opportunity_id
            )
            
            assert summary.opportunity_id == opportunity_id
            assert summary.total_validations == 2
            assert summary.average_score > 0
            assert summary.confidence_rating >= 0
            assert len(summary.validations_by_type) > 0
            assert len(summary.consensus_strengths) > 0
            assert summary.validation_quality_score > 0
    
    @pytest.mark.asyncio
    async def test_calculate_expertise_relevance(self, validation_service, mock_db_session):
        """Test expertise relevance calculation."""
        # Mock validator with relevant expertise
        validator = User(
            id="user-456",
            username="expert",
            email="expert@example.com",
            hashed_password="hash",
            role=UserRole.EXPERT,
            expertise_domains='["nlp", "legal_tech", "document_processing"]'
        )
        
        # Mock opportunity with matching domains
        opportunity = Opportunity(
            id="opp-123",
            title="Legal Document AI",
            description="AI for legal documents",
            ai_solution_types='["nlp", "text_analysis"]',
            target_industries='["legal", "compliance"]'
        )
        
        relevance = await validation_service._calculate_expertise_relevance(
            mock_db_session, validator, opportunity
        )
        
        # Should be high relevance due to matching domains
        assert relevance > 7.0
        assert relevance <= 10.0
    
    @pytest.mark.asyncio
    async def test_get_validation_analytics(self, validation_service, mock_db_session):
        """Test validation analytics generation."""
        # Mock database queries for analytics
        mock_total_count = AsyncMock()
        mock_total_count.scalar.return_value = 100
        
        mock_type_stats = [
            Mock(validation_type=ValidationType.MARKET_DEMAND, count=40),
            Mock(validation_type=ValidationType.TECHNICAL_FEASIBILITY, count=35),
            Mock(validation_type=ValidationType.BUSINESS_VIABILITY, count=25)
        ]
        
        mock_avg_stats = Mock(avg_score=7.8, avg_confidence=7.2)
        
        mock_top_validators = [
            Mock(username="expert1", validation_count=15, avg_score=8.5),
            Mock(username="expert2", validation_count=12, avg_score=8.2)
        ]
        
        # Mock database execution sequence
        mock_db_session.execute.side_effect = [
            mock_total_count,
            mock_type_stats,
            AsyncMock(first=lambda: mock_avg_stats),
            mock_top_validators
        ]
        
        analytics = await validation_service.get_validation_analytics(
            mock_db_session, timeframe_days=30
        )
        
        assert analytics["total_validations"] == 100
        assert analytics["validations_by_type"]["market_demand"] == 40
        assert analytics["average_score"] == 7.8
        assert analytics["average_confidence"] == 7.2
        assert len(analytics["top_validators"]) == 2
        assert analytics["top_validators"][0]["username"] == "expert1"
        assert analytics["timeframe_days"] == 30
        assert "generated_at" in analytics