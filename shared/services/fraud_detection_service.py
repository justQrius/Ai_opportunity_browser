"""Fraud detection service for validation abuse detection and automated moderation.

This module implements comprehensive fraud detection and automated moderation systems
to maintain validation quality and prevent abuse.

Supports Requirements 2.4-2.5 (Quality control and validation integrity):
- Validation abuse detection algorithms
- Automated moderation systems
- Pattern recognition for fraudulent behavior
- Community-driven fraud reporting
"""

import asyncio
import json
import re
from typing import List, Optional, Dict, Any, Tuple, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload

from shared.models.validation import ValidationResult, ValidationType
from shared.models.user import User, UserRole
from shared.models.reputation import ReputationEvent, ReputationEventType, ReputationSummary
from shared.services.validation_service import validation_service
from shared.services.reputation_service import reputation_service
from shared.services.user_service import user_service
from shared.cache import cache_manager, CacheKeys
import structlog

logger = structlog.get_logger(__name__)


class FraudType(str, Enum):
    """Types of fraud that can be detected."""
    SPAM_VALIDATION = "spam_validation"
    FAKE_EXPERTISE = "fake_expertise"
    VOTE_MANIPULATION = "vote_manipulation"
    DUPLICATE_ACCOUNTS = "duplicate_accounts"
    COORDINATED_ABUSE = "coordinated_abuse"
    LOW_QUALITY_CONTENT = "low_quality_content"
    REPUTATION_FARMING = "reputation_farming"
    SOCKPUPPETING = "sockpuppeting"


class ModerationAction(str, Enum):
    """Types of moderation actions that can be taken."""
    FLAG_FOR_REVIEW = "flag_for_review"
    HIDE_VALIDATION = "hide_validation"
    SUSPEND_USER = "suspend_user"
    REDUCE_INFLUENCE = "reduce_influence"
    REQUIRE_VERIFICATION = "require_verification"
    DELETE_VALIDATION = "delete_validation"
    WARN_USER = "warn_user"
    NO_ACTION = "no_action"


class FraudSeverity(str, Enum):
    """Severity levels for fraud detection."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FraudDetectionResult:
    """Result of fraud detection analysis."""
    fraud_type: FraudType
    severity: FraudSeverity
    confidence_score: float  # 0.0-1.0
    evidence: List[str]
    recommended_action: ModerationAction
    metadata: Dict[str, Any]
    detected_at: datetime


@dataclass
class ModerationDecision:
    """Represents a moderation decision."""
    validation_id: str
    user_id: str
    fraud_results: List[FraudDetectionResult]
    action_taken: ModerationAction
    moderator_id: Optional[str]
    automated: bool
    reason: str
    metadata: Dict[str, Any]
    created_at: datetime


class FraudDetectionService:
    """Service for detecting validation abuse and automated moderation."""
    
    # Fraud detection thresholds
    SPAM_THRESHOLDS = {
        "min_time_between_validations": 30,  # seconds
        "max_validations_per_hour": 10,
        "min_validation_length": 20,  # characters
        "duplicate_content_threshold": 0.8,  # similarity score
    }
    
    QUALITY_THRESHOLDS = {
        "min_evidence_links": 0,
        "min_comment_length": 10,
        "max_generic_phrases": 3,
        "min_confidence_score": 2.0,
    }
    
    REPUTATION_THRESHOLDS = {
        "suspicious_growth_rate": 50.0,  # points per day
        "min_validation_diversity": 0.3,  # different opportunity types
        "max_failed_verifications": 3,
    }
    
    # Generic phrases that indicate low-quality content
    GENERIC_PHRASES = [
        "this is good", "this is bad", "i think", "maybe", "probably",
        "not sure", "could work", "might work", "seems ok", "looks fine",
        "good idea", "bad idea", "interesting", "nice", "cool"
    ]
    
    def __init__(self):
        """Initialize fraud detection service."""
        self._detection_cache: Dict[str, List[FraudDetectionResult]] = {}
        self._moderation_queue: List[ModerationDecision] = []
        self._user_behavior_cache: Dict[str, Dict[str, Any]] = {}
    
    async def analyze_validation_for_fraud(
        self,
        db: AsyncSession,
        validation_id: str
    ) -> List[FraudDetectionResult]:
        """Analyze a validation for potential fraud.
        
        Args:
            db: Database session
            validation_id: Validation to analyze
            
        Returns:
            List of fraud detection results
        """
        # Get validation with relationships
        result = await db.execute(
            select(ValidationResult)
            .options(selectinload(ValidationResult.validator))
            .where(ValidationResult.id == validation_id)
        )
        validation = result.scalar_one_or_none()
        
        if not validation:
            return []
        
        fraud_results = []
        
        # Run all fraud detection algorithms
        fraud_results.extend(await self._detect_spam_validation(db, validation))
        fraud_results.extend(await self._detect_low_quality_content(db, validation))
        fraud_results.extend(await self._detect_vote_manipulation(db, validation))
        fraud_results.extend(await self._detect_fake_expertise(db, validation))
        fraud_results.extend(await self._detect_reputation_farming(db, validation))
        
        # Cache results
        self._detection_cache[validation_id] = fraud_results
        
        logger.info(
            "Fraud analysis completed",
            validation_id=validation_id,
            fraud_count=len(fraud_results),
            max_severity=max([r.severity for r in fraud_results], default=FraudSeverity.LOW)
        )
        
        return fraud_results
    
    async def analyze_user_behavior(
        self,
        db: AsyncSession,
        user_id: str
    ) -> List[FraudDetectionResult]:
        """Analyze user's overall behavior for fraud patterns.
        
        Args:
            db: Database session
            user_id: User to analyze
            
        Returns:
            List of fraud detection results
        """
        fraud_results = []
        
        # Get user behavior data
        behavior_data = await self._get_user_behavior_data(db, user_id)
        
        # Run behavioral analysis
        fraud_results.extend(await self._detect_coordinated_abuse(db, user_id, behavior_data))
        fraud_results.extend(await self._detect_sockpuppeting(db, user_id, behavior_data))
        fraud_results.extend(await self._detect_duplicate_accounts(db, user_id, behavior_data))
        
        # Cache behavior data
        self._user_behavior_cache[user_id] = behavior_data
        
        return fraud_results
    
    async def process_moderation_queue(
        self,
        db: AsyncSession,
        max_items: int = 50
    ) -> List[ModerationDecision]:
        """Process pending moderation decisions.
        
        Args:
            db: Database session
            max_items: Maximum items to process
            
        Returns:
            List of processed moderation decisions
        """
        processed_decisions = []
        
        # Get pending validations that need review
        pending_validations = await self._get_pending_moderation_items(db, max_items)
        
        for validation in pending_validations:
            # Analyze for fraud
            fraud_results = await self.analyze_validation_for_fraud(db, validation.id)
            
            if fraud_results:
                # Determine action based on fraud severity
                action = await self._determine_moderation_action(fraud_results)
                
                # Create moderation decision
                decision = ModerationDecision(
                    validation_id=validation.id,
                    user_id=validation.validator_id,
                    fraud_results=fraud_results,
                    action_taken=action,
                    moderator_id=None,  # Automated
                    automated=True,
                    reason=self._generate_moderation_reason(fraud_results),
                    metadata={"fraud_count": len(fraud_results)},
                    created_at=datetime.utcnow()
                )
                
                # Execute moderation action
                await self._execute_moderation_action(db, decision)
                processed_decisions.append(decision)
        
        logger.info(
            "Moderation queue processed",
            processed_count=len(processed_decisions),
            pending_count=len(pending_validations)
        )
        
        return processed_decisions
    
    async def flag_validation(
        self,
        db: AsyncSession,
        validation_id: str,
        reporter_id: str,
        reason: str,
        evidence: Optional[str] = None
    ) -> bool:
        """Flag a validation for manual review.
        
        Args:
            db: Database session
            validation_id: Validation to flag
            reporter_id: User reporting the validation
            reason: Reason for flagging
            evidence: Optional evidence
            
        Returns:
            True if successfully flagged
        """
        # Get validation
        result = await db.execute(
            select(ValidationResult).where(ValidationResult.id == validation_id)
        )
        validation = result.scalar_one_or_none()
        
        if not validation:
            return False
        
        # Update validation flags
        validation.is_flagged = True
        validation.flag_reason = reason
        
        # Record reputation event for validator
        await reputation_service.record_reputation_event(
            db, validation.validator_id, ReputationEventType.VALIDATION_FLAGGED,
            f"Validation flagged: {reason}",
            related_validation_id=validation_id,
            metadata={"reporter_id": reporter_id, "evidence": evidence}
        )
        
        # Add to moderation queue
        fraud_result = FraudDetectionResult(
            fraud_type=FraudType.LOW_QUALITY_CONTENT,
            severity=FraudSeverity.MEDIUM,
            confidence_score=0.7,
            evidence=[f"Community report: {reason}"],
            recommended_action=ModerationAction.FLAG_FOR_REVIEW,
            metadata={"reporter_id": reporter_id, "manual_flag": True},
            detected_at=datetime.utcnow()
        )
        
        decision = ModerationDecision(
            validation_id=validation_id,
            user_id=validation.validator_id,
            fraud_results=[fraud_result],
            action_taken=ModerationAction.FLAG_FOR_REVIEW,
            moderator_id=None,
            automated=False,
            reason=f"Community flagged: {reason}",
            metadata={"reporter_id": reporter_id},
            created_at=datetime.utcnow()
        )
        
        self._moderation_queue.append(decision)
        
        await db.commit()
        
        logger.info(
            "Validation flagged for review",
            validation_id=validation_id,
            reporter_id=reporter_id,
            reason=reason
        )
        
        return True
    
    async def get_fraud_statistics(
        self,
        db: AsyncSession,
        timeframe_days: int = 30
    ) -> Dict[str, Any]:
        """Get fraud detection statistics.
        
        Args:
            db: Database session
            timeframe_days: Timeframe for statistics
            
        Returns:
            Fraud statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=timeframe_days)
        
        # Get flagged validations count
        flagged_count_result = await db.execute(
            select(func.count(ValidationResult.id))
            .where(
                and_(
                    ValidationResult.is_flagged == True,
                    ValidationResult.created_at >= cutoff_date
                )
            )
        )
        flagged_count = flagged_count_result.scalar() or 0
        
        # Get total validations for comparison
        total_count_result = await db.execute(
            select(func.count(ValidationResult.id))
            .where(ValidationResult.created_at >= cutoff_date)
        )
        total_count = total_count_result.scalar() or 0
        
        # Get moderated validations count
        moderated_count_result = await db.execute(
            select(func.count(ValidationResult.id))
            .where(
                and_(
                    ValidationResult.moderator_reviewed == True,
                    ValidationResult.created_at >= cutoff_date
                )
            )
        )
        moderated_count = moderated_count_result.scalar() or 0
        
        # Calculate fraud rate
        fraud_rate = (flagged_count / total_count * 100) if total_count > 0 else 0.0
        
        return {
            "timeframe_days": timeframe_days,
            "total_validations": total_count,
            "flagged_validations": flagged_count,
            "moderated_validations": moderated_count,
            "fraud_rate_percentage": round(fraud_rate, 2),
            "pending_moderation": len(self._moderation_queue),
            "detection_cache_size": len(self._detection_cache)
        }
    
    # Private methods for fraud detection algorithms
    
    async def _detect_spam_validation(
        self,
        db: AsyncSession,
        validation: ValidationResult
    ) -> List[FraudDetectionResult]:
        """Detect spam validation patterns."""
        results = []
        evidence = []
        
        # Check validation frequency
        recent_validations = await db.execute(
            select(func.count(ValidationResult.id))
            .where(
                and_(
                    ValidationResult.validator_id == validation.validator_id,
                    ValidationResult.created_at >= datetime.utcnow() - timedelta(hours=1)
                )
            )
        )
        recent_count = recent_validations.scalar() or 0
        
        if recent_count > self.SPAM_THRESHOLDS["max_validations_per_hour"]:
            evidence.append(f"Too many validations in 1 hour: {recent_count}")
        
        # Check content length
        content_length = len(validation.comments or "")
        if content_length < self.SPAM_THRESHOLDS["min_validation_length"]:
            evidence.append(f"Very short validation: {content_length} characters")
        
        # Check for duplicate content
        similar_validations = await self._find_similar_validations(
            db, validation.validator_id, validation.comments or ""
        )
        if len(similar_validations) > 2:
            evidence.append(f"Similar content found in {len(similar_validations)} validations")
        
        if evidence:
            severity = FraudSeverity.HIGH if len(evidence) >= 2 else FraudSeverity.MEDIUM
            confidence = min(0.9, len(evidence) * 0.3)
            
            results.append(FraudDetectionResult(
                fraud_type=FraudType.SPAM_VALIDATION,
                severity=severity,
                confidence_score=confidence,
                evidence=evidence,
                recommended_action=ModerationAction.HIDE_VALIDATION if severity == FraudSeverity.HIGH else ModerationAction.FLAG_FOR_REVIEW,
                metadata={"recent_count": recent_count, "content_length": content_length},
                detected_at=datetime.utcnow()
            ))
        
        return results
    
    async def _detect_low_quality_content(
        self,
        db: AsyncSession,
        validation: ValidationResult
    ) -> List[FraudDetectionResult]:
        """Detect low-quality validation content."""
        results = []
        evidence = []
        
        content = (validation.comments or "").lower()
        
        # Check for generic phrases
        generic_count = sum(1 for phrase in self.GENERIC_PHRASES if phrase in content)
        if generic_count > self.QUALITY_THRESHOLDS["max_generic_phrases"]:
            evidence.append(f"Too many generic phrases: {generic_count}")
        
        # Check confidence score
        if validation.confidence < self.QUALITY_THRESHOLDS["min_confidence_score"]:
            evidence.append(f"Very low confidence: {validation.confidence}")
        
        # Check for missing evidence
        if not validation.evidence_links and not validation.supporting_data:
            evidence.append("No supporting evidence provided")
        
        # Check for extremely short comments
        if len(content) < self.QUALITY_THRESHOLDS["min_comment_length"]:
            evidence.append(f"Very short comment: {len(content)} characters")
        
        if evidence:
            severity = FraudSeverity.MEDIUM if len(evidence) >= 2 else FraudSeverity.LOW
            confidence = min(0.8, len(evidence) * 0.2)
            
            results.append(FraudDetectionResult(
                fraud_type=FraudType.LOW_QUALITY_CONTENT,
                severity=severity,
                confidence_score=confidence,
                evidence=evidence,
                recommended_action=ModerationAction.FLAG_FOR_REVIEW,
                metadata={"generic_count": generic_count, "content_length": len(content)},
                detected_at=datetime.utcnow()
            ))
        
        return results
    
    async def _detect_vote_manipulation(
        self,
        db: AsyncSession,
        validation: ValidationResult
    ) -> List[FraudDetectionResult]:
        """Detect vote manipulation patterns."""
        results = []
        evidence = []
        
        # Check for suspicious voting patterns
        total_votes = validation.helpful_votes + validation.unhelpful_votes
        if total_votes > 0:
            # Check for rapid voting
            # This would require tracking vote timestamps in a real implementation
            # For now, we'll check for unusual vote ratios
            
            helpful_ratio = validation.helpful_votes / total_votes
            if helpful_ratio == 1.0 and total_votes > 5:
                evidence.append("Suspiciously high helpful vote ratio")
            elif helpful_ratio == 0.0 and total_votes > 3:
                evidence.append("Suspiciously low helpful vote ratio")
        
        if evidence:
            results.append(FraudDetectionResult(
                fraud_type=FraudType.VOTE_MANIPULATION,
                severity=FraudSeverity.MEDIUM,
                confidence_score=0.6,
                evidence=evidence,
                recommended_action=ModerationAction.FLAG_FOR_REVIEW,
                metadata={"total_votes": total_votes, "helpful_ratio": helpful_ratio if total_votes > 0 else 0},
                detected_at=datetime.utcnow()
            ))
        
        return results
    
    async def _detect_fake_expertise(
        self,
        db: AsyncSession,
        validation: ValidationResult
    ) -> List[FraudDetectionResult]:
        """Detect fake expertise claims."""
        results = []
        evidence = []
        
        # Check if user claims expertise but has low-quality validations
        if validation.expertise_relevance and validation.expertise_relevance > 7.0:
            # Get user's other validations in similar domains
            user_validations = await db.execute(
                select(ValidationResult)
                .where(
                    and_(
                        ValidationResult.validator_id == validation.validator_id,
                        ValidationResult.validation_type == validation.validation_type
                    )
                )
                .limit(10)
            )
            validations = user_validations.scalars().all()
            
            if len(validations) > 3:
                avg_quality = sum(v.helpful_votes - v.unhelpful_votes for v in validations) / len(validations)
                if avg_quality < -1:
                    evidence.append("High expertise claim but low validation quality")
        
        if evidence:
            results.append(FraudDetectionResult(
                fraud_type=FraudType.FAKE_EXPERTISE,
                severity=FraudSeverity.MEDIUM,
                confidence_score=0.7,
                evidence=evidence,
                recommended_action=ModerationAction.REQUIRE_VERIFICATION,
                metadata={"expertise_relevance": validation.expertise_relevance},
                detected_at=datetime.utcnow()
            ))
        
        return results
    
    async def _detect_reputation_farming(
        self,
        db: AsyncSession,
        validation: ValidationResult
    ) -> List[FraudDetectionResult]:
        """Detect reputation farming behavior."""
        results = []
        evidence = []
        
        # Get user's reputation growth rate
        user_events = await db.execute(
            select(ReputationEvent)
            .where(
                and_(
                    ReputationEvent.user_id == validation.validator_id,
                    ReputationEvent.created_at >= datetime.utcnow() - timedelta(days=7)
                )
            )
        )
        events = user_events.scalars().all()
        
        if events:
            total_points = sum(event.points_change for event in events)
            daily_rate = total_points / 7
            
            if daily_rate > self.REPUTATION_THRESHOLDS["suspicious_growth_rate"]:
                evidence.append(f"Suspicious reputation growth: {daily_rate:.1f} points/day")
        
        # Check validation diversity
        user_validations = await db.execute(
            select(ValidationResult.validation_type)
            .where(ValidationResult.validator_id == validation.validator_id)
            .distinct()
        )
        unique_types = len(user_validations.scalars().all())
        
        total_validations_result = await db.execute(
            select(func.count(ValidationResult.id))
            .where(ValidationResult.validator_id == validation.validator_id)
        )
        total_validations = total_validations_result.scalar() or 0
        
        if total_validations > 10:
            diversity_ratio = unique_types / min(5, total_validations)  # Max 5 validation types
            if diversity_ratio < self.REPUTATION_THRESHOLDS["min_validation_diversity"]:
                evidence.append(f"Low validation diversity: {diversity_ratio:.2f}")
        
        if evidence:
            results.append(FraudDetectionResult(
                fraud_type=FraudType.REPUTATION_FARMING,
                severity=FraudSeverity.HIGH,
                confidence_score=0.8,
                evidence=evidence,
                recommended_action=ModerationAction.REDUCE_INFLUENCE,
                metadata={"daily_rate": daily_rate if events else 0, "diversity_ratio": diversity_ratio if total_validations > 10 else 1.0},
                detected_at=datetime.utcnow()
            ))
        
        return results
    
    async def _detect_coordinated_abuse(
        self,
        db: AsyncSession,
        user_id: str,
        behavior_data: Dict[str, Any]
    ) -> List[FraudDetectionResult]:
        """Detect coordinated abuse patterns."""
        results = []
        # This would require more sophisticated analysis of user networks
        # For now, return empty list
        return results
    
    async def _detect_sockpuppeting(
        self,
        db: AsyncSession,
        user_id: str,
        behavior_data: Dict[str, Any]
    ) -> List[FraudDetectionResult]:
        """Detect sockpuppet accounts."""
        results = []
        # This would require IP tracking and behavioral analysis
        # For now, return empty list
        return results
    
    async def _detect_duplicate_accounts(
        self,
        db: AsyncSession,
        user_id: str,
        behavior_data: Dict[str, Any]
    ) -> List[FraudDetectionResult]:
        """Detect duplicate accounts."""
        results = []
        # This would require email/IP analysis
        # For now, return empty list
        return results
    
    async def _get_user_behavior_data(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive user behavior data."""
        # Get validation patterns
        validations_result = await db.execute(
            select(ValidationResult)
            .where(ValidationResult.validator_id == user_id)
            .order_by(desc(ValidationResult.created_at))
            .limit(100)
        )
        validations = validations_result.scalars().all()
        
        # Get reputation events
        events_result = await db.execute(
            select(ReputationEvent)
            .where(ReputationEvent.user_id == user_id)
            .order_by(desc(ReputationEvent.created_at))
            .limit(100)
        )
        events = events_result.scalars().all()
        
        return {
            "validations": validations,
            "reputation_events": events,
            "validation_count": len(validations),
            "total_reputation": sum(event.points_change for event in events),
            "account_age_days": (datetime.utcnow() - validations[-1].created_at).days if validations else 0
        }
    
    async def _find_similar_validations(
        self,
        db: AsyncSession,
        user_id: str,
        content: str
    ) -> List[ValidationResult]:
        """Find validations with similar content."""
        if not content or len(content) < 20:
            return []
        
        # Simple similarity check - in production would use more sophisticated NLP
        content_words = set(content.lower().split())
        
        user_validations = await db.execute(
            select(ValidationResult)
            .where(ValidationResult.validator_id == user_id)
            .limit(50)
        )
        validations = user_validations.scalars().all()
        
        similar = []
        for validation in validations:
            if validation.comments:
                other_words = set(validation.comments.lower().split())
                if content_words and other_words:
                    similarity = len(content_words & other_words) / len(content_words | other_words)
                    if similarity > self.SPAM_THRESHOLDS["duplicate_content_threshold"]:
                        similar.append(validation)
        
        return similar
    
    async def _get_pending_moderation_items(
        self,
        db: AsyncSession,
        limit: int
    ) -> List[ValidationResult]:
        """Get validations that need moderation review."""
        result = await db.execute(
            select(ValidationResult)
            .where(
                and_(
                    ValidationResult.is_flagged == True,
                    ValidationResult.moderator_reviewed == False
                )
            )
            .order_by(desc(ValidationResult.created_at))
            .limit(limit)
        )
        return result.scalars().all()
    
    async def _determine_moderation_action(
        self,
        fraud_results: List[FraudDetectionResult]
    ) -> ModerationAction:
        """Determine appropriate moderation action based on fraud results."""
        if not fraud_results:
            return ModerationAction.NO_ACTION
        
        # Get highest severity
        max_severity = max(result.severity for result in fraud_results)
        high_confidence_count = sum(1 for result in fraud_results if result.confidence_score > 0.8)
        
        if max_severity == FraudSeverity.CRITICAL:
            return ModerationAction.SUSPEND_USER
        elif max_severity == FraudSeverity.HIGH and high_confidence_count >= 2:
            return ModerationAction.HIDE_VALIDATION
        elif max_severity == FraudSeverity.HIGH:
            return ModerationAction.REDUCE_INFLUENCE
        elif max_severity == FraudSeverity.MEDIUM and high_confidence_count >= 1:
            return ModerationAction.FLAG_FOR_REVIEW
        else:
            return ModerationAction.WARN_USER
    
    def _generate_moderation_reason(
        self,
        fraud_results: List[FraudDetectionResult]
    ) -> str:
        """Generate human-readable moderation reason."""
        if not fraud_results:
            return "No issues detected"
        
        fraud_types = [result.fraud_type.value.replace("_", " ").title() for result in fraud_results]
        return f"Automated detection: {', '.join(fraud_types)}"
    
    async def _execute_moderation_action(
        self,
        db: AsyncSession,
        decision: ModerationDecision
    ) -> None:
        """Execute a moderation action."""
        validation_result = await db.execute(
            select(ValidationResult).where(ValidationResult.id == decision.validation_id)
        )
        validation = validation_result.scalar_one_or_none()
        
        if not validation:
            return
        
        if decision.action_taken == ModerationAction.FLAG_FOR_REVIEW:
            validation.is_flagged = True
            validation.flag_reason = decision.reason
        
        elif decision.action_taken == ModerationAction.HIDE_VALIDATION:
            validation.is_flagged = True
            validation.moderator_reviewed = True
            validation.flag_reason = decision.reason
        
        elif decision.action_taken == ModerationAction.DELETE_VALIDATION:
            # In a real system, we might soft-delete instead
            await db.delete(validation)
        
        elif decision.action_taken == ModerationAction.REDUCE_INFLUENCE:
            # Reduce user's influence weight
            summary_result = await db.execute(
                select(ReputationSummary).where(ReputationSummary.user_id == decision.user_id)
            )
            summary = summary_result.scalar_one_or_none()
            if summary:
                summary.influence_weight = max(0.1, summary.influence_weight * 0.8)
        
        elif decision.action_taken == ModerationAction.WARN_USER:
            # Record warning in reputation events
            await reputation_service.record_reputation_event(
                db, decision.user_id, ReputationEventType.PENALTY_APPLIED,
                f"Warning: {decision.reason}",
                points_override=-5.0,
                metadata={"warning": True, "automated": decision.automated}
            )
        
        # Record moderation event
        await reputation_service.record_reputation_event(
            db, decision.user_id, ReputationEventType.VALIDATION_MODERATED,
            f"Moderation action: {decision.action_taken.value}",
            related_validation_id=decision.validation_id,
            metadata={
                "action": decision.action_taken.value,
                "automated": decision.automated,
                "fraud_types": [r.fraud_type.value for r in decision.fraud_results]
            }
        )
        
        await db.commit()
        
        logger.info(
            "Moderation action executed",
            validation_id=decision.validation_id,
            user_id=decision.user_id,
            action=decision.action_taken.value,
            automated=decision.automated
        )


# Global fraud detection service instance
fraud_detection_service = FraudDetectionService()