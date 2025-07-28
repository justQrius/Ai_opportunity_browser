"""
Feature Flag Management API Endpoints

This module provides REST API endpoints for managing feature flags:
- CRUD operations for feature flags
- Feature flag evaluation
- Analytics and usage tracking
- Gradual rollout management
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

from api.core.dependencies import get_current_user, require_admin
from shared.feature_flags import (
    FeatureFlagService,
    FeatureFlag,
    FeatureFlagStatus,
    RolloutStrategy,
    RolloutConfig,
    FeatureVariant,
    TargetingRule,
    UserContext,
    FeatureFlagEvaluation,
    get_feature_flag_service
)
from shared.models.user import User

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])
security = HTTPBearer()


# Request/Response Models

class CreateFeatureFlagRequest(BaseModel):
    """Request model for creating a feature flag."""
    name: str = Field(..., description="Feature flag name (unique identifier)")
    description: str = Field(..., description="Human-readable description")
    default_value: Any = Field(False, description="Default value when flag is disabled")
    rollout_config: Optional[RolloutConfig] = Field(None, description="Rollout configuration")
    variants: Optional[List[FeatureVariant]] = Field(None, description="A/B testing variants")
    environments: Optional[List[str]] = Field(None, description="Target environments")
    tags: Optional[List[str]] = Field(None, description="Organizational tags")


class UpdateFeatureFlagRequest(BaseModel):
    """Request model for updating a feature flag."""
    description: Optional[str] = None
    status: Optional[FeatureFlagStatus] = None
    default_value: Optional[Any] = None
    rollout_config: Optional[RolloutConfig] = None
    variants: Optional[List[FeatureVariant]] = None
    environments: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class FeatureFlagEvaluationRequest(BaseModel):
    """Request model for feature flag evaluation."""
    flag_name: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    plan: Optional[str] = None
    country: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    environment: Optional[str] = None


class FeatureFlagResponse(BaseModel):
    """Response model for feature flag."""
    name: str
    description: str
    status: FeatureFlagStatus
    default_value: Any
    rollout_config: RolloutConfig
    variants: Optional[List[FeatureVariant]]
    environments: List[str]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str


class FeatureFlagEvaluationResponse(BaseModel):
    """Response model for feature flag evaluation."""
    flag_name: str
    enabled: bool
    variant: Optional[str] = None
    value: Any = None
    reason: str
    evaluated_at: datetime


class FeatureFlagAnalyticsResponse(BaseModel):
    """Response model for feature flag analytics."""
    flag_name: str
    environment: str
    period: Dict[str, str]
    total_evaluations: int
    enabled_count: int
    disabled_count: int
    unique_users: int
    variants: Dict[str, int]
    daily_stats: Dict[str, Dict[str, int]]


class TrackUsageRequest(BaseModel):
    """Request model for tracking feature usage."""
    flag_name: str
    outcome: str
    metadata: Optional[Dict[str, Any]] = None


# API Endpoints

@router.post("/", response_model=FeatureFlagResponse)
async def create_feature_flag(
    request: CreateFeatureFlagRequest,
    current_user: User = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """Create a new feature flag."""
    try:
        flag = await service.create_feature_flag(
            name=request.name,
            description=request.description,
            default_value=request.default_value,
            rollout_config=request.rollout_config,
            variants=request.variants,
            environments=request.environments,
            tags=request.tags,
            created_by=current_user.email
        )
        
        return FeatureFlagResponse(**flag.dict())
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create feature flag: {str(e)}")


@router.get("/", response_model=List[FeatureFlagResponse])
async def list_feature_flags(
    environment: Optional[str] = Query(None, description="Filter by environment"),
    status: Optional[FeatureFlagStatus] = Query(None, description="Filter by status"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    current_user: User = Depends(get_current_user),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """List feature flags with optional filtering."""
    try:
        flags = await service.list_feature_flags(
            environment=environment,
            status=status,
            tags=tags
        )
        
        return [FeatureFlagResponse(**flag.dict()) for flag in flags]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list feature flags: {str(e)}")


@router.get("/{flag_name}", response_model=FeatureFlagResponse)
async def get_feature_flag(
    flag_name: str,
    current_user: User = Depends(get_current_user),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """Get a specific feature flag."""
    try:
        flag = await service.get_feature_flag(flag_name)
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")
        
        return FeatureFlagResponse(**flag.dict())
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get feature flag: {str(e)}")


@router.put("/{flag_name}", response_model=FeatureFlagResponse)
async def update_feature_flag(
    flag_name: str,
    request: UpdateFeatureFlagRequest,
    current_user: User = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """Update a feature flag."""
    try:
        flag = await service.update_feature_flag(
            name=flag_name,
            description=request.description,
            status=request.status,
            default_value=request.default_value,
            rollout_config=request.rollout_config,
            variants=request.variants,
            environments=request.environments,
            tags=request.tags,
            updated_by=current_user.email
        )
        
        return FeatureFlagResponse(**flag.dict())
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update feature flag: {str(e)}")


@router.delete("/{flag_name}")
async def delete_feature_flag(
    flag_name: str,
    current_user: User = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """Delete a feature flag."""
    try:
        deleted = await service.delete_feature_flag(flag_name, deleted_by=current_user.email)
        if not deleted:
            raise HTTPException(status_code=404, detail="Feature flag not found")
        
        return {"message": f"Feature flag '{flag_name}' deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete feature flag: {str(e)}")


@router.post("/evaluate", response_model=FeatureFlagEvaluationResponse)
async def evaluate_feature_flag(
    request: FeatureFlagEvaluationRequest,
    current_user: User = Depends(get_current_user),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """Evaluate a feature flag for a user context."""
    try:
        # Build user context
        user_context = UserContext(
            user_id=request.user_id or current_user.id,
            email=request.email or current_user.email,
            role=request.role or current_user.role.value,
            plan=request.plan,
            country=request.country,
            created_at=current_user.created_at,
            attributes=request.attributes
        )
        
        evaluation = await service.evaluate_feature_flag(
            flag_name=request.flag_name,
            user_context=user_context,
            environment=request.environment
        )
        
        return FeatureFlagEvaluationResponse(
            flag_name=evaluation.flag_name,
            enabled=evaluation.enabled,
            variant=evaluation.variant,
            value=evaluation.value,
            reason=evaluation.reason,
            evaluated_at=evaluation.evaluated_at
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate feature flag: {str(e)}")


@router.get("/{flag_name}/enabled")
async def is_feature_enabled(
    flag_name: str,
    environment: Optional[str] = Query(None, description="Target environment"),
    current_user: User = Depends(get_current_user),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """Check if a feature flag is enabled for the current user."""
    try:
        user_context = UserContext(
            user_id=current_user.id,
            email=current_user.email,
            role=current_user.role.value,
            created_at=current_user.created_at
        )
        
        enabled = await service.is_feature_enabled(
            flag_name=flag_name,
            user_context=user_context,
            environment=environment
        )
        
        return {"flag_name": flag_name, "enabled": enabled}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check feature flag: {str(e)}")


@router.get("/{flag_name}/variant")
async def get_feature_variant(
    flag_name: str,
    environment: Optional[str] = Query(None, description="Target environment"),
    current_user: User = Depends(get_current_user),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """Get the feature flag variant for the current user."""
    try:
        user_context = UserContext(
            user_id=current_user.id,
            email=current_user.email,
            role=current_user.role.value,
            created_at=current_user.created_at
        )
        
        variant = await service.get_feature_variant(
            flag_name=flag_name,
            user_context=user_context,
            environment=environment
        )
        
        return {"flag_name": flag_name, "variant": variant}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get feature variant: {str(e)}")


@router.post("/{flag_name}/track")
async def track_feature_usage(
    flag_name: str,
    request: TrackUsageRequest,
    environment: Optional[str] = Query(None, description="Target environment"),
    current_user: User = Depends(get_current_user),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """Track feature flag usage outcome."""
    try:
        await service.track_feature_usage(
            flag_name=flag_name,
            user_id=current_user.id,
            outcome=request.outcome,
            environment=environment,
            metadata=request.metadata
        )
        
        return {"message": "Usage tracked successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track usage: {str(e)}")


@router.get("/{flag_name}/analytics", response_model=FeatureFlagAnalyticsResponse)
async def get_feature_analytics(
    flag_name: str,
    start_date: Optional[datetime] = Query(None, description="Start date for analytics"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics"),
    environment: Optional[str] = Query(None, description="Target environment"),
    current_user: User = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """Get feature flag usage analytics."""
    try:
        analytics = await service.get_feature_analytics(
            flag_name=flag_name,
            start_date=start_date,
            end_date=end_date,
            environment=environment
        )
        
        return FeatureFlagAnalyticsResponse(**analytics)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


# Bulk Operations

@router.post("/bulk/evaluate")
async def bulk_evaluate_feature_flags(
    flag_names: List[str],
    environment: Optional[str] = Query(None, description="Target environment"),
    current_user: User = Depends(get_current_user),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """Evaluate multiple feature flags for the current user."""
    try:
        user_context = UserContext(
            user_id=current_user.id,
            email=current_user.email,
            role=current_user.role.value,
            created_at=current_user.created_at
        )
        
        results = {}
        for flag_name in flag_names:
            evaluation = await service.evaluate_feature_flag(
                flag_name=flag_name,
                user_context=user_context,
                environment=environment
            )
            results[flag_name] = {
                "enabled": evaluation.enabled,
                "variant": evaluation.variant,
                "value": evaluation.value,
                "reason": evaluation.reason
            }
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bulk evaluate flags: {str(e)}")


@router.put("/bulk/status")
async def bulk_update_flag_status(
    flag_names: List[str],
    status: FeatureFlagStatus,
    current_user: User = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """Update status for multiple feature flags."""
    try:
        results = {}
        for flag_name in flag_names:
            try:
                flag = await service.update_feature_flag(
                    name=flag_name,
                    status=status,
                    updated_by=current_user.email
                )
                results[flag_name] = {"success": True, "status": flag.status.value}
            except Exception as e:
                results[flag_name] = {"success": False, "error": str(e)}
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bulk update flags: {str(e)}")


# Management Endpoints

@router.post("/{flag_name}/rollout/percentage")
async def update_rollout_percentage(
    flag_name: str,
    percentage: float = Query(..., ge=0, le=100, description="Rollout percentage (0-100)"),
    current_user: User = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """Update rollout percentage for a feature flag."""
    try:
        flag = await service.get_feature_flag(flag_name)
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")
        
        # Update rollout config
        rollout_config = flag.rollout_config
        rollout_config.strategy = RolloutStrategy.PERCENTAGE
        rollout_config.percentage = percentage
        
        updated_flag = await service.update_feature_flag(
            name=flag_name,
            rollout_config=rollout_config,
            updated_by=current_user.email
        )
        
        return {
            "flag_name": flag_name,
            "percentage": percentage,
            "message": f"Rollout percentage updated to {percentage}%"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update rollout: {str(e)}")


@router.post("/{flag_name}/rollout/users")
async def update_rollout_users(
    flag_name: str,
    user_ids: List[str],
    current_user: User = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """Update user list for rollout targeting."""
    try:
        flag = await service.get_feature_flag(flag_name)
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")
        
        # Update rollout config
        rollout_config = flag.rollout_config
        rollout_config.strategy = RolloutStrategy.USER_LIST
        rollout_config.user_ids = user_ids
        
        updated_flag = await service.update_feature_flag(
            name=flag_name,
            rollout_config=rollout_config,
            updated_by=current_user.email
        )
        
        return {
            "flag_name": flag_name,
            "user_count": len(user_ids),
            "message": f"Rollout updated to target {len(user_ids)} users"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update rollout: {str(e)}")


@router.get("/health")
async def feature_flags_health():
    """Health check endpoint for feature flags service."""
    try:
        service = await get_feature_flag_service()
        # Simple health check - try to list flags
        flags = await service.list_feature_flags()
        
        return {
            "status": "healthy",
            "service": "feature_flags",
            "flags_count": len(flags),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Feature flags service unhealthy: {str(e)}")