"""
Session Management Service for the AI Opportunity Browser.

This module provides comprehensive session lifecycle management, tracking,
and security monitoring for user authentication sessions.
"""

import json
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum

from api.core.config import get_settings
from shared.database import get_redis_client
from shared.models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()


class SessionStatus(str, Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPICIOUS = "suspicious"


class SessionDevice(str, Enum):
    """Device type enumeration."""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"
    UNKNOWN = "unknown"


@dataclass
class SessionInfo:
    """Session information data class."""
    session_id: str
    user_id: str
    access_token_jti: str
    refresh_token_jti: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str
    device_type: SessionDevice
    device_fingerprint: Optional[str]
    location: Optional[Dict[str, str]]
    status: SessionStatus
    two_factor_verified: bool = False
    suspicious_activity_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['created_at'] = self.created_at.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        data['expires_at'] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionInfo':
        """Create from dictionary (Redis retrieval)."""
        # Convert ISO strings back to datetime objects
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        
        # Convert enums
        data['device_type'] = SessionDevice(data['device_type'])
        data['status'] = SessionStatus(data['status'])
        
        return cls(**data)


class SessionManager:
    """
    Comprehensive session management service.
    """
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.session_timeout = getattr(settings, 'SESSION_TIMEOUT_HOURS', 24) * 3600  # Convert to seconds
        self.max_sessions_per_user = getattr(settings, 'MAX_SESSIONS_PER_USER', 10)
        self.suspicious_activity_threshold = 5
        self.activity_update_interval = 300  # 5 minutes
    
    def create_session(
        self,
        user: User,
        access_token_jti: str,
        refresh_token_jti: str,
        ip_address: str,
        user_agent: str,
        device_fingerprint: Optional[str] = None,
        location: Optional[Dict[str, str]] = None
    ) -> SessionInfo:
        """
        Create a new user session.
        
        Args:
            user: User object
            access_token_jti: Access token JTI
            refresh_token_jti: Refresh token JTI
            ip_address: Client IP address
            user_agent: Client user agent
            device_fingerprint: Optional device fingerprint
            location: Optional location information
            
        Returns:
            SessionInfo object
        """
        try:
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Determine device type from user agent
            device_type = self._parse_device_type(user_agent)
            
            # Create session info
            now = datetime.now(timezone.utc)
            session_info = SessionInfo(
                session_id=session_id,
                user_id=user.id,
                access_token_jti=access_token_jti,
                refresh_token_jti=refresh_token_jti,
                created_at=now,
                last_activity=now,
                expires_at=now + timedelta(seconds=self.session_timeout),
                ip_address=ip_address,
                user_agent=user_agent,
                device_type=device_type,
                device_fingerprint=device_fingerprint,
                location=location,
                status=SessionStatus.ACTIVE,
                two_factor_verified=user.two_factor_enabled if hasattr(user, 'two_factor_enabled') else False
            )
            
            # Check session limits
            self._enforce_session_limits(user.id)
            
            # Store session
            self._store_session(session_info)
            
            # Update user session list
            self._add_to_user_sessions(user.id, session_id)
            
            logger.info(f"Session created for user {user.username}: {session_id}")
            
            return session_info
            
        except Exception as e:
            logger.error(f"Error creating session for user {user.id}: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """
        Retrieve session information.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionInfo object or None if not found
        """
        try:
            session_key = f"session:{session_id}"
            session_data = self.redis_client.get(session_key)
            
            if not session_data:
                return None
            
            data = json.loads(session_data)
            return SessionInfo.from_dict(data)
            
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}")
            return None
    
    def update_session_activity(
        self,
        session_id: str,
        ip_address: Optional[str] = None,
        location: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Update session last activity timestamp.
        
        Args:
            session_id: Session identifier
            ip_address: Optional new IP address
            location: Optional new location
            
        Returns:
            True if updated successfully
        """
        try:
            session_info = self.get_session(session_id)
            if not session_info:
                return False
            
            now = datetime.now(timezone.utc)
            
            # Check if enough time has passed to warrant an update
            time_since_update = (now - session_info.last_activity).total_seconds()
            if time_since_update < self.activity_update_interval:
                return True  # Skip update but return success
            
            # Update activity timestamp
            session_info.last_activity = now
            
            # Check for IP address changes (potential suspicious activity)
            if ip_address and ip_address != session_info.ip_address:
                session_info.suspicious_activity_count += 1
                session_info.ip_address = ip_address
                
                if session_info.suspicious_activity_count >= self.suspicious_activity_threshold:
                    session_info.status = SessionStatus.SUSPICIOUS
                    logger.warning(f"Session {session_id} marked as suspicious due to IP changes")
            
            # Update location if provided
            if location:
                session_info.location = location
            
            # Extend session expiration
            session_info.expires_at = now + timedelta(seconds=self.session_timeout)
            
            # Store updated session
            self._store_session(session_info)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating session activity {session_id}: {e}")
            return False
    
    def revoke_session(self, session_id: str, reason: str = "user_logout") -> bool:
        """
        Revoke a specific session.
        
        Args:
            session_id: Session identifier
            reason: Reason for revocation
            
        Returns:
            True if revoked successfully
        """
        try:
            session_info = self.get_session(session_id)
            if not session_info:
                return False
            
            # Update session status
            session_info.status = SessionStatus.REVOKED
            
            # Store updated session with shorter TTL
            self._store_session(session_info, ttl=3600)  # Keep for 1 hour for audit
            
            # Remove from user's active sessions
            self._remove_from_user_sessions(session_info.user_id, session_id)
            
            # Blacklist associated tokens
            from shared.auth import blacklist_token
            blacklist_token(session_info.access_token_jti, session_info.expires_at)
            blacklist_token(session_info.refresh_token_jti, session_info.expires_at)
            
            logger.info(f"Session revoked: {session_id} (reason: {reason})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error revoking session {session_id}: {e}")
            return False
    
    def revoke_all_user_sessions(self, user_id: str, except_session: Optional[str] = None) -> int:
        """
        Revoke all sessions for a user.
        
        Args:
            user_id: User identifier
            except_session: Optional session ID to keep active
            
        Returns:
            Number of sessions revoked
        """
        try:
            user_sessions = self.get_user_sessions(user_id)
            revoked_count = 0
            
            for session_id in user_sessions:
                if except_session and session_id == except_session:
                    continue
                
                if self.revoke_session(session_id, "revoke_all_sessions"):
                    revoked_count += 1
            
            logger.info(f"Revoked {revoked_count} sessions for user {user_id}")
            
            return revoked_count
            
        except Exception as e:
            logger.error(f"Error revoking all sessions for user {user_id}: {e}")
            return 0
    
    def get_user_sessions(self, user_id: str) -> List[str]:
        """
        Get all active session IDs for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of session IDs
        """
        try:
            sessions_key = f"user_sessions:{user_id}"
            session_ids = self.redis_client.smembers(sessions_key)
            return [sid.decode() if isinstance(sid, bytes) else sid for sid in session_ids]
            
        except Exception as e:
            logger.error(f"Error getting user sessions for {user_id}: {e}")
            return []
    
    def get_user_session_details(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get detailed information about all user sessions.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of session details
        """
        try:
            session_ids = self.get_user_sessions(user_id)
            session_details = []
            
            for session_id in session_ids:
                session_info = self.get_session(session_id)
                if session_info:
                    # Create safe session details (no sensitive tokens)
                    details = {
                        "session_id": session_info.session_id,
                        "created_at": session_info.created_at.isoformat(),
                        "last_activity": session_info.last_activity.isoformat(),
                        "expires_at": session_info.expires_at.isoformat(),
                        "ip_address": session_info.ip_address,
                        "device_type": session_info.device_type.value,
                        "location": session_info.location,
                        "status": session_info.status.value,
                        "two_factor_verified": session_info.two_factor_verified,
                        "is_current": False  # Will be set by caller if needed
                    }
                    session_details.append(details)
            
            return session_details
            
        except Exception as e:
            logger.error(f"Error getting session details for user {user_id}: {e}")
            return []
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            # This would typically be run as a background task
            pattern = "session:*"
            session_keys = self.redis_client.keys(pattern)
            
            cleaned_count = 0
            now = datetime.now(timezone.utc)
            
            for key in session_keys:
                try:
                    session_data = self.redis_client.get(key)
                    if session_data:
                        data = json.loads(session_data)
                        expires_at = datetime.fromisoformat(data['expires_at'])
                        
                        if expires_at <= now:
                            session_id = data['session_id']
                            user_id = data['user_id']
                            
                            # Remove from user sessions
                            self._remove_from_user_sessions(user_id, session_id)
                            
                            # Delete session
                            self.redis_client.delete(key)
                            cleaned_count += 1
                            
                except Exception as e:
                    logger.error(f"Error processing session {key}: {e}")
                    continue
            
            logger.info(f"Cleaned up {cleaned_count} expired sessions")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """
        Get session statistics.
        
        Returns:
            Dictionary with session statistics
        """
        try:
            pattern = "session:*"
            all_sessions = self.redis_client.keys(pattern)
            
            stats = {
                "total_sessions": len(all_sessions),
                "active_sessions": 0,
                "expired_sessions": 0,
                "revoked_sessions": 0,
                "suspicious_sessions": 0,
                "device_breakdown": {
                    "desktop": 0,
                    "mobile": 0,
                    "tablet": 0,
                    "unknown": 0
                }
            }
            
            now = datetime.now(timezone.utc)
            
            for key in all_sessions:
                try:
                    session_data = self.redis_client.get(key)
                    if session_data:
                        data = json.loads(session_data)
                        status = data.get('status', 'active')
                        device_type = data.get('device_type', 'unknown')
                        expires_at = datetime.fromisoformat(data['expires_at'])
                        
                        # Count by status
                        if expires_at <= now:
                            stats["expired_sessions"] += 1
                        elif status == "revoked":
                            stats["revoked_sessions"] += 1
                        elif status == "suspicious":
                            stats["suspicious_sessions"] += 1
                        else:
                            stats["active_sessions"] += 1
                        
                        # Count by device type
                        stats["device_breakdown"][device_type] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing session statistics for {key}: {e}")
                    continue
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting session statistics: {e}")
            return {}
    
    def _store_session(self, session_info: SessionInfo, ttl: Optional[int] = None) -> None:
        """Store session in Redis."""
        session_key = f"session:{session_info.session_id}"
        session_data = json.dumps(session_info.to_dict())
        
        if ttl:
            self.redis_client.setex(session_key, ttl, session_data)
        else:
            # Use session timeout as TTL
            remaining_time = (session_info.expires_at - datetime.now(timezone.utc)).total_seconds()
            if remaining_time > 0:
                self.redis_client.setex(session_key, int(remaining_time), session_data)
    
    def _add_to_user_sessions(self, user_id: str, session_id: str) -> None:
        """Add session to user's session set."""
        sessions_key = f"user_sessions:{user_id}"
        self.redis_client.sadd(sessions_key, session_id)
        # Set expiration on the user sessions set
        self.redis_client.expire(sessions_key, self.session_timeout * 2)
    
    def _remove_from_user_sessions(self, user_id: str, session_id: str) -> None:
        """Remove session from user's session set."""
        sessions_key = f"user_sessions:{user_id}"
        self.redis_client.srem(sessions_key, session_id)
    
    def _enforce_session_limits(self, user_id: str) -> None:
        """Enforce maximum sessions per user."""
        user_sessions = self.get_user_sessions(user_id)
        
        if len(user_sessions) >= self.max_sessions_per_user:
            # Remove oldest sessions
            sessions_to_remove = len(user_sessions) - self.max_sessions_per_user + 1
            
            # Get session details to find oldest
            session_details = []
            for session_id in user_sessions:
                session_info = self.get_session(session_id)
                if session_info:
                    session_details.append((session_id, session_info.created_at))
            
            # Sort by creation time and remove oldest
            session_details.sort(key=lambda x: x[1])
            for i in range(sessions_to_remove):
                session_id = session_details[i][0]
                self.revoke_session(session_id, "session_limit_exceeded")
                logger.info(f"Revoked oldest session {session_id} for user {user_id} due to session limit")
    
    def _parse_device_type(self, user_agent: str) -> SessionDevice:
        """Parse device type from user agent."""
        user_agent_lower = user_agent.lower()
        
        if any(mobile in user_agent_lower for mobile in ['mobile', 'android', 'iphone']):
            return SessionDevice.MOBILE
        elif any(tablet in user_agent_lower for tablet in ['tablet', 'ipad']):
            return SessionDevice.TABLET
        elif any(desktop in user_agent_lower for desktop in ['windows', 'macintosh', 'linux']):
            return SessionDevice.DESKTOP
        else:
            return SessionDevice.UNKNOWN


# Global session manager instance
session_manager = SessionManager()