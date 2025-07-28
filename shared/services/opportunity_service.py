"""Opportunity service for managing opportunities and related operations.

Supports Requirements 1.1-1.4 (Opportunity Discovery System),
Requirements 2.1-2.5 (Opportunity Validation Framework),
Requirements 3.1-3.5 (User-Friendly Opportunity Browser),
Requirements 6.1-6.5 (Opportunity Analytics and Insights),
Requirements 7.1-7.5 (Implementation Guidance System),
Requirements 8.1-8.5 (Business Intelligence and ROI Analysis).
"""

import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload, joinedload

from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.market_signal import MarketSignal
from shared.models.validation import ValidationResult
from shared.models.user import User
from shared.schemas.opportunity import (
    OpportunityCreate, 
    OpportunityUpdate, 
    OpportunityResponse,
    OpportunitySearchRequest,
    OpportunityRecommendationRequest
)
from shared.cache import CacheKeys
try:
    from shared.cache import cache_manager
except ImportError:
    cache_manager = None
from shared.vector_db import opportunity_vector_service
from shared.services.user_service import user_service
import structlog

logger = structlog.get_logger(__name__)


class OpportunityService:
    """Service for opportunity management and operations."""
    
    async def create_opportunity(
        self, 
        db: AsyncSession, 
        opportunity_data: OpportunityCreate,
        discovered_by_agent: Optional[str] = None
    ) -> Opportunity:
        """Create a new opportunity.
        
        Supports Requirements 1.1-1.4 (Opportunity Discovery System).
        
        Args:
            db: Database session
            opportunity_data: Opportunity creation data
            discovered_by_agent: Name of AI agent that discovered this opportunity
            
        Returns:
            Created opportunity instance
        """
        # Prepare JSON fields
        ai_solution_types_json = None
        if opportunity_data.ai_solution_types:
            ai_solution_types_json = json.dumps(opportunity_data.ai_solution_types)
        
        required_capabilities_json = None
        if opportunity_data.required_capabilities:
            required_capabilities_json = json.dumps(opportunity_data.required_capabilities)
        
        target_industries_json = None
        if opportunity_data.target_industries:
            target_industries_json = json.dumps(opportunity_data.target_industries)
        
        tags_json = None
        if opportunity_data.tags:
            tags_json = json.dumps(opportunity_data.tags)
        
        source_urls_json = None
        if opportunity_data.source_urls:
            source_urls_json = json.dumps(opportunity_data.source_urls)
        
        # Create opportunity
        opportunity = Opportunity(
            title=opportunity_data.title,
            description=opportunity_data.description,
            ai_solution_types=ai_solution_types_json,
            required_capabilities=required_capabilities_json,
            target_industries=target_industries_json,
            geographic_scope=opportunity_data.geographic_scope,
            tags=tags_json,
            source_urls=source_urls_json,
            discovery_method=opportunity_data.discovery_method or discovered_by_agent,
            status=OpportunityStatus.DISCOVERED
        )
        
        db.add(opportunity)
        await db.commit()
        await db.refresh(opportunity)
        
        logger.info(
            "Opportunity created",
            opportunity_id=opportunity.id,
            title=opportunity.title,
            ai_types=opportunity_data.ai_solution_types,
            discovered_by=discovered_by_agent
        )
        
        # Publish opportunity created event
        try:
            from shared.event_config import publish_opportunity_created
            await publish_opportunity_created(
                opportunity_id=opportunity.id,
                title=opportunity.title,
                description=opportunity.description,
                ai_solution_types=opportunity_data.ai_solution_types,
                discovery_method=discovered_by_agent,
                status=opportunity.status.value
            )
        except Exception as e:
            logger.warning("Failed to publish opportunity created event", error=str(e))
        
        # Clear relevant caches
        await self._clear_opportunity_caches()
        
        # Generate and store embedding for semantic search
        await self._generate_and_store_embedding(opportunity)
        
        # Initiate validation workflow (Requirement 2.1)
        await self._initiate_validation_workflow(db, opportunity)
        
        return opportunity
    
    async def get_opportunity_by_id(
        self, 
        db: AsyncSession, 
        opportunity_id: str,
        include_relationships: bool = True
    ) -> Optional[Opportunity]:
        """Get opportunity by ID with caching.
        
        Args:
            db: Database session
            opportunity_id: Opportunity identifier
            include_relationships: Whether to include related data
            
        Returns:
            Opportunity instance or None
        """
        # Try cache first
        cached_opportunity = None
        if cache_manager is not None:
            try:
                cache_key = CacheKeys.format_key(CacheKeys.OPPORTUNITY_DETAILS, opportunity_id=opportunity_id)
                cached_opportunity = await cache_manager.get(cache_key)
                if cached_opportunity and not include_relationships:
                    return Opportunity(**cached_opportunity) if isinstance(cached_opportunity, dict) else None
            except Exception:
                # If cache fails, continue to database query
                pass
        
        # Query database
        query = select(Opportunity).where(Opportunity.id == opportunity_id)
        
        if include_relationships:
            query = query.options(
                selectinload(Opportunity.market_signals),
                selectinload(Opportunity.validations),
                selectinload(Opportunity.ai_capability_assessment),
                selectinload(Opportunity.implementation_guide)
            )
        
        result = await db.execute(query)
        opportunity = result.scalar_one_or_none()
        
        # Cache result (basic data only)
        if opportunity and not include_relationships and cache_manager is not None:
            try:
                opportunity_dict = {
                    "id": opportunity.id,
                    "title": opportunity.title,
                    "description": opportunity.description,
                    "summary": opportunity.summary,
                    "status": opportunity.status.value,
                    "validation_score": opportunity.validation_score,
                    "ai_feasibility_score": opportunity.ai_feasibility_score
                }
                await cache_manager.set(cache_key, opportunity_dict, expire=1800)  # 30 minutes
            except Exception:
                # If cache fails, continue without caching
                pass
        
        return opportunity
    
    async def update_opportunity(
        self, 
        db: AsyncSession, 
        opportunity_id: str, 
        opportunity_data: OpportunityUpdate
    ) -> Optional[Opportunity]:
        """Update opportunity information.
        
        Args:
            db: Database session
            opportunity_id: Opportunity identifier
            opportunity_data: Update data
            
        Returns:
            Updated opportunity instance or None
        """
        opportunity = await self.get_opportunity_by_id(db, opportunity_id, include_relationships=False)
        if not opportunity:
            return None
        
        # Update fields
        update_data = opportunity_data.dict(exclude_unset=True)
        
        # Handle JSON fields
        json_fields = ["ai_solution_types", "target_industries", "tags"]
        for field in json_fields:
            if field in update_data and update_data[field] is not None:
                update_data[field] = json.dumps(update_data[field])
        
        # Apply updates
        for field, value in update_data.items():
            setattr(opportunity, field, value)
        
        await db.commit()
        await db.refresh(opportunity)
        
        logger.info(
            "Opportunity updated",
            opportunity_id=opportunity.id,
            updated_fields=list(update_data.keys())
        )
        
        # Publish opportunity updated event
        try:
            from shared.event_bus import EventType, publish_event
            await publish_event(
                event_type=EventType.OPPORTUNITY_UPDATED,
                payload={
                    "opportunity_id": opportunity.id,
                    "title": opportunity.title,
                    "updated_fields": list(update_data.keys()),
                    "status": opportunity.status.value,
                    "validation_score": opportunity.validation_score
                },
                source="opportunity_service"
            )
        except Exception as e:
            logger.warning("Failed to publish opportunity updated event", error=str(e))
        
        # Clear caches
        await self._clear_opportunity_caches(opportunity_id)
        
        return opportunity
    
    async def search_opportunities(
        self, 
        db: AsyncSession, 
        search_request: OpportunitySearchRequest,
        user_id: Optional[str] = None
    ) -> Tuple[List[Opportunity], int]:
        """Search opportunities with filtering and pagination.
        
        Supports Requirements 3.1-3.2 (Searchable interface and filtering).
        
        Args:
            db: Database session
            search_request: Search parameters
            user_id: Optional user ID for personalization
            
        Returns:
            Tuple of (opportunities list, total count)
        """
        # Build base query
        query = select(Opportunity).options(
            selectinload(Opportunity.market_signals),
            selectinload(Opportunity.validations)
        )
        
        # Apply filters
        filters = []
        
        # Status filter
        if search_request.status:
            filters.append(Opportunity.status.in_(search_request.status))
        else:
            # Default to non-rejected opportunities
            filters.append(Opportunity.status != OpportunityStatus.REJECTED)
        
        # Validation score filter
        if search_request.min_validation_score is not None:
            filters.append(Opportunity.validation_score >= search_request.min_validation_score)
        if search_request.max_validation_score is not None:
            filters.append(Opportunity.validation_score <= search_request.max_validation_score)
        
        # Market size filter
        if search_request.min_market_size is not None:
            # This would require parsing the JSON market_size_estimate
            # For now, we'll skip this complex filter
            pass
        
        # Geographic scope filter
        if search_request.geographic_scope:
            filters.append(Opportunity.geographic_scope.ilike(f"%{search_request.geographic_scope}%"))
        
        # Implementation complexity filter
        if search_request.implementation_complexity:
            filters.append(Opportunity.implementation_complexity.in_(search_request.implementation_complexity))
        
        # Apply all filters
        if filters:
            query = query.where(and_(*filters))
        
        # Text search (if query provided)
        if search_request.query:
            text_filter = or_(
                Opportunity.title.ilike(f"%{search_request.query}%"),
                Opportunity.description.ilike(f"%{search_request.query}%"),
                Opportunity.description.ilike(f"%{search_request.query}%")
            )
            query = query.where(text_filter)
        
        # Get total count
        count_query = select(func.count(Opportunity.id)).select_from(query.subquery())
        total_count_result = await db.execute(count_query)
        total_count = total_count_result.scalar()
        
        # Apply ordering
        query = query.order_by(
            desc(Opportunity.validation_score),
            desc(Opportunity.created_at)
        )
        
        # Apply pagination
        offset = search_request.get_offset()
        query = query.offset(offset).limit(search_request.page_size)
        
        # Execute query
        result = await db.execute(query)
        opportunities = result.scalars().all()
        
        logger.info(
            "Opportunity search completed",
            query=search_request.query,
            total_results=total_count,
            returned_results=len(opportunities),
            user_id=user_id
        )
        
        return list(opportunities), total_count
    
    async def get_personalized_recommendations(
        self, 
        db: AsyncSession, 
        request: OpportunityRecommendationRequest
    ) -> List[Opportunity]:
        """Get personalized opportunity recommendations.
        
        Supports Requirement 3.5 (Personalized recommendations based on user interests).
        
        Args:
            db: Database session
            request: Recommendation request parameters
            
        Returns:
            List of recommended opportunities
        """
        # Use the dedicated recommendation service
        from shared.services.recommendation_service import recommendation_service
        
        return await recommendation_service.get_personalized_recommendations(db, request)
    
    async def update_validation_scores(
        self, 
        db: AsyncSession, 
        opportunity_id: str
    ) -> Optional[Opportunity]:
        """Update opportunity validation scores based on community feedback.
        
        Supports Requirements 2.3, 2.5 (Confidence ratings and ranking updates).
        
        Args:
            db: Database session
            opportunity_id: Opportunity identifier
            
        Returns:
            Updated opportunity instance or None
        """
        opportunity = await self.get_opportunity_by_id(db, opportunity_id, include_relationships=True)
        if not opportunity:
            return None
        
        if not opportunity.validations:
            return opportunity
        
        # Calculate weighted validation score
        total_weighted_score = 0.0
        total_weight = 0.0
        validation_count = len(opportunity.validations)
        
        for validation in opportunity.validations:
            # Get validator's influence weight
            validator_weight = await user_service.get_user_influence_weight(db, validation.validator_id)
            
            # Weight the validation score
            weighted_score = validation.score * validator_weight
            total_weighted_score += weighted_score
            total_weight += validator_weight
        
        # Calculate final scores
        if total_weight > 0:
            new_validation_score = total_weighted_score / total_weight
            
            # Calculate confidence rating based on consensus and validator quality
            score_variance = sum(
                ((v.score - new_validation_score) ** 2) for v in opportunity.validations
            ) / validation_count
            
            # Higher confidence for lower variance and more validations
            confidence_rating = min(10.0, (10.0 - score_variance) * (validation_count / 10.0))
            
            # Update opportunity
            opportunity.validation_score = new_validation_score
            opportunity.confidence_rating = max(0.0, confidence_rating)
            
            # Update status based on validation score (Requirement 2.4)
            if new_validation_score < 3.0 and validation_count >= 3:
                opportunity.status = OpportunityStatus.REJECTED
            elif new_validation_score >= 6.0 and validation_count >= 2:
                opportunity.status = OpportunityStatus.VALIDATED
            else:
                opportunity.status = OpportunityStatus.VALIDATING
            
            await db.commit()
            await db.refresh(opportunity)
            
            logger.info(
                "Validation scores updated",
                opportunity_id=opportunity.id,
                new_score=new_validation_score,
                confidence=confidence_rating,
                validation_count=validation_count,
                status=opportunity.status
            )
        
        # Clear caches
        await self._clear_opportunity_caches(opportunity_id)
        
        return opportunity
    
    async def get_opportunity_analytics(
        self, 
        db: AsyncSession,
        timeframe_days: int = 30
    ) -> Dict[str, Any]:
        """Get opportunity analytics and insights.
        
        Supports Requirements 6.1-6.5 (Opportunity Analytics and Insights).
        
        Args:
            db: Database session
            timeframe_days: Timeframe for analytics
            
        Returns:
            Analytics data dictionary
        """
        cutoff_date = datetime.utcnow() - timedelta(days=timeframe_days)
        
        # Basic statistics
        total_opportunities = await db.execute(
            select(func.count(Opportunity.id))
        )
        total_count = total_opportunities.scalar()
        
        # Opportunities by status
        status_stats = await db.execute(
            select(
                Opportunity.status,
                func.count(Opportunity.id).label("count")
            ).group_by(Opportunity.status)
        )
        
        status_distribution = {
            row.status.value: row.count for row in status_stats
        }
        
        # Average validation score
        avg_score = await db.execute(
            select(func.avg(Opportunity.validation_score))
            .where(Opportunity.validation_score > 0)
        )
        average_validation_score = avg_score.scalar() or 0.0
        
        # Trending opportunities (high validation score, recent activity)
        trending_query = select(Opportunity).options(
            selectinload(Opportunity.validations)
        ).where(
            and_(
                Opportunity.status == OpportunityStatus.VALIDATED,
                Opportunity.validation_score >= 7.0,
                Opportunity.updated_at >= cutoff_date
            )
        ).order_by(
            desc(Opportunity.validation_score),
            desc(Opportunity.updated_at)
        ).limit(10)
        
        trending_result = await db.execute(trending_query)
        trending_opportunities = trending_result.scalars().all()
        
        analytics = {
            "total_opportunities": total_count,
            "opportunities_by_status": status_distribution,
            "average_validation_score": round(average_validation_score, 2),
            "trending_opportunities_count": len(trending_opportunities),
            "timeframe_days": timeframe_days,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        logger.info("Opportunity analytics generated", **analytics)
        
        return analytics
    
    async def _initiate_validation_workflow(
        self, 
        db: AsyncSession, 
        opportunity: Opportunity
    ):
        """Initiate validation workflow for new opportunity.
        
        Supports Requirement 2.1 (Initiate validation workflow).
        
        Args:
            db: Database session
            opportunity: Opportunity instance
        """
        # Parse AI solution types and industries for expert matching
        ai_types = []
        industries = []
        
        if opportunity.ai_solution_types:
            try:
                ai_types = json.loads(opportunity.ai_solution_types)
            except json.JSONDecodeError:
                pass
        
        if opportunity.target_industries:
            try:
                industries = json.loads(opportunity.target_industries)
            except json.JSONDecodeError:
                pass
        
        # Find relevant experts (Requirement 4.2)
        relevant_experts = await user_service.get_experts_for_opportunity(
            db, ai_types, industries
        )
        
        logger.info(
            "Validation workflow initiated",
            opportunity_id=opportunity.id,
            relevant_experts_count=len(relevant_experts),
            ai_types=ai_types,
            industries=industries
        )
        
        # TODO: Send notifications to relevant experts
        # This would be implemented when notification system is built
    
    async def _generate_and_store_embedding(self, opportunity: Opportunity):
        """Generate and store embedding for opportunity semantic search.
        
        Supports Requirements 6.1.2 (Semantic search with vector similarity).
        
        Args:
            opportunity: Opportunity instance
        """
        try:
            from shared.services.ai_service import ai_service
            
            # Prepare opportunity data for embedding
            opportunity_data = {
                "title": opportunity.title,
                "description": opportunity.description,
                "description": opportunity.description,
                "ai_solution_types": opportunity.ai_solution_types,
                "target_industries": opportunity.target_industries,
                "tags": opportunity.tags,
                "geographic_scope": opportunity.geographic_scope
            }
            
            # Generate embedding
            embedding = await ai_service.generate_opportunity_embedding(opportunity_data)
            
            # Prepare metadata for vector storage
            metadata = {
                "title": opportunity.title,
                "status": opportunity.status.value,
                "validation_score": opportunity.validation_score or 0.0,
                "ai_feasibility_score": opportunity.ai_feasibility_score or 0.0,
                "created_at": opportunity.created_at.isoformat(),
                "updated_at": opportunity.updated_at.isoformat()
            }
            
            # Add parsed JSON fields to metadata
            if opportunity.ai_solution_types:
                try:
                    ai_types = json.loads(opportunity.ai_solution_types)
                    if isinstance(ai_types, list):
                        metadata["ai_solution_types"] = ai_types
                except (json.JSONDecodeError, TypeError):
                    pass
            
            if opportunity.target_industries:
                try:
                    industries = json.loads(opportunity.target_industries)
                    if isinstance(industries, list):
                        metadata["target_industries"] = industries
                except (json.JSONDecodeError, TypeError):
                    pass
            
            if opportunity.tags:
                try:
                    tags = json.loads(opportunity.tags)
                    if isinstance(tags, list):
                        metadata["tags"] = tags
                except (json.JSONDecodeError, TypeError):
                    pass
            
            if opportunity.geographic_scope:
                metadata["geographic_scope"] = opportunity.geographic_scope
            
            if opportunity.implementation_complexity:
                metadata["implementation_complexity"] = opportunity.implementation_complexity
            
            # Store embedding in vector database
            success = await opportunity_vector_service.store_opportunity_embedding(
                opportunity_id=opportunity.id,
                embedding=embedding,
                metadata=metadata
            )
            
            if success:
                logger.info(
                    "Opportunity embedding stored successfully",
                    opportunity_id=opportunity.id,
                    embedding_dimension=len(embedding)
                )
            else:
                logger.warning(
                    "Failed to store opportunity embedding",
                    opportunity_id=opportunity.id
                )
                
        except Exception as e:
            logger.error(
                "Failed to generate and store opportunity embedding",
                opportunity_id=opportunity.id,
                error=str(e),
                exc_info=True
            )
            # Don't raise exception - embedding generation is not critical for opportunity creation
    
    async def semantic_search_opportunities(
        self, 
        db: AsyncSession, 
        search_request: OpportunitySearchRequest,
        user_id: Optional[str] = None
    ) -> Tuple[List[Opportunity], int]:
        """Semantic search opportunities using vector similarity.
        
        Supports Requirements 6.1.2 (Semantic search with vector similarity).
        
        Args:
            db: Database session
            search_request: Search parameters with query
            user_id: Optional user ID for personalization
            
        Returns:
            Tuple of (opportunities list, total count)
        """
        if not search_request.query:
            raise ValueError("Query is required for semantic search")
        
        try:
            # Generate embedding for search query
            from shared.services.ai_service import ai_service
            
            # Create filter context for embedding
            filter_context = {}
            if search_request.ai_solution_types:
                filter_context["ai_solution_types"] = search_request.ai_solution_types
            if search_request.target_industries:
                filter_context["target_industries"] = search_request.target_industries
            if search_request.tags:
                filter_context["tags"] = search_request.tags
            
            query_embedding = await ai_service.generate_search_query_embedding(
                search_request.query, filter_context
            )
            
            # Build vector search filters
            vector_filters = {}
            if search_request.status:
                vector_filters["status"] = {"$in": [s.value for s in search_request.status]}
            if search_request.min_validation_score is not None:
                vector_filters["validation_score"] = {"$gte": search_request.min_validation_score}
            if search_request.geographic_scope:
                vector_filters["geographic_scope"] = search_request.geographic_scope
            
            # Perform vector similarity search
            similar_opportunities = await opportunity_vector_service.find_similar_opportunities(
                query_embedding=query_embedding,
                top_k=min(search_request.page_size * 3, 100),  # Get more results for filtering
                filters=vector_filters
            )
            
            # Extract opportunity IDs and similarity scores
            opportunity_ids = [result["id"] for result in similar_opportunities]
            similarity_scores = {result["id"]: result["score"] for result in similar_opportunities}
            
            if not opportunity_ids:
                logger.info("No similar opportunities found in vector search", query=search_request.query)
                return [], 0
            
            # Fetch full opportunity data from database
            query = select(Opportunity).options(
                selectinload(Opportunity.market_signals),
                selectinload(Opportunity.validations)
            ).where(Opportunity.id.in_(opportunity_ids))
            
            # Apply additional filters
            filters = []
            
            if search_request.max_validation_score is not None:
                filters.append(Opportunity.validation_score <= search_request.max_validation_score)
            
            if search_request.implementation_complexity:
                filters.append(Opportunity.implementation_complexity.in_(search_request.implementation_complexity))
            
            if filters:
                query = query.where(and_(*filters))
            
            # Execute query
            result = await db.execute(query)
            opportunities = result.scalars().all()
            
            # Sort by similarity score (vector search results are already sorted)
            opportunities_dict = {opp.id: opp for opp in opportunities}
            sorted_opportunities = []
            
            for opp_id in opportunity_ids:
                if opp_id in opportunities_dict:
                    opp = opportunities_dict[opp_id]
                    # Add similarity score as metadata (could be used for ranking)
                    opp._similarity_score = similarity_scores[opp_id]
                    sorted_opportunities.append(opp)
            
            # Apply pagination
            total_count = len(sorted_opportunities)
            start_idx = search_request.get_offset()
            end_idx = start_idx + search_request.page_size
            paginated_opportunities = sorted_opportunities[start_idx:end_idx]
            
            logger.info(
                "Semantic search completed",
                query=search_request.query,
                vector_results=len(similar_opportunities),
                db_results=len(opportunities),
                final_results=len(paginated_opportunities),
                total_count=total_count,
                user_id=user_id
            )
            
            return paginated_opportunities, total_count
            
        except Exception as e:
            logger.error("Semantic search failed", error=str(e), query=search_request.query)
            # Fall back to regular text search
            logger.info("Falling back to regular text search")
            return await self.search_opportunities(db, search_request, user_id)
    
    async def get_search_facets(
        self, 
        db: AsyncSession, 
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get faceted search data for filtering opportunities.
        
        Supports Requirements 6.1.2 (Faceted search capabilities).
        
        Args:
            db: Database session
            query: Optional query to filter facets
            
        Returns:
            Dictionary of facet data with counts
        """
        try:
            # Build base query
            base_query = select(Opportunity).where(
                Opportunity.status != OpportunityStatus.REJECTED
            )
            
            # Apply text filter if query provided
            if query:
                text_filter = or_(
                    Opportunity.title.ilike(f"%{query}%"),
                    Opportunity.description.ilike(f"%{query}%"),
                    Opportunity.summary.ilike(f"%{query}%")
                )
                base_query = base_query.where(text_filter)
            
            # Get all opportunities for facet calculation
            result = await db.execute(base_query)
            opportunities = result.scalars().all()
            
            # Calculate facets
            facets = {
                "status": {},
                "ai_solution_types": {},
                "target_industries": {},
                "implementation_complexity": {},
                "geographic_scope": {},
                "validation_score_ranges": {
                    "0-2": 0,
                    "2-4": 0,
                    "4-6": 0,
                    "6-8": 0,
                    "8-10": 0
                },
                "tags": {}
            }
            
            for opp in opportunities:
                # Status facet
                status_key = opp.status.value
                facets["status"][status_key] = facets["status"].get(status_key, 0) + 1
                
                # Implementation complexity facet
                if opp.implementation_complexity:
                    complexity = opp.implementation_complexity
                    facets["implementation_complexity"][complexity] = facets["implementation_complexity"].get(complexity, 0) + 1
                
                # Geographic scope facet
                if opp.geographic_scope:
                    scope = opp.geographic_scope
                    facets["geographic_scope"][scope] = facets["geographic_scope"].get(scope, 0) + 1
                
                # Validation score ranges
                score = opp.validation_score or 0
                if score < 2:
                    facets["validation_score_ranges"]["0-2"] += 1
                elif score < 4:
                    facets["validation_score_ranges"]["2-4"] += 1
                elif score < 6:
                    facets["validation_score_ranges"]["4-6"] += 1
                elif score < 8:
                    facets["validation_score_ranges"]["6-8"] += 1
                else:
                    facets["validation_score_ranges"]["8-10"] += 1
                
                # AI solution types facet (JSON field)
                if opp.ai_solution_types:
                    try:
                        ai_types = json.loads(opp.ai_solution_types)
                        if isinstance(ai_types, list):
                            for ai_type in ai_types:
                                facets["ai_solution_types"][ai_type] = facets["ai_solution_types"].get(ai_type, 0) + 1
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # Target industries facet (JSON field)
                if opp.target_industries:
                    try:
                        industries = json.loads(opp.target_industries)
                        if isinstance(industries, list):
                            for industry in industries:
                                facets["target_industries"][industry] = facets["target_industries"].get(industry, 0) + 1
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # Tags facet (JSON field)
                if opp.tags:
                    try:
                        tags = json.loads(opp.tags)
                        if isinstance(tags, list):
                            for tag in tags:
                                facets["tags"][tag] = facets["tags"].get(tag, 0) + 1
                    except (json.JSONDecodeError, TypeError):
                        pass
            
            # Sort facets by count (descending) and limit to top items
            for facet_name, facet_data in facets.items():
                if facet_name != "validation_score_ranges" and isinstance(facet_data, dict):
                    # Sort by count and take top 20
                    sorted_items = sorted(facet_data.items(), key=lambda x: x[1], reverse=True)[:20]
                    facets[facet_name] = dict(sorted_items)
            
            # Add metadata
            facets["_metadata"] = {
                "total_opportunities": len(opportunities),
                "query": query,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(
                "Search facets calculated",
                query=query,
                total_opportunities=len(opportunities),
                facet_categories=len([k for k in facets.keys() if not k.startswith("_")])
            )
            
            return facets
            
        except Exception as e:
            logger.error("Failed to calculate search facets", error=str(e), query=query)
            # Return empty facets structure
            return {
                "status": {},
                "ai_solution_types": {},
                "target_industries": {},
                "implementation_complexity": {},
                "geographic_scope": {},
                "validation_score_ranges": {
                    "0-2": 0,
                    "2-4": 0,
                    "4-6": 0,
                    "6-8": 0,
                    "8-10": 0
                },
                "tags": {},
                "_metadata": {
                    "total_opportunities": 0,
                    "query": query,
                    "error": str(e),
                    "generated_at": datetime.utcnow().isoformat()
                }
            }
    
    async def _clear_opportunity_caches(self, opportunity_id: Optional[str] = None):
        """Clear opportunity-related cache entries.
        
        Args:
            opportunity_id: Specific opportunity ID to clear, or None for general caches
        """
        if cache_manager is not None and opportunity_id:
            try:
                cache_keys = [
                    CacheKeys.format_key(CacheKeys.OPPORTUNITY_DETAILS, opportunity_id=opportunity_id),
                ]
                for key in cache_keys:
                    await cache_manager.delete(key)
            except Exception:
                # If cache fails, continue without clearing
                pass
        
        # Clear general caches (would need pattern matching in production)
        # For now, we'll just log the cache clear
        logger.debug("Opportunity caches cleared", opportunity_id=opportunity_id)


# Global opportunity service instance
opportunity_service = OpportunityService()