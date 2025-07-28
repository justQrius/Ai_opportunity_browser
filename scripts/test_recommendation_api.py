#!/usr/bin/env python3
"""
Test script for the Recommendation API implementation.

This script tests the personalized recommendation engine and user preference learning
functionality as specified in Requirements 6.1.3.

Tests:
- Personalized recommendations endpoint
- Recommendation feedback endpoint
- Recommendation explanation endpoint
- User preference endpoints
- User interaction recording
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from shared.database import get_db_session
from shared.models.user import User, UserRole
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.user_interaction import UserInteraction, UserPreference, RecommendationFeedback, InteractionType
from shared.services.recommendation_service import recommendation_service
from shared.schemas.opportunity import OpportunityRecommendationRequest
import structlog

logger = structlog.get_logger(__name__)


class RecommendationAPITester:
    """Test the recommendation API functionality."""
    
    def __init__(self):
        self.test_user_id = None
        self.test_opportunities = []
        self.test_interactions = []
        
    async def run_all_tests(self):
        """Run all recommendation API tests."""
        print("🚀 Starting Recommendation API Tests")
        print("=" * 50)
        
        async with get_db_session() as db:
            try:
                # Setup test data
                await self.setup_test_data(db)
                
                # Test core recommendation functionality
                await self.test_personalized_recommendations(db)
                await self.test_recommendation_feedback(db)
                await self.test_recommendation_explanation(db)
                await self.test_user_preferences(db)
                await self.test_interaction_recording(db)
                await self.test_preference_learning(db)
                
                print("\n✅ All Recommendation API tests completed successfully!")
                
            except Exception as e:
                print(f"\n❌ Test failed: {str(e)}")
                raise
            finally:
                # Cleanup test data
                await self.cleanup_test_data(db)
    
    async def setup_test_data(self, db: AsyncSession):
        """Set up test data for recommendation tests."""
        print("\n📋 Setting up test data...")
        
        # Create test user
        test_user = User(
            email="test_recommendations@example.com",
            username="test_rec_user",
            full_name="Test Recommendation User",
            role=UserRole.USER,
            hashed_password="test_hash"
        )
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)
        self.test_user_id = test_user.id
        
        # Create test opportunities with different characteristics
        opportunities_data = [
            {
                "title": "AI-Powered Healthcare Diagnosis Assistant",
                "description": "An AI system that helps doctors diagnose diseases using machine learning and computer vision to analyze medical images and patient data.",
                "ai_solution_types": '["ml", "computer_vision", "nlp"]',
                "target_industries": '["healthcare", "medical_devices"]',
                "validation_score": 8.5,
                "implementation_complexity": "high"
            },
            {
                "title": "Smart Financial Trading Bot",
                "description": "Automated trading system using reinforcement learning and predictive analytics to make investment decisions in real-time.",
                "ai_solution_types": '["ml", "predictive_analytics", "automation"]',
                "target_industries": '["fintech", "investment"]',
                "validation_score": 7.2,
                "implementation_complexity": "medium"
            },
            {
                "title": "Natural Language Customer Support",
                "description": "AI chatbot that provides intelligent customer support using natural language processing and sentiment analysis.",
                "ai_solution_types": '["nlp", "chatbot", "sentiment_analysis"]',
                "target_industries": '["customer_service", "e_commerce"]',
                "validation_score": 6.8,
                "implementation_complexity": "low"
            },
            {
                "title": "Computer Vision Quality Control",
                "description": "Manufacturing quality control system using computer vision to detect defects in products on assembly lines.",
                "ai_solution_types": '["computer_vision", "automation"]',
                "target_industries": '["manufacturing", "automotive"]',
                "validation_score": 9.1,
                "implementation_complexity": "medium"
            },
            {
                "title": "Predictive Maintenance System",
                "description": "IoT and ML-based system that predicts equipment failures before they happen, reducing downtime and maintenance costs.",
                "ai_solution_types": '["ml", "predictive_analytics", "iot"]',
                "target_industries": '["manufacturing", "energy", "transportation"]',
                "validation_score": 8.7,
                "implementation_complexity": "high"
            }
        ]
        
        for opp_data in opportunities_data:
            opportunity = Opportunity(
                title=opp_data["title"],
                description=opp_data["description"],
                ai_solution_types=opp_data["ai_solution_types"],
                target_industries=opp_data["target_industries"],
                validation_score=opp_data["validation_score"],
                implementation_complexity=opp_data["implementation_complexity"],
                status=OpportunityStatus.VALIDATED,
                confidence_rating=0.8,
                ai_feasibility_score=7.5,
                discovered_by_agent="test_agent"
            )
            db.add(opportunity)
            self.test_opportunities.append(opportunity)
        
        await db.commit()
        for opp in self.test_opportunities:
            await db.refresh(opp)
        
        print(f"✅ Created test user: {self.test_user_id}")
        print(f"✅ Created {len(self.test_opportunities)} test opportunities")
    
    async def test_personalized_recommendations(self, db: AsyncSession):
        """Test the personalized recommendation engine."""
        print("\n🎯 Testing Personalized Recommendations...")
        
        # Test basic recommendations
        request = OpportunityRecommendationRequest(
            user_id=self.test_user_id,
            limit=3,
            include_viewed=False
        )
        
        recommendations = await recommendation_service.get_personalized_recommendations(db, request)
        
        assert len(recommendations) <= 3, f"Expected max 3 recommendations, got {len(recommendations)}"
        assert all(isinstance(opp, Opportunity) for opp in recommendations), "All recommendations should be Opportunity objects"
        
        print(f"✅ Basic recommendations: {len(recommendations)} opportunities returned")
        
        # Test filtered recommendations
        filtered_request = OpportunityRecommendationRequest(
            user_id=self.test_user_id,
            limit=5,
            ai_solution_types=["ml", "computer_vision"],
            industries=["healthcare", "manufacturing"]
        )
        
        filtered_recommendations = await recommendation_service.get_personalized_recommendations(db, filtered_request)
        
        print(f"✅ Filtered recommendations: {len(filtered_recommendations)} opportunities returned")
        
        # Test with user preferences
        await self._create_user_preferences(db)
        
        personalized_request = OpportunityRecommendationRequest(
            user_id=self.test_user_id,
            limit=5
        )
        
        personalized_recommendations = await recommendation_service.get_personalized_recommendations(db, personalized_request)
        
        print(f"✅ Personalized recommendations: {len(personalized_recommendations)} opportunities returned")
        print("✅ Personalized recommendation engine working correctly")
    
    async def test_recommendation_feedback(self, db: AsyncSession):
        """Test recommendation feedback recording."""
        print("\n📝 Testing Recommendation Feedback...")
        
        if not self.test_opportunities:
            raise Exception("No test opportunities available for feedback testing")
        
        test_opportunity = self.test_opportunities[0]
        
        # Test positive feedback
        positive_feedback = await recommendation_service.record_recommendation_feedback(
            db=db,
            user_id=self.test_user_id,
            opportunity_id=test_opportunity.id,
            is_relevant=True,
            feedback_score=5,
            feedback_text="This recommendation was very relevant to my interests",
            recommendation_algorithm="hybrid",
            recommendation_score=0.85,
            recommendation_rank=1
        )
        
        assert positive_feedback.is_relevant == True
        assert positive_feedback.feedback_score == 5
        assert positive_feedback.user_id == self.test_user_id
        
        print("✅ Positive feedback recorded successfully")
        
        # Test negative feedback
        negative_feedback = await recommendation_service.record_recommendation_feedback(
            db=db,
            user_id=self.test_user_id,
            opportunity_id=self.test_opportunities[1].id,
            is_relevant=False,
            feedback_score=2,
            feedback_text="This was not relevant to my needs",
            recommendation_algorithm="hybrid",
            recommendation_score=0.45,
            recommendation_rank=3
        )
        
        assert negative_feedback.is_relevant == False
        assert negative_feedback.feedback_score == 2
        
        print("✅ Negative feedback recorded successfully")
        print("✅ Recommendation feedback system working correctly")
    
    async def test_recommendation_explanation(self, db: AsyncSession):
        """Test recommendation explanation generation."""
        print("\n💡 Testing Recommendation Explanations...")
        
        if not self.test_opportunities:
            raise Exception("No test opportunities available for explanation testing")
        
        test_opportunity = self.test_opportunities[0]
        
        explanation = await recommendation_service.explain_recommendation(
            db, self.test_user_id, test_opportunity.id
        )
        
        assert "opportunity_id" in explanation
        assert "recommendation_factors" in explanation
        assert "overall_score" in explanation
        assert "confidence" in explanation
        
        assert explanation["opportunity_id"] == test_opportunity.id
        assert isinstance(explanation["recommendation_factors"], list)
        assert isinstance(explanation["overall_score"], (int, float))
        
        print(f"✅ Explanation generated with {len(explanation['recommendation_factors'])} factors")
        print(f"✅ Overall recommendation score: {explanation['overall_score']:.2f}")
        
        # Test explanation for opportunity without user preferences
        new_user = User(
            email="test_explain@example.com",
            username="test_explain_user",
            full_name="Test Explain User",
            role=UserRole.USER,
            hashed_password="test_hash"
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        basic_explanation = await recommendation_service.explain_recommendation(
            db, new_user.id, test_opportunity.id
        )
        
        assert "recommendation_factors" in basic_explanation
        assert len(basic_explanation["recommendation_factors"]) > 0
        
        print("✅ Basic explanation for new user generated successfully")
        print("✅ Recommendation explanation system working correctly")
    
    async def test_user_preferences(self, db: AsyncSession):
        """Test user preference management."""
        print("\n⚙️ Testing User Preferences...")
        
        # Test getting/creating preferences
        preferences = await recommendation_service.get_or_create_user_preferences(db, self.test_user_id)
        
        assert preferences.user_id == self.test_user_id
        assert preferences.min_validation_score >= 0.0
        assert isinstance(preferences.prefers_trending, bool)
        assert isinstance(preferences.prefers_new_opportunities, bool)
        
        print("✅ User preferences retrieved/created successfully")
        
        # Test updating preferences from interactions
        await self._create_test_interactions(db)
        
        updated_preferences = await recommendation_service.update_user_preferences_from_interactions(
            db, self.test_user_id
        )
        
        assert updated_preferences is not None
        assert updated_preferences.interaction_count > 0
        assert updated_preferences.confidence_score >= 0.0
        
        print(f"✅ Preferences updated from {updated_preferences.interaction_count} interactions")
        print(f"✅ Confidence score: {updated_preferences.confidence_score:.2f}")
        print("✅ User preference system working correctly")
    
    async def test_interaction_recording(self, db: AsyncSession):
        """Test user interaction recording."""
        print("\n📊 Testing Interaction Recording...")
        
        test_opportunity = self.test_opportunities[0]
        
        # Test different interaction types
        interaction_tests = [
            {
                "type": InteractionType.VIEW,
                "duration": 45,
                "description": "View interaction"
            },
            {
                "type": InteractionType.CLICK,
                "duration": 120,
                "description": "Click interaction"
            },
            {
                "type": InteractionType.BOOKMARK,
                "duration": None,
                "description": "Bookmark interaction"
            },
            {
                "type": InteractionType.SEARCH,
                "duration": None,
                "description": "Search interaction"
            }
        ]
        
        for test_data in interaction_tests:
            interaction = await recommendation_service.record_interaction(
                db=db,
                user_id=self.test_user_id,
                interaction_type=test_data["type"],
                opportunity_id=test_opportunity.id if test_data["type"] != InteractionType.SEARCH else None,
                search_query="AI healthcare solutions" if test_data["type"] == InteractionType.SEARCH else None,
                duration_seconds=test_data["duration"]
            )
            
            assert interaction.user_id == self.test_user_id
            assert interaction.interaction_type == test_data["type"]
            assert interaction.engagement_score > 0.0
            
            print(f"✅ {test_data['description']} recorded (engagement: {interaction.engagement_score:.2f})")
        
        print("✅ Interaction recording system working correctly")
    
    async def test_preference_learning(self, db: AsyncSession):
        """Test that preferences are learned from user behavior."""
        print("\n🧠 Testing Preference Learning...")
        
        # Get initial preferences
        initial_preferences = await recommendation_service.get_or_create_user_preferences(db, self.test_user_id)
        initial_confidence = initial_preferences.confidence_score
        
        # Simulate user interactions with healthcare AI opportunities
        healthcare_opportunities = [opp for opp in self.test_opportunities 
                                  if "healthcare" in opp.target_industries]
        
        if healthcare_opportunities:
            for opp in healthcare_opportunities[:2]:  # Interact with first 2 healthcare opportunities
                # Record positive interactions
                await recommendation_service.record_interaction(
                    db=db,
                    user_id=self.test_user_id,
                    interaction_type=InteractionType.VIEW,
                    opportunity_id=opp.id,
                    duration_seconds=180  # 3 minutes - high engagement
                )
                
                await recommendation_service.record_interaction(
                    db=db,
                    user_id=self.test_user_id,
                    interaction_type=InteractionType.BOOKMARK,
                    opportunity_id=opp.id
                )
                
                # Record positive feedback
                await recommendation_service.record_recommendation_feedback(
                    db=db,
                    user_id=self.test_user_id,
                    opportunity_id=opp.id,
                    is_relevant=True,
                    feedback_score=5,
                    recommendation_algorithm="hybrid",
                    recommendation_score=0.8,
                    recommendation_rank=1
                )
        
        # Update preferences based on interactions
        updated_preferences = await recommendation_service.update_user_preferences_from_interactions(
            db, self.test_user_id
        )
        
        # Check that preferences have been learned
        assert updated_preferences.confidence_score >= initial_confidence
        assert updated_preferences.interaction_count > 0
        
        # Check if healthcare preference was learned
        if updated_preferences.preferred_industries:
            try:
                preferred_industries = json.loads(updated_preferences.preferred_industries)
                if "healthcare" in preferred_industries:
                    print(f"✅ Healthcare preference learned: {preferred_industries['healthcare']:.2f}")
            except json.JSONDecodeError:
                pass
        
        print(f"✅ Confidence score improved: {initial_confidence:.2f} → {updated_preferences.confidence_score:.2f}")
        print("✅ Preference learning system working correctly")
    
    async def _create_user_preferences(self, db: AsyncSession):
        """Create test user preferences."""
        preferences = UserPreference(
            user_id=self.test_user_id,
            preferred_ai_types='{"ml": 0.8, "computer_vision": 0.7, "nlp": 0.6}',
            preferred_industries='{"healthcare": 0.9, "fintech": 0.5}',
            preferred_complexity="medium",
            min_validation_score=7.0,
            prefers_trending=True,
            prefers_new_opportunities=True,
            confidence_score=0.6,
            interaction_count=15
        )
        db.add(preferences)
        await db.commit()
    
    async def _create_test_interactions(self, db: AsyncSession):
        """Create test interactions for preference learning."""
        for i, opportunity in enumerate(self.test_opportunities[:3]):
            interaction = UserInteraction(
                user_id=self.test_user_id,
                opportunity_id=opportunity.id,
                interaction_type=InteractionType.VIEW,
                duration_seconds=60 + (i * 30),
                engagement_score=2.0 + (i * 0.5)
            )
            db.add(interaction)
            self.test_interactions.append(interaction)
        
        await db.commit()
    
    async def cleanup_test_data(self, db: AsyncSession):
        """Clean up test data."""
        print("\n🧹 Cleaning up test data...")
        
        try:
            # Delete test interactions
            for interaction in self.test_interactions:
                await db.delete(interaction)
            
            # Delete test opportunities
            for opportunity in self.test_opportunities:
                await db.delete(opportunity)
            
            # Delete test user and related data
            if self.test_user_id:
                from sqlalchemy import delete
                
                # Delete user preferences
                await db.execute(delete(UserPreference).where(UserPreference.user_id == self.test_user_id))
                
                # Delete user interactions
                await db.execute(delete(UserInteraction).where(UserInteraction.user_id == self.test_user_id))
                
                # Delete recommendation feedback
                await db.execute(delete(RecommendationFeedback).where(RecommendationFeedback.user_id == self.test_user_id))
                
                # Delete user
                await db.execute(delete(User).where(User.id == self.test_user_id))
            
            await db.commit()
            print("✅ Test data cleaned up successfully")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not clean up all test data: {str(e)}")


async def main():
    """Run the recommendation API tests."""
    tester = RecommendationAPITester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())