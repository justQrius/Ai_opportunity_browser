"""Base plugin system for data source ingestion."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, AsyncIterator
from pydantic import BaseModel


class PluginStatus(str, Enum):
    """Plugin status enumeration."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class DataSourceType(str, Enum):
    """Types of data sources supported."""
    REDDIT = "reddit"
    GITHUB = "github"
    TWITTER = "twitter"
    HACKERNEWS = "hackernews"
    PRODUCTHUNT = "producthunt"
    YCOMBINATOR = "ycombinator"
    STACKOVERFLOW = "stackoverflow"
    LINKEDIN = "linkedin"
    DISCORD = "discord"


@dataclass
class PluginMetadata:
    """Metadata for a data source plugin."""
    name: str
    version: str
    description: str
    author: str
    source_type: DataSourceType
    supported_signal_types: List[str]
    rate_limit_per_hour: int
    requires_auth: bool
    config_schema: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RawData(BaseModel):
    """Raw data structure from data sources."""
    source: str
    source_id: str
    source_url: Optional[str] = None
    title: Optional[str] = None
    content: str
    raw_content: Optional[str] = None
    author: Optional[str] = None
    author_reputation: Optional[float] = None
    upvotes: Optional[int] = 0
    downvotes: Optional[int] = 0
    comments_count: Optional[int] = 0
    shares_count: Optional[int] = 0
    views_count: Optional[int] = 0
    extracted_at: datetime
    metadata: Dict[str, Any] = {}


class PluginConfig(BaseModel):
    """Base configuration for plugins."""
    enabled: bool = True
    rate_limit_per_hour: int = 1000
    max_retries: int = 3
    timeout_seconds: int = 30
    batch_size: int = 100


class DataSourcePlugin(ABC):
    """Abstract base class for data source plugins."""
    
    def __init__(self, config: PluginConfig):
        self.config = config
        self.status = PluginStatus.INACTIVE
        self._last_error: Optional[str] = None
        self._request_count = 0
        self._last_reset = datetime.now()
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the plugin with necessary connections and auth."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Clean shutdown of the plugin."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the plugin is healthy and can fetch data."""
        pass
    
    @abstractmethod
    async def fetch_data(self, params: Dict[str, Any]) -> AsyncIterator[RawData]:
        """Fetch data from the source with given parameters."""
        pass
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin-specific configuration."""
        pass
    
    async def set_status(self, status: PluginStatus, error: Optional[str] = None) -> None:
        """Set plugin status and optional error message."""
        self.status = status
        self._last_error = error
    
    def get_status(self) -> Dict[str, Any]:
        """Get current plugin status information."""
        return {
            "status": self.status,
            "last_error": self._last_error,
            "request_count": self._request_count,
            "last_reset": self._last_reset
        }
    
    async def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.now()
        if (now - self._last_reset).total_seconds() >= 3600:  # Reset hourly
            self._request_count = 0
            self._last_reset = now
        
        return self._request_count < self.config.rate_limit_per_hour
    
    async def _increment_request_count(self) -> None:
        """Increment the request counter."""
        self._request_count += 1


class PluginError(Exception):
    """Base exception for plugin errors."""
    pass


class PluginConfigError(PluginError):
    """Configuration error in plugin."""
    pass


class PluginRateLimitError(PluginError):
    """Rate limit exceeded error."""
    pass


class PluginAuthError(PluginError):
    """Authentication error in plugin."""
    pass


class PluginNetworkError(PluginError):
    """Network error in plugin."""
    pass