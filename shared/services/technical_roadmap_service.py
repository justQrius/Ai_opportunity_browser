"""
Technical Roadmap Service for AI Opportunity Browser.

Implements Phase 7.2.1 requirements:
- Architecture recommendation engine
- Technology stack suggestions
- Development timeline estimation
- Technical implementation guidance

Provides comprehensive technical roadmaps for AI opportunities including
architecture patterns, technology recommendations, and implementation phases.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import math

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from shared.models.opportunity import Opportunity
from shared.models.market_signal import MarketSignal
from shared.models.ai_capability import AICapabilityAssessment
from shared.services.business_intelligence_service import MarketAnalysisResult

logger = logging.getLogger(__name__)


class ArchitecturePattern(Enum):
    """Recommended architecture patterns for AI solutions."""
    MICROSERVICES = "microservices"
    MONOLITHIC = "monolithic"
    SERVERLESS = "serverless"
    EDGE_COMPUTING = "edge_computing"
    HYBRID_CLOUD = "hybrid_cloud"
    EVENT_DRIVEN = "event_driven"
    PIPELINE_ARCHITECTURE = "pipeline_architecture"


class TechnologyCategory(Enum):
    """Categories of technology recommendations."""
    AI_FRAMEWORK = "ai_framework"
    DATABASE = "database"
    BACKEND_FRAMEWORK = "backend_framework"
    FRONTEND_FRAMEWORK = "frontend_framework"
    CLOUD_PLATFORM = "cloud_platform"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    SECURITY = "security"


class ComplexityLevel(Enum):
    """Technical complexity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ImplementationPhase(Enum):
    """Implementation phases for technical roadmap."""
    RESEARCH_POC = "research_poc"
    MVP_DEVELOPMENT = "mvp_development"
    BETA_TESTING = "beta_testing"
    PRODUCTION_LAUNCH = "production_launch"
    SCALE_OPTIMIZATION = "scale_optimization"


class RoleType(Enum):
    """Types of team roles."""
    AI_ML_ENGINEER = "ai_ml_engineer"
    BACKEND_DEVELOPER = "backend_developer"
    FRONTEND_DEVELOPER = "frontend_developer"
    DATA_ENGINEER = "data_engineer"
    DATA_SCIENTIST = "data_scientist"
    DEVOPS_ENGINEER = "devops_engineer"
    PRODUCT_MANAGER = "product_manager"
    UI_UX_DESIGNER = "ui_ux_designer"
    QA_ENGINEER = "qa_engineer"
    SECURITY_ENGINEER = "security_engineer"
    TECHNICAL_LEAD = "technical_lead"
    RESEARCH_SCIENTIST = "research_scientist"


class ExperienceLevel(Enum):
    """Experience levels for team members."""
    JUNIOR = "junior"
    MID_LEVEL = "mid_level"
    SENIOR = "senior"
    EXPERT = "expert"


class CommitmentType(Enum):
    """Time commitment types."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONSULTANT = "consultant"
    CONTRACTOR = "contractor"


@dataclass
class SkillRequirement:
    """Individual skill requirement."""
    skill_name: str
    importance: str  # critical, important, nice_to_have
    proficiency_level: str  # basic, intermediate, advanced, expert
    alternatives: List[str]
    learning_resources: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TeamRoleRecommendation:
    """Team role recommendation with detailed requirements."""
    role_type: RoleType
    role_title: str
    description: str
    required_skills: List[SkillRequirement]
    experience_level: ExperienceLevel
    commitment_type: CommitmentType
    estimated_hours_per_week: int
    phases_involved: List[ImplementationPhase]
    salary_range: Dict[str, float]  # min, max, currency
    alternatives: List[str]
    justification: str
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['role_type'] = self.role_type.value
        result['experience_level'] = self.experience_level.value
        result['commitment_type'] = self.commitment_type.value
        result['phases_involved'] = [phase.value for phase in self.phases_involved]
        result['required_skills'] = [skill.to_dict() for skill in self.required_skills]
        return result


@dataclass
class TeamCompositionAnalysis:
    """Comprehensive team composition analysis."""
    analysis_id: str
    opportunity_id: str
    generated_at: datetime
    recommended_roles: List[TeamRoleRecommendation]
    total_team_size: int
    team_structure: Dict[str, Any]
    skill_matrix: Dict[str, List[str]]
    hiring_timeline: Dict[str, Any]
    budget_implications: Dict[str, Any]
    scaling_recommendations: List[str]
    risk_mitigation: List[Dict[str, Any]]
    alternative_compositions: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['generated_at'] = self.generated_at.isoformat()
        result['recommended_roles'] = [role.to_dict() for role in self.recommended_roles]
        return result


@dataclass
class TechnologyRecommendation:
    """Individual technology recommendation."""
    name: str
    category: TechnologyCategory
    description: str
    reasoning: str
    complexity: ComplexityLevel
    learning_curve: str  # low, medium, high
    community_support: str  # poor, good, excellent
    license_type: str  # open_source, commercial, hybrid
    alternatives: List[str]
    integration_effort: str  # minimal, moderate, significant
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['category'] = self.category.value
        result['complexity'] = self.complexity.value
        return result


@dataclass
class ArchitectureRecommendation:
    """Architecture pattern recommendation."""
    pattern: ArchitecturePattern
    description: str
    advantages: List[str]
    disadvantages: List[str]
    best_use_cases: List[str]
    complexity: ComplexityLevel
    scalability_rating: int  # 1-10
    development_speed_rating: int  # 1-10
    maintenance_rating: int  # 1-10
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['pattern'] = self.pattern.value
        result['complexity'] = self.complexity.value
        return result


@dataclass
class ImplementationPhaseDetail:
    """Detailed implementation phase information."""
    phase: ImplementationPhase
    name: str
    description: str
    duration_weeks: int
    key_deliverables: List[str]
    required_skills: List[str]
    technologies_introduced: List[str]
    success_criteria: List[str]
    risks: List[str]
    dependencies: List[str]
    estimated_effort_hours: int
    team_size_recommendation: int
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['phase'] = self.phase.value
        return result


@dataclass
class TechnicalRoadmap:
    """Comprehensive technical roadmap."""
    roadmap_id: str
    opportunity_id: str
    generated_at: datetime
    architecture_recommendation: ArchitectureRecommendation
    technology_stack: List[TechnologyRecommendation]
    implementation_phases: List[ImplementationPhaseDetail]
    overall_complexity: ComplexityLevel
    estimated_timeline_weeks: int
    total_estimated_hours: int
    recommended_team_size: int
    team_composition_analysis: TeamCompositionAnalysis
    key_technical_risks: List[Dict[str, Any]]
    infrastructure_requirements: Dict[str, Any]
    performance_targets: Dict[str, Any]
    security_considerations: List[str]
    scalability_plan: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['generated_at'] = self.generated_at.isoformat()
        result['overall_complexity'] = self.overall_complexity.value
        result['architecture_recommendation'] = self.architecture_recommendation.to_dict()
        result['technology_stack'] = [tech.to_dict() for tech in self.technology_stack]
        result['implementation_phases'] = [phase.to_dict() for phase in self.implementation_phases]
        result['team_composition_analysis'] = self.team_composition_analysis.to_dict()
        return result


class TechnicalRoadmapService:
    """Service for generating technical roadmaps and architecture recommendations."""
    
    def __init__(self):
        self.technology_database = self._initialize_technology_database()
        self.architecture_patterns = self._initialize_architecture_patterns()
    
    async def generate_technical_roadmap(
        self,
        db: AsyncSession,
        opportunity: Opportunity,
        market_analysis: Optional[MarketAnalysisResult] = None
    ) -> TechnicalRoadmap:
        """Generate comprehensive technical roadmap for an opportunity.
        
        Args:
            db: Database session
            opportunity: Target opportunity
            market_analysis: Market analysis results for context
            
        Returns:
            TechnicalRoadmap with complete implementation guidance
        """
        logger.info(f"Generating technical roadmap for opportunity {opportunity.id}")
        
        # Analyze opportunity requirements
        ai_requirements = await self._analyze_ai_requirements(opportunity)
        technical_complexity = await self._assess_technical_complexity(opportunity, ai_requirements)
        
        # Generate architecture recommendation
        architecture = await self._recommend_architecture(
            opportunity, ai_requirements, technical_complexity, market_analysis
        )
        
        # Generate technology stack recommendations
        tech_stack = await self._recommend_technology_stack(
            opportunity, ai_requirements, architecture, technical_complexity
        )
        
        # Create implementation phases
        phases = await self._create_implementation_phases(
            opportunity, architecture, tech_stack, technical_complexity
        )
        
        # Calculate timeline and effort estimates
        timeline_weeks = sum(phase.duration_weeks for phase in phases)
        total_hours = sum(phase.estimated_effort_hours for phase in phases)
        team_size = await self._recommend_team_size(technical_complexity, total_hours, timeline_weeks)
        
        # Generate team composition analysis
        team_composition = await self._analyze_team_composition(
            opportunity, architecture, tech_stack, phases, technical_complexity, timeline_weeks, total_hours
        )
        
        # Identify technical risks
        risks = await self._identify_technical_risks(opportunity, architecture, tech_stack)
        
        # Generate infrastructure and performance requirements
        infrastructure = await self._define_infrastructure_requirements(
            opportunity, architecture, tech_stack, market_analysis
        )
        performance_targets = await self._define_performance_targets(opportunity, market_analysis)
        
        # Security and scalability considerations
        security = await self._define_security_considerations(opportunity, tech_stack)
        scalability = await self._create_scalability_plan(opportunity, architecture, market_analysis)
        
        return TechnicalRoadmap(
            roadmap_id=f"roadmap_{opportunity.id}",
            opportunity_id=str(opportunity.id),
            generated_at=datetime.utcnow(),
            architecture_recommendation=architecture,
            technology_stack=tech_stack,
            implementation_phases=phases,
            overall_complexity=technical_complexity,
            estimated_timeline_weeks=timeline_weeks,
            total_estimated_hours=total_hours,
            recommended_team_size=team_size,
            team_composition_analysis=team_composition,
            key_technical_risks=risks,
            infrastructure_requirements=infrastructure,
            performance_targets=performance_targets,
            security_considerations=security,
            scalability_plan=scalability
        )
    
    async def _analyze_ai_requirements(self, opportunity: Opportunity) -> Dict[str, Any]:
        """Analyze AI-specific requirements from opportunity."""
        requirements = {
            "ai_types": [],
            "capabilities": [],
            "data_requirements": [],
            "performance_needs": [],
            "integration_requirements": []
        }
        
        # Parse AI solution types
        if opportunity.ai_solution_types:
            try:
                ai_types = json.loads(opportunity.ai_solution_types) if isinstance(opportunity.ai_solution_types, str) else opportunity.ai_solution_types
                requirements["ai_types"] = ai_types
            except:
                pass
        
        # Parse required capabilities
        if opportunity.required_capabilities:
            try:
                capabilities = json.loads(opportunity.required_capabilities) if isinstance(opportunity.required_capabilities, str) else opportunity.required_capabilities
                requirements["capabilities"] = capabilities
            except:
                pass
        
        # Infer data requirements from AI types and description
        for ai_type in requirements["ai_types"]:
            ai_type_lower = str(ai_type).lower()
            if "nlp" in ai_type_lower or "language" in ai_type_lower:
                requirements["data_requirements"].extend(["text_corpus", "tokenization", "embeddings"])
            if "computer_vision" in ai_type_lower or "vision" in ai_type_lower:
                requirements["data_requirements"].extend(["image_datasets", "annotation_tools", "gpu_processing"])
            if "machine_learning" in ai_type_lower:
                requirements["data_requirements"].extend(["training_data", "feature_engineering", "model_storage"])
            if "recommendation" in ai_type_lower:
                requirements["data_requirements"].extend(["user_behavior_data", "collaborative_filtering", "real_time_inference"])
        
        # Infer performance needs
        if opportunity.description:
            description_lower = opportunity.description.lower()
            if any(word in description_lower for word in ["real-time", "instant", "fast", "immediate"]):
                requirements["performance_needs"].append("low_latency")
            if any(word in description_lower for word in ["scale", "volume", "large", "big"]):
                requirements["performance_needs"].append("high_throughput")
            if any(word in description_lower for word in ["accurate", "precision", "quality"]):
                requirements["performance_needs"].append("high_accuracy")
        
        # Infer integration requirements
        if opportunity.target_industries:
            try:
                industries = json.loads(opportunity.target_industries) if isinstance(opportunity.target_industries, str) else opportunity.target_industries
                for industry in industries:
                    industry_lower = industry.lower()
                    if industry_lower in ["finance", "banking"]:
                        requirements["integration_requirements"].extend(["regulatory_compliance", "audit_trails", "encryption"])
                    elif industry_lower in ["healthcare", "medical"]:
                        requirements["integration_requirements"].extend(["hipaa_compliance", "hl7_integration", "data_privacy"])
                    elif industry_lower in ["retail", "ecommerce"]:
                        requirements["integration_requirements"].extend(["payment_processing", "inventory_systems", "crm_integration"])
            except:
                pass
        
        return requirements
    
    async def _assess_technical_complexity(self, opportunity: Opportunity, ai_requirements: Dict[str, Any]) -> ComplexityLevel:
        """Assess overall technical complexity of the opportunity."""
        complexity_score = 0
        
        # AI types complexity
        ai_types = ai_requirements.get("ai_types", [])
        complexity_score += len(ai_types) * 2  # 2 points per AI type
        
        # Advanced AI capabilities
        capabilities = ai_requirements.get("capabilities", [])
        advanced_capabilities = ["transformer", "gpt", "bert", "reinforcement_learning", "generative_ai", "neural_networks"]
        for cap in capabilities:
            if any(advanced in str(cap).lower() for advanced in advanced_capabilities):
                complexity_score += 3
        
        # Performance requirements
        performance_needs = ai_requirements.get("performance_needs", [])
        if "low_latency" in performance_needs:
            complexity_score += 4
        if "high_throughput" in performance_needs:
            complexity_score += 3
        if "high_accuracy" in performance_needs:
            complexity_score += 2
        
        # Integration complexity
        integration_reqs = ai_requirements.get("integration_requirements", [])
        complexity_score += len(integration_reqs) * 2
        
        # Industry-specific complexity
        if opportunity.target_industries:
            try:
                industries = json.loads(opportunity.target_industries) if isinstance(opportunity.target_industries, str) else opportunity.target_industries
                regulated_industries = ["finance", "healthcare", "legal", "government"]
                for industry in industries:
                    if industry.lower() in regulated_industries:
                        complexity_score += 5
                        break
            except:
                pass
        
        # Determine complexity level
        if complexity_score >= 25:
            return ComplexityLevel.VERY_HIGH
        elif complexity_score >= 15:
            return ComplexityLevel.HIGH
        elif complexity_score >= 8:
            return ComplexityLevel.MEDIUM
        else:
            return ComplexityLevel.LOW
    
    async def _recommend_architecture(
        self,
        opportunity: Opportunity,
        ai_requirements: Dict[str, Any],
        complexity: ComplexityLevel,
        market_analysis: Optional[MarketAnalysisResult]
    ) -> ArchitectureRecommendation:
        """Recommend architecture pattern based on requirements."""
        
        ai_types = ai_requirements.get("ai_types", [])
        performance_needs = ai_requirements.get("performance_needs", [])
        
        # Analyze requirements to determine best architecture
        if "low_latency" in performance_needs and len(ai_types) == 1:
            # Single AI type with low latency needs - edge computing
            pattern = ArchitecturePattern.EDGE_COMPUTING
            description = "Edge computing architecture for low-latency AI processing"
            advantages = [
                "Minimal network latency",
                "Reduced bandwidth usage",
                "Better privacy and security",
                "Offline capability"
            ]
            disadvantages = [
                "Limited computational resources",
                "Complex deployment and updates",
                "Hardware dependency"
            ]
            best_use_cases = [
                "Real-time image processing",
                "IoT sensor data analysis",
                "Autonomous systems"
            ]
            
        elif len(ai_types) > 2 or complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]:
            # Complex multi-AI solution - microservices
            pattern = ArchitecturePattern.MICROSERVICES
            description = "Microservices architecture for scalable multi-AI platform"
            advantages = [
                "Independent scaling of AI components",
                "Technology diversity support",
                "Fault isolation",
                "Team autonomy"
            ]
            disadvantages = [
                "Increased operational complexity",
                "Network overhead",
                "Distributed system challenges"
            ]
            best_use_cases = [
                "Multi-modal AI platforms",
                "Enterprise AI solutions",
                "High-scale applications"
            ]
            
        elif "high_throughput" in performance_needs:
            # High throughput needs - pipeline architecture
            pattern = ArchitecturePattern.PIPELINE_ARCHITECTURE
            description = "AI pipeline architecture for high-throughput data processing"
            advantages = [
                "Optimized for batch processing",
                "High throughput capabilities",
                "Clear data flow",
                "Easy monitoring"
            ]
            disadvantages = [
                "Less flexibility for real-time changes",
                "Potential bottlenecks",
                "Complex error handling"
            ]
            best_use_cases = [
                "Batch data processing",
                "ETL with AI transformations",
                "Large-scale analytics"
            ]
            
        elif complexity == ComplexityLevel.LOW:
            # Simple solution - monolithic
            pattern = ArchitecturePattern.MONOLITHIC
            description = "Monolithic architecture for simple AI application"
            advantages = [
                "Simple deployment",
                "Easy development and testing",
                "Lower operational overhead",
                "Better performance for small scale"
            ]
            disadvantages = [
                "Limited scalability",
                "Technology lock-in",
                "Deployment coupling"
            ]
            best_use_cases = [
                "Single-purpose AI tools",
                "Prototype applications",
                "Small team projects"
            ]
            
        else:
            # Default to serverless for moderate complexity
            pattern = ArchitecturePattern.SERVERLESS
            description = "Serverless architecture for cost-effective AI deployment"
            advantages = [
                "Auto-scaling",
                "Pay-per-use pricing",
                "Reduced operational overhead",
                "Fast deployment"
            ]
            disadvantages = [
                "Cold start latency",
                "Vendor lock-in",
                "Limited control over infrastructure"
            ]
            best_use_cases = [
                "Event-driven AI processing",
                "Variable workload patterns",
                "Cost-sensitive applications"
            ]
        
        # Calculate ratings based on pattern
        ratings = self._calculate_architecture_ratings(pattern, complexity, performance_needs)
        
        return ArchitectureRecommendation(
            pattern=pattern,
            description=description,
            advantages=advantages,
            disadvantages=disadvantages,
            best_use_cases=best_use_cases,
            complexity=complexity,
            scalability_rating=ratings["scalability"],
            development_speed_rating=ratings["development_speed"],
            maintenance_rating=ratings["maintenance"]
        )
    
    def _calculate_architecture_ratings(self, pattern: ArchitecturePattern, complexity: ComplexityLevel, performance_needs: List[str]) -> Dict[str, int]:
        """Calculate architecture ratings (1-10 scale)."""
        ratings = {
            ArchitecturePattern.MICROSERVICES: {"scalability": 9, "development_speed": 6, "maintenance": 5},
            ArchitecturePattern.MONOLITHIC: {"scalability": 4, "development_speed": 8, "maintenance": 7},
            ArchitecturePattern.SERVERLESS: {"scalability": 8, "development_speed": 9, "maintenance": 8},
            ArchitecturePattern.EDGE_COMPUTING: {"scalability": 6, "development_speed": 5, "maintenance": 6},
            ArchitecturePattern.PIPELINE_ARCHITECTURE: {"scalability": 7, "development_speed": 7, "maintenance": 7},
            ArchitecturePattern.EVENT_DRIVEN: {"scalability": 8, "development_speed": 6, "maintenance": 6},
            ArchitecturePattern.HYBRID_CLOUD: {"scalability": 8, "development_speed": 5, "maintenance": 5}
        }
        
        return ratings.get(pattern, {"scalability": 7, "development_speed": 7, "maintenance": 7})
    
    async def _recommend_technology_stack(
        self,
        opportunity: Opportunity,
        ai_requirements: Dict[str, Any],
        architecture: ArchitectureRecommendation,
        complexity: ComplexityLevel
    ) -> List[TechnologyRecommendation]:
        """Recommend technology stack based on requirements."""
        recommendations = []
        
        ai_types = ai_requirements.get("ai_types", [])
        capabilities = ai_requirements.get("capabilities", [])
        
        # AI Framework recommendations
        ai_framework = self._recommend_ai_framework(ai_types, capabilities, complexity)
        recommendations.append(ai_framework)
        
        # Backend framework
        backend_framework = self._recommend_backend_framework(architecture.pattern, complexity)
        recommendations.append(backend_framework)
        
        # Database recommendations
        database_recs = self._recommend_databases(ai_requirements, architecture.pattern)
        recommendations.extend(database_recs)
        
        # Cloud platform
        cloud_platform = self._recommend_cloud_platform(architecture.pattern, complexity)
        recommendations.append(cloud_platform)
        
        # Frontend framework (if needed)
        if self._needs_frontend(opportunity):
            frontend_framework = self._recommend_frontend_framework(complexity)
            recommendations.append(frontend_framework)
        
        # Deployment and DevOps
        deployment_tools = self._recommend_deployment_tools(architecture.pattern, complexity)
        recommendations.extend(deployment_tools)
        
        # Monitoring and observability
        monitoring_tools = self._recommend_monitoring_tools(architecture.pattern, complexity)
        recommendations.extend(monitoring_tools)
        
        # Security tools
        security_tools = self._recommend_security_tools(ai_requirements, complexity)
        recommendations.extend(security_tools)
        
        return recommendations
    
    def _recommend_ai_framework(self, ai_types: List[str], capabilities: List[str], complexity: ComplexityLevel) -> TechnologyRecommendation:
        """Recommend AI/ML framework."""
        
        # Analyze AI types to determine best framework
        has_nlp = any("nlp" in str(ai_type).lower() or "language" in str(ai_type).lower() for ai_type in ai_types)
        has_cv = any("vision" in str(ai_type).lower() or "image" in str(ai_type).lower() for ai_type in ai_types)
        has_advanced = any(adv in str(capabilities).lower() for adv in ["transformer", "gpt", "bert", "neural"])
        
        if has_advanced or complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]:
            return TechnologyRecommendation(
                name="PyTorch + Transformers",
                category=TechnologyCategory.AI_FRAMEWORK,
                description="Advanced deep learning framework with state-of-the-art transformer models",
                reasoning="Best support for cutting-edge AI models and research-grade implementations",
                complexity=ComplexityLevel.HIGH,
                learning_curve="high",
                community_support="excellent",
                license_type="open_source",
                alternatives=["TensorFlow", "JAX", "Hugging Face Transformers"],
                integration_effort="moderate"
            )
        elif has_nlp and has_cv:
            return TechnologyRecommendation(
                name="TensorFlow",
                category=TechnologyCategory.AI_FRAMEWORK,
                description="Comprehensive ML platform supporting multiple AI modalities",
                reasoning="Strong support for both NLP and computer vision with good production tools",
                complexity=ComplexityLevel.MEDIUM,
                learning_curve="medium",
                community_support="excellent",
                license_type="open_source",
                alternatives=["PyTorch", "Keras", "Scikit-learn"],
                integration_effort="moderate"
            )
        elif complexity == ComplexityLevel.LOW:
            return TechnologyRecommendation(
                name="Scikit-learn + OpenAI API",
                category=TechnologyCategory.AI_FRAMEWORK,
                description="Simple ML library combined with cloud AI services",
                reasoning="Low complexity solution with pre-built AI capabilities via APIs",
                complexity=ComplexityLevel.LOW,
                learning_curve="low",
                community_support="excellent",
                license_type="hybrid",
                alternatives=["Azure Cognitive Services", "Google AI Platform", "AWS AI Services"],
                integration_effort="minimal"
            )
        else:
            return TechnologyRecommendation(
                name="Hugging Face Transformers",
                category=TechnologyCategory.AI_FRAMEWORK,
                description="Pre-trained transformer models with easy deployment",
                reasoning="Balance of advanced capabilities with ease of use",
                complexity=ComplexityLevel.MEDIUM,
                learning_curve="medium",
                community_support="excellent",
                license_type="open_source",
                alternatives=["OpenAI API", "Cohere API", "Custom PyTorch models"],
                integration_effort="moderate"
            )
    
    def _recommend_backend_framework(self, pattern: ArchitecturePattern, complexity: ComplexityLevel) -> TechnologyRecommendation:
        """Recommend backend framework."""
        
        if pattern == ArchitecturePattern.SERVERLESS:
            return TechnologyRecommendation(
                name="FastAPI + AWS Lambda",
                category=TechnologyCategory.BACKEND_FRAMEWORK,
                description="High-performance async API framework optimized for serverless",
                reasoning="Excellent performance with automatic documentation and async support",
                complexity=ComplexityLevel.MEDIUM,
                learning_curve="medium",
                community_support="excellent",
                license_type="open_source",
                alternatives=["Flask + Serverless", "Node.js + Express", "Django"],
                integration_effort="moderate"
            )
        elif pattern == ArchitecturePattern.MICROSERVICES:
            return TechnologyRecommendation(
                name="FastAPI + Docker + Kubernetes",
                category=TechnologyCategory.BACKEND_FRAMEWORK,
                description="Microservices-ready API framework with container orchestration",
                reasoning="Native async support, automatic API docs, and excellent containerization",
                complexity=ComplexityLevel.HIGH,
                learning_curve="high",
                community_support="excellent",
                license_type="open_source",
                alternatives=["Spring Boot", "Node.js + Express", "Django REST"],
                integration_effort="significant"
            )
        else:
            return TechnologyRecommendation(
                name="FastAPI",
                category=TechnologyCategory.BACKEND_FRAMEWORK,
                description="Modern, fast web framework for building APIs with Python",
                reasoning="High performance, automatic documentation, and excellent AI/ML library integration",
                complexity=ComplexityLevel.MEDIUM,
                learning_curve="medium",
                community_support="excellent",
                license_type="open_source",
                alternatives=["Django REST Framework", "Flask", "Express.js"],
                integration_effort="moderate"
            )
    
    def _recommend_databases(self, ai_requirements: Dict[str, Any], pattern: ArchitecturePattern) -> List[TechnologyRecommendation]:
        """Recommend database technologies."""
        recommendations = []
        
        # Primary database
        if pattern == ArchitecturePattern.SERVERLESS:
            recommendations.append(TechnologyRecommendation(
                name="Amazon DynamoDB",
                category=TechnologyCategory.DATABASE,
                description="Serverless NoSQL database with auto-scaling",
                reasoning="Perfect for serverless architectures with predictable performance",
                complexity=ComplexityLevel.LOW,
                learning_curve="low",
                community_support="good",
                license_type="commercial",
                alternatives=["MongoDB Atlas", "FaunaDB", "PostgreSQL"],
                integration_effort="minimal"
            ))
        else:
            recommendations.append(TechnologyRecommendation(
                name="PostgreSQL",
                category=TechnologyCategory.DATABASE,
                description="Advanced open-source relational database with JSON support",
                reasoning="Excellent for complex queries, ACID compliance, and structured AI metadata",
                complexity=ComplexityLevel.MEDIUM,
                learning_curve="medium",
                community_support="excellent",
                license_type="open_source",
                alternatives=["MySQL", "MongoDB", "CockroachDB"],
                integration_effort="moderate"
            ))
        
        # Vector database for AI embeddings
        data_requirements = ai_requirements.get("data_requirements", [])
        if "embeddings" in data_requirements or any("nlp" in str(ai_type).lower() for ai_type in ai_requirements.get("ai_types", [])):
            recommendations.append(TechnologyRecommendation(
                name="Pinecone",
                category=TechnologyCategory.DATABASE,
                description="Managed vector database for AI embeddings and similarity search",
                reasoning="Optimized for AI workloads with excellent performance and scalability",
                complexity=ComplexityLevel.LOW,
                learning_curve="low",
                community_support="good",
                license_type="commercial",
                alternatives=["Weaviate", "Qdrant", "ChromaDB"],
                integration_effort="minimal"
            ))
        
        # Cache/session store
        recommendations.append(TechnologyRecommendation(
            name="Redis",
            category=TechnologyCategory.DATABASE,
            description="In-memory data store for caching and session management",
            reasoning="Essential for high-performance AI applications requiring fast data access",
            complexity=ComplexityLevel.LOW,
            learning_curve="low",
            community_support="excellent",
            license_type="open_source",
            alternatives=["Memcached", "Amazon ElastiCache", "Hazelcast"],
            integration_effort="minimal"
        ))
        
        return recommendations
    
    def _recommend_cloud_platform(self, pattern: ArchitecturePattern, complexity: ComplexityLevel) -> TechnologyRecommendation:
        """Recommend cloud platform."""
        
        if pattern == ArchitecturePattern.SERVERLESS:
            return TechnologyRecommendation(
                name="AWS",
                category=TechnologyCategory.CLOUD_PLATFORM,
                description="Comprehensive cloud platform with extensive serverless offerings",
                reasoning="Best-in-class serverless ecosystem with Lambda, API Gateway, and AI services",
                complexity=ComplexityLevel.MEDIUM,
                learning_curve="medium",
                community_support="excellent",
                license_type="commercial",
                alternatives=["Google Cloud Platform", "Azure", "Vercel"],
                integration_effort="moderate"
            )
        elif complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]:
            return TechnologyRecommendation(
                name="Google Cloud Platform",
                category=TechnologyCategory.CLOUD_PLATFORM,
                description="AI-first cloud platform with advanced ML and data services",
                reasoning="Leading AI/ML services, excellent Kubernetes support, and competitive GPU pricing",
                complexity=ComplexityLevel.HIGH,
                learning_curve="high",
                community_support="excellent",
                license_type="commercial",
                alternatives=["AWS", "Azure", "IBM Cloud"],
                integration_effort="significant"
            )
        else:
            return TechnologyRecommendation(
                name="Azure",
                category=TechnologyCategory.CLOUD_PLATFORM,
                description="Microsoft's cloud platform with strong enterprise integration",
                reasoning="Good balance of AI services, enterprise features, and development tools",
                complexity=ComplexityLevel.MEDIUM,
                learning_curve="medium",
                community_support="excellent",
                license_type="commercial",
                alternatives=["AWS", "Google Cloud", "DigitalOcean"],
                integration_effort="moderate"
            )
    
    def _needs_frontend(self, opportunity: Opportunity) -> bool:
        """Determine if opportunity needs frontend framework."""
        if opportunity.description:
            description_lower = opportunity.description.lower()
            ui_indicators = ["dashboard", "interface", "ui", "user", "frontend", "web app", "application"]
            return any(indicator in description_lower for indicator in ui_indicators)
        return True  # Default to needing frontend
    
    def _recommend_frontend_framework(self, complexity: ComplexityLevel) -> TechnologyRecommendation:
        """Recommend frontend framework."""
        
        if complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]:
            return TechnologyRecommendation(
                name="React + TypeScript",
                category=TechnologyCategory.FRONTEND_FRAMEWORK,
                description="Component-based UI library with strong typing for complex applications",
                reasoning="Excellent for complex AI dashboards with real-time data visualization",
                complexity=ComplexityLevel.HIGH,
                learning_curve="high",
                community_support="excellent",
                license_type="open_source",
                alternatives=["Vue.js", "Angular", "Svelte"],
                integration_effort="significant"
            )
        else:
            return TechnologyRecommendation(
                name="Next.js",
                category=TechnologyCategory.FRONTEND_FRAMEWORK,
                description="Full-stack React framework with built-in optimization",
                reasoning="Great developer experience with SSR, API routes, and deployment optimization",
                complexity=ComplexityLevel.MEDIUM,
                learning_curve="medium",
                community_support="excellent",
                license_type="open_source",
                alternatives=["React + Vite", "Vue.js + Nuxt", "Streamlit"],
                integration_effort="moderate"
            )
    
    def _recommend_deployment_tools(self, pattern: ArchitecturePattern, complexity: ComplexityLevel) -> List[TechnologyRecommendation]:
        """Recommend deployment and DevOps tools."""
        recommendations = []
        
        if pattern == ArchitecturePattern.SERVERLESS:
            recommendations.append(TechnologyRecommendation(
                name="Serverless Framework",
                category=TechnologyCategory.DEPLOYMENT,
                description="Framework for deploying serverless applications across cloud providers",
                reasoning="Simplifies serverless deployment with infrastructure as code",
                complexity=ComplexityLevel.LOW,
                learning_curve="low",
                community_support="excellent",
                license_type="open_source",
                alternatives=["AWS SAM", "Terraform", "CDK"],
                integration_effort="minimal"
            ))
        elif pattern == ArchitecturePattern.MICROSERVICES:
            recommendations.extend([
                TechnologyRecommendation(
                    name="Docker",
                    category=TechnologyCategory.DEPLOYMENT,
                    description="Containerization platform for consistent deployment environments",
                    reasoning="Essential for microservices architecture and consistent environments",
                    complexity=ComplexityLevel.MEDIUM,
                    learning_curve="medium",
                    community_support="excellent",
                    license_type="open_source",
                    alternatives=["Podman", "containerd", "LXC"],
                    integration_effort="moderate"
                ),
                TechnologyRecommendation(
                    name="Kubernetes",
                    category=TechnologyCategory.DEPLOYMENT,
                    description="Container orchestration platform for managing microservices",
                    reasoning="Industry standard for microservices deployment and scaling",
                    complexity=ComplexityLevel.VERY_HIGH,
                    learning_curve="high",
                    community_support="excellent",
                    license_type="open_source",
                    alternatives=["Docker Swarm", "Amazon ECS", "HashiCorp Nomad"],
                    integration_effort="significant"
                )
            ])
        else:
            recommendations.append(TechnologyRecommendation(
                name="GitHub Actions",
                category=TechnologyCategory.DEPLOYMENT,
                description="CI/CD platform integrated with GitHub for automated deployments",
                reasoning="Simple, integrated CI/CD solution for standard deployment workflows",
                complexity=ComplexityLevel.LOW,
                learning_curve="low",
                community_support="excellent",
                license_type="commercial",
                alternatives=["GitLab CI", "CircleCI", "Jenkins"],
                integration_effort="minimal"
            ))
        
        return recommendations
    
    def _recommend_monitoring_tools(self, pattern: ArchitecturePattern, complexity: ComplexityLevel) -> List[TechnologyRecommendation]:
        """Recommend monitoring and observability tools."""
        recommendations = []
        
        if complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]:
            recommendations.extend([
                TechnologyRecommendation(
                    name="Prometheus + Grafana",
                    category=TechnologyCategory.MONITORING,
                    description="Time-series monitoring with advanced visualization dashboards",
                    reasoning="Comprehensive monitoring solution with excellent AI metrics visualization",
                    complexity=ComplexityLevel.HIGH,
                    learning_curve="high",
                    community_support="excellent",
                    license_type="open_source",
                    alternatives=["DataDog", "New Relic", "CloudWatch"],
                    integration_effort="significant"
                ),
                TechnologyRecommendation(
                    name="Jaeger",
                    category=TechnologyCategory.MONITORING,
                    description="Distributed tracing system for microservices observability",
                    reasoning="Essential for debugging complex AI pipelines and microservices",
                    complexity=ComplexityLevel.HIGH,
                    learning_curve="medium",
                    community_support="good",
                    license_type="open_source",
                    alternatives=["Zipkin", "AWS X-Ray", "Honeycomb"],
                    integration_effort="moderate"
                )
            ])
        else:
            recommendations.append(TechnologyRecommendation(
                name="Application Insights",
                category=TechnologyCategory.MONITORING,
                description="Application performance monitoring with AI-powered insights",
                reasoning="Simple setup with AI-powered anomaly detection and performance insights",
                complexity=ComplexityLevel.LOW,
                learning_curve="low",
                community_support="good",
                license_type="commercial",
                alternatives=["CloudWatch", "DataDog", "New Relic"],
                integration_effort="minimal"
            ))
        
        return recommendations
    
    def _recommend_security_tools(self, ai_requirements: Dict[str, Any], complexity: ComplexityLevel) -> List[TechnologyRecommendation]:
        """Recommend security tools."""
        recommendations = []
        
        integration_reqs = ai_requirements.get("integration_requirements", [])
        
        # Always recommend basic security
        recommendations.append(TechnologyRecommendation(
            name="OAuth 2.0 + JWT",
            category=TechnologyCategory.SECURITY,
            description="Industry-standard authentication and authorization framework",
            reasoning="Secure, scalable authentication suitable for AI applications",
            complexity=ComplexityLevel.MEDIUM,
            learning_curve="medium",
            community_support="excellent",
            license_type="open_source",
            alternatives=["Auth0", "Firebase Auth", "AWS Cognito"],
            integration_effort="moderate"
        ))
        
        # Enhanced security for regulated industries
        if any(req in integration_reqs for req in ["regulatory_compliance", "hipaa_compliance", "encryption"]):
            recommendations.append(TechnologyRecommendation(
                name="HashiCorp Vault",
                category=TechnologyCategory.SECURITY,
                description="Secrets management and data protection platform",
                reasoning="Enterprise-grade secrets management required for regulatory compliance",
                complexity=ComplexityLevel.HIGH,
                learning_curve="high",
                community_support="excellent",
                license_type="open_source",
                alternatives=["AWS Secrets Manager", "Azure Key Vault", "CyberArk"],
                integration_effort="significant"
            ))
        
        return recommendations
    
    # Implementation phase methods
    async def _create_implementation_phases(
        self,
        opportunity: Opportunity,
        architecture: ArchitectureRecommendation,
        tech_stack: List[TechnologyRecommendation],
        complexity: ComplexityLevel
    ) -> List[ImplementationPhaseDetail]:
        """Create detailed implementation phases."""
        phases = []
        
        # Phase 1: Research and POC
        phases.append(ImplementationPhaseDetail(
            phase=ImplementationPhase.RESEARCH_POC,
            name="Research and Proof of Concept",
            description="Technology research, architecture design, and initial prototype development",
            duration_weeks=3 if complexity == ComplexityLevel.LOW else 6 if complexity == ComplexityLevel.MEDIUM else 8,
            key_deliverables=[
                "Technical architecture document",
                "Technology stack validation",
                "Core AI model prototype",
                "Data pipeline proof of concept",
                "Performance benchmarks"
            ],
            required_skills=[
                "AI/ML expertise",
                "Architecture design",
                "Prototype development",
                "Performance testing"
            ],
            technologies_introduced=[tech.name for tech in tech_stack[:3]],  # Core technologies
            success_criteria=[
                "Architecture approved by stakeholders",
                "AI model achieves target accuracy metrics",
                "Performance meets initial requirements",
                "Technical feasibility confirmed"
            ],
            risks=[
                "Technology selection may prove inadequate",
                "AI model performance below expectations",
                "Integration complexity underestimated"
            ],
            dependencies=["Requirements finalization", "Team formation"],
            estimated_effort_hours=320 if complexity == ComplexityLevel.LOW else 480 if complexity == ComplexityLevel.MEDIUM else 640,
            team_size_recommendation=2 if complexity == ComplexityLevel.LOW else 3
        ))
        
        # Phase 2: MVP Development
        phases.append(ImplementationPhaseDetail(
            phase=ImplementationPhase.MVP_DEVELOPMENT,
            name="Minimum Viable Product Development",
            description="Core feature development with basic AI functionality and user interface",
            duration_weeks=8 if complexity == ComplexityLevel.LOW else 12 if complexity == ComplexityLevel.MEDIUM else 16,
            key_deliverables=[
                "Core AI functionality",
                "Basic user interface",
                "API endpoints",
                "Database schema",
                "Initial deployment pipeline"
            ],
            required_skills=[
                "Full-stack development",
                "AI/ML engineering",
                "DevOps",
                "UI/UX design"
            ],
            technologies_introduced=[tech.name for tech in tech_stack[3:6]],  # Additional technologies
            success_criteria=[
                "MVP demonstrates core value proposition",
                "AI model integrated successfully",
                "User interface functional and intuitive",
                "Basic security measures implemented"
            ],
            risks=[
                "Feature scope creep",
                "AI model training delays",
                "Integration challenges between components"
            ],
            dependencies=["POC completion", "Design approval"],
            estimated_effort_hours=640 if complexity == ComplexityLevel.LOW else 960 if complexity == ComplexityLevel.MEDIUM else 1280,
            team_size_recommendation=3 if complexity == ComplexityLevel.LOW else 5
        ))
        
        # Phase 3: Beta Testing
        phases.append(ImplementationPhaseDetail(
            phase=ImplementationPhase.BETA_TESTING,
            name="Beta Testing and Refinement",
            description="User testing, feedback integration, and system optimization",
            duration_weeks=4 if complexity == ComplexityLevel.LOW else 6 if complexity == ComplexityLevel.MEDIUM else 8,
            key_deliverables=[
                "Beta testing program",
                "User feedback integration",
                "Performance optimization",
                "Security audit",
                "Documentation completion"
            ],
            required_skills=[
                "QA testing",
                "Performance optimization",
                "Security testing",
                "Documentation"
            ],
            technologies_introduced=["Monitoring and analytics tools"],
            success_criteria=[
                "Positive user feedback from beta testers",
                "Performance meets production requirements",
                "Security vulnerabilities addressed",
                "Documentation complete"
            ],
            risks=[
                "Negative user feedback requiring major changes",
                "Performance issues under load",
                "Security vulnerabilities discovered"
            ],
            dependencies=["MVP completion", "Beta user recruitment"],
            estimated_effort_hours=320 if complexity == ComplexityLevel.LOW else 480 if complexity == ComplexityLevel.MEDIUM else 640,
            team_size_recommendation=4 if complexity == ComplexityLevel.LOW else 6
        ))
        
        # Phase 4: Production Launch
        phases.append(ImplementationPhaseDetail(
            phase=ImplementationPhase.PRODUCTION_LAUNCH,
            name="Production Launch",
            description="Production deployment, monitoring setup, and go-live support",
            duration_weeks=2 if complexity == ComplexityLevel.LOW else 4 if complexity == ComplexityLevel.MEDIUM else 6,
            key_deliverables=[
                "Production deployment",
                "Monitoring and alerting",
                "Backup and disaster recovery",
                "Launch marketing materials",
                "Support documentation"
            ],
            required_skills=[
                "DevOps",
                "Production support",
                "Marketing",
                "Customer support"
            ],
            technologies_introduced=["Production monitoring", "Deployment automation"],
            success_criteria=[
                "Successful production deployment",
                "Monitoring and alerting operational",
                "Initial user acquisition targets met",
                "System stability confirmed"
            ],
            risks=[
                "Production deployment issues",
                "Unexpected load patterns",
                "User adoption below expectations"
            ],
            dependencies=["Beta testing completion", "Production environment setup"],
            estimated_effort_hours=160 if complexity == ComplexityLevel.LOW else 320 if complexity == ComplexityLevel.MEDIUM else 480,
            team_size_recommendation=5 if complexity == ComplexityLevel.LOW else 7
        ))
        
        # Phase 5: Scale and Optimization (for higher complexity projects)
        if complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]:
            phases.append(ImplementationPhaseDetail(
                phase=ImplementationPhase.SCALE_OPTIMIZATION,
                name="Scale and Optimization",
                description="Performance optimization, feature enhancement, and scaling for growth",
                duration_weeks=8 if complexity == ComplexityLevel.HIGH else 12,
                key_deliverables=[
                    "Performance optimization",
                    "Advanced AI features",
                    "Scaling infrastructure",
                    "Advanced analytics",
                    "Enterprise features"
                ],
                required_skills=[
                    "Performance engineering",
                    "Advanced AI/ML",
                    "Scaling architecture",
                    "Enterprise development"
                ],
                technologies_introduced=["Advanced monitoring", "Scaling tools", "Enterprise integrations"],
                success_criteria=[
                    "System handles increased load",
                    "Advanced features delivered",
                    "Enterprise customers onboarded",
                    "Profitability targets met"
                ],
                risks=[
                    "Scaling challenges",
                    "Feature complexity issues",
                    "Competitive pressure"
                ],
                dependencies=["Production launch success", "Market validation"],
                estimated_effort_hours=640 if complexity == ComplexityLevel.HIGH else 960,
                team_size_recommendation=8 if complexity == ComplexityLevel.HIGH else 10
            ))
        
        return phases
    
    async def _recommend_team_size(self, complexity: ComplexityLevel, total_hours: int, timeline_weeks: int) -> int:
        """Recommend team size based on complexity and timeline."""
        # Calculate base team size from hours and timeline
        available_hours_per_week = 40  # Standard work week
        total_available_hours = timeline_weeks * available_hours_per_week
        
        base_team_size = math.ceil(total_hours / total_available_hours)
        
        # Adjust based on complexity
        complexity_multipliers = {
            ComplexityLevel.LOW: 1.0,
            ComplexityLevel.MEDIUM: 1.2,
            ComplexityLevel.HIGH: 1.5,
            ComplexityLevel.VERY_HIGH: 2.0
        }
        
        adjusted_team_size = math.ceil(base_team_size * complexity_multipliers[complexity])
        
        # Ensure reasonable bounds
        return max(2, min(12, adjusted_team_size))
    
    async def _analyze_team_composition(
        self,
        opportunity: Opportunity,
        architecture: ArchitectureRecommendation,
        tech_stack: List[TechnologyRecommendation],
        phases: List[ImplementationPhaseDetail],
        complexity: ComplexityLevel,
        timeline_weeks: int,
        total_hours: int
    ) -> TeamCompositionAnalysis:
        """Analyze and recommend comprehensive team composition."""
        logger.info(f"Analyzing team composition for opportunity {opportunity.id}")
        
        # Identify required skills from technology stack and phases
        required_skills = await self._identify_skill_requirements(
            opportunity, architecture, tech_stack, phases, complexity
        )
        
        # Generate role recommendations
        recommended_roles = await self._generate_role_recommendations(
            required_skills, architecture, complexity, timeline_weeks, total_hours
        )
        
        # Calculate team structure and size
        team_structure = await self._calculate_team_structure(recommended_roles, phases)
        total_team_size = len(recommended_roles)
        
        # Create skill matrix
        skill_matrix = await self._create_skill_matrix(recommended_roles)
        
        # Generate hiring timeline
        hiring_timeline = await self._generate_hiring_timeline(recommended_roles, phases)
        
        # Calculate budget implications
        budget_implications = await self._calculate_team_budget(recommended_roles, timeline_weeks)
        
        # Generate scaling recommendations
        scaling_recommendations = await self._generate_scaling_recommendations(
            recommended_roles, complexity, timeline_weeks
        )
        
        # Identify risk mitigation strategies
        risk_mitigation = await self._identify_team_risks_and_mitigation(
            recommended_roles, complexity, timeline_weeks
        )
        
        # Generate alternative compositions
        alternative_compositions = await self._generate_alternative_compositions(
            recommended_roles, complexity, budget_implications
        )
        
        return TeamCompositionAnalysis(
            analysis_id=f"team_analysis_{opportunity.id}",
            opportunity_id=str(opportunity.id),
            generated_at=datetime.utcnow(),
            recommended_roles=recommended_roles,
            total_team_size=total_team_size,
            team_structure=team_structure,
            skill_matrix=skill_matrix,
            hiring_timeline=hiring_timeline,
            budget_implications=budget_implications,
            scaling_recommendations=scaling_recommendations,
            risk_mitigation=risk_mitigation,
            alternative_compositions=alternative_compositions
        )
    
    async def _identify_skill_requirements(
        self,
        opportunity: Opportunity,
        architecture: ArchitectureRecommendation,
        tech_stack: List[TechnologyRecommendation],
        phases: List[ImplementationPhaseDetail],
        complexity: ComplexityLevel
    ) -> Dict[str, List[SkillRequirement]]:
        """Identify all required skills categorized by domain."""
        skills = {
            "ai_ml": [],
            "backend": [],
            "frontend": [],
            "data": [],
            "devops": [],
            "product": [],
            "design": [],
            "security": [],
            "research": []
        }
        
        # AI/ML skills from opportunity and tech stack
        if opportunity.ai_solution_types:
            ai_types = json.loads(opportunity.ai_solution_types) if isinstance(opportunity.ai_solution_types, str) else opportunity.ai_solution_types
            for ai_type in ai_types:
                ai_type_lower = str(ai_type).lower()
                if "nlp" in ai_type_lower or "language" in ai_type_lower:
                    skills["ai_ml"].extend([
                        SkillRequirement(
                            skill_name="Natural Language Processing",
                            importance="critical",
                            proficiency_level="advanced",
                            alternatives=["Transformers", "BERT", "GPT"],
                            learning_resources=["Hugging Face Course", "CS224N Stanford", "NLP with Python"]
                        ),
                        SkillRequirement(
                            skill_name="Text Processing",
                            importance="critical",
                            proficiency_level="intermediate",
                            alternatives=["spaCy", "NLTK", "TextBlob"],
                            learning_resources=["spaCy Documentation", "NLTK Book"]
                        )
                    ])
                
                if "computer_vision" in ai_type_lower or "vision" in ai_type_lower:
                    skills["ai_ml"].extend([
                        SkillRequirement(
                            skill_name="Computer Vision",
                            importance="critical",
                            proficiency_level="advanced",
                            alternatives=["OpenCV", "PIL", "scikit-image"],
                            learning_resources=["CS231n Stanford", "OpenCV Tutorials", "Deep Learning for Computer Vision"]
                        ),
                        SkillRequirement(
                            skill_name="Image Processing",
                            importance="important",
                            proficiency_level="intermediate",
                            alternatives=["PIL", "OpenCV", "ImageIO"],
                            learning_resources=["Digital Image Processing Book", "OpenCV Python Tutorials"]
                        )
                    ])
                
                if "machine_learning" in ai_type_lower:
                    skills["ai_ml"].extend([
                        SkillRequirement(
                            skill_name="Machine Learning",
                            importance="critical",
                            proficiency_level="advanced",
                            alternatives=["scikit-learn", "XGBoost", "LightGBM"],
                            learning_resources=["Andrew Ng Course", "Hands-On ML Book", "scikit-learn Documentation"]
                        ),
                        SkillRequirement(
                            skill_name="Deep Learning",
                            importance="important",
                            proficiency_level="advanced",
                            alternatives=["PyTorch", "TensorFlow", "Keras"],
                            learning_resources=["Deep Learning Book", "Fast.ai Course", "PyTorch Tutorials"]
                        )
                    ])
        
        # Technology stack skills
        for tech in tech_stack:
            if tech.category == TechnologyCategory.AI_FRAMEWORK:
                if "pytorch" in tech.name.lower():
                    skills["ai_ml"].append(SkillRequirement(
                        skill_name="PyTorch",
                        importance="critical",
                        proficiency_level="advanced",
                        alternatives=["TensorFlow", "JAX"],
                        learning_resources=["PyTorch Tutorials", "Deep Learning with PyTorch"]
                    ))
                elif "tensorflow" in tech.name.lower():
                    skills["ai_ml"].append(SkillRequirement(
                        skill_name="TensorFlow",
                        importance="critical",
                        proficiency_level="advanced",
                        alternatives=["PyTorch", "Keras"],
                        learning_resources=["TensorFlow Documentation", "TensorFlow Developer Certificate"]
                    ))
            
            elif tech.category == TechnologyCategory.BACKEND_FRAMEWORK:
                if "fastapi" in tech.name.lower():
                    skills["backend"].extend([
                        SkillRequirement(
                            skill_name="FastAPI",
                            importance="critical",
                            proficiency_level="advanced",
                            alternatives=["Django", "Flask", "Express.js"],
                            learning_resources=["FastAPI Documentation", "FastAPI Tutorial"]
                        ),
                        SkillRequirement(
                            skill_name="Python",
                            importance="critical",
                            proficiency_level="advanced",
                            alternatives=["JavaScript", "Java", "Go"],
                            learning_resources=["Python Documentation", "Effective Python"]
                        ),
                        SkillRequirement(
                            skill_name="Async Programming",
                            importance="important",
                            proficiency_level="intermediate",
                            alternatives=["asyncio", "aiohttp"],
                            learning_resources=["Python Async Programming", "asyncio Documentation"]
                        )
                    ])
            
            elif tech.category == TechnologyCategory.DATABASE:
                if "postgresql" in tech.name.lower():
                    skills["data"].append(SkillRequirement(
                        skill_name="PostgreSQL",
                        importance="critical",
                        proficiency_level="intermediate",
                        alternatives=["MySQL", "MongoDB", "SQLite"],
                        learning_resources=["PostgreSQL Documentation", "PostgreSQL Up & Running"]
                    ))
                elif "redis" in tech.name.lower():
                    skills["data"].append(SkillRequirement(
                        skill_name="Redis",
                        importance="important",
                        proficiency_level="intermediate",
                        alternatives=["Memcached", "DynamoDB"],
                        learning_resources=["Redis Documentation", "Redis in Action"]
                    ))
        
        # Architecture-specific skills
        if architecture.pattern == ArchitecturePattern.MICROSERVICES:
            skills["devops"].extend([
                SkillRequirement(
                    skill_name="Docker",
                    importance="critical",
                    proficiency_level="advanced",
                    alternatives=["Podman", "containerd"],
                    learning_resources=["Docker Documentation", "Docker Deep Dive"]
                ),
                SkillRequirement(
                    skill_name="Kubernetes",
                    importance="critical",
                    proficiency_level="advanced",
                    alternatives=["Docker Swarm", "ECS", "Nomad"],
                    learning_resources=["Kubernetes Documentation", "Kubernetes in Action"]
                ),
                SkillRequirement(
                    skill_name="Service Mesh",
                    importance="important",
                    proficiency_level="intermediate",
                    alternatives=["Istio", "Linkerd", "Consul Connect"],
                    learning_resources=["Istio Documentation", "Service Mesh Patterns"]
                )
            ])
        elif architecture.pattern == ArchitecturePattern.SERVERLESS:
            skills["devops"].extend([
                SkillRequirement(
                    skill_name="AWS Lambda",
                    importance="critical",
                    proficiency_level="advanced",
                    alternatives=["Azure Functions", "Google Cloud Functions"],
                    learning_resources=["AWS Lambda Documentation", "Serverless Architectures on AWS"]
                ),
                SkillRequirement(
                    skill_name="Serverless Framework",
                    importance="important",
                    proficiency_level="intermediate",
                    alternatives=["SAM", "Terraform", "CDK"],
                    learning_resources=["Serverless Framework Documentation"]
                )
            ])
        
        # Complexity-based skills
        if complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]:
            skills["research"].extend([
                SkillRequirement(
                    skill_name="Research & Development",
                    importance="critical",
                    proficiency_level="expert",
                    alternatives=["Academic Research", "Industry Research"],
                    learning_resources=["Research Methodology", "AI Research Papers"]
                ),
                SkillRequirement(
                    skill_name="Algorithm Design",
                    importance="important",
                    proficiency_level="advanced",
                    alternatives=["Mathematical Optimization", "Heuristic Methods"],
                    learning_resources=["Algorithm Design Manual", "Introduction to Algorithms"]
                )
            ])
        
        # Always needed skills
        skills["product"].extend([
            SkillRequirement(
                skill_name="Product Management",
                importance="critical",
                proficiency_level="advanced",
                alternatives=["Technical Product Management", "AI Product Management"],
                learning_resources=["Inspired Book", "Product Management Course"]
            ),
            SkillRequirement(
                skill_name="Agile Methodologies",
                importance="important",
                proficiency_level="intermediate",
                alternatives=["Scrum", "Kanban", "Lean"],
                learning_resources=["Scrum Guide", "Agile Manifesto"]
            )
        ])
        
        skills["security"].extend([
            SkillRequirement(
                skill_name="Application Security",
                importance="important",
                proficiency_level="intermediate",
                alternatives=["OWASP", "Security Testing"],
                learning_resources=["OWASP Top 10", "Web Application Security"]
            ),
            SkillRequirement(
                skill_name="Data Privacy",
                importance="critical",
                proficiency_level="intermediate",
                alternatives=["GDPR", "CCPA", "HIPAA"],
                learning_resources=["Data Privacy Laws", "Privacy by Design"]
            )
        ])
        
        return skills
    
    async def _generate_role_recommendations(
        self,
        required_skills: Dict[str, List[SkillRequirement]],
        architecture: ArchitectureRecommendation,
        complexity: ComplexityLevel,
        timeline_weeks: int,
        total_hours: int
    ) -> List[TeamRoleRecommendation]:
        """Generate specific role recommendations based on skill requirements."""
        roles = []
        
        # AI/ML Engineer (always needed for AI opportunities)
        if required_skills["ai_ml"]:
            ai_skills = required_skills["ai_ml"]
            experience_level = ExperienceLevel.SENIOR if complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH] else ExperienceLevel.MID_LEVEL
            
            roles.append(TeamRoleRecommendation(
                role_type=RoleType.AI_ML_ENGINEER,
                role_title="AI/ML Engineer",
                description="Responsible for designing, implementing, and optimizing AI/ML models and algorithms",
                required_skills=ai_skills,
                experience_level=experience_level,
                commitment_type=CommitmentType.FULL_TIME,
                estimated_hours_per_week=40,
                phases_involved=[ImplementationPhase.RESEARCH_POC, ImplementationPhase.MVP_DEVELOPMENT, ImplementationPhase.BETA_TESTING],
                salary_range={"min": 120000, "max": 180000, "currency": "USD"},
                alternatives=["Data Scientist with ML focus", "Research Scientist"],
                justification="Critical for implementing AI capabilities and ensuring model performance"
            ))
        
        # Backend Developer
        if required_skills["backend"]:
            backend_skills = required_skills["backend"]
            experience_level = ExperienceLevel.SENIOR if architecture.pattern == ArchitecturePattern.MICROSERVICES else ExperienceLevel.MID_LEVEL
            
            roles.append(TeamRoleRecommendation(
                role_type=RoleType.BACKEND_DEVELOPER,
                role_title="Backend Developer",
                description="Responsible for API development, system architecture, and backend infrastructure",
                required_skills=backend_skills,
                experience_level=experience_level,
                commitment_type=CommitmentType.FULL_TIME,
                estimated_hours_per_week=40,
                phases_involved=[ImplementationPhase.MVP_DEVELOPMENT, ImplementationPhase.BETA_TESTING, ImplementationPhase.PRODUCTION_LAUNCH],
                salary_range={"min": 90000, "max": 140000, "currency": "USD"},
                alternatives=["Full-stack Developer", "Software Engineer"],
                justification="Essential for building scalable backend systems and APIs"
            ))
        
        # Data Engineer (if significant data processing needed)
        if required_skills["data"] and len(required_skills["data"]) > 2:
            data_skills = required_skills["data"]
            
            roles.append(TeamRoleRecommendation(
                role_type=RoleType.DATA_ENGINEER,
                role_title="Data Engineer",
                description="Responsible for data pipeline design, ETL processes, and data infrastructure",
                required_skills=data_skills,
                experience_level=ExperienceLevel.MID_LEVEL,
                commitment_type=CommitmentType.FULL_TIME,
                estimated_hours_per_week=40,
                phases_involved=[ImplementationPhase.RESEARCH_POC, ImplementationPhase.MVP_DEVELOPMENT],
                salary_range={"min": 100000, "max": 150000, "currency": "USD"},
                alternatives=["Backend Developer with data focus", "Data Scientist"],
                justification="Needed for robust data processing and pipeline management"
            ))
        
        # DevOps Engineer (for complex architectures)
        if required_skills["devops"] and (architecture.pattern in [ArchitecturePattern.MICROSERVICES, ArchitecturePattern.SERVERLESS]):
            devops_skills = required_skills["devops"]
            
            roles.append(TeamRoleRecommendation(
                role_type=RoleType.DEVOPS_ENGINEER,
                role_title="DevOps Engineer",
                description="Responsible for deployment automation, infrastructure management, and CI/CD",
                required_skills=devops_skills,
                experience_level=ExperienceLevel.SENIOR,
                commitment_type=CommitmentType.FULL_TIME,
                estimated_hours_per_week=40,
                phases_involved=[ImplementationPhase.MVP_DEVELOPMENT, ImplementationPhase.BETA_TESTING, ImplementationPhase.PRODUCTION_LAUNCH, ImplementationPhase.SCALE_OPTIMIZATION],
                salary_range={"min": 110000, "max": 160000, "currency": "USD"},
                alternatives=["Platform Engineer", "Site Reliability Engineer"],
                justification="Critical for managing complex deployment and scaling requirements"
            ))
        
        # Product Manager (always needed)
        product_skills = required_skills["product"]
        roles.append(TeamRoleRecommendation(
            role_type=RoleType.PRODUCT_MANAGER,
            role_title="Product Manager",
            description="Responsible for product strategy, roadmap, and stakeholder coordination",
            required_skills=product_skills,
            experience_level=ExperienceLevel.SENIOR,
            commitment_type=CommitmentType.FULL_TIME,
            estimated_hours_per_week=40,
            phases_involved=[ImplementationPhase.RESEARCH_POC, ImplementationPhase.MVP_DEVELOPMENT, ImplementationPhase.BETA_TESTING, ImplementationPhase.PRODUCTION_LAUNCH],
            salary_range={"min": 130000, "max": 180000, "currency": "USD"},
            alternatives=["Technical Product Manager", "Product Owner"],
            justification="Essential for coordinating development and ensuring market fit"
        ))
        
        # Frontend Developer (if UI needed)
        if self._needs_frontend_role(complexity, timeline_weeks):
            roles.append(TeamRoleRecommendation(
                role_type=RoleType.FRONTEND_DEVELOPER,
                role_title="Frontend Developer",
                description="Responsible for user interface development and user experience implementation",
                required_skills=[
                    SkillRequirement(
                        skill_name="React/Vue.js",
                        importance="critical",
                        proficiency_level="advanced",
                        alternatives=["Angular", "Svelte"],
                        learning_resources=["React Documentation", "Vue.js Guide"]
                    ),
                    SkillRequirement(
                        skill_name="JavaScript/TypeScript",
                        importance="critical",
                        proficiency_level="advanced",
                        alternatives=["JavaScript ES6+"],
                        learning_resources=["MDN JavaScript", "TypeScript Handbook"]
                    )
                ],
                experience_level=ExperienceLevel.MID_LEVEL,
                commitment_type=CommitmentType.FULL_TIME,
                estimated_hours_per_week=40,
                phases_involved=[ImplementationPhase.MVP_DEVELOPMENT, ImplementationPhase.BETA_TESTING],
                salary_range={"min": 80000, "max": 130000, "currency": "USD"},
                alternatives=["Full-stack Developer", "UI Developer"],
                justification="Needed for creating user-friendly interfaces for AI applications"
            ))
        
        # Technical Lead (for complex projects)
        if complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH] or timeline_weeks > 20:
            roles.append(TeamRoleRecommendation(
                role_type=RoleType.TECHNICAL_LEAD,
                role_title="Technical Lead",
                description="Responsible for technical architecture decisions and team coordination",
                required_skills=[
                    SkillRequirement(
                        skill_name="Technical Leadership",
                        importance="critical",
                        proficiency_level="expert",
                        alternatives=["Engineering Management", "Solution Architecture"],
                        learning_resources=["The Manager's Path", "Staff Engineer Book"]
                    ),
                    SkillRequirement(
                        skill_name="System Design",
                        importance="critical",
                        proficiency_level="expert",
                        alternatives=["Software Architecture", "Distributed Systems"],
                        learning_resources=["Designing Data-Intensive Applications", "System Design Interview"]
                    )
                ],
                experience_level=ExperienceLevel.EXPERT,
                commitment_type=CommitmentType.FULL_TIME,
                estimated_hours_per_week=40,
                phases_involved=[ImplementationPhase.RESEARCH_POC, ImplementationPhase.MVP_DEVELOPMENT, ImplementationPhase.BETA_TESTING, ImplementationPhase.PRODUCTION_LAUNCH],
                salary_range={"min": 160000, "max": 220000, "currency": "USD"},
                alternatives=["Senior Software Architect", "Engineering Manager"],
                justification="Required for complex projects to ensure technical coherence and team coordination"
            ))
        
        # Research Scientist (for cutting-edge AI)
        if required_skills["research"] and complexity == ComplexityLevel.VERY_HIGH:
            research_skills = required_skills["research"]
            
            roles.append(TeamRoleRecommendation(
                role_type=RoleType.RESEARCH_SCIENTIST,
                role_title="Research Scientist",
                description="Responsible for advanced AI research and novel algorithm development",
                required_skills=research_skills,
                experience_level=ExperienceLevel.EXPERT,
                commitment_type=CommitmentType.CONSULTANT,
                estimated_hours_per_week=20,
                phases_involved=[ImplementationPhase.RESEARCH_POC],
                salary_range={"min": 150, "max": 300, "currency": "USD_per_hour"},
                alternatives=["AI Research Engineer", "Academic Consultant"],
                justification="Needed for breakthrough AI capabilities and research-grade implementations"
            ))
        
        # QA Engineer (for production systems)
        if timeline_weeks > 12:
            roles.append(TeamRoleRecommendation(
                role_type=RoleType.QA_ENGINEER,
                role_title="QA Engineer",
                description="Responsible for testing strategy, quality assurance, and test automation",
                required_skills=[
                    SkillRequirement(
                        skill_name="Test Automation",
                        importance="critical",
                        proficiency_level="advanced",
                        alternatives=["Selenium", "Cypress", "Playwright"],
                        learning_resources=["Test Automation University", "Selenium Documentation"]
                    ),
                    SkillRequirement(
                        skill_name="AI Model Testing",
                        importance="important",
                        proficiency_level="intermediate",
                        alternatives=["Model Validation", "A/B Testing"],
                        learning_resources=["ML Testing Best Practices", "Model Validation Techniques"]
                    )
                ],
                experience_level=ExperienceLevel.MID_LEVEL,
                commitment_type=CommitmentType.PART_TIME,
                estimated_hours_per_week=20,
                phases_involved=[ImplementationPhase.BETA_TESTING, ImplementationPhase.PRODUCTION_LAUNCH],
                salary_range={"min": 70000, "max": 110000, "currency": "USD"},
                alternatives=["SDET", "Test Engineer"],
                justification="Essential for ensuring quality and reliability of AI systems"
            ))
        
        return roles
    
    def _needs_frontend_role(self, complexity: ComplexityLevel, timeline_weeks: int) -> bool:
        """Determine if a frontend developer is needed."""
        # Most AI applications need some form of UI
        return timeline_weeks > 8 or complexity in [ComplexityLevel.MEDIUM, ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]
    
    async def _calculate_team_structure(
        self,
        recommended_roles: List[TeamRoleRecommendation],
        phases: List[ImplementationPhaseDetail]
    ) -> Dict[str, Any]:
        """Calculate team structure and organization."""
        structure = {
            "total_roles": len(recommended_roles),
            "full_time_roles": len([r for r in recommended_roles if r.commitment_type == CommitmentType.FULL_TIME]),
            "part_time_roles": len([r for r in recommended_roles if r.commitment_type == CommitmentType.PART_TIME]),
            "consultant_roles": len([r for r in recommended_roles if r.commitment_type == CommitmentType.CONSULTANT]),
            "experience_distribution": {},
            "role_distribution": {},
            "phase_coverage": {}
        }
        
        # Experience level distribution
        for level in ExperienceLevel:
            count = len([r for r in recommended_roles if r.experience_level == level])
            if count > 0:
                structure["experience_distribution"][level.value] = count
        
        # Role type distribution
        for role_type in RoleType:
            count = len([r for r in recommended_roles if r.role_type == role_type])
            if count > 0:
                structure["role_distribution"][role_type.value] = count
        
        # Phase coverage
        for phase in phases:
            roles_in_phase = [r for r in recommended_roles if phase.phase in r.phases_involved]
            structure["phase_coverage"][phase.phase.value] = {
                "role_count": len(roles_in_phase),
                "roles": [r.role_title for r in roles_in_phase]
            }
        
        return structure
    
    async def _create_skill_matrix(
        self,
        recommended_roles: List[TeamRoleRecommendation]
    ) -> Dict[str, List[str]]:
        """Create a skill matrix mapping skills to roles."""
        skill_matrix = {}
        
        for role in recommended_roles:
            for skill in role.required_skills:
                if skill.skill_name not in skill_matrix:
                    skill_matrix[skill.skill_name] = []
                skill_matrix[skill.skill_name].append(role.role_title)
        
        return skill_matrix
    
    async def _generate_hiring_timeline(
        self,
        recommended_roles: List[TeamRoleRecommendation],
        phases: List[ImplementationPhaseDetail]
    ) -> Dict[str, Any]:
        """Generate recommended hiring timeline."""
        timeline = {
            "immediate_hires": [],
            "phase_based_hires": {},
            "hiring_priorities": [],
            "total_hiring_duration_weeks": 0
        }
        
        # Immediate hires (critical roles needed from start)
        critical_roles = [
            RoleType.TECHNICAL_LEAD,
            RoleType.PRODUCT_MANAGER,
            RoleType.AI_ML_ENGINEER
        ]
        
        for role in recommended_roles:
            if role.role_type in critical_roles:
                timeline["immediate_hires"].append({
                    "role": role.role_title,
                    "justification": "Critical for project initiation and technical direction"
                })
        
        # Phase-based hiring
        for phase in phases:
            phase_roles = []
            for role in recommended_roles:
                if phase.phase in role.phases_involved and role.role_type not in critical_roles:
                    phase_roles.append({
                        "role": role.role_title,
                        "commitment": role.commitment_type.value,
                        "justification": f"Needed for {phase.name} phase activities"
                    })
            
            if phase_roles:
                timeline["phase_based_hires"][phase.phase.value] = phase_roles
        
        # Hiring priorities
        priority_order = [
            ("Technical Lead", "Provides technical direction and architecture decisions"),
            ("Product Manager", "Defines requirements and coordinates stakeholders"),
            ("AI/ML Engineer", "Core AI capability development"),
            ("Backend Developer", "System infrastructure and APIs"),
            ("Data Engineer", "Data pipeline and processing capabilities"),
            ("DevOps Engineer", "Deployment and infrastructure automation"),
            ("Frontend Developer", "User interface and experience"),
            ("QA Engineer", "Quality assurance and testing"),
            ("Research Scientist", "Advanced AI research and innovation")
        ]
        
        for role_title, justification in priority_order:
            if any(r.role_title == role_title for r in recommended_roles):
                timeline["hiring_priorities"].append({
                    "role": role_title,
                    "justification": justification
                })
        
        # Estimate total hiring duration
        timeline["total_hiring_duration_weeks"] = min(12, len(recommended_roles) * 2)
        
        return timeline
    
    async def _calculate_team_budget(
        self,
        recommended_roles: List[TeamRoleRecommendation],
        timeline_weeks: int
    ) -> Dict[str, Any]:
        """Calculate budget implications for the team."""
        budget = {
            "annual_salary_costs": {},
            "total_annual_cost": 0,
            "project_cost_estimate": 0,
            "cost_breakdown": {},
            "cost_optimization_suggestions": []
        }
        
        total_annual = 0
        for role in recommended_roles:
            if role.commitment_type == CommitmentType.FULL_TIME:
                avg_salary = (role.salary_range["min"] + role.salary_range["max"]) / 2
                budget["annual_salary_costs"][role.role_title] = avg_salary
                total_annual += avg_salary
            elif role.commitment_type == CommitmentType.PART_TIME:
                avg_salary = (role.salary_range["min"] + role.salary_range["max"]) / 2
                part_time_cost = avg_salary * 0.5  # Assuming 50% time
                budget["annual_salary_costs"][role.role_title] = part_time_cost
                total_annual += part_time_cost
            elif role.commitment_type == CommitmentType.CONSULTANT:
                if "per_hour" in role.salary_range["currency"]:
                    avg_hourly = (role.salary_range["min"] + role.salary_range["max"]) / 2
                    annual_cost = avg_hourly * role.estimated_hours_per_week * 52
                    budget["annual_salary_costs"][role.role_title] = annual_cost
                    total_annual += annual_cost
        
        budget["total_annual_cost"] = total_annual
        budget["project_cost_estimate"] = total_annual * (timeline_weeks / 52)
        
        # Cost breakdown
        budget["cost_breakdown"] = {
            "engineering_costs": sum(cost for role, cost in budget["annual_salary_costs"].items() 
                                   if any(eng_role in role.lower() for eng_role in ["engineer", "developer", "scientist"])),
            "management_costs": sum(cost for role, cost in budget["annual_salary_costs"].items() 
                                  if any(mgmt_role in role.lower() for mgmt_role in ["manager", "lead"])),
            "consultant_costs": sum(cost for role, cost in budget["annual_salary_costs"].items() 
                                  if "consultant" in role.lower() or "research" in role.lower())
        }
        
        # Cost optimization suggestions
        if total_annual > 800000:  # High cost threshold
            budget["cost_optimization_suggestions"].extend([
                "Consider hiring junior developers with senior mentorship",
                "Evaluate remote team members for cost savings",
                "Phase hiring to spread costs over time"
            ])
        
        if len([r for r in recommended_roles if r.commitment_type == CommitmentType.CONSULTANT]) > 2:
            budget["cost_optimization_suggestions"].append(
                "Consider converting consultant roles to full-time for long-term projects"
            )
        
        return budget
    
    async def _generate_scaling_recommendations(
        self,
        recommended_roles: List[TeamRoleRecommendation],
        complexity: ComplexityLevel,
        timeline_weeks: int
    ) -> List[str]:
        """Generate team scaling recommendations."""
        recommendations = []
        
        # Team size recommendations
        team_size = len(recommended_roles)
        if team_size < 4:
            recommendations.append("Consider cross-functional team members to reduce coordination overhead")
        elif team_size > 8:
            recommendations.append("Plan for team structure and communication protocols for larger teams")
        
        # Scaling based on complexity
        if complexity == ComplexityLevel.VERY_HIGH:
            recommendations.extend([
                "Plan for specialized expertise acquisition as project evolves",
                "Consider academic partnerships for cutting-edge research capabilities",
                "Implement knowledge sharing protocols to prevent single points of failure"
            ])
        
        # Timeline-based scaling
        if timeline_weeks > 24:
            recommendations.extend([
                "Plan for team member rotation to prevent burnout",
                "Consider phased team scaling to match project phases",
                "Implement mentorship programs for knowledge transfer"
            ])
        
        # Role-specific scaling
        ai_roles = [r for r in recommended_roles if r.role_type in [RoleType.AI_ML_ENGINEER, RoleType.DATA_SCIENTIST]]
        if len(ai_roles) > 2:
            recommendations.append("Consider AI/ML team lead role for coordination")
        
        return recommendations
    
    async def _identify_team_risks_and_mitigation(
        self,
        recommended_roles: List[TeamRoleRecommendation],
        complexity: ComplexityLevel,
        timeline_weeks: int
    ) -> List[Dict[str, Any]]:
        """Identify team-related risks and mitigation strategies."""
        risks = []
        
        # Key person dependency risk
        critical_roles = [r for r in recommended_roles if r.experience_level == ExperienceLevel.EXPERT]
        if len(critical_roles) > 0:
            risks.append({
                "risk": "Key person dependency",
                "description": "Over-reliance on expert-level team members",
                "probability": "medium",
                "impact": "high",
                "mitigation": [
                    "Implement knowledge documentation practices",
                    "Cross-train team members on critical components",
                    "Maintain backup consultant relationships"
                ]
            })
        
        # Skill gap risk
        high_skill_requirements = sum(len(r.required_skills) for r in recommended_roles)
        if high_skill_requirements > 20:
            risks.append({
                "risk": "Skill acquisition challenge",
                "description": "High number of specialized skills required",
                "probability": "high",
                "impact": "medium",
                "mitigation": [
                    "Prioritize core skills for immediate hiring",
                    "Plan for training and skill development programs",
                    "Consider external training partnerships"
                ]
            })
        
        # Team coordination risk
        if len(recommended_roles) > 6:
            risks.append({
                "risk": "Team coordination complexity",
                "description": "Large team size may impact communication and coordination",
                "probability": "medium",
                "impact": "medium",
                "mitigation": [
                    "Implement clear communication protocols",
                    "Use project management tools and practices",
                    "Regular team synchronization meetings"
                ]
            })
        
        # Budget risk
        consultant_roles = [r for r in recommended_roles if r.commitment_type == CommitmentType.CONSULTANT]
        if len(consultant_roles) > 1:
            risks.append({
                "risk": "Budget volatility",
                "description": "High consultant costs may impact budget predictability",
                "probability": "medium",
                "impact": "medium",
                "mitigation": [
                    "Negotiate fixed-price contracts where possible",
                    "Plan for consultant-to-employee conversion",
                    "Maintain budget contingency for consultant costs"
                ]
            })
        
        return risks
    
    async def _generate_alternative_compositions(
        self,
        recommended_roles: List[TeamRoleRecommendation],
        complexity: ComplexityLevel,
        budget_implications: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate alternative team compositions."""
        alternatives = []
        
        # Budget-optimized composition
        if budget_implications["total_annual_cost"] > 600000:
            alternatives.append({
                "name": "Budget-Optimized Team",
                "description": "Reduced cost team with cross-functional roles",
                "changes": [
                    "Combine AI/ML Engineer and Data Scientist roles",
                    "Use full-stack developer instead of separate frontend/backend",
                    "Part-time Product Manager instead of full-time",
                    "Consultant DevOps instead of full-time"
                ],
                "estimated_savings": "30-40% cost reduction",
                "trade_offs": [
                    "Longer development timeline",
                    "Potential skill gaps in specialized areas",
                    "Higher individual workload"
                ]
            })
        
        # Startup-focused composition
        if len(recommended_roles) > 5:
            alternatives.append({
                "name": "Startup Team",
                "description": "Minimal viable team for early-stage development",
                "core_roles": [
                    "Technical Co-founder (AI/ML + Backend)",
                    "Full-stack Developer",
                    "Product Manager/Designer hybrid"
                ],
                "estimated_cost": "60-70% of recommended team cost",
                "scaling_plan": "Add specialists as product grows and funding increases"
            })
        
        # Enterprise composition
        if complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]:
            alternatives.append({
                "name": "Enterprise Team",
                "description": "Comprehensive team with specialized roles and redundancy",
                "additional_roles": [
                    "Solution Architect",
                    "Data Architect", 
                    "Security Specialist",
                    "Business Analyst",
                    "Scrum Master"
                ],
                "estimated_cost": "40-50% increase over recommended team",
                "benefits": [
                    "Reduced technical risk",
                    "Faster development with specialized expertise",
                    "Better compliance and security posture"
                ]
            })
        
        return alternatives
    
    async def _identify_technical_risks(
        self,
        opportunity: Opportunity,
        architecture: ArchitectureRecommendation,
        tech_stack: List[TechnologyRecommendation]
    ) -> List[Dict[str, Any]]:
        """Identify key technical risks."""
        risks = []
        
        # Architecture-specific risks
        if architecture.pattern == ArchitecturePattern.MICROSERVICES:
            risks.append({
                "risk": "Microservices complexity overhead",
                "category": "architecture",
                "probability": "medium",
                "impact": "high",
                "mitigation": "Start with modular monolith, migrate to microservices gradually"
            })
        
        # AI-specific risks
        if opportunity.ai_solution_types:
            risks.append({
                "risk": "AI model performance degradation in production",
                "category": "ai_model",
                "probability": "medium",
                "impact": "high",
                "mitigation": "Implement model monitoring, A/B testing, and gradual rollout"
            })
        
        # Technology risks
        high_complexity_techs = [tech for tech in tech_stack if tech.complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]]
        if high_complexity_techs:
            risks.append({
                "risk": "Learning curve for complex technologies",
                "category": "technology",
                "probability": "high",
                "impact": "medium",
                "mitigation": "Invest in training, consider consulting, start with simpler alternatives"
            })
        
        # Data risks
        risks.append({
            "risk": "Data quality and availability issues",
            "category": "data",
            "probability": "medium",
            "impact": "high",
            "mitigation": "Implement data validation, backup sources, and quality monitoring"
        })
        
        # Scalability risks
        risks.append({
            "risk": "Unexpected scalability bottlenecks",
            "category": "scalability",
            "probability": "medium",
            "impact": "medium",
            "mitigation": "Load testing, monitoring, and scalable architecture patterns"
        })
        
        return risks
    
    async def _define_infrastructure_requirements(
        self,
        opportunity: Opportunity,
        architecture: ArchitectureRecommendation,
        tech_stack: List[TechnologyRecommendation],
        market_analysis: Optional[MarketAnalysisResult]
    ) -> Dict[str, Any]:
        """Define infrastructure requirements."""
        
        # Estimate compute requirements based on AI workload
        compute_requirements = self._estimate_compute_requirements(opportunity, tech_stack)
        
        # Storage requirements
        storage_requirements = self._estimate_storage_requirements(opportunity, market_analysis)
        
        # Network requirements
        network_requirements = self._estimate_network_requirements(opportunity, architecture)
        
        return {
            "compute": compute_requirements,
            "storage": storage_requirements,
            "network": network_requirements,
            "estimated_monthly_cost": self._estimate_infrastructure_cost(
                compute_requirements, storage_requirements, network_requirements
            )
        }
    
    def _estimate_compute_requirements(self, opportunity: Opportunity, tech_stack: List[TechnologyRecommendation]) -> Dict[str, Any]:
        """Estimate compute requirements."""
        
        # Base requirements
        base_cpu_cores = 2
        base_memory_gb = 8
        
        # Check for AI-intensive workloads
        ai_framework = next((tech for tech in tech_stack if tech.category == TechnologyCategory.AI_FRAMEWORK), None)
        if ai_framework and "pytorch" in ai_framework.name.lower():
            base_cpu_cores *= 2
            base_memory_gb *= 4
            gpu_required = True
        else:
            gpu_required = False
        
        # Scale based on opportunity description
        if opportunity.description and any(word in opportunity.description.lower() for word in ["real-time", "high-volume", "scale"]):
            base_cpu_cores *= 2
            base_memory_gb *= 2
        
        return {
            "min_cpu_cores": base_cpu_cores,
            "min_memory_gb": base_memory_gb,
            "gpu_required": gpu_required,
            "gpu_memory_gb": 16 if gpu_required else 0,
            "auto_scaling": True,
            "max_instances": 10
        }
    
    def _estimate_storage_requirements(self, opportunity: Opportunity, market_analysis: Optional[MarketAnalysisResult]) -> Dict[str, Any]:
        """Estimate storage requirements."""
        
        # Base storage
        base_storage_gb = 100
        
        # Estimate based on market size if available
        if market_analysis:
            # Larger markets likely need more storage
            if market_analysis.serviceable_addressable_market > 100000000:  # $100M+ SAM
                base_storage_gb *= 10
            elif market_analysis.serviceable_addressable_market > 10000000:  # $10M+ SAM
                base_storage_gb *= 5
        
        # AI workloads typically need more storage
        if opportunity.ai_solution_types:
            base_storage_gb *= 3
        
        return {
            "primary_storage_gb": base_storage_gb,
            "backup_storage_gb": base_storage_gb * 2,
            "storage_type": "ssd",
            "backup_retention_days": 30,
            "disaster_recovery": True
        }
    
    def _estimate_network_requirements(self, opportunity: Opportunity, architecture: ArchitectureRecommendation) -> Dict[str, Any]:
        """Estimate network requirements."""
        
        # Base bandwidth
        base_bandwidth_mbps = 100
        
        # Microservices need more network capacity
        if architecture.pattern == ArchitecturePattern.MICROSERVICES:
            base_bandwidth_mbps *= 3
        
        # Real-time applications need low latency
        requires_low_latency = (
            opportunity.description and 
            any(word in opportunity.description.lower() for word in ["real-time", "instant", "live"])
        )
        
        return {
            "bandwidth_mbps": base_bandwidth_mbps,
            "latency_requirement": "low" if requires_low_latency else "standard",
            "cdn_required": True,
            "load_balancer_required": True,
            "ssl_required": True
        }
    
    def _estimate_infrastructure_cost(self, compute: Dict, storage: Dict, network: Dict) -> Dict[str, float]:
        """Estimate monthly infrastructure costs (rough estimates)."""
        
        # AWS-based cost estimates (rough)
        compute_cost = compute["min_cpu_cores"] * compute["min_memory_gb"] * 10  # $10 per core-GB per month
        if compute["gpu_required"]:
            compute_cost += 500  # GPU instance premium
        
        storage_cost = (storage["primary_storage_gb"] + storage["backup_storage_gb"]) * 0.10  # $0.10 per GB
        
        network_cost = network["bandwidth_mbps"] * 1.0  # $1 per Mbps
        
        total_cost = compute_cost + storage_cost + network_cost
        
        return {
            "compute_monthly_usd": compute_cost,
            "storage_monthly_usd": storage_cost,
            "network_monthly_usd": network_cost,
            "total_monthly_usd": total_cost
        }
    
    async def _define_performance_targets(self, opportunity: Opportunity, market_analysis: Optional[MarketAnalysisResult]) -> Dict[str, Any]:
        """Define performance targets."""
        
        # Base performance targets
        targets = {
            "response_time_ms": 500,
            "availability_percent": 99.5,
            "throughput_requests_per_second": 100,
            "ai_model_accuracy_percent": 85,
            "data_processing_latency_ms": 1000
        }
        
        # Adjust based on opportunity description
        if opportunity.description:
            description_lower = opportunity.description.lower()
            
            if "real-time" in description_lower:
                targets["response_time_ms"] = 100
                targets["data_processing_latency_ms"] = 200
            
            if "enterprise" in description_lower or "mission-critical" in description_lower:
                targets["availability_percent"] = 99.9
            
            if "high-volume" in description_lower or "scale" in description_lower:
                targets["throughput_requests_per_second"] = 1000
        
        # Adjust based on market size
        if market_analysis and market_analysis.serviceable_addressable_market > 50000000:  # $50M+ SAM
            targets["availability_percent"] = 99.9
            targets["throughput_requests_per_second"] *= 5
        
        return targets
    
    async def _define_security_considerations(self, opportunity: Opportunity, tech_stack: List[TechnologyRecommendation]) -> List[str]:
        """Define security considerations."""
        considerations = [
            "Implement OAuth 2.0 authentication",
            "Use HTTPS for all communications",
            "Implement input validation and sanitization",
            "Set up monitoring and logging",
            "Regular security updates and patches"
        ]
        
        # Industry-specific security
        if opportunity.target_industries:
            try:
                industries = json.loads(opportunity.target_industries) if isinstance(opportunity.target_industries, str) else opportunity.target_industries
                for industry in industries:
                    industry_lower = industry.lower()
                    if industry_lower in ["finance", "banking"]:
                        considerations.extend([
                            "PCI DSS compliance for payment data",
                            "SOX compliance for financial reporting",
                            "Multi-factor authentication required"
                        ])
                    elif industry_lower in ["healthcare", "medical"]:
                        considerations.extend([
                            "HIPAA compliance for patient data",
                            "Data encryption at rest and in transit",
                            "Audit logs for all data access"
                        ])
                    elif industry_lower in ["legal", "government"]:
                        considerations.extend([
                            "Data residency requirements",
                            "Enhanced access controls",
                            "Regular security audits"
                        ])
            except:
                pass
        
        # AI-specific security
        if opportunity.ai_solution_types:
            considerations.extend([
                "Model versioning and rollback capabilities",
                "AI model security and adversarial attack protection",
                "Data privacy in AI training and inference"
            ])
        
        return considerations
    
    async def _create_scalability_plan(
        self,
        opportunity: Opportunity,
        architecture: ArchitectureRecommendation,
        market_analysis: Optional[MarketAnalysisResult]
    ) -> Dict[str, Any]:
        """Create scalability plan."""
        
        plan = {
            "horizontal_scaling": {
                "enabled": True,
                "auto_scaling_triggers": ["CPU > 70%", "Memory > 80%", "Response time > 1s"],
                "max_instances": 10
            },
            "database_scaling": {
                "read_replicas": True,
                "connection_pooling": True,
                "caching_strategy": "Redis with TTL"
            },
            "cdn_strategy": {
                "static_assets": True,
                "api_caching": True,
                "global_distribution": False
            }
        }
        
        # Adjust based on market potential
        if market_analysis and market_analysis.serviceable_addressable_market > 100000000:  # $100M+ SAM
            plan["horizontal_scaling"]["max_instances"] = 50
            plan["cdn_strategy"]["global_distribution"] = True
            plan["database_scaling"]["sharding"] = True
        
        # Architecture-specific scaling
        if architecture.pattern == ArchitecturePattern.MICROSERVICES:
            plan["microservices_scaling"] = {
                "independent_scaling": True,
                "service_mesh": True,
                "circuit_breakers": True
            }
        
        return plan
    
    def _initialize_technology_database(self) -> Dict[str, Any]:
        """Initialize technology recommendation database."""
        # This would typically be loaded from a database or configuration
        return {
            "ai_frameworks": {
                "pytorch": {"complexity": "high", "learning_curve": "high"},
                "tensorflow": {"complexity": "medium", "learning_curve": "medium"},
                "scikit_learn": {"complexity": "low", "learning_curve": "low"}
            },
            "databases": {
                "postgresql": {"complexity": "medium", "use_cases": ["relational", "json"]},
                "mongodb": {"complexity": "low", "use_cases": ["document", "flexible_schema"]},
                "redis": {"complexity": "low", "use_cases": ["cache", "session"]}
            }
        }
    
    def _initialize_architecture_patterns(self) -> Dict[str, Any]:
        """Initialize architecture pattern database."""
        return {
            "microservices": {"complexity": "high", "scalability": 9, "maintenance": 5},
            "monolithic": {"complexity": "low", "scalability": 4, "maintenance": 7},
            "serverless": {"complexity": "medium", "scalability": 8, "maintenance": 8}
        }


# Singleton instance
technical_roadmap_service = TechnicalRoadmapService()