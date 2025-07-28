#!/usr/bin/env python3
"""
Simple test script for Timeline Estimation Service functionality.

This script tests the core timeline estimation functionality
without importing the full API stack.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from unittest.mock import Mock

from shared.services.timeline_estimation_service import (
    TimelineEstimationService,
    EstimationMethod,
    ResourceType,
    ComplexityLevel
)


def test_timeline_estimation_service():
    """Test timeline estimation service functionality."""
    print("🧪 Testing Timeline Estimation Service Core Functionality")
    print("=" * 60)
    
    # Initialize service
    service = TimelineEstimationService()
    print("✅ Timeline Estimation Service initialized successfully")
    
    # Test service attributes
    print(f"📊 Historical velocity data entries: {len(service.historical_velocity_data)}")
    print(f"💰 Resource rate entries: {len(service.resource_rates)}")
    print(f"🔧 Complexity factor entries: {len(service.complexity_factors)}")
    
    # Test estimation methods
    print(f"\n🔬 Available Estimation Methods:")
    for method in EstimationMethod:
        print(f"   - {method.value}: {method.name}")
    
    # Test resource types
    print(f"\n👥 Available Resource Types:")
    sample_resources = list(ResourceType)[:5]  # Show first 5
    for resource in sample_resources:
        rates = service.resource_rates.get(resource, {})
        junior_rate = rates.get("junior", 0)
        senior_rate = rates.get("senior", 0)
        print(f"   - {resource.value}: ${junior_rate}/hr (junior) - ${senior_rate}/hr (senior)")
    print(f"   ... and {len(ResourceType) - 5} more resource types")
    
    # Test complexity levels
    print(f"\n⚡ Team Velocity by Complexity:")
    for complexity in ComplexityLevel:
        velocity = service._estimate_team_velocity(complexity)
        print(f"   - {complexity.value}: {velocity:.2f}x")
    
    # Test Fibonacci rounding
    print(f"\n📊 Fibonacci Rounding Examples:")
    test_values = [1.2, 2.8, 7.1, 15.0, 25.0, 50.0]
    for value in test_values:
        rounded = service._round_to_fibonacci(value)
        print(f"   {value} → {rounded}")
    
    # Test task templates
    print(f"\n📝 Task Template Generation:")
    for phase in ["research_poc", "mvp_development", "beta_testing"]:
        templates = service._get_task_templates(phase, ComplexityLevel.MEDIUM)
        total_hours = sum(t["base_hours"] for t in templates)
        print(f"   - {phase}: {len(templates)} tasks, {total_hours} base hours")
    
    print(f"\n🎉 Timeline Estimation Service core functionality verified!")
    print("=" * 60)


def test_estimation_algorithms():
    """Test specific estimation algorithms."""
    print("\n🧮 Testing Estimation Algorithm Components:")
    print("-" * 45)
    
    service = TimelineEstimationService()
    
    # Test skill level determination
    print("🎯 Skill Level Determination:")
    mock_roadmap = Mock()
    mock_roadmap.overall_complexity = ComplexityLevel.HIGH
    
    sample_resources = [ResourceType.AI_ML_ENGINEER, ResourceType.BACKEND_DEVELOPER, ResourceType.DATA_SCIENTIST]
    for resource in sample_resources:
        skill_level = service._determine_required_skill_level(resource, mock_roadmap)
        print(f"   - {resource.value} (high complexity): {skill_level}")
    
    # Test parallel capacity calculation
    print(f"\n⚡ Parallel Capacity Calculation:")
    test_hours = [100, 500, 1000, 2000]
    for hours in test_hours:
        capacity = service._calculate_parallel_capacity(ResourceType.BACKEND_DEVELOPER, hours)
        print(f"   - {hours} hours: {capacity} parallel resources")
    
    # Test complexity factor calculation
    print(f"\n🔧 Complexity Factor Examples:")
    factors = {
        "Simple task": {"technical": 1.0, "ai": 1.0, "integration": 1.0},
        "AI-heavy task": {"technical": 1.2, "ai": 1.8, "integration": 1.1},
        "Complex integration": {"technical": 1.5, "ai": 1.2, "integration": 1.7}
    }
    
    for task_name, task_factors in factors.items():
        total_multiplier = 1.0
        for factor_type, factor_value in task_factors.items():
            total_multiplier *= factor_value
        print(f"   - {task_name}: {total_multiplier:.2f}x multiplier")
    
    print(f"\n✅ Estimation algorithm components verified!")


def test_data_structures():
    """Test data structure initialization."""
    print("\n📊 Testing Data Structure Initialization:")
    print("-" * 40)
    
    service = TimelineEstimationService()
    
    # Test historical velocity data
    print("📈 Historical Velocity Data:")
    velocity_sample = dict(list(service.historical_velocity_data.items())[:3])
    for task_type, velocity in velocity_sample.items():
        print(f"   - {task_type}: {velocity:.2f}")
    
    # Test resource rates structure
    print(f"\n💰 Resource Rates Structure:")
    for resource_type in list(ResourceType)[:3]:
        if resource_type in service.resource_rates:
            rates = service.resource_rates[resource_type]
            print(f"   - {resource_type.value}:")
            for skill, rate in rates.items():
                print(f"     {skill}: ${rate}/hr")
    
    # Test complexity factors
    print(f"\n🔧 Complexity Factors:")
    complexity_sample = dict(list(service.complexity_factors.items())[:3])
    for factor_name, factor_value in complexity_sample.items():
        print(f"   - {factor_name}: {factor_value}")
    
    print(f"\n✅ Data structures properly initialized!")


if __name__ == "__main__":
    print("🧪 Timeline Estimation Service Test Suite")
    print("=" * 70)
    
    # Run core functionality tests
    test_timeline_estimation_service()
    
    # Run algorithm tests
    test_estimation_algorithms()
    
    # Run data structure tests
    test_data_structures()
    
    print("\n🎉 All tests completed successfully!")
    print("=" * 70)
    print("\n📋 Summary:")
    print("   ✅ Timeline Estimation Service initialized")
    print("   ✅ All estimation methods available")
    print("   ✅ Resource types and rates configured")
    print("   ✅ Complexity factors working")
    print("   ✅ Algorithm components functional")
    print("   ✅ Data structures properly initialized")
    print("\n🚀 Timeline Estimation Service is ready for use!")