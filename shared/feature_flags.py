"""
Feature Flag Management System for AI Opportunity Browser

This module provides a comprehensive feature flag system with support for:
- Feature toggle management with gradual rollout capabilities
- User segmentation and targeting
- A/B testing support
- Real-time flag updates without deployments
- Analytics and usage tracking
- Integration with configuration service
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import asynccontextmanager

import redis.asyncio as redis
from pydantic import BaseModel, Field, validator

from .config_service import ConfigurationService, ConfigScope, ConfigMetadata, ConfigType
from .event_bus import publish_event
from .database import get_redis_client

logger = logging.getLogger(__name__)


class FeatureFlagStatus(str, Enum):
    """Feature flag status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class RolloutStrategy(str, Enum):
    """Rollout strategy types."""
    PERCENTAGE = "percentage"
    USER_LIST = "user_list"
    USER_ATTRIBUTE = "user_attribute"
    GRADUAL = "gradual"
    CANARY = "canary"


class TargetingRule(BaseModel):
    """Targeting rule for feature flags."""
    attribute: str
    operator: str  # equals, not_equals, in, not_in, greater_than, less_than, contains
    values: List[Any]
    description: Optional[str] = None


class RolloutConfig(BaseModel):
    """Rollout configuration for feature flags."""
    strategy: RolloutStrategy
    percentage: Optional[float] = None  # 0-100
    user_ids: Optional[List[str]] = None
    targeting_rules: Optional[List[TargetingRule]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    gradual_increment: Optional[float] = None  # Daily increment for gradual rollout
    
    @validator('percentage')
    def validate_percentage(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Percentage must be between 0 and 100")
        return v


class FeatureVariant(BaseModel):
    """Feature flag variant for A/B testing."""
    name: str
    value: Any
    weight: float = 0.0  # 0-100
    description: Optional[str] = None
    
    @validator('weight')
    def validate_weight(cls, v):
        if v < 0 or v > 100:
            raise ValueError("Weight must be between 0 and 100")
        return v


@dataclass
class UserContext:
    """User context for feature flag evaluation."""
    user_id: str
    email: Optional[str] = None
    role: Optional[str] = None
    plan: Optional[str] = None
    country: Optional[str] = None
    created_at: Optional[datetime] = None
    attributes: Optional[Dict[str, Any]] = None


@dataclass
class FeatureFlagEvaluation:
    """Result of feature flag evaluation."""
    flag_name: str
    enabled: bool
    variant: Optional[str] = None
    value: Any = None
    reason: str = "default"
    user_context: Optional[UserContext] = None
    evaluated_at: datetime = None
    
    def __post_init__(self):
        if self.evaluated_at is None:
            self.evaluated_at = datetime.now(timezone.utc)


class FeatureFlag(BaseModel):
    """Feature flag definition."""
    name: str
    description: str
    status: FeatureFlagStatus = FeatureFlagStatus.ACTIVE
    default_value: Any = False
    rollout_config: RolloutConfig
    variants: Optional[List[FeatureVariant]] = None
    environments: List[str] = Field(default_factory=lambda: ["development", "staging", "production"])
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    updated_by: str = "system"
    
    @validator('variants')
    def validate_variants(cls, v):
        if v:
            total_weight = sum(variant.weight for variant in v)
            if abs(total_weight - 100.0) > 0.01:  # Allow small floating point errors
                raise ValueError("Variant weights must sum to 100")
        return v


class FeatureFlagUsage(BaseModel):
    """Feature flag usage analytics."""
    flag_name: str
    user_id: str
    enabled: bool
    variant: Optional[str] = None
    environment: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class FeatureFlagService:
    """
    Feature flag management service with gradual rollout capabilities.
    
    Features:
    - Feature toggle management with real-time updates
    - Gradual rollout with percentage-based and user-based targeting
    - A/B testing with weighted variants
    - User segmentation and targeting rules
    - Analytics and usage tracking
    - Integration with configuration service
    """
    
    def __init__(
        self,
        config_service: Optional[ConfigurationService] = None,
        redis_client: Optional[redis.Redis] = None,
        default_environment: str = "development",
        enable_analytics: bool = True
    ):
        self.config_service = config_service
        self.redis_client = redis_client
        self.default_environment = default_environment
        self.enable_analytics = enable_analytics
        
        # Feature flag cache
        self._flag_cache: Dict[str, FeatureFlag] = {}
        self._evaluation_cache: Dict[str, FeatureFlagEvaluation] = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Event handlers
        self._flag_change_handlers: List[Callable] = []
        
        self._initialized = False
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> None:
        """Initialize the feature flag service."""
        if self._initialized:
            return
        
        try:
            # Initialize Redis client if not provided
            if self.redis_client is None:
                self.redis_client = await get_redis_client()
            
            # Initialize configuration service if not provided
            if self.config_service is None:
                self.config_service = ConfigurationService(
                    redis_client=self.redis_client,
                    default_environment=self.default_environment
                )
                await self.config_service.initialize()
            
            # Register feature flag configuration schemas
            await self._register_config_schemas()
            
            # Load existing feature flags
            await self._load_feature_flags()
            
            # Start gradual rollout scheduler
            asyncio.create_task(self._gradual_rollout_scheduler())
            
            self._initialized = True
            self.logger.info("Feature flag service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize feature flag service: {e}")
            raise
    
    async def create_feature_flag(
        self,
        name: str,
        description: str,
        default_value: Any = False,
        rollout_config: Optional[RolloutConfig] = None,
        variants: Optional[List[FeatureVariant]] = None,
        environments: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        created_by: str = "system"
    ) -> FeatureFlag:
        """
        Create a new feature flag.
        
        Args:
            name: Feature flag name (unique identifier)
            description: Human-readable description
            default_value: Default value when flag is disabled
            rollout_config: Rollout configuration
            variants: A/B testing variants
            environments: Target environments
            tags: Organizational tags
            created_by: User creating the flag
            
        Returns:
            Created feature flag
        """
        if not self._initialized:
            await self.initialize()
        
        # Check if flag already exists
        existing_flag = await self.get_feature_flag(name)
        if existing_flag:
            raise ValueError(f"Feature flag '{name}' already exists")
        
        # Set default rollout config
        if rollout_config is None:
            rollout_config = RolloutConfig(
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=0.0
            )
        
        # Create feature flag
        flag = FeatureFlag(
            name=name,
            description=description,
            default_value=default_value,
            rollout_config=rollout_config,
            variants=variants or [],
            environments=environments or ["development", "staging", "production"],
            tags=tags or [],
            created_by=created_by,
            updated_by=created_by
        )
        
        # Store flag
        await self._store_feature_flag(flag)
        
        # Update cache
        self._flag_cache[name] = flag
        
        # Publish event
        await publish_event("feature_flag.created", {
            "flag_name": name,
            "created_by": created_by,
            "environments": flag.environments
        }, source="feature_flag_service")
        
        self.logger.info(f"Created feature flag: {name}")
        return flag
    
    async def update_feature_flag(
        self,
        name: str,
        description: Optional[str] = None,
        status: Optional[FeatureFlagStatus] = None,
        default_value: Optional[Any] = None,
        rollout_config: Optional[RolloutConfig] = None,
        variants: Optional[List[FeatureVariant]] = None,
        environments: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        updated_by: str = "system"
    ) -> FeatureFlag:
        """Update an existing feature flag."""
        if not self._initialized:
            await self.initialize()
        
        # Get existing flag
        flag = await self.get_feature_flag(name)
        if not flag:
            raise ValueError(f"Feature flag '{name}' not found")
        
        # Update fields
        if description is not None:
            flag.description = description
        if status is not None:
            flag.status = status
        if default_value is not None:
            flag.default_value = default_value
        if rollout_config is not None:
            flag.rollout_config = rollout_config
        if variants is not None:
            flag.variants = variants
        if environments is not None:
            flag.environments = environments
        if tags is not None:
            flag.tags = tags
        
        flag.updated_at = datetime.now(timezone.utc)
        flag.updated_by = updated_by
        
        # Validate updated flag
        flag = FeatureFlag(**flag.dict())
        
        # Store updated flag
        await self._store_feature_flag(flag)
        
        # Update cache
        self._flag_cache[name] = flag
        
        # Clear evaluation cache for this flag
        self._clear_evaluation_cache(name)
        
        # Notify handlers
        await self._notify_flag_change_handlers(name, flag)
        
        # Publish event
        await publish_event("feature_flag.updated", {
            "flag_name": name,
            "updated_by": updated_by,
            "status": status.value if status else flag.status.value
        }, source="feature_flag_service")
        
        self.logger.info(f"Updated feature flag: {name}")
        return flag
    
    async def delete_feature_flag(
        self,
        name: str,
        deleted_by: str = "system"
    ) -> bool:
        """Delete a feature flag."""
        if not self._initialized:
            await self.initialize()
        
        # Check if flag exists
        flag = await self.get_feature_flag(name)
        if not flag:
            return False
        
        # Delete from Redis
        flag_key = f"feature_flag:{name}"
        deleted = await self.redis_client.delete(flag_key) > 0
        
        if deleted:
            # Remove from cache
            self._flag_cache.pop(name, None)
            
            # Clear evaluation cache
            self._clear_evaluation_cache(name)
            
            # Publish event
            await publish_event("feature_flag.deleted", {
                "flag_name": name,
                "deleted_by": deleted_by
            }, source="feature_flag_service")
            
            self.logger.info(f"Deleted feature flag: {name}")
        
        return deleted
    
    async def get_feature_flag(self, name: str) -> Optional[FeatureFlag]:
        """Get a feature flag by name."""
        if not self._initialized:
            await self.initialize()
        
        # Try cache first
        flag = self._flag_cache.get(name)
        if flag:
            return flag
        
        # Load from Redis
        flag_key = f"feature_flag:{name}"
        data = await self.redis_client.get(flag_key)
        
        if data:
            try:
                flag_data = json.loads(data)
                flag = FeatureFlag(**flag_data)
                self._flag_cache[name] = flag
                return flag
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.error(f"Error loading feature flag {name}: {e}")
        
        return None
    
    async def list_feature_flags(
        self,
        environment: Optional[str] = None,
        status: Optional[FeatureFlagStatus] = None,
        tags: Optional[List[str]] = None
    ) -> List[FeatureFlag]:
        """List feature flags with optional filtering."""
        if not self._initialized:
            await self.initialize()
        
        # Get all flag keys
        flag_keys = await self.redis_client.keys("feature_flag:*")
        
        flags = []
        for flag_key in flag_keys:
            flag_name = flag_key.replace("feature_flag:", "")
            flag = await self.get_feature_flag(flag_name)
            
            if flag:
                # Apply filters
                if environment and environment not in flag.environments:
                    continue
                if status and flag.status != status:
                    continue
                if tags and not any(tag in flag.tags for tag in tags):
                    continue
                
                flags.append(flag)
        
        return sorted(flags, key=lambda x: x.name)
    
    async def is_feature_enabled(
        self,
        flag_name: str,
        user_context: Optional[UserContext] = None,
        environment: Optional[str] = None
    ) -> bool:
        """
        Check if a feature flag is enabled for a user.
        
        Args:
            flag_name: Feature flag name
            user_context: User context for evaluation
            environment: Target environment
            
        Returns:
            True if feature is enabled, False otherwise
        """
        evaluation = await self.evaluate_feature_flag(flag_name, user_context, environment)
        return evaluation.enabled
    
    async def get_feature_variant(
        self,
        flag_name: str,
        user_context: Optional[UserContext] = None,
        environment: Optional[str] = None
    ) -> Any:
        """
        Get the feature flag variant value for a user.
        
        Args:
            flag_name: Feature flag name
            user_context: User context for evaluation
            environment: Target environment
            
        Returns:
            Feature variant value
        """
        evaluation = await self.evaluate_feature_flag(flag_name, user_context, environment)
        return evaluation.value
    
    async def evaluate_feature_flag(
        self,
        flag_name: str,
        user_context: Optional[UserContext] = None,
        environment: Optional[str] = None
    ) -> FeatureFlagEvaluation:
        """
        Evaluate a feature flag for a user context.
        
        Args:
            flag_name: Feature flag name
            user_context: User context for evaluation
            environment: Target environment
            
        Returns:
            Feature flag evaluation result
        """
        if not self._initialized:
            await self.initialize()
        
        environment = environment or self.default_environment
        
        # Check evaluation cache
        cache_key = self._build_evaluation_cache_key(flag_name, user_context, environment)
        cached_evaluation = self._evaluation_cache.get(cache_key)
        if cached_evaluation and self._is_cache_valid(cached_evaluation.evaluated_at):
            return cached_evaluation
        
        # Get feature flag
        flag = await self.get_feature_flag(flag_name)
        if not flag:
            evaluation = FeatureFlagEvaluation(
                flag_name=flag_name,
                enabled=False,
                value=False,
                reason="flag_not_found"
            )
            return evaluation
        
        # Check if flag is active
        if flag.status != FeatureFlagStatus.ACTIVE:
            evaluation = FeatureFlagEvaluation(
                flag_name=flag_name,
                enabled=False,
                value=flag.default_value,
                reason="flag_inactive",
                user_context=user_context
            )
            return evaluation
        
        # Check environment
        if environment not in flag.environments:
            evaluation = FeatureFlagEvaluation(
                flag_name=flag_name,
                enabled=False,
                value=flag.default_value,
                reason="environment_not_targeted",
                user_context=user_context
            )
            return evaluation
        
        # Evaluate rollout configuration
        enabled, reason = await self._evaluate_rollout(flag, user_context, environment)
        
        # Determine variant if enabled
        variant_name = None
        variant_value = flag.default_value
        
        if enabled and flag.variants:
            variant = self._select_variant(flag.variants, user_context)
            if variant:
                variant_name = variant.name
                variant_value = variant.value
        elif enabled:
            variant_value = True  # Default enabled value
        
        evaluation = FeatureFlagEvaluation(
            flag_name=flag_name,
            enabled=enabled,
            variant=variant_name,
            value=variant_value,
            reason=reason,
            user_context=user_context
        )
        
        # Cache evaluation
        self._evaluation_cache[cache_key] = evaluation
        
        # Track usage if analytics enabled
        if self.enable_analytics and user_context:
            await self._track_flag_usage(flag_name, user_context, evaluation, environment)
        
        return evaluation
    
    async def track_feature_usage(
        self,
        flag_name: str,
        user_id: str,
        outcome: str,
        environment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track feature flag usage outcome."""
        if not self.enable_analytics:
            return
        
        environment = environment or self.default_environment
        
        usage_data = {
            "flag_name": flag_name,
            "user_id": user_id,
            "outcome": outcome,
            "environment": environment,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Store in Redis for analytics
        usage_key = f"feature_usage:{flag_name}:{datetime.now().strftime('%Y-%m-%d')}"
        await self.redis_client.lpush(usage_key, json.dumps(usage_data))
        await self.redis_client.expire(usage_key, 86400 * 30)  # 30 days
        
        # Publish event
        await publish_event("feature_flag.usage_tracked", usage_data, source="feature_flag_service")
    
    async def get_feature_analytics(
        self,
        flag_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        environment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get feature flag usage analytics."""
        if not self.enable_analytics:
            return {}
        
        start_date = start_date or (datetime.now() - timedelta(days=7))
        end_date = end_date or datetime.now()
        environment = environment or self.default_environment
        
        analytics = {
            "flag_name": flag_name,
            "environment": environment,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_evaluations": 0,
            "enabled_count": 0,
            "disabled_count": 0,
            "unique_users": set(),
            "variants": {},
            "daily_stats": {}
        }
        
        # Collect usage data for date range
        current_date = start_date.date()
        while current_date <= end_date.date():
            usage_key = f"feature_usage:{flag_name}:{current_date.strftime('%Y-%m-%d')}"
            usage_data = await self.redis_client.lrange(usage_key, 0, -1)
            
            daily_enabled = 0
            daily_disabled = 0
            daily_users = set()
            
            for data in usage_data:
                try:
                    usage = json.loads(data)
                    if usage.get("environment") != environment:
                        continue
                    
                    analytics["total_evaluations"] += 1
                    daily_users.add(usage["user_id"])
                    analytics["unique_users"].add(usage["user_id"])
                    
                    if usage.get("enabled", False):
                        analytics["enabled_count"] += 1
                        daily_enabled += 1
                    else:
                        analytics["disabled_count"] += 1
                        daily_disabled += 1
                    
                    # Track variants
                    variant = usage.get("variant")
                    if variant:
                        if variant not in analytics["variants"]:
                            analytics["variants"][variant] = 0
                        analytics["variants"][variant] += 1
                
                except json.JSONDecodeError:
                    continue
            
            analytics["daily_stats"][current_date.isoformat()] = {
                "enabled": daily_enabled,
                "disabled": daily_disabled,
                "unique_users": len(daily_users)
            }
            
            current_date += timedelta(days=1)
        
        # Convert set to count
        analytics["unique_users"] = len(analytics["unique_users"])
        
        return analytics
    
    async def add_flag_change_handler(self, handler: Callable[[str, FeatureFlag], None]) -> None:
        """Add a handler for feature flag changes."""
        self._flag_change_handlers.append(handler)
    
    async def _evaluate_rollout(
        self,
        flag: FeatureFlag,
        user_context: Optional[UserContext],
        environment: str
    ) -> tuple[bool, str]:
        """Evaluate rollout configuration."""
        rollout = flag.rollout_config
        
        # Check date range
        now = datetime.now(timezone.utc)
        if rollout.start_date and now < rollout.start_date:
            return False, "before_start_date"
        if rollout.end_date and now > rollout.end_date:
            return False, "after_end_date"
        
        # Evaluate based on strategy
        if rollout.strategy == RolloutStrategy.PERCENTAGE:
            return self._evaluate_percentage_rollout(rollout, user_context)
        elif rollout.strategy == RolloutStrategy.USER_LIST:
            return self._evaluate_user_list_rollout(rollout, user_context)
        elif rollout.strategy == RolloutStrategy.USER_ATTRIBUTE:
            return self._evaluate_user_attribute_rollout(rollout, user_context)
        elif rollout.strategy == RolloutStrategy.GRADUAL:
            return await self._evaluate_gradual_rollout(flag, rollout, user_context)
        elif rollout.strategy == RolloutStrategy.CANARY:
            return self._evaluate_canary_rollout(rollout, user_context)
        
        return False, "unknown_strategy"
    
    def _evaluate_percentage_rollout(
        self,
        rollout: RolloutConfig,
        user_context: Optional[UserContext]
    ) -> tuple[bool, str]:
        """Evaluate percentage-based rollout."""
        if rollout.percentage is None:
            return False, "no_percentage_configured"
        
        if rollout.percentage >= 100:
            return True, "percentage_100"
        
        if rollout.percentage <= 0:
            return False, "percentage_0"
        
        # Use user ID for consistent hashing if available
        if user_context and user_context.user_id:
            hash_value = hash(user_context.user_id) % 100
        else:
            hash_value = random.randint(0, 99)
        
        enabled = hash_value < rollout.percentage
        return enabled, f"percentage_{rollout.percentage}"
    
    def _evaluate_user_list_rollout(
        self,
        rollout: RolloutConfig,
        user_context: Optional[UserContext]
    ) -> tuple[bool, str]:
        """Evaluate user list-based rollout."""
        if not rollout.user_ids or not user_context or not user_context.user_id:
            return False, "no_user_list_or_context"
        
        enabled = user_context.user_id in rollout.user_ids
        return enabled, "user_list_match" if enabled else "user_list_no_match"
    
    def _evaluate_user_attribute_rollout(
        self,
        rollout: RolloutConfig,
        user_context: Optional[UserContext]
    ) -> tuple[bool, str]:
        """Evaluate user attribute-based rollout."""
        if not rollout.targeting_rules or not user_context:
            return False, "no_targeting_rules_or_context"
        
        for rule in rollout.targeting_rules:
            if self._evaluate_targeting_rule(rule, user_context):
                return True, f"targeting_rule_match_{rule.attribute}"
        
        return False, "no_targeting_rule_match"
    
    async def _evaluate_gradual_rollout(
        self,
        flag: FeatureFlag,
        rollout: RolloutConfig,
        user_context: Optional[UserContext]
    ) -> tuple[bool, str]:
        """Evaluate gradual rollout."""
        if not rollout.start_date or not rollout.gradual_increment:
            return False, "gradual_rollout_not_configured"
        
        # Calculate current percentage based on time elapsed
        now = datetime.now(timezone.utc)
        days_elapsed = (now - rollout.start_date).days
        current_percentage = min(rollout.gradual_increment * days_elapsed, 100.0)
        
        # Update the rollout percentage
        rollout.percentage = current_percentage
        
        # Evaluate as percentage rollout
        return self._evaluate_percentage_rollout(rollout, user_context)
    
    def _evaluate_canary_rollout(
        self,
        rollout: RolloutConfig,
        user_context: Optional[UserContext]
    ) -> tuple[bool, str]:
        """Evaluate canary rollout (specific users + percentage)."""
        # First check user list
        if rollout.user_ids and user_context and user_context.user_id:
            if user_context.user_id in rollout.user_ids:
                return True, "canary_user_list"
        
        # Then check percentage
        if rollout.percentage:
            return self._evaluate_percentage_rollout(rollout, user_context)
        
        return False, "canary_no_match"
    
    def _evaluate_targeting_rule(
        self,
        rule: TargetingRule,
        user_context: UserContext
    ) -> bool:
        """Evaluate a single targeting rule."""
        # Get attribute value from user context
        attr_value = None
        if rule.attribute == "user_id":
            attr_value = user_context.user_id
        elif rule.attribute == "email":
            attr_value = user_context.email
        elif rule.attribute == "role":
            attr_value = user_context.role
        elif rule.attribute == "plan":
            attr_value = user_context.plan
        elif rule.attribute == "country":
            attr_value = user_context.country
        elif user_context.attributes and rule.attribute in user_context.attributes:
            attr_value = user_context.attributes[rule.attribute]
        
        if attr_value is None:
            return False
        
        # Evaluate operator
        if rule.operator == "equals":
            return attr_value in rule.values
        elif rule.operator == "not_equals":
            return attr_value not in rule.values
        elif rule.operator == "in":
            return attr_value in rule.values
        elif rule.operator == "not_in":
            return attr_value not in rule.values
        elif rule.operator == "contains":
            return any(str(val) in str(attr_value) for val in rule.values)
        elif rule.operator == "greater_than":
            try:
                return float(attr_value) > float(rule.values[0])
            except (ValueError, IndexError):
                return False
        elif rule.operator == "less_than":
            try:
                return float(attr_value) < float(rule.values[0])
            except (ValueError, IndexError):
                return False
        
        return False
    
    def _select_variant(
        self,
        variants: List[FeatureVariant],
        user_context: Optional[UserContext]
    ) -> Optional[FeatureVariant]:
        """Select a variant based on weights."""
        if not variants:
            return None
        
        # Use user ID for consistent variant selection
        if user_context and user_context.user_id:
            hash_value = hash(user_context.user_id) % 100
        else:
            hash_value = random.randint(0, 99)
        
        # Select variant based on cumulative weights
        cumulative_weight = 0
        for variant in variants:
            cumulative_weight += variant.weight
            if hash_value < cumulative_weight:
                return variant
        
        # Fallback to first variant
        return variants[0] if variants else None
    
    async def _store_feature_flag(self, flag: FeatureFlag) -> None:
        """Store feature flag in Redis."""
        flag_key = f"feature_flag:{flag.name}"
        flag_data = flag.dict()
        
        # Convert datetime objects to ISO strings
        flag_data['created_at'] = flag.created_at.isoformat()
        flag_data['updated_at'] = flag.updated_at.isoformat()
        
        # Handle rollout config dates
        if flag.rollout_config.start_date:
            flag_data['rollout_config']['start_date'] = flag.rollout_config.start_date.isoformat()
        if flag.rollout_config.end_date:
            flag_data['rollout_config']['end_date'] = flag.rollout_config.end_date.isoformat()
        
        await self.redis_client.set(
            flag_key,
            json.dumps(flag_data, default=str),
            ex=86400 * 365  # 1 year
        )
    
    async def _load_feature_flags(self) -> None:
        """Load all feature flags from Redis into cache."""
        try:
            flag_keys = await self.redis_client.keys("feature_flag:*")
            
            for flag_key in flag_keys:
                flag_name = flag_key.replace("feature_flag:", "")
                flag = await self.get_feature_flag(flag_name)
                if flag:
                    self._flag_cache[flag_name] = flag
            
            self.logger.info(f"Loaded {len(self._flag_cache)} feature flags")
            
        except Exception as e:
            self.logger.error(f"Error loading feature flags: {e}")
    
    async def _register_config_schemas(self) -> None:
        """Register configuration schemas for feature flags."""
        await self.config_service.register_config_schema(
            "feature_flags.default_environment",
            ConfigMetadata(
                description="Default environment for feature flag evaluation",
                config_type=ConfigType.STRING,
                default_value="development",
                allowed_values=["development", "staging", "production"]
            )
        )
        
        await self.config_service.register_config_schema(
            "feature_flags.enable_analytics",
            ConfigMetadata(
                description="Enable feature flag usage analytics",
                config_type=ConfigType.BOOLEAN,
                default_value=True
            )
        )
        
        await self.config_service.register_config_schema(
            "feature_flags.cache_ttl",
            ConfigMetadata(
                description="Feature flag evaluation cache TTL in seconds",
                config_type=ConfigType.INTEGER,
                default_value=300,
                min_value=60,
                max_value=3600
            )
        )
    
    def _build_evaluation_cache_key(
        self,
        flag_name: str,
        user_context: Optional[UserContext],
        environment: str
    ) -> str:
        """Build cache key for evaluation result."""
        user_id = user_context.user_id if user_context else "anonymous"
        return f"eval:{flag_name}:{user_id}:{environment}"
    
    def _is_cache_valid(self, evaluated_at: datetime) -> bool:
        """Check if cached evaluation is still valid."""
        return (datetime.now(timezone.utc) - evaluated_at).total_seconds() < self._cache_ttl
    
    def _clear_evaluation_cache(self, flag_name: str) -> None:
        """Clear evaluation cache for a specific flag."""
        keys_to_remove = [
            key for key in self._evaluation_cache.keys()
            if key.startswith(f"eval:{flag_name}:")
        ]
        for key in keys_to_remove:
            self._evaluation_cache.pop(key, None)
    
    async def _track_flag_usage(
        self,
        flag_name: str,
        user_context: UserContext,
        evaluation: FeatureFlagEvaluation,
        environment: str
    ) -> None:
        """Track feature flag usage for analytics."""
        usage = FeatureFlagUsage(
            flag_name=flag_name,
            user_id=user_context.user_id,
            enabled=evaluation.enabled,
            variant=evaluation.variant,
            environment=environment
        )
        
        # Store in Redis for analytics
        usage_key = f"feature_usage:{flag_name}:{datetime.now().strftime('%Y-%m-%d')}"
        usage_data = usage.dict()
        usage_data['timestamp'] = usage.timestamp.isoformat()
        
        await self.redis_client.lpush(usage_key, json.dumps(usage_data))
        await self.redis_client.expire(usage_key, 86400 * 30)  # 30 days
    
    async def _notify_flag_change_handlers(self, flag_name: str, flag: FeatureFlag) -> None:
        """Notify registered flag change handlers."""
        for handler in self._flag_change_handlers:
            try:
                await handler(flag_name, flag)
            except Exception as e:
                self.logger.error(f"Error in flag change handler: {e}")
    
    async def _gradual_rollout_scheduler(self) -> None:
        """Background task to update gradual rollouts."""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                # Get all active flags with gradual rollout
                flags = await self.list_feature_flags(status=FeatureFlagStatus.ACTIVE)
                
                for flag in flags:
                    if (flag.rollout_config.strategy == RolloutStrategy.GRADUAL and
                        flag.rollout_config.start_date and
                        flag.rollout_config.gradual_increment):
                        
                        # Calculate new percentage
                        now = datetime.now(timezone.utc)
                        days_elapsed = (now - flag.rollout_config.start_date).days
                        new_percentage = min(
                            flag.rollout_config.gradual_increment * days_elapsed,
                            100.0
                        )
                        
                        # Update if changed
                        if new_percentage != flag.rollout_config.percentage:
                            flag.rollout_config.percentage = new_percentage
                            await self._store_feature_flag(flag)
                            self._flag_cache[flag.name] = flag
                            
                            self.logger.info(
                                f"Updated gradual rollout for {flag.name}: {new_percentage}%"
                            )
            
            except Exception as e:
                self.logger.error(f"Error in gradual rollout scheduler: {e}")


# Global feature flag service instance
_feature_flag_service: Optional[FeatureFlagService] = None


async def get_feature_flag_service() -> FeatureFlagService:
    """Get the global feature flag service instance."""
    global _feature_flag_service
    
    if _feature_flag_service is None:
        _feature_flag_service = FeatureFlagService()
        await _feature_flag_service.initialize()
    
    return _feature_flag_service


async def is_feature_enabled(
    flag_name: str,
    user_context: Optional[UserContext] = None,
    environment: Optional[str] = None
) -> bool:
    """Convenience function to check if a feature is enabled."""
    service = await get_feature_flag_service()
    return await service.is_feature_enabled(flag_name, user_context, environment)


async def get_feature_variant(
    flag_name: str,
    user_context: Optional[UserContext] = None,
    environment: Optional[str] = None
) -> Any:
    """Convenience function to get a feature variant."""
    service = await get_feature_flag_service()
    return await service.get_feature_variant(flag_name, user_context, environment)