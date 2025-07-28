#!/usr/bin/env python3
"""Demonstration of user matching functionality."""

import asyncio
from shared.services.user_matching_service import (
    UserMatchingService, 
    InterestProfile, 
    SkillGap,
    UserMatch,
    MatchingType
)


def create_sample_interest_profiles():
    """Create sample interest profiles for demonstration."""
    
    # AI/ML Expert Profile
    ai_expert_profile = InterestProfile(
        ai_solution_preferences={
            "machine_learning": 0.95,
            "nlp": 0.90,
            "computer_vision": 0.75,
            "deep_learning": 0.85
        },
        industry_preferences={
            "healthcare": 0.80,
            "fintech": 0.70,
            "autonomous_vehicles": 0.60
        },
        complexity_preference="high",
        market_size_preference="large",
        activity_patterns={
            "total_interactions": 150,
            "recent_interactions": 25,
            "bookmark_rate": 0.15
        },
        engagement_level=0.85
    )
    
    # Business Strategist Profile
    business_expert_profile = InterestProfile(
        ai_solution_preferences={
            "automation": 0.80,
            "predictive_analytics": 0.75,
            "recommendation_systems": 0.70
        },
        industry_preferences={
            "ecommerce": 0.90,
            "retail": 0.85,
            "marketing": 0.80,
            "fintech": 0.60
        },
        complexity_preference="medium",
        market_size_preference="large",
        activity_patterns={
            "total_interactions": 80,
            "recent_interactions": 15,
            "bookmark_rate": 0.20
        },
        engagement_level=0.70
    )
    
    # Product Manager Profile
    product_manager_profile = InterestProfile(
        ai_solution_preferences={
            "recommendation_systems": 0.85,
            "nlp": 0.70,
            "automation": 0.65,
            "predictive_analytics": 0.60
        },
        industry_preferences={
            "saas": 0.90,
            "ecommerce": 0.75,
            "healthcare": 0.50,
            "fintech": 0.70
        },
        complexity_preference="medium",
        market_size_preference="medium",
        activity_patterns={
            "total_interactions": 120,
            "recent_interactions": 20,
            "bookmark_rate": 0.18
        },
        engagement_level=0.75
    )
    
    return {
        "ai_expert": ai_expert_profile,
        "business_expert": business_expert_profile,
        "product_manager": product_manager_profile
    }


def create_sample_skill_profiles():
    """Create sample skill profiles for demonstration."""
    
    # AI/ML Expert Skills
    ai_expert_skills = {
        "ai_machine_learning": 0.95,
        "ai_nlp": 0.90,
        "ai_computer_vision": 0.75,
        "ai_deep_learning": 0.85,
        "technical_python": 0.90,
        "technical_tensorflow": 0.80,
        "technical_pytorch": 0.75,
        "expertise_machine_learning": 1.0,
        "expertise_nlp": 1.0,
        "domain_expertise": 1.0,
        "validation": 0.9
    }
    
    # Business Strategist Skills
    business_expert_skills = {
        "business_strategy": 0.95,
        "business_marketing": 0.85,
        "business_product_management": 0.80,
        "business_fundraising": 0.70,
        "business_partnerships": 0.75,
        "expertise_business_strategy": 1.0,
        "expertise_product_management": 1.0,
        "expertise_marketing": 1.0,
        "domain_expertise": 1.0,
        "validation": 0.9
    }
    
    # Full-stack Developer Skills
    fullstack_dev_skills = {
        "technical_web_development": 0.90,
        "technical_api_design": 0.85,
        "technical_database_design": 0.80,
        "technical_javascript": 0.85,
        "technical_python": 0.75,
        "technical_react": 0.80,
        "technical_nodejs": 0.75,
        "expertise_web_development": 1.0,
        "expertise_api_design": 1.0,
        "expertise_database_design": 1.0
    }
    
    return {
        "ai_expert": ai_expert_skills,
        "business_expert": business_expert_skills,
        "fullstack_dev": fullstack_dev_skills
    }


def create_sample_skill_gaps():
    """Create sample skill gaps for demonstration."""
    
    # AI Expert's skill gaps (needs business skills)
    ai_expert_gaps = [
        SkillGap("business", "strategy", 0.85, 0.80),
        SkillGap("business", "marketing", 0.70, 0.75),
        SkillGap("business", "fundraising", 0.60, 0.70),
        SkillGap("product", "management", 0.75, 0.65),
        SkillGap("finance", "business_model", 0.65, 0.60)
    ]
    
    # Business Expert's skill gaps (needs technical skills)
    business_expert_gaps = [
        SkillGap("ai", "machine_learning", 0.80, 0.85),
        SkillGap("ai", "nlp", 0.70, 0.75),
        SkillGap("technical", "programming", 0.75, 0.80),
        SkillGap("technical", "api_design", 0.65, 0.70),
        SkillGap("technical", "database_design", 0.60, 0.65)
    ]
    
    return {
        "ai_expert": ai_expert_gaps,
        "business_expert": business_expert_gaps
    }


async def demonstrate_interest_matching():
    """Demonstrate interest-based matching."""
    print("🎯 Interest-Based Matching Demonstration")
    print("=" * 50)
    
    matching_service = UserMatchingService()
    profiles = create_sample_interest_profiles()
    
    # Compare AI Expert with others
    ai_profile = profiles["ai_expert"]
    
    print("AI Expert's Interests:")
    print(f"  AI Preferences: {ai_profile.ai_solution_preferences}")
    print(f"  Industry Preferences: {ai_profile.industry_preferences}")
    print(f"  Complexity: {ai_profile.complexity_preference}")
    print(f"  Engagement Level: {ai_profile.engagement_level:.2f}")
    print()
    
    for name, profile in profiles.items():
        if name == "ai_expert":
            continue
        
        similarity = await matching_service._calculate_interest_similarity(ai_profile, profile)
        
        print(f"Match with {name.replace('_', ' ').title()}:")
        print(f"  Similarity Score: {similarity:.3f}")
        
        # Find common interests
        common_ai = set(ai_profile.ai_solution_preferences.keys()) & set(profile.ai_solution_preferences.keys())
        common_industries = set(ai_profile.industry_preferences.keys()) & set(profile.industry_preferences.keys())
        
        print(f"  Common AI Interests: {', '.join(common_ai)}")
        print(f"  Common Industries: {', '.join(common_industries)}")
        print(f"  Complexity Match: {ai_profile.complexity_preference == profile.complexity_preference}")
        print()


async def demonstrate_skill_complementarity():
    """Demonstrate skill complementarity matching."""
    print("🔧 Skill Complementarity Demonstration")
    print("=" * 50)
    
    matching_service = UserMatchingService()
    skills = create_sample_skill_profiles()
    gaps = create_sample_skill_gaps()
    
    # AI Expert looking for complementary skills
    ai_skills = skills["ai_expert"]
    ai_gaps = gaps["ai_expert"]
    
    print("AI Expert's Skills:")
    top_skills = sorted(ai_skills.items(), key=lambda x: x[1], reverse=True)[:5]
    for skill, score in top_skills:
        print(f"  {skill}: {score:.2f}")
    print()
    
    print("AI Expert's Skill Gaps:")
    for gap in ai_gaps:
        print(f"  {gap.skill_category}/{gap.skill_name}: importance={gap.importance_score:.2f}, severity={gap.gap_severity:.2f}")
    print()
    
    # Test complementarity with business expert
    business_skills = skills["business_expert"]
    
    complementarity = await matching_service._calculate_skill_complementarity(
        ai_skills, business_skills, ai_gaps
    )
    
    print(f"Complementarity with Business Expert: {complementarity:.3f}")
    
    # Show which gaps can be filled
    print("Skills that Business Expert can provide:")
    for gap in ai_gaps:
        skill_key = f"{gap.skill_category}_{gap.skill_name}"
        if skill_key in business_skills and business_skills[skill_key] > 0.5:
            print(f"  ✓ {gap.skill_category}/{gap.skill_name} (expert level: {business_skills[skill_key]:.2f})")
    print()


def demonstrate_matching_algorithms():
    """Demonstrate different matching algorithm concepts."""
    print("🧠 Matching Algorithm Concepts")
    print("=" * 50)
    
    matching_service = UserMatchingService()
    
    # Cosine Similarity Example
    print("1. Cosine Similarity for Interest Matching:")
    user_interests = {"ai": 0.9, "healthcare": 0.8, "fintech": 0.6}
    candidate1_interests = {"ai": 0.8, "healthcare": 0.9, "retail": 0.5}
    candidate2_interests = {"blockchain": 0.9, "gaming": 0.8, "entertainment": 0.7}
    
    sim1 = matching_service._calculate_cosine_similarity(user_interests, candidate1_interests)
    sim2 = matching_service._calculate_cosine_similarity(user_interests, candidate2_interests)
    
    print(f"  User interests: {user_interests}")
    print(f"  Candidate 1 similarity: {sim1:.3f} (overlapping interests)")
    print(f"  Candidate 2 similarity: {sim2:.3f} (different interests)")
    print()
    
    # Skill Overlap Example
    print("2. Skill Overlap Analysis:")
    user_skills = {"python": 0.9, "ml": 0.8, "nlp": 0.7}
    candidate_skills = {"python": 0.7, "javascript": 0.8, "react": 0.9}
    
    overlap = matching_service._calculate_skill_overlap(user_skills, candidate_skills)
    print(f"  User skills: {user_skills}")
    print(f"  Candidate skills: {candidate_skills}")
    print(f"  Skill overlap: {overlap:.3f}")
    print()
    
    # Diversity vs Similarity Trade-off
    print("3. Diversity vs Similarity Trade-off:")
    print("  Interest-based matching: Finds users with SIMILAR interests")
    print("  Skill-complementary matching: Finds users with DIFFERENT but complementary skills")
    print("  Hybrid matching: Balances both similarity and complementarity")
    print()


def create_mock_user_match():
    """Create a mock UserMatch for demonstration."""
    return UserMatch(
        user_id="demo-user-123",
        username="business_strategist",
        full_name="Sarah Johnson",
        avatar_url="https://example.com/avatar.jpg",
        match_score=0.87,
        match_type=MatchingType.SKILL_COMPLEMENTARY,
        match_reasons=[
            "Fills critical business strategy gap",
            "Strong marketing expertise complements technical skills",
            "Experience in target industry (fintech)"
        ],
        common_interests=["fintech", "automation"],
        complementary_skills=[
            "business: strategy",
            "business: marketing", 
            "business: fundraising",
            "product: management"
        ],
        expertise_domains=["business_strategy", "product_management", "marketing"],
        reputation_score=8.2,
        compatibility_factors={
            "skill_complementarity": 0.92,
            "skill_overlap": 0.15,
            "gap_coverage": 0.80,
            "reputation_compatibility": 0.85
        }
    )


def demonstrate_match_results():
    """Demonstrate what a complete match result looks like."""
    print("📊 Complete Match Result Example")
    print("=" * 50)
    
    match = create_mock_user_match()
    
    print(f"Matched User: {match.full_name} (@{match.username})")
    print(f"Match Score: {match.match_score:.2f}/1.00")
    print(f"Match Type: {match.match_type.value}")
    print(f"Reputation: {match.reputation_score:.1f}/10.0")
    print()
    
    print("Why this is a good match:")
    for i, reason in enumerate(match.match_reasons, 1):
        print(f"  {i}. {reason}")
    print()
    
    print("Common Interests:")
    for interest in match.common_interests:
        print(f"  • {interest}")
    print()
    
    print("Complementary Skills They Bring:")
    for skill in match.complementary_skills:
        print(f"  • {skill}")
    print()
    
    print("Expertise Domains:")
    for domain in match.expertise_domains:
        print(f"  • {domain}")
    print()
    
    print("Compatibility Analysis:")
    for factor, score in match.compatibility_factors.items():
        print(f"  {factor.replace('_', ' ').title()}: {score:.2f}")
    print()


async def main():
    """Run the complete demonstration."""
    print("🚀 AI Opportunity Browser - User Matching System Demo")
    print("=" * 60)
    print()
    
    await demonstrate_interest_matching()
    print()
    
    await demonstrate_skill_complementarity()
    print()
    
    demonstrate_matching_algorithms()
    print()
    
    demonstrate_match_results()
    print()
    
    print("✨ Key Benefits of the User Matching System:")
    print("  • Intelligent interest-based matching finds like-minded collaborators")
    print("  • Skill complementarity analysis identifies perfect co-founders")
    print("  • Hybrid approach balances similarity and diversity")
    print("  • Detailed compatibility scoring helps users make informed decisions")
    print("  • Supports both technical and business collaboration needs")
    print()
    
    print("🎯 Use Cases:")
    print("  • AI experts finding business co-founders")
    print("  • Entrepreneurs discovering technical partners")
    print("  • Investors connecting with domain experts")
    print("  • Teams forming around specific opportunities")
    print("  • Skill gap identification and filling")


if __name__ == "__main__":
    asyncio.run(main())