"""ValidationSystem core for managing validation workflows and aggregation.

This module implements the core validation system that orchestrates validation workflows
and provides advanced validation aggregation logic beyond the basic validation service.

Supports Requirements 2.1-2.5 (Opportunity Validation Framework):
- Validation workflow management and orchestration
- Advanced validation aggregation with consensus algorithms
- Quality control and validation integrity checks
- Automated validation triggers and lifecycle management
"""

import asyncio
import json
from typing import List, Optional, Dict, Any, Tuple, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from shared.models.validation import ValidationResult, ValidationType
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.user import User, UserRole
from shared.schemas.validation import ValidationSummary
from shared.services.validation_service import validation_service
from shared.services.opportunity_service import opportunity_service
from shared.services.user_service import user_service
from shared.cache import cache_manager, CacheKeys
import structlog

logger = structlog.get_logger(__name__)


class ValidationWorkflowStatus(str, Enum):
    """Status of validation workflow."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationPriority(str, Enum):
    """Priority levels for validation workflows."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ValidationWorkflow:
    """Represents a validation workflow for an opportunity."""
    opportunity_id: str
    status: ValidationWorkflowStatus
    priority: ValidationPriority
    required_validation_types: Set[ValidationType]
    completed_validation_types: Set[ValidationType]
    target_validator_count: int
    current_validator_count: int
    min_expert_validations: int
    current_expert_validations: int
    deadline: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    @property
    def completion_percentage(self) -> float:
        """Calculate workflow completion percentage."""
        if not self.required_validation_types:
            return 100.0
        
        completed_count = len(self.completed_validation_types)
        required_count = len(self.required_validation_types)
        return (completed_count / required_count) * 100.0
    
    @property
    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        return (
            self.completed_validation_types >= self.required_validation_types and
            self.current_validator_count >= self.target_validator_count and
            self.current_expert_validations >= self.min_expert_validations
        )


@dataclass
class ValidationConsensus:
    """Represents consensus analysis for validation results."""
    opportunity_id: str
    consensus_score: float
    confidence_level: float
    agreement_ratio: float
    outlier_count: int
    quality_score: float
    recommendation: str
    supporting_evidence_count: int
    expert_consensus: float
    community_consensus: float


class ValidationSystem:
    """Core validation system for workflow management and aggregation."""
    
    def __init__(self):
        """Initialize validation system."""
        self._active_workflows: Dict[str, ValidationWorkflow] = {}
        self._workflow_lock = asyncio.Lock()
    
    async def initiate_validation_workflow(
        self,
        db: AsyncSession,
        opportunity_id: str,
        priority: ValidationPriority = ValidationPriority.NORMAL,
        required_validation_types: Optional[Set[ValidationType]] = None,
        target_validator_count: int = 5,
        min_expert_validations: int = 2,
        deadline: Optional[datetime] = None
    ) -> ValidationWorkflow:
        """Initiate a validation workflow for an opportunity.
        
        Supports Requirement 2.1 (Initiate validation workflow when opportunities are discovered).
        
        Args:
            db: Database session
            opportunity_id: Opportunity to validate
            priority: Workflow priority level
            required_validation_types: Types of validation required
            target_validator_count: Target number of validators
            min_expert_validations: Minimum expert validations required
            deadline: Optional deadline for completion
            
        Returns:
            Created validation workflow
        """
        # Verify opportunity exists
        opportunity = await opportunity_service.get_opportunity_by_id(
            db, opportunity_id, include_relationships=False
        )
        if not opportunity:
            raise ValueError(f"Opportunity {opportunity_id} not found")
        
        # Set default validation types if not provided
        if required_validation_types is None:
            required_validation_types = {
                ValidationType.MARKET_DEMAND,
                ValidationType.TECHNICAL_FEASIBILITY,
                ValidationType.BUSINESS_VIABILITY
            }
        
        # Check for existing workflow
        async with self._workflow_lock:
            if opportunity_id in self._active_workflows:
                existing_workflow = self._active_workflows[opportunity_id]
                if existing_workflow.status in [ValidationWorkflowStatus.PENDING, ValidationWorkflowStatus.IN_PROGRESS]:
                    logger.info(
                        "Validation workflow already exists",
                        opportunity_id=opportunity_id,
                        status=existing_workflow.status
                    )
                    return existing_workflow
        
        # Get existing validations to determine current state
        existing_validations = await validation_service.get_opportunity_validations(
            db, opportunity_id
        )
        
        completed_types = set()
        current_validator_count = len(existing_validations)
        current_expert_validations = 0
        
        for validation in existing_validations:
            completed_types.add(validation.validation_type)
            
            # Count expert validations
            validator = await user_service.get_user_by_id(db, validation.validator_id)
            if validator and validator.role == UserRole.EXPERT:
                current_expert_validations += 1
        
        # Create workflow
        now = datetime.utcnow()
        workflow = ValidationWorkflow(
            opportunity_id=opportunity_id,
            status=ValidationWorkflowStatus.PENDING,
            priority=priority,
            required_validation_types=required_validation_types,
            completed_validation_types=completed_types,
            target_validator_count=target_validator_count,
            current_validator_count=current_validator_count,
            min_expert_validations=min_expert_validations,
            current_expert_validations=current_expert_validations,
            deadline=deadline,
            created_at=now,
            updated_at=now
        )
        
        # Store workflow
        async with self._workflow_lock:
            self._active_workflows[opportunity_id] = workflow
        
        # Update opportunity status
        if opportunity.status == OpportunityStatus.DISCOVERED:
            opportunity.status = OpportunityStatus.VALIDATING
            await db.commit()
        
        logger.info(
            "Validation workflow initiated",
            opportunity_id=opportunity_id,
            priority=priority.value,
            required_types=len(required_validation_types),
            target_validators=target_validator_count,
            completion_pct=workflow.completion_percentage
        )
        
        # Start workflow processing
        asyncio.create_task(self._process_workflow(db, workflow))
        
        return workflow
    
    async def update_validation_workflow(
        self,
        db: AsyncSession,
        opportunity_id: str,
        validation_result: ValidationResult
    ) -> Optional[ValidationWorkflow]:
        """Update validation workflow when new validation is added.
        
        Args:
            db: Database session
            opportunity_id: Opportunity identifier
            validation_result: New validation result
            
        Returns:
            Updated workflow or None if no active workflow
        """
        async with self._workflow_lock:
            workflow = self._active_workflows.get(opportunity_id)
            if not workflow:
                return None
            
            # Update workflow state
            workflow.completed_validation_types.add(validation_result.validation_type)
            workflow.current_validator_count += 1
            workflow.updated_at = datetime.utcnow()
            
            # Check if validator is expert
            validator = await user_service.get_user_by_id(db, validation_result.validator_id)
            if validator and validator.role == UserRole.EXPERT:
                workflow.current_expert_validations += 1
            
            # Update status based on completion
            if workflow.is_complete:
                workflow.status = ValidationWorkflowStatus.COMPLETED
                logger.info(
                    "Validation workflow completed",
                    opportunity_id=opportunity_id,
                    completion_pct=workflow.completion_percentage
                )
                
                # Trigger final aggregation and consensus analysis
                await self._finalize_workflow(db, workflow)
            else:
                workflow.status = ValidationWorkflowStatus.IN_PROGRESS
        
        return workflow
    
    async def get_validation_workflow(
        self,
        opportunity_id: str
    ) -> Optional[ValidationWorkflow]:
        """Get validation workflow for an opportunity.
        
        Args:
            opportunity_id: Opportunity identifier
            
        Returns:
            Validation workflow or None
        """
        async with self._workflow_lock:
            return self._active_workflows.get(opportunity_id)
    
    async def get_active_workflows(
        self,
        priority: Optional[ValidationPriority] = None,
        status: Optional[ValidationWorkflowStatus] = None
    ) -> List[ValidationWorkflow]:
        """Get list of active validation workflows.
        
        Args:
            priority: Optional priority filter
            status: Optional status filter
            
        Returns:
            List of matching workflows
        """
        async with self._workflow_lock:
            workflows = list(self._active_workflows.values())
        
        # Apply filters
        if priority:
            workflows = [w for w in workflows if w.priority == priority]
        
        if status:
            workflows = [w for w in workflows if w.status == status]
        
        # Sort by priority and creation time
        priority_order = {
            ValidationPriority.URGENT: 0,
            ValidationPriority.HIGH: 1,
            ValidationPriority.NORMAL: 2,
            ValidationPriority.LOW: 3
        }
        
        workflows.sort(key=lambda w: (priority_order[w.priority], w.created_at))
        
        return workflows
    
    async def analyze_validation_consensus(
        self,
        db: AsyncSession,
        opportunity_id: str
    ) -> ValidationConsensus:
        """Analyze validation consensus for an opportunity.
        
        Supports Requirements 2.2-2.3 (Validation aggregation and confidence ratings).
        
        Args:
            db: Database session
            opportunity_id: Opportunity identifier
            
        Returns:
            Validation consensus analysis
        """
        # Get all validations for the opportunity
        validations = await validation_service.get_opportunity_validations(
            db, opportunity_id
        )
        
        if not validations:
            return ValidationConsensus(
                opportunity_id=opportunity_id,
                consensus_score=0.0,
                confidence_level=0.0,
                agreement_ratio=0.0,
                outlier_count=0,
                quality_score=0.0,
                recommendation="No validations available",
                supporting_evidence_count=0,
                expert_consensus=0.0,
                community_consensus=0.0
            )
        
        # Separate expert and community validations
        expert_validations = []
        community_validations = []
        
        for validation in validations:
            validator = await user_service.get_user_by_id(db, validation.validator_id)
            if validator and validator.role == UserRole.EXPERT:
                expert_validations.append(validation)
            else:
                community_validations.append(validation)
        
        # Calculate weighted consensus score
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for validation in validations:
            # Get validator influence weight
            validator_weight = await user_service.get_user_influence_weight(
                db, validation.validator_id
            )
            
            # Apply confidence weighting
            confidence_weight = validation.confidence / 10.0
            final_weight = validator_weight * confidence_weight
            
            total_weighted_score += validation.score * final_weight
            total_weight += final_weight
        
        consensus_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
        
        # Calculate agreement ratio (how close scores are to consensus)
        if len(validations) > 1:
            score_deviations = [abs(v.score - consensus_score) for v in validations]
            avg_deviation = sum(score_deviations) / len(score_deviations)
            agreement_ratio = max(0.0, 1.0 - (avg_deviation / 10.0))
        else:
            agreement_ratio = 1.0
        
        # Identify outliers (scores more than 2 standard deviations from mean)
        if len(validations) > 2:
            scores = [v.score for v in validations]
            mean_score = sum(scores) / len(scores)
            variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
            std_dev = variance ** 0.5
            
            outlier_count = sum(
                1 for score in scores 
                if abs(score - mean_score) > 2 * std_dev
            )
        else:
            outlier_count = 0
        
        # Calculate quality score based on evidence and methodology
        evidence_count = 0
        quality_scores = []
        
        for validation in validations:
            quality_score = 5.0  # Base quality
            
            # Evidence bonus
            if validation.evidence_links:
                try:
                    links = json.loads(validation.evidence_links)
                    evidence_count += len(links)
                    quality_score += min(2.0, len(links) * 0.5)
                except json.JSONDecodeError:
                    pass
            
            # Methodology bonus
            if validation.methodology:
                quality_score += 1.0
            
            # Detailed feedback bonus
            if validation.strengths and validation.weaknesses:
                quality_score += 1.0
            
            # Community feedback adjustment
            total_votes = validation.helpful_votes + validation.unhelpful_votes
            if total_votes > 0:
                helpful_ratio = validation.helpful_votes / total_votes
                quality_score += (helpful_ratio - 0.5) * 2.0
            
            quality_scores.append(min(10.0, max(0.0, quality_score)))
        
        overall_quality = sum(quality_scores) / len(quality_scores)
        
        # Calculate expert vs community consensus
        expert_consensus = 0.0
        if expert_validations:
            expert_scores = [v.score for v in expert_validations]
            expert_consensus = sum(expert_scores) / len(expert_scores)
        
        community_consensus = 0.0
        if community_validations:
            community_scores = [v.score for v in community_validations]
            community_consensus = sum(community_scores) / len(community_scores)
        
        # Calculate confidence level based on multiple factors
        confidence_factors = [
            len(validations) / 10.0,  # More validations = higher confidence
            agreement_ratio,  # Higher agreement = higher confidence
            overall_quality / 10.0,  # Higher quality = higher confidence
            min(1.0, len(expert_validations) / 3.0)  # Expert participation
        ]
        
        confidence_level = min(10.0, sum(confidence_factors) * 2.5)
        
        # Generate recommendation
        if consensus_score >= 7.0 and confidence_level >= 6.0:
            recommendation = "Strong validation - proceed with development"
        elif consensus_score >= 5.0 and confidence_level >= 4.0:
            recommendation = "Moderate validation - consider additional research"
        elif consensus_score >= 3.0:
            recommendation = "Weak validation - significant concerns identified"
        else:
            recommendation = "Poor validation - not recommended for development"
        
        return ValidationConsensus(
            opportunity_id=opportunity_id,
            consensus_score=round(consensus_score, 2),
            confidence_level=round(confidence_level, 2),
            agreement_ratio=round(agreement_ratio, 2),
            outlier_count=outlier_count,
            quality_score=round(overall_quality, 2),
            recommendation=recommendation,
            supporting_evidence_count=evidence_count,
            expert_consensus=round(expert_consensus, 2),
            community_consensus=round(community_consensus, 2)
        )
    
    async def get_validation_quality_metrics(
        self,
        db: AsyncSession,
        opportunity_id: str
    ) -> Dict[str, Any]:
        """Get detailed validation quality metrics.
        
        Args:
            db: Database session
            opportunity_id: Opportunity identifier
            
        Returns:
            Quality metrics dictionary
        """
        validations = await validation_service.get_opportunity_validations(
            db, opportunity_id
        )
        
        if not validations:
            return {
                "total_validations": 0,
                "quality_score": 0.0,
                "completeness_score": 0.0,
                "evidence_score": 0.0,
                "expertise_score": 0.0,
                "community_engagement_score": 0.0
            }
        
        # Calculate individual quality components
        evidence_scores = []
        expertise_scores = []
        engagement_scores = []
        completeness_scores = []
        
        for validation in validations:
            # Evidence quality
            evidence_score = 0.0
            if validation.evidence_links:
                try:
                    links = json.loads(validation.evidence_links)
                    evidence_score = min(10.0, len(links) * 2.0)
                except json.JSONDecodeError:
                    pass
            evidence_scores.append(evidence_score)
            
            # Expertise relevance
            expertise_score = validation.expertise_relevance or 5.0
            expertise_scores.append(expertise_score)
            
            # Community engagement
            total_votes = validation.helpful_votes + validation.unhelpful_votes
            if total_votes > 0:
                engagement_score = min(10.0, total_votes * 0.5)
            else:
                engagement_score = 0.0
            engagement_scores.append(engagement_score)
            
            # Completeness (based on filled fields)
            completeness_score = 0.0
            if validation.comments:
                completeness_score += 2.0
            if validation.strengths:
                completeness_score += 2.0
            if validation.weaknesses:
                completeness_score += 2.0
            if validation.recommendations:
                completeness_score += 2.0
            if validation.methodology:
                completeness_score += 2.0
            completeness_scores.append(completeness_score)
        
        return {
            "total_validations": len(validations),
            "quality_score": round(sum(evidence_scores + expertise_scores + engagement_scores + completeness_scores) / (len(validations) * 4), 2),
            "completeness_score": round(sum(completeness_scores) / len(completeness_scores), 2),
            "evidence_score": round(sum(evidence_scores) / len(evidence_scores), 2),
            "expertise_score": round(sum(expertise_scores) / len(expertise_scores), 2),
            "community_engagement_score": round(sum(engagement_scores) / len(engagement_scores), 2)
        }
    
    async def _process_workflow(
        self,
        db: AsyncSession,
        workflow: ValidationWorkflow
    ) -> None:
        """Process validation workflow in background.
        
        Args:
            db: Database session
            workflow: Validation workflow to process
        """
        try:
            workflow.status = ValidationWorkflowStatus.IN_PROGRESS
            
            # Check for deadline expiration
            if workflow.deadline and datetime.utcnow() > workflow.deadline:
                workflow.status = ValidationWorkflowStatus.FAILED
                logger.warning(
                    "Validation workflow deadline expired",
                    opportunity_id=workflow.opportunity_id,
                    deadline=workflow.deadline
                )
                return
            
            # Monitor workflow progress
            while workflow.status == ValidationWorkflowStatus.IN_PROGRESS:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Refresh workflow state
                current_validations = await validation_service.get_opportunity_validations(
                    db, workflow.opportunity_id
                )
                
                # Update counts
                workflow.current_validator_count = len(current_validations)
                workflow.completed_validation_types = {v.validation_type for v in current_validations}
                
                # Count expert validations
                expert_count = 0
                for validation in current_validations:
                    validator = await user_service.get_user_by_id(db, validation.validator_id)
                    if validator and validator.role == UserRole.EXPERT:
                        expert_count += 1
                workflow.current_expert_validations = expert_count
                
                # Check completion
                if workflow.is_complete:
                    workflow.status = ValidationWorkflowStatus.COMPLETED
                    await self._finalize_workflow(db, workflow)
                    break
                
                # Check deadline
                if workflow.deadline and datetime.utcnow() > workflow.deadline:
                    workflow.status = ValidationWorkflowStatus.FAILED
                    logger.warning(
                        "Validation workflow deadline expired during processing",
                        opportunity_id=workflow.opportunity_id
                    )
                    break
        
        except Exception as e:
            workflow.status = ValidationWorkflowStatus.FAILED
            logger.error(
                "Validation workflow processing failed",
                opportunity_id=workflow.opportunity_id,
                error=str(e)
            )
    
    async def _finalize_workflow(
        self,
        db: AsyncSession,
        workflow: ValidationWorkflow
    ) -> None:
        """Finalize completed validation workflow.
        
        Args:
            db: Database session
            workflow: Completed workflow
        """
        try:
            # Perform final consensus analysis
            consensus = await self.analyze_validation_consensus(db, workflow.opportunity_id)
            
            # Update opportunity based on consensus
            opportunity = await opportunity_service.get_opportunity_by_id(
                db, workflow.opportunity_id, include_relationships=False
            )
            
            if opportunity:
                # Update status based on consensus
                if consensus.consensus_score >= 7.0 and consensus.confidence_level >= 6.0:
                    opportunity.status = OpportunityStatus.VALIDATED
                elif consensus.consensus_score < 3.0:
                    opportunity.status = OpportunityStatus.REJECTED
                else:
                    opportunity.status = OpportunityStatus.VALIDATING  # Needs more validation
                
                await db.commit()
            
            # Cache consensus results
            cache_key = CacheKeys.format_key(
                CacheKeys.VALIDATION_CONSENSUS, 
                opportunity_id=workflow.opportunity_id
            )
            await cache_manager.set(cache_key, consensus, ttl=3600)
            
            logger.info(
                "Validation workflow finalized",
                opportunity_id=workflow.opportunity_id,
                consensus_score=consensus.consensus_score,
                confidence_level=consensus.confidence_level,
                final_status=opportunity.status if opportunity else "unknown"
            )
            
        except Exception as e:
            logger.error(
                "Failed to finalize validation workflow",
                opportunity_id=workflow.opportunity_id,
                error=str(e)
            )


# Global validation system instance
validation_system = ValidationSystem()