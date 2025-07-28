"""
Tests for Opportunities API endpoints.
Tests CRUD operations, filtering, and pagination for opportunities.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch, Mock
from fastapi.testclient import TestClient
from fastapi import status

from api.main import app
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.schemas.opportunity import OpportunityCreate, OpportunityUpdate


class TestOpportunitiesAPI:
    """Test cases for Opportunities API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        return Mock(
            id="test-user-id",
            username="testuser",
            email="test@example.com",
            role=Mock(value="user")
        )
    
    @pytest.fixture
    def mock_admin_user(self):
        """Mock admin user."""
        return Mock(
            id="admin-user-id",
            username="admin",
            email="admin@example.com",
            role=Mock(value="admin")
        )
    
    @pytest.fixture
    def sample_opportunity(self):
        """Sample opportunity for testing."""
        return Opportunity(
            id="test-opp-id",
            title="AI-Powered Document Analysis",
            description="Automated document processing using NLP and computer vision",
            summary="AI solution for document automation",
            status=OpportunityStatus.VALIDATED,
            validation_score=8.5,
            confidence_rating=7.8,
            ai_feasibility_score=8.2,
            ai_solution_types='["nlp", "computer_vision"]',
            target_industries='["legal", "healthcare"]',
            geographic_scope="global",
            tags='["automation", "documents"]',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def test_list_opportunities_success(self, client, sample_opportunity):
        """Test successful opportunity listing."""
        with patch('api.routers.opportunities.opportunity_service') as mock_service, \
             patch('api.routers.opportunities.get_optional_user', return_value=None):
            
            # Mock service response
            mock_service.search_opportunities.return_value = ([sample_opportunity], 1)
            
            response = client.get("/api/v1/opportunities/")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "items" in data
            assert "pagination" in data
            assert "total_count" in data
            assert data["total_count"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["title"] == "AI-Powered Document Analysis"
    
    def test_list_opportunities_with_filters(self, client, sample_opportunity):
        """Test opportunity listing with filters."""
        with patch('api.routers.opportunities.opportunity_service') as mock_service, \
             patch('api.routers.opportunities.get_optional_user', return_value=None):
            
            mock_service.search_opportunities.return_value = ([sample_opportunity], 1)
            
            response = client.get(
                "/api/v1/opportunities/",
                params={
                    "search": "AI document",
                    "min_validation_score": 7.0,
                    "status": ["validated"],
                    "page": 1,
                    "page_size": 10
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify filters were applied
            assert "filters_applied" in data
            assert data["filters_applied"]["search"] == "AI document"
            assert data["filters_applied"]["min_validation_score"] == 7.0
    
    def test_get_opportunity_success(self, client, sample_opportunity):
        """Test successful opportunity retrieval."""
        with patch('api.routers.opportunities.opportunity_service') as mock_service, \
             patch('api.routers.opportunities.get_optional_user', return_value=None):
            
            mock_service.get_opportunity_by_id.return_value = sample_opportunity
            
            response = client.get("/api/v1/opportunities/test-opp-id")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["id"] == "test-opp-id"
            assert data["title"] == "AI-Powered Document Analysis"
            assert data["status"] == "validated"
            assert data["validation_score"] == 8.5
    
    def test_get_opportunity_not_found(self, client):
        """Test opportunity not found."""
        with patch('api.routers.opportunities.opportunity_service') as mock_service, \
             patch('api.routers.opportunities.get_optional_user', return_value=None):
            
            mock_service.get_opportunity_by_id.return_value = None
            
            response = client.get("/api/v1/opportunities/nonexistent-id")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "not found" in data["detail"].lower()
    
    def test_create_opportunity_success(self, client, mock_user):
        """Test successful opportunity creation."""
        opportunity_data = {
            "title": "New AI Opportunity",
            "description": "A new AI-powered solution for business automation",
            "summary": "Business automation AI solution",
            "ai_solution_types": ["machine_learning", "automation"],
            "target_industries": ["business", "technology"],
            "geographic_scope": "global",
            "tags": ["automation", "business", "ai"]
        }
        
        mock_created_opportunity = Mock()
        mock_created_opportunity.id = "new-opp-id"
        mock_created_opportunity.title = opportunity_data["title"]
        mock_created_opportunity.status = OpportunityStatus.DISCOVERED
        mock_created_opportunity.created_at = datetime.utcnow()
        
        with patch('api.routers.opportunities.opportunity_service') as mock_service, \
             patch('api.routers.opportunities.get_current_user', return_value=mock_user):
            
            mock_service.create_opportunity.return_value = mock_created_opportunity
            
            response = client.post(
                "/api/v1/opportunities/",
                json=opportunity_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["success"] is True
            assert "created successfully" in data["message"]
            assert data["data"]["opportunity_id"] == "new-opp-id"
            assert data["data"]["title"] == opportunity_data["title"]
    
    def test_create_opportunity_validation_error(self, client, mock_user):
        """Test opportunity creation with validation error."""
        invalid_data = {
            "title": "Short",  # Too short
            "description": "Too short description"  # Too short
        }
        
        with patch('api.routers.opportunities.get_current_user', return_value=mock_user):
            response = client.post(
                "/api/v1/opportunities/",
                json=invalid_data
            )
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_update_opportunity_success(self, client, mock_user, sample_opportunity):
        """Test successful opportunity update."""
        update_data = {
            "title": "Updated AI Solution",
            "summary": "Updated summary",
            "status": "validating"
        }
        
        updated_opportunity = Mock()
        updated_opportunity.id = sample_opportunity.id
        updated_opportunity.title = update_data["title"]
        updated_opportunity.status = OpportunityStatus.VALIDATING
        updated_opportunity.updated_at = datetime.utcnow()
        
        with patch('api.routers.opportunities.opportunity_service') as mock_service, \
             patch('api.routers.opportunities.get_current_user', return_value=mock_user):
            
            mock_service.get_opportunity_by_id.return_value = sample_opportunity
            mock_service.update_opportunity.return_value = updated_opportunity
            
            response = client.put(
                f"/api/v1/opportunities/{sample_opportunity.id}",
                json=update_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["success"] is True
            assert "updated successfully" in data["message"]
            assert data["data"]["title"] == update_data["title"]
    
    def test_update_opportunity_not_found(self, client, mock_user):
        """Test updating non-existent opportunity."""
        update_data = {
            "title": "Updated Title"
        }
        
        with patch('api.routers.opportunities.opportunity_service') as mock_service, \
             patch('api.routers.opportunities.get_current_user', return_value=mock_user):
            
            mock_service.get_opportunity_by_id.return_value = None
            
            response = client.put(
                "/api/v1/opportunities/nonexistent-id",
                json=update_data
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_opportunity_success(self, client, mock_admin_user, sample_opportunity):
        """Test successful opportunity deletion (admin only)."""
        updated_opportunity = Mock()
        updated_opportunity.id = sample_opportunity.id
        updated_opportunity.status = OpportunityStatus.ARCHIVED
        updated_opportunity.updated_at = datetime.utcnow()
        
        with patch('api.routers.opportunities.opportunity_service') as mock_service, \
             patch('api.routers.opportunities.require_admin', return_value=lambda: mock_admin_user):
            
            mock_service.get_opportunity_by_id.return_value = sample_opportunity
            mock_service.update_opportunity.return_value = updated_opportunity
            
            response = client.delete(f"/api/v1/opportunities/{sample_opportunity.id}")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["success"] is True
            assert "deleted successfully" in data["message"]
            assert data["data"]["status"] == "archived"
    
    def test_delete_opportunity_not_found(self, client, mock_admin_user):
        """Test deleting non-existent opportunity."""
        with patch('api.routers.opportunities.opportunity_service') as mock_service, \
             patch('api.routers.opportunities.require_admin', return_value=lambda: mock_admin_user):
            
            mock_service.get_opportunity_by_id.return_value = None
            
            response = client.delete("/api/v1/opportunities/nonexistent-id")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_search_opportunities_advanced(self, client, sample_opportunity):
        """Test advanced opportunity search."""
        search_data = {
            "query": "AI automation",
            "min_validation_score": 6.0,
            "max_validation_score": 10.0,
            "status": ["validated"],
            "ai_solution_types": ["nlp"],
            "page": 1,
            "page_size": 20
        }
        
        with patch('api.routers.opportunities.opportunity_service') as mock_service, \
             patch('api.routers.opportunities.get_optional_user', return_value=None):
            
            mock_service.search_opportunities.return_value = ([sample_opportunity], 1)
            
            response = client.post(
                "/api/v1/opportunities/search",
                json=search_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "items" in data
            assert "pagination" in data
            assert data["total_count"] == 1
            assert "filters_applied" in data
    
    def test_get_recommendations_success(self, client, mock_user, sample_opportunity):
        """Test personalized recommendations."""
        recommendation_data = {
            "user_id": mock_user.id,
            "limit": 5,
            "ai_solution_types": ["nlp", "ml"],
            "industries": ["healthcare"]
        }
        
        with patch('api.routers.opportunities.opportunity_service') as mock_service, \
             patch('api.routers.opportunities.get_current_user', return_value=mock_user):
            
            mock_service.get_personalized_recommendations.return_value = [sample_opportunity]
            
            response = client.post(
                "/api/v1/opportunities/recommendations",
                json=recommendation_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "items" in data
            assert len(data["items"]) == 1
            assert data["items"][0]["title"] == sample_opportunity.title
    
    def test_get_recommendations_forbidden(self, client, mock_user):
        """Test recommendations for another user (should be forbidden)."""
        recommendation_data = {
            "user_id": "another-user-id",  # Different from mock_user.id
            "limit": 5
        }
        
        with patch('api.routers.opportunities.get_current_user', return_value=mock_user):
            response = client.post(
                "/api/v1/opportunities/recommendations",
                json=recommendation_data
            )
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_opportunity_stats(self, client):
        """Test opportunity statistics endpoint."""
        mock_analytics = {
            "total_opportunities": 150,
            "opportunities_by_status": {
                "discovered": 50,
                "validating": 40,
                "validated": 45,
                "rejected": 15
            },
            "average_validation_score": 6.8
        }
        
        with patch('api.routers.opportunities.opportunity_service') as mock_service, \
             patch('api.routers.opportunities.get_optional_user', return_value=None):
            
            mock_service.get_opportunity_analytics.return_value = mock_analytics
            mock_service.search_opportunities.return_value = ([], 0)  # For trending
            
            response = client.get("/api/v1/opportunities/stats/overview")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["total_opportunities"] == 150
            assert data["average_validation_score"] == 6.8
            assert "opportunities_by_status" in data
    
    def test_bookmark_opportunity_success(self, client, mock_user, sample_opportunity):
        """Test opportunity bookmarking."""
        bookmark_data = {
            "user_id": mock_user.id,
            "opportunity_id": sample_opportunity.id,
            "collection_name": "My Favorites",
            "notes": "Interesting AI solution"
        }
        
        with patch('api.routers.opportunities.opportunity_service') as mock_service, \
             patch('api.routers.opportunities.get_current_user', return_value=mock_user):
            
            mock_service.get_opportunity_by_id.return_value = sample_opportunity
            
            response = client.post(
                "/api/v1/opportunities/bookmarks",
                json=bookmark_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["success"] is True
            assert "bookmarked successfully" in data["message"]
            assert data["data"]["opportunity_id"] == sample_opportunity.id
    
    def test_bookmark_opportunity_forbidden(self, client, mock_user):
        """Test bookmarking for another user (should be forbidden)."""
        bookmark_data = {
            "user_id": "another-user-id",  # Different from mock_user.id
            "opportunity_id": "test-opp-id"
        }
        
        with patch('api.routers.opportunities.get_current_user', return_value=mock_user):
            response = client.post(
                "/api/v1/opportunities/bookmarks",
                json=bookmark_data
            )
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_user_bookmarks_success(self, client, mock_user):
        """Test retrieving user bookmarks."""
        with patch('api.routers.opportunities.get_current_user', return_value=mock_user):
            response = client.get(f"/api/v1/opportunities/bookmarks/{mock_user.id}")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "items" in data
            assert "pagination" in data
            assert data["total_count"] == 0  # Placeholder implementation returns empty
    
    def test_get_user_bookmarks_forbidden(self, client, mock_user):
        """Test accessing another user's bookmarks (should be forbidden)."""
        with patch('api.routers.opportunities.get_current_user', return_value=mock_user):
            response = client.get("/api/v1/opportunities/bookmarks/another-user-id")
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_pagination_parameters(self, client):
        """Test pagination parameter validation."""
        with patch('api.routers.opportunities.opportunity_service') as mock_service, \
             patch('api.routers.opportunities.get_optional_user', return_value=None):
            
            mock_service.search_opportunities.return_value = ([], 0)
            
            # Test valid pagination
            response = client.get(
                "/api/v1/opportunities/",
                params={"page": 2, "page_size": 50}
            )
            assert response.status_code == status.HTTP_200_OK
            
            # Test invalid page (should default to 1)
            response = client.get(
                "/api/v1/opportunities/",
                params={"page": 0}
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            
            # Test invalid page_size (should be limited)
            response = client.get(
                "/api/v1/opportunities/",
                params={"page_size": 200}
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_error_handling(self, client):
        """Test API error handling."""
        with patch('api.routers.opportunities.opportunity_service') as mock_service, \
             patch('api.routers.opportunities.get_optional_user', return_value=None):
            
            # Simulate service error
            mock_service.search_opportunities.side_effect = Exception("Database error")
            
            response = client.get("/api/v1/opportunities/")
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "Failed to retrieve opportunities" in data["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])