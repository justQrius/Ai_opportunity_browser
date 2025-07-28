"""User service for managing user operations and community features.

Supports Requirements 4.1-4.4 (Community Engagement Platform).
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.orm import selectinload

from shared.models.user import User, UserRole
from shared.models.validation import ValidationResult
from shared.schemas.user import UserCreate, UserUpdate, UserResponse
from shared.auth_utils import (
    hash_password, 
    verify_password, 
    create_access_token,
    calculate_reputation_score,
    determine_user_influence_weight,
    should_notify_expert
)
from shared.cache import cache_manager, CacheKeys
import structlog

logger = structlog.get_logger(__name__)


class UserService:
    """Service for user management and community features."""
    
    async def create_user(self, db: AsyncSession, user_data: UserCreate) -> User:
        """Create a new user.
        
        Supports Requirement 4.1 (Expert profiles showcasing expertise).
        
        Args:
            db: Database session
            user_data: User creation data
            
        Returns:
            Created user instance
            
        Raises:
            ValueError: If user already exists
        """
        # Check if user already exists
        existing_user = await self.get_user_by_email(db, user_data.email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        existing_username = await self.get_user_by_username(db, user_data.username)
        if existing_username:
            raise ValueError("Username already taken")
        
        # Hash password
        hashed_password = hash_password(user_data.password)
        
        # Prepare expertise domains
        expertise_domains_json = None
        if user_data.expertise_domains:
            expertise_domains_json = json.dumps(user_data.expertise_domains)
        
        # Create user
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            bio=user_data.bio,
            avatar_url=user_data.avatar_url,
            expertise_domains=expertise_domains_json,
            linkedin_url=user_data.linkedin_url,
            github_url=user_data.github_url,
            role=UserRole.EXPERT if user_data.expertise_domains else UserRole.USER
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info("User created", user_id=user.id, username=user.username, role=user.role)
        
        # Publish user registered event
        try:
            from shared.event_config import publish_user_registered
            await publish_user_registered(
                user_id=user.id,
                email=user.email,
                username=user.username,
                role=user.role.value,
                expertise_domains=user_data.expertise_domains
            )
        except Exception as e:
            logger.warning("Failed to publish user registered event", error=str(e))
        
        # Clear cache
        await self._clear_user_cache(user.id, user.email, user.username)
        
        return user
    
    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password.
        
        Args:
            db: Database session
            email: User email
            password: Plain text password
            
        Returns:
            User instance if authentication successful, None otherwise
        """
        user = await self.get_user_by_email(db, email)
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        logger.info("User authenticated", user_id=user.id, username=user.username)
        return user
    
    async def get_user_by_id(self, db: AsyncSession, user_id: str) -> Optional[User]:
        """Get user by ID with caching.
        
        Args:
            db: Database session
            user_id: User identifier
            
        Returns:
            User instance or None
        """
        # Try cache first
        cache_key = CacheKeys.format_key(CacheKeys.USER_BY_ID, user_id=user_id)
        cached_user = await cache_manager.get(cache_key)
        if cached_user:
            return User(**cached_user) if isinstance(cached_user, dict) else None
        
        # Query database
        result = await db.execute(
            select(User)
            .options(selectinload(User.validations))
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        # Cache result
        if user:
            user_dict = {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role.value,
                "reputation_score": user.reputation_score,
                "is_active": user.is_active
            }
            await cache_manager.set(cache_key, user_dict, expire=3600)  # 1 hour
        
        return user
    
    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email with caching.
        
        Args:
            db: Database session
            email: User email
            
        Returns:
            User instance or None
        """
        # Try cache first
        cache_key = CacheKeys.format_key(CacheKeys.USER_BY_EMAIL, email=email)
        cached_user = await cache_manager.get(cache_key)
        if cached_user:
            return User(**cached_user) if isinstance(cached_user, dict) else None
        
        # Query database
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        # Cache result
        if user:
            user_dict = {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "hashed_password": user.hashed_password,
                "is_active": user.is_active,
                "role": user.role.value
            }
            await cache_manager.set(cache_key, user_dict, expire=3600)
        
        return user
    
    async def get_user_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """Get user by username.
        
        Args:
            db: Database session
            username: Username
            
        Returns:
            User instance or None
        """
        result = await db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def update_user(self, db: AsyncSession, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """Update user information.
        
        Args:
            db: Database session
            user_id: User identifier
            user_data: Update data
            
        Returns:
            Updated user instance or None
        """
        user = await self.get_user_by_id(db, user_id)
        if not user:
            return None
        
        # Update fields
        update_data = user_data.dict(exclude_unset=True)
        
        # Handle expertise domains
        if "expertise_domains" in update_data:
            if update_data["expertise_domains"]:
                update_data["expertise_domains"] = json.dumps(update_data["expertise_domains"])
            else:
                update_data["expertise_domains"] = None
        
        # Apply updates
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await db.commit()
        await db.refresh(user)
        
        logger.info("User updated", user_id=user.id, updated_fields=list(update_data.keys()))
        
        # Clear cache
        await self._clear_user_cache(user.id, user.email, user.username)
        
        return user
    
    async def update_user_reputation(
        self, 
        db: AsyncSession, 
        user_id: str,
        recalculate: bool = True
    ) -> Optional[User]:
        """Update user reputation score.
        
        Supports Requirement 4.4 (Reputation points and badges for contributions).
        
        Args:
            db: Database session
            user_id: User identifier
            recalculate: Whether to recalculate from validation data
            
        Returns:
            Updated user instance or None
        """
        user = await self.get_user_by_id(db, user_id)
        if not user:
            return None
        
        if recalculate:
            # Get validation statistics
            validation_stats = await db.execute(
                select(
                    func.count(ValidationResult.id).label("validation_count"),
                    func.avg(ValidationResult.score).label("avg_score"),
                    func.sum(ValidationResult.helpful_votes).label("helpful_votes"),
                    func.sum(ValidationResult.unhelpful_votes).label("unhelpful_votes")
                ).where(ValidationResult.validator_id == user_id)
            )
            stats = validation_stats.first()
            
            if stats and stats.validation_count > 0:
                # Calculate days active
                days_active = max(1, (datetime.utcnow() - user.created_at).days)
                
                # Calculate new reputation
                new_reputation = calculate_reputation_score(
                    validation_count=stats.validation_count or 0,
                    validation_accuracy=min(1.0, (stats.avg_score or 0) / 10.0),
                    helpful_votes=stats.helpful_votes or 0,
                    unhelpful_votes=stats.unhelpful_votes or 0,
                    days_active=days_active
                )
                
                # Update user
                user.reputation_score = new_reputation
                user.validation_count = stats.validation_count or 0
                user.validation_accuracy = min(1.0, (stats.avg_score or 0) / 10.0)
                
                await db.commit()
                await db.refresh(user)
                
                logger.info(
                    "User reputation updated",
                    user_id=user.id,
                    new_reputation=new_reputation,
                    validation_count=user.validation_count
                )
        
        # Clear cache
        await self._clear_user_cache(user.id, user.email, user.username)
        
        return user
    
    async def get_experts_for_opportunity(
        self, 
        db: AsyncSession,
        ai_solution_types: List[str],
        target_industries: List[str],
        min_reputation: float = 3.0
    ) -> List[User]:
        """Get experts who should be notified about an opportunity.
        
        Supports Requirement 4.2 (Notify relevant experts for validation).
        
        Args:
            db: Database session
            ai_solution_types: Opportunity's AI solution types
            target_industries: Opportunity's target industries
            min_reputation: Minimum reputation score for experts
            
        Returns:
            List of expert users
        """
        # Get all experts with sufficient reputation
        result = await db.execute(
            select(User)
            .where(
                and_(
                    User.role == UserRole.EXPERT,
                    User.is_active == True,
                    User.reputation_score >= min_reputation,
                    User.expertise_domains.isnot(None)
                )
            )
        )
        experts = result.scalars().all()
        
        # Filter experts based on domain matching
        relevant_experts = []
        for expert in experts:
            if expert.expertise_domains:
                try:
                    domains = json.loads(expert.expertise_domains)
                    if should_notify_expert(domains, ai_solution_types, target_industries):
                        relevant_experts.append(expert)
                except json.JSONDecodeError:
                    continue
        
        logger.info(
            "Found relevant experts",
            total_experts=len(experts),
            relevant_experts=len(relevant_experts),
            ai_types=ai_solution_types,
            industries=target_industries
        )
        
        return relevant_experts
    
    async def get_user_influence_weight(self, db: AsyncSession, user_id: str) -> float:
        """Get user's influence weight for validation scoring.
        
        Supports Requirement 4.4 (Increase influence weight for quality validation).
        
        Args:
            db: Database session
            user_id: User identifier
            
        Returns:
            Influence weight (0.1-2.0 scale)
        """
        user = await self.get_user_by_id(db, user_id)
        if not user:
            return 0.1
        
        return determine_user_influence_weight(user.reputation_score, user.role.value)
    
    async def get_top_contributors(
        self, 
        db: AsyncSession, 
        limit: int = 10,
        timeframe_days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get top contributors by reputation and activity.
        
        Args:
            db: Database session
            limit: Number of contributors to return
            timeframe_days: Timeframe for activity calculation
            
        Returns:
            List of top contributor data
        """
        cutoff_date = datetime.utcnow() - timedelta(days=timeframe_days)
        
        result = await db.execute(
            select(
                User.id,
                User.username,
                User.full_name,
                User.reputation_score,
                User.validation_count,
                func.count(ValidationResult.id).label("recent_validations")
            )
            .outerjoin(
                ValidationResult,
                and_(
                    ValidationResult.validator_id == User.id,
                    ValidationResult.created_at >= cutoff_date
                )
            )
            .where(User.is_active == True)
            .group_by(User.id)
            .order_by(User.reputation_score.desc(), func.count(ValidationResult.id).desc())
            .limit(limit)
        )
        
        contributors = []
        for row in result:
            contributors.append({
                "user_id": row.id,
                "username": row.username,
                "full_name": row.full_name,
                "reputation_score": row.reputation_score,
                "total_validations": row.validation_count,
                "recent_validations": row.recent_validations
            })
        
        return contributors
    
    async def _clear_user_cache(self, user_id: str, email: str, username: str):
        """Clear user-related cache entries.
        
        Args:
            user_id: User identifier
            email: User email
            username: Username
        """
        cache_keys = [
            CacheKeys.format_key(CacheKeys.USER_BY_ID, user_id=user_id),
            CacheKeys.format_key(CacheKeys.USER_BY_EMAIL, email=email),
            CacheKeys.format_key(CacheKeys.USER_PREFERENCES, user_id=user_id),
            CacheKeys.format_key(CacheKeys.USER_REPUTATION, user_id=user_id)
        ]
        
        for key in cache_keys:
            await cache_manager.delete(key)


# Global user service instance
user_service = UserService()