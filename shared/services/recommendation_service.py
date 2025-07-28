"""Recommendation service for personalized opportunity recommendations.

Supports Requirements 6.1.3 (Personalized recommendation engine and user preference learning).
"""

import json
import math
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload

from shared.models.user import User
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.user_interaction import UserInteraction, UserPreference, InteractionType, RecommendationFeedback
from shared.schemas.opportunity import OpportunityRecommendationRequest
from shared.cache import cache_manager, CacheKeys
from shared.vector_db import opportunity_vector_service
from shared.services.ai_service import ai_service
import structlog

logger = structlog.get_logger(__name__)


class RecommendationService:
    """Service for generating personalized opportunity recommendations."""
    
    async def get_personalized_recommendations(
        self, 
        db: AsyncSession, 
        request: OpportunityRecommendationRequest
    ) -> List[Opportunity]:
        """Generate personalized recommendations using multiple algorithms.
        
        Supports Requirements 6.1.3 (Personalized recommendation engine).
        
        Args:
            db: Database session
            request: Recommendation request parameters
            
        Returns:
            List of recommended opportunities
        """
        # Try cache first
        cache_key = CacheKeys.format_key(
            CacheKeys.OPPORTUNITY_RECOMMENDATIONS, 
            user_id=request.user_id,
            limit=request.limit,
            ai_types=str(sorted(request.ai_solution_types or [])),
            industries=str(sorted(request.industries or []))
        )
        
        cached_recommendations = None
        if cache_manager is not None:
            try:
                cached_recommendations = await cache_manager.get(cache_key)
                if cached_recommendations:
                    # Fetch opportunities from cached IDs
                    opportunity_ids = cached_recommendations.get("opportunity_ids", [])
                    if opportunity_ids:
                        query = select(Opportunity).options(
                            selectinload(Opportunity.validations)
                        ).where(Opportunity.id.in_(opportunity_ids))
                        result = await db.execute(query)
                        opportunities = result.scalars().all()
                        
                        # Maintain order from cache
                        id_to_opp = {opp.id: opp for opp in opportunities}
                        ordered_opportunities = [id_to_opp[opp_id] for opp_id in opportunity_ids if opp_id in id_to_opp]
                        
                        if len(ordered_opportunities) >= request.limit * 0.8:  # If we have most cached results
                            logger.info("Returning cached recommendations", user_id=request.user_id, count=len(ordered_opportunities))
                            return ordered_opportunities[:request.limit]
            except Exception as e:
                logger.warning("Failed to retrieve cached recommendations", error=str(e))
        
        # Get user preferences
        user_preferences = await self.get_or_create_user_preferences(db, request.user_id)
        
        # Generate recommendations using multiple algorithms
        recommendations = await self._generate_hybrid_recommendations(db, request, user_preferences)
        
        # Cache results
        if cache_manager is not None and recommendations:
            try:
                cache_data = {
                    "opportunity_ids": [opp.id for opp in recommendations],
                    "generated_at": datetime.utcnow().isoformat(),
                    "algorithm": "hybrid"
                }
                await cache_manager.set(cache_key, cache_data, expire=1800)  # 30 minutes
            except Exception as e:
                logger.warning("Failed to cache recommendations", error=str(e))
        
        logger.info(
            "Generated personalized recommendations",
            user_id=request.user_id,
            recommendation_count=len(recommendations),
            algorithm="hybrid"
        )
        
        return recommendations
    
    async def _generate_hybrid_recommendations(
        self,
        db: AsyncSession,
        request: OpportunityRecommendationRequest,
        user_preferences: UserPreference
    ) -> List[Opportunity]:
        """Generate recommendations using a hybrid approach combining multiple algorithms."""
        
        # Get base opportunities (high quality, not viewed if requested)
        base_opportunities = await self._get_base_opportunities(db, request, user_preferences)
        
        if not base_opportunities:
            return []
        
        # Apply different recommendation algorithms
        algorithms = [
            ("collaborative_filtering", 0.3),
            ("content_based", 0.4),
            ("popularity_based", 0.2),
            ("semantic_similarity", 0.1)
        ]
        
        # Score opportunities using each algorithm
        opportunity_scores = {}
        
        for algorithm, weight in algorithms:
            try:
                if algorithm == "collaborative_filtering":
                    scores = await self._collaborative_filtering_scores(db, request.user_id, base_opportunities)
                elif algorithm == "content_based":
                    scores = await self._content_based_scores(db, request.user_id, base_opportunities, user_preferences)
                elif algorithm == "popularity_based":
                    scores = await self._popularity_based_scores(base_opportunities)
                elif algorithm == "semantic_similarity":
                    scores = await self._semantic_similarity_scores(db, request.user_id, base_opportunities)
                else:
                    continue
                
                # Apply weight and combine scores
                for opp_id, score in scores.items():
                    if opp_id not in opportunity_scores:
                        opportunity_scores[opp_id] = 0.0
                    opportunity_scores[opp_id] += score * weight
                    
            except Exception as e:
                logger.warning(f"Failed to apply {algorithm} algorithm", error=str(e))
                continue
        
        # Sort opportunities by combined score
        sorted_opportunities = sorted(
            base_opportunities,
            key=lambda opp: opportunity_scores.get(opp.id, 0.0),
            reverse=True
        )
        
        # Apply diversity and freshness factors
        final_recommendations = await self._apply_diversity_and_freshness(
            db, sorted_opportunities, request, user_preferences
        )
        
        return final_recommendations[:request.limit]
    
    async def _get_base_opportunities(
        self,
        db: AsyncSession,
        request: OpportunityRecommendationRequest,
        user_preferences: UserPreference
    ) -> List[Opportunity]:
        """Get base set of high-quality opportunities for recommendation."""
        
        query = select(Opportunity).options(
            selectinload(Opportunity.validations),
            selectinload(Opportunity.interactions)
        ).where(
            and_(
                Opportunity.status.in_([OpportunityStatus.VALIDATED, OpportunityStatus.VALIDATING]),
                Opportunity.validation_score >= user_preferences.min_validation_score
            )
        )
        
        # Apply user-specified filters
        filters = []
        
        if request.ai_solution_types:
            # This would require JSON querying - simplified for now
            pass
        
        if request.industries:
            # This would require JSON querying - simplified for now
            pass
        
        # Exclude viewed opportunities if requested
        if not request.include_viewed:
            viewed_subquery = select(UserInteraction.opportunity_id).where(
                and_(
                    UserInteraction.user_id == request.user_id,
                    UserInteraction.interaction_type.in_([InteractionType.VIEW, InteractionType.CLICK]),
                    UserInteraction.opportunity_id.isnot(None)
                )
            )
            query = query.where(Opportunity.id.not_in(viewed_subquery))
        
        # Apply filters
        if filters:
            query = query.where(and_(*filters))
        
        # Get more opportunities than needed for better recommendation quality
        query = query.limit(request.limit * 5)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def _collaborative_filtering_scores(
        self,
        db: AsyncSession,
        user_id: str,
        opportunities: List[Opportunity]
    ) -> Dict[str, float]:
        """Generate scores based on collaborative filtering (users with similar preferences)."""
        
        # Find users with similar interaction patterns
        similar_users = await self._find_similar_users(db, user_id)
        
        if not similar_users:
            return {opp.id: 0.0 for opp in opportunities}
        
        # Get interactions from similar users
        similar_user_ids = [user["user_id"] for user in similar_users]
        
        interactions_query = select(UserInteraction).where(
            and_(
                UserInteraction.user_id.in_(similar_user_ids),
                UserInteraction.opportunity_id.in_([opp.id for opp in opportunities]),
                UserInteraction.interaction_type.in_([InteractionType.VIEW, InteractionType.CLICK, InteractionType.BOOKMARK])
            )
        )
        
        result = await db.execute(interactions_query)
        interactions = result.scalars().all()
        
        # Calculate scores based on similar user interactions
        scores = {}
        for opp in opportunities:
            score = 0.0
            interaction_count = 0
            
            for interaction in interactions:
                if interaction.opportunity_id == opp.id:
                    # Find similarity weight for this user
                    user_similarity = next(
                        (u["similarity"] for u in similar_users if u["user_id"] == interaction.user_id),
                        0.0
                    )
                    
                    # Weight by interaction type and user similarity
                    interaction_weight = {
                        InteractionType.VIEW: 1.0,
                        InteractionType.CLICK: 2.0,
                        InteractionType.BOOKMARK: 3.0
                    }.get(interaction.interaction_type, 1.0)
                    
                    score += user_similarity * interaction_weight
                    interaction_count += 1
            
            # Normalize by interaction count
            if interaction_count > 0:
                score = score / interaction_count
            
            scores[opp.id] = min(1.0, score)  # Cap at 1.0
        
        return scores
    
    async def _content_based_scores(
        self,
        db: AsyncSession,
        user_id: str,
        opportunities: List[Opportunity],
        user_preferences: UserPreference
    ) -> Dict[str, float]:
        """Generate scores based on content similarity to user preferences."""
        
        scores = {}
        
        # Parse user preferences
        preferred_ai_types = {}
        preferred_industries = {}
        
        if user_preferences.preferred_ai_types:
            try:
                preferred_ai_types = json.loads(user_preferences.preferred_ai_types)
            except json.JSONDecodeError:
                pass
        
        if user_preferences.preferred_industries:
            try:
                preferred_industries = json.loads(user_preferences.preferred_industries)
            except json.JSONDecodeError:
                pass
        
        for opp in opportunities:
            score = 0.0
            factors = 0
            
            # AI solution type matching
            if preferred_ai_types and opp.ai_solution_types:
                try:
                    opp_ai_types = json.loads(opp.ai_solution_types)
                    if isinstance(opp_ai_types, list):
                        ai_score = 0.0
                        for ai_type in opp_ai_types:
                            if ai_type in preferred_ai_types:
                                ai_score += preferred_ai_types[ai_type]
                        
                        if len(opp_ai_types) > 0:
                            ai_score = ai_score / len(opp_ai_types)
                            score += ai_score
                            factors += 1
                except json.JSONDecodeError:
                    pass
            
            # Industry matching
            if preferred_industries and opp.target_industries:
                try:
                    opp_industries = json.loads(opp.target_industries)
                    if isinstance(opp_industries, list):
                        industry_score = 0.0
                        for industry in opp_industries:
                            if industry in preferred_industries:
                                industry_score += preferred_industries[industry]
                        
                        if len(opp_industries) > 0:
                            industry_score = industry_score / len(opp_industries)
                            score += industry_score
                            factors += 1
                except json.JSONDecodeError:
                    pass
            
            # Complexity preference
            if user_preferences.preferred_complexity and opp.implementation_complexity:
                if user_preferences.preferred_complexity == opp.implementation_complexity:
                    score += 1.0
                    factors += 1
            
            # Validation score preference (higher is better)
            if opp.validation_score >= user_preferences.min_validation_score:
                validation_bonus = min(1.0, (opp.validation_score - user_preferences.min_validation_score) / 5.0)
                score += validation_bonus
                factors += 1
            
            # Normalize by number of factors
            if factors > 0:
                score = score / factors
            
            scores[opp.id] = min(1.0, score)
        
        return scores
    
    async def _popularity_based_scores(self, opportunities: List[Opportunity]) -> Dict[str, float]:
        """Generate scores based on opportunity popularity metrics."""
        
        scores = {}
        
        # Calculate popularity metrics
        max_validation_score = max((opp.validation_score for opp in opportunities), default=1.0)
        max_interaction_count = max(
            (len(opp.interactions) for opp in opportunities), 
            default=1
        )
        
        for opp in opportunities:
            # Combine validation score and interaction count
            validation_factor = opp.validation_score / max_validation_score if max_validation_score > 0 else 0
            interaction_factor = len(opp.interactions) / max_interaction_count if max_interaction_count > 0 else 0
            
            # Weight validation more heavily than interactions
            popularity_score = (validation_factor * 0.7) + (interaction_factor * 0.3)
            
            scores[opp.id] = min(1.0, popularity_score)
        
        return scores
    
    async def _semantic_similarity_scores(
        self,
        db: AsyncSession,
        user_id: str,
        opportunities: List[Opportunity]
    ) -> Dict[str, float]:
        """Generate scores based on semantic similarity to user's past interactions."""
        
        # Get user's past interactions to understand their interests
        interactions_query = select(UserInteraction).where(
            and_(
                UserInteraction.user_id == user_id,
                UserInteraction.search_query.isnot(None),
                UserInteraction.interaction_type == InteractionType.SEARCH
            )
        ).order_by(desc(UserInteraction.created_at)).limit(10)
        
        result = await db.execute(interactions_query)
        past_interactions = result.scalars().all()
        
        if not past_interactions:
            return {opp.id: 0.0 for opp in opportunities}
        
        try:
            # Combine recent search queries
            search_queries = [interaction.search_query for interaction in past_interactions if interaction.search_query]
            
            if not search_queries:
                return {opp.id: 0.0 for opp in opportunities}
            
            combined_query = " ".join(search_queries[-3:])  # Use last 3 searches
            
            # Generate embedding for user's search pattern
            query_embedding = await ai_service.generate_search_query_embedding(combined_query)
            
            # Find similar opportunities using vector search
            similar_opportunities = await opportunity_vector_service.find_similar_opportunities(
                query_embedding=query_embedding,
                top_k=len(opportunities),
                filters={"id": {"$in": [opp.id for opp in opportunities]}}
            )
            
            # Convert to scores
            scores = {}
            for result in similar_opportunities:
                scores[result["id"]] = result["score"]
            
            # Fill in missing scores
            for opp in opportunities:
                if opp.id not in scores:
                    scores[opp.id] = 0.0
            
            return scores
            
        except Exception as e:
            logger.warning("Failed to generate semantic similarity scores", error=str(e))
            return {opp.id: 0.0 for opp in opportunities}
    
    async def _apply_diversity_and_freshness(
        self,
        db: AsyncSession,
        opportunities: List[Opportunity],
        request: OpportunityRecommendationRequest,
        user_preferences: UserPreference
    ) -> List[Opportunity]:
        """Apply diversity and freshness factors to recommendations."""
        
        if not opportunities:
            return []
        
        # Group opportunities by AI solution type and industry for diversity
        ai_type_groups = {}
        industry_groups = {}
        
        for opp in opportunities:
            # Group by AI types
            if opp.ai_solution_types:
                try:
                    ai_types = json.loads(opp.ai_solution_types)
                    if isinstance(ai_types, list):
                        for ai_type in ai_types:
                            if ai_type not in ai_type_groups:
                                ai_type_groups[ai_type] = []
                            ai_type_groups[ai_type].append(opp)
                except json.JSONDecodeError:
                    pass
            
            # Group by industries
            if opp.target_industries:
                try:
                    industries = json.loads(opp.target_industries)
                    if isinstance(industries, list):
                        for industry in industries:
                            if industry not in industry_groups:
                                industry_groups[industry] = []
                            industry_groups[industry].append(opp)
                except json.JSONDecodeError:
                    pass
        
        # Select diverse recommendations
        selected = []
        used_ai_types = set()
        used_industries = set()
        
        # First pass: select top opportunities with diversity constraints
        for opp in opportunities:
            if len(selected) >= request.limit:
                break
            
            # Check diversity constraints
            opp_ai_types = set()
            opp_industries = set()
            
            if opp.ai_solution_types:
                try:
                    ai_types = json.loads(opp.ai_solution_types)
                    if isinstance(ai_types, list):
                        opp_ai_types = set(ai_types)
                except json.JSONDecodeError:
                    pass
            
            if opp.target_industries:
                try:
                    industries = json.loads(opp.target_industries)
                    if isinstance(industries, list):
                        opp_industries = set(industries)
                except json.JSONDecodeError:
                    pass
            
            # Apply diversity rules (allow some overlap but prefer diversity)
            ai_overlap = len(opp_ai_types & used_ai_types)
            industry_overlap = len(opp_industries & used_industries)
            
            # Allow if it's diverse enough or if we don't have enough recommendations yet
            if (len(selected) < request.limit // 2 or 
                ai_overlap <= 1 or 
                industry_overlap <= 1):
                selected.append(opp)
                used_ai_types.update(opp_ai_types)
                used_industries.update(opp_industries)
        
        # Second pass: fill remaining slots with best remaining opportunities
        remaining_slots = request.limit - len(selected)
        if remaining_slots > 0:
            remaining_opportunities = [opp for opp in opportunities if opp not in selected]
            selected.extend(remaining_opportunities[:remaining_slots])
        
        # Apply freshness boost for new opportunities if user prefers them
        if user_preferences.prefers_new_opportunities:
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            # Separate new and old opportunities
            new_opportunities = [opp for opp in selected if opp.created_at >= cutoff_date]
            old_opportunities = [opp for opp in selected if opp.created_at < cutoff_date]
            
            # Boost new opportunities in ranking
            final_recommendations = new_opportunities + old_opportunities
        else:
            final_recommendations = selected
        
        return final_recommendations
    
    async def _find_similar_users(self, db: AsyncSession, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find users with similar interaction patterns."""
        
        # Get current user's interactions
        user_interactions_query = select(UserInteraction).where(
            and_(
                UserInteraction.user_id == user_id,
                UserInteraction.opportunity_id.isnot(None)
            )
        )
        
        result = await db.execute(user_interactions_query)
        user_interactions = result.scalars().all()
        
        if not user_interactions:
            return []
        
        user_opportunity_ids = set(interaction.opportunity_id for interaction in user_interactions)
        
        # Find other users who interacted with similar opportunities
        similar_interactions_query = select(UserInteraction).where(
            and_(
                UserInteraction.user_id != user_id,
                UserInteraction.opportunity_id.in_(list(user_opportunity_ids))
            )
        )
        
        result = await db.execute(similar_interactions_query)
        similar_interactions = result.scalars().all()
        
        # Calculate similarity scores
        user_similarities = {}
        
        for interaction in similar_interactions:
            other_user_id = interaction.user_id
            
            if other_user_id not in user_similarities:
                user_similarities[other_user_id] = {
                    "user_id": other_user_id,
                    "common_opportunities": set(),
                    "total_interactions": 0
                }
            
            user_similarities[other_user_id]["common_opportunities"].add(interaction.opportunity_id)
            user_similarities[other_user_id]["total_interactions"] += 1
        
        # Calculate Jaccard similarity
        similar_users = []
        for other_user_id, data in user_similarities.items():
            common_count = len(data["common_opportunities"])
            
            # Get total opportunities for other user
            other_user_query = select(func.count(UserInteraction.opportunity_id.distinct())).where(
                and_(
                    UserInteraction.user_id == other_user_id,
                    UserInteraction.opportunity_id.isnot(None)
                )
            )
            result = await db.execute(other_user_query)
            other_user_total = result.scalar() or 0
            
            # Calculate Jaccard similarity
            union_size = len(user_opportunity_ids) + other_user_total - common_count
            similarity = common_count / union_size if union_size > 0 else 0.0
            
            if similarity > 0.1:  # Minimum similarity threshold
                similar_users.append({
                    "user_id": other_user_id,
                    "similarity": similarity,
                    "common_opportunities": common_count
                })
        
        # Sort by similarity and return top users
        similar_users.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_users[:limit]
    
    async def get_or_create_user_preferences(
        self, 
        db: AsyncSession, 
        user_id: str
    ) -> UserPreference:
        """Get existing user preferences or create default ones."""
        
        # Try to get existing preferences
        result = await db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        preferences = result.scalar_one_or_none()
        
        if preferences:
            return preferences
        
        # Create default preferences
        preferences = UserPreference(
            user_id=user_id,
            min_validation_score=5.0,
            prefers_trending=True,
            prefers_new_opportunities=True,
            confidence_score=0.0,
            interaction_count=0
        )
        
        db.add(preferences)
        await db.commit()
        await db.refresh(preferences)
        
        logger.info("Created default user preferences", user_id=user_id)
        
        return preferences
    
    async def update_user_preferences_from_interactions(
        self, 
        db: AsyncSession, 
        user_id: str
    ) -> Optional[UserPreference]:
        """Update user preferences based on their interaction history."""
        
        preferences = await self.get_or_create_user_preferences(db, user_id)
        
        # Get user's interactions with opportunities
        interactions_query = select(UserInteraction).options(
            selectinload(UserInteraction.opportunity)
        ).where(
            and_(
                UserInteraction.user_id == user_id,
                UserInteraction.opportunity_id.isnot(None)
            )
        ).order_by(desc(UserInteraction.created_at)).limit(100)  # Last 100 interactions
        
        result = await db.execute(interactions_query)
        interactions = result.scalars().all()
        
        if not interactions:
            return preferences
        
        # Analyze AI solution type preferences
        ai_type_counts = {}
        industry_counts = {}
        complexity_counts = {}
        
        total_weight = 0.0
        
        for interaction in interactions:
            if not interaction.opportunity:
                continue
            
            # Weight interactions by type and recency
            interaction_weight = {
                InteractionType.VIEW: 1.0,
                InteractionType.CLICK: 2.0,
                InteractionType.BOOKMARK: 3.0,
                InteractionType.VALIDATE: 2.5
            }.get(interaction.interaction_type, 1.0)
            
            # Apply recency decay
            days_ago = (datetime.utcnow() - interaction.created_at).days
            recency_weight = math.exp(-days_ago / 30.0)  # Decay over 30 days
            
            final_weight = interaction_weight * recency_weight
            total_weight += final_weight
            
            # Count AI solution types
            if interaction.opportunity.ai_solution_types:
                try:
                    ai_types = json.loads(interaction.opportunity.ai_solution_types)
                    if isinstance(ai_types, list):
                        for ai_type in ai_types:
                            ai_type_counts[ai_type] = ai_type_counts.get(ai_type, 0) + final_weight
                except json.JSONDecodeError:
                    pass
            
            # Count industries
            if interaction.opportunity.target_industries:
                try:
                    industries = json.loads(interaction.opportunity.target_industries)
                    if isinstance(industries, list):
                        for industry in industries:
                            industry_counts[industry] = industry_counts.get(industry, 0) + final_weight
                except json.JSONDecodeError:
                    pass
            
            # Count complexity preferences
            if interaction.opportunity.implementation_complexity:
                complexity = interaction.opportunity.implementation_complexity
                complexity_counts[complexity] = complexity_counts.get(complexity, 0) + final_weight
        
        # Update preferences with normalized scores
        if total_weight > 0:
            # Normalize AI type preferences
            if ai_type_counts:
                normalized_ai_types = {
                    ai_type: count / total_weight 
                    for ai_type, count in ai_type_counts.items()
                }
                preferences.preferred_ai_types = json.dumps(normalized_ai_types)
            
            # Normalize industry preferences
            if industry_counts:
                normalized_industries = {
                    industry: count / total_weight 
                    for industry, count in industry_counts.items()
                }
                preferences.preferred_industries = json.dumps(normalized_industries)
            
            # Set preferred complexity (most common)
            if complexity_counts:
                preferred_complexity = max(complexity_counts.items(), key=lambda x: x[1])[0]
                preferences.preferred_complexity = preferred_complexity
            
            # Update metadata
            preferences.interaction_count = len(interactions)
            preferences.confidence_score = min(1.0, len(interactions) / 50.0)  # Max confidence at 50 interactions
            preferences.last_updated = datetime.utcnow()
            
            await db.commit()
            await db.refresh(preferences)
            
            logger.info(
                "Updated user preferences from interactions",
                user_id=user_id,
                interaction_count=len(interactions),
                confidence_score=preferences.confidence_score
            )
        
        return preferences
    
    async def record_interaction(
        self,
        db: AsyncSession,
        user_id: str,
        interaction_type: InteractionType,
        opportunity_id: Optional[str] = None,
        search_query: Optional[str] = None,
        filters_applied: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        referrer_source: Optional[str] = None
    ) -> UserInteraction:
        """Record a user interaction for preference learning."""
        
        interaction = UserInteraction(
            user_id=user_id,
            opportunity_id=opportunity_id,
            interaction_type=interaction_type,
            search_query=search_query,
            filters_applied=filters_applied,
            duration_seconds=duration_seconds,
            referrer_source=referrer_source,
            engagement_score=self._calculate_engagement_score(interaction_type, duration_seconds)
        )
        
        db.add(interaction)
        await db.commit()
        await db.refresh(interaction)
        
        # Periodically update user preferences (every 10 interactions)
        interaction_count = await db.execute(
            select(func.count(UserInteraction.id)).where(UserInteraction.user_id == user_id)
        )
        count = interaction_count.scalar()
        
        if count % 10 == 0:  # Update preferences every 10 interactions
            await self.update_user_preferences_from_interactions(db, user_id)
        
        return interaction
    
    def _calculate_engagement_score(
        self, 
        interaction_type: InteractionType, 
        duration_seconds: Optional[int]
    ) -> float:
        """Calculate engagement score for an interaction."""
        
        base_scores = {
            InteractionType.VIEW: 1.0,
            InteractionType.CLICK: 2.0,
            InteractionType.BOOKMARK: 3.0,
            InteractionType.SHARE: 2.5,
            InteractionType.VALIDATE: 3.0,
            InteractionType.SEARCH: 0.5,
            InteractionType.FILTER: 0.3
        }
        
        base_score = base_scores.get(interaction_type, 1.0)
        
        # Adjust based on duration for view/click interactions
        if duration_seconds and interaction_type in [InteractionType.VIEW, InteractionType.CLICK]:
            # Longer engagement indicates higher interest
            duration_multiplier = min(2.0, 1.0 + (duration_seconds / 300.0))  # Max 2x for 5+ minutes
            base_score *= duration_multiplier
        
        return min(5.0, base_score)  # Cap at 5.0
    
    async def record_recommendation_feedback(
        self,
        db: AsyncSession,
        user_id: str,
        opportunity_id: str,
        is_relevant: bool,
        feedback_score: Optional[int] = None,
        feedback_text: Optional[str] = None,
        recommendation_algorithm: str = "hybrid",
        recommendation_score: float = 0.0,
        recommendation_rank: int = 1
    ) -> RecommendationFeedback:
        """Record user feedback on a recommendation.
        
        Supports Requirements 6.1.3 (User preference learning).
        
        Args:
            db: Database session
            user_id: User providing feedback
            opportunity_id: Opportunity being rated
            is_relevant: Whether the recommendation was relevant
            feedback_score: Optional 1-5 rating
            feedback_text: Optional text feedback
            recommendation_algorithm: Algorithm used for recommendation
            recommendation_score: Original recommendation score
            recommendation_rank: Position in recommendation list
            
        Returns:
            Created RecommendationFeedback instance
        """
        feedback = RecommendationFeedback(
            user_id=user_id,
            opportunity_id=opportunity_id,
            is_relevant=is_relevant,
            feedback_score=feedback_score,
            feedback_text=feedback_text,
            recommendation_algorithm=recommendation_algorithm,
            recommendation_score=recommendation_score,
            recommendation_rank=recommendation_rank
        )
        
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)
        
        # Update user preferences based on feedback
        await self._update_preferences_from_feedback(db, user_id, feedback)
        
        logger.info(
            "Recommendation feedback recorded",
            user_id=user_id,
            opportunity_id=opportunity_id,
            is_relevant=is_relevant,
            feedback_score=feedback_score
        )
        
        return feedback
    
    async def explain_recommendation(
        self,
        db: AsyncSession,
        user_id: str,
        opportunity_id: str
    ) -> Dict[str, Any]:
        """Explain why an opportunity was recommended to a user.
        
        Supports Requirements 6.1.3 (Personalized recommendation engine).
        
        Args:
            db: Database session
            user_id: User to explain recommendation for
            opportunity_id: Opportunity to explain
            
        Returns:
            Dictionary with explanation details
        """
        # Get user preferences
        user_preferences = await self.get_or_create_user_preferences(db, user_id)
        
        # Get opportunity details
        opportunity_query = select(Opportunity).options(
            selectinload(Opportunity.validations)
        ).where(Opportunity.id == opportunity_id)
        
        result = await db.execute(opportunity_query)
        opportunity = result.scalar_one_or_none()
        
        if not opportunity:
            return {"error": "Opportunity not found"}
        
        explanation = {
            "opportunity_id": opportunity_id,
            "recommendation_factors": [],
            "overall_score": 0.0,
            "confidence": user_preferences.confidence_score
        }
        
        total_score = 0.0
        factor_count = 0
        
        # Analyze AI solution type match
        if user_preferences.preferred_ai_types and opportunity.ai_solution_types:
            try:
                preferred_ai_types = json.loads(user_preferences.preferred_ai_types)
                opp_ai_types = json.loads(opportunity.ai_solution_types)
                
                if isinstance(opp_ai_types, list) and isinstance(preferred_ai_types, dict):
                    matching_types = []
                    ai_score = 0.0
                    
                    for ai_type in opp_ai_types:
                        if ai_type in preferred_ai_types:
                            matching_types.append(ai_type)
                            ai_score += preferred_ai_types[ai_type]
                    
                    if matching_types:
                        ai_score = ai_score / len(opp_ai_types)
                        total_score += ai_score
                        factor_count += 1
                        
                        explanation["recommendation_factors"].append({
                            "factor": "AI Solution Type Match",
                            "score": ai_score,
                            "description": f"This opportunity matches your preferred AI types: {', '.join(matching_types)}",
                            "weight": 0.4
                        })
            except json.JSONDecodeError:
                pass
        
        # Analyze industry match
        if user_preferences.preferred_industries and opportunity.target_industries:
            try:
                preferred_industries = json.loads(user_preferences.preferred_industries)
                opp_industries = json.loads(opportunity.target_industries)
                
                if isinstance(opp_industries, list) and isinstance(preferred_industries, dict):
                    matching_industries = []
                    industry_score = 0.0
                    
                    for industry in opp_industries:
                        if industry in preferred_industries:
                            matching_industries.append(industry)
                            industry_score += preferred_industries[industry]
                    
                    if matching_industries:
                        industry_score = industry_score / len(opp_industries)
                        total_score += industry_score
                        factor_count += 1
                        
                        explanation["recommendation_factors"].append({
                            "factor": "Industry Match",
                            "score": industry_score,
                            "description": f"This opportunity targets industries you're interested in: {', '.join(matching_industries)}",
                            "weight": 0.4
                        })
            except json.JSONDecodeError:
                pass
        
        # Analyze validation score
        if opportunity.validation_score >= user_preferences.min_validation_score:
            validation_factor = min(1.0, opportunity.validation_score / 10.0)
            total_score += validation_factor
            factor_count += 1
            
            explanation["recommendation_factors"].append({
                "factor": "Quality Score",
                "score": validation_factor,
                "description": f"This opportunity has a high validation score ({opportunity.validation_score:.1f}/10.0) which meets your quality standards",
                "weight": 0.2
            })
        
        # Calculate overall score
        if factor_count > 0:
            explanation["overall_score"] = total_score / factor_count
        
        # Add general factors
        if opportunity.status.value == "validated":
            explanation["recommendation_factors"].append({
                "factor": "Community Validated",
                "score": 1.0,
                "description": "This opportunity has been validated by the community",
                "weight": 0.1
            })
        
        if not explanation["recommendation_factors"]:
            explanation["recommendation_factors"].append({
                "factor": "General Recommendation",
                "score": 0.5,
                "description": "This opportunity was recommended based on general popularity and quality metrics",
                "weight": 1.0
            })
            explanation["overall_score"] = 0.5
        
        return explanation
    
    async def _update_preferences_from_feedback(
        self,
        db: AsyncSession,
        user_id: str,
        feedback: RecommendationFeedback
    ) -> None:
        """Update user preferences based on recommendation feedback."""
        
        try:
            # Get the opportunity details
            opportunity_query = select(Opportunity).where(Opportunity.id == feedback.opportunity_id)
            result = await db.execute(opportunity_query)
            opportunity = result.scalar_one_or_none()
            
            if not opportunity:
                return
            
            # Get user preferences
            preferences = await self.get_or_create_user_preferences(db, user_id)
            
            # Update preferences based on feedback
            learning_rate = 0.1  # How much to adjust preferences
            
            if feedback.is_relevant and feedback.feedback_score and feedback.feedback_score >= 4:
                # Positive feedback - strengthen preferences
                if opportunity.ai_solution_types:
                    try:
                        opp_ai_types = json.loads(opportunity.ai_solution_types)
                        preferred_ai_types = {}
                        
                        if preferences.preferred_ai_types:
                            preferred_ai_types = json.loads(preferences.preferred_ai_types)
                        
                        for ai_type in opp_ai_types:
                            current_score = preferred_ai_types.get(ai_type, 0.5)
                            preferred_ai_types[ai_type] = min(1.0, current_score + learning_rate)
                        
                        preferences.preferred_ai_types = json.dumps(preferred_ai_types)
                    except json.JSONDecodeError:
                        pass
                
                if opportunity.target_industries:
                    try:
                        opp_industries = json.loads(opportunity.target_industries)
                        preferred_industries = {}
                        
                        if preferences.preferred_industries:
                            preferred_industries = json.loads(preferences.preferred_industries)
                        
                        for industry in opp_industries:
                            current_score = preferred_industries.get(industry, 0.5)
                            preferred_industries[industry] = min(1.0, current_score + learning_rate)
                        
                        preferences.preferred_industries = json.dumps(preferred_industries)
                    except json.JSONDecodeError:
                        pass
            
            elif not feedback.is_relevant or (feedback.feedback_score and feedback.feedback_score <= 2):
                # Negative feedback - weaken preferences
                if opportunity.ai_solution_types:
                    try:
                        opp_ai_types = json.loads(opportunity.ai_solution_types)
                        preferred_ai_types = {}
                        
                        if preferences.preferred_ai_types:
                            preferred_ai_types = json.loads(preferences.preferred_ai_types)
                        
                        for ai_type in opp_ai_types:
                            current_score = preferred_ai_types.get(ai_type, 0.5)
                            preferred_ai_types[ai_type] = max(0.0, current_score - learning_rate)
                        
                        preferences.preferred_ai_types = json.dumps(preferred_ai_types)
                    except json.JSONDecodeError:
                        pass
            
            # Update confidence score
            preferences.confidence_score = min(1.0, preferences.confidence_score + 0.01)
            preferences.last_updated = datetime.utcnow()
            
            await db.commit()
            
        except Exception as e:
            logger.warning("Failed to update preferences from feedback", error=str(e))


# Global recommendation service instance
recommendation_service = RecommendationService()