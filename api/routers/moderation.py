"""Moderation API endpoints for fraud detection and automated moderation.

This module provides API endpoints for moderators and administrators to manage
validation quality control and fraud detection systems.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from shared.database import get_db
from api.core.dependencies import get_current_user, require_moderator, require_admin
from shared.models.user import User, UserRole
from shared.services.fraud_detection_service import (
    fraud_detection_service,
    FraudType,
    FraudSeverity,
    ModerationAction
)
from shared.services.moderation_service import (
    moderation_service,
    ModerationStatus,
    AppealStatus
)

router = APIRouter(prefix="/moderation", tags=["moderation"])


# Request/Response Models

class FraudDetectionResponse(BaseModel):
    """Response model for fraud detection results."""
    fraud_type: FraudType
    severity: FraudSeverity
    confidence_score: float
    evidence: List[str]
    recommended_action: ModerationAction
    metadata: Dict[str, Any]
    detected_at: str


class ModerationItemResponse(BaseModel):
    """Response model for moderation queue items."""
    validation_id: str
    user_id: str
    fraud_results: List[FraudDetectionResponse]
    status: ModerationStatus
    priority: int
    assigned_moderator: Optional[str]
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]


class ModerationActionRequest(BaseModel):
    """Request model for moderation actions."""
    action: ModerationAction
    reason: str
    notes: Optional[str] = None


class FlagValidationRequest(BaseModel):
    """Request model for flagging validations."""
    reason: str
    evidence: Optional[str] = None


class AppealRequest(BaseModel):
    """Request model for submitting appeals."""
    appeal_reason: str
    evidence: Optional[str] = None


class AppealResponse(BaseModel):
    """Response model for appeals."""
    validation_id: str
    user_id: str
    original_action: ModerationAction
    appeal_reason: str
    status: AppealStatus
    assigned_reviewer: Optional[str]
    created_at: str
    resolved_at: Optional[str]
    resolution: Optional[str]
    metadata: Dict[str, Any]


class ProcessAppealRequest(BaseModel):
    """Request model for processing appeals."""
    approved: bool
    resolution: str


# Fraud Detection Endpoints

@router.post("/analyze/{validation_id}", response_model=List[FraudDetectionResponse])
async def analyze_validation_fraud(
    validation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_moderator())
):
    """Analyze a validation for potential fraud."""
    try:
        fraud_results = await fraud_detection_service.analyze_validation_for_fraud(
            db, validation_id
        )
        
        return [
            FraudDetectionResponse(
                fraud_type=result.fraud_type,
                severity=result.severity,
                confidence_score=result.confidence_score,
                evidence=result.evidence,
                recommended_action=result.recommended_action,
                metadata=result.metadata,
                detected_at=result.detected_at.isoformat()
            )
            for result in fraud_results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fraud analysis failed: {str(e)}"
        )


@router.post("/analyze-user/{user_id}", response_model=List[FraudDetectionResponse])
async def analyze_user_behavior(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_moderator())
):
    """Analyze a user's behavior for fraud patterns."""
    try:
        fraud_results = await fraud_detection_service.analyze_user_behavior(
            db, user_id
        )
        
        return [
            FraudDetectionResponse(
                fraud_type=result.fraud_type,
                severity=result.severity,
                confidence_score=result.confidence_score,
                evidence=result.evidence,
                recommended_action=result.recommended_action,
                metadata=result.metadata,
                detected_at=result.detected_at.isoformat()
            )
            for result in fraud_results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User behavior analysis failed: {str(e)}"
        )


@router.get("/fraud-stats", response_model=Dict[str, Any])
async def get_fraud_statistics(
    timeframe_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_moderator())
):
    """Get fraud detection statistics."""
    try:
        stats = await fraud_detection_service.get_fraud_statistics(db, timeframe_days)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get fraud statistics: {str(e)}"
        )


# Community Reporting Endpoints

@router.post("/flag/{validation_id}")
async def flag_validation(
    validation_id: str,
    request: FlagValidationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Flag a validation for review."""
    try:
        success = await fraud_detection_service.flag_validation(
            db, validation_id, current_user.id, request.reason, request.evidence
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation not found"
            )
        
        return {"message": "Validation flagged successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to flag validation: {str(e)}"
        )


# Moderation Queue Endpoints

@router.get("/queue", response_model=List[ModerationItemResponse])
async def get_moderation_queue(
    status: Optional[ModerationStatus] = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_moderator())
):
    """Get items from the moderation queue."""
    try:
        items = await moderation_service.get_moderation_queue(
            moderator_id=current_user.id if current_user.role == UserRole.MODERATOR else None,
            status=status,
            limit=limit
        )
        
        return [
            ModerationItemResponse(
                validation_id=item.validation_id,
                user_id=item.user_id,
                fraud_results=[
                    FraudDetectionResponse(
                        fraud_type=result.fraud_type,
                        severity=result.severity,
                        confidence_score=result.confidence_score,
                        evidence=result.evidence,
                        recommended_action=result.recommended_action,
                        metadata=result.metadata,
                        detected_at=result.detected_at.isoformat()
                    )
                    for result in item.fraud_results
                ],
                status=item.status,
                priority=item.priority,
                assigned_moderator=item.assigned_moderator,
                created_at=item.created_at.isoformat(),
                updated_at=item.updated_at.isoformat(),
                metadata=item.metadata
            )
            for item in items
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get moderation queue: {str(e)}"
        )


@router.post("/assign/{validation_id}")
async def assign_moderation_item(
    validation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_moderator())
):
    """Assign a moderation item to the current moderator."""
    try:
        success = await moderation_service.assign_moderation_item(
            validation_id, current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item not available for assignment"
            )
        
        return {"message": "Item assigned successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign item: {str(e)}"
        )


@router.post("/moderate/{validation_id}")
async def moderate_validation(
    validation_id: str,
    request: ModerationActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_moderator())
):
    """Make a moderation decision on a validation."""
    try:
        success = await moderation_service.moderate_validation(
            db, validation_id, current_user.id, request.action, request.reason, request.notes
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to moderate validation"
            )
        
        return {"message": "Validation moderated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to moderate validation: {str(e)}"
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_moderation_statistics(
    timeframe_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_moderator())
):
    """Get moderation system statistics."""
    try:
        stats = await moderation_service.get_moderation_statistics(db, timeframe_days)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get moderation statistics: {str(e)}"
        )


@router.get("/workload", response_model=Dict[str, Any])
async def get_moderator_workload(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_moderator())
):
    """Get workload information for the current moderator."""
    try:
        workload = await moderation_service.get_moderator_workload(current_user.id)
        return workload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workload: {str(e)}"
        )


# Appeal System Endpoints

@router.post("/appeal/{validation_id}", response_model=AppealResponse)
async def submit_appeal(
    validation_id: str,
    request: AppealRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit an appeal against a moderation action."""
    try:
        appeal = await moderation_service.submit_appeal(
            db, validation_id, current_user.id, request.appeal_reason, request.evidence
        )
        
        return AppealResponse(
            validation_id=appeal.validation_id,
            user_id=appeal.user_id,
            original_action=appeal.original_action,
            appeal_reason=appeal.appeal_reason,
            status=appeal.status,
            assigned_reviewer=appeal.assigned_reviewer,
            created_at=appeal.created_at.isoformat(),
            resolved_at=appeal.resolved_at.isoformat() if appeal.resolved_at else None,
            resolution=appeal.resolution,
            metadata=appeal.metadata
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit appeal: {str(e)}"
        )


@router.post("/appeal/{validation_id}/process")
async def process_appeal(
    validation_id: str,
    request: ProcessAppealRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin())
):
    """Process an appeal (admin only)."""
    try:
        success = await moderation_service.process_appeal(
            db, validation_id, current_user.id, request.approved, request.resolution
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appeal not found"
            )
        
        return {"message": "Appeal processed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process appeal: {str(e)}"
        )


# Automated Processing Endpoints

@router.post("/process-queue")
async def process_moderation_queue(
    max_items: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin())
):
    """Process the moderation queue (admin only)."""
    try:
        decisions = await fraud_detection_service.process_moderation_queue(db, max_items)
        
        return {
            "message": f"Processed {len(decisions)} items",
            "processed_count": len(decisions)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process moderation queue: {str(e)}"
        )


@router.post("/process-validation/{validation_id}")
async def process_validation_moderation(
    validation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_moderator())
):
    """Process a specific validation through the moderation pipeline."""
    try:
        item = await moderation_service.process_validation_for_moderation(
            db, validation_id
        )
        
        if item:
            return {
                "message": "Validation added to moderation queue",
                "moderation_item": ModerationItemResponse(
                    validation_id=item.validation_id,
                    user_id=item.user_id,
                    fraud_results=[
                        FraudDetectionResponse(
                            fraud_type=result.fraud_type,
                            severity=result.severity,
                            confidence_score=result.confidence_score,
                            evidence=result.evidence,
                            recommended_action=result.recommended_action,
                            metadata=result.metadata,
                            detected_at=result.detected_at.isoformat()
                        )
                        for result in item.fraud_results
                    ],
                    status=item.status,
                    priority=item.priority,
                    assigned_moderator=item.assigned_moderator,
                    created_at=item.created_at.isoformat(),
                    updated_at=item.updated_at.isoformat(),
                    metadata=item.metadata
                )
            }
        else:
            return {"message": "Validation auto-approved"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process validation: {str(e)}"
        )
