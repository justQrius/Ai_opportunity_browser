"""
Opportunity Ranking System for the AI Opportunity Browser.
Implements opportunity ranking, filtering, and personalization algorithms.

This module implements:
- Multi-criteria opportunity ranking with configurable weights
- Advanced filtering capabilities by industry, AI type, market size, validation score
- Personalized recommendation algorithms based on user interests and history
- Real-time ranking updates based on validation changes and market dynamics
- Performance-optimized ranking with caching and batch processing

Supports Requirements 3.2 (filtering capabilities) and 3.5 (personalized recommendations)
from the requirements document.
"""

import asyncio
import json
import logging
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, asdict
from collections import defaultdict
from enum import Enum
import math

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text
from sqlalchemy.orm import selectinload

from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.user import User
from shared.models.validation import ValidationResult
from shared.cache import cache_manager, CacheKeys
from shared.services.scoring_algorithms import advanced_scoring_engine

logger = logging.getLogger(__name__)


class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


class RankingCriteria(str, Enum):
    """Available ranking criteria."""
    OVERALL_SCORE = "overall_score"
    VALIDATION_SCORE = "validation_score"
    AI_FEASIBILITY = "ai_feasibility_score"
    MARKET_SIZE = "market_size"
    COMPETITION_LEVEL = "competition_level"
    IMPLEMENTATION_COMPLEXITY = "implementation_complexity"
    MARKET_TIMING = "market_timing"
    CREATED_DATE = "created_at"
    UPDATED_DATE = "updated_at"
    ENGAGEMENT_SCORE = "engagement_score"


@dataclass
class FilterCriteria:
    """Comprehensive filtering criteria for opportunities."""
    
    # Basic filters
    ai_solution_types: Optional[List[str]] = None
    target_industries: Optional[List[str]] = None
    geographic_scope: Optional[List[str]] = None
    status: Optional[List[OpportunityStatus]] = None
    tags: Optional[List[str]] = None
    
    # Score-based filters
    min_validation_score: Optional[float] = None
    max_validation_score: Optional[float] = None
    min_ai_feasibility_score: Optional[float] = None
    max_ai_feasibility_score: Optional[float] = None
    min_confidence_rating: Optional[float] = None
    max_confidence_rating: Optional[float] = None
    
    # Market-based filters
    min_market_size: Optional[int] = None
    max_market_size: Optional[int] = None
    competition_levels: Optional[List[str]] = None  # low, medium, high
    implementation_complexity: Optional[List[str]] = None  # low, medium, high
    
    # Time-based filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    updated_after: Optional[datetime] = None
    updated_before: Optional[datetime] = None
    
    # Text search
    search_query: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for caching and serialization."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, list) and value:
                    result[key] = value
                elif not isinstance(value, list):
                    result[key] = value
        return result


@dataclass
class RankingConfig:
    """Configuration for opportunity ranking."""
    
    # Primary ranking criteria and weight
    primary_criteria: RankingCriteria = RankingCriteria.OVERALL_SCORE
    primary_weight: float = 0.4
    
    # Secondary ranking criteria and weights
    secondary_criteria: Dict[RankingCriteria, float] = None
    
    # Sort order
    sort_order: SortOrder = SortOrder.DESC
    
    # Personalization settings
    enable_personalization: bool = True
    personalization_weight: float = 0.3
    
    # Freshness boost
    enable_freshness_boost: bool = True
    freshness_weight: float = 0.1
    
    # Trending boost
    enable_trending_boost: bool = True
    trending_weight: float = 0.2
    
    def __post_init__(self):
        """Initialize default secondary criteria if not provided."""
        if self.secondary_criteria is None:
            self.secondary_criteria = {
                RankingCriteria.VALIDATION_SCORE: 0.25,
                RankingCriteria.AI_FEASIBILITY: 0.20,
                RankingCriteria.MARKET_TIMING: 0.15
            }


@dataclass
class UserPreferences:
    """User preferences for personalized ranking."""
    
    user_id: str
    preferred_ai_types: List[str] = None
    preferred_industries: List[str] = None
    preferred_complexity_levels: List[str] = None
    preferred_market_sizes: List[str] = None  # small, medium, large
    
    # Interaction-based preferences (learned from behavior)
    viewed_opportunities: List[str] = None
    bookmarked_opportunities: List[str] = None
    validated_opportunities: List[str] = None
    
    # Preference weights (0.0 to 1.0)
    ai_type_weight: float = 0.3
    industry_weight: float = 0.3
    complexity_weight: float = 0.2
    market_size_weight: float = 0.2
    
    # Learning parameters
    interaction_decay_days: int = 90  # How long to consider past interactions
    min_interactions_for_learning: int = 5  # Minimum interactions to enable learning
    
    def __post_init__(self):
        """Initialize empty lists if None."""
        if self.preferred_ai_types is None:
            self.preferred_ai_types = []
        if self.preferred_industries is None:
            self.preferred_industries = []
        if self.preferred_complexity_levels is None:
            self.preferred_complexity_levels = []
        if self.preferred_market_sizes is None:
            self.preferred_market_sizes = []
        if self.viewed_opportunities is None:
            self.viewed_opportunities = []
        if self.bookmarked_opportunities is None:
            self.bookmarked_opportunities = []
        if self.validated_opportunities is None:
            self.validated_opportunities = []


@dataclass
class RankedOpportunity:
    """Opportunity with ranking information."""
    
    opportunity: Opportunity
    rank_score: float
    rank_position: int
    
    # Score breakdown for transparency
    base_score: float
    personalization_score: float
    freshness_score: float
    trending_score: float
    
    # Ranking factors
    ranking_factors: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "opportunity_id": self.opportunity.id,
            "rank_score": self.rank_score,
            "rank_position": self.rank_position,
            "base_score": self.base_score,
            "personalization_score": self.personalization_score,
            "freshness_score": self.freshness_score,
            "trending_score": self.trending_score,
            "ranking_factors": self.ranking_factors
        }


@dataclass
class RankingResult:
    """Result of opportunity ranking operation."""
    
    ranked_opportunities: List[RankedOpportunity]
    total_count: int
    filter_criteria: FilterCriteria
    ranking_config: RankingConfig
    user_preferences: Optional[UserPreferences]
    
    # Performance metrics
    ranking_time_ms: float
    cache_hit: bool
    
    # Pagination info
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    
    def __post_init__(self):
        """Calculate total pages."""
        self.total_pages = math.ceil(self.total_count / self.page_size)


class OpportunityRankingSystem:
    """
    Advanced opportunity ranking system with filtering and personalization.
    
    Implements multi-criteria ranking, advanced filtering, and personalized
    recommendations for the AI Opportunity Browser platform.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Default ranking configuration
        self.default_ranking_config = RankingConfig()
        
        # Cache settings
        self.cache_ttl = self.config.get("cache_ttl", 300)  # 5 minutes
        self.enable_caching = self.config.get("enable_caching", True)
        
        # Performance settings
        self.max_opportunities_per_query = self.config.get("max_opportunities", 1000)
        self.batch_size = self.config.get("batch_size", 100)
        
        # Personalization settings
        self.enable_learning = self.config.get("enable_learning", True)
        self.learning_update_interval = self.config.get("learning_interval", 3600)  # 1 hour
        
        logger.info("OpportunityRankingSystem initialized", config=self.config)
    
    async def rank_opportunities(
        self,
        db: AsyncSession,
        filter_criteria: FilterCriteria = None,
        ranking_config: RankingConfig = None,
        user_preferences: UserPreferences = None,
        page: int = 1,
        page_size: int = 20
    ) -> RankingResult:
        """
        Rank opportunities based on multiple criteria with filtering and personalization.
        
        Args:
            db: Database session
            filter_criteria: Filtering criteria
            ranking_config: Ranking configuration
            user_preferences: User preferences for personalization
            page: Page number for pagination
            page_size: Number of results per page
            
        Returns:
            RankingResult with ranked opportunities and metadata
        """
        start_time = datetime.utcnow()
        
        # Use defaults if not provided
        filter_criteria = filter_criteria or FilterCriteria()
        ranking_config = ranking_config or self.default_ranking_config
        
        # Check cache first
        cache_key = self._generate_cache_key(filter_criteria, ranking_config, user_preferences, page, page_size)
        cached_result = None
        
        if self.enable_caching:
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                logger.debug("Cache hit for ranking query", cache_key=cache_key)
                cached_result["cache_hit"] = True
                return RankingResult(**cached_result)
        
        try:
            # Get filtered opportunities
            opportunities, total_count = await self._get_filtered_opportunities(
                db, filter_criteria, page, page_size
            )
            
            if not opportunities:
                return RankingResult(
                    ranked_opportunities=[],
                    total_count=0,
                    filter_criteria=filter_criteria,
                    ranking_config=ranking_config,
                    user_preferences=user_preferences,
                    ranking_time_ms=0.0,
                    cache_hit=False,
                    page=page,
                    page_size=page_size
                )
            
            # Calculate ranking scores
            ranked_opportunities = await self._calculate_ranking_scores(
                opportunities, ranking_config, user_preferences
            )
            
            # Sort by rank score
            if ranking_config.sort_order == SortOrder.DESC:
                ranked_opportunities.sort(key=lambda x: x.rank_score, reverse=True)
            else:
                ranked_opportunities.sort(key=lambda x: x.rank_score)
            
            # Assign rank positions
            for i, ranked_opp in enumerate(ranked_opportunities, 1):
                ranked_opp.rank_position = (page - 1) * page_size + i
            
            # Calculate performance metrics
            ranking_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            result = RankingResult(
                ranked_opportunities=ranked_opportunities,
                total_count=total_count,
                filter_criteria=filter_criteria,
                ranking_config=ranking_config,
                user_preferences=user_preferences,
                ranking_time_ms=ranking_time_ms,
                cache_hit=False,
                page=page,
                page_size=page_size
            )
            
            # Cache the result
            if self.enable_caching:
                await cache_manager.set(
                    cache_key,
                    {
                        "ranked_opportunities": [opp.to_dict() for opp in ranked_opportunities],
                        "total_count": total_count,
                        "filter_criteria": filter_criteria.to_dict(),
                        "ranking_config": asdict(ranking_config),
                        "user_preferences": asdict(user_preferences) if user_preferences else None,
                        "ranking_time_ms": ranking_time_ms,
                        "page": page,
                        "page_size": page_size
                    },
                    ttl=self.cache_ttl
                )
            
            logger.info(
                "Opportunities ranked successfully",
                total_count=total_count,
                returned_count=len(ranked_opportunities),
                ranking_time_ms=ranking_time_ms,
                page=page
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Opportunity ranking failed: {e}", exc_info=True)
            raise
    
    async def _get_filtered_opportunities(
        self,
        db: AsyncSession,
        filter_criteria: FilterCriteria,
        page: int,
        page_size: int
    ) -> Tuple[List[Opportunity], int]:
        """Get opportunities matching filter criteria."""
        
        # Build base query
        query = select(Opportunity).options(
            selectinload(Opportunity.market_signals),
            selectinload(Opportunity.validations)
        )
        
        # Apply filters
        conditions = []
        
        # Status filter
        if filter_criteria.status:
            conditions.append(Opportunity.status.in_(filter_criteria.status))
        else:
            # Default to non-rejected opportunities
            conditions.append(Opportunity.status != OpportunityStatus.REJECTED)
        
        # AI solution types filter
        if filter_criteria.ai_solution_types:
            ai_types_condition = or_(*[
                func.json_contains(Opportunity.ai_solution_types, json.dumps(ai_type))
                for ai_type in filter_criteria.ai_solution_types
            ])
            conditions.append(ai_types_condition)
        
        # Target industries filter
        if filter_criteria.target_industries:
            industries_condition = or_(*[
                func.json_contains(Opportunity.target_industries, json.dumps(industry))
                for industry in filter_criteria.target_industries
            ])
            conditions.append(industries_condition)
        
        # Geographic scope filter
        if filter_criteria.geographic_scope:
            conditions.append(Opportunity.geographic_scope.in_(filter_criteria.geographic_scope))
        
        # Tags filter
        if filter_criteria.tags:
            tags_condition = or_(*[
                func.json_contains(Opportunity.tags, json.dumps(tag))
                for tag in filter_criteria.tags
            ])
            conditions.append(tags_condition)
        
        # Score-based filters
        if filter_criteria.min_validation_score is not None:
            conditions.append(Opportunity.validation_score >= filter_criteria.min_validation_score)
        if filter_criteria.max_validation_score is not None:
            conditions.append(Opportunity.validation_score <= filter_criteria.max_validation_score)
        
        if filter_criteria.min_ai_feasibility_score is not None:
            conditions.append(Opportunity.ai_feasibility_score >= filter_criteria.min_ai_feasibility_score)
        if filter_criteria.max_ai_feasibility_score is not None:
            conditions.append(Opportunity.ai_feasibility_score <= filter_criteria.max_ai_feasibility_score)
        
        if filter_criteria.min_confidence_rating is not None:
            conditions.append(Opportunity.confidence_rating >= filter_criteria.min_confidence_rating)
        if filter_criteria.max_confidence_rating is not None:
            conditions.append(Opportunity.confidence_rating <= filter_criteria.max_confidence_rating)
        
        # Implementation complexity filter
        if filter_criteria.implementation_complexity:
            conditions.append(Opportunity.implementation_complexity.in_(filter_criteria.implementation_complexity))
        
        # Time-based filters
        if filter_criteria.created_after:
            conditions.append(Opportunity.created_at >= filter_criteria.created_after)
        if filter_criteria.created_before:
            conditions.append(Opportunity.created_at <= filter_criteria.created_before)
        if filter_criteria.updated_after:
            conditions.append(Opportunity.updated_at >= filter_criteria.updated_after)
        if filter_criteria.updated_before:
            conditions.append(Opportunity.updated_at <= filter_criteria.updated_before)
        
        # Text search filter
        if filter_criteria.search_query:
            search_condition = or_(
                Opportunity.title.ilike(f"%{filter_criteria.search_query}%"),
                Opportunity.description.ilike(f"%{filter_criteria.search_query}%"),
                Opportunity.summary.ilike(f"%{filter_criteria.search_query}%")
            )
            conditions.append(search_condition)
        
        # Apply all conditions
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count(Opportunity.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        result = await db.execute(query)
        opportunities = result.scalars().all()
        
        return list(opportunities), total_count
    
    async def _calculate_ranking_scores(
        self,
        opportunities: List[Opportunity],
        ranking_config: RankingConfig,
        user_preferences: UserPreferences = None
    ) -> List[RankedOpportunity]:
        """Calculate ranking scores for opportunities."""
        
        ranked_opportunities = []
        
        for opportunity in opportunities:
            # Calculate base score from opportunity metrics
            base_score = await self._calculate_base_score(opportunity, ranking_config)
            
            # Calculate personalization score
            personalization_score = 0.0
            if ranking_config.enable_personalization and user_preferences:
                personalization_score = await self._calculate_personalization_score(
                    opportunity, user_preferences
                )
            
            # Calculate freshness score
            freshness_score = 0.0
            if ranking_config.enable_freshness_boost:
                freshness_score = self._calculate_freshness_score(opportunity)
            
            # Calculate trending score
            trending_score = 0.0
            if ranking_config.enable_trending_boost:
                trending_score = await self._calculate_trending_score(opportunity)
            
            # Combine scores with weights
            final_score = (
                base_score * (1.0 - ranking_config.personalization_weight - 
                             ranking_config.freshness_weight - ranking_config.trending_weight) +
                personalization_score * ranking_config.personalization_weight +
                freshness_score * ranking_config.freshness_weight +
                trending_score * ranking_config.trending_weight
            )
            
            # Create ranking factors for transparency
            ranking_factors = {
                "base_score": base_score,
                "personalization_score": personalization_score,
                "freshness_score": freshness_score,
                "trending_score": trending_score,
                "validation_score": opportunity.validation_score,
                "ai_feasibility_score": opportunity.ai_feasibility_score,
                "confidence_rating": opportunity.confidence_rating
            }
            
            ranked_opportunity = RankedOpportunity(
                opportunity=opportunity,
                rank_score=final_score,
                rank_position=0,  # Will be set after sorting
                base_score=base_score,
                personalization_score=personalization_score,
                freshness_score=freshness_score,
                trending_score=trending_score,
                ranking_factors=ranking_factors
            )
            
            ranked_opportunities.append(ranked_opportunity)
        
        return ranked_opportunities
    
    async def _calculate_base_score(
        self,
        opportunity: Opportunity,
        ranking_config: RankingConfig
    ) -> float:
        """Calculate base ranking score from opportunity metrics."""
        
        # Get primary score
        primary_score = self._get_opportunity_metric(opportunity, ranking_config.primary_criteria)
        weighted_score = primary_score * ranking_config.primary_weight
        
        # Add secondary scores
        for criteria, weight in ranking_config.secondary_criteria.items():
            secondary_score = self._get_opportunity_metric(opportunity, criteria)
            weighted_score += secondary_score * weight
        
        # Normalize to 0-100 scale
        return min(100.0, max(0.0, weighted_score))
    
    def _get_opportunity_metric(self, opportunity: Opportunity, criteria: RankingCriteria) -> float:
        """Get specific metric value from opportunity."""
        
        if criteria == RankingCriteria.VALIDATION_SCORE:
            return opportunity.validation_score or 0.0
        elif criteria == RankingCriteria.AI_FEASIBILITY:
            return opportunity.ai_feasibility_score or 0.0
        elif criteria == RankingCriteria.OVERALL_SCORE:
            # Calculate overall score from available metrics
            scores = [
                opportunity.validation_score or 0.0,
                opportunity.ai_feasibility_score or 0.0,
                opportunity.confidence_rating or 0.0
            ]
            return statistics.mean([s for s in scores if s > 0]) if any(s > 0 for s in scores) else 0.0
        elif criteria == RankingCriteria.MARKET_SIZE:
            # Extract market size from market_size_estimate JSON
            if opportunity.market_size_estimate:
                try:
                    market_data = json.loads(opportunity.market_size_estimate) if isinstance(opportunity.market_size_estimate, str) else opportunity.market_size_estimate
                    return market_data.get("size_score", 0.0)
                except:
                    return 0.0
            return 0.0
        elif criteria == RankingCriteria.COMPETITION_LEVEL:
            # Convert competition level to score (lower competition = higher score)
            if opportunity.competition_analysis:
                try:
                    comp_data = json.loads(opportunity.competition_analysis) if isinstance(opportunity.competition_analysis, str) else opportunity.competition_analysis
                    level = comp_data.get("competition_level", "medium")
                    return {"low": 100.0, "medium": 50.0, "high": 10.0}.get(level, 50.0)
                except:
                    return 50.0
            return 50.0
        elif criteria == RankingCriteria.IMPLEMENTATION_COMPLEXITY:
            # Convert complexity to score (lower complexity = higher score)
            complexity = opportunity.implementation_complexity or "medium"
            return {"low": 100.0, "medium": 50.0, "high": 10.0}.get(complexity, 50.0)
        elif criteria == RankingCriteria.CREATED_DATE:
            # More recent = higher score
            days_old = (datetime.utcnow() - opportunity.created_at).days
            return max(0.0, 100.0 - days_old)
        elif criteria == RankingCriteria.UPDATED_DATE:
            # More recently updated = higher score
            days_old = (datetime.utcnow() - opportunity.updated_at).days
            return max(0.0, 100.0 - days_old)
        elif criteria == RankingCriteria.ENGAGEMENT_SCORE:
            # Calculate engagement from market signals
            if opportunity.market_signals:
                total_engagement = sum(
                    (signal.upvotes or 0) + (signal.comments_count or 0)
                    for signal in opportunity.market_signals
                )
                return min(100.0, total_engagement / 10)  # Normalize
            return 0.0
        else:
            return 0.0
    
    async def _calculate_personalization_score(
        self,
        opportunity: Opportunity,
        user_preferences: UserPreferences
    ) -> float:
        """Calculate personalization score based on user preferences."""
        
        if not user_preferences:
            return 0.0
        
        personalization_score = 0.0
        
        # AI solution type preference
        if user_preferences.preferred_ai_types and opportunity.ai_solution_types:
            try:
                opp_ai_types = json.loads(opportunity.ai_solution_types) if isinstance(opportunity.ai_solution_types, str) else opportunity.ai_solution_types
                if opp_ai_types:
                    ai_match = len(set(user_preferences.preferred_ai_types) & set(opp_ai_types))
                    ai_score = (ai_match / len(user_preferences.preferred_ai_types)) * 100
                    personalization_score += ai_score * user_preferences.ai_type_weight
            except:
                pass
        
        # Industry preference
        if user_preferences.preferred_industries and opportunity.target_industries:
            try:
                opp_industries = json.loads(opportunity.target_industries) if isinstance(opportunity.target_industries, str) else opportunity.target_industries
                if opp_industries:
                    industry_match = len(set(user_preferences.preferred_industries) & set(opp_industries))
                    industry_score = (industry_match / len(user_preferences.preferred_industries)) * 100
                    personalization_score += industry_score * user_preferences.industry_weight
            except:
                pass
        
        # Complexity preference
        if user_preferences.preferred_complexity_levels and opportunity.implementation_complexity:
            if opportunity.implementation_complexity in user_preferences.preferred_complexity_levels:
                personalization_score += 100.0 * user_preferences.complexity_weight
        
        # Interaction history boost
        if opportunity.id in user_preferences.bookmarked_opportunities:
            personalization_score += 20.0  # Boost for bookmarked opportunities
        
        if opportunity.id in user_preferences.validated_opportunities:
            personalization_score += 15.0  # Boost for previously validated opportunities
        
        return min(100.0, personalization_score)
    
    def _calculate_freshness_score(self, opportunity: Opportunity) -> float:
        """Calculate freshness score based on creation and update times."""
        
        now = datetime.utcnow()
        
        # Score based on creation time (more recent = higher score)
        created_days_ago = (now - opportunity.created_at).days
        creation_score = max(0.0, 100.0 - created_days_ago * 2)  # Decay by 2 points per day
        
        # Score based on update time
        updated_days_ago = (now - opportunity.updated_at).days
        update_score = max(0.0, 100.0 - updated_days_ago * 1)  # Decay by 1 point per day
        
        # Combine scores (favor recent updates)
        freshness_score = (creation_score * 0.3) + (update_score * 0.7)
        
        return freshness_score
    
    async def _calculate_trending_score(self, opportunity: Opportunity) -> float:
        """Calculate trending score based on recent validation activity."""
        
        if not opportunity.validations:
            return 0.0
        
        # Look at validations in the last 7 days
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        recent_validations = [
            v for v in opportunity.validations
            if v.validated_at >= cutoff_date
        ]
        
        if not recent_validations:
            return 0.0
        
        # Calculate trending score based on validation velocity and quality
        validation_count = len(recent_validations)
        avg_validation_score = statistics.mean([v.score for v in recent_validations])
        
        # Trending score combines volume and quality
        trending_score = min(100.0, (validation_count * 10) + (avg_validation_score * 5))
        
        return trending_score
    
    def _generate_cache_key(
        self,
        filter_criteria: FilterCriteria,
        ranking_config: RankingConfig,
        user_preferences: UserPreferences,
        page: int,
        page_size: int
    ) -> str:
        """Generate cache key for ranking query."""
        
        key_parts = [
            "ranking",
            str(hash(json.dumps(filter_criteria.to_dict(), sort_keys=True))),
            str(hash(json.dumps(asdict(ranking_config), sort_keys=True))),
            str(hash(json.dumps(asdict(user_preferences), sort_keys=True))) if user_preferences else "no_prefs",
            f"page_{page}",
            f"size_{page_size}"
        ]
        
        return ":".join(key_parts)
    
    async def get_user_preferences(
        self,
        db: AsyncSession,
        user_id: str
    ) -> UserPreferences:
        """Get or create user preferences with learning from interaction history."""
        
        # Try to get cached preferences first
        cache_key = f"user_preferences:{user_id}"
        cached_prefs = await cache_manager.get(cache_key)
        
        if cached_prefs:
            return UserPreferences(**cached_prefs)
        
        # Get user from database
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            # Return default preferences for unknown user
            return UserPreferences(user_id=user_id)
        
        # Create preferences from user profile and learn from interactions
        preferences = UserPreferences(user_id=user_id)
        
        # TODO: Implement learning from user interaction history
        # This would analyze user's past views, bookmarks, validations to infer preferences
        
        # Cache the preferences
        await cache_manager.set(
            cache_key,
            asdict(preferences),
            ttl=self.learning_update_interval
        )
        
        return preferences
    
    async def update_user_preferences(
        self,
        db: AsyncSession,
        user_id: str,
        preferences: UserPreferences
    ) -> None:
        """Update user preferences and clear cache."""
        
        # Update cache
        cache_key = f"user_preferences:{user_id}"
        await cache_manager.set(
            cache_key,
            asdict(preferences),
            ttl=self.learning_update_interval
        )
        
        # TODO: Persist preferences to database if needed
        
        logger.info("User preferences updated", user_id=user_id)
    
    async def get_trending_opportunities(
        self,
        db: AsyncSession,
        limit: int = 10,
        time_window_days: int = 7
    ) -> List[RankedOpportunity]:
        """Get trending opportunities based on recent validation activity."""
        
        # Configure for trending ranking
        trending_config = RankingConfig(
            primary_criteria=RankingCriteria.VALIDATION_SCORE,
            enable_trending_boost=True,
            trending_weight=0.6,
            enable_freshness_boost=True,
            freshness_weight=0.3
        )
        
        # Filter for recent opportunities
        filter_criteria = FilterCriteria(
            created_after=datetime.utcnow() - timedelta(days=time_window_days * 2),
            status=[OpportunityStatus.VALIDATED, OpportunityStatus.VALIDATING]
        )
        
        result = await self.rank_opportunities(
            db=db,
            filter_criteria=filter_criteria,
            ranking_config=trending_config,
            page_size=limit
        )
        
        return result.ranked_opportunities
    
    async def get_personalized_recommendations(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 20
    ) -> List[RankedOpportunity]:
        """Get personalized opportunity recommendations for a user."""
        
        # Get user preferences
        user_preferences = await self.get_user_preferences(db, user_id)
        
        # Configure for personalized ranking
        personalized_config = RankingConfig(
            enable_personalization=True,
            personalization_weight=0.5,
            enable_freshness_boost=True,
            freshness_weight=0.2,
            enable_trending_boost=True,
            trending_weight=0.3
        )
        
        # Filter based on user preferences
        filter_criteria = FilterCriteria(
            ai_solution_types=user_preferences.preferred_ai_types if user_preferences.preferred_ai_types else None,
            target_industries=user_preferences.preferred_industries if user_preferences.preferred_industries else None,
            implementation_complexity=user_preferences.preferred_complexity_levels if user_preferences.preferred_complexity_levels else None,
            status=[OpportunityStatus.VALIDATED, OpportunityStatus.VALIDATING]
        )
        
        result = await self.rank_opportunities(
            db=db,
            filter_criteria=filter_criteria,
            ranking_config=personalized_config,
            user_preferences=user_preferences,
            page_size=limit
        )
        
        return result.ranked_opportunities


# Global ranking system instance
opportunity_ranking_system = OpportunityRankingSystem()