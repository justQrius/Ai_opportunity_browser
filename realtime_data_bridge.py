"""Real-time data bridge connecting data ingestion plugins to AI agents."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sys
import os

# Add data-ingestion to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'data-ingestion'))

try:
    from plugins.reddit_plugin import RedditPlugin, RedditConfig
    from plugins.github_plugin import GitHubPlugin, GitHubConfig
    from plugins.hackernews_plugin import HackerNewsPlugin, HackerNewsConfig
    from plugins.producthunt_plugin import ProductHuntPlugin, ProductHuntConfig
    from plugins.ycombinator_plugin import YCombinatorPlugin, YCombinatorConfig
    from plugins.base import RawData
except ImportError as e:
    print(f"Plugin import error: {e}")
    # Fallback - continue without plugins
    pass


logger = logging.getLogger(__name__)


class RealTimeDataBridge:
    """Bridge service that provides real-time market data to AI agents."""
    
    def __init__(self):
        self.plugins = {}
        self.data_cache = {
            'reddit': [],
            'github': [],  
            'hackernews': [],
            'producthunt': [],
            'ycombinator': []
        }
        self.last_updated = {}
        self.update_interval = 3600  # 1 hour
        self.initialized = False
        
    async def initialize(self) -> bool:
        """Initialize all data source plugins."""
        try:
            print("🚀 Initializing Real-Time Data Bridge...")
            
            # Initialize plugins with minimal config for demo
            # Note: In production, these would come from environment variables
            
            # Hacker News (no auth required)
            try:
                hn_config = HackerNewsConfig()
                hn_plugin = HackerNewsPlugin(hn_config)
                await hn_plugin.initialize()
                self.plugins['hackernews'] = hn_plugin
                print("✅ Hacker News plugin initialized")
            except Exception as e:
                print(f"⚠️  Hacker News plugin failed: {e}")
            
            # Reddit (requires API keys)
            reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
            reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
            if reddit_client_id and reddit_client_secret:
                try:
                    reddit_config = RedditConfig(
                        client_id=reddit_client_id,
                        client_secret=reddit_client_secret,
                        user_agent="AI-Opportunity-Browser/1.0"
                    )
                    reddit_plugin = RedditPlugin(reddit_config)
                    await reddit_plugin.initialize()
                    self.plugins['reddit'] = reddit_plugin
                    print("✅ Reddit plugin initialized")
                except Exception as e:
                    print(f"⚠️  Reddit plugin failed: {e}")
            else:
                print("⚠️  Reddit plugin skipped (no API keys)")
            
            # GitHub (requires API token)
            github_token = os.getenv('GITHUB_ACCESS_TOKEN')
            if github_token:
                try:
                    github_config = GitHubConfig(access_token=github_token)
                    github_plugin = GitHubPlugin(github_config)
                    await github_plugin.initialize()
                    self.plugins['github'] = github_plugin
                    print("✅ GitHub plugin initialized")
                except Exception as e:
                    print(f"⚠️  GitHub plugin failed: {e}")
            else:
                print("⚠️  GitHub plugin skipped (no API token)")
            
            # Product Hunt (requires API token)
            ph_token = os.getenv('PRODUCTHUNT_ACCESS_TOKEN')
            if ph_token:
                try:
                    ph_config = ProductHuntConfig(access_token=ph_token)
                    ph_plugin = ProductHuntPlugin(ph_config)
                    await ph_plugin.initialize()
                    self.plugins['producthunt'] = ph_plugin
                    print("✅ Product Hunt plugin initialized")
                except Exception as e:
                    print(f"⚠️  Product Hunt plugin failed: {e}")
            else:
                print("⚠️  Product Hunt plugin skipped (no API token)")
            
            # Y Combinator (no auth required, web scraping)
            try:
                yc_config = YCombinatorConfig()
                yc_plugin = YCombinatorPlugin(yc_config)
                await yc_plugin.initialize()
                self.plugins['ycombinator'] = yc_plugin
                print("✅ Y Combinator plugin initialized")
            except Exception as e:
                print(f"⚠️  Y Combinator plugin failed: {e}")
            
            print(f"🎯 Data Bridge initialized with {len(self.plugins)} active plugins")
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Data Bridge initialization failed: {e}")
            return False
    
    async def get_trending_topics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending topics from all data sources."""
        if not self.initialized:
            await self.initialize()
        
        trending_data = []
        
        # Fetch from Hacker News
        if 'hackernews' in self.plugins:
            try:
                hn_trends = await self._fetch_hackernews_trends(limit)
                trending_data.extend(hn_trends)
            except Exception as e:
                print(f"HN trends error: {e}")
        
        # Fetch from Reddit
        if 'reddit' in self.plugins:
            try:
                reddit_trends = await self._fetch_reddit_trends(limit)
                trending_data.extend(reddit_trends)
            except Exception as e:
                print(f"Reddit trends error: {e}")
        
        # Fetch from Y Combinator
        if 'ycombinator' in self.plugins:
            try:
                yc_trends = await self._fetch_yc_trends(limit)
                trending_data.extend(yc_trends)
            except Exception as e:
                print(f"YC trends error: {e}")
        
        # Sort by relevance/engagement and return top items
        trending_data.sort(key=lambda x: x.get('engagement_score', 0), reverse=True)
        return trending_data[:limit]
    
    async def get_market_signals(self, keywords: List[str], limit: int = 20) -> List[Dict[str, Any]]:
        """Get market signals based on keywords."""
        if not self.initialized:
            await self.initialize()
        
        signals = []
        
        # Fetch from all available plugins
        for source_name, plugin in self.plugins.items():
            try:
                source_signals = await self._fetch_source_signals(plugin, keywords, limit // len(self.plugins))
                signals.extend(source_signals)
            except Exception as e:
                print(f"Error fetching from {source_name}: {e}")
        
        # Sort by relevance and return
        signals.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return signals[:limit]
    
    async def get_startup_opportunities(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Get startup opportunities from YC, Product Hunt, and other sources."""
        if not self.initialized:
            await self.initialize()
        
        opportunities = []
        
        # Y Combinator companies
        if 'ycombinator' in self.plugins:
            try:
                yc_opportunities = await self._fetch_yc_opportunities(limit // 2)
                opportunities.extend(yc_opportunities)
            except Exception as e:
                print(f"YC opportunities error: {e}")
        
        # Product Hunt launches
        if 'producthunt' in self.plugins:
            try:
                ph_opportunities = await self._fetch_ph_opportunities(limit // 2)
                opportunities.extend(ph_opportunities)
            except Exception as e:
                print(f"PH opportunities error: {e}")
        
        return opportunities[:limit]
    
    async def _fetch_hackernews_trends(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch trending topics from Hacker News."""
        plugin = self.plugins['hackernews']
        
        params = {
            "story_types": ["top", "best"],
            "keywords": ["AI", "startup", "business", "opportunity", "automation"],
            "max_stories": limit * 2,
            "min_score": 50
        }
        
        trends = []
        async for raw_data in plugin.fetch_data(params):
            trend = {
                "title": raw_data.title,
                "description": raw_data.content[:200] + "..." if len(raw_data.content) > 200 else raw_data.content,
                "source": "Hacker News",
                "url": raw_data.source_url,
                "engagement_score": raw_data.metadata.get('engagement_score', 0),
                "signal_type": raw_data.metadata.get('signal_type', 'discussion'),
                "created_at": raw_data.extracted_at.isoformat(),
                "votes": raw_data.upvotes,
                "comments": raw_data.comments_count
            }
            trends.append(trend)
            
            if len(trends) >= limit:
                break
        
        return trends
    
    async def _fetch_reddit_trends(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch trending topics from Reddit."""
        if 'reddit' not in self.plugins:
            return []
        
        plugin = self.plugins['reddit']
        
        params = {
            "subreddits": ["artificial", "MachineLearning", "startups", "entrepreneur"],
            "keywords": ["AI", "automation", "startup", "opportunity", "pain point"],
            "max_posts": limit * 2,
            "sort_by": "hot"
        }
        
        trends = []
        async for raw_data in plugin.fetch_data(params):
            trend = {
                "title": raw_data.title,
                "description": raw_data.content[:200] + "..." if len(raw_data.content) > 200 else raw_data.content,
                "source": f"Reddit r/{raw_data.metadata.get('subreddit', 'unknown')}",
                "url": raw_data.source_url,
                "engagement_score": raw_data.metadata.get('engagement_score', 0),
                "signal_type": raw_data.metadata.get('signal_type', 'discussion'),
                "created_at": raw_data.extracted_at.isoformat(),
                "votes": raw_data.upvotes,
                "comments": raw_data.comments_count
            }
            trends.append(trend)
            
            if len(trends) >= limit:
                break
        
        return trends
    
    async def _fetch_yc_trends(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch trending topics from Y Combinator companies."""
        if 'ycombinator' not in self.plugins:
            return []
        
        plugin = self.plugins['ycombinator']
        
        params = {
            "batch_years": ["2024", "2023"],
            "keywords": ["AI", "automation", "SaaS", "B2B", "productivity"],
            "max_companies_per_batch": limit
        }
        
        trends = []
        async for raw_data in plugin.fetch_data(params):
            trend = {
                "title": raw_data.title,
                "description": raw_data.content[:300] + "..." if len(raw_data.content) > 300 else raw_data.content,
                "source": f"Y Combinator {raw_data.metadata.get('batch', 'Unknown')}",
                "url": raw_data.source_url,
                "engagement_score": raw_data.metadata.get('relevance_score', 0),
                "signal_type": raw_data.metadata.get('signal_type', 'startup_validation'),
                "created_at": raw_data.extracted_at.isoformat(),
                "status": raw_data.metadata.get('status', 'Active'),
                "industries": raw_data.metadata.get('industries', []),
                "funding": raw_data.metadata.get('funding_amount')
            }
            trends.append(trend)
            
            if len(trends) >= limit:
                break
        
        return trends
    
    async def _fetch_source_signals(self, plugin, keywords: List[str], limit: int) -> List[Dict[str, Any]]:
        """Generic method to fetch signals from any plugin."""
        signals = []
        
        params = {
            "keywords": keywords,
            "max_results": limit * 2  # Fetch more to filter later
        }
        
        # Customize params based on plugin type
        if hasattr(plugin, 'hn_config'):  # Hacker News
            params.update({
                "story_types": ["ask", "show", "top"],
                "max_stories": limit * 2,
                "min_score": 20
            })
        elif hasattr(plugin, 'reddit_config'):  # Reddit
            params.update({
                "subreddits": ["artificial", "MachineLearning", "startups", "entrepreneur", "SaaS"],
                "max_posts": limit * 2
            })
        elif hasattr(plugin, 'yc_config'):  # Y Combinator
            params.update({
                "batch_years": ["2024", "2023"],
                "max_companies_per_batch": limit
            })
        
        try:
            async for raw_data in plugin.fetch_data(params):
                signal = {
                    "title": raw_data.title,
                    "content": raw_data.content,
                    "source": raw_data.source,
                    "url": raw_data.source_url,
                    "author": raw_data.author,
                    "engagement_score": raw_data.metadata.get('engagement_score', 0),
                    "relevance_score": raw_data.metadata.get('relevance_score', 0),
                    "signal_type": raw_data.metadata.get('signal_type', 'unknown'),
                    "created_at": raw_data.extracted_at.isoformat(),
                    "metadata": raw_data.metadata
                }
                signals.append(signal)
                
                if len(signals) >= limit:
                    break
        except Exception as e:
            print(f"Error fetching signals from {plugin.__class__.__name__}: {e}")
        
        return signals
    
    async def _fetch_yc_opportunities(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch startup opportunities from Y Combinator."""
        if 'ycombinator' not in self.plugins:
            return []
        
        plugin = self.plugins['ycombinator']
        
        params = {
            "batch_years": ["2024", "2023"],
            "keywords": ["AI", "machine learning", "automation", "SaaS", "B2B"],
            "max_companies_per_batch": limit,
            "include_failed_companies": False
        }
        
        opportunities = []
        async for raw_data in plugin.fetch_data(params):
            opportunity = {
                "title": raw_data.title,
                "description": raw_data.content,
                "source": "Y Combinator",
                "url": raw_data.source_url,
                "batch": raw_data.metadata.get('batch'),
                "status": raw_data.metadata.get('status'),
                "industries": raw_data.metadata.get('industries', []),
                "funding": raw_data.metadata.get('funding_amount'),
                "location": raw_data.metadata.get('location'),
                "relevance_score": raw_data.metadata.get('relevance_score', 0),
                "signal_type": "startup_validation",
                "created_at": raw_data.extracted_at.isoformat()
            }
            opportunities.append(opportunity)
            
            if len(opportunities) >= limit:
                break
        
        return opportunities
    
    async def _fetch_ph_opportunities(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch opportunities from Product Hunt."""
        if 'producthunt' not in self.plugins:
            return []
        
        plugin = self.plugins['producthunt']
        
        params = {
            "categories": ["artificial-intelligence", "developer-tools", "productivity"],
            "keywords": ["AI", "automation", "productivity", "developer", "tool"],
            "days_back": 7,
            "min_votes": 20,
            "max_products_per_day": limit
        }
        
        opportunities = []
        async for raw_data in plugin.fetch_data(params):
            opportunity = {
                "title": raw_data.title,
                "description": raw_data.content,
                "source": "Product Hunt",
                "url": raw_data.source_url,
                "votes": raw_data.upvotes,
                "comments": raw_data.comments_count,
                "topics": raw_data.metadata.get('topics', []),
                "engagement_score": raw_data.metadata.get('engagement_score', 0),
                "signal_type": "product_launch",
                "created_at": raw_data.extracted_at.isoformat()
            }
            opportunities.append(opportunity)
            
            if len(opportunities) >= limit:
                break
        
        return opportunities
    
    async def shutdown(self):
        """Shutdown all plugins."""
        for plugin in self.plugins.values():
            try:
                await plugin.shutdown()
            except Exception as e:
                print(f"Error shutting down plugin: {e}")


# Global instance
data_bridge = RealTimeDataBridge()


# Async helper functions for the AI agents
async def get_trending_market_data(limit: int = 10) -> List[Dict[str, Any]]:
    """Get trending market data for AI agents."""
    return await data_bridge.get_trending_topics(limit)


async def get_market_signals_by_keywords(keywords: List[str], limit: int = 20) -> List[Dict[str, Any]]:
    """Get market signals based on keywords for AI agents."""
    return await data_bridge.get_market_signals(keywords, limit)


async def get_startup_validation_data(limit: int = 15) -> List[Dict[str, Any]]:
    """Get startup validation data for AI agents."""
    return await data_bridge.get_startup_opportunities(limit)


# Test function
async def test_data_bridge():
    """Test the data bridge functionality."""
    print("🧪 Testing Real-Time Data Bridge...")
    
    # Initialize
    success = await data_bridge.initialize()
    if not success:
        print("❌ Data bridge initialization failed")
        return
    
    # Test trending topics
    print("\n📈 Testing trending topics...")
    trends = await data_bridge.get_trending_topics(5)
    for i, trend in enumerate(trends, 1):
        print(f"{i}. {trend['title'][:60]}... [{trend['source']}]")
    
    # Test market signals
    print("\n🔍 Testing market signals...")
    signals = await data_bridge.get_market_signals(["AI", "automation"], 3)
    for i, signal in enumerate(signals, 1):
        print(f"{i}. {signal['title'][:60]}... [{signal['source']}]")
    
    # Test startup opportunities
    print("\n🚀 Testing startup opportunities...")
    opportunities = await data_bridge.get_startup_opportunities(3)
    for i, opp in enumerate(opportunities, 1):
        print(f"{i}. {opp['title'][:60]}... [{opp['source']}]")
    
    await data_bridge.shutdown()
    print("\n✅ Data bridge test completed!")


if __name__ == "__main__":
    asyncio.run(test_data_bridge())