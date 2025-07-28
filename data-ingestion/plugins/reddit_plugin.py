"""Reddit data source plugin for market signal extraction."""

import asyncio
import aiohttp
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncIterator
from urllib.parse import urlencode
from pydantic import BaseModel

from .base import (
    DataSourcePlugin,
    PluginMetadata,
    PluginConfig,
    PluginStatus,
    RawData,
    DataSourceType,
    PluginError,
    PluginAuthError,
    PluginRateLimitError,
    PluginNetworkError
)


class RedditConfig(PluginConfig):
    """Reddit-specific configuration."""
    client_id: str
    client_secret: str
    user_agent: str
    subreddits: List[str] = [
        "MachineLearning", "artificial", "ArtificialIntelligence", 
        "deeplearning", "compsci", "programming", "startups",
        "entrepreneur", "SaaS", "webdev", "datascience"
    ]
    keywords: List[str] = [
        "AI", "machine learning", "automation", "pain point",
        "frustrating", "time consuming", "manual process",
        "wish there was", "need a tool", "looking for solution"
    ]
    max_posts_per_subreddit: int = 100
    time_filter: str = "week"  # hour, day, week, month, year, all
    sort_by: str = "hot"  # hot, new, top, rising


class RedditPost(BaseModel):
    """Reddit post data structure."""
    id: str
    title: str
    selftext: str
    author: str
    subreddit: str
    score: int
    upvote_ratio: float
    num_comments: int
    created_utc: float
    url: str
    permalink: str
    is_self: bool
    over_18: bool
    stickied: bool
    locked: bool


class RedditComment(BaseModel):
    """Reddit comment data structure."""
    id: str
    body: str
    author: str
    score: int
    created_utc: float
    parent_id: str
    link_id: str
    subreddit: str
    permalink: str


class RedditPlugin(DataSourcePlugin):
    """Reddit data source plugin for extracting market signals."""
    
    def __init__(self, config: RedditConfig):
        super().__init__(config)
        self.reddit_config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._base_url = "https://oauth.reddit.com"
        self._auth_url = "https://www.reddit.com/api/v1/access_token"
    
    async def initialize(self) -> None:
        """Initialize Reddit API connection and authentication."""
        try:
            # Create HTTP session
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                headers={"User-Agent": self.reddit_config.user_agent}
            )
            
            # Authenticate with Reddit API
            await self._authenticate()
            
            await self.set_status(PluginStatus.ACTIVE)
            
        except Exception as e:
            await self.set_status(PluginStatus.ERROR, f"Initialization failed: {e}")
            raise PluginError(f"Failed to initialize Reddit plugin: {e}")
    
    async def shutdown(self) -> None:
        """Clean shutdown of Reddit plugin."""
        if self._session:
            await self._session.close()
        await self.set_status(PluginStatus.INACTIVE)
    
    async def health_check(self) -> bool:
        """Check Reddit API connectivity and authentication."""
        try:
            if not self._session or not self._access_token:
                return False
            
            # Check if token is still valid
            if self._token_expires_at and datetime.now() >= self._token_expires_at:
                await self._authenticate()
            
            # Test API call
            url = f"{self._base_url}/api/v1/me"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            
            async with self._session.get(url, headers=headers) as response:
                return response.status == 200
                
        except Exception:
            return False
    
    async def fetch_data(self, params: Dict[str, Any]) -> AsyncIterator[RawData]:
        """Fetch data from Reddit based on parameters."""
        if not await self._check_rate_limit():
            raise PluginRateLimitError("Rate limit exceeded")
        
        try:
            # Extract parameters
            subreddits = params.get("subreddits", self.reddit_config.subreddits)
            keywords = params.get("keywords", self.reddit_config.keywords)
            max_posts = params.get("max_posts", self.reddit_config.max_posts_per_subreddit)
            time_filter = params.get("time_filter", self.reddit_config.time_filter)
            sort_by = params.get("sort_by", self.reddit_config.sort_by)
            
            # Fetch from each subreddit
            for subreddit in subreddits:
                async for raw_data in self._fetch_subreddit_data(
                    subreddit, keywords, max_posts, time_filter, sort_by
                ):
                    await self._increment_request_count()
                    yield raw_data
                    
        except Exception as e:
            await self.set_status(PluginStatus.ERROR, f"Data fetching failed: {e}")
            raise PluginError(f"Failed to fetch Reddit data: {e}")
    
    def get_metadata(self) -> PluginMetadata:
        """Return Reddit plugin metadata."""
        return PluginMetadata(
            name="reddit_plugin",
            version="1.0.0",
            description="Reddit data source plugin for market signal extraction",
            author="AI Opportunity Browser",
            source_type=DataSourceType.REDDIT,
            supported_signal_types=[
                "pain_point", "feature_request", "complaint", 
                "opportunity", "trend", "discussion"
            ],
            rate_limit_per_hour=self.config.rate_limit_per_hour,
            requires_auth=True,
            config_schema={
                "client_id": {"type": "string", "required": True},
                "client_secret": {"type": "string", "required": True},
                "user_agent": {"type": "string", "required": True},
                "subreddits": {"type": "array", "items": {"type": "string"}},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "max_posts_per_subreddit": {"type": "integer", "minimum": 1, "maximum": 1000},
                "time_filter": {"type": "string", "enum": ["hour", "day", "week", "month", "year", "all"]},
                "sort_by": {"type": "string", "enum": ["hot", "new", "top", "rising"]}
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Reddit plugin configuration."""
        required_fields = ["client_id", "client_secret", "user_agent"]
        
        for field in required_fields:
            if field not in config or not config[field]:
                return False
        
        # Validate optional fields
        if "subreddits" in config and not isinstance(config["subreddits"], list):
            return False
        
        if "keywords" in config and not isinstance(config["keywords"], list):
            return False
        
        if "max_posts_per_subreddit" in config:
            max_posts = config["max_posts_per_subreddit"]
            if not isinstance(max_posts, int) or max_posts < 1 or max_posts > 1000:
                return False
        
        return True
    
    async def _authenticate(self) -> None:
        """Authenticate with Reddit API using OAuth2."""
        if not self._session:
            raise PluginAuthError("HTTP session not initialized")
        
        auth_data = {
            "grant_type": "client_credentials"
        }
        
        auth = aiohttp.BasicAuth(
            self.reddit_config.client_id,
            self.reddit_config.client_secret
        )
        
        try:
            async with self._session.post(
                self._auth_url,
                data=auth_data,
                auth=auth
            ) as response:
                if response.status != 200:
                    raise PluginAuthError(f"Authentication failed: {response.status}")
                
                auth_response = await response.json()
                self._access_token = auth_response["access_token"]
                expires_in = auth_response.get("expires_in", 3600)
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
                
        except aiohttp.ClientError as e:
            raise PluginNetworkError(f"Network error during authentication: {e}")
    
    async def _fetch_subreddit_data(
        self,
        subreddit: str,
        keywords: List[str],
        max_posts: int,
        time_filter: str,
        sort_by: str
    ) -> AsyncIterator[RawData]:
        """Fetch data from a specific subreddit."""
        if not self._access_token:
            await self._authenticate()
        
        # Build URL for subreddit posts
        url = f"{self._base_url}/r/{subreddit}/{sort_by}"
        params = {
            "limit": min(max_posts, 100),  # Reddit API limit
        }
        
        # Only add time filter parameter if needed
        if sort_by == "top":
            params["t"] = time_filter
        
        headers = {"Authorization": f"Bearer {self._access_token}"}
        
        try:
            async with self._session.get(url, headers=headers, params=params) as response:
                if response.status == 429:
                    raise PluginRateLimitError("Reddit API rate limit exceeded")
                elif response.status != 200:
                    raise PluginNetworkError(f"Reddit API error: {response.status}")
                
                data = await response.json()
                posts = data.get("data", {}).get("children", [])
                
                for post_data in posts:
                    post = post_data.get("data", {})
                    
                    # Convert to RedditPost for easier handling
                    reddit_post = RedditPost(
                        id=post.get("id", ""),
                        title=post.get("title", ""),
                        selftext=post.get("selftext", ""),
                        author=post.get("author", ""),
                        subreddit=post.get("subreddit", ""),
                        score=post.get("score", 0),
                        upvote_ratio=post.get("upvote_ratio", 0.0),
                        num_comments=post.get("num_comments", 0),
                        created_utc=post.get("created_utc", 0),
                        url=post.get("url", ""),
                        permalink=post.get("permalink", ""),
                        is_self=post.get("is_self", False),
                        over_18=post.get("over_18", False),
                        stickied=post.get("stickied", False),
                        locked=post.get("locked", False)
                    )
                    
                    # Filter and normalize the post
                    raw_data = await self._normalize_post_data(reddit_post, keywords)
                    if raw_data:
                        yield raw_data
                        
        except aiohttp.ClientError as e:
            raise PluginNetworkError(f"Network error fetching subreddit data: {e}")
    
    async def _normalize_post_data(self, post: RedditPost, keywords: List[str]) -> Optional[RawData]:
        """Normalize Reddit post data into RawData format."""
        # Skip stickied, locked, or NSFW posts
        if post.stickied or post.locked or post.over_18:
            return None
        
        # Combine title and content for analysis
        full_content = f"{post.title}\n\n{post.selftext}".strip()
        
        # Check if content contains relevant keywords
        if not self._contains_keywords(full_content, keywords):
            return None
        
        # Determine signal type based on content analysis
        signal_type = self._classify_signal_type(full_content)
        
        # Calculate engagement score
        engagement_score = self._calculate_engagement_score(post)
        
        return RawData(
            source="reddit",
            source_id=post.id,
            source_url=f"https://reddit.com{post.permalink}",
            title=post.title,
            content=self._clean_content(full_content),
            raw_content=full_content,
            author=post.author,
            author_reputation=None,  # Reddit doesn't provide user karma in post data
            upvotes=max(0, int(post.score * post.upvote_ratio)) if post.upvote_ratio > 0 else post.score,
            downvotes=max(0, post.score - int(post.score * post.upvote_ratio)) if post.upvote_ratio > 0 else 0,
            comments_count=post.num_comments,
            shares_count=0,  # Reddit doesn't track shares
            views_count=0,   # Reddit doesn't provide view counts
            extracted_at=datetime.now(),
            metadata={
                "subreddit": post.subreddit,
                "signal_type": signal_type,
                "engagement_score": engagement_score,
                "upvote_ratio": post.upvote_ratio,
                "is_self_post": post.is_self,
                "created_utc": post.created_utc,
                "reddit_url": post.url if not post.is_self else f"https://reddit.com{post.permalink}"
            }
        )
    
    def _contains_keywords(self, content: str, keywords: List[str]) -> bool:
        """Check if content contains any of the specified keywords."""
        content_lower = content.lower()
        return any(keyword.lower() in content_lower for keyword in keywords)
    
    def _classify_signal_type(self, content: str) -> str:
        """Classify the type of market signal based on content."""
        content_lower = content.lower()
        
        # Pain point indicators
        pain_indicators = [
            "frustrating", "annoying", "hate", "terrible", "awful",
            "pain point", "problem", "issue", "struggle", "difficult"
        ]
        
        # Feature request indicators
        feature_indicators = [
            "wish", "want", "need", "should have", "would be nice",
            "feature request", "suggestion", "idea", "proposal"
        ]
        
        # Complaint indicators
        complaint_indicators = [
            "complaint", "complain", "disappointed", "unsatisfied",
            "doesn't work", "broken", "bug", "error"
        ]
        
        # Opportunity indicators
        opportunity_indicators = [
            "opportunity", "market", "business idea", "startup idea",
            "gap in market", "untapped", "potential"
        ]
        
        if any(indicator in content_lower for indicator in pain_indicators):
            return "pain_point"
        elif any(indicator in content_lower for indicator in feature_indicators):
            return "feature_request"
        elif any(indicator in content_lower for indicator in complaint_indicators):
            return "complaint"
        elif any(indicator in content_lower for indicator in opportunity_indicators):
            return "opportunity"
        else:
            return "discussion"
    
    def _calculate_engagement_score(self, post: RedditPost) -> float:
        """Calculate engagement score based on Reddit metrics."""
        # Normalize score based on subreddit activity
        base_score = max(0, post.score)
        comment_weight = post.num_comments * 2
        ratio_weight = post.upvote_ratio * 10
        
        # Time decay factor (newer posts get slight boost)
        time_factor = 1.0
        post_age_hours = (datetime.now().timestamp() - post.created_utc) / 3600
        if post_age_hours < 24:
            time_factor = 1.2
        elif post_age_hours < 168:  # 1 week
            time_factor = 1.1
        
        return (base_score + comment_weight + ratio_weight) * time_factor
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content text."""
        # Remove Reddit markdown
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Bold
        content = re.sub(r'\*(.*?)\*', r'\1', content)      # Italic
        content = re.sub(r'~~(.*?)~~', r'\1', content)      # Strikethrough
        content = re.sub(r'\^(\w+)', r'\1', content)        # Superscript
        
        # Remove Reddit-specific formatting
        content = re.sub(r'/u/\w+', '', content)            # User mentions
        content = re.sub(r'/r/\w+', '', content)            # Subreddit mentions
        content = re.sub(r'&gt;.*?\n', '', content)         # Quotes
        
        # Clean up whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)       # Multiple newlines
        content = re.sub(r' +', ' ', content)               # Multiple spaces
        
        return content.strip()