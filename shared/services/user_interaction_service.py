"""Service layer for user interactions, bookmarks, and collections."""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func, and_, desc, or_
from sqlalchemy.exc import IntegrityError

from shared.models.user import User
from shared.models.opportunity import Opportunity
from shared.models.user_interaction import (
    UserInteraction, UserPreference, RecommendationFeedback, InteractionType
)
from shared.models.user_collection import UserCollection, BookmarkInteraction, collection_opportunities
from shared.schemas.user_interaction import (
    UserInteractionCreate, UserPreferenceUpdate, ActivitySummary,
    RecommendationFeedbackRequest, UserCollectionCreate, UserCollectionUpdate,
    CollectionOpportunityAdd
)
import logging

logger = logging.getLogger(__name__)


class UserInteractionService:
    """Service for managing user interactions and preferences."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_interaction(
        self, 
        user_id: str, 
        interaction_data: UserInteractionCreate
    ) -> UserInteraction:
        """Create a new user interaction record."""
        try:
            # Calculate engagement score based on interaction type and duration
            engagement_score = self._calculate_engagement_score(
                interaction_data.interaction_type,
                interaction_data.duration_seconds
            )
            
            # Convert filters to JSON string if present
            filters_json = None
            if interaction_data.filters_applied:
                filters_json = json.dumps(interaction_data.filters_applied)
            
            interaction = UserInteraction(
                user_id=user_id,
                opportunity_id=interaction_data.opportunity_id,
                interaction_type=interaction_data.interaction_type,
                duration_seconds=interaction_data.duration_seconds,
                search_query=interaction_data.search_query,
                filters_applied=filters_json,
                referrer_source=interaction_data.referrer_source,
                engagement_score=engagement_score
            )
            
            self.db.add(interaction)
            self.db.commit()
            self.db.refresh(interaction)
            
            # Update user preferences asynchronously
            await self._update_user_preferences(user_id, interaction)
            
            logger.info(f"Created interaction for user {user_id}: {interaction_data.interaction_type}")
            return interaction
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating interaction: {e}")
            raise
    
    def _calculate_engagement_score(
        self, 
        interaction_type: InteractionType, 
        duration_seconds: Optional[int]
    ) -> float:
        """Calculate engagement score based on interaction type and duration."""
        base_scores = {
            InteractionType.VIEW: 1.0,
            InteractionType.CLICK: 2.0,
            InteractionType.BOOKMARK: 5.0,
            InteractionType.SHARE: 4.0,
            InteractionType.VALIDATE: 6.0,
            InteractionType.SEARCH: 1.5,
            InteractionType.FILTER: 2.0
        }
        
        base_score = base_scores.get(interaction_type, 1.0)
        
        # Adjust score based on duration for view interactions
        if interaction_type == InteractionType.VIEW and duration_seconds:
            if duration_seconds > 300:  # 5+ minutes
                base_score *= 3.0
            elif duration_seconds > 120:  # 2+ minutes
                base_score *= 2.0
            elif duration_seconds > 30:  # 30+ seconds
                base_score *= 1.5
        
        return min(base_score, 10.0)  # Cap at 10.0
    
    async def _update_user_preferences(self, user_id: str, interaction: UserInteraction):
        """Update user preferences based on interaction patterns."""
        try:
            # Get or create user preferences
            result = self.db.execute(
                select(UserPreference).where(UserPreference.user_id == user_id)
            )
            preferences = result.scalar_one_or_none()
            
            if not preferences:
                preferences = UserPreference(user_id=user_id)
                self.db.add(preferences)
            
            # Update interaction count
            preferences.interaction_count += 1
            preferences.last_updated = datetime.utcnow()
            
            # Update confidence score based on interaction count
            preferences.confidence_score = min(preferences.interaction_count / 100.0, 1.0)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
            # Don't re-raise as this is a background update
    
    def get_user_interactions(
        self, 
        user_id: str, 
        interaction_type: Optional[InteractionType] = None,
        limit: int = 50
    ) -> List[UserInteraction]:
        """Get user interactions with optional filtering."""
        query = select(UserInteraction).where(UserInteraction.user_id == user_id)
        
        if interaction_type:
            query = query.where(UserInteraction.interaction_type == interaction_type)
        
        query = query.order_by(desc(UserInteraction.created_at)).limit(limit)
        
        result = self.db.execute(query)
        return result.scalars().all()
    
    def get_activity_summary(self, user_id: str, days: int = 30) -> ActivitySummary:
        """Get user activity summary for the specified number of days."""
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Get interaction counts by type
        result = self.db.execute(
            select(
                UserInteraction.interaction_type,
                func.count(UserInteraction.id).label('count'),
                func.avg(UserInteraction.engagement_score).label('avg_engagement')
            )
            .where(
                and_(
                    UserInteraction.user_id == user_id,
                    UserInteraction.created_at >= since_date
                )
            )
            .group_by(UserInteraction.interaction_type)
        )
        interaction_stats = result.all()
        
        # Calculate summary metrics
        total_interactions = sum(stat.count for stat in interaction_stats)
        recent_views = next(
            (stat.count for stat in interaction_stats if stat.interaction_type == InteractionType.VIEW), 
            0
        )
        searches_count = next(
            (stat.count for stat in interaction_stats if stat.interaction_type == InteractionType.SEARCH), 
            0
        )
        validations_count = next(
            (stat.count for stat in interaction_stats if stat.interaction_type == InteractionType.VALIDATE), 
            0
        )
        
        avg_engagement = sum(stat.avg_engagement * stat.count for stat in interaction_stats) / max(total_interactions, 1)
        
        # Get bookmarks count
        bookmarks_result = self.db.execute(
            select(func.count(BookmarkInteraction.id))
            .where(
                and_(
                    BookmarkInteraction.user_id == user_id,
                    BookmarkInteraction.created_at >= since_date
                )
            )
        )
        bookmarks_count = bookmarks_result.scalar() or 0
        
        # TODO: Implement category analysis once we have better categorization
        most_viewed_categories = []
        most_bookmarked_categories = []
        
        return ActivitySummary(
            total_interactions=total_interactions,
            recent_views=recent_views,
            bookmarks_count=bookmarks_count,
            searches_count=searches_count,
            validations_count=validations_count,
            average_engagement_score=avg_engagement,
            most_viewed_categories=most_viewed_categories,
            most_bookmarked_categories=most_bookmarked_categories
        )
    
    def update_user_preferences(
        self, 
        user_id: str, 
        preferences_update: UserPreferenceUpdate
    ) -> UserPreference:
        """Update user preferences."""
        try:
            result = self.db.execute(
                select(UserPreference).where(UserPreference.user_id == user_id)
            )
            preferences = result.scalar_one_or_none()
            
            if not preferences:
                preferences = UserPreference(user_id=user_id)
                self.db.add(preferences)
            
            # Update fields
            update_data = preferences_update.dict(exclude_unset=True)
            
            # Handle JSON fields
            if "preferred_ai_types" in update_data:
                preferences.preferred_ai_types = json.dumps(update_data["preferred_ai_types"]) if update_data["preferred_ai_types"] else None
            if "preferred_industries" in update_data:
                preferences.preferred_industries = json.dumps(update_data["preferred_industries"]) if update_data["preferred_industries"] else None
            
            # Update other fields
            for field, value in update_data.items():
                if field not in ["preferred_ai_types", "preferred_industries"] and hasattr(preferences, field):
                    setattr(preferences, field, value)
            
            preferences.last_updated = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(preferences)
            
            logger.info(f"Updated preferences for user {user_id}")
            return preferences
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating user preferences: {e}")
            raise
    
    def create_recommendation_feedback(
        self, 
        user_id: str, 
        feedback_data: RecommendationFeedbackRequest
    ) -> RecommendationFeedback:
        """Create recommendation feedback."""
        try:
            feedback = RecommendationFeedback(
                user_id=user_id,
                opportunity_id=feedback_data.opportunity_id,
                is_relevant=feedback_data.is_relevant,
                feedback_score=feedback_data.feedback_score,
                feedback_text=feedback_data.feedback_text,
                recommendation_algorithm=feedback_data.recommendation_algorithm,
                recommendation_score=feedback_data.recommendation_score,
                recommendation_rank=feedback_data.recommendation_rank
            )
            
            self.db.add(feedback)
            self.db.commit()
            self.db.refresh(feedback)
            
            logger.info(f"Created recommendation feedback for user {user_id}")
            return feedback
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating recommendation feedback: {e}")
            raise


class BookmarkService:
    """Service for managing user bookmarks."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_bookmark(self, user_id: str, opportunity_id: str, note: Optional[str] = None) -> BookmarkInteraction:
        """Create a new bookmark."""
        try:
            # Check if bookmark already exists
            existing = self.db.execute(
                select(BookmarkInteraction)
                .where(
                    and_(
                        BookmarkInteraction.user_id == user_id,
                        BookmarkInteraction.opportunity_id == opportunity_id
                    )
                )
            ).scalar_one_or_none()
            
            if existing:
                raise ValueError("Opportunity already bookmarked")
            
            bookmark = BookmarkInteraction(
                user_id=user_id,
                opportunity_id=opportunity_id,
                note=note
            )
            
            self.db.add(bookmark)
            self.db.commit()
            self.db.refresh(bookmark)
            
            logger.info(f"Created bookmark for user {user_id}, opportunity {opportunity_id}")
            return bookmark
            
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Opportunity already bookmarked")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating bookmark: {e}")
            raise
    
    def remove_bookmark(self, user_id: str, opportunity_id: str) -> bool:
        """Remove a bookmark."""
        try:
            result = self.db.execute(
                select(BookmarkInteraction)
                .where(
                    and_(
                        BookmarkInteraction.user_id == user_id,
                        BookmarkInteraction.opportunity_id == opportunity_id
                    )
                )
            )
            bookmark = result.scalar_one_or_none()
            
            if not bookmark:
                return False
            
            self.db.delete(bookmark)
            self.db.commit()
            
            logger.info(f"Removed bookmark for user {user_id}, opportunity {opportunity_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing bookmark: {e}")
            raise
    
    def get_user_bookmarks(
        self, 
        user_id: str, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[BookmarkInteraction]:
        """Get user bookmarks with opportunity details."""
        query = (
            select(BookmarkInteraction)
            .options(selectinload(BookmarkInteraction.opportunity))
            .where(BookmarkInteraction.user_id == user_id)
            .order_by(desc(BookmarkInteraction.created_at))
            .offset(offset)
            .limit(limit)
        )
        
        result = self.db.execute(query)
        return result.scalars().all()
    
    def is_bookmarked(self, user_id: str, opportunity_id: str) -> bool:
        """Check if an opportunity is bookmarked by the user."""
        result = self.db.execute(
            select(BookmarkInteraction.id)
            .where(
                and_(
                    BookmarkInteraction.user_id == user_id,
                    BookmarkInteraction.opportunity_id == opportunity_id
                )
            )
        )
        return result.scalar_one_or_none() is not None


class CollectionService:
    """Service for managing user collections."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_collection(
        self, 
        user_id: str, 
        collection_data: UserCollectionCreate
    ) -> UserCollection:
        """Create a new user collection."""
        try:
            tags_json = json.dumps(collection_data.tags) if collection_data.tags else None
            
            collection = UserCollection(
                user_id=user_id,
                name=collection_data.name,
                description=collection_data.description,
                is_public=collection_data.is_public,
                tags=tags_json
            )
            
            self.db.add(collection)
            self.db.commit()
            self.db.refresh(collection)
            
            logger.info(f"Created collection '{collection_data.name}' for user {user_id}")
            return collection
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating collection: {e}")
            raise
    
    def update_collection(
        self, 
        collection_id: str, 
        user_id: str, 
        update_data: UserCollectionUpdate
    ) -> Optional[UserCollection]:
        """Update a user collection."""
        try:
            result = self.db.execute(
                select(UserCollection)
                .where(
                    and_(
                        UserCollection.id == collection_id,
                        UserCollection.user_id == user_id
                    )
                )
            )
            collection = result.scalar_one_or_none()
            
            if not collection:
                return None
            
            # Update fields
            update_dict = update_data.dict(exclude_unset=True)
            
            if "tags" in update_dict:
                collection.tags = json.dumps(update_dict["tags"]) if update_dict["tags"] else None
                del update_dict["tags"]
            
            for field, value in update_dict.items():
                if hasattr(collection, field):
                    setattr(collection, field, value)
            
            self.db.commit()
            self.db.refresh(collection)
            
            logger.info(f"Updated collection {collection_id}")
            return collection
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating collection: {e}")
            raise
    
    def delete_collection(self, collection_id: str, user_id: str) -> bool:
        """Delete a user collection."""
        try:
            result = self.db.execute(
                select(UserCollection)
                .where(
                    and_(
                        UserCollection.id == collection_id,
                        UserCollection.user_id == user_id
                    )
                )
            )
            collection = result.scalar_one_or_none()
            
            if not collection:
                return False
            
            self.db.delete(collection)
            self.db.commit()
            
            logger.info(f"Deleted collection {collection_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting collection: {e}")
            raise
    
    def get_user_collections(self, user_id: str) -> List[UserCollection]:
        """Get all collections for a user."""
        query = (
            select(UserCollection)
            .where(UserCollection.user_id == user_id)
            .order_by(desc(UserCollection.created_at))
        )
        
        result = self.db.execute(query)
        return result.scalars().all()
    
    def add_opportunity_to_collection(
        self, 
        collection_id: str, 
        user_id: str, 
        opportunity_data: CollectionOpportunityAdd
    ) -> bool:
        """Add an opportunity to a collection."""
        try:
            # Verify collection ownership
            collection = self.db.execute(
                select(UserCollection)
                .where(
                    and_(
                        UserCollection.id == collection_id,
                        UserCollection.user_id == user_id
                    )
                )
            ).scalar_one_or_none()
            
            if not collection:
                raise ValueError("Collection not found")
            
            # Check if opportunity exists
            opportunity = self.db.execute(
                select(Opportunity).where(Opportunity.id == opportunity_data.opportunity_id)
            ).scalar_one_or_none()
            
            if not opportunity:
                raise ValueError("Opportunity not found")
            
            # Add to collection (SQLAlchemy will handle the association table)
            collection.opportunities.append(opportunity)
            self.db.commit()
            
            logger.info(f"Added opportunity {opportunity_data.opportunity_id} to collection {collection_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding opportunity to collection: {e}")
            raise
    
    def remove_opportunity_from_collection(
        self, 
        collection_id: str, 
        user_id: str, 
        opportunity_id: str
    ) -> bool:
        """Remove an opportunity from a collection."""
        try:
            # Verify collection ownership and get with opportunities
            collection = self.db.execute(
                select(UserCollection)
                .options(selectinload(UserCollection.opportunities))
                .where(
                    and_(
                        UserCollection.id == collection_id,
                        UserCollection.user_id == user_id
                    )
                )
            ).scalar_one_or_none()
            
            if not collection:
                return False
            
            # Find and remove the opportunity
            opportunity_to_remove = None
            for opportunity in collection.opportunities:
                if opportunity.id == opportunity_id:
                    opportunity_to_remove = opportunity
                    break
            
            if not opportunity_to_remove:
                return False
            
            collection.opportunities.remove(opportunity_to_remove)
            self.db.commit()
            
            logger.info(f"Removed opportunity {opportunity_id} from collection {collection_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing opportunity from collection: {e}")
            raise


# Service instances
def get_interaction_service(db: Session) -> UserInteractionService:
    """Get user interaction service instance."""
    return UserInteractionService(db)

def get_bookmark_service(db: Session) -> BookmarkService:
    """Get bookmark service instance."""
    return BookmarkService(db)

def get_collection_service(db: Session) -> CollectionService:
    """Get collection service instance."""
    return CollectionService(db)