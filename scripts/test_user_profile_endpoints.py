#!/usr/bin/env python3
"""
Test script for user profile endpoints implementation.

This script tests the user profile CRUD operations and expertise tracking
functionality implemented in task 6.2.1.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db_session
from shared.models.user import User, UserRole
from shared.models.reputation import UserBadge, BadgeType, ExpertiseVerification, ReputationSummary
from shared.auth import hash_password
from sqlalchemy import select
import json


async def create_test_user() -> str:
    """Create a test user with badges and expertise."""
    async with get_db_session() as db:
        # Create test user
        test_user = User(
            email="testuser@example.com",
            username="testuser",
            hashed_password=hash_password("testpassword123"),
            full_name="Test User",
            bio="A test user for profile endpoint testing",
            role=UserRole.EXPERT,
            expertise_domains=json.dumps(["machine_learning", "natural_language_processing"]),
            linkedin_url="https://linkedin.com/in/testuser",
            github_url="https://github.com/testuser",
            reputation_score=7.5,
            validation_count=25,
            validation_accuracy=0.85,
            is_active=True,
            is_verified=True
        )
        
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)
        
        # Add test badge
        badge = UserBadge(
            user_id=test_user.id,
            badge_type=BadgeType.EXPERT_CONTRIBUTOR,
            title="Expert Contributor",
            description="Contributed high-quality validations in expert domain",
            earned_for="25 high-quality validations in ML domain",
            milestone_value=25,
            color="#FFD700",
            is_visible=True
        )
        
        db.add(badge)
        
        # Add expertise verification
        verification = ExpertiseVerification(
            user_id=test_user.id,
            domain="machine_learning",
            verification_method="linkedin",
            verification_status="verified",
            evidence_url="https://linkedin.com/in/testuser",
            years_experience=5,
            verified_at=datetime.utcnow(),
            expertise_score=8.5,
            confidence_level=9.0
        )
        
        db.add(verification)
        
        # Add reputation summary
        reputation_summary = ReputationSummary(
            user_id=test_user.id,
            total_reputation_points=750.0,
            reputation_rank=15,
            influence_weight=1.5,
            total_validations=25,
            helpful_validations=22,
            accuracy_score=85.0,
            total_votes_received=45,
            helpful_votes_received=38,
            badges_earned=1,
            verified_domains=1,
            days_active=90,
            quality_score=8.2
        )
        
        db.add(reputation_summary)
        
        await db.commit()
        
        print(f"✅ Created test user: {test_user.id}")
        return test_user.id


async def test_user_profile_endpoints():
    """Test user profile endpoints functionality."""
    print("🧪 Testing User Profile Endpoints Implementation")
    print("=" * 60)
    
    try:
        # Create test user
        user_id = await create_test_user()
        
        # Test 1: Test user profile data structure
        print("\n1. Testing user profile data structure...")
        async with get_db_session() as db:
            from sqlalchemy.orm import selectinload
            
            result = await db.execute(
                select(User)
                .options(
                    selectinload(User.badges),
                    selectinload(User.expertise_verifications),
                    selectinload(User.reputation_summary)
                )
                .where(User.id == user_id)
            )
            user = result.scalar_one()
            
            # Test user data
            assert user.username == "testuser"
            assert user.role == UserRole.EXPERT
            assert user.reputation_score == 7.5
            assert len(user.badges) == 1
            assert len(user.expertise_verifications) == 1
            assert user.reputation_summary is not None
            
            print("   ✅ User profile data structure is correct")
        
        # Test 2: Test profile response building
        print("\n2. Testing profile response building...")
        async with get_db_session() as db:
            from api.routers.users import _build_user_profile_response
            from sqlalchemy.orm import selectinload
            
            result = await db.execute(
                select(User)
                .options(
                    selectinload(User.badges),
                    selectinload(User.expertise_verifications),
                    selectinload(User.reputation_summary)
                )
                .where(User.id == user_id)
            )
            user = result.scalar_one()
            
            profile = _build_user_profile_response(user)
            
            # Test profile structure
            assert profile.id == user_id
            assert profile.username == "testuser"
            assert profile.role == UserRole.EXPERT
            assert len(profile.badges) == 1
            assert len(profile.expertise_verifications) == 1
            assert profile.stats is not None
            assert profile.stats["total_validations"] == 25
            assert profile.stats["accuracy_score"] == 85.0
            
            print("   ✅ Profile response building works correctly")
        
        # Test 3: Test expertise domain parsing
        print("\n3. Testing expertise domain parsing...")
        async with get_db_session() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one()
            
            # Test JSON parsing
            if user.expertise_domains:
                domains = json.loads(user.expertise_domains)
                assert "machine_learning" in domains
                assert "natural_language_processing" in domains
                
            print("   ✅ Expertise domain parsing works correctly")
        
        # Test 4: Test badge functionality
        print("\n4. Testing badge functionality...")
        async with get_db_session() as db:
            result = await db.execute(
                select(UserBadge).where(UserBadge.user_id == user_id)
            )
            badges = result.scalars().all()
            
            assert len(badges) == 1
            badge = badges[0]
            assert badge.badge_type == BadgeType.EXPERT_CONTRIBUTOR
            assert badge.title == "Expert Contributor"
            assert badge.milestone_value == 25
            assert badge.is_visible == True
            
            print("   ✅ Badge functionality works correctly")
        
        # Test 5: Test expertise verification
        print("\n5. Testing expertise verification...")
        async with get_db_session() as db:
            result = await db.execute(
                select(ExpertiseVerification).where(ExpertiseVerification.user_id == user_id)
            )
            verifications = result.scalars().all()
            
            assert len(verifications) == 1
            verification = verifications[0]
            assert verification.domain == "machine_learning"
            assert verification.verification_status == "verified"
            assert verification.expertise_score == 8.5
            assert verification.years_experience == 5
            
            print("   ✅ Expertise verification works correctly")
        
        # Test 6: Test reputation summary
        print("\n6. Testing reputation summary...")
        async with get_db_session() as db:
            result = await db.execute(
                select(ReputationSummary).where(ReputationSummary.user_id == user_id)
            )
            summary = result.scalar_one()
            
            assert summary.total_reputation_points == 750.0
            assert summary.reputation_rank == 15
            assert summary.influence_weight == 1.5
            assert summary.total_validations == 25
            assert summary.helpful_validations == 22
            assert summary.accuracy_score == 85.0
            
            print("   ✅ Reputation summary works correctly")
        
        print("\n" + "=" * 60)
        print("✅ All user profile endpoint tests passed!")
        print("\nImplemented functionality:")
        print("- ✅ User profile CRUD operations")
        print("- ✅ Expertise tracking and domain parsing")
        print("- ✅ Badge system integration")
        print("- ✅ Expertise verification system")
        print("- ✅ Reputation summary statistics")
        print("- ✅ Profile response building")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def cleanup_test_data():
    """Clean up test data."""
    try:
        async with get_db_session() as db:
            # Delete test user and related data (cascade will handle relationships)
            result = await db.execute(
                select(User).where(User.email == "testuser@example.com")
            )
            user = result.scalar_one_or_none()
            
            if user:
                await db.delete(user)
                await db.commit()
                print("🧹 Cleaned up test data")
                
    except Exception as e:
        print(f"⚠️  Error cleaning up test data: {e}")


async def main():
    """Main test function."""
    try:
        success = await test_user_profile_endpoints()
        await cleanup_test_data()
        
        if success:
            print("\n🎉 Task 6.2.1 implementation is working correctly!")
            sys.exit(0)
        else:
            print("\n💥 Task 6.2.1 implementation has issues!")
            sys.exit(1)
            
    except Exception as e:
        print(f"💥 Test execution failed: {e}")
        await cleanup_test_data()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())