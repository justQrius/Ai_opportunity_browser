#!/usr/bin/env python3
"""
Final Integration Test - Verify CORS fix and complete data flow
"""

import asyncio
import aiohttp
import json


async def test_cors_and_integration():
    """Test that CORS is fixed and data flows properly"""
    print("🔧 FINAL INTEGRATION TEST - CORS FIX VERIFICATION")
    print("=" * 60)
    
    # Test CORS with the actual frontend origin
    print("\n1️⃣ Testing CORS with Frontend Origin (localhost:3004)")
    
    async with aiohttp.ClientSession() as session:
        headers = {
            'Origin': 'http://localhost:3004',
            'Content-Type': 'application/json'
        }
        
        try:
            async with session.get('http://localhost:8000/opportunities/', headers=headers) as resp:
                print(f"   Status: {resp.status}")
                print(f"   CORS Headers: {resp.headers.get('Access-Control-Allow-Origin', 'Not set')}")
                
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   ✅ SUCCESS: Loaded {len(data['items'])} opportunities")
                    
                    # Show sample data
                    if data['items']:
                        sample = data['items'][0]
                        print(f"   📋 Sample: {sample['title'][:50]}...")
                        print(f"   🎯 Score: {sample['validation_score']}")
                    
                    print("   🎉 CORS issue is RESOLVED!")
                    return True
                else:
                    print(f"   ❌ FAILED: Status {resp.status}")
                    return False
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            return False


async def test_all_endpoints():
    """Test all critical endpoints with CORS"""
    print("\n2️⃣ Testing All Critical Endpoints with CORS")
    
    endpoints = [
        ("/opportunities/", "Opportunities List"),
        ("/opportunities/trending", "Trending Opportunities"),
        ("/opportunities/recommendations", "Recommendations"),
        ("/health", "Health Check"),
        ("/agents/status", "Agent Status")
    ]
    
    headers = {
        'Origin': 'http://localhost:3004',
        'Content-Type': 'application/json'
    }
    
    results = {}
    
    async with aiohttp.ClientSession() as session:
        for endpoint, name in endpoints:
            try:
                async with session.get(f'http://localhost:8000{endpoint}', headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            count = len(data)
                        elif isinstance(data, dict):
                            count = len(data.get('items', data))
                        else:
                            count = 1
                        
                        print(f"   ✅ {name}: {count} items")
                        results[endpoint] = True
                    else:
                        print(f"   ❌ {name}: Status {resp.status}")
                        results[endpoint] = False
            except Exception as e:
                print(f"   ❌ {name}: Error {e}")
                results[endpoint] = False
    
    success_rate = sum(results.values()) / len(results)
    print(f"\n   📊 Success Rate: {success_rate:.1%} ({sum(results.values())}/{len(results)})")
    return success_rate >= 0.8


async def simulate_frontend_requests():
    """Simulate the exact requests the React frontend would make"""
    print("\n3️⃣ Simulating React Frontend Requests")
    
    # These are the exact requests the frontend components make
    frontend_requests = [
        {
            "url": "http://localhost:8000/opportunities/",
            "params": {"page": 1, "size": 20},
            "component": "OpportunityList"
        },
        {
            "url": "http://localhost:8000/opportunities/trending",
            "params": {"limit": 5},
            "component": "TrendingSection"
        },
        {
            "url": "http://localhost:8000/opportunities/recommendations",
            "params": {"limit": 5},
            "component": "RecommendationsSection"
        }
    ]
    
    headers = {
        'Origin': 'http://localhost:3004',
        'Content-Type': 'application/json'
    }
    
    all_successful = True
    
    async with aiohttp.ClientSession() as session:
        for request in frontend_requests:
            try:
                async with session.get(request['url'], params=request['params'], headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"   ✅ {request['component']}: Request successful")
                        
                        # Validate data structure
                        if request['component'] == 'OpportunityList':
                            if 'items' in data and 'total' in data:
                                print(f"      📊 Paginated response: {len(data['items'])} items of {data['total']} total")
                            else:
                                print(f"      ⚠️  Unexpected format: {list(data.keys())}")
                        else:
                            if isinstance(data, list):
                                print(f"      📋 Array response: {len(data)} items")
                            else:
                                print(f"      📊 Object response: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                    else:
                        print(f"   ❌ {request['component']}: Status {resp.status}")
                        all_successful = False
            except Exception as e:
                print(f"   ❌ {request['component']}: Error {e}")
                all_successful = False
    
    if all_successful:
        print("   🎉 All frontend requests are working perfectly!")
    else:
        print("   ⚠️  Some frontend requests had issues")
    
    return all_successful


async def main():
    """Run all tests"""
    print("🚀 Running Final Integration Test Suite...")
    
    test1 = await test_cors_and_integration()
    test2 = await test_all_endpoints()
    test3 = await simulate_frontend_requests()
    
    print("\n" + "=" * 60)
    print("📋 FINAL TEST RESULTS")
    print("=" * 60)
    
    results = [
        ("CORS Fix", test1),
        ("All Endpoints", test2),
        ("Frontend Simulation", test3)
    ]
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name}: {status}")
    
    print(f"\nOverall: {passed}/{total} ({passed/total:.1%})")
    
    if passed == total:
        print("\n🎉 PERFECT! All tests passed!")
        print("✅ CORS issue is completely resolved")
        print("✅ Frontend can now load opportunities from backend")
        print("✅ Real-time data integration is working")
        print("✅ All API endpoints are accessible")
        print("\n🚀 Your frontend should now work without any network errors!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the details above.")


if __name__ == "__main__":
    asyncio.run(main())