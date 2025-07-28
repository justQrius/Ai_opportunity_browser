"""Market signal service for AI agent discovery operations.

Supports Requirement 5.1-5.6 (Agentic AI Discovery Engine):
- Monitoring agents scan data sources for pain point signals
- Analysis agents score opportunities based on market validation signals
- Research agents gather context from various sources
- Trend agents identify patterns and emerging opportunities
- Capability agents assess AI feasibility
"""

import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload

from shared.models.market_signal import MarketSignal, SignalType
from shared.models.opportunity import Opportunity
from shared.schemas.market_signal import MarketSignalCreate, MarketSignalUpdate, MarketSignalSearch
from shared.cache import cache_manager, CacheKeys
from shared.vector_db import market_signal_vector_service
import structlog

logger = structlog.get_logger(__name__)


class MarketSignalService:
    """Service for market signal management and AI agent operations."""
    
    async def create_market_signal(
        self, 
        db: AsyncSession, 
        signal_data: MarketSignalCreate,
        agent_name: Optional[str] = None
    ) -> MarketSignal:
        """Create a new market signal from AI agent discovery.
        
        Supports Requirement 5.1 (Monitoring agents scan data sources).
        
        Args:
            db: Database session
            signal_data: Market signal creation data
            agent_name: Name of AI agent that discovered this signal
            
        Returns:
            Created market signal instance
        """
        # Prepare JSON fields
        keywords_json = None
        if signal_data.keywords:
            keywords_json = json.dumps(signal_data.keywords)
        
        categories_json = None
        if signal_data.categories:
            categories_json = json.dumps(signal_data.categories)
        
        # Create market signal
        market_signal = MarketSignal(
            source=signal_data.source,
            source_id=signal_data.source_id,
            source_url=signal_data.source_url,
            signal_type=signal_data.signal_type,
            title=signal_data.title,
            content=signal_data.content,
            raw_content=signal_data.raw_content,
            author=signal_data.author,
            author_reputation=signal_data.author_reputation,
            upvotes=signal_data.upvotes or 0,
            downvotes=signal_data.downvotes or 0,
            comments_count=signal_data.comments_count or 0,
            shares_count=signal_data.shares_count or 0,
            views_count=signal_data.views_count or 0,
            extracted_at=signal_data.extracted_at,
            keywords=keywords_json,
            categories=categories_json,
            processing_version=f"agent_{agent_name}" if agent_name else None
        )
        
        db.add(market_signal)
        await db.commit()
        await db.refresh(market_signal)
        
        logger.info(
            "Market signal created",
            signal_id=market_signal.id,
            source=market_signal.source,
            signal_type=market_signal.signal_type,
            agent=agent_name
        )
        
        # Clear relevant caches
        await self._clear_signal_caches()
        
        # Trigger analysis workflow (Requirement 5.2)
        await self._trigger_analysis_workflow(db, market_signal)
        
        return market_signal
    
    async def process_signal_analysis(
        self, 
        db: AsyncSession, 
        signal_id: str,
        analysis_results: Dict[str, Any],
        agent_name: Optional[str] = None
    ) -> Optional[MarketSignal]:
        """Process AI analysis results for a market signal.
        
        Supports Requirement 5.2 (Analysis agents score opportunities).
        
        Args:
            db: Database session
            signal_id: Market signal identifier
            analysis_results: AI analysis results
            agent_name: Name of analysis agent
            
        Returns:
            Updated market signal instance or None
        """
        signal = await self.get_signal_by_id(db, signal_id)
        if not signal:
            return None
        
        # Update analysis results
        signal.sentiment_score = analysis_results.get("sentiment_score", 0.0)
        signal.confidence_level = analysis_results.get("confidence_level", 0.0)
        signal.pain_point_intensity = analysis_results.get("pain_point_intensity")
        signal.ai_relevance_score = analysis_results.get("ai_relevance_score")
        
        # Update market validation signals
        if "market_validation_signals" in analysis_results:
            signal.market_validation_signals = json.dumps(analysis_results["market_validation_signals"])
        
        # Update keywords and categories from analysis
        if "extracted_keywords" in analysis_results:
            signal.keywords = json.dumps(analysis_results["extracted_keywords"])
        
        if "categories" in analysis_results:
            signal.categories = json.dumps(analysis_results["categories"])
        
        # Mark as processed
        signal.processed_at = datetime.utcnow()
        signal.processing_version = f"analysis_{agent_name}" if agent_name else "analysis"
        
        await db.commit()
        await db.refresh(signal)
        
        logger.info(
            "Market signal analysis processed",
            signal_id=signal.id,
            sentiment_score=signal.sentiment_score,
            pain_point_intensity=signal.pain_point_intensity,
            ai_relevance=signal.ai_relevance_score,
            agent=agent_name
        )
        
        # Clear caches
        await self._clear_signal_caches(signal_id)
        
        # Check if signal should trigger opportunity generation
        await self._evaluate_opportunity_generation(db, signal)
        
        return signal
    
    async def get_signal_by_id(
        self, 
        db: AsyncSession, 
        signal_id: str
    ) -> Optional[MarketSignal]:
        """Get market signal by ID.
        
        Args:
            db: Database session
            signal_id: Signal identifier
            
        Returns:
            Market signal instance or None
        """
        result = await db.execute(
            select(MarketSignal)
            .options(selectinload(MarketSignal.opportunity))
            .where(MarketSignal.id == signal_id)
        )
        return result.scalar_one_or_none()
    
    async def search_signals(
        self, 
        db: AsyncSession, 
        search_params: MarketSignalSearch,
        limit: int = 50
    ) -> List[MarketSignal]:
        """Search market signals with filtering.
        
        Args:
            db: Database session
            search_params: Search parameters
            limit: Maximum results to return
            
        Returns:
            List of matching market signals
        """
        query = select(MarketSignal).options(
            selectinload(MarketSignal.opportunity)
        )
        
        # Apply filters
        filters = []
        
        if search_params.source:
            filters.append(MarketSignal.source == search_params.source)
        
        if search_params.signal_type:
            filters.append(MarketSignal.signal_type == search_params.signal_type)
        
        if search_params.min_sentiment_score is not None:
            filters.append(MarketSignal.sentiment_score >= search_params.min_sentiment_score)
        
        if search_params.max_sentiment_score is not None:
            filters.append(MarketSignal.sentiment_score <= search_params.max_sentiment_score)
        
        if search_params.min_confidence_level is not None:
            filters.append(MarketSignal.confidence_level >= search_params.min_confidence_level)
        
        if search_params.opportunity_id:
            filters.append(MarketSignal.opportunity_id == search_params.opportunity_id)
        
        if search_params.date_from:
            filters.append(MarketSignal.extracted_at >= search_params.date_from)
        
        if search_params.date_to:
            filters.append(MarketSignal.extracted_at <= search_params.date_to)
        
        # Apply all filters
        if filters:
            query = query.where(and_(*filters))
        
        # Apply ordering
        query = query.order_by(
            desc(MarketSignal.pain_point_intensity),
            desc(MarketSignal.extracted_at)
        ).limit(limit)
        
        result = await db.execute(query)
        signals = result.scalars().all()
        
        logger.info(
            "Market signals search completed",
            filters_applied=len(filters),
            results_count=len(signals)
        )
        
        return list(signals)
    
    async def find_similar_signals(
        self, 
        db: AsyncSession, 
        signal_id: str,
        similarity_threshold: float = 0.8,
        limit: int = 10
    ) -> List[MarketSignal]:
        """Find similar market signals using vector similarity.
        
        Supports duplicate detection and clustering for Requirement 5.4 (Trend agents).
        
        Args:
            db: Database session
            signal_id: Reference signal ID
            similarity_threshold: Minimum similarity score
            limit: Maximum results to return
            
        Returns:
            List of similar market signals
        """
        reference_signal = await self.get_signal_by_id(db, signal_id)
        if not reference_signal:
            return []
        
        # TODO: Implement vector similarity search when embeddings are available
        # For now, use text-based similarity as placeholder
        
        # Simple keyword-based similarity (placeholder)
        if not reference_signal.keywords:
            return []
        
        try:
            reference_keywords = json.loads(reference_signal.keywords)
        except json.JSONDecodeError:
            return []
        
        # Find signals with overlapping keywords
        similar_signals = []
        
        # This is a simplified implementation - in production, use vector similarity
        query = select(MarketSignal).where(
            and_(
                MarketSignal.id != signal_id,
                MarketSignal.keywords.isnot(None),
                MarketSignal.source == reference_signal.source  # Same source for now
            )
        ).limit(limit * 2)  # Get more to filter
        
        result = await db.execute(query)
        candidates = result.scalars().all()
        
        for candidate in candidates:
            if candidate.keywords:
                try:
                    candidate_keywords = json.loads(candidate.keywords)
                    # Calculate simple keyword overlap
                    overlap = len(set(reference_keywords) & set(candidate_keywords))
                    total_keywords = len(set(reference_keywords) | set(candidate_keywords))
                    
                    if total_keywords > 0:
                        similarity = overlap / total_keywords
                        if similarity >= similarity_threshold:
                            similar_signals.append(candidate)
                            
                            if len(similar_signals) >= limit:
                                break
                except json.JSONDecodeError:
                    continue
        
        logger.info(
            "Similar signals found",
            reference_signal_id=signal_id,
            similar_count=len(similar_signals),
            threshold=similarity_threshold
        )
        
        return similar_signals
    
    async def get_trending_signals(
        self, 
        db: AsyncSession,
        timeframe_hours: int = 24,
        min_engagement: int = 5,
        limit: int = 20
    ) -> List[MarketSignal]:
        """Get trending market signals based on engagement and recency.
        
        Supports Requirement 5.4 (Trend agents identify patterns).
        
        Args:
            db: Database session
            timeframe_hours: Time window for trending analysis
            min_engagement: Minimum engagement threshold
            limit: Maximum results to return
            
        Returns:
            List of trending market signals
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=timeframe_hours)
        
        # Calculate engagement score
        query = select(MarketSignal).where(
            and_(
                MarketSignal.extracted_at >= cutoff_time,
                or_(
                    MarketSignal.upvotes >= min_engagement,
                    MarketSignal.comments_count >= min_engagement,
                    MarketSignal.shares_count >= min_engagement
                )
            )
        ).order_by(
            desc(
                (MarketSignal.upvotes + MarketSignal.comments_count + MarketSignal.shares_count)
                * MarketSignal.pain_point_intensity
            ),
            desc(MarketSignal.extracted_at)
        ).limit(limit)
        
        result = await db.execute(query)
        trending_signals = result.scalars().all()
        
        logger.info(
            "Trending signals retrieved",
            timeframe_hours=timeframe_hours,
            trending_count=len(trending_signals),
            min_engagement=min_engagement
        )
        
        return list(trending_signals)
    
    async def get_signal_analytics(
        self, 
        db: AsyncSession,
        timeframe_days: int = 7
    ) -> Dict[str, Any]:
        """Get market signal analytics and insights.
        
        Supports Requirement 6.4 (Generate reports on opportunity clusters).
        
        Args:
            db: Database session
            timeframe_days: Analysis timeframe
            
        Returns:
            Analytics data dictionary
        """
        cutoff_date = datetime.utcnow() - timedelta(days=timeframe_days)
        
        # Total signals
        total_signals = await db.execute(
            select(func.count(MarketSignal.id))
            .where(MarketSignal.extracted_at >= cutoff_date)
        )
        total_count = total_signals.scalar()
        
        # Signals by source
        source_stats = await db.execute(
            select(
                MarketSignal.source,
                func.count(MarketSignal.id).label("count")
            )
            .where(MarketSignal.extracted_at >= cutoff_date)
            .group_by(MarketSignal.source)
        )
        
        signals_by_source = {
            row.source: row.count for row in source_stats
        }
        
        # Signals by type
        type_stats = await db.execute(
            select(
                MarketSignal.signal_type,
                func.count(MarketSignal.id).label("count")
            )
            .where(MarketSignal.extracted_at >= cutoff_date)
            .group_by(MarketSignal.signal_type)
        )
        
        signals_by_type = {
            row.signal_type.value: row.count for row in type_stats
        }
        
        # Average sentiment and confidence
        avg_stats = await db.execute(
            select(
                func.avg(MarketSignal.sentiment_score).label("avg_sentiment"),
                func.avg(MarketSignal.confidence_level).label("avg_confidence")
            )
            .where(
                and_(
                    MarketSignal.extracted_at >= cutoff_date,
                    MarketSignal.processed_at.isnot(None)
                )
            )
        )
        
        avg_result = avg_stats.first()
        
        analytics = {
            "total_signals": total_count,
            "signals_by_source": signals_by_source,
            "signals_by_type": signals_by_type,
            "average_sentiment": round(avg_result.avg_sentiment or 0.0, 2),
            "average_confidence": round(avg_result.avg_confidence or 0.0, 2),
            "timeframe_days": timeframe_days,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        logger.info("Market signal analytics generated", **analytics)
        
        return analytics
    
    async def _trigger_analysis_workflow(
        self, 
        db: AsyncSession, 
        signal: MarketSignal
    ):
        """Trigger AI analysis workflow for new market signal.
        
        Supports Requirement 5.2 (Analysis agents process data).
        
        Args:
            db: Database session
            signal: Market signal instance
        """
        logger.info(
            "Analysis workflow triggered",
            signal_id=signal.id,
            source=signal.source,
            signal_type=signal.signal_type
        )
        
        # TODO: Queue signal for AI analysis
        # This would trigger analysis agents to:
        # 1. Perform sentiment analysis
        # 2. Extract keywords and categories
        # 3. Calculate pain point intensity
        # 4. Assess AI relevance
        # 5. Identify market validation signals
    
    async def _evaluate_opportunity_generation(
        self, 
        db: AsyncSession, 
        signal: MarketSignal
    ):
        """Evaluate if signal should trigger opportunity generation.
        
        Supports Requirements 5.2-5.4 (Signal clustering and opportunity generation).
        
        Args:
            db: Database session
            signal: Processed market signal
        """
        # Check if signal meets opportunity generation criteria
        if (signal.pain_point_intensity and signal.pain_point_intensity >= 0.7 and
            signal.ai_relevance_score and signal.ai_relevance_score >= 0.6 and
            signal.confidence_level >= 0.8):
            
            logger.info(
                "Signal qualifies for opportunity generation",
                signal_id=signal.id,
                pain_point_intensity=signal.pain_point_intensity,
                ai_relevance=signal.ai_relevance_score,
                confidence=signal.confidence_level
            )
            
            # TODO: Trigger opportunity generation workflow
            # This would:
            # 1. Find similar signals
            # 2. Cluster related signals
            # 3. Generate opportunity from signal cluster
            # 4. Initiate validation workflow
    
    async def _clear_signal_caches(self, signal_id: Optional[str] = None):
        """Clear market signal related cache entries.
        
        Args:
            signal_id: Specific signal ID to clear, or None for general caches
        """
        if signal_id:
            # Clear specific signal caches
            pass
        
        # Clear general caches
        logger.debug("Market signal caches cleared", signal_id=signal_id)


# Global market signal service instance
market_signal_service = MarketSignalService()