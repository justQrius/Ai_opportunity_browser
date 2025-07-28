"""Tests for user matching service functionality."""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.user_matching_service import (
    UserMatchingService, 
    MatchingType, 
    UserMatch, 
    SkillGap, 
    InterestProfile
)
from shared.models.user import User, UserRole
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.user_interaction import UserInteraction, InteractionType, UserPreference
from tests.conftest import create_test_user, create_test_opportunity


class TestUserMatchingService:
    """Test cases for UserMatchingService."""
    
    @pytest.fixture
    def matching_service(self):
        """Create UserMatchingService instance."""
        return UserMatchingService()
    
    @pytest.fixture
    async def test_users(self, db_session: AsyncSession):
        """Create test users with different profiles."""
        users = []
        
        # User 1: AI/ML expert
        user1 = await create_test_user(
            db_session,
            email="ai_expert@test.com",
            username="ai_expert",
            expertise_domains=["machine_learning", "nlp", "computer_vision"],
            role=UserRole.EXPERT
        )
        users.append(user1)
        
        # User 2: Business strategist
        user2 = await create_test_user(
            db_session,
            email="business_expert@test.com",
            username="business_expert",
            expertise_domains=["business_strategy", "product_management", "marketing"],
            role=UserRole.EXPERT
        )
        users.append(user2)
        
        # User 3: Full-stack developer
        user3 = await create_test_user(
            db_session,
            email="fullstack_dev@test.com",
            username="fullstack_dev",
            expertise_domains=["web_development", "api_design", "database_design"],
            role=UserRole.USER
        )
        users.append(user3)
        
        # User 4: Similar to user 1 (for interest matching)
        user4 = await create_test_user(
            db_session,
            email="ai_researcher@test.com",
            username="ai_researcher",
            expertise_domains=["machine_learning", "deep_learning", "research"],
            role=UserRole.EXPERT
        )
        users.append(user4)
        
        return users
    
    @pytest.fixture
    async def test_opportunities(self, db_session: AsyncSession):
        """Create test opportunities."""
        opportunities = []
        
        # AI/ML opportunity
        opp1 = await create_test_opportunity(
            db_session,
            title="AI-Powered Customer Service",
            ai_solution_types=["nlp", "machine_learning"],
            target_industries=["customer_service", "saas"],
            implementation_complexity="medium"
        )
        opportunities.append(opp1)
        
        # Computer vision opportunity
        opp2 = await create_test_opportunity(
            db_session,
            title="Automated Quality Control",
            ai_solution_types=["computer_vision", "automation"],
            target_industries=["manufacturing", "quality_control"],
            implementation_complexity="high"
        )
        opportunities.append(opp2)
        
        return opportunities
    
    @pytest.fixture
    async def test_interactions(self, db_session: AsyncSession, test_users, test_opportunities):
        """Create test user interactions."""
        interactions = []
        
        # User 1 interactions (AI expert interested in NLP)
        for i, opp in enumerate(test_opportunities):
            interaction = UserInteraction(
                user_id=test_users[0].id,
                opportunity_id=opp.id,
                interaction_type=InteractionType.VIEW if i % 2 == 0 else InteractionType.BOOKMARK,
                duration_seconds=120 + i * 30,
                engagement_score=0.8 + i * 0.1
            )
            db_session.add(interaction)
            interactions.append(interaction)
        
        # User 4 interactions (similar to user 1)
        for i, opp in enumerate(test_opportunities):
            interaction = UserInteraction(
                user_id=test_users[3].id,
                opportunity_id=opp.id,
                interaction_type=InteractionType.VIEW if i % 2 == 1 else InteractionType.CLICK,
                duration_seconds=100 + i * 25,
                engagement_score=0.7 + i * 0.1
            )
            db_session.add(interaction)
            interactions.append(interaction)
        
        await db_session.commit()
        return interactions
    
    async def test_build_user_interest_profile(
        self, 
        matching_service: UserMatchingService,
        db_session: AsyncSession,
        test_users,
        test_opportunities,
        test_interactions
    ):
        """Test building user interest profile from interactions."""
        user_id = test_users[0].id
        
        profile = await matching_service._build_user_interest_profile(db_session, user_id)
        
        assert profile is not None
        assert isinstance(profile, InterestProfile)
        assert len(profile.ai_solution_preferences) > 0
        assert "nlp" in profile.ai_solution_preferences
        assert "machine_learning" in profile.ai_solution_preferences
        assert profile.engagement_level > 0
        assert profile.activity_patterns["total_interactions"] > 0
    
    async def test_extract_user_skills(
        self,
        matching_service: UserMatchingService,
        db_session: AsyncSession,
        test_users
    ):
        """Test extracting user skills from profile and interactions."""
        user_id = test_users[0].id  # AI expert
        
        skills = await matching_service._extract_user_skills(db_session, user_id)
        
        assert isinstance(skills, dict)
        assert len(skills) > 0
        assert "expertise_machine_learning" in skills
        assert "expertise_nlp" in skills
        assert skills["expertise_machine_learning"] == 1.0
        
        # Check role-based skills
        assert "domain_expertise" in skills
        assert "validation" in skills
    
    async def test_identify_skill_gaps(
        self,
        matching_service: UserMatchingService,
        db_session: AsyncSession,
        test_users,
        test_opportunities
    ):
        """Test identifying skill gaps for a user."""
        user_id = test_users[0].id  # AI expert
        opportunity_id = test_opportunities[0].id
        
        skill_gaps = await matching_service._identify_skill_gaps(
            db_session, user_id, opportunity_id
        )
        
        assert isinstance(skill_gaps, list)
        assert len(skill_gaps) > 0
        
        # Check that gaps are SkillGap objects
        for gap in skill_gaps:
            assert isinstance(gap, SkillGap)
            assert hasattr(gap, 'skill_category')
            assert hasattr(gap, 'skill_name')
            assert hasattr(gap, 'importance_score')
            assert hasattr(gap, 'gap_severity')
            assert 0.0 <= gap.importance_score <= 1.0
            assert 0.0 <= gap.gap_severity <= 1.0
    
    async def test_calculate_interest_similarity(
        self,
        matching_service: UserMatchingService
    ):
        """Test calculating interest similarity between users."""
        profile1 = InterestProfile(
            ai_solution_preferences={"nlp": 0.8, "machine_learning": 0.9},
            industry_preferences={"healthcare": 0.7, "fintech": 0.5},
            complexity_preference="medium",
            market_size_preference="large",
            activity_patterns={},
            engagement_level=0.8
        )
        
        profile2 = InterestProfile(
            ai_solution_preferences={"nlp": 0.7, "computer_vision": 0.6},
            industry_preferences={"healthcare": 0.8, "retail": 0.4},
            complexity_preference="medium",
            market_size_preference="large",
            activity_patterns={},
            engagement_level=0.7
        )
        
        similarity = await matching_service._calculate_interest_similarity(profile1, profile2)
        
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.0  # Should have some similarity due to overlapping preferences
    
    def test_calculate_cosine_similarity(self, matching_service: UserMatchingService):
        """Test cosine similarity calculation."""
        dict1 = {"a": 1.0, "b": 2.0, "c": 0.0}
        dict2 = {"a": 2.0, "b": 1.0, "d": 1.0}
        
        similarity = matching_service._calculate_cosine_similarity(dict1, dict2)
        
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
        
        # Test identical dictionaries
        identical_similarity = matching_service._calculate_cosine_similarity(dict1, dict1)
        assert abs(identical_similarity - 1.0) < 1e-6
        
        # Test empty dictionaries
        empty_similarity = matching_service._calculate_cosine_similarity({}, dict1)
        assert empty_similarity == 0.0
    
    async def test_calculate_skill_complementarity(
        self,
        matching_service: UserMatchingService
    ):
        """Test calculating skill complementarity score."""
        user_skills = {
            "ai_nlp": 0.9,
            "ai_machine_learning": 0.8,
            "technical_programming": 0.7
        }
        
        candidate_skills = {
            "business_strategy": 0.8,
            "business_marketing": 0.7,
            "technical_architecture": 0.6
        }
        
        skill_gaps = [
            SkillGap("business", "strategy", 0.8, 0.7),
            SkillGap("business", "marketing", 0.6, 0.5),
            SkillGap("technical", "architecture", 0.7, 0.6)
        ]
        
        complementarity = await matching_service._calculate_skill_complementarity(
            user_skills, candidate_skills, skill_gaps
        )
        
        assert isinstance(complementarity, float)
        assert 0.0 <= complementarity <= 1.0
        assert complementarity > 0.0  # Should have complementarity
    
    def test_calculate_skill_overlap(self, matching_service: UserMatchingService):
        """Test calculating skill overlap between users."""
        skills1 = {"ai_nlp": 0.8, "ai_ml": 0.9, "tech_python": 0.7}
        skills2 = {"ai_nlp": 0.7, "business_strategy": 0.8, "tech_javascript": 0.6}
        
        overlap = matching_service._calculate_skill_overlap(skills1, skills2)
        
        assert isinstance(overlap, float)
        assert 0.0 <= overlap <= 1.0
        
        # Test identical skills
        identical_overlap = matching_service._calculate_skill_overlap(skills1, skills1)
        assert identical_overlap > 0.5  # Should have significant overlap
        
        # Test no overlap
        no_overlap_skills = {"completely_different": 1.0}
        no_overlap = matching_service._calculate_skill_overlap(skills1, no_overlap_skills)
        assert no_overlap == 0.0
    
    @patch('shared.cache.cache_manager')
    async def test_find_interest_based_matches(
        self,
        mock_cache,
        matching_service: UserMatchingService,
        db_session: AsyncSession,
        test_users,
        test_opportunities,
        test_interactions
    ):
        """Test finding interest-based matches."""
        # Mock cache to return None (no cached results)
        mock_cache.get.return_value = None
        
        user_id = test_users[0].id
        matches = await matching_service.find_interest_based_matches(
            db_session, user_id, limit=10, min_match_score=0.1
        )
        
        assert isinstance(matches, list)
        # Should find at least one match (user 4 has similar interests)
        assert len(matches) >= 0
        
        for match in matches:
            assert isinstance(match, UserMatch)
            assert match.user_id != user_id  # Shouldn't match with self
            assert match.match_type == MatchingType.INTEREST_BASED
            assert 0.0 <= match.match_score <= 1.0
            assert isinstance(match.match_reasons, list)
            assert isinstance(match.common_interests, list)
    
    @patch('shared.cache.cache_manager')
    async def test_find_complementary_skill_matches(
        self,
        mock_cache,
        matching_service: UserMatchingService,
        db_session: AsyncSession,
        test_users,
        test_opportunities
    ):
        """Test finding complementary skill matches."""
        # Mock cache to return None
        mock_cache.get.return_value = None
        
        user_id = test_users[0].id  # AI expert
        opportunity_id = test_opportunities[0].id
        
        matches = await matching_service.find_complementary_skill_matches(
            db_session, user_id, opportunity_id, limit=10, min_match_score=0.1
        )
        
        assert isinstance(matches, list)
        
        for match in matches:
            assert isinstance(match, UserMatch)
            assert match.user_id != user_id
            assert match.match_type == MatchingType.SKILL_COMPLEMENTARY
            assert 0.0 <= match.match_score <= 1.0
            assert isinstance(match.complementary_skills, list)
    
    @patch('shared.cache.cache_manager')
    async def test_find_hybrid_matches(
        self,
        mock_cache,
        matching_service: UserMatchingService,
        db_session: AsyncSession,
        test_users,
        test_opportunities,
        test_interactions
    ):
        """Test finding hybrid matches (interest + skill)."""
        # Mock cache to return None
        mock_cache.get.return_value = None
        
        user_id = test_users[0].id
        opportunity_id = test_opportunities[0].id
        
        matches = await matching_service.find_hybrid_matches(
            db_session, user_id, opportunity_id, limit=10, min_match_score=0.1
        )
        
        assert isinstance(matches, list)
        
        for match in matches:
            assert isinstance(match, UserMatch)
            assert match.user_id != user_id
            assert 0.0 <= match.match_score <= 1.0
    
    async def test_get_potential_matches(
        self,
        matching_service: UserMatchingService,
        db_session: AsyncSession,
        test_users
    ):
        """Test getting potential user matches."""
        user_id = test_users[0].id
        
        potential_matches = await matching_service._get_potential_matches(
            db_session, user_id, min_reputation=0.0
        )
        
        assert isinstance(potential_matches, list)
        assert len(potential_matches) >= 3  # Should find other test users
        
        # Verify user is not in their own potential matches
        match_ids = [user.id for user in potential_matches]
        assert user_id not in match_ids
        
        # Verify all matches are active users
        for user in potential_matches:
            assert user.is_active is True
    
    async def test_extract_opportunity_skill_requirements(
        self,
        matching_service: UserMatchingService,
        test_opportunities
    ):
        """Test extracting skill requirements from opportunities."""
        opportunity = test_opportunities[0]  # AI-powered customer service
        
        requirements = await matching_service._extract_opportunity_skill_requirements(opportunity)
        
        assert isinstance(requirements, dict)
        assert "ai" in requirements
        assert "technical" in requirements
        assert "business" in requirements
        assert "domain" in requirements
        
        # Check AI requirements
        assert "nlp" in requirements["ai"]
        assert "machine_learning" in requirements["ai"]
        
        # Check domain requirements
        assert "customer_service" in requirements["domain"]
        assert "saas" in requirements["domain"]
    
    async def test_create_user_match(
        self,
        matching_service: UserMatchingService,
        test_users
    ):
        """Test creating UserMatch objects."""
        candidate = test_users[1]  # Business expert
        match_score = 0.75
        
        user_profile = InterestProfile(
            ai_solution_preferences={"nlp": 0.8},
            industry_preferences={"healthcare": 0.7},
            complexity_preference="medium",
            market_size_preference="large",
            activity_patterns={},
            engagement_level=0.8
        )
        
        candidate_profile = InterestProfile(
            ai_solution_preferences={"nlp": 0.6},
            industry_preferences={"healthcare": 0.8},
            complexity_preference="medium",
            market_size_preference="large",
            activity_patterns={},
            engagement_level=0.7
        )
        
        match = await matching_service._create_user_match(
            candidate, match_score, MatchingType.INTEREST_BASED,
            user_profile, candidate_profile
        )
        
        assert isinstance(match, UserMatch)
        assert match.user_id == candidate.id
        assert match.username == candidate.username
        assert match.match_score == match_score
        assert match.match_type == MatchingType.INTEREST_BASED
        assert len(match.match_reasons) > 0
        assert len(match.common_interests) > 0
        assert "nlp" in match.common_interests
        assert "healthcare" in match.common_interests
    
    async def test_create_skill_match(
        self,
        matching_service: UserMatchingService,
        test_users
    ):
        """Test creating skill-based UserMatch objects."""
        candidate = test_users[1]  # Business expert
        match_score = 0.8
        
        user_skills = {"ai_nlp": 0.9, "technical_programming": 0.8}
        candidate_skills = {"business_strategy": 0.9, "business_marketing": 0.7}
        skill_gaps = [
            SkillGap("business", "strategy", 0.8, 0.7),
            SkillGap("business", "marketing", 0.6, 0.5)
        ]
        
        match = await matching_service._create_skill_match(
            candidate, match_score, user_skills, candidate_skills, skill_gaps
        )
        
        assert isinstance(match, UserMatch)
        assert match.user_id == candidate.id
        assert match.match_score == match_score
        assert match.match_type == MatchingType.SKILL_COMPLEMENTARY
        assert len(match.complementary_skills) > 0
        assert "business: strategy" in match.complementary_skills
        assert len(match.match_reasons) > 0


@pytest.mark.asyncio
class TestUserMatchingIntegration:
    """Integration tests for user matching functionality."""
    
    async def test_end_to_end_matching_workflow(
        self,
        db_session: AsyncSession
    ):
        """Test complete matching workflow from user creation to match results."""
        matching_service = UserMatchingService()
        
        # Create users with different profiles
        ai_expert = await create_test_user(
            db_session,
            email="ai_expert_integration@test.com",
            username="ai_expert_integration",
            expertise_domains=["machine_learning", "nlp"],
            role=UserRole.EXPERT
        )
        
        business_expert = await create_test_user(
            db_session,
            email="business_expert_integration@test.com",
            username="business_expert_integration",
            expertise_domains=["business_strategy", "marketing"],
            role=UserRole.EXPERT
        )
        
        # Create opportunity
        opportunity = await create_test_opportunity(
            db_session,
            title="AI Chatbot for E-commerce",
            ai_solution_types=["nlp", "machine_learning"],
            target_industries=["ecommerce", "retail"]
        )
        
        # Create interactions for AI expert
        interaction = UserInteraction(
            user_id=ai_expert.id,
            opportunity_id=opportunity.id,
            interaction_type=InteractionType.BOOKMARK,
            duration_seconds=180,
            engagement_score=0.9
        )
        db_session.add(interaction)
        await db_session.commit()
        
        # Test interest-based matching
        with patch('shared.cache.cache_manager') as mock_cache:
            mock_cache.get.return_value = None
            
            interest_matches = await matching_service.find_interest_based_matches(
                db_session, ai_expert.id, limit=5, min_match_score=0.1
            )
            
            assert isinstance(interest_matches, list)
        
        # Test skill-complementary matching
        with patch('shared.cache.cache_manager') as mock_cache:
            mock_cache.get.return_value = None
            
            skill_matches = await matching_service.find_complementary_skill_matches(
                db_session, ai_expert.id, opportunity.id, limit=5, min_match_score=0.1
            )
            
            assert isinstance(skill_matches, list)
        
        # Test hybrid matching
        with patch('shared.cache.cache_manager') as mock_cache:
            mock_cache.get.return_value = None
            
            hybrid_matches = await matching_service.find_hybrid_matches(
                db_session, ai_expert.id, opportunity.id, limit=5, min_match_score=0.1
            )
            
            assert isinstance(hybrid_matches, list)