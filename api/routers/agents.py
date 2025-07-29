"""
API endpoints for interacting with the agent system.
"""

import asyncio
import traceback
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from shared.services.opportunity_service import opportunity_service
from shared.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from shared.schemas.opportunity import OpportunityResponse
import structlog

from api.core.dependencies import get_orchestrator
from agents.orchestrator import AgentOrchestrator

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.post("/opportunities/{opportunity_id}/deep-dive", status_code=202)
async def trigger_deep_dive_workflow(
    opportunity_id: str,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers a dynamic workflow to perform a deep dive on an existing opportunity.
    """
    logger.info(f"Deep dive requested for opportunity: {opportunity_id}")
    
    try:
        logger.info("Fetching opportunity from database...")
        opportunity = await opportunity_service.get_opportunity_by_id(db, opportunity_id, include_relationships=False)
        if not opportunity:
            logger.warning(f"Opportunity not found: {opportunity_id}")
            raise HTTPException(status_code=404, detail="Opportunity not found.")
        
        logger.info(f"Found opportunity: {opportunity.title}")
        
        # Create a problem description from the opportunity
        problem_description = f"Perform deep dive analysis on opportunity: {opportunity.title}. Description: {opportunity.description}"
        logger.info(f"Problem description: {problem_description}")
        
        logger.info("Triggering workflow with orchestrator...")
        workflow_id = await orchestrator.trigger_dynamic_workflow(problem_description)
        logger.info(f"Workflow triggered successfully: {workflow_id}")
        
        return {"message": "Deep dive workflow triggered successfully.", "workflow_id": workflow_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in deep dive workflow: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger workflow: {str(e)}")

@router.get("/workflows/{workflow_id}/status")
async def get_workflow_status(
    workflow_id: str,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """
    Gets the status of a specific workflow.
    """
    try:
        status = await orchestrator.get_workflow_status(workflow_id)
        return status
    except ValueError:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow status: {e}")