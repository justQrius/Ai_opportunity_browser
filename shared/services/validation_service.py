"""Service layer for validation management and analytics."""

import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func, and_, desc, or_, text
from sqlalchemy.exc import IntegrityError

from shared.models.user import User, UserRole
from shared.models.opportunity import Opportunity
from shared.models.validation import ValidationResult, ValidationType
from shared.models.reputation import ReputationEvent, ReputationEventType
from shared.schemas.validation import (
    ValidationCreate, ValidationUpdate, ValidationResponse, ValidationSummary,
    ValidationStats, ValidationFlag, ValidationVote
)
import logging

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for managing opportunity validations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_validation(
        self, 
        user_id: str, 
        validation_data: ValidationCreate
    ) -> ValidationResult:
        """Create a new validation."""
        try:
            # Check if user exists and get their role
            user = self.db.execute(
                select(User).where(User.id == user_id)
            ).scalar_one_or_none()
            
            if not user:
                raise ValueError("User not found")
            
            # Check if opportunity exists
            opportunity = self.db.execute(
                select(Opportunity).where(Opportunity.id == validation_data.opportunity_id)
            ).scalar_one_or_none()
            
            if not opportunity:
                raise ValueError("Opportunity not found")
            
            # Check for duplicate validation (same user, same opportunity, same type)
            existing = self.db.execute(
                select(ValidationResult).where(
                    and_(
                        ValidationResult.validator_id == user_id,
                        ValidationResult.opportunity_id == validation_data.opportunity_id,
                        ValidationResult.validation_type == validation_data.validation_type
                    )
                )
            ).scalar_one_or_none()
            
            if existing:
                raise ValueError(f"User has already submitted {validation_data.validation_type.value} validation for this opportunity")
            
            # Convert lists to JSON
            evidence_links_json = json.dumps(validation_data.evidence_links) if validation_data.evidence_links else None
            supporting_data_json = json.dumps(validation_data.supporting_data) if validation_data.supporting_data else None
            
            # Create validation
            validation = ValidationResult(
                opportunity_id=validation_data.opportunity_id,
                validator_id=user_id,
                validation_type=validation_data.validation_type,
                score=validation_data.score,
                confidence=validation_data.confidence,
                comments=validation_data.comments,
                strengths=validation_data.strengths,
                weaknesses=validation_data.weaknesses,
                recommendations=validation_data.recommendations,
                evidence_links=evidence_links_json,
                supporting_data=supporting_data_json,
                methodology=validation_data.methodology,
                time_spent_minutes=validation_data.time_spent_minutes,
                expertise_relevance=validation_data.expertise_relevance or 5.0
            )
            
            self.db.add(validation)
            self.db.flush()  # Get the validation ID
            
            # Create reputation event for the validator
            self._create_reputation_event(user_id, validation)
            
            # Update user validation stats
            self._update_user_validation_stats(user_id)
            
            self.db.commit()
            self.db.refresh(validation)
            
            logger.info(f"Created validation {validation.id} by user {user_id} for opportunity {validation_data.opportunity_id}")
            
            # Publish validation submitted event
            try:
                from shared.event_bus import EventType, publish_event
                await publish_event(
                    event_type=EventType.VALIDATION_SUBMITTED,
                    payload={
                        "validation_id": validation.id,
                        "opportunity_id": validation.opportunity_id,
                        "validator_id": user_id,
                        "validation_type": validation.validation_type.value,
                        "score": validation.score,
                        "confidence": validation.confidence
                    },
                    source="validation_service"
                )
            except Exception as e:
                logger.warning("Failed to publish validation submitted event", error=str(e))
            return validation
            
        except (ValueError, IntegrityError) as e:
            self.db.rollback()
            raise ValueError(str(e))
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating validation: {e}")
            raise
    
    def _create_reputation_event(self, user_id: str, validation: ValidationResult):
        """Create reputation event for validation submission."""
        try:
            # Calculate base points based on validation quality indicators
            base_points = 10.0  # Base points for submitting a validation
            
            # Bonus points for comprehensive validation
            if validation.comments and len(validation.comments) > 100:
                base_points += 5.0
            if validation.evidence_links:
                base_points += 5.0
            if validation.time_spent_minutes and validation.time_spent_minutes >= 30:
                base_points += 5.0
            if validation.expertise_relevance and validation.expertise_relevance >= 8.0:
                base_points += 10.0
            
            reputation_event = ReputationEvent(
                user_id=user_id,
                event_type=EventType.VALIDATION_SUBMITTED,
                points=base_points,
                related_validation_id=validation.id,
                description=f"Submitted {validation.validation_type.value} validation",
                metadata=json.dumps({
                    "validation_type": validation.validation_type.value,
                    "score": validation.score,
                    "confidence": validation.confidence
                })
            )
            
            self.db.add(reputation_event)
            
        except Exception as e:
            logger.error(f"Error creating reputation event: {e}")
            # Don't re-raise as this is a background operation
    
    def _update_user_validation_stats(self, user_id: str):
        """Update user validation statistics."""
        try:
            # Get user validation count and accuracy
            result = self.db.execute(
                select(
                    func.count(ValidationResult.id).label('total_validations'),
                    func.avg(ValidationResult.score).label('avg_score')
                ).where(ValidationResult.validator_id == user_id)
            )
            stats = result.first()
            
            # Update user stats
            user = self.db.execute(
                select(User).where(User.id == user_id)
            ).scalar_one()
            
            user.validation_count = stats.total_validations or 0
            # Validation accuracy will be calculated based on community votes later
            
        except Exception as e:
            logger.error(f"Error updating user validation stats: {e}")
    
    def get_validation_by_id(
        self, 
        validation_id: str, 
        include_validator_info: bool = True
    ) -> Optional[ValidationResult]:
        """Get a validation by ID with optional validator information."""
        try:
            query = select(ValidationResult)
            
            if include_validator_info:
                query = query.options(selectinload(ValidationResult.validator))
            
            query = query.where(ValidationResult.id == validation_id)
            
            result = self.db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting validation: {e}")
            raise
    
    def get_validations(
        self,
        opportunity_id: Optional[str] = None,
        validator_id: Optional[str] = None,
        validation_type: Optional[ValidationType] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        is_flagged: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
        include_validator_info: bool = True
    ) -> Tuple[List[ValidationResult], int]:
        """Get validations with filtering and pagination."""
        try:
            query = select(ValidationResult)
            
            if include_validator_info:
                query = query.options(selectinload(ValidationResult.validator))
            
            # Apply filters
            if opportunity_id:
                query = query.where(ValidationResult.opportunity_id == opportunity_id)
            
            if validator_id:
                query = query.where(ValidationResult.validator_id == validator_id)
            
            if validation_type:
                query = query.where(ValidationResult.validation_type == validation_type)
            
            if min_score is not None:
                query = query.where(ValidationResult.score >= min_score)
            
            if max_score is not None:
                query = query.where(ValidationResult.score <= max_score)
            
            if is_flagged is not None:
                query = query.where(ValidationResult.is_flagged == is_flagged)
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_count = self.db.execute(count_query).scalar()
            
            # Apply pagination
            offset = (page - 1) * page_size
            query = query.order_by(desc(ValidationResult.created_at)).offset(offset).limit(page_size)
            
            # Execute query
            result = self.db.execute(query)
            validations = result.scalars().all()
            
            return validations, total_count
            
        except Exception as e:
            logger.error(f"Error getting validations: {e}")
            raise
    
    def update_validation(
        self,
        validation_id: str,
        user_id: str,
        update_data: ValidationUpdate
    ) -> Optional[ValidationResult]:
        """Update a validation (only by the original validator)."""
        try:
            # Get validation and check ownership
            validation = self.db.execute(
                select(ValidationResult).where(
                    and_(
                        ValidationResult.id == validation_id,
                        ValidationResult.validator_id == user_id
                    )
                )
            ).scalar_one_or_none()
            
            if not validation:
                return None
            
            # Update fields
            update_dict = update_data.dict(exclude_unset=True)
            
            # Handle JSON fields
            if "evidence_links" in update_dict:
                validation.evidence_links = json.dumps(update_dict["evidence_links"]) if update_dict["evidence_links"] else None
                del update_dict["evidence_links"]
            
            if "supporting_data" in update_dict:
                validation.supporting_data = json.dumps(update_dict["supporting_data"]) if update_dict["supporting_data"] else None
                del update_dict["supporting_data"]
            
            # Update other fields
            for field, value in update_dict.items():
                if hasattr(validation, field):
                    setattr(validation, field, value)
            
            self.db.commit()
            self.db.refresh(validation)
            
            logger.info(f"Updated validation {validation_id}")
            return validation
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating validation: {e}")
            raise
    
    def vote_on_validation(
        self,
        validation_id: str,
        user_id: str,
        is_helpful: bool
    ) -> bool:
        """Vote on a validation's helpfulness."""
        try:
            # Check if validation exists
            validation = self.db.execute(
                select(ValidationResult).where(ValidationResult.id == validation_id)
            ).scalar_one_or_none()
            
            if not validation:
                raise ValueError("Validation not found")
            
            # Prevent self-voting
            if validation.validator_id == user_id:
                raise ValueError("Cannot vote on your own validation")
            
            # For simplicity, we'll allow multiple votes per user but track the most recent
            # In production, you might want a separate votes table to track individual votes
            
            if is_helpful:
                validation.helpful_votes += 1
            else:
                validation.unhelpful_votes += 1
            
            # Create reputation event for the validator
            points = 2.0 if is_helpful else -1.0
            reputation_event = ReputationEvent(
                user_id=validation.validator_id,
                event_type=EventType.VALIDATION_VOTED,
                points=points,
                related_validation_id=validation.id,
                description=f"Received {'helpful' if is_helpful else 'unhelpful'} vote",
                metadata=json.dumps({
                    "vote_type": "helpful" if is_helpful else "unhelpful",
                    "voter_id": user_id
                })
            )
            
            self.db.add(reputation_event)
            self.db.commit()
            
            logger.info(f"User {user_id} voted {'helpful' if is_helpful else 'unhelpful'} on validation {validation_id}")
            return True
            
        except ValueError:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error voting on validation: {e}")
            raise
    
    def flag_validation(
        self,
        validation_id: str,
        user_id: str,
        flag_data: ValidationFlag
    ) -> bool:
        """Flag a validation for inappropriate content."""
        try:
            validation = self.db.execute(
                select(ValidationResult).where(ValidationResult.id == validation_id)
            ).scalar_one_or_none()
            
            if not validation:
                raise ValueError("Validation not found")
            
            validation.is_flagged = True
            validation.flag_reason = flag_data.reason
            
            # Create reputation event (negative points for being flagged)
            reputation_event = ReputationEvent(
                user_id=validation.validator_id,
                event_type=EventType.CONTENT_FLAGGED,
                points=-5.0,
                related_validation_id=validation.id,
                description=f"Validation flagged for: {flag_data.reason}",
                metadata=json.dumps({
                    "flag_reason": flag_data.reason,
                    "flag_details": flag_data.details,
                    "flagger_id": user_id
                })
            )
            
            self.db.add(reputation_event)
            self.db.commit()
            
            logger.info(f"Validation {validation_id} flagged by user {user_id}")
            return True
            
        except ValueError:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error flagging validation: {e}")
            raise
    
    def get_opportunity_validation_summary(self, opportunity_id: str) -> Optional[ValidationSummary]:
        """Get validation summary for an opportunity."""
        try:
            # Check if opportunity exists
            opportunity = self.db.execute(
                select(Opportunity).where(Opportunity.id == opportunity_id)
            ).scalar_one_or_none()
            
            if not opportunity:
                return None
            
            # Get validation statistics
            result = self.db.execute(
                select(
                    func.count(ValidationResult.id).label('total_validations'),
                    func.avg(ValidationResult.score).label('avg_score'),
                    func.avg(ValidationResult.confidence).label('avg_confidence')
                ).where(ValidationResult.opportunity_id == opportunity_id)
            )
            stats = result.first()
            
            if not stats.total_validations:
                return ValidationSummary(
                    opportunity_id=opportunity_id,
                    total_validations=0,
                    average_score=0.0,
                    confidence_rating=0.0,
                    validations_by_type={},
                    consensus_strengths=[],
                    consensus_weaknesses=[],
                    top_recommendations=[],
                    validation_quality_score=0.0
                )
            
            # Get validations by type
            type_result = self.db.execute(
                select(
                    ValidationResult.validation_type,
                    func.count(ValidationResult.id).label('count'),
                    func.avg(ValidationResult.score).label('avg_score')
                ).where(ValidationResult.opportunity_id == opportunity_id)
                .group_by(ValidationResult.validation_type)
            )
            
            validations_by_type = {}
            for row in type_result:
                validations_by_type[row.validation_type.value] = {
                    "count": row.count,
                    "average_score": round(row.avg_score, 2)
                }
            
            # Get common themes (simplified version - in production, you'd use NLP)
            validations_with_content = self.db.execute(
                select(ValidationResult).where(
                    and_(
                        ValidationResult.opportunity_id == opportunity_id,
                        or_(
                            ValidationResult.strengths.isnot(None),
                            ValidationResult.weaknesses.isnot(None),
                            ValidationResult.recommendations.isnot(None)
                        )
                    )
                )
            ).scalars().all()
            
            # Extract common themes (simplified)
            strengths = []
            weaknesses = []
            recommendations = []
            
            for validation in validations_with_content:
                if validation.strengths:
                    strengths.append(validation.strengths)
                if validation.weaknesses:
                    weaknesses.append(validation.weaknesses)
                if validation.recommendations:
                    recommendations.append(validation.recommendations)
            
            # Calculate quality score based on validator reputation and evidence
            quality_score = self._calculate_validation_quality_score(opportunity_id)
            
            return ValidationSummary(
                opportunity_id=opportunity_id,
                total_validations=stats.total_validations,
                average_score=round(stats.avg_score, 2),
                confidence_rating=round(stats.avg_confidence, 2),
                validations_by_type=validations_by_type,
                consensus_strengths=strengths[:3],  # Top 3 most common
                consensus_weaknesses=weaknesses[:3],
                top_recommendations=recommendations[:3],
                validation_quality_score=quality_score
            )
            
        except Exception as e:
            logger.error(f"Error getting validation summary: {e}")
            raise
    
    def _calculate_validation_quality_score(self, opportunity_id: str) -> float:
        """Calculate overall validation quality score for an opportunity."""
        try:
            # Get validations with validator information
            result = self.db.execute(
                select(ValidationResult, User.reputation_score)
                .join(User, ValidationResult.validator_id == User.id)
                .where(ValidationResult.opportunity_id == opportunity_id)
            )
            
            validations_with_reputation = result.all()
            
            if not validations_with_reputation:
                return 0.0
            
            total_weighted_score = 0.0
            total_weight = 0.0
            
            for validation, validator_reputation in validations_with_reputation:
                # Weight based on validator reputation
                reputation_weight = min(validator_reputation / 10.0, 1.0)  # Normalize to 0-1
                
                # Evidence quality bonus
                evidence_bonus = 0.0
                if validation.evidence_links:
                    evidence_bonus += 0.2
                if validation.methodology:
                    evidence_bonus += 0.1
                if validation.expertise_relevance and validation.expertise_relevance >= 7.0:
                    evidence_bonus += 0.2
                
                # Community feedback weight
                total_votes = validation.helpful_votes + validation.unhelpful_votes
                if total_votes > 0:
                    helpfulness_ratio = validation.helpful_votes / total_votes
                    community_weight = helpfulness_ratio * 0.3
                else:
                    community_weight = 0.0
                
                final_weight = reputation_weight + evidence_bonus + community_weight
                total_weighted_score += validation.score * final_weight
                total_weight += final_weight
            
            if total_weight == 0:
                return 0.0
            
            quality_score = (total_weighted_score / total_weight) / 10.0  # Normalize to 0-1
            return round(quality_score, 3)
            
        except Exception as e:
            logger.error(f"Error calculating validation quality score: {e}")
            return 0.0
    
    def get_validation_stats(self) -> ValidationStats:
        """Get overall validation statistics."""
        try:
            # Total validations
            total_result = self.db.execute(
                select(func.count(ValidationResult.id))
            )
            total_validations = total_result.scalar()
            
            # Validations by type
            type_result = self.db.execute(
                select(
                    ValidationResult.validation_type,
                    func.count(ValidationResult.id).label('count')
                ).group_by(ValidationResult.validation_type)
            )
            
            validations_by_type = {}
            for row in type_result:
                validations_by_type[row.validation_type.value] = row.count
            
            # Average scores
            avg_result = self.db.execute(
                select(
                    func.avg(ValidationResult.score).label('avg_score'),
                    func.avg(ValidationResult.confidence).label('avg_confidence')
                )
            )
            averages = avg_result.first()
            
            # Top validators (by validation count and quality)
            top_validators_result = self.db.execute(
                select(
                    User.id,
                    User.username,
                    func.count(ValidationResult.id).label('validation_count'),
                    func.avg(ValidationResult.score).label('avg_score'),
                    User.reputation_score
                )
                .join(ValidationResult, User.id == ValidationResult.validator_id)
                .group_by(User.id, User.username, User.reputation_score)
                .order_by(desc(func.count(ValidationResult.id)))
                .limit(10)
            )
            
            top_validators = []
            for row in top_validators_result:
                top_validators.append({
                    "user_id": row.id,
                    "username": row.username,
                    "validation_count": row.validation_count,
                    "average_score": round(row.avg_score, 2),
                    "reputation_score": row.reputation_score
                })
            
            # Validation trends (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            trend_result = self.db.execute(
                select(
                    func.date(ValidationResult.created_at).label('date'),
                    func.count(ValidationResult.id).label('count')
                )
                .where(ValidationResult.created_at >= thirty_days_ago)
                .group_by(func.date(ValidationResult.created_at))
                .order_by(func.date(ValidationResult.created_at))
            )
            
            validation_trends = {}
            for row in trend_result:
                validation_trends[str(row.date)] = row.count
            
            return ValidationStats(
                total_validations=total_validations or 0,
                validations_by_type=validations_by_type,
                average_score=round(averages.avg_score, 2) if averages.avg_score else 0.0,
                average_confidence=round(averages.avg_confidence, 2) if averages.avg_confidence else 0.0,
                top_validators=top_validators,
                validation_trends=validation_trends
            )
            
        except Exception as e:
            logger.error(f"Error getting validation stats: {e}")
            raise
    
    def bulk_moderate_validations(
        self,
        validation_ids: List[str],
        moderator_id: str,
        action: str  # "approve" or "reject"
    ) -> int:
        """Bulk approve or reject validations (moderator only)."""
        try:
            # Check if user is moderator
            moderator = self.db.execute(
                select(User).where(User.id == moderator_id)
            ).scalar_one_or_none()
            
            if not moderator or moderator.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
                raise ValueError("User is not authorized to moderate validations")
            
            # Get validations to update
            validations = self.db.execute(
                select(ValidationResult).where(ValidationResult.id.in_(validation_ids))
            ).scalars().all()
            
            # Update each validation
            updated_count = 0
            for validation in validations:
                if action == "approve":
                    validation.moderator_reviewed = True
                    validation.is_flagged = False
                elif action == "reject":
                    validation.moderator_reviewed = True
                    validation.is_flagged = True
                else:
                    raise ValueError("Invalid action. Must be 'approve' or 'reject'")
                updated_count += 1
            
            self.db.commit()
            
            logger.info(f"Moderator {moderator_id} {action}d {updated_count} validations")
            return updated_count
            
        except ValueError:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error bulk moderating validations: {e}")
            raise


def get_validation_service(db: Session) -> ValidationService:
    """Get validation service instance."""
    return ValidationService(db)


# Create a default instance for import compatibility
# Note: This requires a database session to be passed when using the service
validation_service = ValidationService