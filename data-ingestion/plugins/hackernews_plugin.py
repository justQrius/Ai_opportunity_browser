"""Hacker News data source plugin for market signal extraction."""

import asyncio
import aiohttp
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncIterator
from pydantic import BaseModel

from .base import (
    DataSourcePlugin,
    PluginMetadata,
    PluginConfig,
    PluginStatus,
    RawData,
    DataSourceType,
    PluginError,
    PluginRateLimitError,
    PluginNetworkError
)


class HackerNewsConfig(PluginConfig):
    """Hacker News-specific configuration."""
    keywords: List[str] = [
        "AI", "machine learning", "automation", "startup", "pain point",
        "frustrating", "time consuming", "manual process", "wish there was",
        "need a tool", "looking for solution", "business idea", "opportunity"
    ]
    story_types: List[str] = ["top", "new", "best", "ask", "show", "job"]
    max_stories: int = 500
    min_score: int = 10
    max_age_hours: int = 168  # 1 week
    include_comments: bool = True
    max_comments_per_story: int = 50


class HackerNewsStory(BaseModel):
    """Hacker News story data structure."""
    id: int
    title: str
    url: Optional[str] = None
    text: Optional[str] = None
    by: str
    score: int
    descendants: Optional[int] = 0  # comment count
    time: int
    type: str
    kids: List[int] = []


class HackerNewsComment(BaseModel):
    """Hacker News comment data structure."""
    id: int
    text: Optional[str] = None
    by: Optional[str] = None
    parent: int
    time: int
    kids: List[int] = []


class HackerNewsPlugin(DataSourcePlugin):
    """Hacker News data source plugin for extracting market signals."""
    
    def __init__(self, config: HackerNewsConfig):
        super().__init__(config)
        self.hn_config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url = "https://hacker-news.firebaseio.com/v0"
        # HN API is public and doesn't require authentication
    
    async def initialize(self) -> None:
        """Initialize Hacker News API connection."""
        try:
            # Create HTTP session
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                headers={"User-Agent": "AI-Opportunity-Browser/1.0"}
            )
            
            await self.set_status(PluginStatus.ACTIVE)
            
        except Exception as e:
            await self.set_status(PluginStatus.ERROR, f"Initialization failed: {e}")
            raise PluginError(f"Failed to initialize Hacker News plugin: {e}")
    
    async def shutdown(self) -> None:
        """Clean shutdown of Hacker News plugin."""
        if self._session:
            await self._session.close()
        await self.set_status(PluginStatus.INACTIVE)
    
    async def health_check(self) -> bool:
        """Check Hacker News API connectivity."""
        try:
            if not self._session:
                return False
            
            # Test API call to get top stories
            url = f"{self._base_url}/topstories.json"
            async with self._session.get(url) as response:
                return response.status == 200
                
        except Exception:
            return False
    
    async def fetch_data(self, params: Dict[str, Any]) -> AsyncIterator[RawData]:
        """Fetch data from Hacker News based on parameters."""
        if not await self._check_rate_limit():
            raise PluginRateLimitError("Rate limit exceeded")
        
        try:
            # Extract parameters
            story_types = params.get("story_types", self.hn_config.story_types)
            keywords = params.get("keywords", self.hn_config.keywords)
            max_stories = params.get("max_stories", self.hn_config.max_stories)
            min_score = params.get("min_score", self.hn_config.min_score)
            max_age_hours = params.get("max_age_hours", self.hn_config.max_age_hours)
            include_comments = params.get("include_comments", self.hn_config.include_comments)
            
            # Fetch from each story type
            for story_type in story_types:
                async for raw_data in self._fetch_stories_by_type(
                    story_type, keywords, max_stories, min_score, max_age_hours, include_comments
                ):
                    await self._increment_request_count()
                    yield raw_data
                    
        except Exception as e:
            await self.set_status(PluginStatus.ERROR, f"Data fetching failed: {e}")
            raise PluginError(f"Failed to fetch Hacker News data: {e}")
    
    def get_metadata(self) -> PluginMetadata:
        """Return Hacker News plugin metadata."""
        return PluginMetadata(
            name="hackernews_plugin",
            version="1.0.0",
            description="Hacker News data source plugin for market signal extraction",
            author="AI Opportunity Browser",
            source_type=DataSourceType.HACKERNEWS,
            supported_signal_types=[
                "pain_point", "startup_idea", "complaint", 
                "opportunity", "trend", "discussion", "job_posting"
            ],
            rate_limit_per_hour=self.config.rate_limit_per_hour,
            requires_auth=False,
            config_schema={
                "keywords": {"type": "array", "items": {"type": "string"}},
                "story_types": {"type": "array", "items": {"type": "string"}},
                "max_stories": {"type": "integer", "minimum": 1, "maximum": 1000},
                "min_score": {"type": "integer", "minimum": 0},
                "max_age_hours": {"type": "integer", "minimum": 1},
                "include_comments": {"type": "boolean"},
                "max_comments_per_story": {"type": "integer", "minimum": 0, "maximum": 500}
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Hacker News plugin configuration."""
        # No required fields for HN since it's public API
        
        # Validate optional fields
        if "keywords" in config and not isinstance(config["keywords"], list):
            return False
        
        if "story_types" in config:
            valid_types = ["top", "new", "best", "ask", "show", "job"]
            if not all(t in valid_types for t in config["story_types"]):
                return False
        
        if "max_stories" in config:
            max_stories = config["max_stories"]
            if not isinstance(max_stories, int) or max_stories < 1 or max_stories > 1000:
                return False
        
        return True
    
    async def _fetch_stories_by_type(
        self,
        story_type: str,
        keywords: List[str],
        max_stories: int,
        min_score: int,
        max_age_hours: int,
        include_comments: bool
    ) -> AsyncIterator[RawData]:
        """Fetch stories of a specific type from Hacker News."""
        
        # Get story IDs
        url = f"{self._base_url}/{story_type}stories.json"
        
        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    raise PluginNetworkError(f"HN API error: {response.status}")
                
                story_ids = await response.json()
                
                # Process stories in batches to avoid overwhelming the API
                batch_size = 20
                processed_count = 0
                
                for i in range(0, min(len(story_ids), max_stories), batch_size):
                    batch_ids = story_ids[i:i + batch_size]
                    
                    # Fetch story details concurrently
                    tasks = [self._fetch_story_details(story_id) for story_id in batch_ids]
                    stories = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for story in stories:
                        if isinstance(story, Exception):
                            continue
                        
                        if not story:
                            continue
                        
                        # Apply filters
                        if story.score < min_score:
                            continue
                        
                        # Check age
                        story_age = (datetime.now().timestamp() - story.time) / 3600
                        if story_age > max_age_hours:
                            continue
                        
                        # Convert to RawData
                        raw_data = await self._normalize_story_data(story, keywords)
                        if raw_data:
                            yield raw_data
                            processed_count += 1
                            
                            # If comments are enabled, fetch them too
                            if include_comments and story.kids:
                                async for comment_data in self._fetch_story_comments(
                                    story, keywords, self.hn_config.max_comments_per_story
                                ):
                                    yield comment_data
                        
                        if processed_count >= max_stories:
                            return
                    
                    # Small delay between batches to be respectful
                    await asyncio.sleep(0.1)
                        
        except aiohttp.ClientError as e:
            raise PluginNetworkError(f"Network error fetching stories: {e}")
    
    async def _fetch_story_details(self, story_id: int) -> Optional[HackerNewsStory]:
        """Fetch detailed information for a single story."""
        url = f"{self._base_url}/item/{story_id}.json"
        
        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                if not data or data.get("deleted") or data.get("dead"):
                    return None
                
                return HackerNewsStory(
                    id=data.get("id", story_id),
                    title=data.get("title", ""),
                    url=data.get("url"),
                    text=data.get("text"),
                    by=data.get("by", "unknown"),
                    score=data.get("score", 0),
                    descendants=data.get("descendants", 0),
                    time=data.get("time", 0),
                    type=data.get("type", "story"),
                    kids=data.get("kids", [])
                )
                
        except Exception:
            return None
    
    async def _fetch_story_comments(
        self, 
        story: HackerNewsStory, 
        keywords: List[str], 
        max_comments: int
    ) -> AsyncIterator[RawData]:
        """Fetch comments for a story that contain relevant keywords."""
        
        comment_count = 0
        
        # Process comments in batches
        batch_size = 10
        for i in range(0, min(len(story.kids), max_comments), batch_size):
            batch_ids = story.kids[i:i + batch_size]
            
            tasks = [self._fetch_comment_details(comment_id) for comment_id in batch_ids]
            comments = await asyncio.gather(*tasks, return_exceptions=True)
            
            for comment in comments:
                if isinstance(comment, Exception) or not comment:
                    continue
                
                # Convert to RawData if relevant
                raw_data = await self._normalize_comment_data(comment, story, keywords)
                if raw_data:
                    yield raw_data
                    comment_count += 1
                
                if comment_count >= max_comments:
                    return
    
    async def _fetch_comment_details(self, comment_id: int) -> Optional[HackerNewsComment]:
        """Fetch detailed information for a single comment."""
        url = f"{self._base_url}/item/{comment_id}.json"
        
        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                if not data or data.get("deleted") or data.get("dead"):
                    return None
                
                return HackerNewsComment(
                    id=data.get("id", comment_id),
                    text=data.get("text"),
                    by=data.get("by"),
                    parent=data.get("parent", 0),
                    time=data.get("time", 0),
                    kids=data.get("kids", [])
                )
                
        except Exception:
            return None
    
    async def _normalize_story_data(self, story: HackerNewsStory, keywords: List[str]) -> Optional[RawData]:
        """Normalize Hacker News story data into RawData format."""
        
        # Combine title and text for analysis
        full_content = f"{story.title}\n\n{story.text or ''}".strip()
        
        # Check if content contains relevant keywords
        if not self._contains_keywords(full_content, keywords):
            return None
        
        # Determine signal type based on content analysis
        signal_type = self._classify_signal_type(full_content, story.type)
        
        # Calculate engagement score
        engagement_score = self._calculate_engagement_score(story)
        
        return RawData(
            source="hackernews",
            source_id=str(story.id),
            source_url=f"https://news.ycombinator.com/item?id={story.id}",
            title=story.title,
            content=self._clean_content(full_content),
            raw_content=full_content,
            author=story.by,
            author_reputation=None,  # HN doesn't provide karma in API
            upvotes=story.score,
            downvotes=0,  # HN doesn't show downvotes
            comments_count=story.descendants or 0,
            shares_count=0,  # HN doesn't track shares
            views_count=0,   # HN doesn't provide view counts
            extracted_at=datetime.now(),
            metadata={
                "story_type": story.type,
                "signal_type": signal_type,
                "engagement_score": engagement_score,
                "hn_url": story.url,
                "created_time": story.time,
                "has_comments": len(story.kids) > 0
            }
        )
    
    async def _normalize_comment_data(
        self, 
        comment: HackerNewsComment, 
        story: HackerNewsStory, 
        keywords: List[str]
    ) -> Optional[RawData]:
        """Normalize Hacker News comment data into RawData format."""
        
        if not comment.text:
            return None
        
        # Check if comment contains relevant keywords
        if not self._contains_keywords(comment.text, keywords):
            return None
        
        # Determine signal type
        signal_type = self._classify_signal_type(comment.text, "comment")
        
        return RawData(
            source="hackernews",
            source_id=f"{story.id}_{comment.id}",
            source_url=f"https://news.ycombinator.com/item?id={comment.id}",
            title=f"Comment on: {story.title}",
            content=self._clean_content(comment.text),
            raw_content=comment.text,
            author=comment.by,
            author_reputation=None,
            upvotes=0,  # Comments don't have visible scores
            downvotes=0,
            comments_count=len(comment.kids),
            shares_count=0,
            views_count=0,
            extracted_at=datetime.now(),
            metadata={
                "story_type": "comment",
                "signal_type": signal_type,
                "parent_story_id": story.id,
                "parent_comment_id": comment.parent,
                "created_time": comment.time,
                "has_replies": len(comment.kids) > 0
            }
        )
    
    def _contains_keywords(self, content: str, keywords: List[str]) -> bool:
        """Check if content contains any of the specified keywords."""
        content_lower = content.lower()
        return any(keyword.lower() in content_lower for keyword in keywords)
    
    def _classify_signal_type(self, content: str, item_type: str) -> str:
        """Classify the type of market signal based on content."""
        content_lower = content.lower()
        
        # Job posting detection
        if item_type == "job" or any(indicator in content_lower for indicator in [
            "hiring", "job", "position", "career", "employment", "work at", "join our team"
        ]):
            return "job_posting"
        
        # Startup/Show HN detection
        if item_type in ["show", "ask"] or any(indicator in content_lower for indicator in [
            "show hn", "ask hn", "launch", "built", "created", "made", "startup"
        ]):
            return "startup_idea"
        
        # Pain point indicators
        pain_indicators = [
            "frustrating", "annoying", "hate", "terrible", "awful", "broken",
            "pain point", "problem", "issue", "struggle", "difficult", "impossible"
        ]
        
        # Opportunity indicators
        opportunity_indicators = [
            "opportunity", "market", "business idea", "startup idea", "need for",
            "gap in market", "untapped", "potential", "wish there was", "should exist"
        ]
        
        # Complaint indicators
        complaint_indicators = [
            "complaint", "complain", "disappointed", "unsatisfied",
            "doesn't work", "broken", "bug", "error", "horrible experience"
        ]
        
        if any(indicator in content_lower for indicator in pain_indicators):
            return "pain_point"
        elif any(indicator in content_lower for indicator in opportunity_indicators):
            return "opportunity"
        elif any(indicator in content_lower for indicator in complaint_indicators):
            return "complaint"
        else:
            return "discussion"
    
    def _calculate_engagement_score(self, story: HackerNewsStory) -> float:
        """Calculate engagement score based on HN metrics."""
        base_score = max(0, story.score)
        comment_weight = (story.descendants or 0) * 0.5
        
        # Time decay factor (newer posts get slight boost)
        time_factor = 1.0
        story_age_hours = (datetime.now().timestamp() - story.time) / 3600
        if story_age_hours < 24:
            time_factor = 1.2
        elif story_age_hours < 168:  # 1 week
            time_factor = 1.1
        
        return (base_score + comment_weight) * time_factor
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content text."""
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Convert HTML entities
        content = content.replace('&gt;', '>').replace('&lt;', '<')
        content = content.replace('&quot;', '"').replace('&amp;', '&')
        content = content.replace('&#x27;', "'").replace('&#x2F;', '/')
        
        # Clean up whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = re.sub(r' +', ' ', content)
        
        return content.strip()