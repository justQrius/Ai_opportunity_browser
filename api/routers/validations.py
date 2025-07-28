"""
Validations API endpoints for the AI Opportunity Browser.

This module provides REST API endpoints for managing opportunity validations,
including submission, retrieval, and validation analytics.

Supports Requirements 2 (Opportunity Validation Framework) and 4 (Community Engagement).
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends, status
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.schemas.validation import (
    ValidationCreate, ValidationUpdate, ValidationResponse,
    ValidationVote, ValidationFlag, ValidationStats, ValidationSummary
)
from shared.schemas.base import APIResponse, PaginatedResponse, PaginationResponse
from shared.schemas.auth import CurrentUser
from shared.services.validation_service import get_validation_service
from shared.models.validation import ValidationType
from shared.models.user import UserRole
from api.routers.auth import get_current_user
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def list_validations(
    opportunity_id: Optional[str] = Query(None, description="Filter by opportunity ID"),
    validator_id: Optional[str] = Query(None, description="Filter by validator ID"),
    validation_type: Optional[str] = Query(None, description="Filter by validation type"),
    min_score: Optional[float] = Query(None, ge=1.0, le=10.0, description="Minimum validation score"),
    max_score: Optional[float] = Query(None, ge=1.0, le=10.0, description="Maximum validation score"),
    is_flagged: Optional[bool] = Query(None, description="Filter by flagged status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db)
):
    """
    List validations with filtering and pagination.
    
    Supports Requirements 2.2 (Collect and aggregate validation scores).
    """
    try:
        validation_service = get_validation_service(db)
        
        # Convert validation_type string to enum if provided
        validation_type_enum = None
        if validation_type:
            try:
                validation_type_enum = ValidationType(validation_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid validation type: {validation_type}"
                )
        
        validations, total_count = validation_service.get_validations(
            opportunity_id=opportunity_id,
            validator_id=validator_id,
            validation_type=validation_type_enum,
            min_score=min_score,
            max_score=max_score,
            is_flagged=is_flagged,
            page=page,
            page_size=page_size
        )
        
        # Convert to response format
        validation_items = []
        for validation in validations:
            # Parse JSON fields
            evidence_links = []
            supporting_data = None
            
            if validation.evidence_links:
                try:
                    evidence_links = json.loads(validation.evidence_links)
                except json.JSONDecodeError:
                    pass
            
            if validation.supporting_data:
                try:
                    supporting_data = json.loads(validation.supporting_data)
                except json.JSONDecodeError:
                    pass
            
            validation_items.append({
                "id": validation.id,
                "opportunity_id": validation.opportunity_id,
                "validator_id": validation.validator_id,
                "validation_type": validation.validation_type,
                "score": validation.score,
                "confidence": validation.confidence,
                "comments": validation.comments,
                "strengths": validation.strengths,
                "weaknesses": validation.weaknesses,
                "recommendations": validation.recommendations,
                "evidence_links": evidence_links,
                "supporting_data": supporting_data,
                "methodology": validation.methodology,
                "time_spent_minutes": validation.time_spent_minutes,
                "expertise_relevance": validation.expertise_relevance,
                "is_flagged": validation.is_flagged,
                "flag_reason": validation.flag_reason,
                "moderator_reviewed": validation.moderator_reviewed,
                "helpful_votes": validation.helpful_votes,
                "unhelpful_votes": validation.unhelpful_votes,
                "validator_username": validation.validator.username if validation.validator else None,
                "validator_reputation": validation.validator.reputation_score if validation.validator else None,
                "created_at": validation.created_at,
                "updated_at": validation.updated_at
            })
        
        pagination = PaginationResponse.create(
            page=page,
            page_size=page_size,
            total_count=total_count
        )
        
        return PaginatedResponse(
            items=validation_items,
            pagination=pagination,
            total_count=total_count,
            filters_applied={
                "opportunity_id": opportunity_id,
                "validator_id": validator_id,
                "validation_type": validation_type,
                "min_score": min_score,
                "max_score": max_score,
                "is_flagged": is_flagged
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing validations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list validations"
        )


@router.get("/{validation_id}", response_model=ValidationResponse)
async def get_validation(
    validation_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific validation by ID.
    
    Supports Requirements 2.2 (Community validation collection).
    """
    try:
        validation_service = get_validation_service(db)
        validation = validation_service.get_validation_by_id(validation_id)
        
        if not validation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation not found"
            )
        
        # Parse JSON fields
        evidence_links = []
        supporting_data = None
        
        if validation.evidence_links:
            try:
                evidence_links = json.loads(validation.evidence_links)
            except json.JSONDecodeError:
                pass
        
        if validation.supporting_data:
            try:
                supporting_data = json.loads(validation.supporting_data)
            except json.JSONDecodeError:
                pass
        
        return ValidationResponse(
            id=validation.id,
            opportunity_id=validation.opportunity_id,
            validator_id=validation.validator_id,
            validation_type=validation.validation_type,
            score=validation.score,
            confidence=validation.confidence,
            comments=validation.comments,
            strengths=validation.strengths,
            weaknesses=validation.weaknesses,
            recommendations=validation.recommendations,
            evidence_links=evidence_links,
            supporting_data=supporting_data,
            methodology=validation.methodology,
            time_spent_minutes=validation.time_spent_minutes,
            expertise_relevance=validation.expertise_relevance,
            is_flagged=validation.is_flagged,
            flag_reason=validation.flag_reason,
            moderator_reviewed=validation.moderator_reviewed,
            helpful_votes=validation.helpful_votes,
            unhelpful_votes=validation.unhelpful_votes,
            validator_username=validation.validator.username if validation.validator else None,
            validator_reputation=validation.validator.reputation_score if validation.validator else None,
            created_at=validation.created_at,
            updated_at=validation.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get validation"
        )


@router.post("/", response_model=ValidationResponse)
async def submit_validation(
    validation: ValidationCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a new validation for an opportunity.
    
    Supports Requirements 2.1 (Initiate validation workflow) and 4.3 (Track contributions).
    """
    try:
        validation_service = get_validation_service(db)
        created_validation = validation_service.create_validation(
            current_user.id,
            validation
        )
        
        # Parse JSON fields for response
        evidence_links = []
        supporting_data = None
        
        if created_validation.evidence_links:
            try:
                evidence_links = json.loads(created_validation.evidence_links)
            except json.JSONDecodeError:
                pass
        
        if created_validation.supporting_data:
            try:
                supporting_data = json.loads(created_validation.supporting_data)
            except json.JSONDecodeError:
                pass
        
        return ValidationResponse(
            id=created_validation.id,
            opportunity_id=created_validation.opportunity_id,
            validator_id=created_validation.validator_id,
            validation_type=created_validation.validation_type,
            score=created_validation.score,
            confidence=created_validation.confidence,
            comments=created_validation.comments,
            strengths=created_validation.strengths,
            weaknesses=created_validation.weaknesses,
            recommendations=created_validation.recommendations,
            evidence_links=evidence_links,
            supporting_data=supporting_data,
            methodology=created_validation.methodology,
            time_spent_minutes=created_validation.time_spent_minutes,
            expertise_relevance=created_validation.expertise_relevance,
            is_flagged=created_validation.is_flagged,
            flag_reason=created_validation.flag_reason,
            moderator_reviewed=created_validation.moderator_reviewed,
            helpful_votes=created_validation.helpful_votes,
            unhelpful_votes=created_validation.unhelpful_votes,
            validator_username=current_user.username,
            validator_reputation=None,  # Will be loaded separately if needed
            created_at=created_validation.created_at,
            updated_at=created_validation.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error submitting validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit validation"
        )


@router.put("/{validation_id}", response_model=ValidationResponse)
async def update_validation(
    validation_id: str,
    validation: ValidationUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing validation.
    
    Supports validation editing and improvement.
    """
    try:
        validation_service = get_validation_service(db)
        updated_validation = validation_service.update_validation(
            validation_id,
            current_user.id,
            validation
        )
        
        if not updated_validation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation not found or you don't have permission to update it"
            )
        
        # Parse JSON fields for response
        evidence_links = []
        supporting_data = None
        
        if updated_validation.evidence_links:
            try:
                evidence_links = json.loads(updated_validation.evidence_links)
            except json.JSONDecodeError:
                pass
        
        if updated_validation.supporting_data:
            try:
                supporting_data = json.loads(updated_validation.supporting_data)
            except json.JSONDecodeError:
                pass
        
        return ValidationResponse(
            id=updated_validation.id,
            opportunity_id=updated_validation.opportunity_id,
            validator_id=updated_validation.validator_id,
            validation_type=updated_validation.validation_type,
            score=updated_validation.score,
            confidence=updated_validation.confidence,
            comments=updated_validation.comments,
            strengths=updated_validation.strengths,
            weaknesses=updated_validation.weaknesses,
            recommendations=updated_validation.recommendations,
            evidence_links=evidence_links,
            supporting_data=supporting_data,
            methodology=updated_validation.methodology,
            time_spent_minutes=updated_validation.time_spent_minutes,
            expertise_relevance=updated_validation.expertise_relevance,
            is_flagged=updated_validation.is_flagged,
            flag_reason=updated_validation.flag_reason,
            moderator_reviewed=updated_validation.moderator_reviewed,
            helpful_votes=updated_validation.helpful_votes,
            unhelpful_votes=updated_validation.unhelpful_votes,
            validator_username=current_user.username,
            validator_reputation=None,
            created_at=updated_validation.created_at,
            updated_at=updated_validation.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update validation"
        )


@router.post("/{validation_id}/vote", response_model=APIResponse)
async def vote_on_validation(
    validation_id: str,
    vote: ValidationVote,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Vote on a validation (helpful/unhelpful).
    
    Supports Requirements 4.3-4.4 (Community feedback and reputation).
    """
    try:
        validation_service = get_validation_service(db)
        success = validation_service.vote_on_validation(
            validation_id,
            current_user.id,
            vote.is_helpful
        )
        
        return APIResponse(
            success=True,
            message=f"Voted {'helpful' if vote.is_helpful else 'unhelpful'} on validation"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error voting on validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to vote on validation"
        )


@router.post("/{validation_id}/flag", response_model=APIResponse)
async def flag_validation(
    validation_id: str,
    flag: ValidationFlag,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Flag a validation for inappropriate content or quality issues.
    
    Supports Requirements 2.4 (Quality control) and community moderation.
    """
    try:
        validation_service = get_validation_service(db)
        success = validation_service.flag_validation(
            validation_id,
            current_user.id,
            flag
        )
        
        return APIResponse(
            success=True,
            message=f"Validation flagged for: {flag.reason}"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error flagging validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to flag validation"
        )


@router.get("/opportunity/{opportunity_id}/summary", response_model=ValidationSummary)
async def get_opportunity_validation_summary(
    opportunity_id: str,
    db: Session = Depends(get_db)
):
    """
    Get validation summary for a specific opportunity.
    
    Supports Requirements 2.3 (Assign confidence ratings based on community feedback).
    """
    try:
        validation_service = get_validation_service(db)
        summary = validation_service.get_opportunity_validation_summary(opportunity_id)
        
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opportunity not found"
            )
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting validation summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get validation summary"
        )


@router.get("/stats/overview", response_model=ValidationStats)
async def get_validation_stats(db: Session = Depends(get_db)):
    """
    Get overall validation statistics.
    
    Supports Requirements 2.5 (Update opportunity rankings) and analytics.
    """
    try:
        validation_service = get_validation_service(db)
        stats = validation_service.get_validation_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting validation stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get validation statistics"
        )


@router.get("/leaderboard/validators", response_model=PaginatedResponse)
async def get_validator_leaderboard(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    validation_type: Optional[str] = Query(None, description="Filter by validation type"),
    time_period: str = Query("all_time", pattern="^(week|month|quarter|year|all_time)$"),
    db: Session = Depends(get_db)
):
    """
    Get validator leaderboard based on contribution quality.
    
    Supports Requirements 4.4 (Influence weight for quality validation).
    """
    try:
        validation_service = get_validation_service(db)
        stats = validation_service.get_validation_stats()
        
        # For now, use the top validators from stats
        # In a more advanced implementation, you'd filter by time_period and validation_type
        top_validators = stats.top_validators
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_validators = top_validators[start_idx:end_idx]
        
        pagination = PaginationResponse.create(
            page=page,
            page_size=page_size,
            total_count=len(top_validators)
        )
        
        return PaginatedResponse(
            items=paginated_validators,
            pagination=pagination,
            total_count=len(top_validators),
            filters_applied={
                "validation_type": validation_type,
                "time_period": time_period
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting validator leaderboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get validator leaderboard"
        )


@router.get("/quality/metrics", response_model=dict)
async def get_validation_quality_metrics(db: Session = Depends(get_db)):
    """
    Get validation quality metrics and trends.
    
    Supports quality control and system improvement.
    """
    try:
        validation_service = get_validation_service(db)
        
        # Get basic statistics
        from shared.models.validation import ValidationResult
        from sqlalchemy import func, select
        
        # Calculate quality metrics
        result = db.execute(
            select(
                func.avg(ValidationResult.score).label('avg_quality'),
                func.count(ValidationResult.id).label('total'),
                func.count().filter(ValidationResult.is_flagged == True).label('flagged_count'),
                func.avg(ValidationResult.helpful_votes).label('avg_helpful_votes'),
                func.avg(ValidationResult.unhelpful_votes).label('avg_unhelpful_votes')
            )
        )
        metrics = result.first()
        
        total_validations = metrics.total or 0
        flagged_count = metrics.flagged_count or 0
        avg_helpful = metrics.avg_helpful_votes or 0
        avg_unhelpful = metrics.avg_unhelpful_votes or 0
        
        flagged_percentage = (flagged_count / total_validations * 100) if total_validations > 0 else 0.0
        consensus_rate = (avg_helpful / (avg_helpful + avg_unhelpful)) if (avg_helpful + avg_unhelpful) > 0 else 0.0
        
        return {
            "average_quality_score": round(metrics.avg_quality or 0.0, 2),
            "flagged_percentage": round(flagged_percentage, 2),
            "consensus_rate": round(consensus_rate, 2),
            "validator_agreement": round(consensus_rate, 2),  # Simplified metric
            "quality_trends": {},  # Would be implemented with time-series data
            "improvement_suggestions": [
                "Encourage validators to provide evidence links",
                "Implement peer review for high-impact validations",
                "Create validation guidelines for consistency"
            ] if flagged_percentage > 10 else []
        }
        
    except Exception as e:
        logger.error(f"Error getting quality metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get quality metrics"
        )


@router.post("/bulk/approve", response_model=APIResponse)
async def bulk_approve_validations(
    validation_ids: List[str] = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bulk approve validations (moderator only).
    
    Supports moderation workflows and quality control.
    """
    try:
        validation_service = get_validation_service(db)
        updated_count = validation_service.bulk_moderate_validations(
            validation_ids,
            current_user.id,
            "approve"
        )
        
        return APIResponse(
            success=True,
            message=f"Successfully approved {updated_count} validations"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error bulk approving validations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk approve validations"
        )


@router.post("/bulk/reject", response_model=APIResponse)
async def bulk_reject_validations(
    validation_ids: List[str] = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bulk reject validations (moderator only).
    
    Supports moderation workflows and quality control.
    """
    try:
        validation_service = get_validation_service(db)
        updated_count = validation_service.bulk_moderate_validations(
            validation_ids,
            current_user.id,
            "reject"
        )
        
        return APIResponse(
            success=True,
            message=f"Successfully rejected {updated_count} validations"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error bulk rejecting validations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk reject validations"
        )