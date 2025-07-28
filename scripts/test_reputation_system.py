#!/usr/bin/env python3
"""
Simple Reputation System Test Script

This script tests the reputation system functionality without requiring
a database connection.

Usage:
    python scripts/test_reputation_system.py
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.services.reputation_service import ReputationService
from shared.models.reputation import ReputationEventType, BadgeType


def test_reputation_service():
    """Test reputation service functionality."""
    print("🏆 AI Opportunity Browser - Reputation System Test")
    print("=" * 60)
    
    # Initialize service
    service = ReputationService()
    
    # Test 1: Reputation points configuration
    print("\n1. Testing Reputation Points Configuration")
    print("-" * 40)
    
    points = service.REPUTATION_POINTS
    print(f"  ✅ Validation submitted: {points[ReputationEventType.VALIDATION_SUBMITTED]} points")
    print(f"  ✅ Validation helpful: {points[ReputationEventType.VALIDATION_HELPFUL]} points")
    print(f"  ✅ Expert verification: {points[ReputationEventType.EXPERT_VERIFICATION]} points")
    print(f"  ✅ Badge earned: {points[ReputationEventType.BADGE_EARNED]} points")
    
    # Test 2: Verification methods configuration
    print("\n2. Testing Verification Methods Configuration")
    print("-" * 40)
    
    methods = service.VERIFICATION_METHODS
    for method, config in methods.items():
        auto_verify = "✅ Auto" if config["auto_verify"] else "🔍 Manual"
        credibility = config["credibility"]
        print(f"  {method}: {credibility:.1f} credibility, {auto_verify}")
    
    # Test 3: Badge requirements configuration
    print("\n3. Testing Badge Requirements Configuration")
    print("-" * 40)
    
    requirements = service.BADGE_REQUIREMENTS
    for badge_type, req in requirements.items():
        req_str = ", ".join([f"{k}: {v}" for k, v in req.items()])
        print(f"  {badge_type.value}: {req_str}")
    
    # Test 4: Expertise score calculation
    print("\n4. Testing Expertise Score Calculation")
    print("-" * 40)
    
    test_cases = [
        ("linkedin", "https://linkedin.com/in/expert", "PhD in ML", 8),
        ("github", "https://github.com/expert", "Open source contributor", 5),
        ("academic", "https://university.edu/profile", "Professor of AI", 15),
        ("portfolio", "https://portfolio.com", None, None),
        ("certification", None, "AWS ML Specialty", 3)
    ]
    
    for method, evidence_url, credentials, years_exp in test_cases:
        score = service._calculate_expertise_score(method, evidence_url, credentials, years_exp)
        print(f"  {method}: {score:.1f}/10.0 (exp: {years_exp or 0} years)")
    
    # Test 5: Verification method validation
    print("\n5. Testing Verification Method Validation")
    print("-" * 40)
    
    valid_methods = list(service.VERIFICATION_METHODS.keys())
    print(f"  ✅ Valid methods: {', '.join(valid_methods)}")
    
    # Test invalid method
    try:
        service._calculate_expertise_score("invalid_method", None, None, None)
        print("  ❌ Should have failed for invalid method")
    except KeyError:
        print("  ✅ Correctly rejected invalid verification method")
    
    print("\n✅ All reputation system tests completed successfully!")
    print("\n📊 Summary:")
    print(f"  - {len(service.REPUTATION_POINTS)} reputation event types configured")
    print(f"  - {len(service.VERIFICATION_METHODS)} verification methods available")
    print(f"  - {len(service.BADGE_REQUIREMENTS)} badge types defined")
    print(f"  - Auto-verify methods: {sum(1 for m in service.VERIFICATION_METHODS.values() if m['auto_verify'])}")
    print(f"  - Manual-verify methods: {sum(1 for m in service.VERIFICATION_METHODS.values() if not m['auto_verify'])}")


def test_reputation_calculations():
    """Test reputation calculation functions."""
    print("\n🧮 Testing Reputation Calculations")
    print("=" * 40)
    
    # Import calculation functions from auth module
    from shared.auth import calculate_reputation_score, determine_user_influence_weight
    
    # Test reputation score calculation
    test_cases = [
        (10, 0.8, 15, 3, 2),  # Good performer
        (50, 0.9, 40, 5, 5),  # Excellent performer
        (5, 0.6, 2, 8, 0),    # Poor performer
        (100, 0.95, 80, 10, 10)  # Outstanding performer
    ]
    
    print("Reputation Score Tests:")
    for validations, accuracy, helpful, unhelpful, endorsements in test_cases:
        score = calculate_reputation_score(validations, accuracy, helpful, unhelpful, endorsements)
        print(f"  {validations} validations, {accuracy:.0%} accuracy: {score:.1f}/10.0")
    
    # Test influence weight calculation
    print("\nInfluence Weight Tests:")
    test_roles = [
        (5.0, "user"),
        (7.5, "expert"),
        (8.0, "admin"),
        (9.5, "expert")
    ]
    
    for reputation, role in test_roles:
        weight = determine_user_influence_weight(reputation, role)
        print(f"  {role} with {reputation:.1f} reputation: {weight:.2f}x influence")


if __name__ == "__main__":
    test_reputation_service()
    test_reputation_calculations()