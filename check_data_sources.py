#!/usr/bin/env python3
"""
Check what real-time data sources are currently being used by agents
"""

import asyncio
import json
from realtime_data_bridge import data_bridge


async def analyze_current_data_sources():
    """Analyze what data sources are currently active and what data they provide"""
    print("📊 REAL-TIME DATA SOURCES ANALYSIS")
    print("=" * 60)
    
    # Initialize the data bridge
    print("🚀 Initializing data bridge...")
    await data_bridge.initialize()
    
    print(f"\n📡 ACTIVE PLUGINS: {len(data_bridge.plugins)}")
    print("-" * 40)
    
    for plugin_name, plugin in data_bridge.plugins.items():
        print(f"✅ {plugin_name.upper()}: {plugin.__class__.__name__}")
    
    print(f"\n🔍 TESTING DATA RETRIEVAL")
    print("-" * 40)
    
    # Test trending topics
    print("\n1️⃣ Trending Topics (Last 5)")
    try:
        trends = await data_bridge.get_trending_topics(5)
        print(f"   Found: {len(trends)} trending topics")
        
        for i, trend in enumerate(trends, 1):
            print(f"   {i}. [{trend['source']}] {trend['title'][:50]}...")
            print(f"      📅 {trend['created_at']}")
            print(f"      👍 {trend.get('votes', 0)} votes, 💬 {trend.get('comments', 0)} comments")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test market signals
    print(f"\n2️⃣ Market Signals (AI keywords)")
    try:
        signals = await data_bridge.get_market_signals(["AI", "automation", "startup"], 5)
        print(f"   Found: {len(signals)} market signals")
        
        for i, signal in enumerate(signals, 1):
            print(f"   {i}. [{signal['source']}] {signal['title'][:50]}...")
            print(f"      🎯 Relevance: {signal.get('relevance_score', 0)}")
            print(f"      📊 Engagement: {signal.get('engagement_score', 0)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test startup opportunities
    print(f"\n3️⃣ Startup Validation Data")
    try:
        startups = await data_bridge.get_startup_opportunities(3)
        print(f"   Found: {len(startups)} startup opportunities")
        
        for i, startup in enumerate(startups, 1):
            print(f"   {i}. [{startup['source']}] {startup['title'][:50]}...")
            if 'industries' in startup:
                print(f"      🏭 Industries: {', '.join(startup['industries'][:3])}")
            if 'funding' in startup:
                print(f"      💰 Funding: {startup['funding']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"\n📋 DATA SOURCE CAPABILITIES")
    print("-" * 40)
    
    # Hacker News capabilities
    if 'hackernews' in data_bridge.plugins:
        print("🟢 HACKER NEWS:")
        print("   - Story types: top, best, ask, show")
        print("   - Keywords: AI, startup, business, opportunity, automation")
        print("   - Min score threshold: 50 points")
        print("   - Data: title, content, votes, comments, URL")
    
    # Y Combinator capabilities  
    if 'ycombinator' in data_bridge.plugins:
        print("🟢 Y COMBINATOR:")
        print("   - Batch years: 2024, 2023")
        print("   - Keywords: AI, automation, SaaS, B2B, productivity")
        print("   - Data: company info, description, batch, funding, industries")
        print("   - Note: Currently having API access issues")
    
    # Missing sources
    print("🔴 UNAVAILABLE SOURCES:")
    missing_sources = {
        'reddit': 'Requires REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET',
        'github': 'Requires GITHUB_ACCESS_TOKEN', 
        'producthunt': 'Requires PRODUCTHUNT_ACCESS_TOKEN'
    }
    
    for source, requirement in missing_sources.items():
        if source not in data_bridge.plugins:
            print(f"   - {source.upper()}: {requirement}")
    
    print(f"\n💡 RECOMMENDATIONS")
    print("-" * 40)
    print("To add more data sources, set these environment variables:")
    print("   export REDDIT_CLIENT_ID='your_reddit_client_id'")
    print("   export REDDIT_CLIENT_SECRET='your_reddit_client_secret'")
    print("   export GITHUB_ACCESS_TOKEN='your_github_token'") 
    print("   export PRODUCTHUNT_ACCESS_TOKEN='your_producthunt_token'")
    
    await data_bridge.shutdown()


if __name__ == "__main__":
    asyncio.run(analyze_current_data_sources())