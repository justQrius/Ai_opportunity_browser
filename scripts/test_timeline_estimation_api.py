#!/usr/bin/env python3
"""
Test script for Timeline Estimation API endpoints.

This script tests the timeline estimation API functionality
including endpoint responses and data validation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient

# Import the FastAPI app
from api.main import app
from shared.services.timeline_estimation_service import EstimationMethod


def test_timeline_estimation_api():
    """Test timeline estimation API endpoints."""
    print("🧪 Testing Timeline Estimation API")
    print("=" * 50)
    
    client = TestClient(app)
    
    # Test getting estimation methods
    print("📊 Testing GET /api/v1/timeline-estimation/methods")
    response = client.get("/api/v1/timeline-estimation/methods")
    
    if response.status_code == 200:
        methods_data = response.json()
        print("✅ Successfully retrieved estimation methods")
        print(f"   Available methods: {len(methods_data['methods'])}")
        
        for method in methods_data['methods']:
            print(f"   - {method['name']}: {method['description']}")
    else:
        print(f"❌ Failed to get estimation methods: {response.status_code}")
        print(f"   Response: {response.text}")
    
    # Test getting resource rates
    print(f"\n💰 Testing GET /api/v1/timeline-estimation/resource-rates")
    response = client.get("/api/v1/timeline-estimation/resource-rates")
    
    if response.status_code == 200:
        rates_data = response.json()
        print("✅ Successfully retrieved resource rates")
        print(f"   Currency: {rates_data['currency']}")
        print(f"   Resource types: {len(rates_data['resource_rates'])}")
        
        # Show sample rates
        sample_resources = list(rates_data['resource_rates'].keys())[:3]
        for resource in sample_resources:
            rates = rates_data['resource_rates'][resource]
            junior_rate = rates.get('junior', 0)
            senior_rate = rates.get('senior', 0)
            print(f"   - {resource}: ${junior_rate}/hr (junior) - ${senior_rate}/hr (senior)")
    else:
        print(f"❌ Failed to get resource rates: {response.status_code}")
        print(f"   Response: {response.text}")
    
    # Test timeline estimation endpoint (this will fail without auth, but we can test the structure)
    print(f"\n📅 Testing POST /api/v1/timeline-estimation/estimate")
    
    estimation_request = {
        "opportunity_id": "test-opportunity-123",
        "estimation_method": "expert_judgment",
        "include_monte_carlo": False
    }
    
    response = client.post(
        "/api/v1/timeline-estimation/estimate",
        json=estimation_request
    )
    
    # This will likely fail with 401 (unauthorized) since we don't have auth
    if response.status_code == 401:
        print("✅ Endpoint correctly requires authentication")
        print("   Status: 401 Unauthorized (expected)")
    elif response.status_code == 422:
        print("✅ Endpoint correctly validates request data")
        print("   Status: 422 Validation Error (expected)")
    else:
        print(f"⚠️  Unexpected response: {response.status_code}")
        print(f"   Response: {response.text}")
    
    # Test getting timeline estimate by ID
    print(f"\n🔍 Testing GET /api/v1/timeline-estimation/estimate/test-id")
    response = client.get("/api/v1/timeline-estimation/estimate/test-id")
    
    if response.status_code == 401:
        print("✅ Endpoint correctly requires authentication")
        print("   Status: 401 Unauthorized (expected)")
    else:
        print(f"⚠️  Unexpected response: {response.status_code}")
        print(f"   Response: {response.text}")
    
    print(f"\n🎉 Timeline Estimation API testing completed!")
    print("=" * 50)


def test_estimation_method_enum():
    """Test that estimation method enum values are correct."""
    print("\n🔬 Testing Estimation Method Enum Values:")
    print("-" * 40)
    
    expected_methods = [
        "expert_judgment",
        "function_point", 
        "story_point",
        "historical_data",
        "monte_carlo",
        "parametric"
    ]
    
    for method in expected_methods:
        try:
            enum_value = EstimationMethod(method)
            print(f"✅ {method}: {enum_value.value}")
        except ValueError:
            print(f"❌ {method}: Not found in enum")
    
    print(f"\n✅ Estimation method enum validation completed!")


def test_api_documentation():
    """Test that API documentation is accessible."""
    print("\n📚 Testing API Documentation:")
    print("-" * 30)
    
    client = TestClient(app)
    
    # Test OpenAPI schema
    response = client.get("/openapi.json")
    if response.status_code == 200:
        openapi_data = response.json()
        print("✅ OpenAPI schema accessible")
        
        # Check if timeline estimation endpoints are documented
        paths = openapi_data.get("paths", {})
        timeline_paths = [path for path in paths.keys() if "timeline" in path]
        
        print(f"   Timeline estimation endpoints documented: {len(timeline_paths)}")
        for path in timeline_paths:
            print(f"   - {path}")
    else:
        print(f"❌ OpenAPI schema not accessible: {response.status_code}")
    
    # Test Swagger UI (if available)
    response = client.get("/docs")
    if response.status_code == 200:
        print("✅ Swagger UI accessible at /docs")
    else:
        print(f"⚠️  Swagger UI not accessible: {response.status_code}")


if __name__ == "__main__":
    print("🧪 Timeline Estimation API Test Suite")
    print("=" * 60)
    
    # Run API tests
    test_timeline_estimation_api()
    
    # Run enum tests
    test_estimation_method_enum()
    
    # Test API documentation
    test_api_documentation()
    
    print("\n✅ All API tests completed!")