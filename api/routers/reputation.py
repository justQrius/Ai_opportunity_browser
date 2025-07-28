"""
Reputation API endpoints for community engagement and expert verification.

Supports Requirements 4.3-4.4 (Community Engagement Platform):
- Expert verification mechanisms
- Reputation tracking and scoring
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.services.reputation_service import reputation_service
from shared.services.user_service import user_service
from shared.models.user import User, UserRole
from shared.models.reputation import ReputationEventType, BadgeType
from shared.schemas.reputation import (
    ReputationEventResponse,
    BadgeResponse,
    ExpertiseVerificationCreate,
    ExpertiseVerificationResponse,
    ExpertiseVerificationUpdate,
    ReputationSummaryResponse,
    UserReputationProfile,
    LeaderboardEntry,
    ReputationAnalytics
)
from api.core.dependencies import get_current_user, require_role
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/reputation", tags=["reputation"])


@router.post("/expertise/verify", response_model=ExpertiseVerificationResponse)
async def initiate_expertise_verification(
    verification_data: ExpertiseVerificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initiate expert verification process."""
    try:
        # Users can only verify their own expertise
        if verification_data.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only verify your own expertise"
            )
        
        verification = await reputation_service.initiate_expert_verification(
            db,
            verification_data.user_id,
            verification_data.domain,
            verification_data.verification_method,
            verification_data.evidence_url,
            verification_data.credentials,
            verification_data.years_experience
        )
        
        logger.info(
            "Expertise verification initiated",
            user_id=current_user.id,
            domain=verification_data.domain,
            verification_id=verification.id
        )
        
        return verification
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to initiate expertise verification", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate verification"
        )


@router.post("/expertise/{verification_id}/approve", response_model=ExpertiseVerificationResponse)
async def approve_expertise_verification(
    verification_id: str,
    verification_notes: Optional[str] = None,
    expertise_score_override: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MODERATOR]))
):
    """Approve a pending expertise verification."""
    try:
        verification = await reputation_service.approve_expert_verification(
            db,
            verification_id,
            current_user.id,
            verification_notes,
            expertise_score_override
        )
        
        logger.info(
            "Expertise verification approved",
            verification_id=verification_id,
            approver_id=current_user.id
        )
        
        return verification
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to approve expertise verification", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve verification"
        )


@router.post("/expertise/{verification_id}/reject", response_model=ExpertiseVerificationResponse)
async def reject_expertise_verification(
    verification_id: str,
    rejection_reason: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MODERATOR]))
):
    """Reject a pending expertise verification."""
    try:
        verification = await reputation_service.reject_expert_verification(
            db,
            verification_id,
            current_user.id,
            rejection_reason
        )
        
        logger.info(
            "Expertise verification rejected",
            verification_id=verification_id,
            rejector_id=current_user.id,
            reason=rejection_reason
        )
        
        return verification
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to reject expertise verification", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject verification"
        )


@router.get("/expertise/pending", response_model=List[ExpertiseVerificationResponse])
async def get_pending_verifications(
    limit: int = Query(50, ge=1, le=100),
    domain_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MODERATOR]))
):
    """Get pending expertise verifications for review."""
    try:
        verifications = await reputation_service.get_pending_verifications(
            db, limit, domain_filter
        )
        
        return verifications
        
    except Exception as e:
        logger.error("Failed to get pending verifications", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pending verifications"
        )


@router.get("/domains/{domain}/experts", response_model=List[Dict[str, Any]])
async def get_domain_experts(
    domain: str,
    min_expertise_score: float = Query(6.0, ge=1.0, le=10.0),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get list of experts in a specific domain."""
    try:
        experts = await reputation_service.get_domain_experts(
            db, domain, min_expertise_score, limit
        )
        
        return experts
        
    except Exception as e:
        logger.error("Failed to get domain experts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get domain experts"
        )


@router.get("/users/{user_id}/domains", response_model=List[str])
async def get_user_expert_domains(
    user_id: str,
    verified_only: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """Get list of domains where user has expertise."""
    try:
        domains = await reputation_service.get_expert_domains(
            db, user_id, verified_only
        )
        
        return domains
        
    except Exception as e:
        logger.error("Failed to get user expert domains", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get expert domains"
        )


@router.get("/users/{user_id}/summary", response_model=ReputationSummaryResponse)
async def get_user_reputation_summary(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get reputation summary for a user."""
    try:
        summary = await reputation_service.get_user_reputation_summary(db, user_id)
        
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reputation summary not found"
            )
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get reputation summary", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get reputation summary"
        )


@router.get("/users/{user_id}/history", response_model=List[ReputationEventResponse])
async def get_user_reputation_history(
    user_id: str,
    limit: int = Query(50, ge=1, le=100),
    event_type: Optional[ReputationEventType] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's reputation event history."""
    try:
        # Users can only see their own detailed history
        if user_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.MODERATOR]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only view your own reputation history"
            )
        
        events = await reputation_service.get_user_reputation_history(
            db, user_id, limit, event_type
        )
        
        return events
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get reputation history", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get reputation history"
        )


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_reputation_leaderboard(
    limit: int = Query(50, ge=1, le=100),
    timeframe_days: Optional[int] = Query(None, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get reputation leaderboard."""
    try:
        leaderboard = await reputation_service.get_reputation_leaderboard(
            db, limit, timeframe_days
        )
        
        return leaderboard
        
    except Exception as e:
        logger.error("Failed to get reputation leaderboard", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get leaderboard"
        )


@router.post("/validations/{validation_id}/feedback")
async def provide_validation_feedback(
    validation_id: str,
    feedback_type: str = Query(..., regex="^(helpful|unhelpful)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Provide feedback on a validation."""
    try:
        await reputation_service.track_validation_feedback(
            db, validation_id, feedback_type, current_user.id
        )
        
        logger.info(
            "Validation feedback provided",
            validation_id=validation_id,
            feedback_type=feedback_type,
            user_id=current_user.id
        )
        
        return {"message": "Feedback recorded successfully"}
        
    except Exception as e:
        logger.error("Failed to provide validation feedback", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record feedback"
        )


@router.get("/analytics", response_model=ReputationAnalytics)
async def get_reputation_analytics(
    timeframe_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MODERATOR]))
):
    """Get reputation system analytics."""
    try:
        analytics = await reputation_service.get_reputation_analytics(
            db, timeframe_days
        )
        
        return analytics
        
    except Exception as e:
        logger.error("Failed to get reputation analytics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analytics"
        )


@router.get("/validations/{validation_id}/quality-score", response_model=Dict[str, float])
async def get_validation_quality_score(
    validation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get quality score for a validation."""
    try:
        quality_score = await reputation_service.calculate_validation_quality_score(
            db, validation_id
        )
        
        return {"quality_score": quality_score}
        
    except Exception as e:
        logger.error("Failed to get validation quality score", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get quality score"
        )