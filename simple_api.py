#!/usr/bin/env python3
"""
Simplified API server for testing the AI Opportunity Browser frontend.
This bypasses complex imports and focuses on getting the frontend working.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime
import json

# Simple data models
class Opportunity(BaseModel):
    id: str
    title: str
    description: str
    industry: str
    ai_solution_type: str
    validation_score: int
    ai_feasibility_score: int
    market_size_estimate: int
    implementation_complexity: str
    validation_count: int
    created_at: str
    updated_at: str

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: dict

# Create FastAPI app
app = FastAPI(
    title="AI Opportunity Browser API (Simplified)",
    description="Simplified API for testing frontend integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data
MOCK_OPPORTUNITIES = [
    {
        "id": "1",
        "title": "AI-Powered Customer Service Automation for SMBs",
        "description": "Automated customer service system using NLP to handle 80% of customer inquiries for small and medium businesses.",
        "industry": "Technology",
        "ai_solution_type": "Natural Language Processing",
        "validation_score": 87,
        "ai_feasibility_score": 85,
        "market_size_estimate": 5000000,
        "implementation_complexity": "MEDIUM",
        "validation_count": 12,
        "created_at": "2024-01-20T10:00:00Z",
        "updated_at": "2024-01-20T10:00:00Z"
    },
    {
        "id": "2", 
        "title": "AI Diagnostic Assistant for Rural Healthcare",
        "description": "Machine learning system to assist rural healthcare providers with preliminary diagnosis suggestions.",
        "industry": "Healthcare",
        "ai_solution_type": "Machine Learning",
        "validation_score": 92,
        "ai_feasibility_score": 78,
        "market_size_estimate": 15000000,
        "implementation_complexity": "HIGH",
        "validation_count": 23,
        "created_at": "2024-01-19T14:30:00Z",
        "updated_at": "2024-01-19T14:30:00Z"
    },
    {
        "id": "3",
        "title": "Automated Inventory Management with Computer Vision", 
        "description": "Computer vision solution for real-time inventory tracking in retail environments.",
        "industry": "Retail",
        "ai_solution_type": "Computer Vision",
        "validation_score": 76,
        "ai_feasibility_score": 90,
        "market_size_estimate": 8000000,
        "implementation_complexity": "MEDIUM",
        "validation_count": 8,
        "created_at": "2024-01-18T09:15:00Z",
        "updated_at": "2024-01-18T09:15:00Z"
    },
    {
        "id": "4",
        "title": "Smart Predictive Maintenance for Manufacturing",
        "description": "IoT sensors combined with AI to predict equipment failures before they occur, reducing downtime by 40%.",
        "industry": "Manufacturing", 
        "ai_solution_type": "Predictive Analytics",
        "validation_score": 84,
        "ai_feasibility_score": 82,
        "market_size_estimate": 12000000,
        "implementation_complexity": "HIGH",
        "validation_count": 15,
        "created_at": "2024-01-17T16:45:00Z",
        "updated_at": "2024-01-17T16:45:00Z"
    },
    {
        "id": "5",
        "title": "AI-Driven Content Personalization Engine",
        "description": "Dynamic content personalization for e-commerce platforms to increase conversion rates by 30%.",
        "industry": "E-commerce",
        "ai_solution_type": "Machine Learning",
        "validation_score": 79,
        "ai_feasibility_score": 88,
        "market_size_estimate": 25000000,
        "implementation_complexity": "MEDIUM",
        "validation_count": 19,
        "created_at": "2024-01-16T11:20:00Z",
        "updated_at": "2024-01-16T11:20:00Z"
    }
]

MOCK_USER = {
    "id": "demo-user-123",
    "email": "demo@example.com",
    "full_name": "Demo User",
    "expertise_domains": ["Machine Learning", "Natural Language Processing"],
    "reputation_score": 2847,
    "is_verified": True
}

# Routes
@app.get("/")
async def root():
    return {"message": "AI Opportunity Browser API - Simplified Version"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.post("/auth/login")
async def login(credentials: LoginRequest):
    # Accept any email/password for demo
    if credentials.email and credentials.password:
        return AuthResponse(
            access_token="demo-access-token-123",
            refresh_token="demo-refresh-token-456", 
            token_type="bearer",
            user=MOCK_USER
        )
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/auth/register")
async def register(data: dict):
    return AuthResponse(
        access_token="demo-access-token-123",
        refresh_token="demo-refresh-token-456",
        token_type="bearer", 
        user=MOCK_USER
    )

@app.get("/users/me")
async def get_current_user():
    return MOCK_USER

@app.get("/opportunities/")
async def get_opportunities(
    page: int = 1,
    size: int = 10,
    query: Optional[str] = None,
    industry: Optional[str] = None
):
    filtered_opportunities = MOCK_OPPORTUNITIES.copy()
    
    # Simple filtering
    if query:
        filtered_opportunities = [
            opp for opp in filtered_opportunities 
            if query.lower() in opp["title"].lower() or query.lower() in opp["description"].lower()
        ]
    
    if industry:
        filtered_opportunities = [
            opp for opp in filtered_opportunities
            if opp["industry"].lower() == industry.lower()
        ]
    
    # Simple pagination
    start = (page - 1) * size
    end = start + size
    items = filtered_opportunities[start:end]
    
    return {
        "items": items,
        "total": len(filtered_opportunities),
        "page": page,
        "size": size,
        "pages": (len(filtered_opportunities) + size - 1) // size
    }

@app.get("/opportunities/{opportunity_id}")
async def get_opportunity(opportunity_id: str):
    opportunity = next((opp for opp in MOCK_OPPORTUNITIES if opp["id"] == opportunity_id), None)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity

@app.get("/opportunities/search")
async def search_opportunities(query: str = "", page: int = 1, size: int = 10):
    return await get_opportunities(page=page, size=size, query=query)

@app.get("/opportunities/recommendations")
async def get_recommendations(limit: int = 5):
    return MOCK_OPPORTUNITIES[:limit]

@app.get("/opportunities/trending") 
async def get_trending(limit: int = 5):
    # Return sorted by validation score
    sorted_opps = sorted(MOCK_OPPORTUNITIES, key=lambda x: x["validation_score"], reverse=True)
    return sorted_opps[:limit]

if __name__ == "__main__":
    uvicorn.run(
        "simple_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )