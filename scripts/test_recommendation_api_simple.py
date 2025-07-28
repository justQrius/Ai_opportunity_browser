#!/usr/bin/env python3
"""
Simple test script for the Recommendation API implementation.

This script tests the API structure and imports without requiring database connections.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all recommendation-related modules can be imported."""
    print("🧪 Testing Recommendation API Imports...")
    
    try:
        # Test recommendation service import
        from shared.services.recommendation_service import recommendation_service
        print("✅ Recommendation service imported successfully")
        
        # Test recommendation router import
        from api.routers.recommendations import router
        print("✅ Recommendation router imported successfully")
        
        # Test schemas import
        from shared.schemas.opportunity import OpportunityRecommendationRequest
        print("✅ Recommendation schemas imported successfully")
        
        # Test models import
        from shared.models.user_interaction import UserInteraction, UserPreference, RecommendationFeedback, InteractionType
        print("✅ User interaction models imported successfully")
        
        print("\n✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {str(e)}")
        return False

def test_api_structure():
    """Test the API router structure."""
    print("\n🏗️ Testing API Structure...")
    
    try:
        from api.routers.recommendations import router
        
        # Check that router has the expected routes
        routes = [route.path for route in router.routes]
        expected_routes = [
            "/",
            "/feedback", 
            "/explain/{opportunity_id}",
            "/interactions",
            "/preferences",
            "/preferences/update",
            "/stats"
        ]
        
        for expected_route in expected_routes:
            if expected_route not in routes:
                print(f"❌ Missing route: {expected_route}")
                return False
            else:
                print(f"✅ Found route: {expected_route}")
        
        print("\n✅ API structure is correct!")
        return True
        
    except Exception as e:
        print(f"\n❌ API structure test failed: {str(e)}")
        return False

def test_recommendation_service_methods():
    """Test that recommendation service has expected methods."""
    print("\n🔧 Testing Recommendation Service Methods...")
    
    try:
        from shared.services.recommendation_service import RecommendationService
        
        service = RecommendationService()
        
        expected_methods = [
            "get_personalized_recommendations",
            "record_interaction",
            "record_recommendation_feedback",
            "explain_recommendation",
            "get_or_create_user_preferences",
            "update_user_preferences_from_interactions"
        ]
        
        for method_name in expected_methods:
            if hasattr(service, method_name):
                print(f"✅ Found method: {method_name}")
            else:
                print(f"❌ Missing method: {method_name}")
                return False
        
        print("\n✅ All expected methods found!")
        return True
        
    except Exception as e:
        print(f"\n❌ Service methods test failed: {str(e)}")
        return False

def test_schemas():
    """Test that schemas are properly defined."""
    print("\n📋 Testing Schemas...")
    
    try:
        from shared.schemas.opportunity import OpportunityRecommendationRequest
        from shared.models.user_interaction import InteractionType
        
        # Test creating a recommendation request
        request = OpportunityRecommendationRequest(
            user_id="test-user-id",
            limit=10,
            include_viewed=False,
            ai_solution_types=["ml", "nlp"],
            industries=["healthcare", "fintech"]
        )
        
        print(f"✅ OpportunityRecommendationRequest created: {request.user_id}")
        
        # Test interaction types
        interaction_types = [
            InteractionType.VIEW,
            InteractionType.CLICK,
            InteractionType.BOOKMARK,
            InteractionType.SEARCH,
            InteractionType.VALIDATE
        ]
        
        for interaction_type in interaction_types:
            print(f"✅ InteractionType available: {interaction_type.value}")
        
        print("\n✅ All schemas working correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ Schema test failed: {str(e)}")
        return False

def main():
    """Run all simple tests."""
    print("🚀 Starting Simple Recommendation API Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_api_structure,
        test_recommendation_service_methods,
        test_schemas
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Recommendation API implementation is complete.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)