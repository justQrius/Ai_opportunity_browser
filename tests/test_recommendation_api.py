"""
Test suite for the Recommendation API endpoints.

This module tests the recommendation API endpoints to ensure they work correctly
and support the requirements for personalized recommendations and user preference learning.

Supports Requirements 6.1.3 (Personalized recommendation engine and user preference learning).
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import json
from datetime import datetime

from api.main import app
from shared.models.user import User, UserRole
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.user_interaction import UserInteraction, UserPreference, InteractionType


class TestRecommendationAPI:
    """Test the recommendation API endpoints."""
    
    def setup_method(self):
        """Set up test client and mock data."""
        self.client = TestClient(app)
        self.test_user_id = "test-user-123"
        self.test_opportunity_id = "test-opp-123"
        
        # Mock user for authentication
        self.mock_user = User(
            id=self.test_user_id,
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            role=UserRole.USER,
            hashed_password="test_hash"
        )
        
        # Mock opportunity
        self.mock_opportunity = Opportunity(
            id=self.test_opportunity_id,
            title="Test AI Opportunity",
            description="A test opportunity for AI development",
            status=OpportunityStatus.VALIDATED,
            validation_score=8.5,
            confidence_rating=0.8,
            ai_feasibility_score=7.5,
            discovery_method="test_agent"
        )
    
    @patch('api.core.dependencies.get_current_user')
    @patch('shared.services.recommendation_service.recommendation_service.get_personalized_recommendations')
    def test_get_personalized_recommendations(self, mock_get_recommendations, mock_get_user):
        """Test the personalized recommendations endpoint."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_get_recommendations.return_value = [self.mock_opportunity]
        
        # Test request
        request_data = {
            "user_id": self.test_user_id,
            "limit": 5,
            "include_viewed": False,
            "ai_solution_types": ["ml", "nlp"],
            "industries": ["healthcare"]
        }
        
        response = self.client.post("/api/v1/recommendations/", json=request_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "pagination" in data
        assert "total_count" in data
        assert "metadata" in data
        
        assert data["metadata"]["recommendation_algorithm"] == "hybrid"
        assert data["metadata"]["includes_preference_learning"] == True
        assert data["metadata"]["personalization_enabled"] == True
        
        # Verify service was called correctly
        mock_get_recommendations.assert_called_once()
        call_args = mock_get_recommendations.call_args[0]
        request_obj = call_args[1]
        assert request_obj.user_id == self.test_user_id
        assert request_obj.limit == 5
        assert request_obj.ai_solution_types == ["ml", "nlp"]
    
    @patch('api.core.dependencies.get_current_user')
    def test_get_recommendations_unauthorized_user(self, mock_get_user):
        """Test that users can only get their own recommendations."""
        mock_get_user.return_value = self.mock_user
        
        # Try to get recommendations for another user
        request_data = {
            "user_id": "other-user-123",
            "limit": 5
        }
        
        response = self.client.post("/api/v1/recommendations/", json=request_data)
        
        assert response.status_code == 403
        assert "You can only get your own recommendations" in response.json()["detail"]
    
    @patch('api.core.dependencies.get_current_user')
    @patch('shared.services.recommendation_service.recommendation_service.record_recommendation_feedback')
    def test_record_recommendation_feedback(self, mock_record_feedback, mock_get_user):
        """Test recording recommendation feedback."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_feedback = MagicMock()
        mock_feedback.id = "feedback-123"
        mock_feedback.opportunity_id = self.test_opportunity_id
        mock_feedback.is_relevant = True
        mock_feedback.feedback_score = 5
        mock_feedback.created_at = datetime.utcnow()
        mock_record_feedback.return_value = mock_feedback
        
        # Test request
        feedback_data = {
            "opportunity_id": self.test_opportunity_id,
            "is_relevant": True,
            "feedback_score": 5,
            "feedback_text": "Very relevant recommendation",
            "recommendation_algorithm": "hybrid",
            "recommendation_score": 0.85,
            "recommendation_rank": 1
        }
        
        response = self.client.post("/api/v1/recommendations/feedback", json=feedback_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["message"] == "Recommendation feedback recorded successfully"
        assert data["data"]["feedback_id"] == "feedback-123"
        assert data["data"]["is_relevant"] == True
        assert data["data"]["feedback_score"] == 5
        
        # Verify service was called correctly
        mock_record_feedback.assert_called_once()
    
    @patch('api.core.dependencies.get_current_user')
    def test_record_feedback_missing_fields(self, mock_get_user):
        """Test feedback recording with missing required fields."""
        mock_get_user.return_value = self.mock_user
        
        # Missing required fields
        feedback_data = {
            "opportunity_id": self.test_opportunity_id,
            "is_relevant": True
            # Missing recommendation_algorithm, recommendation_score, recommendation_rank
        }
        
        response = self.client.post("/api/v1/recommendations/feedback", json=feedback_data)
        
        assert response.status_code == 400
        assert "Missing required field" in response.json()["detail"]
    
    @patch('api.core.dependencies.get_current_user')
    @patch('shared.services.recommendation_service.recommendation_service.explain_recommendation')
    def test_explain_recommendation(self, mock_explain, mock_get_user):
        """Test recommendation explanation endpoint."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_explanation = {
            "opportunity_id": self.test_opportunity_id,
            "overall_score": 0.85,
            "confidence": 0.8,
            "recommendation_factors": [
                {"factor": "content_similarity", "score": 0.9, "description": "High content match"},
                {"factor": "user_preferences", "score": 0.8, "description": "Matches user interests"}
            ]
        }
        mock_explain.return_value = mock_explanation
        
        response = self.client.get(f"/api/v1/recommendations/explain/{self.test_opportunity_id}")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["opportunity_id"] == self.test_opportunity_id
        assert data["user_id"] == self.test_user_id
        assert "explanation" in data
        assert data["explanation"]["overall_score"] == 0.85
        assert len(data["explanation"]["recommendation_factors"]) == 2
        
        # Verify service was called correctly
        mock_explain.assert_called_once_with(mock.ANY, self.test_user_id, self.test_opportunity_id)
    
    @patch('api.core.dependencies.get_current_user')
    @patch('shared.services.recommendation_service.recommendation_service.record_interaction')
    def test_record_user_interaction(self, mock_record_interaction, mock_get_user):
        """Test recording user interactions."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_interaction = MagicMock()
        mock_interaction.id = "interaction-123"
        mock_interaction.interaction_type = InteractionType.VIEW
        mock_interaction.engagement_score = 2.5
        mock_interaction.opportunity_id = self.test_opportunity_id
        mock_interaction.created_at = datetime.utcnow()
        mock_record_interaction.return_value = mock_interaction
        
        # Test request
        interaction_data = {
            "interaction_type": "view",
            "opportunity_id": self.test_opportunity_id,
            "duration_seconds": 120,
            "referrer_source": "search_results"
        }
        
        response = self.client.post("/api/v1/recommendations/interactions", json=interaction_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["message"] == "User interaction recorded successfully"
        assert data["data"]["interaction_id"] == "interaction-123"
        assert data["data"]["interaction_type"] == "view"
        assert data["data"]["engagement_score"] == 2.5
        
        # Verify service was called correctly
        mock_record_interaction.assert_called_once()
    
    @patch('api.core.dependencies.get_current_user')
    def test_record_interaction_invalid_type(self, mock_get_user):
        """Test recording interaction with invalid type."""
        mock_get_user.return_value = self.mock_user
        
        interaction_data = {
            "interaction_type": "invalid_type",
            "opportunity_id": self.test_opportunity_id
        }
        
        response = self.client.post("/api/v1/recommendations/interactions", json=interaction_data)
        
        assert response.status_code == 400
        assert "Invalid interaction_type" in response.json()["detail"]
    
    @patch('api.core.dependencies.get_current_user')
    @patch('shared.services.recommendation_service.recommendation_service.get_or_create_user_preferences')
    def test_get_user_preferences(self, mock_get_preferences, mock_get_user):
        """Test getting user preferences."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_preferences = UserPreference(
            user_id=self.test_user_id,
            preferred_ai_types='{"ml": 0.8, "nlp": 0.6}',
            preferred_industries='{"healthcare": 0.9, "fintech": 0.5}',
            preferred_complexity="medium",
            min_validation_score=7.0,
            prefers_trending=True,
            prefers_new_opportunities=True,
            confidence_score=0.75,
            interaction_count=25,
            last_updated=datetime.utcnow()
        )
        mock_get_preferences.return_value = mock_preferences
        
        response = self.client.get("/api/v1/recommendations/preferences")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_id"] == self.test_user_id
        assert "preferences" in data
        assert "learning_metadata" in data
        
        preferences = data["preferences"]
        assert preferences["preferred_ai_types"]["ml"] == 0.8
        assert preferences["preferred_industries"]["healthcare"] == 0.9
        assert preferences["preferred_complexity"] == "medium"
        assert preferences["min_validation_score"] == 7.0
        
        learning_metadata = data["learning_metadata"]
        assert learning_metadata["confidence_score"] == 0.75
        assert learning_metadata["interaction_count"] == 25
    
    @patch('api.core.dependencies.get_current_user')
    @patch('shared.services.recommendation_service.recommendation_service.update_user_preferences_from_interactions')
    def test_update_user_preferences(self, mock_update_preferences, mock_get_user):
        """Test updating user preferences from interactions."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_updated_preferences = UserPreference(
            user_id=self.test_user_id,
            confidence_score=0.85,
            interaction_count=30,
            last_updated=datetime.utcnow()
        )
        mock_update_preferences.return_value = mock_updated_preferences
        
        response = self.client.post("/api/v1/recommendations/preferences/update")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["message"] == "User preferences updated successfully"
        assert data["data"]["confidence_score"] == 0.85
        assert data["data"]["interaction_count"] == 30
        
        # Verify service was called correctly
        mock_update_preferences.assert_called_once_with(mock.ANY, self.test_user_id)
    
    @patch('api.core.dependencies.get_current_user')
    @patch('shared.database.get_db')
    def test_get_recommendation_stats(self, mock_get_db, mock_get_user):
        """Test getting recommendation statistics."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock database query results
        mock_interaction_result = MagicMock()
        mock_interaction_result.interaction_type = InteractionType.VIEW
        mock_interaction_result.count = 15
        mock_interaction_result.avg_engagement = 2.5
        
        mock_feedback_result = MagicMock()
        mock_feedback_result.total_feedback = 10
        mock_feedback_result.relevant_count = 8
        mock_feedback_result.avg_score = 4.2
        
        mock_db.execute.return_value.first.return_value = mock_feedback_result
        mock_db.execute.return_value.__iter__.return_value = [mock_interaction_result]
        
        # Mock preferences
        with patch('shared.services.recommendation_service.recommendation_service.get_or_create_user_preferences') as mock_get_prefs:
            mock_preferences = UserPreference(
                user_id=self.test_user_id,
                confidence_score=0.8,
                interaction_count=25,
                last_updated=datetime.utcnow()
            )
            mock_get_prefs.return_value = mock_preferences
            
            response = self.client.get("/api/v1/recommendations/stats?timeframe_days=30")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_id"] == self.test_user_id
        assert data["timeframe_days"] == 30
        assert "interaction_stats" in data
        assert "feedback_stats" in data
        assert "preference_learning" in data
        
        preference_learning = data["preference_learning"]
        assert preference_learning["confidence_score"] == 0.8
        assert preference_learning["interaction_count"] == 25


# Import mock for the test
from unittest import mock