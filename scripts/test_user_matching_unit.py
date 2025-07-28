#!/usr/bin/env python3
"""Unit tests for user matching functionality without database dependencies."""

import asyncio
from shared.services.user_matching_service import UserMatchingService, InterestProfile, SkillGap


def test_cosine_similarity():
    """Test cosine similarity calculation."""
    print("Testing cosine similarity calculation...")
    
    matching_service = UserMatchingService()
    
    # Test identical dictionaries
    dict1 = {"a": 1.0, "b": 2.0, "c": 3.0}
    similarity = matching_service._calculate_cosine_similarity(dict1, dict1)
    print(f"Identical dictionaries similarity: {similarity:.3f} (should be ~1.0)")
    assert abs(similarity - 1.0) < 1e-6
    
    # Test orthogonal dictionaries
    dict2 = {"d": 1.0, "e": 2.0, "f": 3.0}
    similarity = matching_service._calculate_cosine_similarity(dict1, dict2)
    print(f"Orthogonal dictionaries similarity: {similarity:.3f} (should be 0.0)")
    assert similarity == 0.0
    
    # Test partial overlap
    dict3 = {"a": 2.0, "b": 1.0, "d": 1.0}
    similarity = matching_service._calculate_cosine_similarity(dict1, dict3)
    print(f"Partial overlap similarity: {similarity:.3f} (should be > 0.0)")
    assert similarity > 0.0
    
    # Test empty dictionaries
    similarity = matching_service._calculate_cosine_similarity({}, dict1)
    print(f"Empty dictionary similarity: {similarity:.3f} (should be 0.0)")
    assert similarity == 0.0
    
    print("✓ Cosine similarity tests passed\n")


async def test_interest_similarity():
    """Test interest similarity calculation."""
    print("Testing interest similarity calculation...")
    
    matching_service = UserMatchingService()
    
    # Create test profiles
    profile1 = InterestProfile(
        ai_solution_preferences={"nlp": 0.8, "machine_learning": 0.9, "computer_vision": 0.3},
        industry_preferences={"healthcare": 0.7, "fintech": 0.5, "retail": 0.2},
        complexity_preference="medium",
        market_size_preference="large",
        activity_patterns={},
        engagement_level=0.8
    )
    
    profile2 = InterestProfile(
        ai_solution_preferences={"nlp": 0.7, "machine_learning": 0.6, "automation": 0.4},
        industry_preferences={"healthcare": 0.8, "manufacturing": 0.6, "retail": 0.3},
        complexity_preference="medium",
        market_size_preference="large",
        activity_patterns={},
        engagement_level=0.7
    )
    
    similarity = await matching_service._calculate_interest_similarity(profile1, profile2)
    print(f"Interest similarity: {similarity:.3f}")
    assert 0.0 <= similarity <= 1.0
    assert similarity > 0.0  # Should have some similarity
    
    # Test with completely different profiles
    profile3 = InterestProfile(
        ai_solution_preferences={"automation": 0.9, "robotics": 0.8},
        industry_preferences={"manufacturing": 0.9, "logistics": 0.7},
        complexity_preference="high",
        market_size_preference="small",
        activity_patterns={},
        engagement_level=0.5
    )
    
    similarity2 = await matching_service._calculate_interest_similarity(profile1, profile3)
    print(f"Different profiles similarity: {similarity2:.3f}")
    assert similarity2 < similarity  # Should be less similar
    
    print("✓ Interest similarity tests passed\n")


def test_skill_overlap():
    """Test skill overlap calculation."""
    print("Testing skill overlap calculation...")
    
    matching_service = UserMatchingService()
    
    # Test identical skills
    skills1 = {"ai_nlp": 0.8, "ai_ml": 0.9, "tech_python": 0.7}
    overlap = matching_service._calculate_skill_overlap(skills1, skills1)
    print(f"Identical skills overlap: {overlap:.3f}")
    assert overlap > 0.5  # Should have significant overlap
    
    # Test no overlap
    skills2 = {"business_strategy": 0.8, "marketing": 0.7, "sales": 0.6}
    overlap = matching_service._calculate_skill_overlap(skills1, skills2)
    print(f"No overlap skills: {overlap:.3f} (should be 0.0)")
    assert overlap == 0.0
    
    # Test partial overlap
    skills3 = {"ai_nlp": 0.7, "business_strategy": 0.8, "tech_javascript": 0.6}
    overlap = matching_service._calculate_skill_overlap(skills1, skills3)
    print(f"Partial overlap: {overlap:.3f}")
    assert 0.0 < overlap < 0.5
    
    # Test empty skills
    overlap = matching_service._calculate_skill_overlap({}, skills1)
    print(f"Empty skills overlap: {overlap:.3f} (should be 0.0)")
    assert overlap == 0.0
    
    print("✓ Skill overlap tests passed\n")


async def test_skill_complementarity():
    """Test skill complementarity calculation."""
    print("Testing skill complementarity calculation...")
    
    matching_service = UserMatchingService()
    
    # User with AI skills
    user_skills = {
        "ai_nlp": 0.9,
        "ai_machine_learning": 0.8,
        "technical_programming": 0.7
    }
    
    # Candidate with business skills (complementary)
    candidate_skills = {
        "business_strategy": 0.8,
        "business_marketing": 0.7,
        "business_sales": 0.6
    }
    
    # Skill gaps that the candidate can fill
    skill_gaps = [
        SkillGap("business", "strategy", 0.8, 0.7),
        SkillGap("business", "marketing", 0.6, 0.5),
        SkillGap("business", "sales", 0.5, 0.4)
    ]
    
    complementarity = await matching_service._calculate_skill_complementarity(
        user_skills, candidate_skills, skill_gaps
    )
    print(f"Skill complementarity: {complementarity:.3f}")
    assert 0.0 <= complementarity <= 1.0
    assert complementarity > 0.0  # Should have complementarity
    
    # Test with candidate who can't fill gaps
    poor_candidate_skills = {
        "ai_computer_vision": 0.8,  # Similar to user, not complementary
        "technical_databases": 0.7
    }
    
    poor_complementarity = await matching_service._calculate_skill_complementarity(
        user_skills, poor_candidate_skills, skill_gaps
    )
    print(f"Poor complementarity: {poor_complementarity:.3f}")
    assert poor_complementarity < complementarity
    
    # Test with no skill gaps
    no_complementarity = await matching_service._calculate_skill_complementarity(
        user_skills, candidate_skills, []
    )
    print(f"No gaps complementarity: {no_complementarity:.3f} (should be 0.0)")
    assert no_complementarity == 0.0
    
    print("✓ Skill complementarity tests passed\n")


def test_skill_gap_creation():
    """Test SkillGap object creation and validation."""
    print("Testing SkillGap creation...")
    
    gap = SkillGap(
        skill_category="business",
        skill_name="strategy",
        importance_score=0.8,
        gap_severity=0.6
    )
    
    assert gap.skill_category == "business"
    assert gap.skill_name == "strategy"
    assert gap.importance_score == 0.8
    assert gap.gap_severity == 0.6
    
    print("✓ SkillGap creation tests passed\n")


def test_interest_profile_creation():
    """Test InterestProfile object creation."""
    print("Testing InterestProfile creation...")
    
    profile = InterestProfile(
        ai_solution_preferences={"nlp": 0.8, "ml": 0.9},
        industry_preferences={"healthcare": 0.7},
        complexity_preference="medium",
        market_size_preference="large",
        activity_patterns={"total_interactions": 50},
        engagement_level=0.8
    )
    
    assert len(profile.ai_solution_preferences) == 2
    assert profile.ai_solution_preferences["nlp"] == 0.8
    assert profile.complexity_preference == "medium"
    assert profile.engagement_level == 0.8
    
    print("✓ InterestProfile creation tests passed\n")


async def main():
    """Run all unit tests."""
    print("Starting User Matching Unit Tests")
    print("=" * 50)
    
    try:
        test_cosine_similarity()
        await test_interest_similarity()
        test_skill_overlap()
        await test_skill_complementarity()
        test_skill_gap_creation()
        test_interest_profile_creation()
        
        print("=" * 50)
        print("✅ All unit tests passed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())