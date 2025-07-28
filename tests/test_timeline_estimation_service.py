"""
Tests for Timeline Estimation Service.

Comprehensive test suite for advanced timeline estimation capabilities
including Monte Carlo simulation, resource allocation, and risk analysis.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
from typing import List, Dict

from shared.services.timeline_estimation_service import (
    TimelineEstimationService,
    EstimationMethod,
    ResourceType,
    RiskCategory,
    TaskEstimate,
    ResourceRequirement,
    TimelineRisk,
    MonteCarloSimulation,
    ResourceAllocation,
    TimelineEstimate
)
from shared.services.technical_roadmap_service import (
    TechnicalRoadmap,
    ComplexityLevel,
    ArchitecturePattern,
    ArchitectureRecommendation,
    ImplementationPhase,
    ImplementationPhaseDetail
)
from shared.services.business_intelligence_service import MarketAnalysisResult
from shared.models.opportunity import Opportunity


class TestTimelineEstimationService:
    """Test suite for TimelineEstimationService."""
    
    @pytest.fixture
    def service(self):
        """Create timeline estimation service instance."""
        return TimelineEstimationService()
    
    @pytest.fixture
    def mock_opportunity(self):
        """Create mock opportunity for testing."""
        opportunity = Mock(spec=Opportunity)
        opportunity.id = "test-opportunity-123"
        opportunity.title = "AI-Powered Customer Service Bot"
        opportunity.description = "Real-time AI chatbot for customer support with NLP capabilities"
        opportunity.ai_solution_types = '["nlp", "machine_learning"]'
        opportunity.target_industries = '["finance", "retail"]'
        opportunity.required_capabilities = '["transformer", "bert", "conversation_management"]'
        return opportunity
    
    @pytest.fixture
    def mock_technical_roadmap(self):
        """Create mock technical roadmap for testing."""
        roadmap = Mock(spec=TechnicalRoadmap)
        roadmap.roadmap_id = "roadmap_test-opportunity-123"
        roadmap.opportunity_id = "test-opportunity-123"
        roadmap.overall_complexity = ComplexityLevel.HIGH
        roadmap.estimated_timeline_weeks = 32
        roadmap.total_estimated_hours = 2560
        roadmap.recommended_team_size = 6
        
        # Mock architecture recommendation
        architecture = Mock(spec=ArchitectureRecommendation)
        architecture.pattern = ArchitecturePattern.MICROSERVICES
        roadmap.architecture_recommendation = architecture
        
        # Mock implementation phases
        phases = [
            Mock(spec=ImplementationPhaseDetail),
            Mock(spec=ImplementationPhaseDetail),
            Mock(spec=ImplementationPhaseDetail)
        ]
        phases[0].phase = ImplementationPhase.RESEARCH_POC
        phases[0].duration_weeks = 8
        phases[0].estimated_effort_hours = 640
        
        phases[1].phase = ImplementationPhase.MVP_DEVELOPMENT
        phases[1].duration_weeks = 16
        phases[1].estimated_effort_hours = 1280
        
        phases[2].phase = ImplementationPhase.BETA_TESTING
        phases[2].duration_weeks = 8
        phases[2].estimated_effort_hours = 640
        
        roadmap.implementation_phases = phases
        return roadmap
    
    @pytest.fixture
    def mock_market_analysis(self):
        """Create mock market analysis for testing."""
        analysis = Mock(spec=MarketAnalysisResult)
        analysis.total_addressable_market = 500000000
        analysis.serviceable_addressable_market = 150000000
        analysis.market_growth_rate = 15.5
        analysis.market_maturity = "growth"
        return analysis
    
    @pytest.mark.asyncio
    async def test_generate_timeline_estimate_basic(self, service, mock_opportunity, mock_technical_roadmap):
        """Test basic timeline estimate generation."""
        db_mock = AsyncMock()
        
        estimate = await service.generate_timeline_estimate(
            db_mock,
            mock_opportunity,
            mock_technical_roadmap,
            estimation_method=EstimationMethod.EXPERT_JUDGMENT
        )
        
        assert isinstance(estimate, TimelineEstimate)
        assert estimate.opportunity_id == "test-opportunity-123"
        assert estimate.estimation_method == EstimationMethod.EXPERT_JUDGMENT
        assert estimate.total_duration_days > 0
        assert 0.3 <= estimate.confidence_level <= 0.95
        assert len(estimate.task_estimates) > 0
        assert isinstance(estimate.resource_allocation, ResourceAllocation)
        assert len(estimate.timeline_risks) > 0
    
    @pytest.mark.asyncio
    async def test_generate_timeline_estimate_monte_carlo(self, service, mock_opportunity, mock_technical_roadmap):
        """Test timeline estimate with Monte Carlo simulation."""
        db_mock = AsyncMock()
        
        estimate = await service.generate_timeline_estimate(
            db_mock,
            mock_opportunity,
            mock_technical_roadmap,
            estimation_method=EstimationMethod.MONTE_CARLO
        )
        
        assert estimate.monte_carlo_simulation is not None
        assert isinstance(estimate.monte_carlo_simulation, MonteCarloSimulation)
        assert estimate.monte_carlo_simulation.iterations > 0
        assert estimate.monte_carlo_simulation.mean_duration_days > 0
        assert "90%" in estimate.monte_carlo_simulation.confidence_intervals
        assert len(estimate.monte_carlo_simulation.risk_scenarios) > 0
    
    @pytest.mark.asyncio
    async def test_create_detailed_task_estimates(self, service, mock_opportunity, mock_technical_roadmap):
        """Test detailed task estimation creation."""
        tasks = await service._create_detailed_task_estimates(
            mock_opportunity,
            mock_technical_roadmap,
            EstimationMethod.FUNCTION_POINT
        )
        
        assert len(tasks) > 0
        
        for task in tasks:
            assert isinstance(task, TaskEstimate)
            assert task.task_id
            assert task.name
            assert task.estimated_hours > 0
            assert task.optimistic_hours <= task.estimated_hours <= task.pessimistic_hours
            assert 0.0 <= task.confidence_level <= 1.0
            assert len(task.required_resources) > 0
            assert all(isinstance(r, ResourceType) for r in task.required_resources)
    
    def test_get_task_templates(self, service):
        """Test task template generation for different phases."""
        # Test research POC phase
        poc_templates = service._get_task_templates("research_poc", ComplexityLevel.MEDIUM)
        assert len(poc_templates) > 0
        assert any("requirements_analysis" in template["id"] for template in poc_templates)
        assert any("ai_model_prototype" in template["id"] for template in poc_templates)
        
        # Test MVP development phase
        mvp_templates = service._get_task_templates("mvp_development", ComplexityLevel.HIGH)
        assert len(mvp_templates) > 0
        assert any("backend_development" in template["id"] for template in mvp_templates)
        assert any("ai_model_integration" in template["id"] for template in mvp_templates)
        
        # Verify complexity adjustment
        low_complexity = service._get_task_templates("mvp_development", ComplexityLevel.LOW)
        high_complexity = service._get_task_templates("mvp_development", ComplexityLevel.HIGH)
        
        # High complexity should have more base hours
        low_total_hours = sum(t["base_hours"] for t in low_complexity)
        high_total_hours = sum(t["base_hours"] for t in high_complexity)
        assert high_total_hours > low_total_hours
    
    def test_calculate_task_complexity_factors(self, service, mock_opportunity, mock_technical_roadmap):
        """Test task complexity factor calculation."""
        template = {
            "id": "ai_model_integration",
            "type": "ai_integration",
            "base_hours": 100
        }
        
        factors = service._calculate_task_complexity_factors(
            template, mock_technical_roadmap, mock_opportunity
        )
        
        assert isinstance(factors, dict)
        assert "technical_complexity" in factors
        assert "ai_complexity" in factors
        assert "security_complexity" in factors
        
        # AI tasks should have higher AI complexity
        assert factors["ai_complexity"] > 1.0
        
        # Microservices architecture should increase technical complexity
        assert factors["technical_complexity"] > 1.0
        
        # Finance industry should increase security complexity
        assert factors["security_complexity"] > 1.0
    
    @pytest.mark.asyncio
    async def test_estimation_methods(self, service, mock_technical_roadmap):
        """Test different estimation methods."""
        task_data = {
            "base_hours": 100,
            "complexity_factors": {"technical": 1.2, "ai": 1.5},
            "type": "ai_development"
        }
        
        # Test function point estimation
        fp_estimate = await service._estimate_with_function_points(task_data, mock_technical_roadmap)
        assert "nominal" in fp_estimate
        assert "optimistic" in fp_estimate
        assert "pessimistic" in fp_estimate
        assert fp_estimate["optimistic"] <= fp_estimate["nominal"] <= fp_estimate["pessimistic"]
        
        # Test story point estimation
        sp_estimate = await service._estimate_with_story_points(task_data, mock_technical_roadmap)
        assert sp_estimate["nominal"] > 0
        
        # Test expert judgment estimation
        ej_estimate = await service._estimate_with_expert_judgment(task_data, mock_technical_roadmap)
        assert ej_estimate["nominal"] > 0
        
        # Test historical data estimation
        hd_estimate = await service._estimate_with_historical_data(task_data, mock_technical_roadmap)
        assert hd_estimate["nominal"] > 0
    
    @pytest.mark.asyncio
    async def test_analyze_resource_requirements(self, service, mock_technical_roadmap, mock_market_analysis):
        """Test resource requirement analysis."""
        # Create mock task estimates
        task_estimates = [
            TaskEstimate(
                task_id="task1",
                name="Backend Development",
                description="Develop backend APIs",
                estimated_hours=200,
                optimistic_hours=160,
                pessimistic_hours=240,
                confidence_level=0.8,
                dependencies=[],
                required_resources=[ResourceType.BACKEND_DEVELOPER, ResourceType.AI_ML_ENGINEER],
                complexity_factors={"technical": 1.2},
                historical_velocity=1.0
            ),
            TaskEstimate(
                task_id="task2",
                name="AI Model Training",
                description="Train and optimize AI model",
                estimated_hours=160,
                optimistic_hours=120,
                pessimistic_hours=200,
                confidence_level=0.7,
                dependencies=["task1"],
                required_resources=[ResourceType.AI_ML_ENGINEER, ResourceType.DATA_SCIENTIST],
                complexity_factors={"ai": 1.5},
                historical_velocity=0.8
            )
        ]
        
        allocation = await service._analyze_resource_requirements(
            task_estimates, mock_technical_roadmap, mock_market_analysis
        )
        
        assert isinstance(allocation, ResourceAllocation)
        assert len(allocation.resource_requirements) > 0
        assert allocation.estimated_cost_total > 0
        assert allocation.estimated_cost_monthly > 0
        assert len(allocation.team_composition) > 0
        
        # Verify resource requirements
        for req in allocation.resource_requirements:
            assert isinstance(req, ResourceRequirement)
            assert req.required_hours > 0
            assert req.skill_level in ["junior", "mid", "senior", "expert"]
            assert 0.0 <= req.availability_constraint <= 1.0
            assert req.hourly_rate_usd > 0
    
    def test_determine_required_skill_level(self, service, mock_technical_roadmap):
        """Test skill level determination for different resource types."""
        # AI roles should require higher skill levels
        ai_skill = service._determine_required_skill_level(
            ResourceType.AI_ML_ENGINEER, mock_technical_roadmap
        )
        backend_skill = service._determine_required_skill_level(
            ResourceType.BACKEND_DEVELOPER, mock_technical_roadmap
        )
        
        # For high complexity, AI engineers should be expert/senior level
        assert ai_skill in ["senior", "expert"]
        
        # Backend developers should be at least mid level for high complexity
        assert backend_skill in ["mid", "senior", "expert"]
    
    def test_calculate_parallel_capacity(self, service):
        """Test parallel capacity calculation."""
        # High-hour tasks should allow more parallel resources
        high_capacity = service._calculate_parallel_capacity(ResourceType.BACKEND_DEVELOPER, 2000)
        low_capacity = service._calculate_parallel_capacity(ResourceType.BACKEND_DEVELOPER, 200)
        
        assert high_capacity >= low_capacity
        assert high_capacity <= 5  # Cap at 5
        
        # Single-person roles should have lower capacity
        pm_capacity = service._calculate_parallel_capacity(ResourceType.PRODUCT_MANAGER, 1000)
        assert pm_capacity <= 2
    
    @pytest.mark.asyncio
    async def test_identify_timeline_risks(self, service, mock_opportunity, mock_technical_roadmap):
        """Test timeline risk identification."""
        task_estimates = [
            TaskEstimate(
                task_id="ai_task",
                name="AI Development",
                description="Complex AI model development",
                estimated_hours=200,
                optimistic_hours=160,
                pessimistic_hours=280,
                confidence_level=0.6,
                dependencies=[],
                required_resources=[ResourceType.AI_ML_ENGINEER],
                complexity_factors={"ai": 1.8},
                historical_velocity=0.7
            )
        ]
        
        risks = await service._identify_timeline_risks(
            mock_opportunity, mock_technical_roadmap, task_estimates
        )
        
        assert len(risks) > 0
        
        for risk in risks:
            assert isinstance(risk, TimelineRisk)
            assert risk.risk_id
            assert isinstance(risk.category, RiskCategory)
            assert 0.0 <= risk.probability <= 1.0
            assert risk.impact_days > 0
            assert risk.mitigation_strategy
            assert risk.mitigation_cost_usd >= 0
        
        # Should have technical complexity risk for high complexity project
        assert any(risk.category == RiskCategory.TECHNICAL for risk in risks)
        
        # Should have AI-specific risks
        assert any("ai" in risk.description.lower() for risk in risks)
    
    @pytest.mark.asyncio
    async def test_analyze_critical_path(self, service):
        """Test critical path analysis."""
        task_estimates = [
            TaskEstimate(
                task_id="task1",
                name="Task 1",
                description="First task",
                estimated_hours=80,  # 2 weeks
                optimistic_hours=64,
                pessimistic_hours=96,
                confidence_level=0.8,
                dependencies=[],
                required_resources=[ResourceType.BACKEND_DEVELOPER],
                complexity_factors={},
                historical_velocity=1.0
            ),
            TaskEstimate(
                task_id="task2",
                name="Task 2",
                description="Depends on task1",
                estimated_hours=120,  # 3 weeks
                optimistic_hours=96,
                pessimistic_hours=144,
                confidence_level=0.7,
                dependencies=["task1"],
                required_resources=[ResourceType.AI_ML_ENGINEER],
                complexity_factors={},
                historical_velocity=1.0
            ),
            TaskEstimate(
                task_id="task3",
                name="Task 3",
                description="Parallel to task2",
                estimated_hours=40,  # 1 week
                optimistic_hours=32,
                pessimistic_hours=48,
                confidence_level=0.9,
                dependencies=["task1"],
                required_resources=[ResourceType.FRONTEND_DEVELOPER],
                complexity_factors={},
                historical_velocity=1.0
            )
        ]
        
        critical_path = await service._analyze_critical_path(task_estimates)
        
        assert len(critical_path) > 0
        assert "task1" in critical_path  # Should be on critical path
        assert "task2" in critical_path  # Longest path should be critical
        # task3 might not be on critical path since it's shorter
    
    @pytest.mark.asyncio
    async def test_monte_carlo_simulation(self, service):
        """Test Monte Carlo simulation."""
        task_estimates = [
            TaskEstimate(
                task_id="task1",
                name="Development Task",
                description="Core development",
                estimated_hours=100,
                optimistic_hours=80,
                pessimistic_hours=140,
                confidence_level=0.8,
                dependencies=[],
                required_resources=[ResourceType.BACKEND_DEVELOPER],
                complexity_factors={},
                historical_velocity=1.0
            )
        ]
        
        timeline_risks = [
            TimelineRisk(
                risk_id="tech_risk",
                category=RiskCategory.TECHNICAL,
                description="Technical complexity",
                probability=0.3,
                impact_days=5,
                mitigation_strategy="Add buffer time",
                mitigation_cost_usd=5000,
                detection_indicators=["Performance issues"]
            )
        ]
        
        critical_path = ["task1"]
        
        simulation = await service._run_monte_carlo_simulation(
            task_estimates, timeline_risks, critical_path, iterations=100
        )
        
        assert isinstance(simulation, MonteCarloSimulation)
        assert simulation.iterations == 100
        assert simulation.mean_duration_days > 0
        assert simulation.median_duration_days > 0
        assert simulation.std_deviation_days >= 0
        assert len(simulation.confidence_intervals) == 4
        assert "50%" in simulation.confidence_intervals
        assert "95%" in simulation.confidence_intervals
        assert len(simulation.risk_scenarios) > 0
    
    def test_round_to_fibonacci(self, service):
        """Test Fibonacci rounding for story points."""
        assert service._round_to_fibonacci(1.2) == 1
        assert service._round_to_fibonacci(2.8) == 3
        assert service._round_to_fibonacci(7.1) == 8
        assert service._round_to_fibonacci(15.0) == 13
        assert service._round_to_fibonacci(25.0) == 21
    
    def test_estimate_team_velocity(self, service):
        """Test team velocity estimation."""
        low_velocity = service._estimate_team_velocity(ComplexityLevel.LOW)
        high_velocity = service._estimate_team_velocity(ComplexityLevel.VERY_HIGH)
        
        assert low_velocity > high_velocity  # Lower complexity = higher velocity
        assert 0.5 <= high_velocity <= 1.5   # Reasonable velocity range
        assert 0.5 <= low_velocity <= 1.5
    
    def test_calculate_task_confidence(self, service, mock_technical_roadmap):
        """Test task confidence calculation."""
        task_data = {
            "type": "backend_development",  # Familiar task
            "complexity_factors": {"technical": 1.1}  # Low complexity
        }
        
        confidence = service._calculate_task_confidence(
            task_data, mock_technical_roadmap, EstimationMethod.HISTORICAL_DATA
        )
        
        assert 0.5 <= confidence <= 0.95
        
        # Complex AI task should have lower confidence
        complex_task_data = {
            "type": "ai_development",  # Complex task
            "complexity_factors": {"ai": 1.8}  # High complexity
        }
        
        complex_confidence = service._calculate_task_confidence(
            complex_task_data, mock_technical_roadmap, EstimationMethod.EXPERT_JUDGMENT
        )
        
        assert complex_confidence < confidence
    
    @pytest.mark.asyncio
    async def test_recommend_buffers(self, service, mock_technical_roadmap):
        """Test buffer recommendation."""
        timeline_risks = [
            TimelineRisk(
                risk_id="scope_risk",
                category=RiskCategory.SCOPE,
                description="Scope creep in mvp_development phase",
                probability=0.6,
                impact_days=7,
                mitigation_strategy="Change control",
                mitigation_cost_usd=3000,
                detection_indicators=["Feature requests"]
            )
        ]
        
        confidence = 0.7
        
        buffers = await service._recommend_buffers(
            mock_technical_roadmap, timeline_risks, confidence
        )
        
        assert isinstance(buffers, dict)
        assert len(buffers) > 0
        
        # All buffer values should be positive
        for phase, buffer_days in buffers.items():
            assert buffer_days > 0
            assert isinstance(buffer_days, int)
        
        # MVP development should have extra buffer due to scope risk
        if "mvp_development" in buffers:
            assert buffers["mvp_development"] > 1
    
    @pytest.mark.asyncio
    async def test_analyze_costs(self, service):
        """Test cost analysis."""
        # Create mock resource allocation
        resource_allocation = ResourceAllocation(
            allocation_id="test",
            resource_requirements=[],
            team_composition={ResourceType.BACKEND_DEVELOPER: 2, ResourceType.AI_ML_ENGINEER: 1},
            estimated_cost_total=200000,
            estimated_cost_monthly=25000,
            resource_conflicts=[],
            optimization_recommendations=[],
            scaling_strategy={}
        )
        
        timeline_risks = [
            TimelineRisk(
                risk_id="cost_risk",
                category=RiskCategory.TECHNICAL,
                description="Cost risk",
                probability=0.4,
                impact_days=5,
                mitigation_strategy="Mitigation",
                mitigation_cost_usd=10000,
                detection_indicators=[]
            )
        ]
        
        total_duration_days = 180
        
        cost_analysis = await service._analyze_costs(
            resource_allocation, total_duration_days, timeline_risks
        )
        
        assert isinstance(cost_analysis, dict)
        assert "base_development_cost" in cost_analysis
        assert "risk_contingency" in cost_analysis
        assert "total_estimated_cost" in cost_analysis
        assert "monthly_burn_rate" in cost_analysis
        
        # Total cost should include all components
        total = cost_analysis["total_estimated_cost"]
        base = cost_analysis["base_development_cost"]
        assert total > base
        
        # Should have optimization recommendations
        assert "optimization_opportunities" in cost_analysis
        assert len(cost_analysis["optimization_opportunities"]) > 0
    
    def test_initialization(self, service):
        """Test service initialization."""
        assert hasattr(service, 'historical_velocity_data')
        assert hasattr(service, 'resource_rates')
        assert hasattr(service, 'complexity_factors')
        
        # Check that data structures are properly initialized
        assert len(service.historical_velocity_data) > 0
        assert len(service.resource_rates) > 0
        assert len(service.complexity_factors) > 0
        
        # Verify resource rates structure
        for resource_type, rates in service.resource_rates.items():
            assert isinstance(resource_type, ResourceType)
            assert "junior" in rates
            assert "senior" in rates
            assert rates["senior"] > rates["junior"]
    
    @pytest.mark.asyncio
    async def test_edge_cases(self, service, mock_opportunity, mock_technical_roadmap):
        """Test edge cases and error handling."""
        db_mock = AsyncMock()
        
        # Test with minimal opportunity data
        minimal_opportunity = Mock(spec=Opportunity)
        minimal_opportunity.id = "minimal"
        minimal_opportunity.title = "Simple App"
        minimal_opportunity.description = None
        minimal_opportunity.ai_solution_types = None
        minimal_opportunity.target_industries = None
        minimal_opportunity.required_capabilities = None
        
        # Should still generate estimate without errors
        estimate = await service.generate_timeline_estimate(
            db_mock,
            minimal_opportunity,
            mock_technical_roadmap,
            estimation_method=EstimationMethod.EXPERT_JUDGMENT
        )
        
        assert isinstance(estimate, TimelineEstimate)
        assert estimate.total_duration_days > 0
        
        # Test with very low complexity
        low_complexity_roadmap = Mock(spec=mock_technical_roadmap)
        low_complexity_roadmap.overall_complexity = ComplexityLevel.LOW
        low_complexity_roadmap.estimated_timeline_weeks = 8
        low_complexity_roadmap.implementation_phases = mock_technical_roadmap.implementation_phases[:1]
        low_complexity_roadmap.architecture_recommendation = mock_technical_roadmap.architecture_recommendation
        
        low_estimate = await service.generate_timeline_estimate(
            db_mock,
            mock_opportunity,
            low_complexity_roadmap
        )
        
        assert low_estimate.total_duration_days < estimate.total_duration_days
        assert low_estimate.confidence_level >= estimate.confidence_level


@pytest.mark.asyncio
async def test_service_integration():
    """Test service integration with other components."""
    service = TimelineEstimationService()
    
    # Test that service can be imported and instantiated
    assert service is not None
    assert hasattr(service, 'generate_timeline_estimate')
    
    # Test that estimation methods enum works correctly
    assert EstimationMethod.MONTE_CARLO != EstimationMethod.EXPERT_JUDGMENT
    assert EstimationMethod.FUNCTION_POINT.value == "function_point"
    
    # Test that resource types are properly defined
    assert ResourceType.AI_ML_ENGINEER.value == "ai_ml_engineer"
    assert ResourceType.BACKEND_DEVELOPER.value == "backend_developer"
    
    # Test that risk categories are defined
    assert RiskCategory.TECHNICAL.value == "technical"
    assert RiskCategory.RESOURCE.value == "resource"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])