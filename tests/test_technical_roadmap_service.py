"""
Test suite for Technical Roadmap Service.

Tests the Phase 7.2.1 implementation of technical roadmap generation,
architecture recommendations, and technology stack suggestions.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from shared.services.technical_roadmap_service import (
    TechnicalRoadmapService,
    TechnicalRoadmap,
    ArchitectureRecommendation,
    TechnologyRecommendation,
    ImplementationPhaseDetail,
    ArchitecturePattern,
    TechnologyCategory,
    ComplexityLevel,
    ImplementationPhase
)
from shared.models.opportunity import Opportunity
from shared.services.business_intelligence_service import MarketAnalysisResult


@pytest.fixture
def roadmap_service():
    """Create TechnicalRoadmapService instance."""
    return TechnicalRoadmapService()


@pytest.fixture
def simple_opportunity():
    """Create simple AI opportunity for testing."""
    opportunity = MagicMock(spec=Opportunity)
    opportunity.id = "simple-ai-123"
    opportunity.title = "Simple AI Chatbot"
    opportunity.description = "Basic customer service chatbot for small businesses"
    opportunity.ai_solution_types = json.dumps(["nlp"])
    opportunity.target_industries = json.dumps(["retail"])
    opportunity.required_capabilities = json.dumps(["text_processing", "api_integration"])
    return opportunity


@pytest.fixture
def complex_opportunity():
    """Create complex AI opportunity for testing."""
    opportunity = MagicMock(spec=Opportunity)
    opportunity.id = "complex-ai-456"
    opportunity.title = "Real-time Multi-modal AI Platform"
    opportunity.description = "Enterprise-grade real-time AI platform combining computer vision, NLP, and predictive analytics for healthcare applications"
    opportunity.ai_solution_types = json.dumps(["nlp", "computer_vision", "machine_learning", "predictive_analytics"])
    opportunity.target_industries = json.dumps(["healthcare", "finance"])
    opportunity.required_capabilities = json.dumps(["transformer", "deep_learning", "neural_networks", "real_time_processing", "hipaa_compliance"])
    return opportunity


@pytest.fixture
def mock_market_analysis():
    """Create mock market analysis result."""
    return MarketAnalysisResult(
        market_id="test_market",
        market_name="AI Solutions Market",
        total_addressable_market=1000000000,
        serviceable_addressable_market=300000000,
        serviceable_obtainable_market=30000000,
        market_growth_rate=25.0,
        market_maturity="growth",
        key_players=[],
        market_trends=[],
        barriers_to_entry=[],
        success_factors=[],
        risk_assessment={},
        confidence_score=0.8
    )


@pytest.mark.asyncio
class TestTechnicalRoadmapService:
    """Test technical roadmap service functionality."""
    
    async def test_analyze_ai_requirements_simple(self, roadmap_service, simple_opportunity):
        """Test AI requirements analysis for simple opportunity."""
        requirements = await roadmap_service._analyze_ai_requirements(simple_opportunity)
        
        # Verify structure
        assert "ai_types" in requirements
        assert "capabilities" in requirements
        assert "data_requirements" in requirements
        assert "performance_needs" in requirements
        assert "integration_requirements" in requirements
        
        # Verify content
        assert "nlp" in requirements["ai_types"]
        assert len(requirements["capabilities"]) > 0
        assert any("text" in req for req in requirements["data_requirements"])
    
    async def test_analyze_ai_requirements_complex(self, roadmap_service, complex_opportunity):
        """Test AI requirements analysis for complex opportunity."""
        requirements = await roadmap_service._analyze_ai_requirements(complex_opportunity)
        
        # Verify multiple AI types detected
        assert len(requirements["ai_types"]) >= 3
        assert "nlp" in requirements["ai_types"]
        assert "computer_vision" in requirements["ai_types"]
        
        # Verify performance needs for real-time processing
        assert "low_latency" in requirements["performance_needs"]
        
        # Verify healthcare compliance requirements
        assert any("hipaa" in req.lower() for req in requirements["integration_requirements"])
    
    async def test_assess_technical_complexity_levels(self, roadmap_service, simple_opportunity, complex_opportunity):
        """Test technical complexity assessment."""
        # Simple opportunity should be low complexity
        simple_reqs = await roadmap_service._analyze_ai_requirements(simple_opportunity)
        simple_complexity = await roadmap_service._assess_technical_complexity(simple_opportunity, simple_reqs)
        assert simple_complexity in [ComplexityLevel.LOW, ComplexityLevel.MEDIUM]
        
        # Complex opportunity should be high complexity
        complex_reqs = await roadmap_service._analyze_ai_requirements(complex_opportunity)
        complex_complexity = await roadmap_service._assess_technical_complexity(complex_opportunity, complex_reqs)
        assert complex_complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]
    
    async def test_recommend_architecture_patterns(self, roadmap_service, simple_opportunity, complex_opportunity):
        """Test architecture pattern recommendations."""
        # Simple opportunity
        simple_reqs = await roadmap_service._analyze_ai_requirements(simple_opportunity)
        simple_complexity = await roadmap_service._assess_technical_complexity(simple_opportunity, simple_reqs)
        simple_arch = await roadmap_service._recommend_architecture(
            simple_opportunity, simple_reqs, simple_complexity, None
        )
        
        assert isinstance(simple_arch, ArchitectureRecommendation)
        assert simple_arch.pattern in [ArchitecturePattern.MONOLITHIC, ArchitecturePattern.SERVERLESS]
        assert len(simple_arch.advantages) > 0
        assert len(simple_arch.disadvantages) > 0
        
        # Complex opportunity
        complex_reqs = await roadmap_service._analyze_ai_requirements(complex_opportunity)
        complex_complexity = await roadmap_service._assess_technical_complexity(complex_opportunity, complex_reqs)
        complex_arch = await roadmap_service._recommend_architecture(
            complex_opportunity, complex_reqs, complex_complexity, None
        )
        
        assert isinstance(complex_arch, ArchitectureRecommendation)
        assert complex_arch.pattern in [ArchitecturePattern.MICROSERVICES, ArchitecturePattern.PIPELINE_ARCHITECTURE]
        assert complex_arch.scalability_rating >= simple_arch.scalability_rating
    
    async def test_recommend_technology_stack(self, roadmap_service, simple_opportunity):
        """Test technology stack recommendations."""
        ai_requirements = await roadmap_service._analyze_ai_requirements(simple_opportunity)
        complexity = await roadmap_service._assess_technical_complexity(simple_opportunity, ai_requirements)
        architecture = await roadmap_service._recommend_architecture(
            simple_opportunity, ai_requirements, complexity, None
        )
        
        tech_stack = await roadmap_service._recommend_technology_stack(
            simple_opportunity, ai_requirements, architecture, complexity
        )
        
        # Verify technology stack structure
        assert len(tech_stack) > 0
        assert all(isinstance(tech, TechnologyRecommendation) for tech in tech_stack)
        
        # Verify essential categories are covered
        categories = [tech.category for tech in tech_stack]
        assert TechnologyCategory.AI_FRAMEWORK in categories
        assert TechnologyCategory.BACKEND_FRAMEWORK in categories
        assert TechnologyCategory.DATABASE in categories
        assert TechnologyCategory.CLOUD_PLATFORM in categories
        
        # Verify all technologies have required fields
        for tech in tech_stack:
            assert tech.name
            assert tech.description
            assert tech.reasoning
            assert tech.complexity in [ComplexityLevel.LOW, ComplexityLevel.MEDIUM, ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]
            assert tech.learning_curve in ["low", "medium", "high"]
            assert tech.community_support in ["poor", "good", "excellent"]
            assert tech.license_type in ["open_source", "commercial", "hybrid"]
            assert isinstance(tech.alternatives, list)
    
    async def test_create_implementation_phases(self, roadmap_service, simple_opportunity):
        """Test implementation phase creation."""
        ai_requirements = await roadmap_service._analyze_ai_requirements(simple_opportunity)
        complexity = await roadmap_service._assess_technical_complexity(simple_opportunity, ai_requirements)
        architecture = await roadmap_service._recommend_architecture(
            simple_opportunity, ai_requirements, complexity, None
        )
        tech_stack = await roadmap_service._recommend_technology_stack(
            simple_opportunity, ai_requirements, architecture, complexity
        )
        
        phases = await roadmap_service._create_implementation_phases(
            simple_opportunity, architecture, tech_stack, complexity
        )
        
        # Verify phases structure
        assert len(phases) >= 4  # At least 4 standard phases
        assert all(isinstance(phase, ImplementationPhaseDetail) for phase in phases)
        
        # Verify phase order and types
        phase_types = [phase.phase for phase in phases]
        assert ImplementationPhase.RESEARCH_POC in phase_types
        assert ImplementationPhase.MVP_DEVELOPMENT in phase_types
        assert ImplementationPhase.BETA_TESTING in phase_types
        assert ImplementationPhase.PRODUCTION_LAUNCH in phase_types
        
        # Verify each phase has required fields
        for phase in phases:
            assert phase.name
            assert phase.description
            assert phase.duration_weeks > 0
            assert len(phase.key_deliverables) > 0
            assert len(phase.required_skills) > 0
            assert len(phase.success_criteria) > 0
            assert phase.estimated_effort_hours > 0
            assert phase.team_size_recommendation > 0
    
    async def test_generate_full_technical_roadmap(self, roadmap_service, simple_opportunity, mock_market_analysis):
        """Test complete technical roadmap generation."""
        mock_db = AsyncMock()
        
        roadmap = await roadmap_service.generate_technical_roadmap(
            mock_db, simple_opportunity, mock_market_analysis
        )
        
        # Verify roadmap structure
        assert isinstance(roadmap, TechnicalRoadmap)
        assert roadmap.roadmap_id.startswith("roadmap_")
        assert roadmap.opportunity_id == str(simple_opportunity.id)
        assert isinstance(roadmap.generated_at, datetime)
        
        # Verify all components are present
        assert isinstance(roadmap.architecture_recommendation, ArchitectureRecommendation)
        assert len(roadmap.technology_stack) > 0
        assert len(roadmap.implementation_phases) > 0
        assert roadmap.overall_complexity in [ComplexityLevel.LOW, ComplexityLevel.MEDIUM, ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]
        assert roadmap.estimated_timeline_weeks > 0
        assert roadmap.total_estimated_hours > 0
        assert roadmap.recommended_team_size > 0
        
        # Verify infrastructure and requirements
        assert isinstance(roadmap.infrastructure_requirements, dict)
        assert isinstance(roadmap.performance_targets, dict)
        assert isinstance(roadmap.security_considerations, list)
        assert isinstance(roadmap.scalability_plan, dict)
        assert isinstance(roadmap.key_technical_risks, list)
        
        # Verify to_dict method works
        roadmap_dict = roadmap.to_dict()
        assert isinstance(roadmap_dict, dict)
        assert "generated_at" in roadmap_dict
        assert "overall_complexity" in roadmap_dict
    
    async def test_ai_framework_recommendations(self, roadmap_service):
        """Test AI framework recommendation logic."""
        # Test simple NLP framework
        simple_ai_types = ["nlp"]
        simple_capabilities = ["text_processing"]
        
        framework = roadmap_service._recommend_ai_framework(simple_ai_types, simple_capabilities, ComplexityLevel.LOW)
        assert framework.category == TechnologyCategory.AI_FRAMEWORK
        assert framework.complexity in [ComplexityLevel.LOW, ComplexityLevel.MEDIUM]
        
        # Test advanced framework for complex requirements
        complex_ai_types = ["nlp", "computer_vision"]
        complex_capabilities = ["transformer", "deep_learning", "neural_networks"]
        
        framework = roadmap_service._recommend_ai_framework(complex_ai_types, complex_capabilities, ComplexityLevel.VERY_HIGH)
        assert framework.category == TechnologyCategory.AI_FRAMEWORK
        assert "pytorch" in framework.name.lower() or "tensorflow" in framework.name.lower()
    
    async def test_infrastructure_cost_estimation(self, roadmap_service, simple_opportunity):
        """Test infrastructure cost estimation."""
        ai_requirements = await roadmap_service._analyze_ai_requirements(simple_opportunity)
        architecture = ArchitectureRecommendation(
            pattern=ArchitecturePattern.SERVERLESS,
            description="Test architecture",
            advantages=[], disadvantages=[], best_use_cases=[],
            complexity=ComplexityLevel.MEDIUM,
            scalability_rating=8, development_speed_rating=9, maintenance_rating=8
        )
        tech_stack = [
            TechnologyRecommendation(
                name="FastAPI", category=TechnologyCategory.BACKEND_FRAMEWORK,
                description="Test", reasoning="Test", complexity=ComplexityLevel.MEDIUM,
                learning_curve="medium", community_support="excellent",
                license_type="open_source", alternatives=[], integration_effort="moderate"
            )
        ]
        
        infrastructure = await roadmap_service._define_infrastructure_requirements(
            simple_opportunity, architecture, tech_stack, None
        )
        
        # Verify infrastructure structure
        assert "compute" in infrastructure
        assert "storage" in infrastructure
        assert "network" in infrastructure
        assert "estimated_monthly_cost" in infrastructure
        
        # Verify cost estimation
        monthly_cost = infrastructure["estimated_monthly_cost"]
        assert "total_monthly_usd" in monthly_cost
        assert monthly_cost["total_monthly_usd"] > 0
        assert monthly_cost["compute_monthly_usd"] >= 0
        assert monthly_cost["storage_monthly_usd"] >= 0
        assert monthly_cost["network_monthly_usd"] >= 0
    
    async def test_performance_targets_definition(self, roadmap_service, simple_opportunity, complex_opportunity):
        """Test performance targets definition."""
        # Simple opportunity targets
        simple_targets = await roadmap_service._define_performance_targets(simple_opportunity, None)
        
        assert "response_time_ms" in simple_targets
        assert "availability_percent" in simple_targets
        assert "throughput_requests_per_second" in simple_targets
        assert "ai_model_accuracy_percent" in simple_targets
        
        # Complex real-time opportunity should have stricter targets
        complex_targets = await roadmap_service._define_performance_targets(complex_opportunity, None)
        
        # Real-time requirements should result in lower latency targets
        assert complex_targets["response_time_ms"] <= simple_targets["response_time_ms"]
        assert complex_targets["availability_percent"] >= simple_targets["availability_percent"]
    
    async def test_security_considerations(self, roadmap_service, simple_opportunity, complex_opportunity):
        """Test security considerations generation."""
        simple_tech_stack = []
        simple_security = await roadmap_service._define_security_considerations(simple_opportunity, simple_tech_stack)
        
        # Verify basic security measures
        assert len(simple_security) > 0
        assert any("oauth" in consideration.lower() for consideration in simple_security)
        assert any("https" in consideration.lower() for consideration in simple_security)
        
        # Healthcare opportunity should have additional compliance requirements
        complex_tech_stack = []
        complex_security = await roadmap_service._define_security_considerations(complex_opportunity, complex_tech_stack)
        
        # Should include HIPAA compliance for healthcare
        assert any("hipaa" in consideration.lower() for consideration in complex_security)
        assert len(complex_security) > len(simple_security)


@pytest.mark.asyncio
class TestTechnicalRoadmapEdgeCases:
    """Test edge cases for technical roadmap service."""
    
    async def test_malformed_opportunity_data(self, roadmap_service):
        """Test handling of malformed opportunity data."""
        opportunity = MagicMock(spec=Opportunity)
        opportunity.id = "malformed-123"
        opportunity.title = "Test"
        opportunity.description = None
        opportunity.ai_solution_types = "invalid_json"
        opportunity.target_industries = None
        opportunity.required_capabilities = "also_invalid"
        
        # Should handle malformed data gracefully
        ai_requirements = await roadmap_service._analyze_ai_requirements(opportunity)
        
        # Should return default structure even with malformed data
        assert "ai_types" in ai_requirements
        assert "capabilities" in ai_requirements
        assert isinstance(ai_requirements["ai_types"], list)
        assert isinstance(ai_requirements["capabilities"], list)
        
        # Should still assess complexity
        complexity = await roadmap_service._assess_technical_complexity(opportunity, ai_requirements)
        assert complexity in [ComplexityLevel.LOW, ComplexityLevel.MEDIUM, ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]
    
    async def test_minimal_opportunity(self, roadmap_service):
        """Test roadmap generation for minimal opportunity data."""
        opportunity = MagicMock(spec=Opportunity)
        opportunity.id = "minimal-123"
        opportunity.title = "Minimal AI"
        opportunity.description = "Simple AI solution"
        opportunity.ai_solution_types = json.dumps(["machine_learning"])
        opportunity.target_industries = json.dumps(["general"])
        opportunity.required_capabilities = json.dumps(["basic_ml"])
        
        mock_db = AsyncMock()
        
        # Should generate roadmap even with minimal data
        roadmap = await roadmap_service.generate_technical_roadmap(mock_db, opportunity, None)
        
        assert isinstance(roadmap, TechnicalRoadmap)
        assert len(roadmap.technology_stack) > 0
        assert len(roadmap.implementation_phases) > 0
        assert roadmap.estimated_timeline_weeks > 0
    
    async def test_team_size_recommendations(self, roadmap_service):
        """Test team size recommendation logic."""
        # Small project
        small_team = await roadmap_service._recommend_team_size(ComplexityLevel.LOW, 1000, 10)
        assert 2 <= small_team <= 5
        
        # Large project
        large_team = await roadmap_service._recommend_team_size(ComplexityLevel.VERY_HIGH, 5000, 20)
        assert large_team >= small_team
        assert large_team <= 12  # Should cap at reasonable size


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])