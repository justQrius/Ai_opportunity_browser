"""
Test suite for team composition analysis functionality.

Tests the implementation of task 7.2.3: Team Composition Analysis
- Skill requirement identification
- Team size and role recommendations
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from shared.services.technical_roadmap_service import (
    TechnicalRoadmapService,
    ComplexityLevel,
    ArchitecturePattern,
    ArchitectureRecommendation,
    TechnologyRecommendation,
    TechnologyCategory,
    ImplementationPhaseDetail,
    ImplementationPhase,
    RoleType,
    ExperienceLevel,
    CommitmentType
)
from shared.models.opportunity import Opportunity


class TestTeamCompositionAnalysis:
    """Test team composition analysis functionality."""
    
    @pytest.fixture
    def service(self):
        """Create TechnicalRoadmapService instance."""
        return TechnicalRoadmapService()
    
    @pytest.fixture
    def sample_opportunity(self):
        """Create sample opportunity for testing."""
        opportunity = MagicMock(spec=Opportunity)
        opportunity.id = "test-opportunity-123"
        opportunity.title = "AI-Powered Customer Support Chatbot"
        opportunity.description = "Real-time AI chatbot for customer support with NLP capabilities"
        opportunity.ai_solution_types = '["nlp", "machine_learning"]'
        opportunity.required_capabilities = '["transformer", "bert", "sentiment_analysis"]'
        opportunity.target_industries = '["customer_service", "retail"]'
        return opportunity
    
    @pytest.fixture
    def sample_architecture(self):
        """Create sample architecture recommendation."""
        return ArchitectureRecommendation(
            pattern=ArchitecturePattern.MICROSERVICES,
            description="Microservices architecture for scalable AI platform",
            advantages=["Independent scaling", "Technology diversity"],
            disadvantages=["Operational complexity"],
            best_use_cases=["Multi-modal AI platforms"],
            complexity=ComplexityLevel.HIGH,
            scalability_rating=9,
            development_speed_rating=6,
            maintenance_rating=5
        )
    
    @pytest.fixture
    def sample_tech_stack(self):
        """Create sample technology stack."""
        return [
            TechnologyRecommendation(
                name="PyTorch + Transformers",
                category=TechnologyCategory.AI_FRAMEWORK,
                description="Advanced deep learning framework",
                reasoning="Best for transformer models",
                complexity=ComplexityLevel.HIGH,
                learning_curve="high",
                community_support="excellent",
                license_type="open_source",
                alternatives=["TensorFlow"],
                integration_effort="moderate"
            ),
            TechnologyRecommendation(
                name="FastAPI",
                category=TechnologyCategory.BACKEND_FRAMEWORK,
                description="Modern API framework",
                reasoning="High performance with async support",
                complexity=ComplexityLevel.MEDIUM,
                learning_curve="medium",
                community_support="excellent",
                license_type="open_source",
                alternatives=["Django"],
                integration_effort="moderate"
            )
        ]
    
    @pytest.fixture
    def sample_phases(self):
        """Create sample implementation phases."""
        return [
            ImplementationPhaseDetail(
                phase=ImplementationPhase.RESEARCH_POC,
                name="Research & Proof of Concept",
                description="Initial research and prototype development",
                duration_weeks=4,
                key_deliverables=["AI model prototype", "Architecture design"],
                required_skills=["AI/ML", "Research"],
                technologies_introduced=["PyTorch", "Transformers"],
                success_criteria=["Working prototype", "Performance benchmarks"],
                risks=["Model performance", "Technical feasibility"],
                dependencies=[],
                estimated_effort_hours=320,
                team_size_recommendation=3
            ),
            ImplementationPhaseDetail(
                phase=ImplementationPhase.MVP_DEVELOPMENT,
                name="MVP Development",
                description="Minimum viable product development",
                duration_weeks=8,
                key_deliverables=["API endpoints", "Basic UI", "Model integration"],
                required_skills=["Backend", "Frontend", "AI/ML"],
                technologies_introduced=["FastAPI", "React"],
                success_criteria=["Working MVP", "User testing"],
                risks=["Integration complexity", "Performance"],
                dependencies=["Research POC"],
                estimated_effort_hours=640,
                team_size_recommendation=5
            )
        ]
    
    @pytest.mark.asyncio
    async def test_skill_requirement_identification(self, service, sample_opportunity, sample_architecture, sample_tech_stack, sample_phases):
        """Test skill requirement identification."""
        skills = await service._identify_skill_requirements(
            sample_opportunity,
            sample_architecture,
            sample_tech_stack,
            sample_phases,
            ComplexityLevel.HIGH
        )
        
        # Verify skill categories are present
        assert "ai_ml" in skills
        assert "backend" in skills
        assert "devops" in skills
        assert "product" in skills
        assert "security" in skills
        
        # Verify AI/ML skills are identified
        ai_skills = skills["ai_ml"]
        assert len(ai_skills) > 0
        
        # Check for NLP-specific skills
        nlp_skills = [skill for skill in ai_skills if "nlp" in skill.skill_name.lower() or "language" in skill.skill_name.lower()]
        assert len(nlp_skills) > 0
        
        # Verify skill structure
        for skill in ai_skills:
            assert hasattr(skill, 'skill_name')
            assert hasattr(skill, 'importance')
            assert hasattr(skill, 'proficiency_level')
            assert hasattr(skill, 'alternatives')
            assert hasattr(skill, 'learning_resources')
            assert skill.importance in ["critical", "important", "nice_to_have"]
            assert skill.proficiency_level in ["basic", "intermediate", "advanced", "expert"]
    
    @pytest.mark.asyncio
    async def test_role_recommendations_generation(self, service, sample_architecture, sample_tech_stack):
        """Test role recommendations generation."""
        # Mock skill requirements
        required_skills = {
            "ai_ml": [MagicMock(skill_name="PyTorch", importance="critical")],
            "backend": [MagicMock(skill_name="FastAPI", importance="critical")],
            "devops": [MagicMock(skill_name="Docker", importance="important")],
            "product": [MagicMock(skill_name="Product Management", importance="critical")],
            "data": [],
            "frontend": [],
            "design": [],
            "security": [],
            "research": []
        }
        
        roles = await service._generate_role_recommendations(
            required_skills,
            sample_architecture,
            ComplexityLevel.HIGH,
            timeline_weeks=16,
            total_hours=1000
        )
        
        # Verify essential roles are present
        role_types = [role.role_type for role in roles]
        assert RoleType.AI_ML_ENGINEER in role_types
        assert RoleType.BACKEND_DEVELOPER in role_types
        assert RoleType.PRODUCT_MANAGER in role_types
        
        # Verify role structure
        for role in roles:
            assert hasattr(role, 'role_type')
            assert hasattr(role, 'role_title')
            assert hasattr(role, 'description')
            assert hasattr(role, 'required_skills')
            assert hasattr(role, 'experience_level')
            assert hasattr(role, 'commitment_type')
            assert hasattr(role, 'estimated_hours_per_week')
            assert hasattr(role, 'salary_range')
            assert hasattr(role, 'justification')
            
            # Verify enums are used correctly
            assert isinstance(role.role_type, RoleType)
            assert isinstance(role.experience_level, ExperienceLevel)
            assert isinstance(role.commitment_type, CommitmentType)
            
            # Verify salary range structure
            assert "min" in role.salary_range
            assert "max" in role.salary_range
            assert "currency" in role.salary_range
    
    @pytest.mark.asyncio
    async def test_team_structure_calculation(self, service, sample_phases):
        """Test team structure calculation."""
        # Mock recommended roles
        mock_roles = [
            MagicMock(
                commitment_type=CommitmentType.FULL_TIME,
                experience_level=ExperienceLevel.SENIOR,
                role_type=RoleType.AI_ML_ENGINEER,
                phases_involved=[ImplementationPhase.RESEARCH_POC, ImplementationPhase.MVP_DEVELOPMENT]
            ),
            MagicMock(
                commitment_type=CommitmentType.FULL_TIME,
                experience_level=ExperienceLevel.MID_LEVEL,
                role_type=RoleType.BACKEND_DEVELOPER,
                phases_involved=[ImplementationPhase.MVP_DEVELOPMENT]
            ),
            MagicMock(
                commitment_type=CommitmentType.PART_TIME,
                experience_level=ExperienceLevel.SENIOR,
                role_type=RoleType.PRODUCT_MANAGER,
                phases_involved=[ImplementationPhase.RESEARCH_POC, ImplementationPhase.MVP_DEVELOPMENT]
            )
        ]
        
        structure = await service._calculate_team_structure(mock_roles, sample_phases)
        
        # Verify structure components
        assert "total_roles" in structure
        assert "full_time_roles" in structure
        assert "part_time_roles" in structure
        assert "consultant_roles" in structure
        assert "experience_distribution" in structure
        assert "role_distribution" in structure
        assert "phase_coverage" in structure
        
        # Verify counts
        assert structure["total_roles"] == 3
        assert structure["full_time_roles"] == 2
        assert structure["part_time_roles"] == 1
        assert structure["consultant_roles"] == 0
    
    @pytest.mark.asyncio
    async def test_skill_matrix_creation(self, service):
        """Test skill matrix creation."""
        # Mock roles with skills
        mock_skill1 = MagicMock(skill_name="Python")
        mock_skill2 = MagicMock(skill_name="PyTorch")
        mock_skill3 = MagicMock(skill_name="FastAPI")
        
        mock_roles = [
            MagicMock(role_title="AI/ML Engineer", required_skills=[mock_skill1, mock_skill2]),
            MagicMock(role_title="Backend Developer", required_skills=[mock_skill1, mock_skill3])
        ]
        
        skill_matrix = await service._create_skill_matrix(mock_roles)
        
        # Verify skill matrix structure
        assert "Python" in skill_matrix
        assert "PyTorch" in skill_matrix
        assert "FastAPI" in skill_matrix
        
        # Verify role assignments
        assert "AI/ML Engineer" in skill_matrix["Python"]
        assert "Backend Developer" in skill_matrix["Python"]
        assert "AI/ML Engineer" in skill_matrix["PyTorch"]
        assert "Backend Developer" in skill_matrix["FastAPI"]
    
    @pytest.mark.asyncio
    async def test_hiring_timeline_generation(self, service, sample_phases):
        """Test hiring timeline generation."""
        # Mock roles
        mock_roles = [
            MagicMock(
                role_type=RoleType.TECHNICAL_LEAD,
                role_title="Technical Lead",
                phases_involved=[ImplementationPhase.RESEARCH_POC]
            ),
            MagicMock(
                role_type=RoleType.AI_ML_ENGINEER,
                role_title="AI/ML Engineer",
                phases_involved=[ImplementationPhase.RESEARCH_POC, ImplementationPhase.MVP_DEVELOPMENT]
            ),
            MagicMock(
                role_type=RoleType.FRONTEND_DEVELOPER,
                role_title="Frontend Developer",
                phases_involved=[ImplementationPhase.MVP_DEVELOPMENT]
            )
        ]
        
        timeline = await service._generate_hiring_timeline(mock_roles, sample_phases)
        
        # Verify timeline structure
        assert "immediate_hires" in timeline
        assert "phase_based_hires" in timeline
        assert "hiring_priorities" in timeline
        assert "total_hiring_duration_weeks" in timeline
        
        # Verify immediate hires include critical roles
        immediate_roles = [hire["role"] for hire in timeline["immediate_hires"]]
        assert "Technical Lead" in immediate_roles
        assert "AI/ML Engineer" in immediate_roles
    
    @pytest.mark.asyncio
    async def test_budget_calculation(self, service):
        """Test team budget calculation."""
        # Mock roles with salary ranges
        mock_roles = [
            MagicMock(
                role_title="AI/ML Engineer",
                commitment_type=CommitmentType.FULL_TIME,
                salary_range={"min": 120000, "max": 180000, "currency": "USD"}
            ),
            MagicMock(
                role_title="Backend Developer",
                commitment_type=CommitmentType.FULL_TIME,
                salary_range={"min": 90000, "max": 140000, "currency": "USD"}
            ),
            MagicMock(
                role_title="Consultant",
                commitment_type=CommitmentType.CONSULTANT,
                salary_range={"min": 150, "max": 300, "currency": "USD_per_hour"},
                estimated_hours_per_week=20
            )
        ]
        
        budget = await service._calculate_team_budget(mock_roles, timeline_weeks=20)
        
        # Verify budget structure
        assert "annual_salary_costs" in budget
        assert "total_annual_cost" in budget
        assert "project_cost_estimate" in budget
        assert "cost_breakdown" in budget
        assert "cost_optimization_suggestions" in budget
        
        # Verify calculations
        assert budget["total_annual_cost"] > 0
        assert budget["project_cost_estimate"] > 0
        assert len(budget["annual_salary_costs"]) == 3
    
    @pytest.mark.asyncio
    async def test_complete_team_composition_analysis(self, service, sample_opportunity, sample_architecture, sample_tech_stack, sample_phases):
        """Test complete team composition analysis integration."""
        analysis = await service._analyze_team_composition(
            sample_opportunity,
            sample_architecture,
            sample_tech_stack,
            sample_phases,
            ComplexityLevel.HIGH,
            timeline_weeks=16,
            total_hours=1000
        )
        
        # Verify analysis structure
        assert hasattr(analysis, 'analysis_id')
        assert hasattr(analysis, 'opportunity_id')
        assert hasattr(analysis, 'generated_at')
        assert hasattr(analysis, 'recommended_roles')
        assert hasattr(analysis, 'total_team_size')
        assert hasattr(analysis, 'team_structure')
        assert hasattr(analysis, 'skill_matrix')
        assert hasattr(analysis, 'hiring_timeline')
        assert hasattr(analysis, 'budget_implications')
        assert hasattr(analysis, 'scaling_recommendations')
        assert hasattr(analysis, 'risk_mitigation')
        assert hasattr(analysis, 'alternative_compositions')
        
        # Verify data types and content
        assert isinstance(analysis.recommended_roles, list)
        assert len(analysis.recommended_roles) > 0
        assert analysis.total_team_size > 0
        assert isinstance(analysis.team_structure, dict)
        assert isinstance(analysis.skill_matrix, dict)
        assert isinstance(analysis.hiring_timeline, dict)
        assert isinstance(analysis.budget_implications, dict)
        assert isinstance(analysis.scaling_recommendations, list)
        assert isinstance(analysis.risk_mitigation, list)
        assert isinstance(analysis.alternative_compositions, list)
        
        # Verify analysis can be serialized
        analysis_dict = analysis.to_dict()
        assert isinstance(analysis_dict, dict)
        assert "recommended_roles" in analysis_dict
        assert "team_structure" in analysis_dict


if __name__ == "__main__":
    # Run basic test
    async def run_basic_test():
        service = TechnicalRoadmapService()
        
        # Create mock opportunity
        opportunity = MagicMock(spec=Opportunity)
        opportunity.id = "test-123"
        opportunity.title = "Test AI Opportunity"
        opportunity.description = "Test AI application with NLP capabilities"
        opportunity.ai_solution_types = '["nlp", "machine_learning"]'
        opportunity.required_capabilities = '["transformer"]'
        opportunity.target_industries = '["technology"]'
        
        # Test skill identification
        architecture = ArchitectureRecommendation(
            pattern=ArchitecturePattern.MICROSERVICES,
            description="Test architecture",
            advantages=["Scalable"],
            disadvantages=["Complex"],
            best_use_cases=["AI platforms"],
            complexity=ComplexityLevel.HIGH,
            scalability_rating=8,
            development_speed_rating=6,
            maintenance_rating=5
        )
        
        tech_stack = [
            TechnologyRecommendation(
                name="PyTorch",
                category=TechnologyCategory.AI_FRAMEWORK,
                description="AI framework",
                reasoning="Best for AI",
                complexity=ComplexityLevel.HIGH,
                learning_curve="high",
                community_support="excellent",
                license_type="open_source",
                alternatives=["TensorFlow"],
                integration_effort="moderate"
            )
        ]
        
        phases = [
            ImplementationPhaseDetail(
                phase=ImplementationPhase.RESEARCH_POC,
                name="Research POC",
                description="Initial research",
                duration_weeks=4,
                key_deliverables=["Prototype"],
                required_skills=["AI/ML"],
                technologies_introduced=["PyTorch"],
                success_criteria=["Working prototype"],
                risks=["Technical feasibility"],
                dependencies=[],
                estimated_effort_hours=320,
                team_size_recommendation=3
            )
        ]
        
        # Test complete analysis
        analysis = await service._analyze_team_composition(
            opportunity, architecture, tech_stack, phases,
            ComplexityLevel.HIGH, 16, 1000
        )
        
        print("✅ Team Composition Analysis Test Passed!")
        print(f"   📊 Analysis ID: {analysis.analysis_id}")
        print(f"   👥 Total Team Size: {analysis.total_team_size}")
        print(f"   🎯 Recommended Roles: {len(analysis.recommended_roles)}")
        print(f"   💰 Budget Implications: ${analysis.budget_implications.get('total_annual_cost', 0):,.2f}")
        print(f"   📈 Scaling Recommendations: {len(analysis.scaling_recommendations)}")
        
        return True
    
    # Run the test
    result = asyncio.run(run_basic_test())
    if result:
        print("\n🎉 Team Composition Analysis implementation completed successfully!")