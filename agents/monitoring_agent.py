"""
MonitoringAgent implementation for the AI Opportunity Browser system.
Implements continuous data source scanning for pain point signals.

As specified in the design document:
- Continuously scan Reddit discussions, GitHub issues, customer support docs, and social media
- Detect pain point signals and market opportunities
- Filter and normalize data for downstream processing
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .base import BaseAgent, AgentTask

logger = logging.getLogger(__name__)


@dataclass
class MonitoringConfig:
    """Configuration for monitoring agents"""
    data_source: str
    scan_interval: int = 300  # 5 minutes
    max_signals_per_scan: int = 100
    keywords: List[str] = None
    filters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.filters is None:
            self.filters = {}


@dataclass
class MarketSignal:
    """Represents a market signal detected by monitoring"""
    signal_id: str
    source: str
    signal_type: str  # pain_point, feature_request, complaint, opportunity
    content: str
    metadata: Dict[str, Any]
    engagement_metrics: Dict[str, Any]
    sentiment_score: float
    confidence_level: float
    extracted_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "source": self.source,
            "signal_type": self.signal_type,
            "content": self.content,
            "metadata": self.metadata,
            "engagement_metrics": self.engagement_metrics,
            "sentiment_score": self.sentiment_score,
            "confidence_level": self.confidence_level,
            "extracted_at": self.extracted_at.isoformat()
        }


class MonitoringAgent(BaseAgent):
    """
    Monitoring agent that continuously scans data sources for pain point signals.
    Implements the monitoring capabilities specified in the design document.
    """
    
    def __init__(self, agent_id: str = None, name: str = None, config: Dict[str, Any] = None):
        super().__init__(agent_id, name or "MonitoringAgent", config)
        
        # Parse monitoring configuration
        self.monitoring_config = MonitoringConfig(
            data_source=config.get("data_source", "unknown"),
            scan_interval=config.get("scan_interval", 300),
            max_signals_per_scan=config.get("max_signals_per_scan", 100),
            keywords=config.get("keywords", []),
            filters=config.get("filters", {})
        )
        
        # Monitoring state
        self.last_scan_time: Optional[datetime] = None
        self.scan_cursor: Optional[str] = None
        self.detected_signals: List[MarketSignal] = []
        
        # Scanning task
        self._scanning_task: Optional[asyncio.Task] = None
        
        logger.info(f"MonitoringAgent initialized for source: {self.monitoring_config.data_source}")
    
    async def initialize(self) -> None:
        """Initialize monitoring agent resources"""
        try:
            # Initialize data source connections
            await self._initialize_data_source()
            
            # Start continuous scanning
            self._scanning_task = asyncio.create_task(self._continuous_scan_loop())
            
            logger.info(f"MonitoringAgent {self.name} initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MonitoringAgent {self.name}: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Cleanup monitoring agent resources"""
        # Stop scanning task
        if self._scanning_task and not self._scanning_task.done():
            self._scanning_task.cancel()
            try:
                await self._scanning_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup data source connections
        await self._cleanup_data_source()
        
        logger.info(f"MonitoringAgent {self.name} cleaned up")
    
    async def process_task(self, task: AgentTask) -> Any:
        """Process monitoring tasks"""
        task_type = task.type
        task_data = task.data
        
        if task_type == "scan_source":
            return await self._scan_data_source(task_data)
        elif task_type == "analyze_signal":
            return await self._analyze_signal(task_data)
        elif task_type == "get_signals":
            return await self._get_detected_signals(task_data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform monitoring agent health checks"""
        health_data = {
            "data_source_connected": await self._check_data_source_connection(),
            "last_scan_time": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "signals_detected": len(self.detected_signals),
            "scan_interval": self.monitoring_config.scan_interval,
            "scanning_active": self._scanning_task and not self._scanning_task.done()
        }
        
        # Check if scanning is stale
        if self.last_scan_time:
            time_since_scan = (datetime.utcnow() - self.last_scan_time).total_seconds()
            if time_since_scan > self.monitoring_config.scan_interval * 2:
                health_data["scan_stale"] = True
        
        return health_data
    
    # Private methods
    
    async def _continuous_scan_loop(self) -> None:
        """Continuous scanning loop"""
        logger.debug(f"Starting continuous scan loop for {self.monitoring_config.data_source}")
        
        while not self._shutdown_event.is_set():
            try:
                # Perform scan
                await self._perform_scan()
                
                # Wait for next scan interval
                await asyncio.sleep(self.monitoring_config.scan_interval)
                
            except Exception as e:
                logger.error(f"Error in continuous scan loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
        
        logger.debug("Continuous scan loop stopped")
    
    async def _perform_scan(self) -> None:
        """Perform a single scan of the data source"""
        try:
            logger.debug(f"Performing scan of {self.monitoring_config.data_source}")
            
            # Scan based on data source type
            if self.monitoring_config.data_source == "reddit":
                signals = await self._scan_reddit()
            elif self.monitoring_config.data_source == "github":
                signals = await self._scan_github()
            elif self.monitoring_config.data_source == "social_media":
                signals = await self._scan_social_media()
            else:
                logger.warning(f"Unknown data source: {self.monitoring_config.data_source}")
                return
            
            # Process and store signals
            for signal in signals:
                await self._process_signal(signal)
            
            self.last_scan_time = datetime.utcnow()
            logger.debug(f"Scan completed, found {len(signals)} signals")
            
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            raise
    
    async def _scan_reddit(self) -> List[MarketSignal]:
        """Scan Reddit for pain point signals"""
        signals = []
        
        try:
            # Mock Reddit scanning - in real implementation, use Reddit API
            # This would integrate with the Reddit plugin from data-ingestion
            mock_posts = [
                {
                    "id": "reddit_001",
                    "title": "Why is there no good AI tool for managing customer support tickets?",
                    "content": "I've been looking for an AI solution that can automatically categorize and prioritize customer support tickets, but everything I find is either too expensive or doesn't work well. There has to be a better way to handle this.",
                    "subreddit": "entrepreneur",
                    "upvotes": 45,
                    "comments": 23,
                    "created_at": datetime.utcnow() - timedelta(hours=2)
                },
                {
                    "id": "reddit_002", 
                    "title": "Struggling with inventory forecasting - any AI solutions?",
                    "content": "Our small retail business is constantly over or under-stocked. Manual forecasting is killing us. Are there any affordable AI tools that can help predict demand better?",
                    "subreddit": "smallbusiness",
                    "upvotes": 67,
                    "comments": 34,
                    "created_at": datetime.utcnow() - timedelta(hours=1)
                }
            ]
            
            for post in mock_posts:
                signal = MarketSignal(
                    signal_id=post["id"],
                    source="reddit",
                    signal_type="pain_point",
                    content=f"{post['title']} - {post['content']}",
                    metadata={
                        "subreddit": post["subreddit"],
                        "post_id": post["id"],
                        "title": post["title"]
                    },
                    engagement_metrics={
                        "upvotes": post["upvotes"],
                        "comments": post["comments"]
                    },
                    sentiment_score=-0.6,  # Negative sentiment for pain points
                    confidence_level=0.8,
                    extracted_at=datetime.utcnow()
                )
                signals.append(signal)
            
        except Exception as e:
            logger.error(f"Reddit scanning failed: {e}")
        
        return signals
    
    async def _scan_github(self) -> List[MarketSignal]:
        """Scan GitHub for feature requests and issues"""
        signals = []
        
        try:
            # Mock GitHub scanning - in real implementation, use GitHub API
            # This would integrate with the GitHub plugin from data-ingestion
            mock_issues = [
                {
                    "id": "github_001",
                    "title": "Feature Request: AI-powered code review suggestions",
                    "body": "It would be great if the IDE could use AI to suggest code improvements during review. Current tools are limited and don't understand context well.",
                    "repository": "microsoft/vscode",
                    "labels": ["feature-request", "ai"],
                    "reactions": 156,
                    "comments": 42,
                    "created_at": datetime.utcnow() - timedelta(hours=6)
                },
                {
                    "id": "github_002",
                    "title": "Need better automated testing for ML models",
                    "body": "Testing ML models is still very manual and error-prone. We need better tools for automated model validation and testing pipelines.",
                    "repository": "tensorflow/tensorflow",
                    "labels": ["enhancement", "testing"],
                    "reactions": 89,
                    "comments": 28,
                    "created_at": datetime.utcnow() - timedelta(hours=4)
                }
            ]
            
            for issue in mock_issues:
                signal = MarketSignal(
                    signal_id=issue["id"],
                    source="github",
                    signal_type="feature_request",
                    content=f"{issue['title']} - {issue['body']}",
                    metadata={
                        "repository": issue["repository"],
                        "issue_id": issue["id"],
                        "labels": issue["labels"]
                    },
                    engagement_metrics={
                        "reactions": issue["reactions"],
                        "comments": issue["comments"]
                    },
                    sentiment_score=0.2,  # Slightly positive for feature requests
                    confidence_level=0.9,
                    extracted_at=datetime.utcnow()
                )
                signals.append(signal)
            
        except Exception as e:
            logger.error(f"GitHub scanning failed: {e}")
        
        return signals
    
    async def _scan_social_media(self) -> List[MarketSignal]:
        """Scan social media for market signals"""
        signals = []
        
        try:
            # Mock social media scanning
            mock_posts = [
                {
                    "id": "twitter_001",
                    "content": "Why is it so hard to find an AI tool that actually understands my business needs? Everything is either too generic or too complex.",
                    "platform": "twitter",
                    "likes": 234,
                    "retweets": 45,
                    "replies": 67,
                    "created_at": datetime.utcnow() - timedelta(hours=3)
                }
            ]
            
            for post in mock_posts:
                signal = MarketSignal(
                    signal_id=post["id"],
                    source="social_media",
                    signal_type="complaint",
                    content=post["content"],
                    metadata={
                        "platform": post["platform"],
                        "post_id": post["id"]
                    },
                    engagement_metrics={
                        "likes": post["likes"],
                        "retweets": post["retweets"],
                        "replies": post["replies"]
                    },
                    sentiment_score=-0.4,
                    confidence_level=0.7,
                    extracted_at=datetime.utcnow()
                )
                signals.append(signal)
            
        except Exception as e:
            logger.error(f"Social media scanning failed: {e}")
        
        return signals
    
    async def _process_signal(self, signal: MarketSignal) -> None:
        """Process and store a detected signal"""
        # Apply filters
        if not await self._signal_passes_filters(signal):
            return
        
        # Check for duplicates
        if await self._is_duplicate_signal(signal):
            return
        
        # Store signal
        self.detected_signals.append(signal)
        
        # Keep only recent signals (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self.detected_signals = [
            s for s in self.detected_signals 
            if s.extracted_at > cutoff_time
        ]
        
        logger.debug(f"Processed signal {signal.signal_id}")
    
    async def _signal_passes_filters(self, signal: MarketSignal) -> bool:
        """Check if signal passes configured filters"""
        # Keyword filtering
        if self.monitoring_config.keywords:
            content_lower = signal.content.lower()
            if not any(keyword.lower() in content_lower for keyword in self.monitoring_config.keywords):
                return False
        
        # Engagement threshold filtering
        min_engagement = self.monitoring_config.filters.get("min_engagement", 0)
        total_engagement = sum(signal.engagement_metrics.values())
        if total_engagement < min_engagement:
            return False
        
        # Confidence threshold filtering
        min_confidence = self.monitoring_config.filters.get("min_confidence", 0.0)
        if signal.confidence_level < min_confidence:
            return False
        
        return True
    
    async def _is_duplicate_signal(self, signal: MarketSignal) -> bool:
        """Check if signal is a duplicate"""
        # Simple duplicate detection based on content similarity
        for existing_signal in self.detected_signals:
            if (existing_signal.source == signal.source and
                existing_signal.signal_type == signal.signal_type):
                
                # Check content similarity (simplified)
                if len(set(signal.content.lower().split()) & 
                       set(existing_signal.content.lower().split())) > 5:
                    return True
        
        return False
    
    async def _scan_data_source(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scan_source task"""
        await self._perform_scan()
        return {
            "status": "completed",
            "signals_found": len(self.detected_signals),
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None
        }
    
    async def _analyze_signal(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analyze_signal task"""
        signal_data = task_data.get("signal")
        if not signal_data:
            raise ValueError("No signal data provided")
        
        # Perform signal analysis (mock implementation)
        analysis = {
            "signal_id": signal_data.get("signal_id"),
            "ai_relevance_score": 0.8,
            "market_potential": "high",
            "implementation_complexity": "medium",
            "similar_signals": 3
        }
        
        return analysis
    
    async def _get_detected_signals(self, task_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle get_signals task"""
        limit = task_data.get("limit", 50)
        signal_type = task_data.get("signal_type")
        
        signals = self.detected_signals
        
        # Filter by signal type if specified
        if signal_type:
            signals = [s for s in signals if s.signal_type == signal_type]
        
        # Sort by confidence and recency
        signals.sort(key=lambda s: (s.confidence_level, s.extracted_at), reverse=True)
        
        # Limit results
        signals = signals[:limit]
        
        return [signal.to_dict() for signal in signals]
    
    async def _initialize_data_source(self) -> None:
        """Initialize data source connections"""
        # Mock initialization - in real implementation, set up API clients
        logger.debug(f"Initializing connection to {self.monitoring_config.data_source}")
        await asyncio.sleep(0.1)  # Simulate connection setup
    
    async def _cleanup_data_source(self) -> None:
        """Cleanup data source connections"""
        # Mock cleanup - in real implementation, close API clients
        logger.debug(f"Cleaning up connection to {self.monitoring_config.data_source}")
        await asyncio.sleep(0.1)  # Simulate cleanup
    
    async def _check_data_source_connection(self) -> bool:
        """Check if data source connection is healthy"""
        # Mock health check - in real implementation, ping the API
        return True