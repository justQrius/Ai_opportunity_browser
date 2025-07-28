"""Tests for Redis cache functionality."""

import pytest
import asyncio
from datetime import timedelta
from shared.cache import cache_manager, rate_limiter
from shared.session import session_manager


class TestCacheManager:
    """Test Redis cache manager functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_basic_operations(self):
        """Test basic cache set/get/delete operations."""
        # Initialize cache
        await cache_manager.initialize()
        
        # Test string value
        key = "test_string"
        value = "test_value"
        
        assert await cache_manager.set(key, value)
        assert await cache_manager.get(key) == value
        assert await cache_manager.exists(key)
        assert await cache_manager.delete(key)
        assert not await cache_manager.exists(key)
    
    @pytest.mark.asyncio
    async def test_cache_json_serialization(self):
        """Test caching of complex data structures."""
        await cache_manager.initialize()
        
        # Test dictionary
        key = "test_dict"
        value = {"name": "test", "count": 42, "active": True}
        
        assert await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        assert retrieved == value
        
        # Test list
        key = "test_list"
        value = [1, 2, 3, "test", {"nested": True}]
        
        assert await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        assert retrieved == value
        
        # Cleanup
        await cache_manager.delete("test_dict")
        await cache_manager.delete("test_list")
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test cache expiration functionality."""
        await cache_manager.initialize()
        
        key = "test_expire"
        value = "expire_me"
        
        # Set with 1 second expiration
        assert await cache_manager.set(key, value, expire=1)
        assert await cache_manager.get(key) == value
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        assert await cache_manager.get(key) is None
    
    @pytest.mark.asyncio
    async def test_cache_increment(self):
        """Test cache increment functionality."""
        await cache_manager.initialize()
        
        key = "test_counter"
        
        # Test increment
        count = await cache_manager.increment(key)
        assert count == 1
        
        count = await cache_manager.increment(key, 5)
        assert count == 6
        
        # Cleanup
        await cache_manager.delete(key)
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test cache health check."""
        await cache_manager.initialize()
        
        health = await cache_manager.health_check()
        assert health["status"] == "healthy"
        assert "message" in health


class TestRateLimiter:
    """Test Redis-based rate limiter."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        await cache_manager.initialize()
        
        identifier = "test_user"
        limit = 3
        window = 60
        
        # First requests should be allowed
        for i in range(limit):
            result = await rate_limiter.is_allowed(identifier, limit, window)
            assert result["allowed"] is True
            assert result["current_count"] == i + 1
            assert result["remaining"] == limit - (i + 1)
        
        # Next request should be denied
        result = await rate_limiter.is_allowed(identifier, limit, window)
        assert result["allowed"] is False
        assert result["current_count"] == limit
        
        # Cleanup
        await cache_manager.delete(f"rate_limit:{identifier}")


class TestSessionManager:
    """Test Redis-based session management."""
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self):
        """Test complete session lifecycle."""
        await cache_manager.initialize()
        
        user_id = "test_user_123"
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "role": "user"
        }
        
        # Create session
        session_id = await session_manager.create_session(user_id, user_data)
        assert session_id is not None
        
        # Get session
        session = await session_manager.get_session(session_id)
        assert session is not None
        assert session["user_id"] == user_id
        assert session["user_data"] == user_data
        
        # Update session
        updated_data = {"last_login": "2024-01-01"}
        assert await session_manager.update_session(session_id, updated_data)
        
        # Verify update
        session = await session_manager.get_session(session_id)
        assert session["user_data"]["last_login"] == "2024-01-01"
        
        # Delete session
        assert await session_manager.delete_session(session_id)
        
        # Verify deletion
        session = await session_manager.get_session(session_id)
        assert session is None
    
    @pytest.mark.asyncio
    async def test_session_extension(self):
        """Test session expiration extension."""
        await cache_manager.initialize()
        
        user_id = "test_user_456"
        user_data = {"username": "testuser2"}
        
        # Create session
        session_id = await session_manager.create_session(user_id, user_data, ttl=2)
        
        # Extend session
        assert await session_manager.extend_session(session_id, ttl=10)
        
        # Session should still exist after original TTL
        await asyncio.sleep(2.1)
        session = await session_manager.get_session(session_id)
        assert session is not None
        
        # Cleanup
        await session_manager.delete_session(session_id)