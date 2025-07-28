#!/usr/bin/env python3
"""
Test script for FastAPI application structure.
This script validates that the FastAPI app can be imported and started correctly.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_app_import():
    """Test that the FastAPI app can be imported."""
    print("🧪 Testing FastAPI App Import")
    print("=" * 40)
    
    try:
        from api.main import app
        print("✅ FastAPI app imported successfully")
        
        # Check app configuration
        print(f"✅ App title: {app.title}")
        print(f"✅ App version: {app.version}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to import FastAPI app: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_loading():
    """Test that configuration loads correctly."""
    print("\n⚙️  Testing Configuration Loading")
    print("=" * 40)
    
    try:
        from api.core.config import get_settings
        settings = get_settings()
        
        print(f"✅ App name: {settings.APP_NAME}")
        print(f"✅ Environment: {settings.ENVIRONMENT}")
        print(f"✅ Debug mode: {settings.DEBUG}")
        print(f"✅ Database URL configured: {bool(settings.DATABASE_URL)}")
        print(f"✅ Redis URL configured: {bool(settings.REDIS_URL)}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return False


def test_routers_import():
    """Test that all routers can be imported."""
    print("\n🛣️  Testing Router Imports")
    print("=" * 40)
    
    routers = [
        ("health", "api.routers.health"),
        ("opportunities", "api.routers.opportunities"),
        ("users", "api.routers.users"),
        ("validations", "api.routers.validations")
    ]
    
    all_imported = True
    for router_name, module_path in routers:
        try:
            __import__(module_path)
            print(f"✅ {router_name} router imported successfully")
        except Exception as e:
            print(f"❌ Failed to import {router_name} router: {e}")
            all_imported = False
    
    return all_imported


def test_middleware_import():
    """Test that middleware can be imported."""
    print("\n🔒 Testing Middleware Imports")
    print("=" * 40)
    
    middleware_modules = [
        ("security", "api.middleware.security"),
        ("rate_limit", "api.middleware.rate_limit")
    ]
    
    all_imported = True
    for middleware_name, module_path in middleware_modules:
        try:
            __import__(module_path)
            print(f"✅ {middleware_name} middleware imported successfully")
        except Exception as e:
            print(f"❌ Failed to import {middleware_name} middleware: {e}")
            all_imported = False
    
    return all_imported


def test_app_routes():
    """Test that app routes are properly configured."""
    print("\n🛤️  Testing App Routes")
    print("=" * 40)
    
    try:
        from api.main import app
        
        # Get all routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        expected_routes = [
            "/",
            "/health/",
            "/api/v1/opportunities/",
            "/api/v1/users/",
            "/api/v1/validations/"
        ]
        
        print(f"✅ Total routes configured: {len(routes)}")
        
        for expected_route in expected_routes:
            # Check if any route starts with the expected path
            found = any(route.startswith(expected_route.rstrip('/')) for route in routes)
            if found:
                print(f"✅ Route group '{expected_route}' configured")
            else:
                print(f"❌ Route group '{expected_route}' missing")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Failed to test app routes: {e}")
        return False


def main():
    """Run all FastAPI application tests."""
    print("🚀 FASTAPI APPLICATION STRUCTURE TEST")
    print("=" * 50)
    
    tests = [
        test_app_import,
        test_config_loading,
        test_routers_import,
        test_middleware_import,
        test_app_routes
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All FastAPI application tests passed!")
        print("\nFastAPI application structure is ready!")
        print("\nNext steps:")
        print("1. Run: python -m uvicorn api.main:app --reload")
        print("2. Visit: http://localhost:8000")
        print("3. API docs: http://localhost:8000/docs")
        return 0
    else:
        print("❌ Some FastAPI application tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())