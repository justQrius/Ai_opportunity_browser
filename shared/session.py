"""Session management utilities using Redis."""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from .cache import cache_manager
import structlog

logger = structlog.get_logger(__name__)


class SessionManager:
    """Redis-based session management for user authentication.
    
    Supports the design document's authentication requirements and
    high-performance session handling for 1,000+ concurrent users.
    """
    
    def __init__(self, session_prefix: str = "session:", default_ttl: int = 86400):
        self.session_prefix = session_prefix
        self.default_ttl = default_ttl  # 24 hours default
    
    def _get_session_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"{self.session_prefix}{session_id}"
    
    async def create_session(
        self, 
        user_id: str, 
        user_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> str:
        """Create a new session.
        
        Args:
            user_id: User identifier
            user_data: User data to store in session
            ttl: Session time-to-live in seconds
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        session_key = self._get_session_key(session_id)
        
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "user_data": user_data
        }
        
        ttl = ttl or self.default_ttl
        success = await cache_manager.set(session_key, session_data, expire=ttl)
        
        if success:
            logger.info("Session created", session_id=session_id, user_id=user_id)
            return session_id
        else:
            logger.error("Failed to create session", user_id=user_id)
            raise RuntimeError("Failed to create session")
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found
        """
        session_key = self._get_session_key(session_id)
        session_data = await cache_manager.get(session_key)
        
        if session_data:
            # Update last accessed time
            session_data["last_accessed"] = datetime.utcnow().isoformat()
            await cache_manager.set(session_key, session_data, expire=self.default_ttl)
            
            logger.debug("Session accessed", session_id=session_id)
            return session_data
        
        logger.debug("Session not found", session_id=session_id)
        return None
    
    async def update_session(
        self, 
        session_id: str, 
        user_data: Dict[str, Any]
    ) -> bool:
        """Update session data.
        
        Args:
            session_id: Session identifier
            user_data: Updated user data
            
        Returns:
            True if successful, False otherwise
        """
        session_key = self._get_session_key(session_id)
        session_data = await cache_manager.get(session_key)
        
        if not session_data:
            logger.warning("Attempted to update non-existent session", session_id=session_id)
            return False
        
        session_data["user_data"].update(user_data)
        session_data["last_accessed"] = datetime.utcnow().isoformat()
        
        success = await cache_manager.set(session_key, session_data, expire=self.default_ttl)
        
        if success:
            logger.debug("Session updated", session_id=session_id)
        else:
            logger.error("Failed to update session", session_id=session_id)
        
        return success
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful, False otherwise
        """
        session_key = self._get_session_key(session_id)
        success = await cache_manager.delete(session_key)
        
        if success:
            logger.info("Session deleted", session_id=session_id)
        else:
            logger.warning("Failed to delete session", session_id=session_id)
        
        return success
    
    async def extend_session(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """Extend session expiration.
        
        Args:
            session_id: Session identifier
            ttl: New time-to-live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        session_key = self._get_session_key(session_id)
        ttl = ttl or self.default_ttl
        
        success = await cache_manager.expire(session_key, ttl)
        
        if success:
            logger.debug("Session extended", session_id=session_id, ttl=ttl)
        else:
            logger.warning("Failed to extend session", session_id=session_id)
        
        return success


class CacheKeys:
    """Centralized cache key definitions for consistency.
    
    Implements the design document's caching strategy for:
    - Opportunity data caching
    - Market signal caching
    - User preference caching
    - Validation result caching
    """
    
    # Opportunity caching
    OPPORTUNITY_BY_ID = "opportunity:id:{opportunity_id}"
    OPPORTUNITY_LIST = "opportunity:list:{filters_hash}"
    OPPORTUNITY_SEARCH = "opportunity:search:{query_hash}"
    OPPORTUNITY_RECOMMENDATIONS = "opportunity:recommendations:{user_id}"
    
    # Market signal caching
    MARKET_SIGNALS_BY_OPPORTUNITY = "market_signals:opportunity:{opportunity_id}"
    MARKET_SIGNALS_BY_SOURCE = "market_signals:source:{source}:{page}"
    
    # User caching
    USER_BY_ID = "user:id:{user_id}"
    USER_BY_EMAIL = "user:email:{email}"
    USER_PREFERENCES = "user:preferences:{user_id}"
    USER_REPUTATION = "user:reputation:{user_id}"
    
    # Validation caching
    VALIDATION_RESULTS = "validation:opportunity:{opportunity_id}"
    VALIDATION_BY_USER = "validation:user:{user_id}:{page}"
    
    # Analytics caching
    MARKET_ANALYSIS = "analytics:market:{opportunity_id}"
    TREND_ANALYSIS = "analytics:trends:{timeframe}"
    COMPETITIVE_ANALYSIS = "analytics:competition:{opportunity_id}"
    
    # Rate limiting
    RATE_LIMIT_USER = "rate_limit:user:{user_id}"
    RATE_LIMIT_IP = "rate_limit:ip:{ip_address}"
    RATE_LIMIT_ENDPOINT = "rate_limit:endpoint:{endpoint}:{identifier}"
    
    @staticmethod
    def format_key(template: str, **kwargs) -> str:
        """Format cache key template with parameters."""
        return template.format(**kwargs)


# Global session manager instance
session_manager = SessionManager()