"""Tests for user matching API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from api.main import app
from shared.models.user import User, UserRole
from shared.services.user_matching_service import UserMatch, MatchingType
from tests.conftest import create_test_user, get_auth_headers


class TestUserMatchingAPI:
    """Test cases for user matching API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    async def test_user(self, db_session: AsyncSession):
        """Create test user."""
        return await create_test_user(
            db_session,
            email="matching_test@test.com",
            username="matching_test",
            expertise_domains=["machine_learning", "nlp"],
            role=UserRole.EXPERT
        )
    
    @pytest.fixture
    def mock_user_match(self):
        """Create mock UserMatch object."""
        return UserMatch(
            user_id="test-user-id",
            username="test_user",
            full_name="Test User",
            avatar_url=None,
            match_score=0.85,
            match_type=MatchingType.INTEREST_BASED,
            match_reasons=["Shared interest in machine learning", "Similar complexity preference"],
            common_interests=["machine_learning", "nlp"],
            complementary_skills=[],
            expertise_domains=["machine_learning", "data_science"],
            reputation_score=7.5,
            compatibility_factors={
                "ai_similarity": 0.8,
                "industry_similarity": 0.7,
                "engagement_compatibility": 0.1
            }
        )
    
    @patch('shared.services.user_matching_service.user_matching_service.find_interest_based_matches')
    async def test_find_interest_based_matches_success(
        self,
        mock_find_matches,
        client: TestClient,
        test_user: User,
        mock_user_match: UserMatch
    ):
        """Test successful interest-based matching."""
        # Mock the service method
        mock_find_matches.return_value = [mock_user_match]
        
        # Make request
        headers = get_auth_headers(test_user.id)
        response = client.get(
            "/api/v1/user-matching/interest-based?limit=10&min_match_score=0.3",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "matches" in data
        assert "total_count" in data
        assert "algorithm_used" in data
        assert "user_id" in data
        
        assert len(data["matches"]) == 1
        assert data["total_count"] == 1
        assert data["algorithm_used"] == "interest_based"
        assert data["user_id"] == test_user.id
        
        # Verify match data
        match = data["matches"][0]
        assert match["user_id"] == mock_user_match.user_id
        assert match["username"] == mock_user_match.username
        assert match["match_score"] == mock_user_match.match_score
        assert match["match_type"] == mock_user_match.match_type.value
        assert match["common_interests"] == mock_user_match.common_interests
    
    @patch('shared.services.user_matching_service.user_matching_service.find_complementary_skill_matches')
    async def test_find_skill_complementary_matches_success(
        self,
        mock_find_matches,
        client: TestClient,
        test_user: User,
        mock_user_match: UserMatch
    ):
        """Test successful skill-complementary matching."""
        # Update mock for skill matching
        mock_user_match.match_type = MatchingType.SKILL_COMPLEMENTARY
        mock_user_match.complementary_skills = ["business_strategy", "marketing"]
        mock_find_matches.return_value = [mock_user_match]
        
        headers = get_auth_headers(test_user.id)
        response = client.get(
            "/api/v1/user-matching/skill-complementary?opportunity_id=test-opp-id&limit=10",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["matches"]) == 1
        assert data["algorithm_used"] == "skill_complementary"
        
        match = data["matches"][0]
        assert match["match_type"] == "skill_complementary"
        assert len(match["complementary_skills"]) == 2
    
    @patch('shared.services.user_matching_service.user_matching_service.find_hybrid_matches')
    async def test_find_hybrid_matches_success(
        self,
        mock_find_matches,
        client: TestClient,
        test_user: User,
        mock_user_match: UserMatch
    ):
        """Test successful hybrid matching."""
        mock_find_matches.return_value = [mock_user_match]
        
        headers = get_auth_headers(test_user.id)
        response = client.get(
            "/api/v1/user-matching/hybrid?opportunity_id=test-opp-id&limit=15",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["matches"]) == 1
        assert data["algorithm_used"] == "hybrid"
    
    async def test_find_matches_without_auth(self, client: TestClient):
        """Test that matching endpoints require authentication."""
        response = client.get("/api/v1/user-matching/interest-based")
        assert response.status_code == 401
    
    @patch('shared.services.user_matching_service.user_matching_service.find_interest_based_matches')
    async def test_find_matches_with_custom_request(
        self,
        mock_find_matches,
        client: TestClient,
        test_user: User,
        mock_user_match: UserMatch
    ):
        """Test finding matches with custom request parameters."""
        mock_find_matches.return_value = [mock_user_match]
        
        headers = get_auth_headers(test_user.id)
        request_data = {
            "user_id": test_user.id,
            "match_type": "interest_based",
            "limit": 5,
            "min_match_score": 0.5,
            "include_reasons": True
        }
        
        response = client.post(
            "/api/v1/user-matching/find",
            json=request_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["matches"]) == 1
        assert data["algorithm_used"] == "interest_based"
        
        # Verify match reasons are included
        match = data["matches"][0]
        assert len(match["match_reasons"]) > 0
    
    async def test_find_matches_for_other_user_forbidden(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test that users cannot request matches for other users."""
        headers = get_auth_headers(test_user.id)
        request_data = {
            "user_id": "other-user-id",  # Different user ID
            "match_type": "interest_based",
            "limit": 10
        }
        
        response = client.post(
            "/api/v1/user-matching/find",
            json=request_data,
            headers=headers
        )
        
        assert response.status_code == 403
        assert "Can only request matches for yourself" in response.json()["detail"]
    
    @patch('shared.services.user_matching_service.user_matching_service._extract_user_skills')
    @patch('shared.services.user_matching_service.user_matching_service._identify_skill_gaps')
    async def test_analyze_user_skills_success(
        self,
        mock_identify_gaps,
        mock_extract_skills,
        client: TestClient,
        test_user: User
    ):
        """Test successful skill analysis."""
        # Mock service methods
        mock_extract_skills.return_value = {
            "ai_machine_learning": 0.9,
            "ai_nlp": 0.8,
            "expertise_machine_learning": 1.0
        }
        
        mock_skill_gap = type('SkillGap', (), {
            'skill_category': 'business',
            'skill_name': 'strategy',
            'importance_score': 0.8,
            'gap_severity': 0.6
        })()
        
        mock_identify_gaps.return_value = [mock_skill_gap]
        
        headers = get_auth_headers(test_user.id)
        response = client.get(
            "/api/v1/user-matching/skill-analysis?opportunity_id=test-opp-id&include_gaps=true",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "user_id" in data
        assert "current_skills" in data
        assert "skill_gaps" in data
        assert "skill_recommendations" in data
        assert "complementary_skill_needs" in data
        assert "skill_categories" in data
        
        assert data["user_id"] == test_user.id
        assert len(data["current_skills"]) == 3
        assert len(data["skill_gaps"]) == 1
        assert data["skill_gaps"][0]["skill_category"] == "business"
        assert data["skill_gaps"][0]["skill_name"] == "strategy"
    
    async def test_submit_match_feedback_success(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test successful match feedback submission."""
        headers = get_auth_headers(test_user.id)
        feedback_data = {
            "match_id": "test-match-id",
            "matched_user_id": "matched-user-id",
            "feedback_score": 4,
            "feedback_text": "Great potential collaborator",
            "match_quality_rating": 4,
            "would_collaborate": True,
            "feedback_categories": ["skills", "communication"]
        }
        
        response = client.post(
            "/api/v1/user-matching/feedback",
            json=feedback_data,
            headers=headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Feedback submitted successfully"
    
    async def test_get_matching_analytics_admin_only(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test that analytics endpoint is restricted to admins."""
        # Test with regular user (should be forbidden)
        headers = get_auth_headers(test_user.id)
        response = client.get("/api/v1/user-matching/analytics", headers=headers)
        assert response.status_code == 403
    
    @patch('shared.services.user_matching_service.user_matching_service.find_interest_based_matches')
    async def test_find_matches_service_error(
        self,
        mock_find_matches,
        client: TestClient,
        test_user: User
    ):
        """Test handling of service errors."""
        # Mock service to raise exception
        mock_find_matches.side_effect = Exception("Service error")
        
        headers = get_auth_headers(test_user.id)
        response = client.get(
            "/api/v1/user-matching/interest-based",
            headers=headers
        )
        
        assert response.status_code == 500
        assert "Failed to find interest-based matches" in response.json()["detail"]
    
    async def test_invalid_match_type_in_request(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test handling of invalid match type."""
        headers = get_auth_headers(test_user.id)
        request_data = {
            "user_id": test_user.id,
            "match_type": "invalid_type",
            "limit": 10
        }
        
        response = client.post(
            "/api/v1/user-matching/find",
            json=request_data,
            headers=headers
        )
        
        assert response.status_code == 422  # Validation error
    
    async def test_parameter_validation(self, client: TestClient, test_user: User):
        """Test parameter validation for matching endpoints."""
        headers = get_auth_headers(test_user.id)
        
        # Test invalid limit (too high)
        response = client.get(
            "/api/v1/user-matching/interest-based?limit=200",
            headers=headers
        )
        assert response.status_code == 422
        
        # Test invalid min_match_score (out of range)
        response = client.get(
            "/api/v1/user-matching/interest-based?min_match_score=1.5",
            headers=headers
        )
        assert response.status_code == 422
        
        # Test invalid limit (too low)
        response = client.get(
            "/api/v1/user-matching/interest-based?limit=0",
            headers=headers
        )
        assert response.status_code == 422
    
    @patch('shared.services.user_matching_service.user_matching_service.find_interest_based_matches')
    async def test_empty_matches_response(
        self,
        mock_find_matches,
        client: TestClient,
        test_user: User
    ):
        """Test response when no matches are found."""
        mock_find_matches.return_value = []
        
        headers = get_auth_headers(test_user.id)
        response = client.get(
            "/api/v1/user-matching/interest-based",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["matches"] == []
        assert data["total_count"] == 0
        assert data["algorithm_used"] == "interest_based"
        assert data["user_id"] == test_user.id
    
    async def test_feedback_validation(self, client: TestClient, test_user: User):
        """Test validation of feedback data."""
        headers = get_auth_headers(test_user.id)
        
        # Test missing required fields
        incomplete_feedback = {
            "match_id": "test-match-id",
            # Missing matched_user_id, feedback_score, etc.
        }
        
        response = client.post(
            "/api/v1/user-matching/feedback",
            json=incomplete_feedback,
            headers=headers
        )
        assert response.status_code == 422
        
        # Test invalid feedback score
        invalid_feedback = {
            "match_id": "test-match-id",
            "matched_user_id": "matched-user-id",
            "feedback_score": 10,  # Out of range (1-5)
            "match_quality_rating": 3,
            "would_collaborate": True
        }
        
        response = client.post(
            "/api/v1/user-matching/feedback",
            json=invalid_feedback,
            headers=headers
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestUserMatchingAPIIntegration:
    """Integration tests for user matching API."""
    
    async def test_complete_matching_workflow(self, db_session: AsyncSession):
        """Test complete workflow from API perspective."""
        client = TestClient(app)
        
        # Create test user
        test_user = await create_test_user(
            db_session,
            email="integration_test@test.com",
            username="integration_test",
            expertise_domains=["machine_learning"],
            role=UserRole.EXPERT
        )
        
        headers = get_auth_headers(test_user.id)
        
        # Test skill analysis first
        with patch('shared.services.user_matching_service.user_matching_service._extract_user_skills') as mock_skills:
            with patch('shared.services.user_matching_service.user_matching_service._identify_skill_gaps') as mock_gaps:
                mock_skills.return_value = {"ai_machine_learning": 0.9}
                mock_gaps.return_value = []
                
                response = client.get(
                    "/api/v1/user-matching/skill-analysis",
                    headers=headers
                )
                assert response.status_code == 200
        
        # Test finding matches
        with patch('shared.services.user_matching_service.user_matching_service.find_interest_based_matches') as mock_matches:
            mock_match = UserMatch(
                user_id="other-user",
                username="other_user",
                full_name="Other User",
                avatar_url=None,
                match_score=0.8,
                match_type=MatchingType.INTEREST_BASED,
                match_reasons=["Similar interests"],
                common_interests=["machine_learning"],
                complementary_skills=[],
                expertise_domains=["machine_learning"],
                reputation_score=5.0,
                compatibility_factors={}
            )
            mock_matches.return_value = [mock_match]
            
            response = client.get(
                "/api/v1/user-matching/interest-based",
                headers=headers
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["matches"]) == 1
        
        # Test submitting feedback
        feedback_data = {
            "match_id": "test-match",
            "matched_user_id": "other-user",
            "feedback_score": 4,
            "match_quality_rating": 4,
            "would_collaborate": True
        }
        
        response = client.post(
            "/api/v1/user-matching/feedback",
            json=feedback_data,
            headers=headers
        )
        assert response.status_code == 201