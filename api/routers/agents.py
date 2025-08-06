"""
API endpoints for interacting with the agent system.
"""

import asyncio
import traceback
import re
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from shared.services.opportunity_service import opportunity_service
from shared.database import get_db
from shared.schemas.opportunity import OpportunityResponse, OpportunityCreate, OpportunityUpdate
from api.core.dependencies import get_orchestrator
from agents.orchestrator import OpportunityOrchestrator

logger = structlog.get_logger(__name__)

router = APIRouter()

# --- Pydantic Models and Helper Functions ---

class GenerateOpportunityRequest(BaseModel):
    topic: str

def parse_generated_opportunity(text: str) -> dict:
    """
    Parses the unstructured text from the AI into a structured dictionary.
    Handles both custom orchestrator format and DSPy format.
    """
    data = {}
    try:
        # Try parsing custom orchestrator format first (Title:, Description:, Summary:)
        title_match = re.search(r"Title: (.*?)(?=\n|$)", text)
        description_match = re.search(r"Description: (.*?)(?=\n\nSummary:|\n\n---|\n\n\*\*|$)", text, re.DOTALL)
        summary_match = re.search(r"Summary: (.*?)(?=\n\n|$)", text, re.DOTALL)

        if title_match and description_match and summary_match:
            # Custom orchestrator format found
            data['title'] = title_match.group(1).strip()
            data['description'] = description_match.group(1).strip()
            data['summary'] = summary_match.group(1).strip()
        else:
            # Try DSPy format parsing (different structure)
            # Look for AI Opportunity: or **AI Opportunity:**
            opportunity_match = re.search(r"\*\*AI Opportunity:\s*(.*?)\*\*", text)
            solution_match = re.search(r"\*\*Solution:\*\*(.*?)(?=\*\*Target Users:|\*\*Value Proposition:|\*\*Next Steps:|$)", text, re.DOTALL)
            target_users_match = re.search(r"\*\*Target Users:\*\*(.*?)(?=\*\*Value Proposition:|\*\*Next Steps:|\*\*|$)", text, re.DOTALL)
            value_prop_match = re.search(r"\*\*Value Proposition:\*\*(.*?)(?=\*\*Next Steps:|\*\*|$)", text, re.DOTALL)
            
            if opportunity_match and solution_match:
                # DSPy format found
                data['title'] = opportunity_match.group(1).strip()
                
                # Combine solution and target users for description
                description_parts = []
                if solution_match:
                    description_parts.append(f"Solution: {solution_match.group(1).strip()}")
                if target_users_match:
                    description_parts.append(f"Target Users: {target_users_match.group(1).strip()}")
                
                data['description'] = "\n\n".join(description_parts)
                
                # Use value proposition as summary, or create one
                if value_prop_match:
                    data['summary'] = value_prop_match.group(1).strip()[:400]  # Limit length
                else:
                    # Create summary from first part of solution
                    solution_text = solution_match.group(1).strip()
                    first_sentence = solution_text.split('.')[0] + '.'
                    data['summary'] = first_sentence[:400]
            else:
                # Fallback: extract first meaningful parts
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                # Try to find a title-like line
                title_candidates = [line for line in lines if len(line) < 100 and ('AI' in line or 'Opportunity' in line)]
                if title_candidates:
                    data['title'] = title_candidates[0].replace('**', '').replace('*', '').strip()
                else:
                    data['title'] = "AI-Generated Opportunity"
                
                # Use first few lines as description
                data['description'] = '\n'.join(lines[:5]) if len(lines) >= 5 else text[:500]
                
                # Create summary from first line or sentence
                first_line = lines[0] if lines else text[:200]
                data['summary'] = first_line[:400]

    except (AttributeError, IndexError) as e:
        # Fallback parsing failed, create basic structure
        logger.warning(f"Advanced parsing failed, using fallback: {e}")
        data['title'] = "AI-Generated Opportunity"
        data['description'] = text[:1000] if len(text) > 1000 else text
        data['summary'] = text[:400] if len(text) > 400 else text

    # Ensure all fields have content
    if not data.get('title'):
        data['title'] = "AI-Generated Opportunity"
    if not data.get('description'):
        data['description'] = text[:1000]
    if not data.get('summary'):
        data['summary'] = text[:400]

    # Add default values for other required fields
    data['ai_solution_types'] = ["AI/ML", "Automation"]
    data['target_industries'] = ["Technology", "Business Services"]
    
    return data

# --- API Endpoints ---

@router.post("/opportunities/{opportunity_id}/deep-dive", response_model=OpportunityResponse, status_code=202)
async def trigger_deep_dive_workflow(
    opportunity_id: str,
    orchestrator: OpportunityOrchestrator = Depends(get_orchestrator),
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
        
        problem_description = f"Perform deep dive analysis on opportunity: {opportunity.title}. Description: {opportunity.description}"
        logger.info(f"Problem description: {problem_description}")
        
        analysis_result = await orchestrator.analyze_opportunity(problem_description)
        
        update_data = OpportunityUpdate(description=analysis_result)
        updated_opportunity = await opportunity_service.update_opportunity(db=db, opportunity_id=opportunity_id, opportunity_data=update_data)
        
        logger.info(f"Deep dive analysis completed for opportunity: {opportunity_id}")
        return updated_opportunity

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in deep dive workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger workflow: {str(e)}")


@router.post("/generate-opportunity", status_code=200)
async def generate_new_opportunity(
    request: GenerateOpportunityRequest,
    orchestrator: OpportunityOrchestrator = Depends(get_orchestrator),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a new opportunity from a high-level topic and saves it to database.
    """
    logger.info(f"New opportunity generation requested for topic: {request.topic}")
    
    try:
        # For now, create a simple opportunity without DSPy to test database persistence
        # TODO: Re-enable DSPy integration once database saving is working
        from shared.schemas.opportunity import OpportunityCreate
        
        # Ensure description meets minimum 50 character requirement
        description = f"Innovative AI solution for {request.topic}. This opportunity leverages machine learning and advanced analytics to address market needs in the {request.topic} domain. The solution offers significant potential for automation, efficiency improvements, and competitive advantage through intelligent data processing and predictive capabilities."
        
        opportunity_data = OpportunityCreate(
            title=f"AI-Powered {request.topic.title()} Solution",
            description=description,
            summary=f"AI-driven solution targeting {request.topic} with high market potential and technical feasibility.",
            ai_solution_types=["Machine Learning", "Natural Language Processing", "Computer Vision"],
            target_industries=["Technology", "AI/ML"],
            geographic_scope="global",
            tags=["ai-generated", "opportunity-generator", request.topic.replace(" ", "-").lower()],
            discovery_method="ai_agent",
            required_capabilities=["ML/AI Development", "Data Engineering", "Cloud Infrastructure"],
            source_urls=[]
        )
        
        # Save to database using opportunity service
        created_opportunity = await opportunity_service.create_opportunity(
            db=db,
            opportunity_data=opportunity_data,
            discovered_by_agent="Opportunity Generator"
        )
        
        logger.info(f"Successfully created opportunity with ID: {created_opportunity.id}")
        
        # Return format expected by frontend
        return {
            "success": True,
            "opportunity_id": created_opportunity.id,
            "title": created_opportunity.title,
            "description": created_opportunity.description,
            "summary": created_opportunity.summary,
            "topic_requested": request.topic,
            "message": "Opportunity generated and saved to database successfully"
        }
        
    except ValueError as ve:
        logger.error(f"Error parsing generated opportunity: {ve}")
        raise HTTPException(status_code=500, detail=f"Failed to parse generated opportunity: {ve}")
    except Exception as e:
        logger.error(f"Error generating new opportunity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while generating the opportunity.")
