"""Fraud Detection System Demo

This script demonstrates the fraud detection and automated moderation capabilities
of the AI Opportunity Browser platform.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

from shared.database import get_db
from shared.models.validation import ValidationResult, ValidationType
from shared.models.user import User, UserRole
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.reputation import ReputationEvent, ReputationEventType
from shared.services.fraud_detection_service import (
    fraud_detection_service,
    FraudType,
    FraudSeverity,
    ModerationAction
)
from shared.services.moderation_service import moderation_service, ModerationStatus
from shared.services.user_service import user_service
from shared.services.opportunity_service import opportunity_service
from shared.services.validation_service import validation_service
from shared.services.reputation_service import reputation_service


class FraudDetectionDemo:
    """Demo class for fraud detection system."""
    
    def __init__(self):
        """Initialize demo."""
        self.demo_users = []
        self.demo_opportunities = []
        self.demo_validations = []
    
    async def run_demo(self):
        """Run the complete fraud detection demo."""
        print("🔍 AI Opportunity Browser - Fraud Detection System Demo")
        print("=" * 60)
        
        async for db in get_db():
            try:
                # Setup demo data
                await self._setup_demo_data(db)
                
                # Demonstrate fraud detection algorithms
                await self._demo_spam_detection(db)
                await self._demo_quality_detection(db)
                await self._demo_vote_manipulation_detection(db)
                await self._demo_reputation_farming_detection(db)
                
                # Demonstrate moderation system
                await self._demo_moderation_workflow(db)
                await self._demo_community_flagging(db)
                await self._demo_appeal_system(db)
                
                # Show statistics and analytics
                await self._demo_fraud_analytics(db)
                
                print("\n✅ Fraud Detection Demo completed successfully!")
                
            except Exception as e:
                print(f"❌ Demo failed: {e}")
                raise
            finally:
                # Cleanup demo data
                await self._cleanup_demo_data(db)
    
    async def _setup_demo_data(self, db):
        """Setup demo data for fraud detection testing."""
        print("\n📊 Setting up demo data...")
        
        # Create demo users
        demo_user_data = [
            {
                "username": "legitimate_user",
                "email": "legit@example.com",
                "role": UserRole.USER,
                "description": "Legitimate user with good validation history"
            },
            {
                "username": "spam_user",
                "email": "spam@example.com",
                "role": UserRole.USER,
                "description": "User exhibiting spam behavior"
            },
            {
                "username": "low_quality_user",
                "email": "lowquality@example.com",
                "role": UserRole.USER,
                "description": "User providing low-quality validations"
            },
            {
                "username": "fake_expert",
                "email": "fakeexpert@example.com",
                "role": UserRole.USER,
                "description": "User claiming false expertise"
            },
            {
                "username": "moderator_user",
                "email": "moderator@example.com",
                "role": UserRole.MODERATOR,
                "description": "Platform moderator"
            }
        ]
        
        for user_data in demo_user_data:
            user = await user_service.create_user(
                db,
                username=user_data["username"],
                email=user_data["email"],
                password="demo_password",
                role=user_data["role"]
            )
            self.demo_users.append(user)
            print(f"  Created user: {user.username} ({user.role.value})")
        
        # Create demo opportunities
        for i in range(3):
            opportunity = await opportunity_service.create_opportunity(
                db,
                title=f"Demo AI Opportunity {i+1}",
                description=f"This is demo opportunity {i+1} for fraud detection testing.",
                market_size_estimate=1000000 + i * 500000,
                confidence_score=7.5 + i * 0.5,
                ai_relevance_score=8.0 + i * 0.3,
                implementation_complexity=5 + i,
                market_validation_score=7.0 + i * 0.4,
                status=OpportunityStatus.VALIDATING
            )
            self.demo_opportunities.append(opportunity)
            print(f"  Created opportunity: {opportunity.title}")
        
        print(f"✅ Setup complete: {len(self.demo_users)} users, {len(self.demo_opportunities)} opportunities")
    
    async def _demo_spam_detection(self, db):
        """Demonstrate spam validation detection."""
        print("\n🚨 Demonstrating Spam Detection...")
        
        spam_user = next(u for u in self.demo_users if u.username == "spam_user")
        opportunity = self.demo_opportunities[0]
        
        # Create multiple rapid validations (spam behavior)
        spam_validations = []
        for i in range(5):
            validation = await validation_service.create_validation(
                db,
                opportunity_id=opportunity.id,
                validator_id=spam_user.id,
                validation_type=ValidationType.MARKET_DEMAND,
                score=6.0 + i * 0.5,
                confidence=5.0,
                comments=f"Short comment {i}",  # Very short comments
                methodology="quick_review"
            )
            spam_validations.append(validation)
            self.demo_validations.append(validation)
        
        # Analyze the last validation for fraud
        fraud_results = await fraud_detection_service.analyze_validation_for_fraud(
            db, spam_validations[-1].id
        )
        
        print(f"  Analyzed validation from {spam_user.username}")
        print(f"  Fraud results found: {len(fraud_results)}")
        
        for result in fraud_results:
            if result.fraud_type == FraudType.SPAM_VALIDATION:
                print(f"  🔴 SPAM DETECTED:")
                print(f"    Severity: {result.severity.value}")
                print(f"    Confidence: {result.confidence_score:.2f}")
                print(f"    Evidence: {', '.join(result.evidence)}")
                print(f"    Recommended Action: {result.recommended_action.value}")
    
    async def _demo_quality_detection(self, db):
        """Demonstrate low-quality content detection."""
        print("\n📉 Demonstrating Quality Detection...")
        
        low_quality_user = next(u for u in self.demo_users if u.username == "low_quality_user")
        opportunity = self.demo_opportunities[1]
        
        # Create low-quality validation
        validation = await validation_service.create_validation(
            db,
            opportunity_id=opportunity.id,
            validator_id=low_quality_user.id,
            validation_type=ValidationType.TECHNICAL_FEASIBILITY,
            score=5.0,
            confidence=2.0,  # Very low confidence
            comments="this is good maybe probably not sure could work",  # Generic phrases
            # No evidence or supporting data
        )
        self.demo_validations.append(validation)
        
        # Analyze for fraud
        fraud_results = await fraud_detection_service.analyze_validation_for_fraud(
            db, validation.id
        )
        
        print(f"  Analyzed validation from {low_quality_user.username}")
        
        for result in fraud_results:
            if result.fraud_type == FraudType.LOW_QUALITY_CONTENT:
                print(f"  🟡 LOW QUALITY DETECTED:")
                print(f"    Severity: {result.severity.value}")
                print(f"    Confidence: {result.confidence_score:.2f}")
                print(f"    Evidence: {', '.join(result.evidence)}")
                print(f"    Recommended Action: {result.recommended_action.value}")
    
    async def _demo_vote_manipulation_detection(self, db):
        """Demonstrate vote manipulation detection."""
        print("\n🗳️ Demonstrating Vote Manipulation Detection...")
        
        legitimate_user = next(u for u in self.demo_users if u.username == "legitimate_user")
        opportunity = self.demo_opportunities[2]
        
        # Create validation with suspicious voting pattern
        validation = await validation_service.create_validation(
            db,
            opportunity_id=opportunity.id,
            validator_id=legitimate_user.id,
            validation_type=ValidationType.BUSINESS_VIABILITY,
            score=8.0,
            confidence=7.5,
            comments="This opportunity has strong business viability with clear revenue streams.",
            evidence_links='["https://example.com/market-research"]'
        )
        
        # Simulate suspicious voting (all helpful, no unhelpful)
        validation.helpful_votes = 15
        validation.unhelpful_votes = 0
        await db.commit()
        
        self.demo_validations.append(validation)
        
        # Analyze for fraud
        fraud_results = await fraud_detection_service.analyze_validation_for_fraud(
            db, validation.id
        )
        
        print(f"  Analyzed validation with suspicious voting pattern")
        
        for result in fraud_results:
            if result.fraud_type == FraudType.VOTE_MANIPULATION:
                print(f"  🟠 VOTE MANIPULATION DETECTED:")
                print(f"    Severity: {result.severity.value}")
                print(f"    Confidence: {result.confidence_score:.2f}")
                print(f"    Evidence: {', '.join(result.evidence)}")
                print(f"    Recommended Action: {result.recommended_action.value}")
    
    async def _demo_reputation_farming_detection(self, db):
        """Demonstrate reputation farming detection."""
        print("\n🌾 Demonstrating Reputation Farming Detection...")
        
        fake_expert = next(u for u in self.demo_users if u.username == "fake_expert")
        
        # Create rapid reputation events (farming behavior)
        for i in range(20):
            await reputation_service.record_reputation_event(
                db,
                user_id=fake_expert.id,
                event_type=ReputationEventType.VALIDATION_SUBMITTED,
                description=f"Validation submitted {i+1}",
                points_override=5.0
            )
        
        # Create validation claiming high expertise
        validation = await validation_service.create_validation(
            db,
            opportunity_id=self.demo_opportunities[0].id,
            validator_id=fake_expert.id,
            validation_type=ValidationType.TECHNICAL_FEASIBILITY,
            score=9.0,
            confidence=9.5,
            comments="As an expert in this field, I can confirm this is highly feasible.",
            expertise_relevance=9.0  # Claims high expertise
        )
        self.demo_validations.append(validation)
        
        # Analyze for fraud
        fraud_results = await fraud_detection_service.analyze_validation_for_fraud(
            db, validation.id
        )
        
        print(f"  Analyzed validation from user with rapid reputation growth")
        
        for result in fraud_results:
            if result.fraud_type == FraudType.REPUTATION_FARMING:
                print(f"  🔴 REPUTATION FARMING DETECTED:")
                print(f"    Severity: {result.severity.value}")
                print(f"    Confidence: {result.confidence_score:.2f}")
                print(f"    Evidence: {', '.join(result.evidence)}")
                print(f"    Recommended Action: {result.recommended_action.value}")
    
    async def _demo_moderation_workflow(self, db):
        """Demonstrate automated moderation workflow."""
        print("\n⚖️ Demonstrating Moderation Workflow...")
        
        # Process validations through moderation pipeline
        processed_count = 0
        for validation in self.demo_validations[:3]:  # Process first 3 validations
            item = await moderation_service.process_validation_for_moderation(
                db, validation.id
            )
            
            if item:
                print(f"  📋 Validation {validation.id[:8]} added to moderation queue")
                print(f"    Status: {item.status.value}")
                print(f"    Priority: {item.priority}")
                print(f"    Fraud types: {[r.fraud_type.value for r in item.fraud_results]}")
                processed_count += 1
            else:
                print(f"  ✅ Validation {validation.id[:8]} auto-approved")
        
        # Get moderation queue
        queue_items = await moderation_service.get_moderation_queue(limit=10)
        print(f"\n  Current moderation queue size: {len(queue_items)}")
        
        # Demonstrate moderator assignment and decision
        if queue_items:
            moderator = next(u for u in self.demo_users if u.role == UserRole.MODERATOR)
            item = queue_items[0]
            
            # Assign to moderator
            success = await moderation_service.assign_moderation_item(
                item.validation_id, moderator.id
            )
            
            if success:
                print(f"  👤 Assigned validation to moderator: {moderator.username}")
                
                # Make moderation decision
                await moderation_service.moderate_validation(
                    db,
                    item.validation_id,
                    moderator.id,
                    ModerationAction.FLAG_FOR_REVIEW,
                    "Flagged for manual review due to quality concerns",
                    "Requires additional evidence"
                )
                print(f"  ⚖️ Moderation decision made: FLAG_FOR_REVIEW")
    
    async def _demo_community_flagging(self, db):
        """Demonstrate community flagging system."""
        print("\n🚩 Demonstrating Community Flagging...")
        
        if self.demo_validations:
            validation = self.demo_validations[0]
            reporter = next(u for u in self.demo_users if u.username == "legitimate_user")
            
            # Flag validation
            success = await fraud_detection_service.flag_validation(
                db,
                validation.id,
                reporter.id,
                "Inappropriate content and misleading information",
                "This validation contains false claims about market demand"
            )
            
            if success:
                print(f"  🚩 Validation flagged by community member: {reporter.username}")
                print(f"    Reason: Inappropriate content and misleading information")
                print(f"    Evidence: This validation contains false claims about market demand")
                
                # Check if validation is now flagged
                await db.refresh(validation)
                print(f"    Validation flagged status: {validation.is_flagged}")
                print(f"    Flag reason: {validation.flag_reason}")
    
    async def _demo_appeal_system(self, db):
        """Demonstrate appeal system."""
        print("\n📝 Demonstrating Appeal System...")
        
        if self.demo_validations:
            validation = self.demo_validations[0]
            user = next(u for u in self.demo_users if u.username == "spam_user")
            
            # Submit appeal
            appeal = await moderation_service.submit_appeal(
                db,
                validation.id,
                user.id,
                "I believe this moderation action was incorrect. My validation was based on thorough research.",
                "I have additional evidence that supports my validation."
            )
            
            print(f"  📝 Appeal submitted by: {user.username}")
            print(f"    Appeal reason: {appeal.appeal_reason}")
            print(f"    Status: {appeal.status.value}")
            
            # Process appeal (admin decision)
            admin = next(u for u in self.demo_users if u.role == UserRole.MODERATOR)  # Using moderator as admin for demo
            
            success = await moderation_service.process_appeal(
                db,
                validation.id,
                admin.id,
                approved=False,  # Deny the appeal
                resolution="After review, the original moderation decision stands. The validation lacked sufficient evidence."
            )
            
            if success:
                print(f"  ⚖️ Appeal processed by: {admin.username}")
                print(f"    Decision: DENIED")
                print(f"    Resolution: After review, the original moderation decision stands.")
    
    async def _demo_fraud_analytics(self, db):
        """Demonstrate fraud detection analytics."""
        print("\n📊 Fraud Detection Analytics...")
        
        # Get fraud statistics
        fraud_stats = await fraud_detection_service.get_fraud_statistics(db, 30)
        print(f"  Fraud Statistics (30 days):")
        print(f"    Total validations: {fraud_stats['total_validations']}")
        print(f"    Flagged validations: {fraud_stats['flagged_validations']}")
        print(f"    Moderated validations: {fraud_stats['moderated_validations']}")
        print(f"    Fraud rate: {fraud_stats['fraud_rate_percentage']}%")
        print(f"    Pending moderation: {fraud_stats['pending_moderation']}")
        
        # Get moderation statistics
        mod_stats = await moderation_service.get_moderation_statistics(db, 30)
        print(f"\n  Moderation Statistics (30 days):")
        print(f"    Queue size: {mod_stats['queue_size']}")
        print(f"    Pending items: {mod_stats['pending_items']}")
        print(f"    In review items: {mod_stats['in_review_items']}")
        print(f"    Resolved items: {mod_stats['resolved_items']}")
        print(f"    Appeal queue size: {mod_stats['appeal_queue_size']}")
        print(f"    Average processing time: {mod_stats['average_processing_time_hours']:.2f} hours")
        
        # Get moderator workload
        moderator = next(u for u in self.demo_users if u.role == UserRole.MODERATOR)
        workload = await moderation_service.get_moderator_workload(moderator.id)
        print(f"\n  Moderator Workload ({moderator.username}):")
        print(f"    Assigned items: {workload['assigned_items']}")
        print(f"    Pending items: {workload['pending_items']}")
        print(f"    In review items: {workload['in_review_items']}")
        print(f"    Average item age: {workload['average_item_age_hours']:.2f} hours")
    
    async def _cleanup_demo_data(self, db):
        """Clean up demo data."""
        print("\n🧹 Cleaning up demo data...")
        
        try:
            # Delete demo validations
            for validation in self.demo_validations:
                await db.delete(validation)
            
            # Delete demo opportunities
            for opportunity in self.demo_opportunities:
                await db.delete(opportunity)
            
            # Delete demo users
            for user in self.demo_users:
                await db.delete(user)
            
            await db.commit()
            print("✅ Demo data cleaned up successfully")
            
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
            await db.rollback()


async def main():
    """Run the fraud detection demo."""
    demo = FraudDetectionDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())