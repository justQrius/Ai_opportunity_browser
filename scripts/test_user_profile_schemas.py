#!/usr/bin/env python3
"""
Test script for user profile schemas and response building.

This script tests the user profile schemas and response building functionality
implemented in task 6.2.1 without requiring database connections.
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.schemas.user import (
    UserProfile, UserBadgeResponse, ExpertiseVerificationResponse, 
    UserStatsResponse, UserUpdate
)
from shared.models.user import UserRole
from shared.models.reputation import BadgeType


def test_user_schemas():
    """Test user profile schemas."""
    print("🧪 Testing User Profile Schemas")
    print("=" * 50)
    
    try:
        # Test 1: UserBadgeResponse schema
        print("\n1. Testing UserBadgeResponse schema...")
        badge_data = {
            "id": "badge-123",
            "badge_type": BadgeType.EXPERT_CONTRIBUTOR,
            "title": "Expert Contributor",
            "description": "Contributed high-quality validations",
            "earned_for": "25 high-quality validations",
            "milestone_value": 25,
            "icon_url": "https://example.com/badge.png",
            "color": "#FFD700",
            "is_visible": True,
            "created_at": datetime.utcnow()
        }
        
        badge = UserBadgeResponse(**badge_data)
        assert badge.badge_type == BadgeType.EXPERT_CONTRIBUTOR
        assert badge.title == "Expert Contributor"
        assert badge.milestone_value == 25
        print("   ✅ UserBadgeResponse schema works correctly")
        
        # Test 2: ExpertiseVerificationResponse schema
        print("\n2. Testing ExpertiseVerificationResponse schema...")
        verification_data = {
            "id": "verification-123",
            "domain": "machine_learning",
            "verification_method": "linkedin",
            "verification_status": "verified",
            "evidence_url": "https://linkedin.com/in/user",
            "years_experience": 5,
            "verified_at": datetime.utcnow(),
            "expertise_score": 8.5,
            "confidence_level": 9.0,
            "created_at": datetime.utcnow()
        }
        
        verification = ExpertiseVerificationResponse(**verification_data)
        assert verification.domain == "machine_learning"
        assert verification.verification_status == "verified"
        assert verification.expertise_score == 8.5
        print("   ✅ ExpertiseVerificationResponse schema works correctly")
        
        # Test 3: UserStatsResponse schema
        print("\n3. Testing UserStatsResponse schema...")
        stats_data = {
            "total_validations": 25,
            "helpful_validations": 22,
            "accuracy_score": 85.0,
            "total_votes_received": 45,
            "helpful_votes_received": 38,
            "badges_earned": 1,
            "verified_domains": 1,
            "days_active": 90,
            "quality_score": 8.2
        }
        
        stats = UserStatsResponse(**stats_data)
        assert stats.total_validations == 25
        assert stats.accuracy_score == 85.0
        assert stats.quality_score == 8.2
        print("   ✅ UserStatsResponse schema works correctly")
        
        # Test 4: UserProfile schema with all components
        print("\n4. Testing UserProfile schema...")
        profile_data = {
            "id": "user-123",
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "bio": "A test user",
            "avatar_url": "https://example.com/avatar.jpg",
            "role": UserRole.EXPERT,
            "is_active": True,
            "is_verified": True,
            "reputation_score": 7.5,
            "validation_count": 25,
            "validation_accuracy": 0.85,
            "expertise_domains": ["machine_learning", "nlp"],
            "linkedin_url": "https://linkedin.com/in/testuser",
            "github_url": "https://github.com/testuser",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "badges": [badge],
            "expertise_verifications": [verification],
            "stats": stats
        }
        
        profile = UserProfile(**profile_data)
        assert profile.username == "testuser"
        assert profile.role == UserRole.EXPERT
        assert len(profile.badges) == 1
        assert len(profile.expertise_verifications) == 1
        assert profile.stats is not None
        assert profile.stats.total_validations == 25
        print("   ✅ UserProfile schema works correctly")
        
        # Test 5: UserUpdate schema
        print("\n5. Testing UserUpdate schema...")
        update_data = {
            "full_name": "Updated Name",
            "bio": "Updated bio",
            "expertise_domains": ["machine_learning", "computer_vision"],
            "linkedin_url": "https://linkedin.com/in/updated"
        }
        
        update = UserUpdate(**update_data)
        assert update.full_name == "Updated Name"
        assert "machine_learning" in update.expertise_domains
        print("   ✅ UserUpdate schema works correctly")
        
        print("\n" + "=" * 50)
        print("✅ All user profile schema tests passed!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Schema test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_profile_response_structure():
    """Test the structure of profile responses."""
    print("\n🧪 Testing Profile Response Structure")
    print("=" * 50)
    
    try:
        # Test profile response JSON serialization
        print("\n1. Testing profile response serialization...")
        
        badge_data = {
            "id": "badge-123",
            "badge_type": BadgeType.EXPERT_CONTRIBUTOR,
            "title": "Expert Contributor",
            "description": "Contributed high-quality validations",
            "earned_for": "25 high-quality validations",
            "milestone_value": 25,
            "icon_url": "https://example.com/badge.png",
            "color": "#FFD700",
            "is_visible": True,
            "created_at": datetime.utcnow()
        }
        
        profile_data = {
            "id": "user-123",
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "bio": "A test user",
            "avatar_url": "https://example.com/avatar.jpg",
            "role": UserRole.EXPERT,
            "is_active": True,
            "is_verified": True,
            "reputation_score": 7.5,
            "validation_count": 25,
            "validation_accuracy": 0.85,
            "expertise_domains": ["machine_learning", "nlp"],
            "linkedin_url": "https://linkedin.com/in/testuser",
            "github_url": "https://github.com/testuser",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "badges": [UserBadgeResponse(**badge_data)],
            "expertise_verifications": [],
            "stats": None
        }
        
        profile = UserProfile(**profile_data)
        
        # Test JSON serialization
        profile_dict = profile.dict()
        assert "badges" in profile_dict
        assert "expertise_verifications" in profile_dict
        assert "stats" in profile_dict
        assert len(profile_dict["badges"]) == 1
        
        print("   ✅ Profile response serialization works correctly")
        
        print("\n" + "=" * 50)
        print("✅ Profile response structure tests passed!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Profile response test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print("🧪 Testing User Profile Endpoints Implementation (Schemas)")
    print("=" * 60)
    
    try:
        schema_success = test_user_schemas()
        response_success = test_profile_response_structure()
        
        if schema_success and response_success:
            print("\n🎉 User profile schemas are working correctly!")
            print("\nImplemented functionality:")
            print("- ✅ UserBadgeResponse schema")
            print("- ✅ ExpertiseVerificationResponse schema") 
            print("- ✅ UserStatsResponse schema")
            print("- ✅ Enhanced UserProfile schema")
            print("- ✅ UserUpdate schema")
            print("- ✅ Profile response serialization")
            
            print("\nNext steps:")
            print("- Install asyncpg: pip install asyncpg")
            print("- Run full database tests")
            print("- Test API endpoints with HTTP client")
            
            sys.exit(0)
        else:
            print("\n💥 User profile schema implementation has issues!")
            sys.exit(1)
            
    except Exception as e:
        print(f"💥 Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()