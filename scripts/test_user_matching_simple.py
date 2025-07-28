#!/usr/bin/env python3
"""Simple test script for user matching functionality."""

import asyncio
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from shared.models.base import Base
from shared.models.user import User, UserRole
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.user_interaction import UserInteraction, InteractionType
from shared.services.user_matching_service import UserMatchingService, MatchingType
from shared.auth import hash_password


async def create_test_data(session: AsyncSession):
    """Create test data for user matching."""
    print("Creating test data...")
    
    # Create test users
    users = []
    
    # User 1: AI/ML Expert
    user1 = User(
        email="ai_expert@test.com",
        username="ai_expert",
        hashed_password=hash_password("password123"),
        full_name="AI Expert",
        role=UserRole.EXPERT,
        expertise_domains=json.dumps(["machine_learning", "nlp", "computer_vision"]),
        reputation_score=8.5,
        is_active=True,
        is_verified=True
    )
    session.add(user1)
    users.append(user1)
    
    # User 2: Business Strategist
    user2 = User(
        email="business_expert@test.com",
        username="business_expert",
        hashed_password=hash_password("password123"),
        full_name="Business Expert",
        role=UserRole.EXPERT,
        expertise_domains=json.dumps(["business_strategy", "product_management", "marketing"]),
        reputation_score=7.2,
        is_active=True,
        is_verified=True
    )
    session.add(user2)
    users.append(user2)
    
    # User 3: Full-stack Developer
    user3 = User(
        email="fullstack_dev@test.com",
        username="fullstack_dev",
        hashed_password=hash_password("password123"),
        full_name="Full Stack Developer",
        role=UserRole.USER,
        expertise_domains=json.dumps(["web_development", "api_design", "database_design"]),
        reputation_score=6.8,
        is_active=True,
        is_verified=True
    )
    session.add(user3)
    users.append(user3)
    
    # User 4: Similar to User 1 (for interest matching)
    user4 = User(
        email="ai_researcher@test.com",
        username="ai_researcher",
        hashed_password=hash_password("password123"),
        full_name="AI Researcher",
        role=UserRole.EXPERT,
        expertise_domains=json.dumps(["machine_learning", "deep_learning", "research"]),
        reputation_score=9.1,
        is_active=True,
        is_verified=True
    )
    session.add(user4)
    users.append(user4)
    
    await session.commit()
    
    # Create test opportunities
    opportunities = []
    
    # AI/ML Opportunity
    opp1 = Opportunity(
        title="AI-Powered Customer Service",
        description="Build an AI chatbot for customer service automation",
        ai_solution_types=json.dumps(["nlp", "machine_learning"]),
        target_industries=json.dumps(["customer_service", "saas"]),
        implementation_complexity="medium",
        market_size_estimate="large",
        validation_score=8.2,
        status=OpportunityStatus.VALIDATED
    )
    session.add(opp1)
    opportunities.append(opp1)
    
    # Computer Vision Opportunity
    opp2 = Opportunity(
        title="Automated Quality Control",
        description="Computer vision system for manufacturing quality control",
        ai_solution_types=json.dumps(["computer_vision", "automation"]),
        target_industries=json.dumps(["manufacturing", "quality_control"]),
        implementation_complexity="high",
        market_size_estimate="medium",
        validation_score=7.8,
        status=OpportunityStatus.VALIDATED
    )
    session.add(opp2)
    opportunities.append(opp2)
    
    await session.commit()
    
    # Create user interactions
    interactions = []
    
    # User 1 interactions (AI expert interested in NLP)
    for i, opp in enumerate(opportunities):
        interaction = UserInteraction(
            user_id=user1.id,
            opportunity_id=opp.id,
            interaction_type=InteractionType.VIEW if i % 2 == 0 else InteractionType.BOOKMARK,
            duration_seconds=120 + i * 30,
            engagement_score=0.8 + i * 0.1
        )
        session.add(interaction)
        interactions.append(interaction)
    
    # User 4 interactions (similar to user 1)
    for i, opp in enumerate(opportunities):
        interaction = UserInteraction(
            user_id=user4.id,
            opportunity_id=opp.id,
            interaction_type=InteractionType.VIEW if i % 2 == 1 else InteractionType.CLICK,
            duration_seconds=100 + i * 25,
            engagement_score=0.7 + i * 0.1
        )
        session.add(interaction)
        interactions.append(interaction)
    
    await session.commit()
    
    print(f"Created {len(users)} users, {len(opportunities)} opportunities, {len(interactions)} interactions")
    return users, opportunities, interactions


async def test_user_matching():
    """Test user matching functionality."""
    print("Starting user matching test...")
    
    # Create in-memory database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Create test data
        users, opportunities, interactions = await create_test_data(session)
        
        # Initialize matching service
        matching_service = UserMatchingService()
        
        print("\n=== Testing Interest-Based Matching ===")
        try:
            interest_matches = await matching_service.find_interest_based_matches(
                db=session,
                user_id=users[0].id,  # AI expert
                limit=10,
                min_match_score=0.1
            )
            
            print(f"Found {len(interest_matches)} interest-based matches for {users[0].username}")
            for match in interest_matches:
                print(f"  - {match.username} (score: {match.match_score:.3f})")
                print(f"    Reasons: {', '.join(match.match_reasons)}")
                print(f"    Common interests: {', '.join(match.common_interests)}")
                print()
        
        except Exception as e:
            print(f"Interest-based matching failed: {e}")
        
        print("\n=== Testing Skill-Complementary Matching ===")
        try:
            skill_matches = await matching_service.find_complementary_skill_matches(
                db=session,
                user_id=users[0].id,  # AI expert
                opportunity_id=opportunities[0].id,
                limit=10,
                min_match_score=0.1
            )
            
            print(f"Found {len(skill_matches)} skill-complementary matches for {users[0].username}")
            for match in skill_matches:
                print(f"  - {match.username} (score: {match.match_score:.3f})")
                print(f"    Reasons: {', '.join(match.match_reasons)}")
                print(f"    Complementary skills: {', '.join(match.complementary_skills)}")
                print()
        
        except Exception as e:
            print(f"Skill-complementary matching failed: {e}")
        
        print("\n=== Testing Hybrid Matching ===")
        try:
            hybrid_matches = await matching_service.find_hybrid_matches(
                db=session,
                user_id=users[0].id,  # AI expert
                opportunity_id=opportunities[0].id,
                limit=10,
                min_match_score=0.1
            )
            
            print(f"Found {len(hybrid_matches)} hybrid matches for {users[0].username}")
            for match in hybrid_matches:
                print(f"  - {match.username} (score: {match.match_score:.3f})")
                print(f"    Type: {match.match_type.value}")
                print(f"    Reasons: {', '.join(match.match_reasons)}")
                print()
        
        except Exception as e:
            print(f"Hybrid matching failed: {e}")
        
        print("\n=== Testing Skill Analysis ===")
        try:
            user_skills = await matching_service._extract_user_skills(session, users[0].id)
            print(f"User skills for {users[0].username}:")
            for skill, score in user_skills.items():
                print(f"  - {skill}: {score:.2f}")
            
            skill_gaps = await matching_service._identify_skill_gaps(
                session, users[0].id, opportunities[0].id
            )
            print(f"\nSkill gaps for {users[0].username}:")
            for gap in skill_gaps:
                print(f"  - {gap.skill_category}/{gap.skill_name}: importance={gap.importance_score:.2f}, severity={gap.gap_severity:.2f}")
        
        except Exception as e:
            print(f"Skill analysis failed: {e}")
        
        print("\n=== Testing Interest Profile Building ===")
        try:
            interest_profile = await matching_service._build_user_interest_profile(session, users[0].id)
            if interest_profile:
                print(f"Interest profile for {users[0].username}:")
                print(f"  AI preferences: {interest_profile.ai_solution_preferences}")
                print(f"  Industry preferences: {interest_profile.industry_preferences}")
                print(f"  Complexity preference: {interest_profile.complexity_preference}")
                print(f"  Engagement level: {interest_profile.engagement_level:.2f}")
            else:
                print(f"No interest profile found for {users[0].username}")
        
        except Exception as e:
            print(f"Interest profile building failed: {e}")
    
    await engine.dispose()
    print("\nUser matching test completed!")


if __name__ == "__main__":
    asyncio.run(test_user_matching())