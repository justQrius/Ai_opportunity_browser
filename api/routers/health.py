"""
Health check endpoints for the AI Opportunity Browser API.

This module provides health check endpoints to monitor the status
of the API and its dependencies.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
import time

from api.core.config import get_settings

router = APIRouter()
settings = get_settings()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    checks: Dict[str, Any]


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model."""
    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    system_info: Dict[str, Any]
    dependencies: Dict[str, Any]
    metrics: Dict[str, Any]


# Track application start time
_start_time = time.time()


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns the current status of the API service.
    """
    current_time = time.time()
    uptime = current_time - _start_time
    
    # Basic checks
    checks = {
        "api": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        uptime_seconds=uptime,
        checks=checks
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """
    Detailed health check endpoint with dependency status.
    
    Returns comprehensive health information including database,
    cache, and external service connectivity.
    """
    current_time = time.time()
    uptime = current_time - _start_time
    
    # System information
    system_info = {
        "python_version": "3.12+",
        "fastapi_version": "0.104+",
        "environment": settings.ENVIRONMENT,
        "debug_mode": settings.DEBUG,
    }
    
    # Check dependencies
    dependencies = await _check_dependencies()
    
    # Calculate overall status
    overall_status = "healthy"
    if any(dep.get("status") == "unhealthy" for dep in dependencies.values()):
        overall_status = "degraded"
    if all(dep.get("status") == "unhealthy" for dep in dependencies.values()):
        overall_status = "unhealthy"
    
    # Basic metrics
    metrics = {
        "uptime_seconds": uptime,
        "memory_usage": "N/A",  # Will be implemented with proper monitoring
        "request_count": "N/A",
        "error_rate": "N/A",
    }
    
    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        uptime_seconds=uptime,
        system_info=system_info,
        dependencies=dependencies,
        metrics=metrics
    )


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes readiness probe endpoint.
    
    Returns 200 if the service is ready to accept traffic.
    """
    # Check critical dependencies
    dependencies = await _check_dependencies()
    
    # Service is ready if database is accessible
    if dependencies.get("database", {}).get("status") == "healthy":
        return {"status": "ready", "timestamp": datetime.utcnow()}
    else:
        raise HTTPException(
            status_code=503,
            detail="Service not ready - database unavailable"
        )


@router.get("/live")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    
    Returns 200 if the service is alive and functioning.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow(),
        "uptime_seconds": time.time() - _start_time
    }


async def _check_dependencies() -> Dict[str, Any]:
    """Check the status of external dependencies."""
    dependencies = {}
    
    # Check database connectivity
    dependencies["database"] = await _check_database()
    
    # Check Redis cache
    dependencies["cache"] = await _check_redis()
    
    # Check vector database
    dependencies["vector_db"] = await _check_vector_db()
    
    return dependencies


async def _check_database() -> Dict[str, Any]:
    """Check PostgreSQL database connectivity."""
    from shared.database import check_database_health
    return await check_database_health()


async def _check_redis() -> Dict[str, Any]:
    """Check Redis cache connectivity."""
    from shared.database import check_redis_health
    return await check_redis_health()


async def _check_vector_db() -> Dict[str, Any]:
    """Check vector database connectivity."""
    from shared.database import check_vector_db_health
    return await check_vector_db_health()