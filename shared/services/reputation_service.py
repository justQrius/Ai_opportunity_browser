"""Reputation service for community engagement and expert verification.

Supports Requirements 4.3-4.4 (Community Engagement Platform):
- Track contribution history and accuracy
- Increase influence weight for quality validation
- Award badges and reputation points
"""

import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload, joinedload

from shared.models.reputation import (
    ReputationEvent, 
    ReputationEventType, 
    UserBadge, 
    BadgeType, 
    ExpertiseVerification,
    ReputationSummary
)
from shared.models.user import User, UserRole
from shared.models.validation import ValidationResult
from shared.schemas.reputation import (
    ReputationEventCreate,
    BadgeCreate,
    ExpertiseVerificationCreate,
    ExpertiseVerificationUpdate,
    ReputationSummaryResponse
)
from shared.cache import cache_manager, CacheKeys
import structlog

logger = structlog.get_logger(__name__)


class ReputationService:
    """Service for reputation management and community engagement."""
    
    # Reputation point values for different actions
    REPUTATION_POINTS = {
        ReputationEventType.VALIDATION_SUBMITTED: 5.0,
        ReputationEventType.VALIDATION_HELPFUL: 2.0,
        ReputationEventType.VALIDATION_UNHELPFUL: -1.0,
        ReputationEventType.VALIDATION_FLAGGED: -5.0,
        ReputationEventType.VALIDATION_MODERATED: 0.0,  # Depends on outcome
        ReputationEventType.EXPERT_VERIFICATION: 20.0,
        ReputationEventType.BADGE_EARNED: 10.0,
        ReputationEventType.PENALTY_APPLIED: -10.0,
    }
    
    # Expert verification methods and their credibility scores
    VERIFICATION_METHODS = {
        "linkedin": {"credibility": 0.8, "auto_verify": True},
        "github": {"credibility": 0.7, "auto_verify": True},
        "academic": {"credibility": 0.9, "auto_verify": False},
        "certification": {"credibility": 0.85, "auto_verify": False},
        "employment": {"credibility": 0.9, "auto_verify": False},
        "portfolio": {"credibility": 0.6, "auto_verify": True},
        "peer_endorsement": {"credibility": 0.7, "auto_verify": False},
        "manual_review": {"credibility": 1.0, "auto_verify": False}
    }
    
    # Badge requirements
    BADGE_REQUIREMENTS = {
        BadgeType.FIRST_VALIDATION: {"validations": 1},
        BadgeType.HELPFUL_VALIDATOR: {"helpful_ratio": 0.8, "min_votes": 10},
        BadgeType.EXPERT_CONTRIBUTOR: {"verified_domains": 1, "validations": 10},
        BadgeType.QUALITY_REVIEWER: {"accuracy_score": 0.9, "validations": 25},
        BadgeType.COMMUNITY_MODERATOR: {"role": UserRole.MODERATOR},
        BadgeType.DOMAIN_EXPERT: {"verified_domains": 3, "expertise_score": 8.0},
        BadgeType.PROLIFIC_CONTRIBUTOR: {"validations": 100},
        BadgeType.ACCURACY_CHAMPION: {"accuracy_score": 0.95, "validations": 50},
    }
    
    async def record_reputation_event(
        self,
        db: AsyncSession,
        user_id: str,
        event_type: ReputationEventType,
        description: str,
        points_override: Optional[float] = None,
        related_validation_id: Optional[str] = None,
        related_opportunity_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReputationEvent:
        """Record a reputation event for a user.
        
        Args:
            db: Database session
            user_id: User identifier
            event_type: Type of reputation event
            description: Human-readable description
            points_override: Override default points for this event
            related_validation_id: Optional related validation
            related_opportunity_id: Optional related opportunity
            metadata: Additional context data
            
        Returns:
            Created reputation event
        """
        # Calculate points
        points_change = points_override if points_override is not None else self.REPUTATION_POINTS.get(event_type, 0.0)
        
        # Prepare event metadata
        event_metadata_json = None
        if metadata:
            event_metadata_json = json.dumps(metadata)
        
        # Create reputation event
        event = ReputationEvent(
            user_id=user_id,
            event_type=event_type,
            points_change=points_change,
            description=description,
            related_validation_id=related_validation_id,
            related_opportunity_id=related_opportunity_id,
            event_metadata=event_metadata_json
        )
        
        db.add(event)
        await db.commit()
        await db.refresh(event)
        
        logger.info(
            "Reputation event recorded",
            user_id=user_id,
            event_type=event_type,
            points_change=points_change,
            event_id=event.id
        )
        
        # Update user's reputation summary
        await self.update_reputation_summary(db, user_id)
        
        # Check for new badges
        await self.check_and_award_badges(db, user_id)
        
        return event
    
    async def update_reputation_summary(
        self,
        db: AsyncSession,
        user_id: str
    ) -> ReputationSummary:
        """Update or create reputation summary for a user.
        
        Args:
            db: Database session
            user_id: User identifier
            
        Returns:
            Updated reputation summary
        """
        # Get or create reputation summary
        result = await db.execute(
            select(ReputationSummary).where(ReputationSummary.user_id == user_id)
        )
        summary = result.scalar_one_or_none()
        
        if not summary:
            summary = ReputationSummary(user_id=user_id)
            db.add(summary)
        
        # Calculate total reputation points
        points_result = await db.execute(
            select(func.sum(ReputationEvent.points_change))
            .where(ReputationEvent.user_id == user_id)
        )
        total_points = points_result.scalar() or 0.0
        
        # Get validation metrics
        validation_stats = await db.execute(
            select(
                func.count(ValidationResult.id).label("total_validations"),
                func.sum(ValidationResult.helpful_votes).label("helpful_votes"),
                func.sum(ValidationResult.unhelpful_votes).label("unhelpful_votes")
            )
            .where(ValidationResult.validator_id == user_id)
        )
        val_stats = validation_stats.first()
        
        total_validations = val_stats.total_validations or 0
        helpful_votes = val_stats.helpful_votes or 0
        unhelpful_votes = val_stats.unhelpful_votes or 0
        total_votes = helpful_votes + unhelpful_votes
        
        # Calculate accuracy score (simplified - would be more complex in production)
        accuracy_score = (helpful_votes / total_votes * 100) if total_votes > 0 else 0.0
        
        # Get badge count
        badge_count_result = await db.execute(
            select(func.count(UserBadge.id))
            .where(UserBadge.user_id == user_id)
        )
        badges_earned = badge_count_result.scalar() or 0
        
        # Get verified domains count
        verified_domains_result = await db.execute(
            select(func.count(ExpertiseVerification.id))
            .where(
                and_(
                    ExpertiseVerification.user_id == user_id,
                    ExpertiseVerification.verification_status == "verified"
                )
            )
        )
        verified_domains = verified_domains_result.scalar() or 0
        
        # Calculate average expertise score
        expertise_avg_result = await db.execute(
            select(func.avg(ExpertiseVerification.expertise_score))
            .where(
                and_(
                    ExpertiseVerification.user_id == user_id,
                    ExpertiseVerification.verification_status == "verified"
                )
            )
        )
        avg_expertise_score = expertise_avg_result.scalar() or 0.0
        
        # Calculate influence weight (1.0 base, modified by reputation and accuracy)
        influence_weight = 1.0
        if total_points > 100:
            influence_weight += min(0.5, total_points / 1000)  # Up to +0.5 for high reputation
        if accuracy_score > 80:
            influence_weight += min(0.3, (accuracy_score - 80) / 100)  # Up to +0.3 for high accuracy
        if verified_domains > 0:
            influence_weight += min(0.2, verified_domains * 0.1)  # Up to +0.2 for expertise
        
        influence_weight = min(2.0, max(0.1, influence_weight))  # Clamp between 0.1 and 2.0
        
        # Calculate quality score
        quality_score = 5.0  # Base score
        if accuracy_score > 70:
            quality_score += (accuracy_score - 70) / 10  # Up to +3 for accuracy
        if verified_domains > 0:
            quality_score += min(2.0, verified_domains * 0.5)  # Up to +2 for expertise
        quality_score = min(10.0, max(1.0, quality_score))
        
        # Update summary fields
        summary.total_reputation_points = total_points
        summary.influence_weight = round(influence_weight, 2)
        summary.total_validations = total_validations
        summary.helpful_validations = helpful_votes
        summary.accuracy_score = round(accuracy_score, 1)
        summary.total_votes_received = total_votes
        summary.helpful_votes_received = helpful_votes
        summary.badges_earned = badges_earned
        summary.verified_domains = verified_domains
        summary.average_expertise_score = round(avg_expertise_score, 1)
        summary.quality_score = round(quality_score, 1)
        summary.last_activity_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(summary)
        
        # Update global reputation rank
        await self._update_reputation_ranks(db)
        
        logger.info(
            "Reputation summary updated",
            user_id=user_id,
            total_points=total_points,
            influence_weight=influence_weight,
            quality_score=quality_score
        )
        
        return summary
    
    async def check_and_award_badges(
        self,
        db: AsyncSession,
        user_id: str
    ) -> List[UserBadge]:
        """Check if user qualifies for new badges and award them.
        
        Args:
            db: Database session
            user_id: User identifier
            
        Returns:
            List of newly awarded badges
        """
        # Get user and current badges
        user_result = await db.execute(
            select(User).options(
                selectinload(User.badges),
                selectinload(User.reputation_summary),
                selectinload(User.expertise_verifications)
            ).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return []
        
        current_badge_types = {badge.badge_type for badge in user.badges}
        new_badges = []
        
        # Get user stats
        summary = user.reputation_summary
        if not summary:
            return []
        
        # Check each badge type
        for badge_type, requirements in self.BADGE_REQUIREMENTS.items():
            if badge_type in current_badge_types:
                continue  # User already has this badge
            
            # Check if user meets requirements
            qualifies = True
            
            if "validations" in requirements:
                if summary.total_validations < requirements["validations"]:
                    qualifies = False
            
            if "helpful_ratio" in requirements and "min_votes" in requirements:
                if summary.total_votes_received < requirements["min_votes"]:
                    qualifies = False
                elif summary.total_votes_received > 0:
                    helpful_ratio = summary.helpful_votes_received / summary.total_votes_received
                    if helpful_ratio < requirements["helpful_ratio"]:
                        qualifies = False
            
            if "accuracy_score" in requirements:
                if summary.accuracy_score / 100 < requirements["accuracy_score"]:
                    qualifies = False
            
            if "verified_domains" in requirements:
                if summary.verified_domains < requirements["verified_domains"]:
                    qualifies = False
            
            if "expertise_score" in requirements:
                if summary.average_expertise_score < requirements["expertise_score"]:
                    qualifies = False
            
            if "role" in requirements:
                if user.role != requirements["role"]:
                    qualifies = False
            
            # Award badge if qualified
            if qualifies:
                badge = await self._create_badge(db, user_id, badge_type)
                new_badges.append(badge)
                
                # Record reputation event for badge
                await self.record_reputation_event(
                    db, user_id, ReputationEventType.BADGE_EARNED,
                    f"Earned badge: {badge.title}",
                    metadata={"badge_type": badge_type.value}
                )
        
        return new_badges
    
    async def initiate_expert_verification(
        self,
        db: AsyncSession,
        user_id: str,
        domain: str,
        verification_method: str,
        evidence_url: Optional[str] = None,
        credentials: Optional[str] = None,
        years_experience: Optional[int] = None
    ) -> ExpertiseVerification:
        """Initiate expert verification process for a user.
        
        Args:
            db: Database session
            user_id: User identifier
            domain: Domain of expertise
            verification_method: How expertise will be verified
            evidence_url: URL to evidence
            credentials: Credential details
            years_experience: Years of experience
            
        Returns:
            Created expertise verification
        """
        # Validate verification method
        if verification_method not in self.VERIFICATION_METHODS:
            raise ValueError(f"Invalid verification method: {verification_method}")
        
        method_config = self.VERIFICATION_METHODS[verification_method]
        
        # Check if verification already exists
        existing_result = await db.execute(
            select(ExpertiseVerification).where(
                and_(
                    ExpertiseVerification.user_id == user_id,
                    ExpertiseVerification.domain == domain
                )
            )
        )
        existing_verification = existing_result.scalar_one_or_none()
        
        if existing_verification and existing_verification.verification_status == "verified":
            logger.info(
                "User already has verified expertise in domain",
                user_id=user_id,
                domain=domain
            )
            return existing_verification
        
        # Calculate initial expertise score based on evidence
        expertise_score = self._calculate_expertise_score(
            verification_method, evidence_url, credentials, years_experience
        )
        
        # Create or update verification
        if existing_verification:
            verification = existing_verification
            verification.verification_method = verification_method
            verification.evidence_url = evidence_url
            verification.credentials = credentials
            verification.years_experience = years_experience
            verification.expertise_score = expertise_score
            verification.confidence_level = method_config["credibility"] * 10
        else:
            verification = ExpertiseVerification(
                user_id=user_id,
                domain=domain,
                verification_method=verification_method,
                evidence_url=evidence_url,
                credentials=credentials,
                years_experience=years_experience,
                expertise_score=expertise_score,
                confidence_level=method_config["credibility"] * 10,
                verification_status="pending"
            )
            db.add(verification)
        
        # Auto-verify if method supports it
        if method_config["auto_verify"]:
            verification.verification_status = "verified"
            verification.verified_at = datetime.utcnow()
            
            # Record reputation event
            await self.record_reputation_event(
                db, user_id, ReputationEventType.EXPERT_VERIFICATION,
                f"Expertise auto-verified in {domain} via {verification_method}",
                metadata={"domain": domain, "method": verification_method, "auto_verified": True}
            )
        
        await db.commit()
        await db.refresh(verification)
        
        logger.info(
            "Expert verification initiated",
            user_id=user_id,
            domain=domain,
            method=verification_method,
            status=verification.verification_status,
            verification_id=verification.id
        )
        
        return verification
    
    async def verify_expertise(
        self,
        db: AsyncSession,
        user_id: str,
        domain: str,
        verification_method: str,
        evidence_url: Optional[str] = None,
        credentials: Optional[str] = None,
        years_experience: Optional[int] = None,
        verifier_id: Optional[str] = None
    ) -> ExpertiseVerification:
        """Create or update expertise verification for a user.
        
        Args:
            db: Database session
            user_id: User identifier
            domain: Domain of expertise
            verification_method: How expertise was verified
            evidence_url: URL to evidence
            credentials: Credential details
            years_experience: Years of experience
            verifier_id: ID of verifying admin/moderator
            
        Returns:
            Created or updated expertise verification
        """
        # Check if verification already exists
        existing_result = await db.execute(
            select(ExpertiseVerification).where(
                and_(
                    ExpertiseVerification.user_id == user_id,
                    ExpertiseVerification.domain == domain
                )
            )
        )
        verification = existing_result.scalar_one_or_none()
        
        if verification:
            # Update existing verification
            verification.verification_method = verification_method
            verification.evidence_url = evidence_url
            verification.credentials = credentials
            verification.years_experience = years_experience
            if verifier_id:
                verification.verified_by = verifier_id
                verification.verified_at = datetime.utcnow()
                verification.verification_status = "verified"
        else:
            # Create new verification
            verification = ExpertiseVerification(
                user_id=user_id,
                domain=domain,
                verification_method=verification_method,
                evidence_url=evidence_url,
                credentials=credentials,
                years_experience=years_experience,
                verified_by=verifier_id,
                verification_status="verified" if verifier_id else "pending"
            )
            if verifier_id:
                verification.verified_at = datetime.utcnow()
            
            db.add(verification)
        
        await db.commit()
        await db.refresh(verification)
        
        # If verified, record reputation event
        if verification.verification_status == "verified":
            await self.record_reputation_event(
                db, user_id, ReputationEventType.EXPERT_VERIFICATION,
                f"Expertise verified in {domain}",
                metadata={"domain": domain, "method": verification_method}
            )
        
        logger.info(
            "Expertise verification created/updated",
            user_id=user_id,
            domain=domain,
            status=verification.verification_status,
            verification_id=verification.id
        )
        
        return verification
    
    async def get_user_reputation_summary(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[ReputationSummary]:
        """Get reputation summary for a user.
        
        Args:
            db: Database session
            user_id: User identifier
            
        Returns:
            Reputation summary or None
        """
        result = await db.execute(
            select(ReputationSummary).where(ReputationSummary.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_influence_weight(
        self,
        db: AsyncSession,
        user_id: str
    ) -> float:
        """Get user's influence weight for validation scoring.
        
        Args:
            db: Database session
            user_id: User identifier
            
        Returns:
            Influence weight (0.1-2.0)
        """
        summary = await self.get_user_reputation_summary(db, user_id)
        return summary.influence_weight if summary else 1.0
    
    async def get_reputation_leaderboard(
        self,
        db: AsyncSession,
        limit: int = 50,
        timeframe_days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get reputation leaderboard.
        
        Args:
            db: Database session
            limit: Maximum results to return
            timeframe_days: Optional timeframe filter
            
        Returns:
            List of leaderboard entries
        """
        query = select(
            ReputationSummary,
            User.username,
            User.avatar_url
        ).join(
            User, ReputationSummary.user_id == User.id
        ).order_by(
            desc(ReputationSummary.total_reputation_points)
        ).limit(limit)
        
        result = await db.execute(query)
        entries = result.all()
        
        leaderboard = []
        for i, (summary, username, avatar_url) in enumerate(entries, 1):
            leaderboard.append({
                "rank": i,
                "user_id": summary.user_id,
                "username": username,
                "avatar_url": avatar_url,
                "reputation_points": summary.total_reputation_points,
                "influence_weight": summary.influence_weight,
                "total_validations": summary.total_validations,
                "accuracy_score": summary.accuracy_score,
                "badges_earned": summary.badges_earned,
                "verified_domains": summary.verified_domains
            })
        
        return leaderboard
    
    async def track_validation_feedback(
        self,
        db: AsyncSession,
        validation_id: str,
        feedback_type: str,
        feedback_user_id: str
    ) -> None:
        """Track feedback on validation and update reputation.
        
        Args:
            db: Database session
            validation_id: Validation that received feedback
            feedback_type: Type of feedback (helpful/unhelpful)
            feedback_user_id: User providing feedback
        """
        # Get validation
        result = await db.execute(
            select(ValidationResult).where(ValidationResult.id == validation_id)
        )
        validation = result.scalar_one_or_none()
        
        if not validation:
            return
        
        # Update validation vote counts
        if feedback_type == "helpful":
            validation.helpful_votes += 1
            event_type = ReputationEventType.VALIDATION_HELPFUL
            description = "Validation marked as helpful"
            points = 2.0
        else:
            validation.unhelpful_votes += 1
            event_type = ReputationEventType.VALIDATION_UNHELPFUL
            description = "Validation marked as unhelpful"
            points = -1.0
        
        await db.commit()
        
        # Record reputation event for validator
        await self.record_reputation_event(
            db, validation.validator_id, event_type, description,
            points_override=points,
            related_validation_id=validation_id,
            metadata={"feedback_user_id": feedback_user_id}
        )
    
    async def calculate_validation_quality_score(
        self,
        db: AsyncSession,
        validation_id: str
    ) -> float:
        """Calculate quality score for a validation.
        
        Args:
            db: Database session
            validation_id: Validation identifier
            
        Returns:
            Quality score (0.0-10.0)
        """
        result = await db.execute(
            select(ValidationResult).where(ValidationResult.id == validation_id)
        )
        validation = result.scalar_one_or_none()
        
        if not validation:
            return 0.0
        
        quality_score = 5.0  # Base score
        
        # Evidence quality
        if validation.evidence_links:
            try:
                links = json.loads(validation.evidence_links)
                quality_score += min(2.0, len(links) * 0.5)
            except json.JSONDecodeError:
                pass
        
        # Completeness
        if validation.comments:
            quality_score += 0.5
        if validation.strengths:
            quality_score += 0.5
        if validation.weaknesses:
            quality_score += 0.5
        if validation.recommendations:
            quality_score += 0.5
        if validation.methodology:
            quality_score += 0.5
        
        # Community feedback
        total_votes = validation.helpful_votes + validation.unhelpful_votes
        if total_votes > 0:
            helpful_ratio = validation.helpful_votes / total_votes
            quality_score += (helpful_ratio - 0.5) * 2.0
        
        # Confidence factor
        confidence_factor = validation.confidence / 10.0
        quality_score *= confidence_factor
        
        return max(0.0, min(10.0, quality_score))
    
    async def get_user_reputation_history(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        event_type_filter: Optional[ReputationEventType] = None
    ) -> List[ReputationEvent]:
        """Get user's reputation event history.
        
        Args:
            db: Database session
            user_id: User identifier
            limit: Maximum events to return
            event_type_filter: Optional event type filter
            
        Returns:
            List of reputation events
        """
        query = select(ReputationEvent).where(
            ReputationEvent.user_id == user_id
        ).order_by(desc(ReputationEvent.created_at)).limit(limit)
        
        if event_type_filter:
            query = query.where(ReputationEvent.event_type == event_type_filter)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_reputation_analytics(
        self,
        db: AsyncSession,
        timeframe_days: int = 30
    ) -> Dict[str, Any]:
        """Get reputation system analytics.
        
        Args:
            db: Database session
            timeframe_days: Timeframe for analytics
            
        Returns:
            Analytics data
        """
        cutoff_date = datetime.utcnow() - timedelta(days=timeframe_days)
        
        # Total users with reputation
        total_users_result = await db.execute(
            select(func.count(ReputationSummary.id))
        )
        total_users = total_users_result.scalar() or 0
        
        # Total reputation points
        total_points_result = await db.execute(
            select(func.sum(ReputationSummary.total_reputation_points))
        )
        total_points = total_points_result.scalar() or 0.0
        
        # Average reputation
        avg_reputation = total_points / total_users if total_users > 0 else 0.0
        
        # Total badges awarded
        total_badges_result = await db.execute(
            select(func.count(UserBadge.id))
        )
        total_badges = total_badges_result.scalar() or 0
        
        # Total verifications
        total_verifications_result = await db.execute(
            select(func.count(ExpertiseVerification.id)).where(
                ExpertiseVerification.verification_status == "verified"
            )
        )
        total_verifications = total_verifications_result.scalar() or 0
        
        # Top domains
        top_domains_result = await db.execute(
            select(
                ExpertiseVerification.domain,
                func.count(ExpertiseVerification.id).label("count")
            ).where(
                ExpertiseVerification.verification_status == "verified"
            ).group_by(ExpertiseVerification.domain).order_by(
                desc(func.count(ExpertiseVerification.id))
            ).limit(10)
        )
        top_domains = [{"domain": row[0], "count": row[1]} for row in top_domains_result]
        
        # Recent activity
        recent_events_result = await db.execute(
            select(func.count(ReputationEvent.id)).where(
                ReputationEvent.created_at >= cutoff_date
            )
        )
        recent_activity = recent_events_result.scalar() or 0
        
        return {
            "total_users": total_users,
            "total_reputation_points": total_points,
            "average_reputation": round(avg_reputation, 2),
            "total_badges_awarded": total_badges,
            "total_verifications": total_verifications,
            "top_domains": top_domains,
            "recent_activity": recent_activity,
            "timeframe_days": timeframe_days,
            "generated_at": datetime.utcnow()
        }
    
    async def _create_badge(
        self,
        db: AsyncSession,
        user_id: str,
        badge_type: BadgeType
    ) -> UserBadge:
        """Create a badge for a user.
        
        Args:
            db: Database session
            user_id: User identifier
            badge_type: Type of badge to create
            
        Returns:
            Created badge
        """
        # Badge definitions
        badge_definitions = {
            BadgeType.FIRST_VALIDATION: {
                "title": "First Validator",
                "description": "Submitted your first validation",
                "color": "#4CAF50"
            },
            BadgeType.HELPFUL_VALIDATOR: {
                "title": "Helpful Validator",
                "description": "Consistently provides helpful validations",
                "color": "#2196F3"
            },
            BadgeType.EXPERT_CONTRIBUTOR: {
                "title": "Expert Contributor",
                "description": "Verified expert with quality contributions",
                "color": "#FF9800"
            },
            BadgeType.QUALITY_REVIEWER: {
                "title": "Quality Reviewer",
                "description": "High accuracy in validation reviews",
                "color": "#9C27B0"
            },
            BadgeType.COMMUNITY_MODERATOR: {
                "title": "Community Moderator",
                "description": "Trusted community moderator",
                "color": "#F44336"
            },
            BadgeType.DOMAIN_EXPERT: {
                "title": "Domain Expert",
                "description": "Verified expertise in multiple domains",
                "color": "#795548"
            },
            BadgeType.PROLIFIC_CONTRIBUTOR: {
                "title": "Prolific Contributor",
                "description": "Submitted 100+ validations",
                "color": "#607D8B"
            },
            BadgeType.ACCURACY_CHAMPION: {
                "title": "Accuracy Champion",
                "description": "Exceptional validation accuracy",
                "color": "#FFD700"
            }
        }
        
        definition = badge_definitions.get(badge_type, {
            "title": badge_type.value.replace("_", " ").title(),
            "description": f"Earned {badge_type.value} badge",
            "color": "#666666"
        })
        
        badge = UserBadge(
            user_id=user_id,
            badge_type=badge_type,
            title=definition["title"],
            description=definition["description"],
            color=definition["color"]
        )
        
        db.add(badge)
        await db.commit()
        await db.refresh(badge)
        
        logger.info(
            "Badge awarded",
            user_id=user_id,
            badge_type=badge_type,
            badge_id=badge.id
        )
        
        return badge
    
    async def approve_expert_verification(
        self,
        db: AsyncSession,
        verification_id: str,
        verifier_id: str,
        verification_notes: Optional[str] = None,
        expertise_score_override: Optional[float] = None
    ) -> ExpertiseVerification:
        """Approve a pending expert verification.
        
        Args:
            db: Database session
            verification_id: Verification identifier
            verifier_id: ID of admin/moderator approving
            verification_notes: Optional notes from verifier
            expertise_score_override: Optional score override
            
        Returns:
            Updated verification
        """
        # Get verification
        result = await db.execute(
            select(ExpertiseVerification).where(ExpertiseVerification.id == verification_id)
        )
        verification = result.scalar_one_or_none()
        
        if not verification:
            raise ValueError(f"Verification {verification_id} not found")
        
        if verification.verification_status == "verified":
            logger.info(
                "Verification already approved",
                verification_id=verification_id
            )
            return verification
        
        # Update verification
        verification.verification_status = "verified"
        verification.verified_by = verifier_id
        verification.verified_at = datetime.utcnow()
        verification.verification_notes = verification_notes
        
        if expertise_score_override:
            verification.expertise_score = expertise_score_override
        
        await db.commit()
        await db.refresh(verification)
        
        # Record reputation event
        await self.record_reputation_event(
            db, verification.user_id, ReputationEventType.EXPERT_VERIFICATION,
            f"Expertise verified in {verification.domain}",
            metadata={
                "domain": verification.domain, 
                "method": verification.verification_method,
                "verifier_id": verifier_id
            }
        )
        
        logger.info(
            "Expert verification approved",
            verification_id=verification_id,
            user_id=verification.user_id,
            domain=verification.domain,
            verifier_id=verifier_id
        )
        
        return verification
    
    async def reject_expert_verification(
        self,
        db: AsyncSession,
        verification_id: str,
        verifier_id: str,
        rejection_reason: str
    ) -> ExpertiseVerification:
        """Reject a pending expert verification.
        
        Args:
            db: Database session
            verification_id: Verification identifier
            verifier_id: ID of admin/moderator rejecting
            rejection_reason: Reason for rejection
            
        Returns:
            Updated verification
        """
        # Get verification
        result = await db.execute(
            select(ExpertiseVerification).where(ExpertiseVerification.id == verification_id)
        )
        verification = result.scalar_one_or_none()
        
        if not verification:
            raise ValueError(f"Verification {verification_id} not found")
        
        # Update verification
        verification.verification_status = "rejected"
        verification.verified_by = verifier_id
        verification.verified_at = datetime.utcnow()
        verification.verification_notes = rejection_reason
        
        await db.commit()
        await db.refresh(verification)
        
        logger.info(
            "Expert verification rejected",
            verification_id=verification_id,
            user_id=verification.user_id,
            domain=verification.domain,
            reason=rejection_reason
        )
        
        return verification
    
    async def get_pending_verifications(
        self,
        db: AsyncSession,
        limit: int = 50,
        domain_filter: Optional[str] = None
    ) -> List[ExpertiseVerification]:
        """Get pending expert verifications for review.
        
        Args:
            db: Database session
            limit: Maximum results to return
            domain_filter: Optional domain filter
            
        Returns:
            List of pending verifications
        """
        query = select(ExpertiseVerification).where(
            ExpertiseVerification.verification_status == "pending"
        ).order_by(ExpertiseVerification.created_at.asc()).limit(limit)
        
        if domain_filter:
            query = query.where(ExpertiseVerification.domain.ilike(f"%{domain_filter}%"))
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_expert_domains(
        self,
        db: AsyncSession,
        user_id: str,
        verified_only: bool = True
    ) -> List[str]:
        """Get list of domains where user has expertise.
        
        Args:
            db: Database session
            user_id: User identifier
            verified_only: Only return verified domains
            
        Returns:
            List of domain names
        """
        query = select(ExpertiseVerification.domain).where(
            ExpertiseVerification.user_id == user_id
        )
        
        if verified_only:
            query = query.where(ExpertiseVerification.verification_status == "verified")
        
        result = await db.execute(query)
        return [row[0] for row in result.all()]
    
    async def calculate_domain_expertise_score(
        self,
        db: AsyncSession,
        user_id: str,
        domain: str
    ) -> float:
        """Calculate user's expertise score in a specific domain.
        
        Args:
            db: Database session
            user_id: User identifier
            domain: Domain to calculate score for
            
        Returns:
            Expertise score (0.0-10.0)
        """
        # Get verification for domain
        result = await db.execute(
            select(ExpertiseVerification).where(
                and_(
                    ExpertiseVerification.user_id == user_id,
                    ExpertiseVerification.domain == domain,
                    ExpertiseVerification.verification_status == "verified"
                )
            )
        )
        verification = result.scalar_one_or_none()
        
        if not verification:
            return 0.0
        
        base_score = verification.expertise_score
        
        # Get validation performance in this domain
        domain_validations = await db.execute(
            select(ValidationResult).join(
                # This would need proper join logic based on opportunity domains
                # For now, simplified approach
            ).where(ValidationResult.validator_id == user_id)
        )
        
        # For now, return base score
        # In production, this would factor in validation performance in the domain
        return base_score
    
    async def get_domain_experts(
        self,
        db: AsyncSession,
        domain: str,
        min_expertise_score: float = 6.0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get list of experts in a specific domain.
        
        Args:
            db: Database session
            domain: Domain to find experts for
            min_expertise_score: Minimum expertise score required
            limit: Maximum results to return
            
        Returns:
            List of expert information
        """
        result = await db.execute(
            select(
                ExpertiseVerification,
                User.username,
                User.avatar_url,
                ReputationSummary.total_reputation_points,
                ReputationSummary.influence_weight
            ).join(
                User, ExpertiseVerification.user_id == User.id
            ).outerjoin(
                ReputationSummary, User.id == ReputationSummary.user_id
            ).where(
                and_(
                    ExpertiseVerification.domain == domain,
                    ExpertiseVerification.verification_status == "verified",
                    ExpertiseVerification.expertise_score >= min_expertise_score
                )
            ).order_by(
                desc(ExpertiseVerification.expertise_score),
                desc(ReputationSummary.total_reputation_points)
            ).limit(limit)
        )
        
        experts = []
        for verification, username, avatar_url, reputation_points, influence_weight in result:
            experts.append({
                "user_id": verification.user_id,
                "username": username,
                "avatar_url": avatar_url,
                "domain": verification.domain,
                "expertise_score": verification.expertise_score,
                "years_experience": verification.years_experience,
                "verification_method": verification.verification_method,
                "reputation_points": reputation_points or 0.0,
                "influence_weight": influence_weight or 1.0,
                "verified_at": verification.verified_at
            })
        
        return experts
    
    def _calculate_expertise_score(
        self,
        verification_method: str,
        evidence_url: Optional[str],
        credentials: Optional[str],
        years_experience: Optional[int]
    ) -> float:
        """Calculate initial expertise score based on provided evidence.
        
        Args:
            verification_method: Method of verification
            evidence_url: URL to evidence
            credentials: Credential details
            years_experience: Years of experience
            
        Returns:
            Expertise score (1.0-10.0)
        """
        method_config = self.VERIFICATION_METHODS.get(verification_method, {"credibility": 0.5})
        base_score = method_config["credibility"] * 10  # Convert to 1-10 scale
        
        # Experience bonus
        experience_bonus = 0.0
        if years_experience:
            if years_experience >= 10:
                experience_bonus = 2.0
            elif years_experience >= 5:
                experience_bonus = 1.0
            elif years_experience >= 2:
                experience_bonus = 0.5
        
        # Evidence bonus
        evidence_bonus = 0.0
        if evidence_url:
            evidence_bonus = 0.5
        if credentials:
            evidence_bonus += 0.5
        
        final_score = base_score + experience_bonus + evidence_bonus
        return max(1.0, min(10.0, final_score))
    
    async def _update_reputation_ranks(self, db: AsyncSession):
        """Update reputation ranks for all users."""
        # This would be run periodically, not on every update in production
        # For now, we'll skip the implementation to avoid performance issues
        pass


# Global reputation service instance
reputation_service = ReputationService()