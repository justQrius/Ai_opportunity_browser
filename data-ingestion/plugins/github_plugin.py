"""GitHub data source plugin for market signal extraction."""

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


class GitHubConfig(PluginConfig):
    """GitHub-specific configuration."""
    access_token: str
    repositories: List[str] = [
        "microsoft/vscode", "facebook/react", "tensorflow/tensorflow",
        "pytorch/pytorch", "huggingface/transformers", "openai/openai-python"
    ]
    search_queries: List[str] = [
        "AI tool", "machine learning", "automation", "pain point",
        "feature request", "enhancement", "improvement needed",
        "time consuming", "manual process", "workflow automation"
    ]
    languages: List[str] = ["Python", "JavaScript", "TypeScript", "Go", "Rust"]
    issue_states: List[str] = ["open", "closed"]
    max_issues_per_repo: int = 100
    max_search_results: int = 200
    include_pull_requests: bool = True
    min_stars: int = 100
    created_after: Optional[str] = None  # ISO format date


class GitHubIssue(BaseModel):
    """GitHub issue data structure."""
    id: int
    number: int
    title: str
    body: str
    state: str
    user: Dict[str, Any]
    assignee: Optional[Dict[str, Any]]
    labels: List[Dict[str, Any]]
    comments: int
    created_at: str
    updated_at: str
    closed_at: Optional[str]
    html_url: str
    repository_url: str
    reactions: Dict[str, Any]  # Changed from Dict[str, int] to handle URL and counts


class GitHubRepository(BaseModel):
    """GitHub repository data structure."""
    id: int
    name: str
    full_name: str
    description: Optional[str]
    language: Optional[str]
    stargazers_count: int
    forks_count: int
    open_issues_count: int
    topics: List[str]
    created_at: str
    updated_at: str
    html_url: str


class GitHubPlugin(DataSourcePlugin):
    """GitHub data source plugin for extracting market signals."""
    
    def __init__(self, config: GitHubConfig):
        super().__init__(config)
        self.github_config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url = "https://api.github.com"
        self._rate_limit_remaining = 5000
        self._rate_limit_reset = datetime.now()
    
    async def initialize(self) -> None:
        """Initialize GitHub API connection."""
        try:
            # Create HTTP session with authentication
            headers = {
                "Authorization": f"token {self.github_config.access_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "AI-Opportunity-Browser/1.0"
            }
            
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                headers=headers
            )
            
            # Test authentication
            await self._check_authentication()
            
            await self.set_status(PluginStatus.ACTIVE)
            
        except Exception as e:
            await self.set_status(PluginStatus.ERROR, f"Initialization failed: {e}")
            raise PluginError(f"Failed to initialize GitHub plugin: {e}")
    
    async def shutdown(self) -> None:
        """Clean shutdown of GitHub plugin."""
        if self._session:
            await self._session.close()
        await self.set_status(PluginStatus.INACTIVE)
    
    async def health_check(self) -> bool:
        """Check GitHub API connectivity and rate limits."""
        try:
            if not self._session:
                return False
            
            # Check rate limit status
            url = f"{self._base_url}/rate_limit"
            async with self._session.get(url) as response:
                if response.status != 200:
                    return False
                
                data = await response.json()
                core_limit = data.get("resources", {}).get("core", {})
                self._rate_limit_remaining = core_limit.get("remaining", 0)
                
                return self._rate_limit_remaining > 100  # Keep some buffer
                
        except Exception:
            return False
    
    async def fetch_data(self, params: Dict[str, Any]) -> AsyncIterator[RawData]:
        """Fetch data from GitHub based on parameters."""
        if not await self._check_rate_limit():
            raise PluginRateLimitError("Rate limit exceeded")
        
        try:
            # Extract parameters
            repositories = params.get("repositories", self.github_config.repositories)
            search_queries = params.get("search_queries", self.github_config.search_queries)
            languages = params.get("languages", self.github_config.languages)
            max_issues = params.get("max_issues", self.github_config.max_issues_per_repo)
            
            # Fetch from repositories
            for repo in repositories:
                async for raw_data in self._fetch_repository_issues(repo, max_issues):
                    await self._increment_request_count()
                    yield raw_data
            
            # Fetch from search queries
            for query in search_queries:
                async for raw_data in self._fetch_search_results(query, languages):
                    await self._increment_request_count()
                    yield raw_data
                    
        except Exception as e:
            await self.set_status(PluginStatus.ERROR, f"Data fetching failed: {e}")
            raise PluginError(f"Failed to fetch GitHub data: {e}")
    
    def get_metadata(self) -> PluginMetadata:
        """Return GitHub plugin metadata."""
        return PluginMetadata(
            name="github_plugin",
            version="1.0.0",
            description="GitHub data source plugin for market signal extraction",
            author="AI Opportunity Browser",
            source_type=DataSourceType.GITHUB,
            supported_signal_types=[
                "pain_point", "feature_request", "complaint", 
                "opportunity", "trend", "discussion"
            ],
            rate_limit_per_hour=self.config.rate_limit_per_hour,
            requires_auth=True,
            config_schema={
                "access_token": {"type": "string", "required": True},
                "repositories": {"type": "array", "items": {"type": "string"}},
                "search_queries": {"type": "array", "items": {"type": "string"}},
                "languages": {"type": "array", "items": {"type": "string"}},
                "issue_states": {"type": "array", "items": {"type": "string"}},
                "max_issues_per_repo": {"type": "integer", "minimum": 1, "maximum": 1000},
                "max_search_results": {"type": "integer", "minimum": 1, "maximum": 1000},
                "include_pull_requests": {"type": "boolean"},
                "min_stars": {"type": "integer", "minimum": 0},
                "created_after": {"type": "string", "format": "date"}
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate GitHub plugin configuration."""
        if "access_token" not in config or not config["access_token"]:
            return False
        
        # Validate optional fields
        if "repositories" in config and not isinstance(config["repositories"], list):
            return False
        
        if "search_queries" in config and not isinstance(config["search_queries"], list):
            return False
        
        if "max_issues_per_repo" in config:
            max_issues = config["max_issues_per_repo"]
            if not isinstance(max_issues, int) or max_issues < 1 or max_issues > 1000:
                return False
        
        return True
    
    async def _check_authentication(self) -> None:
        """Check GitHub API authentication."""
        if not self._session:
            raise PluginAuthError("HTTP session not initialized")
        
        url = f"{self._base_url}/user"
        
        try:
            async with self._session.get(url) as response:
                if response.status == 401:
                    raise PluginAuthError("Invalid GitHub access token")
                elif response.status != 200:
                    raise PluginAuthError(f"Authentication check failed: {response.status}")
                
        except aiohttp.ClientError as e:
            raise PluginNetworkError(f"Network error during authentication: {e}")
    
    async def _fetch_repository_issues(
        self,
        repository: str,
        max_issues: int
    ) -> AsyncIterator[RawData]:
        """Fetch issues from a specific repository."""
        url = f"{self._base_url}/repos/{repository}/issues"
        params = {
            "state": "all",
            "sort": "updated",
            "direction": "desc",
            "per_page": min(max_issues, 100)  # GitHub API limit
        }
        
        if self.github_config.created_after:
            params["since"] = self.github_config.created_after
        
        try:
            async with self._session.get(url, params=params) as response:
                await self._update_rate_limit(response)
                
                if response.status == 403:
                    raise PluginRateLimitError("GitHub API rate limit exceeded")
                elif response.status == 404:
                    return  # Repository not found or not accessible
                elif response.status != 200:
                    raise PluginNetworkError(f"GitHub API error: {response.status}")
                
                issues = await response.json()
                
                for issue_data in issues:
                    # Skip pull requests if not included
                    if not self.github_config.include_pull_requests and "pull_request" in issue_data:
                        continue
                    
                    # Convert to GitHubIssue for easier handling
                    github_issue = GitHubIssue(
                        id=issue_data.get("id", 0),
                        number=issue_data.get("number", 0),
                        title=issue_data.get("title", ""),
                        body=issue_data.get("body") or "",
                        state=issue_data.get("state", ""),
                        user=issue_data.get("user", {}),
                        assignee=issue_data.get("assignee"),
                        labels=issue_data.get("labels", []),
                        comments=issue_data.get("comments", 0),
                        created_at=issue_data.get("created_at", ""),
                        updated_at=issue_data.get("updated_at", ""),
                        closed_at=issue_data.get("closed_at"),
                        html_url=issue_data.get("html_url", ""),
                        repository_url=issue_data.get("repository_url", ""),
                        reactions=issue_data.get("reactions", {})
                    )
                    
                    # Normalize the issue data
                    raw_data = await self._normalize_issue_data(github_issue, repository)
                    if raw_data:
                        yield raw_data
                        
        except aiohttp.ClientError as e:
            raise PluginNetworkError(f"Network error fetching repository issues: {e}")
    
    async def _fetch_search_results(
        self,
        query: str,
        languages: List[str]
    ) -> AsyncIterator[RawData]:
        """Fetch issues from GitHub search."""
        # Build search query
        search_terms = [query]
        
        if languages:
            language_filter = " OR ".join([f"language:{lang}" for lang in languages])
            search_terms.append(f"({language_filter})")
        
        if self.github_config.min_stars > 0:
            search_terms.append(f"stars:>={self.github_config.min_stars}")
        
        if self.github_config.created_after:
            search_terms.append(f"created:>={self.github_config.created_after}")
        
        search_query = " ".join(search_terms)
        
        url = f"{self._base_url}/search/issues"
        params = {
            "q": search_query,
            "sort": "updated",
            "order": "desc",
            "per_page": min(self.github_config.max_search_results, 100)
        }
        
        try:
            async with self._session.get(url, params=params) as response:
                await self._update_rate_limit(response)
                
                if response.status == 403:
                    raise PluginRateLimitError("GitHub search API rate limit exceeded")
                elif response.status != 200:
                    raise PluginNetworkError(f"GitHub search API error: {response.status}")
                
                data = await response.json()
                issues = data.get("items", [])
                
                for issue_data in issues:
                    # Skip pull requests if not included
                    if not self.github_config.include_pull_requests and "pull_request" in issue_data:
                        continue
                    
                    # Convert to GitHubIssue
                    github_issue = GitHubIssue(
                        id=issue_data.get("id", 0),
                        number=issue_data.get("number", 0),
                        title=issue_data.get("title", ""),
                        body=issue_data.get("body") or "",
                        state=issue_data.get("state", ""),
                        user=issue_data.get("user", {}),
                        assignee=issue_data.get("assignee"),
                        labels=issue_data.get("labels", []),
                        comments=issue_data.get("comments", 0),
                        created_at=issue_data.get("created_at", ""),
                        updated_at=issue_data.get("updated_at", ""),
                        closed_at=issue_data.get("closed_at"),
                        html_url=issue_data.get("html_url", ""),
                        repository_url=issue_data.get("repository_url", ""),
                        reactions=issue_data.get("reactions", {})
                    )
                    
                    # Extract repository name from URL
                    repo_name = self._extract_repo_name(github_issue.repository_url)
                    
                    # Normalize the issue data
                    raw_data = await self._normalize_issue_data(github_issue, repo_name)
                    if raw_data:
                        yield raw_data
                        
        except aiohttp.ClientError as e:
            raise PluginNetworkError(f"Network error fetching search results: {e}")
    
    async def _normalize_issue_data(self, issue: GitHubIssue, repository: str) -> Optional[RawData]:
        """Normalize GitHub issue data into RawData format."""
        # Combine title and body for analysis
        full_content = f"{issue.title}\n\n{issue.body}".strip()
        
        # Check if content is relevant for AI opportunities
        if not self._is_ai_relevant(full_content, issue.labels):
            return None
        
        # Determine signal type based on content and labels
        signal_type = self._classify_signal_type(full_content, issue.labels)
        
        # Calculate engagement score
        engagement_score = self._calculate_engagement_score(issue)
        
        # Extract author information
        author = issue.user.get("login", "") if issue.user else ""
        author_reputation = issue.user.get("public_repos", 0) if issue.user else 0
        
        # Calculate reaction counts - handle GitHub API response structure
        if issue.reactions and isinstance(issue.reactions, dict):
            # GitHub API returns reactions with total_count and individual counts
            total_reactions = issue.reactions.get('total_count', 0)
            positive_reactions = (
                issue.reactions.get("+1", 0) + 
                issue.reactions.get("heart", 0) + 
                issue.reactions.get("hooray", 0) +
                issue.reactions.get("rocket", 0)  # rocket is also positive
            )
        else:
            total_reactions = 0
            positive_reactions = 0
        
        return RawData(
            source="github",
            source_id=str(issue.id),
            source_url=issue.html_url,
            title=issue.title,
            content=self._clean_content(full_content),
            raw_content=full_content,
            author=author,
            author_reputation=float(author_reputation),
            upvotes=positive_reactions,
            downvotes=issue.reactions.get("-1", 0) if issue.reactions and isinstance(issue.reactions, dict) else 0,
            comments_count=issue.comments,
            shares_count=0,  # GitHub doesn't track shares
            views_count=0,   # GitHub doesn't provide view counts
            extracted_at=datetime.now(),
            metadata={
                "repository": repository,
                "issue_number": issue.number,
                "state": issue.state,
                "signal_type": signal_type,
                "engagement_score": engagement_score,
                "labels": [label.get("name", "") for label in issue.labels],
                "created_at": issue.created_at,
                "updated_at": issue.updated_at,
                "closed_at": issue.closed_at,
                "assignee": issue.assignee.get("login", "") if issue.assignee else None,
                "reactions": issue.reactions,
                "total_reactions": total_reactions
            }
        )
    
    def _is_ai_relevant(self, content: str, labels: List[Dict[str, Any]]) -> bool:
        """Check if the issue is relevant to AI opportunities."""
        content_lower = content.lower()
        
        # AI-related keywords
        ai_keywords = [
            "ai", "artificial intelligence", "machine learning", "ml",
            "deep learning", "neural network", "automation", "nlp",
            "computer vision", "data science", "algorithm", "model",
            "prediction", "classification", "clustering", "recommendation"
        ]
        
        # Check content for AI keywords
        if any(keyword in content_lower for keyword in ai_keywords):
            return True
        
        # Check labels for AI-related tags
        label_names = [label.get("name", "").lower() for label in labels]
        ai_labels = ["ai", "ml", "machine-learning", "automation", "enhancement", "feature"]
        
        if any(ai_label in " ".join(label_names) for ai_label in ai_labels):
            return True
        
        # Check for pain point or opportunity indicators
        opportunity_keywords = [
            "pain point", "frustrating", "time consuming", "manual",
            "automate", "improve", "optimize", "enhance", "feature request",
            "would be nice", "wish", "need", "should have"
        ]
        
        return any(keyword in content_lower for keyword in opportunity_keywords)
    
    def _classify_signal_type(self, content: str, labels: List[Dict[str, Any]]) -> str:
        """Classify the type of market signal based on content and labels."""
        content_lower = content.lower()
        label_names = [label.get("name", "").lower() for label in labels]
        
        # Check labels first (more reliable)
        if any(label in ["bug", "error", "issue"] for label in label_names):
            return "complaint"
        elif any(label in ["enhancement", "feature", "feature-request"] for label in label_names):
            return "feature_request"
        elif any(label in ["question", "help", "discussion"] for label in label_names):
            return "discussion"
        
        # Analyze content
        if any(word in content_lower for word in ["bug", "error", "broken", "doesn't work"]):
            return "complaint"
        elif any(word in content_lower for word in ["feature", "enhancement", "improve", "add"]):
            return "feature_request"
        elif any(word in content_lower for word in ["pain", "frustrating", "difficult", "problem"]):
            return "pain_point"
        elif any(word in content_lower for word in ["opportunity", "market", "business"]):
            return "opportunity"
        else:
            return "discussion"
    
    def _calculate_engagement_score(self, issue: GitHubIssue) -> float:
        """Calculate engagement score based on GitHub metrics."""
        base_score = issue.comments * 2
        reaction_score = issue.reactions.get('total_count', 0) if issue.reactions and isinstance(issue.reactions, dict) else 0
        
        # Time factor (newer issues get slight boost)
        try:
            created_date = datetime.fromisoformat(issue.created_at.replace('Z', '+00:00'))
            age_days = (datetime.now(created_date.tzinfo) - created_date).days
            time_factor = max(0.5, 1.0 - (age_days / 365))  # Decay over a year
        except:
            time_factor = 1.0
        
        return (base_score + reaction_score) * time_factor
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content text."""
        # Remove GitHub markdown
        content = re.sub(r'```[\s\S]*?```', '[CODE_BLOCK]', content)  # Code blocks
        content = re.sub(r'`([^`]+)`', r'\1', content)                # Inline code
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)           # Bold
        content = re.sub(r'\*(.*?)\*', r'\1', content)               # Italic
        content = re.sub(r'~~(.*?)~~', r'\1', content)               # Strikethrough
        
        # Remove GitHub-specific formatting
        content = re.sub(r'@\w+', '', content)                       # User mentions
        content = re.sub(r'#\d+', '', content)                       # Issue references
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)            # Images
        content = re.sub(r'\[.*?\]\(.*?\)', '', content)             # Links
        
        # Clean up whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)                # Multiple newlines
        content = re.sub(r' +', ' ', content)                        # Multiple spaces
        
        return content.strip()
    
    def _extract_repo_name(self, repository_url: str) -> str:
        """Extract repository name from GitHub API URL."""
        # URL format: https://api.github.com/repos/owner/repo
        parts = repository_url.split('/')
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1]}"
        return repository_url
    
    async def _update_rate_limit(self, response: aiohttp.ClientResponse) -> None:
        """Update rate limit information from response headers."""
        remaining = response.headers.get('X-RateLimit-Remaining')
        reset_time = response.headers.get('X-RateLimit-Reset')
        
        if remaining:
            self._rate_limit_remaining = int(remaining)
        
        if reset_time:
            self._rate_limit_reset = datetime.fromtimestamp(int(reset_time))