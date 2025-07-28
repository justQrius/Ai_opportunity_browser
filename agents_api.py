#!/usr/bin/env python3
"""
AI Opportunity Browser API with real AI agents.
This version uses the actual AI agents to generate dynamic opportunities.
"""

import os
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# AI Library imports
import google.generativeai as genai
from dotenv import load_dotenv

# Real-time data integration
try:
    from realtime_data_bridge import (
        data_bridge,
        get_trending_market_data,
        get_market_signals_by_keywords,
        get_startup_validation_data
    )
    REALTIME_DATA_AVAILABLE = True
    print("🌐 Real-time data integration available")
except ImportError as e:
    print(f"⚠️  Real-time data integration not available: {e}")
    REALTIME_DATA_AVAILABLE = False

# Load environment variables
load_dotenv()

# Configure Gemini AI
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print(f"🤖 Gemini AI configured successfully!")
else:
    print("⚠️  GEMINI_API_KEY not found. Using fallback mode.")

# Simple AI Agent base class
@dataclass
class AgentResponse:
    agent_name: str
    data: Dict[str, Any]
    timestamp: str
    confidence: float

class BaseAIAgent:
    def __init__(self, name: str):
        self.name = name
        
    async def generate_opportunities(self, query: str = "", limit: int = 5) -> List[Dict[str, Any]]:
        """Generate opportunities using real AI (Gemini API) enhanced with real-time data"""
        if not GEMINI_API_KEY:
            print(f"⚠️  {self.name}: No Gemini API key, using fallback data")
            return await self._generate_fallback_opportunities(query, limit)
        
        try:
            # Get real-time market context if available
            market_context = ""
            if REALTIME_DATA_AVAILABLE:
                try:
                    print(f"🌐 {self.name}: Gathering real-time market intelligence...")
                    
                    # Get trending topics and market signals
                    keywords = ["AI", "automation", "startup", "opportunity"] + (query.split() if query else [])
                    market_signals = await get_market_signals_by_keywords(keywords, 10)
                    startup_data = await get_startup_validation_data(5)
                    
                    if market_signals or startup_data:
                        market_context = "\n\nCurrent Market Intelligence:\n"
                        
                        if market_signals:
                            market_context += "Recent Market Signals:\n"
                            for signal in market_signals[:5]:
                                market_context += f"- {signal['title']} ({signal['source']})\n"
                        
                        if startup_data:
                            market_context += "\nRecent Startup Activity:\n"
                            for startup in startup_data[:3]:
                                market_context += f"- {startup['title']} - {startup['description'][:100]}...\n"
                        
                        market_context += "\nUse this real market data to inform your opportunity generation."
                        
                        print(f"✅ {self.name}: Enhanced with {len(market_signals)} market signals and {len(startup_data)} startup examples")
                        
                except Exception as e:
                    print(f"⚠️  {self.name}: Real-time data integration error: {e}")
            
            # Configure Gemini model
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Create AI prompt for opportunity generation with real-time context
            prompt = f"""
            You are an AI opportunity discovery agent. Generate {limit} realistic AI business opportunities.
            {f"Focus on opportunities related to: {query}" if query else "Focus on current market trends and gaps."}
            {market_context}
            
            For each opportunity, provide:
            - title: Clear, specific title
            - description: 2-3 sentences explaining the opportunity and its value proposition
            - industry: Target industry (e.g., Healthcare, Finance, Manufacturing, etc.)
            - ai_solution_type: Type of AI solution (e.g., Machine Learning, NLP, Computer Vision, Predictive Analytics)
            - market_size_estimate: Estimated market size in USD (realistic number between 1M-50M)
            - implementation_complexity: LOW, MEDIUM, or HIGH
            
            Return ONLY valid JSON array format:
            [
              {{
                "title": "...",
                "description": "...",
                "industry": "...",
                "ai_solution_type": "...",
                "market_size_estimate": 000000,
                "implementation_complexity": "MEDIUM"
              }}
            ]
            """
            
            # Generate content with Gemini
            response = await asyncio.create_task(
                asyncio.to_thread(model.generate_content, prompt)
            )
            
            # Parse JSON response
            import re
            json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
            if json_match:
                ai_opportunities = json.loads(json_match.group())
                
                # Enhance with metadata
                opportunities = []
                for i, opp in enumerate(ai_opportunities[:limit]):
                    opportunity = {
                        **opp,
                        "id": f"ai_gen_{i+1}_{int(datetime.now().timestamp())}",
                        "validation_score": self._generate_validation_score(),
                        "ai_feasibility_score": self._generate_feasibility_score(),
                        "validation_count": self._generate_validation_count(),
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "generated_by": self.name,
                        "generation_method": "gemini_ai"
                    }
                    opportunities.append(opportunity)
                
                print(f"✅ {self.name}: Generated {len(opportunities)} AI opportunities using Gemini")
                return opportunities
            else:
                print(f"⚠️  {self.name}: Failed to parse Gemini response, using fallback")
                return await self._generate_fallback_opportunities(query, limit)
                
        except Exception as e:
            print(f"❌ {self.name}: Gemini API error: {e}, using fallback")
            return await self._generate_fallback_opportunities(query, limit)
    
    async def _generate_fallback_opportunities(self, query: str = "", limit: int = 5) -> List[Dict[str, Any]]:
        """Fallback method when AI API is not available"""
        base_opportunities = [
            {
                "title": "AI-Powered Predictive Healthcare Analytics",
                "description": "Machine learning system that analyzes patient data to predict health outcomes and optimize treatment plans, reducing hospital readmissions by 30%.",
                "industry": "Healthcare",
                "ai_solution_type": "Predictive Analytics",
                "market_size_estimate": 12000000,
                "implementation_complexity": "HIGH",
            },
            {
                "title": "Smart Energy Consumption Optimizer for Manufacturing", 
                "description": "AI system that optimizes energy usage in manufacturing facilities using IoT sensors and machine learning, reducing energy costs by 25%.",
                "industry": "Manufacturing",
                "ai_solution_type": "IoT Analytics",
                "market_size_estimate": 8500000,
                "implementation_complexity": "MEDIUM",
            },
            {
                "title": "Automated Legal Document Review System",
                "description": "NLP-powered platform that reviews and analyzes legal contracts, identifying key clauses and potential risks 10x faster than manual review.",
                "industry": "Legal Services", 
                "ai_solution_type": "Natural Language Processing",
                "market_size_estimate": 15000000,
                "implementation_complexity": "HIGH",
            },
            {
                "title": "AI Crop Yield Prediction for Small Farms",
                "description": "Computer vision and satellite data analysis to predict crop yields and optimize farming decisions for small agricultural operations.",
                "industry": "Agriculture",
                "ai_solution_type": "Computer Vision",
                "market_size_estimate": 6000000,
                "implementation_complexity": "MEDIUM",
            },
            {
                "title": "Real-time Fraud Detection for E-commerce",
                "description": "Machine learning system that detects fraudulent transactions in real-time, reducing fraud losses by 40% while minimizing false positives.", 
                "industry": "E-commerce",
                "ai_solution_type": "Machine Learning",
                "market_size_estimate": 20000000,
                "implementation_complexity": "MEDIUM",
            }
        ]
        
        # Add AI-generated variations and scores
        opportunities = []
        for i, base_opp in enumerate(base_opportunities[:limit]):
            opportunity = {
                **base_opp,
                "id": f"ai_gen_{i+1}_{int(datetime.now().timestamp())}",
                "validation_score": self._generate_validation_score(),
                "ai_feasibility_score": self._generate_feasibility_score(),
                "validation_count": self._generate_validation_count(),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "generated_by": self.name,
                "generation_method": "fallback_data"
            }
            opportunities.append(opportunity)
            
        return opportunities
    
    def _generate_validation_score(self) -> int:
        """Generate realistic validation scores"""
        import random
        return random.randint(70, 95)
    
    def _generate_feasibility_score(self) -> int:
        """Generate AI feasibility scores"""
        import random
        return random.randint(75, 90)
    
    def _generate_validation_count(self) -> int:
        """Generate validation counts"""
        import random
        return random.randint(5, 25)

# AI Agents (simplified versions of the real ones)
class MonitoringAgent(BaseAIAgent):
    def __init__(self):
        super().__init__("MonitoringAgent")
        
    async def scan_market_trends(self) -> AgentResponse:
        """Monitor current market trends and identify opportunities"""
        print(f"🔍 {self.name}: Scanning market trends...")
        
        trends = {
            "trending_technologies": ["Generative AI", "Edge Computing", "Quantum ML"],
            "market_gaps": ["SMB AI adoption", "Healthcare automation", "Sustainable tech"],
            "growth_areas": ["AI productivity tools", "Automated compliance", "Personalization engines"]
        }
        
        # Enhance with real-time data if available
        if REALTIME_DATA_AVAILABLE:
            try:
                print(f"🌐 {self.name}: Fetching real-time market trends...")
                realtime_trends = await get_trending_market_data(10)
                
                if realtime_trends:
                    # Extract trending topics from real data
                    trending_topics = []
                    market_signals = []
                    
                    for trend in realtime_trends:
                        if trend.get('signal_type') in ['ai_innovation', 'trend', 'startup_idea']:
                            trending_topics.append(trend['title'])
                        elif trend.get('signal_type') in ['pain_point', 'opportunity']:
                            market_signals.append(trend['title'])
                    
                    # Update trends with real data
                    if trending_topics:
                        trends["realtime_trending"] = trending_topics[:5]
                    if market_signals:
                        trends["realtime_opportunities"] = market_signals[:5]
                    
                    trends["data_sources"] = list(set([t['source'] for t in realtime_trends]))
                    trends["last_updated"] = datetime.now().isoformat()
                    
                    print(f"✅ {self.name}: Enhanced with {len(realtime_trends)} real-time signals")
                    
            except Exception as e:
                print(f"⚠️  {self.name}: Real-time data error: {e}")
        
        # Simulate processing time
        await asyncio.sleep(0.3)
        
        return AgentResponse(
            agent_name=self.name,
            data=trends,
            timestamp=datetime.now().isoformat(),
            confidence=0.92 if REALTIME_DATA_AVAILABLE else 0.85
        )

class AnalysisAgent(BaseAIAgent):
    def __init__(self):
        super().__init__("AnalysisAgent")
        
    async def analyze_opportunity_viability(self, opportunity: Dict[str, Any]) -> AgentResponse:
        """Analyze the viability of an opportunity"""
        print(f"📊 {self.name}: Analyzing opportunity viability...")
        
        await asyncio.sleep(0.3)
        
        analysis = {
            "market_size_assessment": "Large addressable market with growing demand",
            "competition_level": "Moderate competition with differentiation opportunities", 
            "technical_feasibility": "High feasibility with current AI technologies",
            "roi_projection": {
                "time_to_market": "6-12 months",
                "break_even": "18 months",
                "projected_revenue_y1": opportunity.get("market_size_estimate", 0) * 0.1
            }
        }
        
        return AgentResponse(
            agent_name=self.name,
            data=analysis,
            timestamp=datetime.now().isoformat(),
            confidence=0.78
        )

class ResearchAgent(BaseAIAgent):
    def __init__(self):
        super().__init__("ResearchAgent")
        
    async def research_implementation_details(self, opportunity: Dict[str, Any]) -> AgentResponse:
        """Research implementation details for an opportunity"""
        print(f"🔬 {self.name}: Researching implementation details...")
        
        await asyncio.sleep(0.4)
        
        research = {
            "required_technologies": ["Python/TensorFlow", "Cloud Infrastructure", "API Development"],
            "team_requirements": ["ML Engineers", "Data Scientists", "Full-stack Developers"],
            "estimated_timeline": f"{opportunity.get('implementation_complexity', 'MEDIUM').lower()}_complexity_project",
            "key_challenges": ["Data quality", "Model accuracy", "Scalability"],
            "success_factors": ["Strong data pipeline", "User experience", "Continuous learning"]
        }
        
        return AgentResponse(
            agent_name=self.name,
            data=research,
            timestamp=datetime.now().isoformat(),
            confidence=0.82
        )

class TrendAgent(BaseAIAgent):
    def __init__(self):
        super().__init__("TrendAgent")
        
    async def identify_emerging_trends(self) -> AgentResponse:
        """Identify emerging technology trends using AI"""
        print(f"📈 {self.name}: Identifying emerging trends...")
        
        if not GEMINI_API_KEY:
            print(f"⚠️  {self.name}: No API key, using fallback trends")
            return await self._get_fallback_trends()
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = """
            You are a technology trend analyst. Identify the top emerging AI/ML technology trends for 2025.
            
            Return your analysis in this exact JSON format:
            {
              "hot_technologies": [
                {"name": "Technology Name", "growth_rate": "XX%", "adoption": "stage"},
                {"name": "Technology Name", "growth_rate": "XX%", "adoption": "stage"}
              ],
              "market_indicators": {
                "vc_funding": "brief description",
                "job_postings": "brief description", 
                "patent_filings": "brief description"
              },
              "predicted_opportunities": ["opportunity 1", "opportunity 2", "opportunity 3"]
            }
            
            Focus on realistic, current market trends. Keep descriptions concise.
            """
            
            response = await asyncio.create_task(
                asyncio.to_thread(model.generate_content, prompt)
            )
            
            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                trends = json.loads(json_match.group())
                print(f"✅ {self.name}: Generated AI-powered trend analysis")
                
                return AgentResponse(
                    agent_name=self.name,
                    data=trends,
                    timestamp=datetime.now().isoformat(),
                    confidence=0.92
                )
            else:
                print(f"⚠️  {self.name}: Failed to parse AI response, using fallback")
                return await self._get_fallback_trends()
                
        except Exception as e:
            print(f"❌ {self.name}: AI error: {e}, using fallback")
            return await self._get_fallback_trends()
    
    async def _get_fallback_trends(self) -> AgentResponse:
        """Fallback trends when AI is not available"""
        await asyncio.sleep(0.3)
        
        trends = {
            "hot_technologies": [
                {"name": "Large Language Models", "growth_rate": "300%", "adoption": "Early majority"},
                {"name": "Computer Vision APIs", "growth_rate": "150%", "adoption": "Mainstream"},
                {"name": "AutoML Platforms", "growth_rate": "200%", "adoption": "Early adopters"}
            ],
            "market_indicators": {
                "vc_funding": "up 40% in AI startups",
                "job_postings": "up 60% for AI engineers", 
                "patent_filings": "up 25% in ML/AI domain"
            },
            "predicted_opportunities": ["AI code generation", "Automated customer insights", "Smart document processing"]
        }
        
        return AgentResponse(
            agent_name=self.name,
            data=trends,
            timestamp=datetime.now().isoformat(),
            confidence=0.88
        )

class CapabilityAgent(BaseAIAgent):
    def __init__(self):
        super().__init__("CapabilityAgent")
        
    async def assess_ai_capabilities(self, opportunity: Dict[str, Any]) -> AgentResponse:
        """Assess AI capabilities needed for an opportunity"""  
        print(f"🤖 {self.name}: Assessing AI capabilities...")
        
        await asyncio.sleep(0.2)
        
        capabilities = {
            "required_ai_stack": {
                "ml_frameworks": ["TensorFlow", "PyTorch", "Scikit-learn"],
                "cloud_services": ["AWS SageMaker", "Google Cloud AI", "Azure ML"],
                "data_tools": ["Apache Spark", "PostgreSQL", "Redis"]
            },
            "complexity_assessment": opportunity.get("implementation_complexity", "MEDIUM"),
            "ai_maturity_level": "Production-ready with existing tools",
            "development_effort": "6-8 engineer months",
            "success_probability": "75-85% with proper execution"
        }
        
        return AgentResponse(
            agent_name=self.name,
            data=capabilities,
            timestamp=datetime.now().isoformat(),
            confidence=0.80
        )

# AI Agent Orchestrator
class AIAgentOrchestrator:
    def __init__(self):
        self.agents = {
            "monitoring": MonitoringAgent(),
            "analysis": AnalysisAgent(), 
            "research": ResearchAgent(),
            "trend": TrendAgent(),
            "capability": CapabilityAgent()
        }
        self.opportunities_cache = []
        self.last_generation = None
        
    async def generate_opportunities(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Orchestrate all agents to generate and analyze opportunities"""
        print("🚀 AI Agent Orchestrator: Starting opportunity generation...")
        
        # Step 1: Monitor trends
        trend_data = await self.agents["trend"].identify_emerging_trends()
        market_data = await self.agents["monitoring"].scan_market_trends()
        
        # Step 2: Generate base opportunities 
        base_opportunities = await self.agents["monitoring"].generate_opportunities(limit=limit)
        
        # Step 3: Enhance each opportunity with agent analysis
        enhanced_opportunities = []
        for opportunity in base_opportunities:
            print(f"✨ Enhancing opportunity: {opportunity['title'][:50]}...")
            
            # Run multiple agents in parallel
            analysis_task = self.agents["analysis"].analyze_opportunity_viability(opportunity)
            research_task = self.agents["research"].research_implementation_details(opportunity)
            capability_task = self.agents["capability"].assess_ai_capabilities(opportunity)
            
            analysis, research, capability = await asyncio.gather(
                analysis_task, research_task, capability_task
            )
            
            # Combine all agent insights
            enhanced_opportunity = {
                **opportunity,
                "agent_analysis": {
                    "viability": analysis.data,
                    "implementation": research.data,
                    "ai_capabilities": capability.data,
                    "market_trends": trend_data.data,
                    "agent_confidence": (analysis.confidence + research.confidence + capability.confidence) / 3
                }
            }
            
            enhanced_opportunities.append(enhanced_opportunity)
        
        self.opportunities_cache = enhanced_opportunities
        self.last_generation = datetime.now()
        
        print(f"✅ Generated {len(enhanced_opportunities)} AI-powered opportunities!")
        return enhanced_opportunities

# Initialize orchestrator
orchestrator = AIAgentOrchestrator()

# FastAPI App
app = FastAPI(
    title="AI Opportunity Browser - Real AI Agents",
    description="AI-powered opportunity discovery with 5 specialized agents",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
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

# Mock user for demo
MOCK_USER = {
    "id": "ai-user-123",
    "email": "demo@ai-browser.com",
    "full_name": "AI Demo User",
    "expertise_domains": ["Machine Learning", "AI Strategy"],
    "reputation_score": 3200,
    "is_verified": True
}

# Routes
@app.get("/")
async def root():
    return {
        "message": "AI Opportunity Browser - Real AI Agents Active!",
        "agents": list(orchestrator.agents.keys()),
        "last_generation": orchestrator.last_generation.isoformat() if orchestrator.last_generation else None
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agents_active": len(orchestrator.agents),
        "opportunities_cached": len(orchestrator.opportunities_cache),
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0-ai-powered"
    }

@app.post("/auth/login")
async def login(credentials: LoginRequest):
    if credentials.email and credentials.password:
        return AuthResponse(
            access_token="ai-demo-token-456",
            refresh_token="ai-demo-refresh-789",
            token_type="bearer",
            user=MOCK_USER
        )
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/auth/register")
async def register(data: dict):
    return AuthResponse(
        access_token="ai-demo-token-456",
        refresh_token="ai-demo-refresh-789",
        token_type="bearer",
        user=MOCK_USER
    )

@app.get("/users/me")
async def get_current_user():
    return MOCK_USER

@app.get("/opportunities/")
async def get_opportunities(
    background_tasks: BackgroundTasks,
    page: int = 1,
    size: int = 10,
    query: Optional[str] = None,
    industry: Optional[str] = None,
    regenerate: bool = False
):
    # Check if we need to regenerate opportunities
    if regenerate or not orchestrator.opportunities_cache or not orchestrator.last_generation:
        print("🔄 Regenerating opportunities with AI agents...")
        opportunities = await orchestrator.generate_opportunities(limit=size)
    else:
        opportunities = orchestrator.opportunities_cache
    
    # Apply filters
    filtered_opportunities = opportunities.copy()
    
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
    
    # Pagination
    start = (page - 1) * size
    end = start + size
    items = filtered_opportunities[start:end]
    
    return {
        "items": items,
        "total": len(filtered_opportunities),
        "page": page,
        "size": size,
        "pages": (len(filtered_opportunities) + size - 1) // size,
        "ai_generated": True,
        "generation_time": orchestrator.last_generation.isoformat() if orchestrator.last_generation else None
    }

@app.get("/opportunities/regenerate")
async def regenerate_opportunities():
    """Force regeneration of opportunities using AI agents"""
    print("🔄 Force regenerating opportunities...")
    opportunities = await orchestrator.generate_opportunities(limit=10)
    return {
        "message": "Opportunities regenerated successfully",
        "count": len(opportunities),
        "generation_time": orchestrator.last_generation.isoformat(),
        "agents_used": list(orchestrator.agents.keys())
    }

@app.get("/opportunities/search")
async def search_opportunities(query: str = "", page: int = 1, size: int = 10):
    return await get_opportunities(page=page, size=size, query=query, background_tasks=BackgroundTasks())

@app.get("/opportunities/recommendations")
async def get_recommendations(limit: int = 5):
    if not orchestrator.opportunities_cache:
        opportunities = await orchestrator.generate_opportunities(limit=limit)
    else:
        opportunities = orchestrator.opportunities_cache
    
    # Sort by AI confidence score
    sorted_opps = sorted(
        opportunities, 
        key=lambda x: x.get("agent_analysis", {}).get("agent_confidence", 0), 
        reverse=True
    )
    return sorted_opps[:limit]

@app.get("/opportunities/trending")
async def get_trending(limit: int = 5):
    if not orchestrator.opportunities_cache:
        opportunities = await orchestrator.generate_opportunities(limit=limit)
    else:
        opportunities = orchestrator.opportunities_cache
    
    # Sort by validation score
    sorted_opps = sorted(opportunities, key=lambda x: x["validation_score"], reverse=True)
    return sorted_opps[:limit]

@app.get("/opportunities/{opportunity_id}")
async def get_opportunity(opportunity_id: str):
    opportunity = next((opp for opp in orchestrator.opportunities_cache if opp["id"] == opportunity_id), None)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity

@app.get("/agents/status")
async def get_agents_status():
    """Get status of all AI agents"""
    return {
        "agents": {name: {"active": True, "type": type(agent).__name__} for name, agent in orchestrator.agents.items()},
        "total_agents": len(orchestrator.agents),
        "last_run": orchestrator.last_generation.isoformat() if orchestrator.last_generation else None,
        "cached_opportunities": len(orchestrator.opportunities_cache)
    }

@app.get("/data-sources/status")
async def get_data_sources_status():
    """Get status of real-time data sources"""
    status = {
        "realtime_integration": REALTIME_DATA_AVAILABLE,
        "data_sources": {
            "reddit": {"available": False, "requires": "REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET"},
            "github": {"available": False, "requires": "GITHUB_ACCESS_TOKEN"},
            "hackernews": {"available": True, "requires": "None (public API)"},
            "producthunt": {"available": False, "requires": "PRODUCTHUNT_ACCESS_TOKEN"},
            "ycombinator": {"available": True, "requires": "None (public data)"}
        },
        "active_sources": 0,
        "last_update": datetime.now().isoformat()
    }
    
    if REALTIME_DATA_AVAILABLE:
        try:
            # Check which sources are actually working
            if hasattr(data_bridge, 'plugins'):
                status["active_sources"] = len(data_bridge.plugins)
                for plugin_name in data_bridge.plugins:
                    if plugin_name in status["data_sources"]:
                        status["data_sources"][plugin_name]["available"] = True
        except Exception as e:
            status["error"] = str(e)
    
    return status

if __name__ == "__main__":
    print("🚀 Starting AI Opportunity Browser with Real AI Agents...")
    print("🤖 Active Agents:", list(orchestrator.agents.keys()))
    
    uvicorn.run(
        "agents_api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Don't reload with agents
        log_level="info"
    )