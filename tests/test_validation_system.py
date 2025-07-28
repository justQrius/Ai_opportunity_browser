"""Tests for ValidationSystem core functionality."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, Mock

from shared.services.validation_system import (
    ValidationSystem,
    ValidationWorkflow,
    ValidationWorkflowStatus,
    ValidationPriority,
    ValidationConsensus
)
from shared.models.validation import ValidationResult, ValidationType
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.user import User, UserRole


class TestValidationWorkflow:
    """Test ValidationWorkflow dataclass functionality."""
    
    def test_validation_workflow_creation(self):
        """Test ValidationWorkflow creation and properties."""
        now = datetime.utcnow()
        workflow = ValidationWorkflow(
            opportunity_id="opp-123",
            status=ValidationWorkflowStatus.PENDING,
            priority=ValidationPriority.HIGH,
            required_validation_types={ValidationType.MARKET_DEMAND, ValidationType.TECHNICAL_FEASIBILITY},
            completed_validation_types={ValidationType.MARKET_DEMAND},
            target_validator_count=5,
            current_validator_count=2,
            min_expert_validations=2,
            current_expert_validations=1,
            deadline=now + timedelta(days=7),
            created_at=now,
            updated_at=now
        )
        
        assert workflow.opportunity_id == "opp-123"
        assert workflow.status == ValidationWorkflowStatus.PENDING
        assert workflow.priority == ValidationPriority.HIGH
        assert workflow.completion_percentage == 50.0  # 1 of 2 types completed
        assert workflow.is_complete is False  # Not all requirements met
    
    def test_validation_workflow_completion_check(self):
        """Test workflow completion logic."""
        now = datetime.utcnow()
        
        # Complete workflow
        complete_workflow = ValidationWorkflow(
            opportunity_id="opp-123",
            status=ValidationWorkflowStatus.IN_PROGRESS,
            priority=ValidationPriority.NORMAL,
            required_validation_types={ValidationType.MARKET_DEMAND, ValidationType.TECHNICAL_FEASIBILITY},
            completed_validation_types={ValidationType.MARKET_DEMAND, ValidationType.TECHNICAL_FEASIBILITY},
            target_validator_count=3,
            current_validator_count=3,
            min_expert_validations=1,
            current_expert_validations=1,
            deadline=None,
            created_at=now,
            updated_at=now
        )
        
        assert complete_workflow.completion_percentage == 100.0
        assert complete_workflow.is_complete is True
        
        # Incomplete workflow (missing expert validations)
        incomplete_workflow = ValidationWorkflow(
            opportunity_id="opp-456",
            status=ValidationWorkflowStatus.IN_PROGRESS,
            priority=ValidationPriority.NORMAL,
            required_validation_types={ValidationType.MARKET_DEMAND},
            completed_validation_types={ValidationType.MARKET_DEMAND},
            target_validator_count=3,
            current_validator_count=3,
            min_expert_validations=2,
            current_expert_validations=0,  # Missing expert validations
            deadline=None,
            created_at=now,
            updated_at=now
        )
        
        assert incomplete_workflow.completion_percentage == 100.0  # Types complete
        assert incomplete_workflow.is_complete is False  # But missing expert validations


class TestValidationConsensus:
    """Test ValidationConsensus dataclass functionality."""
    
    def test_validation_consensus_creation(self):
        """Test ValidationConsensus creation."""
        consensus = ValidationConsensus(
            opportunity_id="opp-123",
            consensus_score=7.5,
            confidence_level=8.2,
            agreement_ratio=0.85,
            outlier_count=1,
            quality_score=7.8,
            recommendation="Strong validation - proceed with development",
            supporting_evidence_count=12,
            expert_consensus=8.0,
            community_consensus=7.2
        )
        
        assert consensus.opportunity_id == "opp-123"
        assert consensus.consensus_score == 7.5
        assert consensus.confidence_level == 8.2
        assert consensus.agreement_ratio == 0.85
        assert consensus.outlier_count == 1
        assert "Strong validation" in consensus.recommendation


class TestValidationSystem:
    """Test ValidationSystem core functionality."""
    
    @pytest.fixture
    def validation_system(self):
        """Create ValidationSystem instance."""
        return ValidationSystem()
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_opportunity(self):
        """Mock opportunity."""
        return Opportunity(
            id="opp-123",
            title="AI Document Analysis",
            description="Automated document processing",
            status=OpportunityStatus.DISCOVERED
        )
    
    @pytest.fixture
    def mock_validations(self):
        """Mock validation results."""
        return [
            ValidationResult(
                id="val-1",
                opportunity_id="opp-123",
                validator_id="user-1",
                validation_type=ValidationType.MARKET_DEMAND,
                score=8.5,
                confidence=8.0,
                evidence_links='["https://evidence1.com"]',
                strengths="Strong market demand",
                weaknesses="High competition",
                recommendations="Focus on niche",
                helpful_votes=10,
                unhelpful_votes=1,
                expertise_relevance=9.0
            ),
            ValidationResult(
                id="val-2",
                opportunity_id="opp-123",
                validator_id="user-2",
                validation_type=ValidationType.TECHNICAL_FEASIBILITY,
                score=7.0,
                confidence=7.5,
                evidence_links='["https://evidence2.com", "https://evidence3.com"]',
                strengths="Technically feasible",
                weaknesses="Complex implementation",
                recommendations="Start with MVP",
                helpful_votes=5,
                unhelpful_votes=2,
                expertise_relevance=8.5
            ),
            ValidationResult(
                id="val-3",
                opportunity_id="opp-123",
                validator_id="user-3",
                validation_type=ValidationType.BUSINESS_VIABILITY,
                score=6.5,
                confidence=6.0,
                strengths="Good business model",
                weaknesses="Uncertain ROI",
                recommendations="Validate pricing",
                helpful_votes=3,
                unhelpful_votes=1,
                expertise_relevance=7.0
            )
        ]
    
    @pytest.fixture
    def mock_users(self):
        """Mock users with different roles."""
        return {
            "user-1": User(
                id="user-1",
                username="expert1",
                email="expert1@example.com",
                hashed_password="hash",
                role=UserRole.EXPERT,
                reputation_score=9.0
            ),
            "user-2": User(
                id="user-2",
                username="expert2",
                email="expert2@example.com",
                hashed_password="hash",
                role=UserRole.EXPERT,
                reputation_score=8.5
            ),
            "user-3": User(
                id="user-3",
                username="user3",
                email="user3@example.com",
                hashed_password="hash",
                role=UserRole.USER,
                reputation_score=6.0
            )
        }
    
    @pytest.mark.asyncio
    async def test_initiate_validation_workflow(self, validation_system, mock_db_session, mock_opportunity):
        """Test validation workflow initiation."""
        with patch('shared.services.validation_system.opportunity_service') as mock_opp_service, \
             patch('shared.services.validation_system.validation_service') as mock_val_service, \
             patch('shared.services.validation_system.user_service') as mock_user_service:
            
            mock_opp_service.get_opportunity_by_id = AsyncMock(return_value=mock_opportunity)
            mock_val_service.get_opportunity_validations = AsyncMock(return_value=[])
            mock_db_session.commit = AsyncMock()
            
            workflow = await validation_system.initiate_validation_workflow(
                mock_db_session,
                "opp-123",
                priority=ValidationPriority.HIGH,
                target_validator_count=5,
                min_expert_validations=2
            )
            
            assert workflow.opportunity_id == "opp-123"
            assert workflow.status == ValidationWorkflowStatus.PENDING
            assert workflow.priority == ValidationPriority.HIGH
            assert workflow.target_validator_count == 5
            assert workflow.min_expert_validations == 2
            assert len(workflow.required_validation_types) == 3  # Default types
            assert workflow.current_validator_count == 0
            assert workflow.completion_percentage == 0.0
            
            # Verify opportunity status was updated
            assert mock_opportunity.status == OpportunityStatus.VALIDATING
    
    @pytest.mark.asyncio
    async def test_initiate_workflow_with_existing_validations(self, validation_system, mock_db_session, mock_opportunity, mock_validations, mock_users):
        """Test workflow initiation with existing validations."""
        with patch('shared.services.validation_system.opportunity_service') as mock_opp_service, \
             patch('shared.services.validation_system.validation_service') as mock_val_service, \
             patch('shared.services.validation_system.user_service') as mock_user_service:
            
            mock_opp_service.get_opportunity_by_id = AsyncMock(return_value=mock_opportunity)
            mock_val_service.get_opportunity_validations = AsyncMock(return_value=mock_validations)
            mock_user_service.get_user_by_id = AsyncMock(side_effect=lambda db, user_id: mock_users.get(user_id))
            mock_db_session.commit = AsyncMock()
            
            workflow = await validation_system.initiate_validation_workflow(
                mock_db_session,
                "opp-123",
                target_validator_count=5,
                min_expert_validations=2
            )
            
            assert workflow.current_validator_count == 3  # Existing validations
            assert workflow.current_expert_validations == 2  # Two experts
            assert len(workflow.completed_validation_types) == 3  # All types covered
            assert workflow.completion_percentage == 100.0  # Types complete
    
    @pytest.mark.asyncio
    async def test_update_validation_workflow(self, validation_system, mock_db_session, mock_users):
        """Test workflow update when new validation is added."""
        # Create initial workflow
        now = datetime.utcnow()
        workflow = ValidationWorkflow(
            opportunity_id="opp-123",
            status=ValidationWorkflowStatus.IN_PROGRESS,
            priority=ValidationPriority.NORMAL,
            required_validation_types={ValidationType.MARKET_DEMAND, ValidationType.TECHNICAL_FEASIBILITY},
            completed_validation_types={ValidationType.MARKET_DEMAND},
            target_validator_count=3,
            current_validator_count=1,
            min_expert_validations=1,
            current_expert_validations=0,
            deadline=None,
            created_at=now,
            updated_at=now
        )
        
        # Store workflow
        validation_system._active_workflows["opp-123"] = workflow
        
        # Create new validation
        new_validation = ValidationResult(
            id="val-new",
            opportunity_id="opp-123",
            validator_id="user-1",
            validation_type=ValidationType.TECHNICAL_FEASIBILITY,
            score=8.0
        )
        
        with patch('shared.services.validation_system.user_service') as mock_user_service:
            mock_user_service.get_user_by_id = AsyncMock(return_value=mock_users["user-1"])  # Expert user
            
            updated_workflow = await validation_system.update_validation_workflow(
                mock_db_session, "opp-123", new_validation
            )
            
            assert updated_workflow is not None
            assert ValidationType.TECHNICAL_FEASIBILITY in updated_workflow.completed_validation_types
            assert updated_workflow.current_validator_count == 2
            assert updated_workflow.current_expert_validations == 1
            assert updated_workflow.updated_at > now
    
    @pytest.mark.asyncio
    async def test_get_active_workflows(self, validation_system):
        """Test getting active workflows with filters."""
        now = datetime.utcnow()
        
        # Create test workflows
        workflows = [
            ValidationWorkflow(
                opportunity_id="opp-1",
                status=ValidationWorkflowStatus.PENDING,
                priority=ValidationPriority.HIGH,
                required_validation_types={ValidationType.MARKET_DEMAND},
                completed_validation_types=set(),
                target_validator_count=3,
                current_validator_count=0,
                min_expert_validations=1,
                current_expert_validations=0,
                deadline=None,
                created_at=now,
                updated_at=now
            ),
            ValidationWorkflow(
                opportunity_id="opp-2",
                status=ValidationWorkflowStatus.IN_PROGRESS,
                priority=ValidationPriority.NORMAL,
                required_validation_types={ValidationType.MARKET_DEMAND},
                completed_validation_types=set(),
                target_validator_count=3,
                current_validator_count=1,
                min_expert_validations=1,
                current_expert_validations=0,
                deadline=None,
                created_at=now + timedelta(minutes=1),
                updated_at=now + timedelta(minutes=1)
            ),
            ValidationWorkflow(
                opportunity_id="opp-3",
                status=ValidationWorkflowStatus.PENDING,
                priority=ValidationPriority.URGENT,
                required_validation_types={ValidationType.MARKET_DEMAND},
                completed_validation_types=set(),
                target_validator_count=3,
                current_validator_count=0,
                min_expert_validations=1,
                current_expert_validations=0,
                deadline=None,
                created_at=now + timedelta(minutes=2),
                updated_at=now + timedelta(minutes=2)
            )
        ]
        
        # Store workflows
        for workflow in workflows:
            validation_system._active_workflows[workflow.opportunity_id] = workflow
        
        # Test getting all workflows
        all_workflows = await validation_system.get_active_workflows()
        assert len(all_workflows) == 3
        
        # Test priority filter
        high_priority = await validation_system.get_active_workflows(priority=ValidationPriority.HIGH)
        assert len(high_priority) == 1
        assert high_priority[0].opportunity_id == "opp-1"
        
        # Test status filter
        pending_workflows = await validation_system.get_active_workflows(status=ValidationWorkflowStatus.PENDING)
        assert len(pending_workflows) == 2
        
        # Test priority ordering (URGENT should come first)
        assert all_workflows[0].priority == ValidationPriority.URGENT
        assert all_workflows[0].opportunity_id == "opp-3"
    
    @pytest.mark.asyncio
    async def test_analyze_validation_consensus(self, validation_system, mock_db_session, mock_validations, mock_users):
        """Test validation consensus analysis."""
        with patch('shared.services.validation_system.validation_service') as mock_val_service, \
             patch('shared.services.validation_system.user_service') as mock_user_service:
            
            mock_val_service.get_opportunity_validations = AsyncMock(return_value=mock_validations)
            mock_user_service.get_user_by_id = AsyncMock(side_effect=lambda db, user_id: mock_users.get(user_id))
            mock_user_service.get_user_influence_weight = AsyncMock(side_effect=lambda db, user_id: {
                "user-1": 1.2,  # Expert with high influence
                "user-2": 1.1,  # Expert with good influence
                "user-3": 0.8   # Regular user
            }.get(user_id, 1.0))
            
            consensus = await validation_system.analyze_validation_consensus(
                mock_db_session, "opp-123"
            )
            
            assert consensus.opportunity_id == "opp-123"
            assert consensus.consensus_score > 0
            assert consensus.confidence_level > 0
            assert consensus.agreement_ratio >= 0
            assert consensus.supporting_evidence_count == 3  # Total evidence links
            assert consensus.expert_consensus > 0  # Should have expert consensus
            assert consensus.community_consensus > 0  # Should have community consensus
            assert len(consensus.recommendation) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_consensus_no_validations(self, validation_system, mock_db_session):
        """Test consensus analysis with no validations."""
        with patch('shared.services.validation_system.validation_service') as mock_val_service:
            mock_val_service.get_opportunity_validations = AsyncMock(return_value=[])
            
            consensus = await validation_system.analyze_validation_consensus(
                mock_db_session, "opp-empty"
            )
            
            assert consensus.opportunity_id == "opp-empty"
            assert consensus.consensus_score == 0.0
            assert consensus.confidence_level == 0.0
            assert consensus.agreement_ratio == 0.0
            assert consensus.outlier_count == 0
            assert consensus.supporting_evidence_count == 0
            assert "No validations available" in consensus.recommendation
    
    @pytest.mark.asyncio
    async def test_get_validation_quality_metrics(self, validation_system, mock_db_session, mock_validations):
        """Test validation quality metrics calculation."""
        with patch('shared.services.validation_system.validation_service') as mock_val_service:
            mock_val_service.get_opportunity_validations = AsyncMock(return_value=mock_validations)
            
            metrics = await validation_system.get_validation_quality_metrics(
                mock_db_session, "opp-123"
            )
            
            assert metrics["total_validations"] == 3
            assert metrics["quality_score"] > 0
            assert metrics["completeness_score"] > 0
            assert metrics["evidence_score"] > 0
            assert metrics["expertise_score"] > 0
            assert metrics["community_engagement_score"] >= 0
            
            # Check that all scores are within valid range
            for key, value in metrics.items():
                if key != "total_validations":
                    assert 0 <= value <= 10
    
    @pytest.mark.asyncio
    async def test_quality_metrics_no_validations(self, validation_system, mock_db_session):
        """Test quality metrics with no validations."""
        with patch('shared.services.validation_system.validation_service') as mock_val_service:
            mock_val_service.get_opportunity_validations = AsyncMock(return_value=[])
            
            metrics = await validation_system.get_validation_quality_metrics(
                mock_db_session, "opp-empty"
            )
            
            assert metrics["total_validations"] == 0
            assert metrics["quality_score"] == 0.0
            assert metrics["completeness_score"] == 0.0
            assert metrics["evidence_score"] == 0.0
            assert metrics["expertise_score"] == 0.0
            assert metrics["community_engagement_score"] == 0.0
    
    @pytest.mark.asyncio
    async def test_workflow_not_found(self, validation_system):
        """Test getting non-existent workflow."""
        workflow = await validation_system.get_validation_workflow("non-existent")
        assert workflow is None
    
    @pytest.mark.asyncio
    async def test_update_workflow_not_found(self, validation_system, mock_db_session):
        """Test updating non-existent workflow."""
        new_validation = ValidationResult(
            id="val-new",
            opportunity_id="non-existent",
            validator_id="user-1",
            validation_type=ValidationType.MARKET_DEMAND,
            score=8.0
        )
        
        result = await validation_system.update_validation_workflow(
            mock_db_session, "non-existent", new_validation
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_initiate_workflow_opportunity_not_found(self, validation_system, mock_db_session):
        """Test workflow initiation with non-existent opportunity."""
        with patch('shared.services.validation_system.opportunity_service') as mock_opp_service:
            mock_opp_service.get_opportunity_by_id = AsyncMock(return_value=None)
            
            with pytest.raises(ValueError, match="Opportunity .* not found"):
                await validation_system.initiate_validation_workflow(
                    mock_db_session, "non-existent"
                )
    
    @pytest.mark.asyncio
    async def test_initiate_workflow_already_exists(self, validation_system, mock_db_session, mock_opportunity):
        """Test workflow initiation when workflow already exists."""
        # Create existing workflow
        now = datetime.utcnow()
        existing_workflow = ValidationWorkflow(
            opportunity_id="opp-123",
            status=ValidationWorkflowStatus.IN_PROGRESS,
            priority=ValidationPriority.NORMAL,
            required_validation_types={ValidationType.MARKET_DEMAND},
            completed_validation_types=set(),
            target_validator_count=3,
            current_validator_count=0,
            min_expert_validations=1,
            current_expert_validations=0,
            deadline=None,
            created_at=now,
            updated_at=now
        )
        
        validation_system._active_workflows["opp-123"] = existing_workflow
        
        with patch('shared.services.validation_system.opportunity_service') as mock_opp_service:
            mock_opp_service.get_opportunity_by_id = AsyncMock(return_value=mock_opportunity)
            
            # Should return existing workflow
            workflow = await validation_system.initiate_validation_workflow(
                mock_db_session, "opp-123"
            )
            
            assert workflow is existing_workflow
            assert workflow.status == ValidationWorkflowStatus.IN_PROGRESS