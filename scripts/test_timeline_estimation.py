#!/usr/bin/env python3
"""
Test script for Timeline Estimation Service.

This script demonstrates the timeline estimation capabilities
including development timeline algorithms and resource requirement analysis.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from datetime import datetime
from unittest.mock import Mock

from shared.services.timeline_estimation_service import (
    TimelineEstimationService,
    EstimationMethod,
    ResourceType,
    ComplexityLevel
)
from shared.services.technical_roadmap_service import (
    TechnicalRoadmap,
    ArchitecturePattern,
    ArchitectureRecommendation,
    ImplementationPhase,
    ImplementationPhaseDetail
)
from shared.models.opportunity import Opportunity


async def test_timeline_estimation():
    """Test timeline estimation functionality."""
    print("🚀 Testing Timeline Estimation Service")
    print("=" * 50)
    
    # Initialize service
    service = TimelineEstimationService()
    print("✅ Timeline Estimation Service initialized")
    
    # Create mock opportunity
    opportunity = Mock(spec=Opportunity)
    opportunity.id = "test-opportunity-123"
    opportunity.title = "AI-Powered Customer Service Bot"
    opportunity.description = "Real-time AI chatbot for customer support with NLP capabilities and sentiment analysis"
    opportunity.ai_solution_types = '["nlp", "machine_learning", "sentiment_analysis"]'
    opportunity.target_industries = '["finance", "retail", "healthcare"]'
    opportunity.required_capabilities = '["transformer", "bert", "conversation_management", "real_time_processing"]'
    
    print(f"📋 Mock Opportunity: {opportunity.title}")
    
    # Create mock technical roadmap
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
    phases = []
    
    # Research POC Phase
    poc_phase = Mock(spec=ImplementationPhaseDetail)
    poc_phase.phase = ImplementationPhase.RESEARCH_POC
    poc_phase.duration_weeks = 8
    poc_phase.estimated_effort_hours = 640
    poc_phase.key_deliverables = ["Requirements document", "AI model prototype", "Architecture design"]
    poc_phase.required_skills = ["AI/ML Engineering", "Data Science", "System Architecture"]
    phases.append(poc_phase)
    
    # MVP Development Phase
    mvp_phase = Mock(spec=ImplementationPhaseDetail)
    mvp_phase.phase = ImplementationPhase.MVP_DEVELOPMENT
    mvp_phase.duration_weeks = 16
    mvp_phase.estimated_effort_hours = 1280
    mvp_phase.key_deliverables = ["Backend API", "AI model integration", "Frontend interface"]
    mvp_phase.required_skills = ["Backend Development", "AI/ML Engineering", "Frontend Development"]
    phases.append(mvp_phase)
    
    # Beta Testing Phase
    beta_phase = Mock(spec=ImplementationPhaseDetail)
    beta_phase.phase = ImplementationPhase.BETA_TESTING
    beta_phase.duration_weeks = 8
    beta_phase.estimated_effort_hours = 640
    beta_phase.key_deliverables = ["Beta environment", "User feedback", "Performance optimization"]
    beta_phase.required_skills = ["DevOps", "QA Engineering", "Product Management"]
    phases.append(beta_phase)
    
    roadmap.implementation_phases = phases
    
    print(f"🏗️  Technical Roadmap: {roadmap.overall_complexity.value} complexity, {len(phases)} phases")
    
    # Test different estimation methods
    estimation_methods = [
        EstimationMethod.EXPERT_JUDGMENT,
        EstimationMethod.FUNCTION_POINT,
        EstimationMethod.STORY_POINT,
        EstimationMethod.MONTE_CARLO
    ]
    
    db_mock = Mock()  # Mock database session
    
    for method in estimation_methods:
        print(f"\n📊 Testing {method.value} estimation method:")
        print("-" * 40)
        
        try:
            # Generate timeline estimate
            estimate = await service.generate_timeline_estimate(
                db_mock,
                opportunity,
                roadmap,
                estimation_method=method
            )
            
            print(f"✅ Estimation completed successfully")
            print(f"   📅 Total Duration: {estimate.total_duration_days} days")
            print(f"   🎯 Confidence Level: {estimate.confidence_level:.2%}")
            print(f"   📋 Number of Tasks: {len(estimate.task_estimates)}")
            print(f"   👥 Team Composition: {len(estimate.resource_allocation.team_composition)} roles")
            print(f"   💰 Estimated Cost: ${estimate.resource_allocation.estimated_cost_total:,.2f}")
            print(f"   ⚠️  Timeline Risks: {len(estimate.timeline_risks)} identified")
            
            # Show resource breakdown
            print(f"   🔧 Resource Allocation:")
            for resource_type, count in estimate.resource_allocation.team_composition.items():
                print(f"      - {resource_type.value}: {count} person(s)")
            
            # Show critical path
            if estimate.critical_path:
                print(f"   🎯 Critical Path: {len(estimate.critical_path)} tasks")
                print(f"      First task: {estimate.critical_path[0] if estimate.critical_path else 'N/A'}")
            
            # Show Monte Carlo results if available
            if estimate.monte_carlo_simulation:
                mc = estimate.monte_carlo_simulation
                print(f"   🎲 Monte Carlo Simulation:")
                print(f"      Iterations: {mc.iterations}")
                print(f"      Mean Duration: {mc.mean_duration_days:.1f} days")
                print(f"      90% Confidence: {mc.confidence_intervals.get('90%', 'N/A')} days")
                print(f"      Risk Scenarios: {len(mc.risk_scenarios)}")
            
            # Show top risks
            if estimate.timeline_risks:
                print(f"   ⚠️  Top Timeline Risks:")
                for i, risk in enumerate(estimate.timeline_risks[:3]):
                    print(f"      {i+1}. {risk.description} ({risk.probability:.1%} chance, {risk.impact_days} days impact)")
            
        except Exception as e:
            print(f"❌ Error with {method.value}: {str(e)}")
    
    # Test specific timeline estimation algorithms
    print(f"\n🧮 Testing Timeline Estimation Algorithms:")
    print("-" * 40)
    
    # Test task decomposition
    print("📝 Testing task decomposition...")
    tasks = await service._create_detailed_task_estimates(
        opportunity, roadmap, EstimationMethod.EXPERT_JUDGMENT
    )
    print(f"   ✅ Generated {len(tasks)} detailed tasks")
    
    # Show sample tasks
    for i, task in enumerate(tasks[:3]):
        print(f"   {i+1}. {task.name}")
        print(f"      Estimated: {task.estimated_hours}h (±{task.pessimistic_hours - task.optimistic_hours}h)")
        print(f"      Confidence: {task.confidence_level:.1%}")
        print(f"      Resources: {[r.value for r in task.required_resources]}")
    
    # Test resource analysis
    print("\n👥 Testing resource requirement analysis...")
    resource_allocation = await service._analyze_resource_requirements(
        tasks, roadmap, None
    )
    print(f"   ✅ Analyzed resource requirements")
    print(f"   💰 Total Cost: ${resource_allocation.estimated_cost_total:,.2f}")
    print(f"   📅 Monthly Burn: ${resource_allocation.estimated_cost_monthly:,.2f}")
    print(f"   ⚡ Optimization Opportunities: {len(resource_allocation.optimization_recommendations)}")
    
    # Test risk identification
    print("\n⚠️  Testing timeline risk identification...")
    risks = await service._identify_timeline_risks(opportunity, roadmap, tasks)
    print(f"   ✅ Identified {len(risks)} timeline risks")
    
    risk_categories = {}
    for risk in risks:
        category = risk.category.value
        risk_categories[category] = risk_categories.get(category, 0) + 1
    
    for category, count in risk_categories.items():
        print(f"   - {category}: {count} risks")
    
    # Test critical path analysis
    print("\n🎯 Testing critical path analysis...")
    critical_path = await service._analyze_critical_path(tasks)
    print(f"   ✅ Critical path identified with {len(critical_path)} tasks")
    
    if critical_path:
        critical_tasks = [task for task in tasks if task.task_id in critical_path]
        total_critical_hours = sum(task.estimated_hours for task in critical_tasks)
        print(f"   ⏱️  Critical path duration: {total_critical_hours} hours")
        print(f"   📋 Critical tasks: {', '.join(critical_path[:3])}{'...' if len(critical_path) > 3 else ''}")
    
    print(f"\n🎉 Timeline Estimation Service testing completed successfully!")
    print("=" * 50)


def test_estimation_algorithms():
    """Test specific estimation algorithms."""
    print("\n🔬 Testing Estimation Algorithms:")
    print("-" * 30)
    
    service = TimelineEstimationService()
    
    # Test Fibonacci rounding for story points
    test_values = [1.2, 2.8, 7.1, 15.0, 25.0]
    print("📊 Fibonacci Rounding:")
    for value in test_values:
        rounded = service._round_to_fibonacci(value)
        print(f"   {value} → {rounded}")
    
    # Test team velocity estimation
    print("\n⚡ Team Velocity by Complexity:")
    for complexity in ComplexityLevel:
        velocity = service._estimate_team_velocity(complexity)
        print(f"   {complexity.value}: {velocity:.2f}")
    
    # Test resource rates
    print("\n💰 Resource Rates (sample):")
    sample_resources = [ResourceType.AI_ML_ENGINEER, ResourceType.BACKEND_DEVELOPER, ResourceType.DATA_SCIENTIST]
    for resource in sample_resources:
        rates = service.resource_rates.get(resource, {})
        junior_rate = rates.get("junior", 0)
        senior_rate = rates.get("senior", 0)
        print(f"   {resource.value}: ${junior_rate}/hr (junior) - ${senior_rate}/hr (senior)")


if __name__ == "__main__":
    print("🧪 Timeline Estimation Service Test Suite")
    print("=" * 60)
    
    # Run async tests
    asyncio.run(test_timeline_estimation())
    
    # Run sync tests
    test_estimation_algorithms()
    
    print("\n✅ All tests completed!")