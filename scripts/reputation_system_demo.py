#!/usr/bin/env python3
"""
Reputation System Demo Script

This script demonstrates the enhanced reputation system functionality
including expert verification mechanisms and reputation tracking.

Usage:
    python scripts/reputation_system_demo.py
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db_session
from shared.services.reputation_service import reputation_service
from shared.services.user_service import user_service
from shared.models.user import User, UserRole
from shared.models.reputation import ReputationEventType, BadgeType
from shared.models.validation import ValidationResult, ValidationType


class ReputationSystemDemo:
    """Demo class for reputation system functionality."""
    
    def __init__(self):
        self.demo_users = []
        self.demo_validations = []
    
    async def run_demo(self):
        """Run the complete reputation system demo."""
        print("🏆 AI Opportunity Browser - Reputation System Demo")
        print("=" * 60)
        
        async with get_db_session() as db:
            try:
                # 1. Create demo users
                await self._create_demo_users(db)
                
                # 2. Demonstrate expert verification
                await self._demo_expert_verification(db)
                
                # 3. Demonstrate reputation tracking
                await self._demo_reputation_tracking(db)
                
                # 4. Demonstrate badge system
                await self._demo_badge_system(db)
                
                # 5. Show reputation analytics
                await self._demo_reputation_analytics(db)
                
                # 6. Show leaderboard
                await self._demo_leaderboard(db)
                
                print("\n✅ Reputation system demo completed successfully!")
                
            except Exception as e:
                print(f"\n❌ Demo failed: {e}")
                raise
    
    async def _create_demo_users(self, db):
        """Create demo users for testing."""
        print("\n1. Creating Demo Users")
        print("-" * 30)
        
        demo_user_data = [
            {
                "username": "ai_expert_alice",
                "email": "alice@example.com",
                "full_name": "Alice Johnson",
                "role": UserRole.EXPERT,
                "expertise_domains": ["machine_learning", "computer_vision", "nlp"]
            },
            {
                "username": "ml_researcher_bob",
                "email": "bob@example.com", 
                "full_name": "Bob Smith",
                "role": UserRole.EXPERT,
                "expertise_domains": ["deep_learning", "reinforcement_learning"]
            },
            {
                "username": "data_scientist_carol",
                "email": "carol@example.com",
                "full_name": "Carol Davis",
                "role": UserRole.USER,
                "expertise_domains": ["data_science", "analytics"]
            },
            {
                "username": "admin_dave",
                "email": "dave@example.com",
                "full_name": "Dave Wilson",
                "role": UserRole.ADMIN,
                "expertise_domains": []
            }
        ]
        
        for user_data in demo_user_data:
            try:
                # Check if user already exists
                existing_user = await user_service.get_user_by_email(db, user_data["email"])
                if existing_user:
                    print(f"  📝 User {user_data['username']} already exists")
                    self.demo_users.append(existing_user)
                    continue
                
                # Create user (simplified - in real app would use proper schemas)
                from shared.schemas.user import UserCreate
                user_create = UserCreate(
                    username=user_data["username"],
                    email=user_data["email"],
                    password="demo_password_123",
                    full_name=user_data["full_name"],
                    expertise_domains=user_data["expertise_domains"]
                )
                
                user = await user_service.create_user(db, user_create)
                user.role = user_data["role"]  # Set role after creation
                await db.commit()
                
                self.demo_users.append(user)
                print(f"  ✅ Created user: {user.username} ({user.role.value})")
                
            except Exception as e:
                print(f"  ❌ Failed to create user {user_data['username']}: {e}")
    
    async def _demo_expert_verification(self, db):
        """Demonstrate expert verification process."""
        print("\n2. Expert Verification Demo")
        print("-" * 30)
        
        if len(self.demo_users) < 2:
            print("  ⚠️  Not enough demo users for verification demo")
            return
        
        alice = self.demo_users[0]  # AI expert
        admin = next((u for u in self.demo_users if u.role == UserRole.ADMIN), None)
        
        if not admin:
            print("  ⚠️  No admin user found for verification demo")
            return
        
        # Initiate verification for Alice
        print(f"  📋 Initiating verification for {alice.username}")
        
        verification_data = [
            {
                "domain": "machine_learning",
                "method": "linkedin",
                "evidence_url": "https://linkedin.com/in/alice-ai-expert",
                "credentials": "PhD in Machine Learning, 8 years industry experience",
                "years_experience": 8
            },
            {
                "domain": "computer_vision",
                "method": "academic",
                "evidence_url": "https://university.edu/faculty/alice",
                "credentials": "Published 15 papers in top CV conferences",
                "years_experience": 6
            },
            {
                "domain": "nlp",
                "method": "github",
                "evidence_url": "https://github.com/alice-nlp",
                "credentials": "Maintainer of popular NLP libraries",
                "years_experience": 5
            }
        ]
        
        for data in verification_data:
            try:
                verification = await reputation_service.initiate_expert_verification(
                    db,
                    alice.id,
                    data["domain"],
                    data["method"],
                    data["evidence_url"],
                    data["credentials"],
                    data["years_experience"]
                )
                
                print(f"    ✅ {data['domain']}: {verification.verification_status} "
                      f"(score: {verification.expertise_score:.1f})")
                
                # If not auto-verified, approve manually
                if verification.verification_status == "pending":
                    approved = await reputation_service.approve_expert_verification(
                        db, verification.id, admin.id, "Credentials verified by admin"
                    )
                    print(f"    👍 Approved by admin (score: {approved.expertise_score:.1f})")
                
            except Exception as e:
                print(f"    ❌ Failed to verify {data['domain']}: {e}")
        
        # Show expert domains
        domains = await reputation_service.get_expert_domains(db, alice.id)
        print(f"  🎯 {alice.username} verified domains: {', '.join(domains)}")
    
    async def _demo_reputation_tracking(self, db):
        """Demonstrate reputation tracking."""
        print("\n3. Reputation Tracking Demo")
        print("-" * 30)
        
        if len(self.demo_users) < 3:
            print("  ⚠️  Not enough demo users for reputation demo")
            return
        
        alice = self.demo_users[0]
        bob = self.demo_users[1]
        carol = self.demo_users[2]
        
        # Simulate validation activities
        print("  📊 Simulating validation activities...")
        
        # Alice submits high-quality validations
        for i in range(5):
            await reputation_service.record_reputation_event(
                db, alice.id, ReputationEventType.VALIDATION_SUBMITTED,
                f"Submitted validation #{i+1}",
                metadata={"validation_score": 8.5, "quality": "high"}
            )
        
        # Alice receives helpful votes
        for i in range(8):
            await reputation_service.record_reputation_event(
                db, alice.id, ReputationEventType.VALIDATION_HELPFUL,
                "Validation marked as helpful"
            )
        
        # Bob submits fewer but good validations
        for i in range(3):
            await reputation_service.record_reputation_event(
                db, bob.id, ReputationEventType.VALIDATION_SUBMITTED,
                f"Submitted validation #{i+1}",
                metadata={"validation_score": 7.2, "quality": "good"}
            )
        
        # Carol is new with basic activity
        await reputation_service.record_reputation_event(
            db, carol.id, ReputationEventType.VALIDATION_SUBMITTED,
            "First validation submitted",
            metadata={"validation_score": 6.0, "quality": "basic"}
        )
        
        # Update reputation summaries
        for user in [alice, bob, carol]:
            summary = await reputation_service.update_reputation_summary(db, user.id)
            print(f"    {user.username}: {summary.total_reputation_points:.1f} points "
                  f"(influence: {summary.influence_weight:.2f})")
    
    async def _demo_badge_system(self, db):
        """Demonstrate badge system."""
        print("\n4. Badge System Demo")
        print("-" * 30)
        
        if not self.demo_users:
            print("  ⚠️  No demo users for badge demo")
            return
        
        # Check and award badges for all users
        for user in self.demo_users:
            try:
                new_badges = await reputation_service.check_and_award_badges(db, user.id)
                
                if new_badges:
                    print(f"  🏅 {user.username} earned {len(new_badges)} new badges:")
                    for badge in new_badges:
                        print(f"    - {badge.title}: {badge.description}")
                else:
                    print(f"  📋 {user.username}: No new badges earned")
                
            except Exception as e:
                print(f"  ❌ Failed to check badges for {user.username}: {e}")
    
    async def _demo_reputation_analytics(self, db):
        """Demonstrate reputation analytics."""
        print("\n5. Reputation Analytics Demo")
        print("-" * 30)
        
        try:
            analytics = await reputation_service.get_reputation_analytics(db, timeframe_days=30)
            
            print(f"  📈 Total Users: {analytics['total_users']}")
            print(f"  💰 Total Reputation Points: {analytics['total_reputation_points']:.1f}")
            print(f"  📊 Average Reputation: {analytics['average_reputation']:.1f}")
            print(f"  🏆 Total Badges Awarded: {analytics['total_badges_awarded']}")
            print(f"  ✅ Total Verifications: {analytics['total_verifications']}")
            print(f"  🔥 Recent Activity: {analytics['recent_activity']} events")
            
            if analytics['top_domains']:
                print("  🎯 Top Expertise Domains:")
                for domain_info in analytics['top_domains'][:5]:
                    print(f"    - {domain_info['domain']}: {domain_info['count']} experts")
            
        except Exception as e:
            print(f"  ❌ Failed to get analytics: {e}")
    
    async def _demo_leaderboard(self, db):
        """Demonstrate reputation leaderboard."""
        print("\n6. Reputation Leaderboard Demo")
        print("-" * 30)
        
        try:
            leaderboard = await reputation_service.get_reputation_leaderboard(db, limit=10)
            
            if not leaderboard:
                print("  📋 No users in leaderboard yet")
                return
            
            print("  🏆 Top Contributors:")
            for entry in leaderboard:
                print(f"    #{entry['rank']} {entry['username']}: "
                      f"{entry['reputation_points']:.1f} points "
                      f"({entry['total_validations']} validations, "
                      f"{entry['accuracy_score']:.1f}% accuracy)")
            
        except Exception as e:
            print(f"  ❌ Failed to get leaderboard: {e}")
    
    async def _demo_domain_experts(self, db):
        """Demonstrate domain expert lookup."""
        print("\n7. Domain Expert Lookup Demo")
        print("-" * 30)
        
        domains_to_check = ["machine_learning", "computer_vision", "nlp"]
        
        for domain in domains_to_check:
            try:
                experts = await reputation_service.get_domain_experts(
                    db, domain, min_expertise_score=5.0, limit=5
                )
                
                if experts:
                    print(f"  🎯 {domain.replace('_', ' ').title()} Experts:")
                    for expert in experts:
                        print(f"    - {expert['username']}: "
                              f"score {expert['expertise_score']:.1f}, "
                              f"{expert['years_experience'] or 0} years exp")
                else:
                    print(f"  📋 No experts found for {domain}")
                
            except Exception as e:
                print(f"  ❌ Failed to get experts for {domain}: {e}")


async def main():
    """Main demo function."""
    demo = ReputationSystemDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())