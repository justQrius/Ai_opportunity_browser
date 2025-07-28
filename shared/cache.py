"""Redis cache configuration and utilities."""

import json
import os
from typing import Any, Optional, Union, Dict, List
from datetime import timedelta
import redis.asyncio as redis
from redis.asyncio import Redis
import structlog

logger = structlog.get_logger(__name__)


class CacheKeys:
    """Cache key constants and utilities."""
    
    # User-related cache keys
    USER_PROFILE = "user:profile:{user_id}"
    USER_REPUTATION = "user:reputation:{user_id}"
    USER_VALIDATIONS = "user:validations:{user_id}:page:{page}"
    USER_MATCHES = "user:matches:{user_id}:{match_type}:{limit}"
    USER_PREFERENCES = "user:preferences:{user_id}"
    USER_BY_ID = "user:by_id:{user_id}"
    USER_BY_EMAIL = "user:by_email:{email}"
    
    # Opportunity-related cache keys
    OPPORTUNITY_DETAILS = "opportunity:details:{opportunity_id}"
    OPPORTUNITY_SEARCH = "opportunity:search:{query_hash}"
    OPPORTUNITY_RECOMMENDATIONS = "opportunity:recommendations:{user_id}"
    
    # Validation-related cache keys
    VALIDATION_RESULTS = "validation:results:{opportunity_id}"
    VALIDATION_SUMMARY = "validation:summary:{opportunity_id}"
    VALIDATION_BY_USER = "validation:by_user:{user_id}:page:{page}"
    
    # Market signal cache keys
    MARKET_SIGNALS = "market:signals:{opportunity_id}"
    SIGNAL_ANALYSIS = "market:analysis:{signal_id}"
    
    # Analytics cache keys
    ANALYTICS_DASHBOARD = "analytics:dashboard:{timeframe}"
    LEADERBOARD = "leaderboard:{timeframe}:{limit}"
    
    # Messaging cache keys
    USER_MESSAGES = "user:messages:{user_id}:page:{page}"
    USER_CONVERSATIONS = "user:conversations:{user_id}"
    MESSAGE_THREAD = "message:thread:{conversation_id}"
    COLLABORATION_DETAILS = "collaboration:details:{collaboration_id}"
    USER_COLLABORATIONS = "user:collaborations:{user_id}:{status}"
    
    # System cache keys
    HEALTH_STATUS = "system:health"
    CONFIG_CACHE = "system:config:{key}"
    
    @classmethod
    def format_key(cls, template: str, **kwargs) -> str:
        """Format cache key template with provided values.
        
        Args:
            template: Cache key template with placeholders
            **kwargs: Values to substitute in template
            
        Returns:
            Formatted cache key
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error("Cache key formatting failed", template=template, kwargs=kwargs, error=str(e))
            # Return a safe fallback key
            return f"cache:error:{hash(str(kwargs))}"


class CacheManager:
    """Redis cache manager for high-performance caching.
    
    Supports the design document's performance requirements:
    - Sub-3-second API response times
    - 1,000+ concurrent users
    - Intelligent request queuing and caching
    """
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client: Optional[Redis] = None
        self._connection_pool = None
    
    async def initialize(self):
        """Initialize Redis connection pool."""
        try:
            # Create connection pool for better performance
            self._connection_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30,
            )
            
            self.redis_client = Redis(
                connection_pool=self._connection_pool,
                decode_responses=True,
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Redis cache", error=str(e), exc_info=True)
            raise
    
    async def close(self):
        """Close Redis connections."""
        if self.redis_client:
            await self.redis_client.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.redis_client:
            await self.initialize()
        
        try:
            value = await self.redis_client.get(key)
            if value is None:
                return None
            
            # Try to deserialize JSON, fallback to string
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error("Cache get failed", key=key, error=str(e))
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """Set value in cache with optional expiration."""
        if not self.redis_client:
            await self.initialize()
        
        try:
            # Serialize complex objects to JSON
            if isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = str(value)
            
            # Convert timedelta to seconds
            if isinstance(expire, timedelta):
                expire = int(expire.total_seconds())
            
            result = await self.redis_client.set(key, serialized_value, ex=expire)
            return bool(result)
            
        except Exception as e:
            logger.error("Cache set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.redis_client:
            await self.initialize()
        
        try:
            result = await self.redis_client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error("Cache delete failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.redis_client:
            await self.initialize()
        
        try:
            result = await self.redis_client.exists(key)
            return bool(result)
        except Exception as e:
            logger.error("Cache exists check failed", key=key, error=str(e))
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter in cache."""
        if not self.redis_client:
            await self.initialize()
        
        try:
            result = await self.redis_client.incrby(key, amount)
            return result
        except Exception as e:
            logger.error("Cache increment failed", key=key, error=str(e))
            return None
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for existing key."""
        if not self.redis_client:
            await self.initialize()
        
        try:
            result = await self.redis_client.expire(key, seconds)
            return bool(result)
        except Exception as e:
            logger.error("Cache expire failed", key=key, error=str(e))
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance."""
        if not self.redis_client:
            try:
                await self.initialize()
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "message": "Failed to initialize Redis connection",
                    "error": str(e)
                }
        
        try:
            # Test basic operations
            test_key = "health_check_test"
            test_value = "test_value"
            
            # Set test value
            await self.redis_client.set(test_key, test_value, ex=10)
            
            # Get test value
            retrieved_value = await self.redis_client.get(test_key)
            
            # Clean up
            await self.redis_client.delete(test_key)
            
            if retrieved_value == test_value:
                return {
                    "status": "healthy",
                    "message": "Redis cache is working correctly"
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Redis cache test failed",
                    "error": f"Expected {test_value}, got {retrieved_value}"
                }
                
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "message": "Redis health check failed",
                "error": str(e)
            }


class CacheDecorator:
    """Decorator for caching function results."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    def cached(
        self, 
        expire: Union[int, timedelta] = 3600,
        key_prefix: str = "",
        key_builder: Optional[callable] = None
    ):
        """Cache decorator for functions.
        
        Args:
            expire: Cache expiration time in seconds or timedelta
            key_prefix: Prefix for cache keys
            key_builder: Custom function to build cache key from args
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Build cache key
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    # Default key building
                    func_name = f"{func.__module__}.{func.__name__}"
                    args_str = "_".join(str(arg) for arg in args)
                    kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = f"{key_prefix}{func_name}_{args_str}_{kwargs_str}"
                
                # Try to get from cache
                cached_result = await self.cache_manager.get(cache_key)
                if cached_result is not None:
                    logger.debug("Cache hit", cache_key=cache_key)
                    return cached_result
                
                # Execute function and cache result
                logger.debug("Cache miss", cache_key=cache_key)
                result = await func(*args, **kwargs)
                
                # Cache the result
                await self.cache_manager.set(cache_key, result, expire)
                
                return result
            
            return wrapper
        return decorator


class RateLimiter:
    """Redis-based rate limiter for API endpoints.
    
    Implements the design document's rate limiting strategy:
    - Per-user and per-endpoint rate limits
    - Intelligent request queuing
    """
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    async def is_allowed(
        self, 
        identifier: str, 
        limit: int, 
        window_seconds: int = 3600
    ) -> Dict[str, Any]:
        """Check if request is allowed under rate limit.
        
        Args:
            identifier: Unique identifier (user_id, IP, etc.)
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            Dict with allowed status and metadata
        """
        key = f"rate_limit:{identifier}"
        
        try:
            # Get current count
            current_count = await self.cache_manager.get(key)
            if current_count is None:
                current_count = 0
            else:
                current_count = int(current_count)
            
            if current_count >= limit:
                return {
                    "allowed": False,
                    "current_count": current_count,
                    "limit": limit,
                    "reset_time": window_seconds,
                    "retry_after": window_seconds
                }
            
            # Increment counter
            new_count = await self.cache_manager.increment(key)
            if new_count == 1:
                # Set expiration for new key
                await self.cache_manager.expire(key, window_seconds)
            
            return {
                "allowed": True,
                "current_count": new_count,
                "limit": limit,
                "remaining": limit - new_count,
                "reset_time": window_seconds
            }
            
        except Exception as e:
            logger.error("Rate limit check failed", identifier=identifier, error=str(e))
            # Fail open - allow request if rate limiter fails
            return {
                "allowed": True,
                "error": "Rate limiter unavailable"
            }


# Global cache manager instance
cache_manager = CacheManager()

# Cache decorator instance
cache_decorator = CacheDecorator(cache_manager)

# Rate limiter instance
rate_limiter = RateLimiter(cache_manager)


# Convenience functions for backward compatibility
def get_cache_key(template: str, **kwargs) -> str:
    """Get formatted cache key."""
    return CacheKeys.format_key(template, **kwargs)


async def cache_get(key: str) -> Any:
    """Get value from cache."""
    return await cache_manager.get(key)


async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set value in cache."""
    return await cache_manager.set(key, value, ttl)