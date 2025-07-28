#!/usr/bin/env python3
"""
Test script to verify the trending endpoint works and fix routing issues.
"""

import asyncio
import aiohttp
import json


async def test_trending_direct():
    """Test trending endpoint directly"""
    print("🧪 Testing Trending Endpoint Fix")
    print("=" * 40)
    
    async with aiohttp.ClientSession() as session:
        # Test all routes to see what's working
        test_urls = [
            ("Health", "http://localhost:8000/health"),
            ("Opportunities Base", "http://localhost:8000/opportunities/"), 
            ("Agent Status", "http://localhost:8000/agents/status"),
            ("Trending", "http://localhost:8000/opportunities/trending"),
            ("Recommendations", "http://localhost:8000/opportunities/recommendations"),
            ("Search", "http://localhost:8000/opportunities/search?query=AI")
        ]
        
        for name, url in test_urls:
            try:
                print(f"\n📡 Testing {name}: {url}")
                async with session.get(url) as resp:
                    print(f"   Status: {resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            print(f"   Response: List with {len(data)} items")
                            if data:
                                print(f"   Sample: {str(data[0])[:100]}...")
                        elif isinstance(data, dict):
                            print(f"   Response: Dict with keys: {list(data.keys())}")
                        else:
                            print(f"   Response: {type(data)}")
                    else:
                        error_data = await resp.text()
                        print(f"   Error: {error_data}")
            except Exception as e:
                print(f"   Exception: {e}")


if __name__ == "__main__":
    asyncio.run(test_trending_direct())