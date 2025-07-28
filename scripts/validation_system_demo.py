#!/usr/bin/env python3
"""
ValidationSystem Demo Script

This script demonstrates the core functionality of the ValidationSystem,
including workflow management and validation aggregation logic.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any

# Mock classes for demonstration
class MockDB:
    """Mock database session for demo purposes."""
    async def commit(self):
        pass

class MockOpportunity:
    """Mock opportunity for demo purposes."""
    def __init__(self, opportunity_id: str, title: str):
        self.id = opportunity_id
        self.title = title
        self.status = "discovered"

class MockValidation:
    """Mock validation result for demo purposes."""
    def __init__(self, validation_id: str, opportunity_id: str, validator_id: str, 
                 validation_type: str, score: float, confidence: float = 8.0):
        self.id = validation_id
        self.opportunity_id = opportunity_id
        self.validator_id = validator_id
        self.validation_type = validation_type
        self.score = score
        self.confidence = confidence
        self.evidence_links = '["https://evidence1.com", "https://evidence2.com"]'
        self.strengths = f"Strong {validation_type} validation"
        self.weaknesses = f"Some concerns about {validation_type}"
        self.recommendations = f"Recommend focusing on {validation_type} improvements"
        self.helpful_votes = 8
        self.unhelpful_votes = 2
        self.expertise_relevance = 8.5
        self.methodology = f"Expert analysis for {validation_type}"
        self.supporting_data = '{"analysis": "detailed"}'
        self.comments = f"Detailed comments about {validation_type}"

class MockUser:
    """Mock user for demo purposes."""
    def __init__(self, user_id: str, username: str, role: str = "user", reputation: float = 7.0):
        self.id = user_id
        self.username = username
        self.role = role
        self.reputation_score = reputation

# Import the actual ValidationSystem
from shared.services.validation_system import (
    ValidationSystem, 
    ValidationPriority, 
    ValidationType,
    ValidationWorkflowStatus
)

async def demo_validation_workflow():
    """Demonstrate validation workflow management."""
    print("🔄 ValidationSystem Workflow Demo")
    print("=" * 50)
    
    # Initialize system
    validation_system = ValidationSystem()
    mock_db = MockDB()
    
    # Mock services
    async def mock_get_opportunity(db, opp_id, include_relationships=False):
        return MockOpportunity(opp_id, f"AI Opportunity {opp_id}")
    
    async def mock_get_validations(db, opp_id):
        return []
    
    # Patch the services for demo
    import shared.services.validation_system as vs_module
    vs_module.opportunity_service.get_opportunity_by_id = mock_get_opportunity
    vs_module.validation_service.get_opportunity_validations = mock_get_validations
    
    # 1. Initiate validation workflow
    print("\n1. Initiating Validation Workflow")
    print("-" * 30)
    
    workflow = await validation_system.initiate_validation_workflow(
        mock_db,
        "opp-demo-123",
        priority=ValidationPriority.HIGH,
        target_validator_count=5,
        min_expert_validations=2
    )
    
    print(f"✅ Workflow created for opportunity: {workflow.opportunity_id}")
    print(f"   Status: {workflow.status.value}")
    print(f"   Priority: {workflow.priority.value}")
    print(f"   Required validation types: {len(workflow.required_validation_types)}")
    print(f"   Completion: {workflow.completion_percentage:.1f}%")
    
    # 2. Simulate validation updates
    print("\n2. Simulating Validation Updates")
    print("-" * 30)
    
    # Add some mock validations
    validations = [
        MockValidation("val-1", "opp-demo-123", "user-1", "market_demand", 8.5),
        MockValidation("val-2", "opp-demo-123", "user-2", "technical_feasibility", 7.0),
        MockValidation("val-3", "opp-demo-123", "user-3", "business_viability", 6.5)
    ]
    
    # Mock user service
    async def mock_get_user(db, user_id):
        users = {
            "user-1": MockUser("user-1", "expert1", "expert", 9.0),
            "user-2": MockUser("user-2", "expert2", "expert", 8.5),
            "user-3": MockUser("user-3", "user3", "user", 6.0)
        }
        return users.get(user_id)
    
    vs_module.user_service.get_user_by_id = mock_get_user
    
    for validation in validations:
        updated_workflow = await validation_system.update_validation_workflow(
            mock_db, "opp-demo-123", validation
        )
        print(f"   Added {validation.validation_type} validation (score: {validation.score})")
        print(f"   Workflow completion: {updated_workflow.completion_percentage:.1f}%")
    
    # 3. Get active workflows
    print("\n3. Active Workflows")
    print("-" * 30)
    
    active_workflows = await validation_system.get_active_workflows()
    for wf in active_workflows:
        print(f"   Opportunity: {wf.opportunity_id}")
        print(f"   Status: {wf.status.value}")
        print(f"   Priority: {wf.priority.value}")
        print(f"   Completion: {wf.completion_percentage:.1f}%")

async def demo_validation_consensus():
    """Demonstrate validation consensus analysis."""
    print("\n\n🎯 ValidationSystem Consensus Demo")
    print("=" * 50)
    
    validation_system = ValidationSystem()
    mock_db = MockDB()
    
    # Mock validation data
    validations = [
        MockValidation("val-1", "opp-consensus-123", "user-1", "market_demand", 8.5, 9.0),
        MockValidation("val-2", "opp-consensus-123", "user-2", "technical_feasibility", 7.8, 8.5),
        MockValidation("val-3", "opp-consensus-123", "user-3", "business_viability", 7.2, 7.0),
        MockValidation("val-4", "opp-consensus-123", "user-4", "market_demand", 8.0, 8.0),
        MockValidation("val-5", "opp-consensus-123", "user-5", "competitive_analysis", 6.5, 7.5)
    ]
    
    # Mock services
    async def mock_get_validations(db, opp_id):
        return validations
    
    async def mock_get_user(db, user_id):
        users = {
            "user-1": MockUser("user-1", "expert1", "expert", 9.2),
            "user-2": MockUser("user-2", "expert2", "expert", 8.8),
            "user-3": MockUser("user-3", "user3", "user", 6.5),
            "user-4": MockUser("user-4", "expert3", "expert", 8.0),
            "user-5": MockUser("user-5", "user5", "user", 7.0)
        }
        return users.get(user_id)
    
    async def mock_get_influence_weight(db, user_id):
        weights = {
            "user-1": 1.3,  # High-reputation expert
            "user-2": 1.2,  # Good expert
            "user-3": 0.8,  # Regular user
            "user-4": 1.1,  # Expert
            "user-5": 0.9   # Regular user
        }
        return weights.get(user_id, 1.0)
    
    # Patch services
    import shared.services.validation_system as vs_module
    vs_module.validation_service.get_opportunity_validations = mock_get_validations
    vs_module.user_service.get_user_by_id = mock_get_user
    vs_module.user_service.get_user_influence_weight = mock_get_influence_weight
    
    # Analyze consensus
    print("\n1. Analyzing Validation Consensus")
    print("-" * 30)
    
    consensus = await validation_system.analyze_validation_consensus(
        mock_db, "opp-consensus-123"
    )
    
    print(f"✅ Consensus Analysis Complete")
    print(f"   Consensus Score: {consensus.consensus_score}/10")
    print(f"   Confidence Level: {consensus.confidence_level}/10")
    print(f"   Agreement Ratio: {consensus.agreement_ratio:.2f}")
    print(f"   Outlier Count: {consensus.outlier_count}")
    print(f"   Quality Score: {consensus.quality_score}/10")
    print(f"   Supporting Evidence: {consensus.supporting_evidence_count} links")
    print(f"   Expert Consensus: {consensus.expert_consensus}/10")
    print(f"   Community Consensus: {consensus.community_consensus}/10")
    print(f"   Recommendation: {consensus.recommendation}")

async def demo_quality_metrics():
    """Demonstrate validation quality metrics."""
    print("\n\n📊 ValidationSystem Quality Metrics Demo")
    print("=" * 50)
    
    validation_system = ValidationSystem()
    mock_db = MockDB()
    
    # Mock high-quality validations
    quality_validations = [
        MockValidation("val-q1", "opp-quality-123", "user-1", "market_demand", 8.5, 9.0),
        MockValidation("val-q2", "opp-quality-123", "user-2", "technical_feasibility", 8.0, 8.5),
        MockValidation("val-q3", "opp-quality-123", "user-3", "business_viability", 7.5, 8.0)
    ]
    
    # Enhance with quality indicators
    for i, val in enumerate(quality_validations):
        val.evidence_links = json.dumps([
            f"https://evidence{i+1}a.com",
            f"https://evidence{i+1}b.com",
            f"https://research{i+1}.com"
        ])
        val.methodology = f"Expert analysis with {i+3} data sources"
        val.helpful_votes = 15 + i * 3
        val.unhelpful_votes = 1
        val.expertise_relevance = 9.0 - i * 0.2
    
    # Mock service
    async def mock_get_quality_validations(db, opp_id):
        return quality_validations
    
    import shared.services.validation_system as vs_module
    vs_module.validation_service.get_opportunity_validations = mock_get_quality_validations
    
    # Get quality metrics
    print("\n1. Calculating Quality Metrics")
    print("-" * 30)
    
    metrics = await validation_system.get_validation_quality_metrics(
        mock_db, "opp-quality-123"
    )
    
    print(f"✅ Quality Metrics Calculated")
    print(f"   Total Validations: {metrics['total_validations']}")
    print(f"   Overall Quality Score: {metrics['quality_score']:.2f}/10")
    print(f"   Completeness Score: {metrics['completeness_score']:.2f}/10")
    print(f"   Evidence Score: {metrics['evidence_score']:.2f}/10")
    print(f"   Expertise Score: {metrics['expertise_score']:.2f}/10")
    print(f"   Community Engagement: {metrics['community_engagement_score']:.2f}/10")

async def demo_workflow_states():
    """Demonstrate different workflow states."""
    print("\n\n🔄 ValidationSystem Workflow States Demo")
    print("=" * 50)
    
    validation_system = ValidationSystem()
    
    # Create workflows in different states
    now = datetime.utcnow()
    
    from shared.services.validation_system import ValidationWorkflow
    
    workflows = [
        ValidationWorkflow(
            opportunity_id="opp-pending",
            status=ValidationWorkflowStatus.PENDING,
            priority=ValidationPriority.HIGH,
            required_validation_types={ValidationType.MARKET_DEMAND, ValidationType.TECHNICAL_FEASIBILITY},
            completed_validation_types=set(),
            target_validator_count=5,
            current_validator_count=0,
            min_expert_validations=2,
            current_expert_validations=0,
            deadline=now + timedelta(days=7),
            created_at=now,
            updated_at=now
        ),
        ValidationWorkflow(
            opportunity_id="opp-progress",
            status=ValidationWorkflowStatus.IN_PROGRESS,
            priority=ValidationPriority.NORMAL,
            required_validation_types={ValidationType.MARKET_DEMAND, ValidationType.TECHNICAL_FEASIBILITY, ValidationType.BUSINESS_VIABILITY},
            completed_validation_types={ValidationType.MARKET_DEMAND},
            target_validator_count=4,
            current_validator_count=2,
            min_expert_validations=1,
            current_expert_validations=1,
            deadline=now + timedelta(days=5),
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(minutes=30)
        ),
        ValidationWorkflow(
            opportunity_id="opp-complete",
            status=ValidationWorkflowStatus.COMPLETED,
            priority=ValidationPriority.LOW,
            required_validation_types={ValidationType.MARKET_DEMAND, ValidationType.TECHNICAL_FEASIBILITY},
            completed_validation_types={ValidationType.MARKET_DEMAND, ValidationType.TECHNICAL_FEASIBILITY},
            target_validator_count=3,
            current_validator_count=3,
            min_expert_validations=1,
            current_expert_validations=2,
            deadline=None,
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(hours=1)
        )
    ]
    
    # Store workflows
    for workflow in workflows:
        validation_system._active_workflows[workflow.opportunity_id] = workflow
    
    print("\n1. Workflow Status Overview")
    print("-" * 30)
    
    for workflow in workflows:
        print(f"   Opportunity: {workflow.opportunity_id}")
        print(f"   Status: {workflow.status.value}")
        print(f"   Priority: {workflow.priority.value}")
        print(f"   Completion: {workflow.completion_percentage:.1f}%")
        print(f"   Validators: {workflow.current_validator_count}/{workflow.target_validator_count}")
        print(f"   Experts: {workflow.current_expert_validations}/{workflow.min_expert_validations}")
        print(f"   Complete: {'✅' if workflow.is_complete else '❌'}")
        if workflow.deadline:
            days_left = (workflow.deadline - now).days
            print(f"   Deadline: {days_left} days remaining")
        print()
    
    # Filter workflows
    print("2. Filtered Workflows")
    print("-" * 30)
    
    high_priority = await validation_system.get_active_workflows(priority=ValidationPriority.HIGH)
    print(f"   High Priority Workflows: {len(high_priority)}")
    
    in_progress = await validation_system.get_active_workflows(status=ValidationWorkflowStatus.IN_PROGRESS)
    print(f"   In Progress Workflows: {len(in_progress)}")
    
    completed = await validation_system.get_active_workflows(status=ValidationWorkflowStatus.COMPLETED)
    print(f"   Completed Workflows: {len(completed)}")

async def main():
    """Run all validation system demos."""
    print("🚀 ValidationSystem Core Demo")
    print("=" * 60)
    print("This demo showcases the ValidationSystem's core functionality:")
    print("- Validation workflow management")
    print("- Validation aggregation logic")
    print("- Consensus analysis")
    print("- Quality metrics calculation")
    print("=" * 60)
    
    try:
        await demo_validation_workflow()
        await demo_validation_consensus()
        await demo_quality_metrics()
        await demo_workflow_states()
        
        print("\n\n✅ ValidationSystem Demo Complete!")
        print("=" * 60)
        print("The ValidationSystem successfully demonstrates:")
        print("✓ Workflow initiation and management")
        print("✓ Validation aggregation with weighted scoring")
        print("✓ Consensus analysis with confidence ratings")
        print("✓ Quality metrics calculation")
        print("✓ Multi-state workflow handling")
        print("✓ Priority-based workflow filtering")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())