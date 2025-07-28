"""Product Hunt data source plugin for market signal extraction."""

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
    PluginAuthError,
    PluginRateLimitError,
    PluginNetworkError
)


class ProductHuntConfig(PluginConfig):
    """Product Hunt-specific configuration."""
    access_token: str
    categories: List[str] = [
        "artificial-intelligence", "developer-tools", "productivity", 
        "saas", "tech", "automation", "analytics", "design-tools"
    ]
    keywords: List[str] = [
        "AI", "machine learning", "automation", "productivity", "tool",
        "platform", "solution", "software", "app", "startup", "SaaS"
    ]
    days_back: int = 7  # How many days back to fetch
    min_votes: int = 10
    include_comments: bool = True
    max_products_per_day: int = 50


class ProductHuntProduct(BaseModel):
    """Product Hunt product data structure."""
    id: int
    name: str
    tagline: str
    description: Optional[str] = None
    votes_count: int
    comments_count: int
    featured_at: str
    created_at: str
    product_url: str
    redirect_url: str
    screenshot_url: Optional[str] = None
    maker_inside: bool
    exclusive: bool
    category_id: Optional[int] = None
    topics: List[str] = []


class ProductHuntComment(BaseModel):
    """Product Hunt comment data structure."""
    id: int
    body: str
    votes_count: int
    created_at: str
    user_name: str
    product_id: int


class ProductHuntPlugin(DataSourcePlugin):
    """Product Hunt data source plugin for extracting market signals."""
    
    def __init__(self, config: ProductHuntConfig):
        super().__init__(config)
        self.ph_config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url = "https://api.producthunt.com/v2/api/graphql"
        self._access_token = config.access_token
    
    async def initialize(self) -> None:
        """Initialize Product Hunt API connection."""
        try:
            # Create HTTP session with auth headers
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
                "User-Agent": "AI-Opportunity-Browser/1.0"
            }
            
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                headers=headers
            )
            
            # Test authentication
            await self._test_auth()
            
            await self.set_status(PluginStatus.ACTIVE)
            
        except Exception as e:
            await self.set_status(PluginStatus.ERROR, f"Initialization failed: {e}")
            raise PluginError(f"Failed to initialize Product Hunt plugin: {e}")
    
    async def shutdown(self) -> None:
        """Clean shutdown of Product Hunt plugin."""
        if self._session:
            await self._session.close()
        await self.set_status(PluginStatus.INACTIVE)
    
    async def health_check(self) -> bool:
        """Check Product Hunt API connectivity."""
        try:
            if not self._session:
                return False
            
            return await self._test_auth()
                
        except Exception:
            return False
    
    async def fetch_data(self, params: Dict[str, Any]) -> AsyncIterator[RawData]:
        """Fetch data from Product Hunt based on parameters."""
        if not await self._check_rate_limit():
            raise PluginRateLimitError("Rate limit exceeded")
        
        try:
            # Extract parameters
            categories = params.get("categories", self.ph_config.categories)
            keywords = params.get("keywords", self.ph_config.keywords)
            days_back = params.get("days_back", self.ph_config.days_back)
            min_votes = params.get("min_votes", self.ph_config.min_votes)
            include_comments = params.get("include_comments", self.ph_config.include_comments)
            max_products = params.get("max_products_per_day", self.ph_config.max_products_per_day)
            
            # Fetch products from recent days
            for day_offset in range(days_back):
                target_date = datetime.now() - timedelta(days=day_offset)
                
                async for raw_data in self._fetch_daily_products(
                    target_date, categories, keywords, min_votes, include_comments, max_products
                ):
                    await self._increment_request_count()
                    yield raw_data
                    
        except Exception as e:
            await self.set_status(PluginStatus.ERROR, f"Data fetching failed: {e}")
            raise PluginError(f"Failed to fetch Product Hunt data: {e}")
    
    def get_metadata(self) -> PluginMetadata:
        """Return Product Hunt plugin metadata."""
        return PluginMetadata(
            name="producthunt_plugin",
            version="1.0.0",
            description="Product Hunt data source plugin for market signal extraction",
            author="AI Opportunity Browser",
            source_type="PRODUCTHUNT",  # Add to enum if needed
            supported_signal_types=[
                "product_launch", "market_validation", "competitor_analysis",
                "trend", "innovation", "startup_idea"
            ],
            rate_limit_per_hour=self.config.rate_limit_per_hour,
            requires_auth=True,
            config_schema={
                "access_token": {"type": "string", "required": True},
                "categories": {"type": "array", "items": {"type": "string"}},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "days_back": {"type": "integer", "minimum": 1, "maximum": 30},
                "min_votes": {"type": "integer", "minimum": 0},
                "include_comments": {"type": "boolean"},
                "max_products_per_day": {"type": "integer", "minimum": 1, "maximum": 200}
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Product Hunt plugin configuration."""
        if "access_token" not in config or not config["access_token"]:
            return False
        
        # Validate optional fields
        if "days_back" in config:
            days_back = config["days_back"]
            if not isinstance(days_back, int) or days_back < 1 or days_back > 30:
                return False
        
        return True
    
    async def _test_auth(self) -> bool:
        """Test Product Hunt API authentication."""
        query = """
        query {
            viewer {
                user {
                    id
                    name
                }
            }
        }
        """
        
        try:
            async with self._session.post(
                self._base_url,
                json={"query": query}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return "errors" not in data
                return False
                
        except Exception:
            return False
    
    async def _fetch_daily_products(
        self,
        target_date: datetime,
        categories: List[str],
        keywords: List[str],
        min_votes: int,
        include_comments: bool,
        max_products: int
    ) -> AsyncIterator[RawData]:
        """Fetch products for a specific day."""
        
        date_str = target_date.strftime("%Y-%m-%d")
        
        # GraphQL query to get products for a specific day
        query = f"""
        query {{
            posts(postedAfter: "{date_str}", postedBefore: "{date_str}", first: {max_products}) {{
                edges {{
                    node {{
                        id
                        name
                        tagline
                        description
                        votesCount
                        commentsCount
                        featuredAt
                        createdAt
                        url
                        redirectUrl
                        thumbnail {{
                            url
                        }}
                        makerInside
                        exclusive
                        topics(first: 10) {{
                            edges {{
                                node {{
                                    name
                                }}
                            }}
                        }}
                        comments(first: 20) {{
                            edges {{
                                node {{
                                    id
                                    body
                                    votesCount
                                    createdAt
                                    user {{
                                        name
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """
        
        try:
            async with self._session.post(
                self._base_url,
                json={"query": query}
            ) as response:
                if response.status == 429:
                    raise PluginRateLimitError("Product Hunt API rate limit exceeded")
                elif response.status != 200:
                    raise PluginNetworkError(f"Product Hunt API error: {response.status}")
                
                data = await response.json()
                
                if "errors" in data:
                    raise PluginError(f"GraphQL errors: {data['errors']}")
                
                posts = data.get("data", {}).get("posts", {}).get("edges", [])
                
                for post_edge in posts:
                    post_data = post_edge.get("node", {})
                    
                    # Convert to ProductHuntProduct
                    product = ProductHuntProduct(
                        id=int(post_data.get("id", 0)),
                        name=post_data.get("name", ""),
                        tagline=post_data.get("tagline", ""),
                        description=post_data.get("description"),
                        votes_count=post_data.get("votesCount", 0),
                        comments_count=post_data.get("commentsCount", 0),
                        featured_at=post_data.get("featuredAt", ""),
                        created_at=post_data.get("createdAt", ""),
                        product_url=post_data.get("url", ""),
                        redirect_url=post_data.get("redirectUrl", ""),
                        screenshot_url=post_data.get("thumbnail", {}).get("url"),
                        maker_inside=post_data.get("makerInside", False),
                        exclusive=post_data.get("exclusive", False),
                        topics=[
                            topic["node"]["name"] 
                            for topic in post_data.get("topics", {}).get("edges", [])
                        ]
                    )
                    
                    # Apply filters
                    if product.votes_count < min_votes:
                        continue
                    
                    # Normalize product data
                    raw_data = await self._normalize_product_data(product, keywords)
                    if raw_data:
                        yield raw_data
                    
                    # Process comments if enabled
                    if include_comments:
                        comments = post_data.get("comments", {}).get("edges", [])
                        for comment_edge in comments:
                            comment_data = comment_edge.get("node", {})
                            comment_raw = await self._normalize_comment_data(
                                comment_data, product, keywords
                            )
                            if comment_raw:
                                yield comment_raw
                        
        except aiohttp.ClientError as e:
            raise PluginNetworkError(f"Network error fetching Product Hunt data: {e}")
    
    async def _normalize_product_data(
        self, 
        product: ProductHuntProduct, 
        keywords: List[str]
    ) -> Optional[RawData]:
        """Normalize Product Hunt product data into RawData format."""
        
        # Combine name, tagline, and description for analysis
        full_content = f"{product.name}\n{product.tagline}"
        if product.description:
            full_content += f"\n\n{product.description}"
        
        # Check if content contains relevant keywords or topics
        relevant = (
            self._contains_keywords(full_content, keywords) or
            self._contains_keywords(" ".join(product.topics), keywords)
        )
        
        if not relevant:
            return None
        
        # Determine signal type
        signal_type = self._classify_signal_type(full_content, product.topics)
        
        # Calculate engagement score
        engagement_score = self._calculate_engagement_score(product)
        
        return RawData(
            source="producthunt",
            source_id=str(product.id),
            source_url=product.product_url,
            title=product.name,
            content=self._clean_content(full_content),
            raw_content=full_content,
            author="Product Hunt",  # PH doesn't expose maker names in API
            author_reputation=None,
            upvotes=product.votes_count,
            downvotes=0,  # PH doesn't have downvotes
            comments_count=product.comments_count,
            shares_count=0,  # PH doesn't track shares
            views_count=0,   # PH doesn't provide view counts
            extracted_at=datetime.now(),
            metadata={
                "signal_type": signal_type,
                "engagement_score": engagement_score,
                "tagline": product.tagline,
                "topics": product.topics,
                "maker_inside": product.maker_inside,
                "exclusive": product.exclusive,
                "featured_at": product.featured_at,
                "redirect_url": product.redirect_url,
                "screenshot_url": product.screenshot_url
            }
        )
    
    async def _normalize_comment_data(
        self,
        comment_data: Dict[str, Any],
        product: ProductHuntProduct,
        keywords: List[str]
    ) -> Optional[RawData]:
        """Normalize Product Hunt comment data into RawData format."""
        
        comment_body = comment_data.get("body", "")
        if not comment_body:
            return None
        
        # Check if comment contains relevant keywords
        if not self._contains_keywords(comment_body, keywords):
            return None
        
        # Determine signal type
        signal_type = self._classify_comment_signal_type(comment_body)
        
        user_name = comment_data.get("user", {}).get("name", "unknown")
        
        return RawData(
            source="producthunt",
            source_id=f"{product.id}_{comment_data.get('id', 0)}",
            source_url=f"{product.product_url}#comment-{comment_data.get('id', 0)}",
            title=f"Comment on: {product.name}",
            content=self._clean_content(comment_body),
            raw_content=comment_body,
            author=user_name,
            author_reputation=None,
            upvotes=comment_data.get("votesCount", 0),
            downvotes=0,
            comments_count=0,
            shares_count=0,
            views_count=0,
            extracted_at=datetime.now(),
            metadata={
                "signal_type": signal_type,
                "parent_product_id": product.id,
                "parent_product_name": product.name,
                "comment_created_at": comment_data.get("createdAt", "")
            }
        )
    
    def _contains_keywords(self, content: str, keywords: List[str]) -> bool:
        """Check if content contains any of the specified keywords."""
        content_lower = content.lower()
        return any(keyword.lower() in content_lower for keyword in keywords)
    
    def _classify_signal_type(self, content: str, topics: List[str]) -> str:
        """Classify the type of market signal based on content and topics."""
        content_lower = content.lower()
        topics_lower = [topic.lower() for topic in topics]
        
        # AI/ML detection
        ai_indicators = ["ai", "artificial intelligence", "machine learning", "automation", "ml"]
        if any(indicator in content_lower for indicator in ai_indicators) or \
           any(indicator in " ".join(topics_lower) for indicator in ai_indicators):
            return "ai_innovation"
        
        # Product launch detection (default for PH)
        launch_indicators = ["launch", "new", "introducing", "announcing", "built", "created"]
        if any(indicator in content_lower for indicator in launch_indicators):
            return "product_launch"
        
        # Market validation signals
        validation_indicators = ["problem", "solution", "need", "pain point", "frustration"]
        if any(indicator in content_lower for indicator in validation_indicators):
            return "market_validation"
        
        # Innovation/trend detection
        innovation_indicators = ["innovative", "revolutionary", "breakthrough", "cutting-edge", "novel"]
        if any(indicator in content_lower for indicator in innovation_indicators):
            return "innovation"
        
        return "product_launch"  # Default for Product Hunt
    
    def _classify_comment_signal_type(self, content: str) -> str:
        """Classify signal type for comments."""
        content_lower = content.lower()
        
        # Feature request/feedback
        feedback_indicators = ["feature", "suggestion", "improvement", "would be nice", "wish"]
        if any(indicator in content_lower for indicator in feedback_indicators):
            return "feature_request"
        
        # Pain point/problem
        pain_indicators = ["problem", "issue", "difficult", "frustrating", "pain point"]
        if any(indicator in content_lower for indicator in pain_indicators):
            return "pain_point"
        
        # Competitor analysis
        competitor_indicators = ["similar to", "like", "competitor", "alternative", "versus"]
        if any(indicator in content_lower for indicator in competitor_indicators):
            return "competitor_analysis"
        
        return "discussion"  # Default
    
    def _calculate_engagement_score(self, product: ProductHuntProduct) -> float:
        """Calculate engagement score based on Product Hunt metrics."""
        base_score = product.votes_count
        comment_weight = product.comments_count * 2
        
        # Maker inside and exclusive boost
        maker_boost = 5 if product.maker_inside else 0
        exclusive_boost = 3 if product.exclusive else 0
        
        # Time decay factor
        time_factor = 1.0
        try:
            created_date = datetime.fromisoformat(product.created_at.replace('Z', '+00:00'))
            age_hours = (datetime.now().timestamp() - created_date.timestamp()) / 3600
            if age_hours < 24:
                time_factor = 1.3
            elif age_hours < 168:  # 1 week
                time_factor = 1.2
        except:
            pass  # Use default time_factor if date parsing fails
        
        return (base_score + comment_weight + maker_boost + exclusive_boost) * time_factor
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content text."""
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Convert HTML entities
        content = content.replace('&gt;', '>').replace('&lt;', '<')
        content = content.replace('&quot;', '"').replace('&amp;', '&')
        
        # Clean up whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = re.sub(r' +', ' ', content)
        
        return content.strip()