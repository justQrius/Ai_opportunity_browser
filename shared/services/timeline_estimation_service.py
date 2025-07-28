"""
Timeline Estimation Service for AI Opportunity Browser.

Implements Phase 7.2.2 requirements:
- Development timeline algorithms
- Resource requirement analysis  
- Risk-adjusted scheduling
- Team composition optimization

Provides advanced timeline estimation capabilities including Monte Carlo simulation,
critical path analysis, and resource-based scheduling for AI opportunity implementation.
"""

import asyncio
import json
import logging
import math
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from shared.models.opportunity import Opportunity
from shared.models.market_signal import MarketSignal
from shared.services.technical_roadmap_service import (
    TechnicalRoadmap, ComplexityLevel, ImplementationPhase,
    TechnologyRecommendation, ArchitectureRecommendation
)
from shared.services.business_intelligence_service import MarketAnalysisResult

logger = logging.getLogger(__name__)


class EstimationMethod(Enum):
    """Timeline estimation methods."""
    FUNCTION_POINT = "function_point"
    STORY_POINT = "story_point"
    EXPERT_JUDGMENT = "expert_judgment"
    HISTORICAL_DATA = "historical_data"
    MONTE_CARLO = "monte_carlo"
    PARAMETRIC = "parametric"


class ResourceType(Enum):
    """Types of development resources."""
    AI_ML_ENGINEER = "ai_ml_engineer"
    BACKEND_DEVELOPER = "backend_developer"
    FRONTEND_DEVELOPER = "frontend_developer"
    DEVOPS_ENGINEER = "devops_engineer"
    DATA_SCIENTIST = "data_scientist"
    PRODUCT_MANAGER = "product_manager"
    UX_DESIGNER = "ux_designer"
    QA_ENGINEER = "qa_engineer"
    SECURITY_ENGINEER = "security_engineer"
    TECHNICAL_WRITER = "technical_writer"


class RiskCategory(Enum):
    """Risk categories affecting timeline."""
    TECHNICAL = "technical"
    RESOURCE = "resource"
    EXTERNAL = "external"
    SCOPE = "scope"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"


@dataclass
class ResourceRequirement:
    """Resource requirement specification."""
    resource_type: ResourceType
    required_hours: int
    skill_level: str  # junior, mid, senior, expert
    parallel_capacity: int  # max parallel resources
    availability_constraint: float  # 0.0-1.0, availability factor
    hourly_rate_usd: float
    critical_path: bool  # whether this resource is on critical path
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['resource_type'] = self.resource_type.value
        return result


@dataclass
class TimelineRisk:
    """Timeline risk assessment."""
    risk_id: str
    category: RiskCategory
    description: str
    probability: float  # 0.0-1.0
    impact_days: int  # potential delay in days
    mitigation_strategy: str
    mitigation_cost_usd: float
    detection_indicators: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['category'] = self.category.value
        return result


@dataclass
class TaskEstimate:
    """Individual task estimation."""
    task_id: str
    name: str
    description: str
    estimated_hours: int
    optimistic_hours: int
    pessimistic_hours: int
    confidence_level: float  # 0.0-1.0
    dependencies: List[str]  # task IDs
    required_resources: List[ResourceType]
    complexity_factors: Dict[str, float]
    historical_velocity: Optional[float]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['required_resources'] = [r.value for r in self.required_resources]
        return result


@dataclass
class MonteCarloSimulation:
    """Monte Carlo simulation results."""
    simulation_id: str
    iterations: int
    confidence_intervals: Dict[str, Tuple[int, int]]  # 50%, 75%, 90%, 95%
    mean_duration_days: float
    median_duration_days: float
    std_deviation_days: float
    risk_scenarios: List[Dict[str, Any]]
    critical_path_analysis: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResourceAllocation:
    """Resource allocation plan."""
    allocation_id: str
    resource_requirements: List[ResourceRequirement]
    team_composition: Dict[ResourceType, int]
    estimated_cost_total: float
    estimated_cost_monthly: float
    resource_conflicts: List[Dict[str, Any]]
    optimization_recommendations: List[str]
    scaling_strategy: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['resource_requirements'] = [req.to_dict() for req in self.resource_requirements]
        result['team_composition'] = {k.value: v for k, v in self.team_composition.items()}
        return result


@dataclass
class TimelineEstimate:
    """Comprehensive timeline estimation."""
    estimate_id: str
    opportunity_id: str
    generated_at: datetime
    estimation_method: EstimationMethod
    total_duration_days: int
    confidence_level: float
    task_estimates: List[TaskEstimate]
    resource_allocation: ResourceAllocation
    timeline_risks: List[TimelineRisk]
    monte_carlo_simulation: Optional[MonteCarloSimulation]
    critical_path: List[str]  # task IDs on critical path
    milestone_dates: Dict[str, datetime]
    buffer_recommendations: Dict[str, int]  # phase -> buffer days
    cost_analysis: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['generated_at'] = self.generated_at.isoformat()
        result['estimation_method'] = self.estimation_method.value
        result['task_estimates'] = [task.to_dict() for task in self.task_estimates]
        result['resource_allocation'] = self.resource_allocation.to_dict()
        result['timeline_risks'] = [risk.to_dict() for risk in self.timeline_risks]
        result['monte_carlo_simulation'] = self.monte_carlo_simulation.to_dict() if self.monte_carlo_simulation else None
        result['milestone_dates'] = {k: v.isoformat() for k, v in self.milestone_dates.items()}
        return result


class TimelineEstimationService:
    """Service for advanced timeline estimation and resource planning."""
    
    def __init__(self):
        self.historical_velocity_data = self._initialize_velocity_data()
        self.resource_rates = self._initialize_resource_rates()
        self.complexity_factors = self._initialize_complexity_factors()
    
    async def generate_timeline_estimate(
        self,
        db: AsyncSession,
        opportunity: Opportunity,
        technical_roadmap: TechnicalRoadmap,
        market_analysis: Optional[MarketAnalysisResult] = None,
        estimation_method: EstimationMethod = EstimationMethod.MONTE_CARLO
    ) -> TimelineEstimate:
        """Generate comprehensive timeline estimate.
        
        Args:
            db: Database session
            opportunity: Target opportunity
            technical_roadmap: Technical roadmap for implementation
            market_analysis: Market analysis for context
            estimation_method: Estimation methodology to use
            
        Returns:
            TimelineEstimate with comprehensive scheduling analysis
        """
        logger.info(f"Generating timeline estimate for opportunity {opportunity.id}")
        
        # Break down technical roadmap into detailed tasks
        task_estimates = await self._create_detailed_task_estimates(
            opportunity, technical_roadmap, estimation_method
        )
        
        # Analyze resource requirements
        resource_allocation = await self._analyze_resource_requirements(
            task_estimates, technical_roadmap, market_analysis
        )
        
        # Identify timeline risks
        timeline_risks = await self._identify_timeline_risks(
            opportunity, technical_roadmap, task_estimates
        )
        
        # Perform critical path analysis
        critical_path = await self._analyze_critical_path(task_estimates)
        
        # Run Monte Carlo simulation if requested
        monte_carlo = None
        if estimation_method == EstimationMethod.MONTE_CARLO:
            monte_carlo = await self._run_monte_carlo_simulation(
                task_estimates, timeline_risks, critical_path
            )
        
        # Calculate total duration and confidence
        total_duration, confidence = await self._calculate_total_duration(
            task_estimates, critical_path, timeline_risks, monte_carlo
        )
        
        # Generate milestone dates
        milestone_dates = await self._generate_milestone_dates(
            task_estimates, critical_path, total_duration
        )
        
        # Recommend buffers
        buffer_recommendations = await self._recommend_buffers(
            technical_roadmap, timeline_risks, confidence
        )
        
        # Cost analysis
        cost_analysis = await self._analyze_costs(
            resource_allocation, total_duration, timeline_risks
        )
        
        return TimelineEstimate(
            estimate_id=f"timeline_{opportunity.id}",
            opportunity_id=str(opportunity.id),
            generated_at=datetime.utcnow(),
            estimation_method=estimation_method,
            total_duration_days=total_duration,
            confidence_level=confidence,
            task_estimates=task_estimates,
            resource_allocation=resource_allocation,
            timeline_risks=timeline_risks,
            monte_carlo_simulation=monte_carlo,
            critical_path=critical_path,
            milestone_dates=milestone_dates,
            buffer_recommendations=buffer_recommendations,
            cost_analysis=cost_analysis
        )
    
    async def _create_detailed_task_estimates(
        self,
        opportunity: Opportunity,
        technical_roadmap: TechnicalRoadmap,
        method: EstimationMethod
    ) -> List[TaskEstimate]:
        """Create detailed task estimates from technical roadmap."""
        tasks = []
        
        for phase_idx, phase in enumerate(technical_roadmap.implementation_phases):
            # Break down each phase into detailed tasks
            phase_tasks = await self._decompose_phase_into_tasks(
                phase, technical_roadmap, opportunity, phase_idx
            )
            
            for task_data in phase_tasks:
                # Apply estimation method
                if method == EstimationMethod.FUNCTION_POINT:
                    estimate = await self._estimate_with_function_points(task_data, technical_roadmap)
                elif method == EstimationMethod.STORY_POINT:
                    estimate = await self._estimate_with_story_points(task_data, technical_roadmap)
                elif method == EstimationMethod.HISTORICAL_DATA:
                    estimate = await self._estimate_with_historical_data(task_data, technical_roadmap)
                else:
                    estimate = await self._estimate_with_expert_judgment(task_data, technical_roadmap)
                
                # Calculate confidence based on complexity and historical data
                confidence = self._calculate_task_confidence(task_data, technical_roadmap, method)
                
                # Identify dependencies
                dependencies = self._identify_task_dependencies(task_data, tasks, phase_idx)
                
                task_estimate = TaskEstimate(
                    task_id=task_data["id"],
                    name=task_data["name"],
                    description=task_data["description"],
                    estimated_hours=estimate["nominal"],
                    optimistic_hours=estimate["optimistic"],
                    pessimistic_hours=estimate["pessimistic"],
                    confidence_level=confidence,
                    dependencies=dependencies,
                    required_resources=task_data["required_resources"],
                    complexity_factors=task_data["complexity_factors"],
                    historical_velocity=self._get_historical_velocity(task_data["type"])
                )
                
                tasks.append(task_estimate)
        
        return tasks
    
    async def _decompose_phase_into_tasks(
        self,
        phase: Any,  # ImplementationPhaseDetail
        technical_roadmap: TechnicalRoadmap,
        opportunity: Opportunity,
        phase_idx: int
    ) -> List[Dict[str, Any]]:
        """Decompose implementation phase into detailed tasks."""
        tasks = []
        phase_name = phase.phase.value
        
        # Define task templates based on phase type and complexity
        task_templates = self._get_task_templates(phase_name, technical_roadmap.overall_complexity)
        
        for template in task_templates:
            # Customize task based on opportunity and technical requirements
            task = {
                "id": f"{phase_name}_{template['id']}_{phase_idx}",
                "name": template["name"],
                "description": template["description"],
                "type": template["type"],
                "required_resources": template["required_resources"],
                "base_hours": template.get("base_hours", 40),  # Default to 40 hours if not specified
                "complexity_factors": self._calculate_task_complexity_factors(
                    template, technical_roadmap, opportunity
                ),
                "phase": phase_name,
                "deliverables": template.get("deliverables", []),
                "acceptance_criteria": template.get("acceptance_criteria", [])
            }
            tasks.append(task)
        
        return tasks
    
    def _get_task_templates(self, phase_name: str, complexity: ComplexityLevel) -> List[Dict[str, Any]]:
        """Get task templates for a specific phase."""
        templates = {
            "research_poc": [
                {
                    "id": "requirements_analysis",
                    "name": "Requirements Analysis and Specification",
                    "description": "Analyze and document detailed technical requirements",
                    "type": "analysis",
                    "required_resources": [ResourceType.PRODUCT_MANAGER, ResourceType.AI_ML_ENGINEER],
                    "base_hours": 40,
                    "deliverables": ["Requirements document", "Technical specifications"]
                },
                {
                    "id": "architecture_design",
                    "name": "System Architecture Design",
                    "description": "Design overall system architecture and component interactions",
                    "type": "design",
                    "required_resources": [ResourceType.AI_ML_ENGINEER, ResourceType.BACKEND_DEVELOPER],
                    "base_hours": 60,
                    "deliverables": ["Architecture diagrams", "Technology selection document"]
                },
                {
                    "id": "ai_model_prototype",
                    "name": "AI Model Prototype Development",
                    "description": "Develop and train initial AI model prototype",
                    "type": "ai_development",
                    "required_resources": [ResourceType.AI_ML_ENGINEER, ResourceType.DATA_SCIENTIST],
                    "base_hours": 120,
                    "deliverables": ["Prototype model", "Performance benchmarks"]
                },
                {
                    "id": "data_pipeline_poc",
                    "name": "Data Pipeline Proof of Concept",
                    "description": "Build initial data ingestion and processing pipeline",
                    "type": "data_engineering",
                    "required_resources": [ResourceType.DATA_SCIENTIST, ResourceType.BACKEND_DEVELOPER],
                    "base_hours": 80,
                    "deliverables": ["Data pipeline prototype", "Data quality metrics"]
                },
                {
                    "id": "technology_validation",
                    "name": "Technology Stack Validation",
                    "description": "Validate chosen technologies and integration approaches",
                    "type": "validation",
                    "required_resources": [ResourceType.AI_ML_ENGINEER, ResourceType.DEVOPS_ENGINEER],
                    "base_hours": 40,
                    "deliverables": ["Technology validation report", "Integration test results"]
                }
            ],
            "mvp_development": [
                {
                    "id": "backend_development",
                    "name": "Backend API Development",
                    "description": "Develop core backend APIs and business logic",
                    "type": "backend_development",
                    "required_resources": [ResourceType.BACKEND_DEVELOPER, ResourceType.AI_ML_ENGINEER],
                    "base_hours": 200,
                    "deliverables": ["API endpoints", "Business logic implementation"]
                },
                {
                    "id": "ai_model_integration",
                    "name": "AI Model Integration",
                    "description": "Integrate AI models into production-ready pipeline",
                    "type": "ai_integration",
                    "required_resources": [ResourceType.AI_ML_ENGINEER, ResourceType.DATA_SCIENTIST],
                    "base_hours": 160,
                    "deliverables": ["Integrated AI pipeline", "Model serving infrastructure"]
                },
                {
                    "id": "database_implementation",
                    "name": "Database Schema and Implementation",
                    "description": "Implement database schema and data access layer",
                    "type": "database_development",
                    "required_resources": [ResourceType.BACKEND_DEVELOPER],
                    "base_hours": 80,
                    "deliverables": ["Database schema", "Data access layer"]
                },
                {
                    "id": "frontend_development",
                    "name": "User Interface Development",
                    "description": "Develop user interface and user experience",
                    "type": "frontend_development",
                    "required_resources": [ResourceType.FRONTEND_DEVELOPER, ResourceType.UX_DESIGNER],
                    "base_hours": 180,
                    "deliverables": ["User interface", "UX workflows"]
                },
                {
                    "id": "authentication_security",
                    "name": "Authentication and Security Implementation",
                    "description": "Implement user authentication and basic security measures",
                    "type": "security_development",
                    "required_resources": [ResourceType.BACKEND_DEVELOPER, ResourceType.SECURITY_ENGINEER],
                    "base_hours": 60,
                    "deliverables": ["Authentication system", "Security measures"]
                },
                {
                    "id": "api_documentation",
                    "name": "API Documentation and Testing",
                    "description": "Create API documentation and automated tests",
                    "type": "documentation",
                    "required_resources": [ResourceType.TECHNICAL_WRITER, ResourceType.QA_ENGINEER],
                    "base_hours": 40,
                    "deliverables": ["API documentation", "Test suites"]
                }
            ],
            "beta_testing": [
                {
                    "id": "test_environment_setup",
                    "name": "Beta Test Environment Setup",
                    "description": "Set up staging environment for beta testing",
                    "type": "devops",
                    "required_resources": [ResourceType.DEVOPS_ENGINEER],
                    "base_hours": 40,
                    "deliverables": ["Staging environment", "Deployment pipeline"]
                },
                {
                    "id": "beta_user_onboarding",
                    "name": "Beta User Recruitment and Onboarding",
                    "description": "Recruit beta users and create onboarding materials",
                    "type": "product_management",
                    "required_resources": [ResourceType.PRODUCT_MANAGER, ResourceType.TECHNICAL_WRITER],
                    "base_hours": 60,
                    "deliverables": ["Beta user program", "Onboarding materials"]
                },
                {
                    "id": "performance_optimization",
                    "name": "Performance Testing and Optimization",
                    "description": "Test system performance and optimize bottlenecks",
                    "type": "performance",
                    "required_resources": [ResourceType.BACKEND_DEVELOPER, ResourceType.AI_ML_ENGINEER],
                    "base_hours": 80,
                    "deliverables": ["Performance test results", "Optimization improvements"]
                },
                {
                    "id": "feedback_integration",
                    "name": "User Feedback Collection and Integration",
                    "description": "Collect user feedback and implement improvements",
                    "type": "product_iteration",
                    "required_resources": [ResourceType.PRODUCT_MANAGER, ResourceType.UX_DESIGNER],
                    "base_hours": 100,
                    "deliverables": ["Feedback analysis", "Product improvements"]
                },
                {
                    "id": "security_audit",
                    "name": "Security Audit and Penetration Testing",
                    "description": "Conduct security audit and address vulnerabilities",
                    "type": "security_testing",
                    "required_resources": [ResourceType.SECURITY_ENGINEER, ResourceType.QA_ENGINEER],
                    "base_hours": 60,
                    "deliverables": ["Security audit report", "Vulnerability fixes"]
                }
            ],
            "production_launch": [
                {
                    "id": "production_environment",
                    "name": "Production Environment Setup",
                    "description": "Set up and configure production infrastructure",
                    "type": "devops",
                    "required_resources": [ResourceType.DEVOPS_ENGINEER],
                    "base_hours": 60,
                    "deliverables": ["Production environment", "Infrastructure monitoring"]
                },
                {
                    "id": "deployment_automation",
                    "name": "Deployment Pipeline Automation",
                    "description": "Automate deployment and rollback procedures",
                    "type": "devops",
                    "required_resources": [ResourceType.DEVOPS_ENGINEER, ResourceType.BACKEND_DEVELOPER],
                    "base_hours": 40,
                    "deliverables": ["CI/CD pipeline", "Automated deployments"]
                },
                {
                    "id": "monitoring_alerting",
                    "name": "Monitoring and Alerting Setup",
                    "description": "Implement comprehensive monitoring and alerting",
                    "type": "devops",
                    "required_resources": [ResourceType.DEVOPS_ENGINEER, ResourceType.AI_ML_ENGINEER],
                    "base_hours": 50,
                    "deliverables": ["Monitoring dashboard", "Alert configurations"]
                },
                {
                    "id": "launch_coordination",
                    "name": "Launch Coordination and Marketing",
                    "description": "Coordinate product launch and marketing activities",
                    "type": "product_management",
                    "required_resources": [ResourceType.PRODUCT_MANAGER],
                    "base_hours": 40,
                    "deliverables": ["Launch plan", "Marketing materials"]
                },
                {
                    "id": "support_documentation",
                    "name": "User Support and Documentation",
                    "description": "Create user documentation and support processes",
                    "type": "documentation",
                    "required_resources": [ResourceType.TECHNICAL_WRITER, ResourceType.PRODUCT_MANAGER],
                    "base_hours": 60,
                    "deliverables": ["User documentation", "Support processes"]
                }
            ],
            "scale_optimization": [
                {
                    "id": "performance_scaling",
                    "name": "Performance Scaling and Optimization",
                    "description": "Optimize system for increased load and performance",
                    "type": "optimization",
                    "required_resources": [ResourceType.BACKEND_DEVELOPER, ResourceType.AI_ML_ENGINEER],
                    "base_hours": 120,
                    "deliverables": ["Scaling improvements", "Performance benchmarks"]
                },
                {
                    "id": "advanced_ai_features",
                    "name": "Advanced AI Features Development",
                    "description": "Develop advanced AI capabilities and features",
                    "type": "ai_development",
                    "required_resources": [ResourceType.AI_ML_ENGINEER, ResourceType.DATA_SCIENTIST],
                    "base_hours": 200,
                    "deliverables": ["Advanced AI features", "Model improvements"]
                },
                {
                    "id": "enterprise_features",
                    "name": "Enterprise Feature Development",
                    "description": "Develop enterprise-grade features and integrations",
                    "type": "enterprise_development",
                    "required_resources": [ResourceType.BACKEND_DEVELOPER, ResourceType.SECURITY_ENGINEER],
                    "base_hours": 150,
                    "deliverables": ["Enterprise features", "Integration APIs"]
                },
                {
                    "id": "analytics_reporting",
                    "name": "Advanced Analytics and Reporting",
                    "description": "Implement comprehensive analytics and reporting",
                    "type": "analytics_development",
                    "required_resources": [ResourceType.DATA_SCIENTIST, ResourceType.FRONTEND_DEVELOPER],
                    "base_hours": 100,
                    "deliverables": ["Analytics platform", "Reporting dashboard"]
                }
            ]
        }
        
        base_templates = templates.get(phase_name, [])
        
        # Adjust task complexity based on overall complexity
        complexity_multipliers = {
            ComplexityLevel.LOW: 0.8,
            ComplexityLevel.MEDIUM: 1.0,
            ComplexityLevel.HIGH: 1.4,
            ComplexityLevel.VERY_HIGH: 1.8
        }
        
        multiplier = complexity_multipliers[complexity]
        
        for template in base_templates:
            template["base_hours"] = int(template["base_hours"] * multiplier)
        
        return base_templates
    
    def _calculate_task_complexity_factors(
        self,
        template: Dict[str, Any],
        technical_roadmap: TechnicalRoadmap,
        opportunity: Opportunity
    ) -> Dict[str, float]:
        """Calculate complexity factors for a task."""
        factors = {
            "technical_complexity": 1.0,
            "integration_complexity": 1.0,
            "ai_complexity": 1.0,
            "data_complexity": 1.0,
            "ui_complexity": 1.0,
            "security_complexity": 1.0
        }
        
        # Technical complexity based on architecture
        if technical_roadmap.architecture_recommendation.pattern.value == "microservices":
            factors["technical_complexity"] *= 1.3
            factors["integration_complexity"] *= 1.5
        elif technical_roadmap.architecture_recommendation.pattern.value == "serverless":
            factors["technical_complexity"] *= 1.2
        
        # AI complexity based on solution types
        if opportunity.ai_solution_types:
            try:
                ai_types = json.loads(opportunity.ai_solution_types) if isinstance(opportunity.ai_solution_types, str) else opportunity.ai_solution_types
                ai_complexity_base = len(ai_types) * 0.2 + 0.8  # Base + scaling
                
                # Advanced AI increases complexity
                advanced_types = ["transformer", "gpt", "bert", "neural", "deep_learning"]
                if any(adv in str(ai_types).lower() for adv in advanced_types):
                    ai_complexity_base *= 1.5
                
                factors["ai_complexity"] = ai_complexity_base
                
                # AI tasks get higher AI complexity
                if template["type"] in ["ai_development", "ai_integration"]:
                    factors["ai_complexity"] *= 1.3
                    
            except:
                factors["ai_complexity"] = 1.2
        
        # Data complexity based on requirements
        if opportunity.description and any(word in opportunity.description.lower() for word in ["big data", "real-time", "streaming"]):
            factors["data_complexity"] *= 1.4
        
        # UI complexity based on task type
        if template["type"] == "frontend_development":
            factors["ui_complexity"] *= 1.3
        
        # Security complexity for regulated industries
        if opportunity.target_industries:
            try:
                industries = json.loads(opportunity.target_industries) if isinstance(opportunity.target_industries, str) else opportunity.target_industries
                regulated_industries = ["finance", "healthcare", "legal", "government"]
                if any(industry.lower() in regulated_industries for industry in industries):
                    factors["security_complexity"] *= 1.6
                    if template["type"] in ["security_development", "security_testing"]:
                        factors["security_complexity"] *= 1.3
            except:
                pass
        
        return factors
    
    async def _estimate_with_function_points(
        self,
        task_data: Dict[str, Any],
        technical_roadmap: TechnicalRoadmap
    ) -> Dict[str, int]:
        """Estimate task using function point analysis."""
        base_hours = task_data["base_hours"]
        complexity_factors = task_data["complexity_factors"]
        
        # Apply complexity multipliers
        total_multiplier = 1.0
        for factor_value in complexity_factors.values():
            total_multiplier *= factor_value
        
        nominal = int(base_hours * total_multiplier)
        
        # Function point method typically has ±25% variance
        optimistic = int(nominal * 0.75)
        pessimistic = int(nominal * 1.25)
        
        return {
            "nominal": nominal,
            "optimistic": optimistic,
            "pessimistic": pessimistic
        }
    
    async def _estimate_with_story_points(
        self,
        task_data: Dict[str, Any],
        technical_roadmap: TechnicalRoadmap
    ) -> Dict[str, int]:
        """Estimate task using story point methodology."""
        base_hours = task_data["base_hours"]
        
        # Convert to story points (assuming 1 story point = 8 hours for experienced team)
        story_points = base_hours / 8
        
        # Apply Fibonacci scaling for story points
        fibonacci_points = self._round_to_fibonacci(story_points)
        
        # Convert back to hours with team velocity
        team_velocity = self._estimate_team_velocity(technical_roadmap.overall_complexity)
        hours_per_point = 8 / team_velocity  # Adjust for team experience
        
        nominal = int(fibonacci_points * hours_per_point)
        optimistic = int(nominal * 0.7)
        pessimistic = int(nominal * 1.5)
        
        return {
            "nominal": nominal,
            "optimistic": optimistic,
            "pessimistic": pessimistic
        }
    
    async def _estimate_with_historical_data(
        self,
        task_data: Dict[str, Any],
        technical_roadmap: TechnicalRoadmap
    ) -> Dict[str, int]:
        """Estimate task using historical data."""
        task_type = task_data["type"]
        historical_velocity = self._get_historical_velocity(task_type)
        
        if historical_velocity:
            base_hours = task_data["base_hours"]
            adjusted_hours = int(base_hours / historical_velocity)
            
            # Historical data typically has better accuracy
            optimistic = int(adjusted_hours * 0.85)
            pessimistic = int(adjusted_hours * 1.15)
            
            return {
                "nominal": adjusted_hours,
                "optimistic": optimistic,
                "pessimistic": pessimistic
            }
        else:
            # Fall back to expert judgment
            return await self._estimate_with_expert_judgment(task_data, technical_roadmap)
    
    async def _estimate_with_expert_judgment(
        self,
        task_data: Dict[str, Any],
        technical_roadmap: TechnicalRoadmap
    ) -> Dict[str, int]:
        """Estimate task using expert judgment (PERT-like)."""
        base_hours = task_data["base_hours"]
        complexity_factors = task_data["complexity_factors"]
        
        # Apply complexity adjustments
        complexity_multiplier = statistics.mean(complexity_factors.values())
        adjusted_hours = int(base_hours * complexity_multiplier)
        
        # Expert judgment typically uses wider variance
        optimistic = int(adjusted_hours * 0.6)
        pessimistic = int(adjusted_hours * 1.8)
        
        # PERT formula: (optimistic + 4*nominal + pessimistic) / 6
        nominal = int((optimistic + 4 * adjusted_hours + pessimistic) / 6)
        
        return {
            "nominal": nominal,
            "optimistic": optimistic,
            "pessimistic": pessimistic
        }
    
    def _round_to_fibonacci(self, value: float) -> int:
        """Round value to nearest Fibonacci number."""
        fibonacci_sequence = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
        return min(fibonacci_sequence, key=lambda x: abs(x - value))
    
    def _estimate_team_velocity(self, complexity: ComplexityLevel) -> float:
        """Estimate team velocity factor based on complexity."""
        velocity_factors = {
            ComplexityLevel.LOW: 1.2,      # Experienced with simple tasks
            ComplexityLevel.MEDIUM: 1.0,   # Standard velocity
            ComplexityLevel.HIGH: 0.8,     # Slower due to complexity
            ComplexityLevel.VERY_HIGH: 0.6 # Much slower for very complex tasks
        }
        return velocity_factors[complexity]
    
    def _get_historical_velocity(self, task_type: str) -> Optional[float]:
        """Get historical velocity for task type."""
        return self.historical_velocity_data.get(task_type)
    
    def _calculate_task_confidence(
        self,
        task_data: Dict[str, Any],
        technical_roadmap: TechnicalRoadmap,
        method: EstimationMethod
    ) -> float:
        """Calculate confidence level for task estimate."""
        base_confidence = 0.7
        
        # Method-based confidence
        method_confidence = {
            EstimationMethod.HISTORICAL_DATA: 0.9,
            EstimationMethod.FUNCTION_POINT: 0.8,
            EstimationMethod.STORY_POINT: 0.75,
            EstimationMethod.EXPERT_JUDGMENT: 0.7,
            EstimationMethod.PARAMETRIC: 0.75,
            EstimationMethod.MONTE_CARLO: 0.85
        }
        base_confidence = method_confidence[method]
        
        # Adjust for complexity
        complexity_factors = task_data["complexity_factors"]
        avg_complexity = statistics.mean(complexity_factors.values())
        
        if avg_complexity > 1.5:
            base_confidence *= 0.8
        elif avg_complexity > 1.2:
            base_confidence *= 0.9
        
        # Adjust for task type familiarity
        familiar_tasks = ["backend_development", "frontend_development", "documentation"]
        if task_data["type"] in familiar_tasks:
            base_confidence *= 1.1
        
        complex_tasks = ["ai_development", "ai_integration", "security_development"]
        if task_data["type"] in complex_tasks:
            base_confidence *= 0.9
        
        return min(0.95, max(0.5, base_confidence))
    
    def _identify_task_dependencies(
        self,
        task_data: Dict[str, Any],
        existing_tasks: List[TaskEstimate],
        phase_idx: int
    ) -> List[str]:
        """Identify task dependencies."""
        dependencies = []
        
        # Phase-based dependencies
        if phase_idx > 0:
            # Tasks depend on completion of previous phase
            prev_phase_tasks = [t for t in existing_tasks if t.task_id.split('_')[-1] == str(phase_idx - 1)]
            if prev_phase_tasks:
                dependencies.extend([t.task_id for t in prev_phase_tasks[-2:]])  # Last 2 tasks of previous phase
        
        # Task type dependencies within same phase
        current_phase_tasks = [t for t in existing_tasks if t.task_id.split('_')[-1] == str(phase_idx)]
        
        dependency_rules = {
            "backend_development": ["requirements_analysis", "architecture_design"],
            "frontend_development": ["backend_development", "api_documentation"],
            "ai_model_integration": ["ai_model_prototype", "backend_development"],
            "performance_optimization": ["backend_development", "ai_model_integration"],
            "security_audit": ["backend_development", "authentication_security"],
            "deployment_automation": ["backend_development", "test_environment_setup"],
            "monitoring_alerting": ["production_environment", "deployment_automation"]
        }
        
        task_type = task_data["type"]
        required_predecessors = dependency_rules.get(task_type, [])
        
        for predecessor_type in required_predecessors:
            predecessor_tasks = [t for t in current_phase_tasks if predecessor_type in t.task_id]
            if predecessor_tasks:
                dependencies.extend([t.task_id for t in predecessor_tasks])
        
        return list(set(dependencies))  # Remove duplicates
    
    async def _analyze_resource_requirements(
        self,
        task_estimates: List[TaskEstimate],
        technical_roadmap: TechnicalRoadmap,
        market_analysis: Optional[MarketAnalysisResult]
    ) -> ResourceAllocation:
        """Analyze resource requirements and create allocation plan."""
        
        # Aggregate resource requirements by type
        resource_hours = {}
        for task in task_estimates:
            for resource_type in task.required_resources:
                if resource_type not in resource_hours:
                    resource_hours[resource_type] = 0
                resource_hours[resource_type] += task.estimated_hours
        
        # Create detailed resource requirements
        resource_requirements = []
        total_cost = 0
        
        for resource_type, hours in resource_hours.items():
            # Determine skill level needed
            skill_level = self._determine_required_skill_level(resource_type, technical_roadmap)
            
            # Get hourly rate
            rate = self.resource_rates[resource_type][skill_level]
            
            # Calculate parallel capacity and availability
            parallel_capacity = self._calculate_parallel_capacity(resource_type, hours)
            availability = self._estimate_resource_availability(resource_type, market_analysis)
            
            # Check if on critical path
            critical_path_tasks = [t for t in task_estimates if resource_type in t.required_resources]
            is_critical = len(critical_path_tasks) > len(task_estimates) * 0.3  # More than 30% of tasks
            
            requirement = ResourceRequirement(
                resource_type=resource_type,
                required_hours=hours,
                skill_level=skill_level,
                parallel_capacity=parallel_capacity,
                availability_constraint=availability,
                hourly_rate_usd=rate,
                critical_path=is_critical
            )
            
            resource_requirements.append(requirement)
            total_cost += hours * rate
        
        # Calculate team composition
        team_composition = self._calculate_optimal_team_composition(
            resource_requirements, technical_roadmap
        )
        
        # Estimate monthly cost
        total_duration_months = technical_roadmap.estimated_timeline_weeks / 4.33
        monthly_cost = total_cost / total_duration_months if total_duration_months > 0 else total_cost
        
        # Identify resource conflicts
        conflicts = self._identify_resource_conflicts(resource_requirements, task_estimates)
        
        # Generate optimization recommendations
        optimizations = self._generate_resource_optimizations(
            resource_requirements, team_composition, conflicts
        )
        
        # Create scaling strategy
        scaling_strategy = self._create_resource_scaling_strategy(
            resource_requirements, technical_roadmap, market_analysis
        )
        
        return ResourceAllocation(
            allocation_id=f"allocation_{technical_roadmap.opportunity_id}",
            resource_requirements=resource_requirements,
            team_composition=team_composition,
            estimated_cost_total=total_cost,
            estimated_cost_monthly=monthly_cost,
            resource_conflicts=conflicts,
            optimization_recommendations=optimizations,
            scaling_strategy=scaling_strategy
        )
    
    def _determine_required_skill_level(self, resource_type: ResourceType, technical_roadmap: TechnicalRoadmap) -> str:
        """Determine required skill level for resource type."""
        complexity = technical_roadmap.overall_complexity
        
        # Base skill requirements by complexity
        complexity_skill_map = {
            ComplexityLevel.LOW: "mid",
            ComplexityLevel.MEDIUM: "mid",
            ComplexityLevel.HIGH: "senior",
            ComplexityLevel.VERY_HIGH: "expert"
        }
        
        base_skill = complexity_skill_map[complexity]
        
        # Adjust for specific resource types
        if resource_type in [ResourceType.AI_ML_ENGINEER, ResourceType.DATA_SCIENTIST]:
            # AI roles typically need higher skill levels
            if base_skill == "mid":
                return "senior"
            elif base_skill == "senior":
                return "expert"
        
        return base_skill
    
    def _calculate_parallel_capacity(self, resource_type: ResourceType, total_hours: int) -> int:
        """Calculate maximum parallel resources for given type."""
        # Base parallel capacity by resource type
        base_capacity = {
            ResourceType.AI_ML_ENGINEER: 2,
            ResourceType.BACKEND_DEVELOPER: 3,
            ResourceType.FRONTEND_DEVELOPER: 2,
            ResourceType.DATA_SCIENTIST: 2,
            ResourceType.DEVOPS_ENGINEER: 1,
            ResourceType.QA_ENGINEER: 2,
            ResourceType.SECURITY_ENGINEER: 1,
            ResourceType.PRODUCT_MANAGER: 1,
            ResourceType.UX_DESIGNER: 1,
            ResourceType.TECHNICAL_WRITER: 1
        }
        
        capacity = base_capacity.get(resource_type, 2)
        
        # Scale capacity based on total work
        if total_hours > 800:  # More than 5 person-months
            capacity += 1
        if total_hours > 1600:  # More than 10 person-months
            capacity += 1
        
        return min(capacity, 5)  # Cap at 5 parallel resources
    
    def _estimate_resource_availability(
        self,
        resource_type: ResourceType,
        market_analysis: Optional[MarketAnalysisResult]
    ) -> float:
        """Estimate resource availability constraint."""
        # Base availability by resource type (scarcity factor)
        base_availability = {
            ResourceType.AI_ML_ENGINEER: 0.7,      # High demand, lower availability
            ResourceType.DATA_SCIENTIST: 0.8,
            ResourceType.SECURITY_ENGINEER: 0.75,
            ResourceType.DEVOPS_ENGINEER: 0.85,
            ResourceType.BACKEND_DEVELOPER: 0.9,
            ResourceType.FRONTEND_DEVELOPER: 0.9,
            ResourceType.QA_ENGINEER: 0.95,
            ResourceType.PRODUCT_MANAGER: 0.85,
            ResourceType.UX_DESIGNER: 0.9,
            ResourceType.TECHNICAL_WRITER: 0.95
        }
        
        availability = base_availability.get(resource_type, 0.9)
        
        # Adjust based on market opportunity size
        if market_analysis and market_analysis.serviceable_addressable_market > 100000000:
            # Large market opportunities can attract talent easier
            availability += 0.1
        
        return min(1.0, availability)
    
    def _calculate_optimal_team_composition(
        self,
        resource_requirements: List[ResourceRequirement],
        technical_roadmap: TechnicalRoadmap
    ) -> Dict[ResourceType, int]:
        """Calculate optimal team composition."""
        composition = {}
        
        for req in resource_requirements:
            # Calculate FTE needed
            total_weeks = technical_roadmap.estimated_timeline_weeks
            hours_per_week = 40
            
            # Adjust for availability constraint
            adjusted_hours = req.required_hours / req.availability_constraint
            
            # Calculate FTE
            fte_needed = adjusted_hours / (total_weeks * hours_per_week)
            
            # Round up to whole persons, considering parallel capacity
            team_size = min(math.ceil(fte_needed), req.parallel_capacity)
            team_size = max(1, team_size)  # Minimum 1 person
            
            composition[req.resource_type] = team_size
        
        return composition
    
    def _identify_resource_conflicts(
        self,
        resource_requirements: List[ResourceRequirement],
        task_estimates: List[TaskEstimate]
    ) -> List[Dict[str, Any]]:
        """Identify potential resource conflicts."""
        conflicts = []
        
        # Check for over-allocation of critical resources
        critical_resources = [req for req in resource_requirements if req.critical_path]
        
        for req in critical_resources:
            if req.availability_constraint < 0.8:
                conflicts.append({
                    "type": "availability_constraint",
                    "resource_type": req.resource_type.value,
                    "description": f"Low availability ({req.availability_constraint:.1%}) for critical resource",
                    "impact": "high",
                    "recommendation": "Consider recruiting earlier or using contractors"
                })
        
        # Check for skill level mismatches
        high_skill_requirements = [req for req in resource_requirements if req.skill_level in ["senior", "expert"]]
        
        if len(high_skill_requirements) > 3:
            conflicts.append({
                "type": "skill_requirement",
                "description": "High number of senior/expert level requirements",
                "impact": "medium",
                "recommendation": "Consider mentorship model with mid-level developers"
            })
        
        return conflicts
    
    def _generate_resource_optimizations(
        self,
        resource_requirements: List[ResourceRequirement],
        team_composition: Dict[ResourceType, int],
        conflicts: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate resource optimization recommendations."""
        optimizations = []
        
        # Check for over-staffing
        total_team_size = sum(team_composition.values())
        if total_team_size > 10:
            optimizations.append("Consider phased team scaling to reduce coordination overhead")
        
        # Check for cost optimization opportunities
        high_cost_resources = [req for req in resource_requirements if req.hourly_rate_usd > 150]
        if high_cost_resources:
            optimizations.append("Consider partial outsourcing for high-cost, non-critical tasks")
        
        # AI-specific optimizations
        ai_resources = [req for req in resource_requirements if req.resource_type in [ResourceType.AI_ML_ENGINEER, ResourceType.DATA_SCIENTIST]]
        if len(ai_resources) > 2:
            optimizations.append("Consider using pre-trained models and AI platforms to reduce custom development")
        
        # Parallel work optimization
        if len(conflicts) > 2:
            optimizations.append("Restructure task dependencies to enable more parallel development")
        
        return optimizations
    
    def _create_resource_scaling_strategy(
        self,
        resource_requirements: List[ResourceRequirement],
        technical_roadmap: TechnicalRoadmap,
        market_analysis: Optional[MarketAnalysisResult]
    ) -> Dict[str, Any]:
        """Create resource scaling strategy."""
        strategy = {
            "initial_team_size": sum(1 for req in resource_requirements if req.critical_path),
            "ramp_up_phases": [],
            "contingency_plans": [],
            "offshore_opportunities": []
        }
        
        # Define ramp-up phases
        phases = technical_roadmap.implementation_phases
        
        for i, phase in enumerate(phases):
            phase_resources = []
            
            if i == 0:  # Research/POC phase
                phase_resources = [ResourceType.AI_ML_ENGINEER, ResourceType.PRODUCT_MANAGER]
            elif i == 1:  # MVP development
                phase_resources = [ResourceType.BACKEND_DEVELOPER, ResourceType.FRONTEND_DEVELOPER, ResourceType.DATA_SCIENTIST]
            elif i == 2:  # Beta testing
                phase_resources = [ResourceType.QA_ENGINEER, ResourceType.DEVOPS_ENGINEER]
            elif i == 3:  # Production launch
                phase_resources = [ResourceType.DEVOPS_ENGINEER, ResourceType.TECHNICAL_WRITER]
            
            strategy["ramp_up_phases"].append({
                "phase": phase.phase.value,
                "week": sum(p.duration_weeks for p in phases[:i]),
                "add_resources": [r.value for r in phase_resources]
            })
        
        # Contingency plans
        strategy["contingency_plans"] = [
            "Cross-train team members for critical role backup",
            "Maintain contractor relationships for rapid scaling",
            "Consider augmented development teams for acceleration"
        ]
        
        # Offshore opportunities
        if market_analysis and market_analysis.serviceable_addressable_market < 50000000:
            strategy["offshore_opportunities"] = [
                "Frontend development",
                "QA testing",
                "Documentation"
            ]
        
        return strategy
    
    async def _identify_timeline_risks(
        self,
        opportunity: Opportunity,
        technical_roadmap: TechnicalRoadmap,
        task_estimates: List[TaskEstimate]
    ) -> List[TimelineRisk]:
        """Identify timeline risks and their potential impact."""
        risks = []
        
        # Technical risks
        if technical_roadmap.overall_complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]:
            risks.append(TimelineRisk(
                risk_id="technical_complexity",
                category=RiskCategory.TECHNICAL,
                description="High technical complexity may lead to underestimation of development effort",
                probability=0.7,
                impact_days=14,
                mitigation_strategy="Add 20% buffer to complex technical tasks and conduct early prototyping",
                mitigation_cost_usd=15000,
                detection_indicators=["Task estimates consistently exceeded", "Integration issues discovered late"]
            ))
        
        # AI-specific risks
        ai_tasks = [t for t in task_estimates if any("ai" in rt.value for rt in t.required_resources)]
        if ai_tasks:
            risks.append(TimelineRisk(
                risk_id="ai_model_performance",
                category=RiskCategory.TECHNICAL,
                description="AI model may not achieve required performance metrics",
                probability=0.5,
                impact_days=21,
                mitigation_strategy="Implement iterative model training with fallback approaches",
                mitigation_cost_usd=25000,
                detection_indicators=["Model accuracy below targets", "Training data quality issues"]
            ))
        
        # Resource risks
        critical_resources = [t for t in task_estimates if len(t.required_resources) == 1]  # Single-person dependencies
        if len(critical_resources) > 5:
            risks.append(TimelineRisk(
                risk_id="key_person_dependency",
                category=RiskCategory.RESOURCE,
                description="Critical dependency on individual team members",
                probability=0.4,
                impact_days=10,
                mitigation_strategy="Cross-train team members and document key processes",
                mitigation_cost_usd=8000,
                detection_indicators=["Team member unavailability", "Knowledge gaps discovered"]
            ))
        
        # Integration risks
        microservices_architecture = technical_roadmap.architecture_recommendation.pattern.value == "microservices"
        if microservices_architecture:
            risks.append(TimelineRisk(
                risk_id="integration_complexity",
                category=RiskCategory.INTEGRATION,
                description="Microservices integration may be more complex than anticipated",
                probability=0.6,
                impact_days=7,
                mitigation_strategy="Implement integration testing early and use API contracts",
                mitigation_cost_usd=12000,
                detection_indicators=["API incompatibilities", "Service communication failures"]
            ))
        
        # External dependency risks
        external_apis = any("api" in t.description.lower() for t in task_estimates)
        if external_apis:
            risks.append(TimelineRisk(
                risk_id="external_api_changes",
                category=RiskCategory.EXTERNAL,
                description="External API changes or service unavailability",
                probability=0.3,
                impact_days=5,
                mitigation_strategy="Build API abstraction layer and have backup providers",
                mitigation_cost_usd=6000,
                detection_indicators=["API rate limiting", "Service deprecation notices"]
            ))
        
        # Scope creep risk
        if opportunity.description and len(opportunity.description) > 500:
            risks.append(TimelineRisk(
                risk_id="scope_creep",
                category=RiskCategory.SCOPE,
                description="Feature scope may expand during development",
                probability=0.8,
                impact_days=14,
                mitigation_strategy="Implement strict change control process and prioritization framework",
                mitigation_cost_usd=5000,
                detection_indicators=["Frequent feature requests", "Stakeholder feedback requesting additions"]
            ))
        
        # Performance risks for high-scale applications
        if opportunity.description and any(word in opportunity.description.lower() for word in ["scale", "real-time", "high-volume"]):
            risks.append(TimelineRisk(
                risk_id="performance_optimization",
                category=RiskCategory.PERFORMANCE,
                description="Performance optimization may require significant additional effort",
                probability=0.6,
                impact_days=10,
                mitigation_strategy="Conduct early performance testing and architecture review",
                mitigation_cost_usd=18000,
                detection_indicators=["Load test failures", "Response time requirements not met"]
            ))
        
        return risks
    
    async def _analyze_critical_path(self, task_estimates: List[TaskEstimate]) -> List[str]:
        """Analyze critical path through project tasks."""
        
        # Build dependency graph
        task_graph = {}
        for task in task_estimates:
            task_graph[task.task_id] = {
                "duration": task.estimated_hours / 40,  # Convert to weeks
                "dependencies": task.dependencies,
                "task": task
            }
        
        # Calculate earliest start times
        earliest_start = {}
        for task_id in task_graph:
            earliest_start[task_id] = self._calculate_earliest_start(task_id, task_graph, earliest_start)
        
        # Calculate latest start times
        latest_start = {}
        project_end = max(earliest_start[tid] + task_graph[tid]["duration"] for tid in task_graph)
        
        for task_id in task_graph:
            latest_start[task_id] = self._calculate_latest_start(task_id, task_graph, latest_start, project_end)
        
        # Identify critical path (tasks with zero slack)
        critical_path = []
        for task_id in task_graph:
            slack = latest_start[task_id] - earliest_start[task_id]
            if slack <= 0.1:  # Allow small floating point errors
                critical_path.append(task_id)
        
        return critical_path
    
    def _calculate_earliest_start(self, task_id: str, graph: Dict, cache: Dict) -> float:
        """Calculate earliest start time for a task."""
        if task_id in cache:
            return cache[task_id]
        
        task_info = graph[task_id]
        dependencies = task_info["dependencies"]
        
        if not dependencies:
            cache[task_id] = 0.0
            return 0.0
        
        max_predecessor_end = 0.0
        for dep_id in dependencies:
            if dep_id in graph:
                dep_earliest = self._calculate_earliest_start(dep_id, graph, cache)
                dep_end = dep_earliest + graph[dep_id]["duration"]
                max_predecessor_end = max(max_predecessor_end, dep_end)
        
        cache[task_id] = max_predecessor_end
        return max_predecessor_end
    
    def _calculate_latest_start(self, task_id: str, graph: Dict, cache: Dict, project_end: float) -> float:
        """Calculate latest start time for a task."""
        if task_id in cache:
            return cache[task_id]
        
        # Find all tasks that depend on this task
        successors = [tid for tid, info in graph.items() if task_id in info["dependencies"]]
        
        if not successors:
            # Task is at the end of the project
            cache[task_id] = project_end - graph[task_id]["duration"]
            return cache[task_id]
        
        min_successor_start = float('inf')
        for succ_id in successors:
            succ_latest = self._calculate_latest_start(succ_id, graph, cache, project_end)
            min_successor_start = min(min_successor_start, succ_latest)
        
        cache[task_id] = min_successor_start - graph[task_id]["duration"]
        return cache[task_id]
    
    async def _run_monte_carlo_simulation(
        self,
        task_estimates: List[TaskEstimate],
        timeline_risks: List[TimelineRisk],
        critical_path: List[str],
        iterations: int = 1000
    ) -> MonteCarloSimulation:
        """Run Monte Carlo simulation for timeline estimation."""
        simulation_results = []
        
        for _ in range(iterations):
            scenario_duration = self._simulate_single_scenario(
                task_estimates, timeline_risks, critical_path
            )
            simulation_results.append(scenario_duration)
        
        # Calculate statistics
        mean_duration = statistics.mean(simulation_results)
        median_duration = statistics.median(simulation_results)
        std_deviation = statistics.stdev(simulation_results)
        
        # Calculate confidence intervals
        sorted_results = sorted(simulation_results)
        confidence_intervals = {
            "50%": (
                sorted_results[int(0.25 * len(sorted_results))],
                sorted_results[int(0.75 * len(sorted_results))]
            ),
            "75%": (
                sorted_results[int(0.125 * len(sorted_results))],
                sorted_results[int(0.875 * len(sorted_results))]
            ),
            "90%": (
                sorted_results[int(0.05 * len(sorted_results))],
                sorted_results[int(0.95 * len(sorted_results))]
            ),
            "95%": (
                sorted_results[int(0.025 * len(sorted_results))],
                sorted_results[int(0.975 * len(sorted_results))]
            )
        }
        
        # Analyze risk scenarios
        risk_scenarios = self._analyze_risk_scenarios(simulation_results, timeline_risks)
        
        # Critical path analysis
        critical_path_analysis = {
            "critical_tasks": len(critical_path),
            "critical_path_duration": sum(
                task.estimated_hours / 40 for task in task_estimates 
                if task.task_id in critical_path
            ),
            "critical_path_percentage": len(critical_path) / len(task_estimates) if task_estimates else 0
        }
        
        return MonteCarloSimulation(
            simulation_id=f"monte_carlo_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            iterations=iterations,
            confidence_intervals=confidence_intervals,
            mean_duration_days=mean_duration,
            median_duration_days=median_duration,
            std_deviation_days=std_deviation,
            risk_scenarios=risk_scenarios,
            critical_path_analysis=critical_path_analysis
        )
    
    def _simulate_single_scenario(
        self,
        task_estimates: List[TaskEstimate],
        timeline_risks: List[TimelineRisk],
        critical_path: List[str]
    ) -> float:
        """Simulate a single project scenario."""
        total_duration_days = 0
        
        # Simulate task duration variations
        for task in task_estimates:
            # Use triangular distribution (optimistic, nominal, pessimistic)
            simulated_hours = random.triangular(
                task.optimistic_hours,
                task.pessimistic_hours,
                task.estimated_hours
            )
            
            # Convert to days
            task_days = simulated_hours / 8  # 8 hours per day
            
            # If task is on critical path, add to total duration
            if task.task_id in critical_path:
                total_duration_days += task_days
        
        # Simulate risk impacts
        for risk in timeline_risks:
            if random.random() < risk.probability:
                total_duration_days += risk.impact_days
        
        return total_duration_days
    
    def _analyze_risk_scenarios(
        self,
        simulation_results: List[float],
        timeline_risks: List[TimelineRisk]
    ) -> List[Dict[str, Any]]:
        """Analyze different risk scenarios from simulation."""
        scenarios = []
        
        # High-risk scenario (90th percentile)
        high_risk_duration = sorted(simulation_results)[int(0.9 * len(simulation_results))]
        scenarios.append({
            "scenario": "high_risk",
            "probability": 0.1,
            "duration_days": high_risk_duration,
            "description": "Multiple risks materialize simultaneously",
            "key_risks": [risk.risk_id for risk in timeline_risks if risk.probability > 0.5]
        })
        
        # Medium-risk scenario (75th percentile)
        medium_risk_duration = sorted(simulation_results)[int(0.75 * len(simulation_results))]
        scenarios.append({
            "scenario": "medium_risk",
            "probability": 0.25,
            "duration_days": medium_risk_duration,
            "description": "Some technical challenges and minor scope changes",
            "key_risks": [risk.risk_id for risk in timeline_risks if 0.3 < risk.probability <= 0.5]
        })
        
        # Low-risk scenario (25th percentile)
        low_risk_duration = sorted(simulation_results)[int(0.25 * len(simulation_results))]
        scenarios.append({
            "scenario": "low_risk",
            "probability": 0.25,
            "duration_days": low_risk_duration,
            "description": "Smooth execution with minimal issues",
            "key_risks": []
        })
        
        return scenarios
    
    async def _calculate_total_duration(
        self,
        task_estimates: List[TaskEstimate],
        critical_path: List[str],
        timeline_risks: List[TimelineRisk],
        monte_carlo: Optional[MonteCarloSimulation]
    ) -> Tuple[int, float]:
        """Calculate total project duration and confidence level."""
        
        if monte_carlo:
            # Use Monte Carlo results
            duration_days = int(monte_carlo.mean_duration_days)
            confidence = 1.0 - (monte_carlo.std_deviation_days / monte_carlo.mean_duration_days)
        else:
            # Calculate from critical path
            critical_tasks = [t for t in task_estimates if t.task_id in critical_path]
            total_hours = sum(task.estimated_hours for task in critical_tasks)
            duration_days = int(total_hours / 8)  # Convert to days
            
            # Calculate confidence based on task confidence levels
            if critical_tasks:
                confidence = statistics.mean(task.confidence_level for task in critical_tasks)
            else:
                confidence = 0.7
        
        # Adjust confidence based on risks
        high_impact_risks = [r for r in timeline_risks if r.probability * r.impact_days > 7]
        if high_impact_risks:
            confidence *= (1.0 - 0.1 * len(high_impact_risks))
        
        return duration_days, max(0.3, min(0.95, confidence))
    
    async def _generate_milestone_dates(
        self,
        task_estimates: List[TaskEstimate],
        critical_path: List[str],
        total_duration_days: int
    ) -> Dict[str, datetime]:
        """Generate milestone dates based on project timeline."""
        milestones = {}
        start_date = datetime.utcnow()
        
        # Extract phases from task IDs
        phases = {}
        for task in task_estimates:
            if task.task_id in critical_path:
                phase = task.task_id.split('_')[0]  # Extract phase from task ID
                if phase not in phases:
                    phases[phase] = []
                phases[phase].append(task)
        
        # Calculate phase durations and dates
        cumulative_days = 0
        phase_order = ["research_poc", "mvp_development", "beta_testing", "production_launch", "scale_optimization"]
        
        for phase in phase_order:
            if phase in phases:
                phase_tasks = phases[phase]
                phase_duration = sum(task.estimated_hours for task in phase_tasks) / 8  # Convert to days
                
                milestone_date = start_date + timedelta(days=cumulative_days + phase_duration)
                milestones[f"{phase}_completion"] = milestone_date
                
                cumulative_days += phase_duration
        
        # Add project completion milestone
        milestones["project_completion"] = start_date + timedelta(days=total_duration_days)
        
        return milestones
    
    async def _recommend_buffers(
        self,
        technical_roadmap: TechnicalRoadmap,
        timeline_risks: List[TimelineRisk],
        confidence: float
    ) -> Dict[str, int]:
        """Recommend buffer time for different phases."""
        buffers = {}
        
        # Base buffer based on confidence
        base_buffer_days = int((1.0 - confidence) * 14)  # Up to 2 weeks
        
        # Phase-specific buffers
        phase_buffers = {
            "research_poc": base_buffer_days + 3,      # Research often takes longer
            "mvp_development": base_buffer_days + 5,   # Development complexity
            "beta_testing": base_buffer_days + 2,      # User feedback integration
            "production_launch": base_buffer_days + 1, # Usually well-defined
            "scale_optimization": base_buffer_days + 4  # Performance challenges
        }
        
        # Adjust based on complexity
        complexity_multiplier = {
            ComplexityLevel.LOW: 0.8,
            ComplexityLevel.MEDIUM: 1.0,
            ComplexityLevel.HIGH: 1.3,
            ComplexityLevel.VERY_HIGH: 1.6
        }
        
        multiplier = complexity_multiplier[technical_roadmap.overall_complexity]
        
        for phase, buffer in phase_buffers.items():
            adjusted_buffer = int(buffer * multiplier)
            
            # Add extra buffer for high-risk phases
            phase_risks = [r for r in timeline_risks if phase in r.description.lower()]
            if phase_risks:
                risk_buffer = sum(r.impact_days * r.probability for r in phase_risks) / 2
                adjusted_buffer += int(risk_buffer)
            
            buffers[phase] = max(1, adjusted_buffer)  # Minimum 1 day buffer
        
        return buffers
    
    async def _analyze_costs(
        self,
        resource_allocation: ResourceAllocation,
        total_duration_days: int,
        timeline_risks: List[TimelineRisk]
    ) -> Dict[str, Any]:
        """Analyze project costs including risk contingencies."""
        
        base_cost = resource_allocation.estimated_cost_total
        
        # Calculate risk contingency
        risk_contingency = sum(
            risk.mitigation_cost_usd * risk.probability 
            for risk in timeline_risks
        )
        
        # Calculate delay costs (if project takes longer)
        daily_burn_rate = resource_allocation.estimated_cost_monthly / 30
        delay_contingency = daily_burn_rate * (total_duration_days * 0.1)  # 10% delay contingency
        
        # Infrastructure and tool costs
        infrastructure_monthly = 5000  # Estimated monthly infrastructure
        infrastructure_total = infrastructure_monthly * (total_duration_days / 30)
        
        # Total cost breakdown
        cost_breakdown = {
            "base_development_cost": base_cost,
            "risk_contingency": risk_contingency,
            "delay_contingency": delay_contingency,
            "infrastructure_cost": infrastructure_total,
            "total_estimated_cost": base_cost + risk_contingency + delay_contingency + infrastructure_total
        }
        
        # Cost per month
        months = total_duration_days / 30
        cost_breakdown["monthly_burn_rate"] = cost_breakdown["total_estimated_cost"] / months if months > 0 else 0
        
        # Cost optimization recommendations
        cost_breakdown["optimization_opportunities"] = [
            "Consider offshore development for non-critical components",
            "Use managed AI services to reduce custom development",
            "Implement automated testing to reduce QA costs",
            "Leverage open-source tools where possible"
        ]
        
        return cost_breakdown
    
    def _initialize_velocity_data(self) -> Dict[str, float]:
        """Initialize historical velocity data for different task types."""
        return {
            "analysis": 1.1,
            "design": 0.9,
            "ai_development": 0.7,
            "backend_development": 1.0,
            "frontend_development": 1.1,
            "ai_integration": 0.8,
            "data_engineering": 0.9,
            "validation": 1.2,
            "devops": 1.0,
            "testing": 1.1,
            "documentation": 1.3,
            "security_development": 0.8,
            "performance": 0.9,
            "optimization": 0.8
        }
    
    def _initialize_resource_rates(self) -> Dict[ResourceType, Dict[str, float]]:
        """Initialize hourly rates for different resource types and skill levels."""
        return {
            ResourceType.AI_ML_ENGINEER: {
                "junior": 80,
                "mid": 120,
                "senior": 160,
                "expert": 220
            },
            ResourceType.DATA_SCIENTIST: {
                "junior": 75,
                "mid": 110,
                "senior": 150,
                "expert": 200
            },
            ResourceType.BACKEND_DEVELOPER: {
                "junior": 60,
                "mid": 90,
                "senior": 130,
                "expert": 180
            },
            ResourceType.FRONTEND_DEVELOPER: {
                "junior": 55,
                "mid": 85,
                "senior": 120,
                "expert": 160
            },
            ResourceType.DEVOPS_ENGINEER: {
                "junior": 65,
                "mid": 95,
                "senior": 140,
                "expert": 190
            },
            ResourceType.SECURITY_ENGINEER: {
                "junior": 70,
                "mid": 105,
                "senior": 150,
                "expert": 210
            },
            ResourceType.QA_ENGINEER: {
                "junior": 45,
                "mid": 70,
                "senior": 100,
                "expert": 140
            },
            ResourceType.PRODUCT_MANAGER: {
                "junior": 70,
                "mid": 110,
                "senior": 160,
                "expert": 220
            },
            ResourceType.UX_DESIGNER: {
                "junior": 50,
                "mid": 80,
                "senior": 120,
                "expert": 170
            },
            ResourceType.TECHNICAL_WRITER: {
                "junior": 40,
                "mid": 65,
                "senior": 90,
                "expert": 130
            }
        }
    
    def _initialize_complexity_factors(self) -> Dict[str, Dict[str, float]]:
        """Initialize complexity factors for different scenarios."""
        return {
            "ai_solution_types": {
                "nlp": 1.2,
                "computer_vision": 1.4,
                "machine_learning": 1.0,
                "deep_learning": 1.6,
                "reinforcement_learning": 1.8,
                "recommendation": 1.1,
                "automation": 1.0,
                "predictive_analytics": 1.2
            },
            "industries": {
                "finance": 1.3,
                "healthcare": 1.4,
                "legal": 1.2,
                "government": 1.5,
                "retail": 1.0,
                "manufacturing": 1.1,
                "education": 0.9
            },
            "architecture_patterns": {
                "microservices": 1.4,
                "monolithic": 1.0,
                "serverless": 1.1,
                "edge_computing": 1.3,
                "pipeline_architecture": 1.2
            }
        }


    async def _generate_hiring_timeline(self, resource_requirements: List[ResourceRequirement]) -> Dict[str, Any]:
        """Generate hiring timeline based on resource requirements."""
        hiring_timeline = {
            "immediate_hires": [],  # Can start immediately
            "short_term_hires": [],  # Within 1-2 months
            "long_term_hires": [],  # 3+ months
            "total_hiring_duration_weeks": 0
        }
        
        for req in resource_requirements:
            hire_info = {
                "resource_type": req.resource_type.value,
                "skill_level": req.skill_level,
                "quantity": req.parallel_capacity,
                "estimated_hire_time_weeks": self._estimate_hiring_time(req.resource_type, req.skill_level)
            }
            
            if hire_info["estimated_hire_time_weeks"] <= 2:
                hiring_timeline["immediate_hires"].append(hire_info)
            elif hire_info["estimated_hire_time_weeks"] <= 8:
                hiring_timeline["short_term_hires"].append(hire_info)
            else:
                hiring_timeline["long_term_hires"].append(hire_info)
        
        # Calculate total hiring duration
        if resource_requirements:
            hiring_timeline["total_hiring_duration_weeks"] = max(
                self._estimate_hiring_time(req.resource_type, req.skill_level) 
                for req in resource_requirements
            )
        
        return hiring_timeline
    
    def _estimate_hiring_time(self, resource_type: ResourceType, skill_level: str) -> int:
        """Estimate hiring time in weeks for a resource type and skill level."""
        base_times = {
            ResourceType.AI_ML_ENGINEER: {"junior": 8, "mid": 12, "senior": 16, "expert": 20},
            ResourceType.DATA_SCIENTIST: {"junior": 6, "mid": 10, "senior": 14, "expert": 18},
            ResourceType.BACKEND_DEVELOPER: {"junior": 4, "mid": 6, "senior": 8, "expert": 12},
            ResourceType.FRONTEND_DEVELOPER: {"junior": 4, "mid": 6, "senior": 8, "expert": 10},
            ResourceType.DEVOPS_ENGINEER: {"junior": 6, "mid": 8, "senior": 12, "expert": 16},
            ResourceType.PRODUCT_MANAGER: {"junior": 4, "mid": 6, "senior": 8, "expert": 10},
            ResourceType.UX_DESIGNER: {"junior": 3, "mid": 5, "senior": 7, "expert": 9},
            ResourceType.QA_ENGINEER: {"junior": 3, "mid": 5, "senior": 7, "expert": 9},
            ResourceType.SECURITY_ENGINEER: {"junior": 8, "mid": 12, "senior": 16, "expert": 20},
            ResourceType.TECHNICAL_WRITER: {"junior": 2, "mid": 3, "senior": 4, "expert": 6}
        }
        
        return base_times.get(resource_type, {"junior": 4, "mid": 6, "senior": 8, "expert": 10}).get(skill_level, 6)


# Singleton instance
timeline_estimation_service = TimelineEstimationService()