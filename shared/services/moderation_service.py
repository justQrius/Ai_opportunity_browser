"""Automated moderation service for validation quality control.

This module implements automated moderation systems that work with fraud detection
to maintain validation quality and community standards.

Supports Requirements 2.4-2.5 (Quality control and validation integrity):
- Automated moderation workflows
- Community reporting and flagging
- Moderator tools and interfaces
- Appeal and review processes
"""

import asyncio
import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, update
from sqlalchemy.orm import selectinload

from shared.models.validation import ValidationResult
from shared.models.user import User, UserRole
from shared.models.reputation import ReputationEvent, ReputationEventType
from shared.services.fraud_detection_service import (
    fraud_detection_service, 
    FraudDetectionResult, 
    ModerationDecision,
    ModerationAction,
    FraudSeverity
)
from shared.services.reputation_service import reputation_service
from shared.services.user_service import user_service
from shared.cache import cache_manager, CacheKeys
import structlog

logger = structlog.get_logger(__name__)


class ModerationStatus(str, Enum):
    """Status of moderation items."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPEALED = "appealed"
    RESOLVED = "resolved"


class AppealStatus(str, Enum):
    """Status of moderation appeals."""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DENIED = "denied"


@dataclass
class ModerationItem:
    """Represents an item in the moderation queue."""
    validation_id: str
    user_id: str
    fraud_results: List[FraudDetectionResult]
    status: ModerationStatus
    priority: int  # 1-10, higher is more urgent
    assigned_moderator: Optional[str]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]


@dataclass
class ModerationAppeal:
    """Represents an appeal against moderation action."""
    validation_id: str
    user_id: str
    original_action: ModerationAction
    appeal_reason: str
    status: AppealStatus
    assigned_reviewer: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
    resolution: Optional[str]
    metadata: Dict[str, Any]


class ModerationService:
    """Service for automated moderation and community quality control."""
    
    # Moderation thresholds
    AUTO_APPROVE_THRESHOLD = 0.3  # Fraud confidence below this = auto-approve
    AUTO_REJECT_THRESHOLD = 0.9   # Fraud confidence above this = auto-reject
    PRIORITY_THRESHOLDS = {
        FraudSeverity.CRITICAL: 10,
        FraudSeverity.HIGH: 8,
        FraudSeverity.MEDIUM: 5,
        FraudSeverity.LOW: 2
    }
    
    def __init__(self):
        """Initialize moderation service."""
        self._moderation_queue: Dict[str, ModerationItem] = {}
        self._appeal_queue: Dict[str, ModerationAppeal] = {}
        self._moderator_assignments: Dict[str, List[str]] = {}  # moderator_id -> validation_ids
        self._processing_lock = asyncio.Lock()
    
    async def process_validation_for_moderation(
        self,
        db: AsyncSession,
        validation_id: str
    ) -> Optional[ModerationItem]:
        """Process a validation through the moderation pipeline.
        
        Args:
            db: Database session
            validation_id: Validation to process
            
        Returns:
            Moderation item if created, None if auto-approved
        """
        # Run fraud detection
        fraud_results = await fraud_detection_service.analyze_validation_for_fraud(
            db, validation_id
        )
        
        if not fraud_results:
            # No fraud detected, auto-approve
            await self._auto_approve_validation(db, validation_id)
            return None
        
        # Calculate overall fraud confidence
        max_confidence = max(result.confidence_score for result in fraud_results)
        
        # Auto-approve if confidence is very low
        if max_confidence < self.AUTO_APPROVE_THRESHOLD:
            await self._auto_approve_validation(db, validation_id)
            return None
        
        # Auto-reject if confidence is very high
        if max_confidence > self.AUTO_REJECT_THRESHOLD:
            await self._auto_reject_validation(db, validation_id, fraud_results)
            return None
        
        # Add to moderation queue for human review
        return await self._add_to_moderation_queue(db, validation_id, fraud_results)
    
    async def get_moderation_queue(
        self,
        moderator_id: Optional[str] = None,
        status: Optional[ModerationStatus] = None,
        limit: int = 50
    ) -> List[ModerationItem]:
        """Get items from the moderation queue.
        
        Args:
            moderator_id: Optional filter by assigned moderator
            status: Optional filter by status
            limit: Maximum items to return
            
        Returns:
            List of moderation items
        """
        items = list(self._moderation_queue.values())
        
        # Apply filters
        if moderator_id:
            items = [item for item in items if item.assigned_moderator == moderator_id]
        
        if status:
            items = [item for item in items if item.status == status]
        
        # Sort by priority (highest first) then by creation time
        items.sort(key=lambda x: (-x.priority, x.created_at))
        
        return items[:limit]
    
    async def assign_moderation_item(
        self,
        validation_id: str,
        moderator_id: str
    ) -> bool:
        """Assign a moderation item to a moderator.
        
        Args:
            validation_id: Validation to assign
            moderator_id: Moderator to assign to
            
        Returns:
            True if successfully assigned
        """
        async with self._processing_lock:
            item = self._moderation_queue.get(validation_id)
            if not item or item.status != ModerationStatus.PENDING:
                return False
            
            item.assigned_moderator = moderator_id
            item.status = ModerationStatus.IN_REVIEW
            item.updated_at = datetime.utcnow()
            
            # Track moderator assignments
            if moderator_id not in self._moderator_assignments:
                self._moderator_assignments[moderator_id] = []
            self._moderator_assignments[moderator_id].append(validation_id)
        
        logger.info(
            "Moderation item assigned",
            validation_id=validation_id,
            moderator_id=moderator_id
        )
        
        return True
    
    async def moderate_validation(
        self,
        db: AsyncSession,
        validation_id: str,
        moderator_id: str,
        action: ModerationAction,
        reason: str,
        notes: Optional[str] = None
    ) -> bool:
        """Moderate a validation with human decision.
        
        Args:
            db: Database session
            validation_id: Validation to moderate
            moderator_id: Moderator making decision
            action: Moderation action to take
            reason: Reason for the action
            notes: Optional additional notes
            
        Returns:
            True if successfully moderated
        """
        async with self._processing_lock:
            item = self._moderation_queue.get(validation_id)
            if not item or item.assigned_moderator != moderator_id:
                return False
            
            # Execute the moderation action
            decision = ModerationDecision(
                validation_id=validation_id,
                user_id=item.user_id,
                fraud_results=item.fraud_results,
                action_taken=action,
                moderator_id=moderator_id,
                automated=False,
                reason=reason,
                metadata={"notes": notes, "manual_review": True},
                created_at=datetime.utcnow()
            )
            
            await self._execute_moderation_decision(db, decision)
            
            # Update item status
            if action in [ModerationAction.DELETE_VALIDATION, ModerationAction.HIDE_VALIDATION]:
                item.status = ModerationStatus.REJECTED
            else:
                item.status = ModerationStatus.APPROVED
            
            item.updated_at = datetime.utcnow()
            
            # Remove from moderator assignments
            if moderator_id in self._moderator_assignments:
                self._moderator_assignments[moderator_id] = [
                    vid for vid in self._moderator_assignments[moderator_id] 
                    if vid != validation_id
                ]
        
        logger.info(
            "Validation moderated",
            validation_id=validation_id,
            moderator_id=moderator_id,
            action=action.value,
            reason=reason
        )
        
        return True
    
    async def submit_appeal(
        self,
        db: AsyncSession,
        validation_id: str,
        user_id: str,
        appeal_reason: str,
        evidence: Optional[str] = None
    ) -> ModerationAppeal:
        """Submit an appeal against moderation action.
        
        Args:
            db: Database session
            validation_id: Validation that was moderated
            user_id: User submitting appeal
            appeal_reason: Reason for appeal
            evidence: Optional supporting evidence
            
        Returns:
            Created appeal
        """
        # Get the original moderation item
        moderation_item = self._moderation_queue.get(validation_id)
        if not moderation_item:
            raise ValueError("No moderation record found for validation")
        
        # Determine original action from fraud results
        original_action = ModerationAction.FLAG_FOR_REVIEW  # Default
        if moderation_item.status == ModerationStatus.REJECTED:
            original_action = ModerationAction.HIDE_VALIDATION
        
        # Create appeal
        appeal = ModerationAppeal(
            validation_id=validation_id,
            user_id=user_id,
            original_action=original_action,
            appeal_reason=appeal_reason,
            status=AppealStatus.PENDING,
            assigned_reviewer=None,
            created_at=datetime.utcnow(),
            resolved_at=None,
            resolution=None,
            metadata={"evidence": evidence, "original_status": moderation_item.status.value}
        )
        
        self._appeal_queue[validation_id] = appeal
        
        # Update moderation item status
        moderation_item.status = ModerationStatus.APPEALED
        moderation_item.updated_at = datetime.utcnow()
        
        logger.info(
            "Moderation appeal submitted",
            validation_id=validation_id,
            user_id=user_id,
            appeal_reason=appeal_reason
        )
        
        return appeal
    
    async def process_appeal(
        self,
        db: AsyncSession,
        validation_id: str,
        reviewer_id: str,
        approved: bool,
        resolution: str
    ) -> bool:
        """Process a moderation appeal.
        
        Args:
            db: Database session
            validation_id: Validation being appealed
            reviewer_id: Reviewer processing appeal
            approved: Whether appeal is approved
            resolution: Resolution explanation
            
        Returns:
            True if successfully processed
        """
        appeal = self._appeal_queue.get(validation_id)
        if not appeal:
            return False
        
        # Update appeal status
        appeal.status = AppealStatus.APPROVED if approved else AppealStatus.DENIED
        appeal.assigned_reviewer = reviewer_id
        appeal.resolved_at = datetime.utcnow()
        appeal.resolution = resolution
        
        # If appeal approved, reverse the moderation action
        if approved:
            await self._reverse_moderation_action(db, validation_id, appeal.original_action)
            
            # Update moderation item
            moderation_item = self._moderation_queue.get(validation_id)
            if moderation_item:
                moderation_item.status = ModerationStatus.RESOLVED
                moderation_item.updated_at = datetime.utcnow()
        
        logger.info(
            "Appeal processed",
            validation_id=validation_id,
            reviewer_id=reviewer_id,
            approved=approved,
            resolution=resolution
        )
        
        return True
    
    async def get_moderation_statistics(
        self,
        db: AsyncSession,
        timeframe_days: int = 30
    ) -> Dict[str, Any]:
        """Get moderation system statistics.
        
        Args:
            db: Database session
            timeframe_days: Timeframe for statistics
            
        Returns:
            Moderation statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=timeframe_days)
        
        # Count items by status
        status_counts = {}
        for status in ModerationStatus:
            count = sum(
                1 for item in self._moderation_queue.values()
                if item.status == status and item.created_at >= cutoff_date
            )
            status_counts[status.value] = count
        
        # Count appeals by status
        appeal_counts = {}
        for status in AppealStatus:
            count = sum(
                1 for appeal in self._appeal_queue.values()
                if appeal.status == status and appeal.created_at >= cutoff_date
            )
            appeal_counts[status.value] = count
        
        # Calculate processing times
        resolved_items = [
            item for item in self._moderation_queue.values()
            if item.status in [ModerationStatus.APPROVED, ModerationStatus.REJECTED, ModerationStatus.RESOLVED]
            and item.created_at >= cutoff_date
        ]
        
        avg_processing_time = 0.0
        if resolved_items:
            total_time = sum(
                (item.updated_at - item.created_at).total_seconds()
                for item in resolved_items
            )
            avg_processing_time = total_time / len(resolved_items) / 3600  # Convert to hours
        
        return {
            "timeframe_days": timeframe_days,
            "queue_size": len(self._moderation_queue),
            "pending_items": status_counts.get("pending", 0),
            "in_review_items": status_counts.get("in_review", 0),
            "resolved_items": len(resolved_items),
            "appeal_queue_size": len(self._appeal_queue),
            "pending_appeals": appeal_counts.get("pending", 0),
            "average_processing_time_hours": round(avg_processing_time, 2),
            "status_breakdown": status_counts,
            "appeal_breakdown": appeal_counts,
            "active_moderators": len(self._moderator_assignments)
        }
    
    async def get_moderator_workload(
        self,
        moderator_id: str
    ) -> Dict[str, Any]:
        """Get workload information for a moderator.
        
        Args:
            moderator_id: Moderator identifier
            
        Returns:
            Workload information
        """
        assigned_items = self._moderator_assignments.get(moderator_id, [])
        
        # Get detailed item information
        items = [
            self._moderation_queue[vid] for vid in assigned_items
            if vid in self._moderation_queue
        ]
        
        # Calculate priority distribution
        priority_counts = {}
        for item in items:
            priority_counts[item.priority] = priority_counts.get(item.priority, 0) + 1
        
        # Calculate average age of assigned items
        avg_age_hours = 0.0
        if items:
            total_age = sum(
                (datetime.utcnow() - item.created_at).total_seconds()
                for item in items
            )
            avg_age_hours = total_age / len(items) / 3600
        
        return {
            "moderator_id": moderator_id,
            "assigned_items": len(assigned_items),
            "pending_items": len([item for item in items if item.status == ModerationStatus.PENDING]),
            "in_review_items": len([item for item in items if item.status == ModerationStatus.IN_REVIEW]),
            "average_item_age_hours": round(avg_age_hours, 2),
            "priority_distribution": priority_counts,
            "oldest_item_age_hours": round(
                max(
                    (datetime.utcnow() - item.created_at).total_seconds() / 3600
                    for item in items
                ) if items else 0, 2
            )
        }
    
    # Private helper methods
    
    async def _auto_approve_validation(
        self,
        db: AsyncSession,
        validation_id: str
    ) -> None:
        """Auto-approve a validation with no fraud detected."""
        result = await db.execute(
            select(ValidationResult).where(ValidationResult.id == validation_id)
        )
        validation = result.scalar_one_or_none()
        
        if validation:
            validation.moderator_reviewed = True
            await db.commit()
            
            logger.info(
                "Validation auto-approved",
                validation_id=validation_id
            )
    
    async def _auto_reject_validation(
        self,
        db: AsyncSession,
        validation_id: str,
        fraud_results: List[FraudDetectionResult]
    ) -> None:
        """Auto-reject a validation with high fraud confidence."""
        decision = ModerationDecision(
            validation_id=validation_id,
            user_id="",  # Will be filled in execute method
            fraud_results=fraud_results,
            action_taken=ModerationAction.HIDE_VALIDATION,
            moderator_id=None,
            automated=True,
            reason="Automated rejection due to high fraud confidence",
            metadata={"auto_rejected": True},
            created_at=datetime.utcnow()
        )
        
        await self._execute_moderation_decision(db, decision)
        
        logger.info(
            "Validation auto-rejected",
            validation_id=validation_id,
            fraud_count=len(fraud_results)
        )
    
    async def _add_to_moderation_queue(
        self,
        db: AsyncSession,
        validation_id: str,
        fraud_results: List[FraudDetectionResult]
    ) -> ModerationItem:
        """Add validation to moderation queue."""
        # Get validation to get user_id
        result = await db.execute(
            select(ValidationResult).where(ValidationResult.id == validation_id)
        )
        validation = result.scalar_one_or_none()
        
        if not validation:
            raise ValueError(f"Validation {validation_id} not found")
        
        # Calculate priority based on fraud severity
        max_severity = max(result.severity for result in fraud_results)
        priority = self.PRIORITY_THRESHOLDS.get(max_severity, 5)
        
        # Create moderation item
        item = ModerationItem(
            validation_id=validation_id,
            user_id=validation.validator_id,
            fraud_results=fraud_results,
            status=ModerationStatus.PENDING,
            priority=priority,
            assigned_moderator=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={
                "fraud_types": [result.fraud_type.value for result in fraud_results],
                "max_confidence": max(result.confidence_score for result in fraud_results)
            }
        )
        
        self._moderation_queue[validation_id] = item
        
        logger.info(
            "Validation added to moderation queue",
            validation_id=validation_id,
            priority=priority,
            fraud_count=len(fraud_results)
        )
        
        return item
    
    async def _execute_moderation_decision(
        self,
        db: AsyncSession,
        decision: ModerationDecision
    ) -> None:
        """Execute a moderation decision."""
        # Get validation if user_id not set
        if not decision.user_id:
            result = await db.execute(
                select(ValidationResult).where(ValidationResult.id == decision.validation_id)
            )
            validation = result.scalar_one_or_none()
            if validation:
                decision.user_id = validation.validator_id
        
        # Use fraud detection service to execute the action
        await fraud_detection_service._execute_moderation_action(db, decision)
    
    async def _reverse_moderation_action(
        self,
        db: AsyncSession,
        validation_id: str,
        original_action: ModerationAction
    ) -> None:
        """Reverse a moderation action after successful appeal."""
        result = await db.execute(
            select(ValidationResult).where(ValidationResult.id == validation_id)
        )
        validation = result.scalar_one_or_none()
        
        if not validation:
            return
        
        # Reverse the action
        if original_action == ModerationAction.HIDE_VALIDATION:
            validation.is_flagged = False
            validation.flag_reason = None
        elif original_action == ModerationAction.FLAG_FOR_REVIEW:
            validation.is_flagged = False
            validation.flag_reason = None
        
        # Mark as reviewed
        validation.moderator_reviewed = True
        
        await db.commit()
        
        logger.info(
            "Moderation action reversed",
            validation_id=validation_id,
            original_action=original_action.value
        )


# Global moderation service instance
moderation_service = ModerationService()