"""
Authentication utilities - separate from main auth module to avoid circular imports.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    # Use a default secret for now - in production this should come from config
    encoded_jwt = jwt.encode(to_encode, "your-secret-key-change-in-production", algorithm="HS256")
    return encoded_jwt

def calculate_reputation_score(user_data: Dict[str, Any]) -> int:
    """Calculate user reputation score based on activities."""
    base_score = 100
    validations_score = user_data.get('validations_count', 0) * 10
    discussions_score = user_data.get('discussions_count', 0) * 5
    return base_score + validations_score + discussions_score

def determine_user_influence_weight(user_data: Dict[str, Any]) -> float:
    """Determine user's influence weight for validation aggregation."""
    reputation = user_data.get('reputation_score', 100)
    expertise_count = len(user_data.get('expertise_domains', []))
    
    # Base weight
    weight = 1.0
    
    # Reputation bonus
    if reputation > 1000:
        weight += 0.5
    elif reputation > 500:
        weight += 0.3
    elif reputation > 200:
        weight += 0.1
    
    # Expertise bonus
    weight += min(expertise_count * 0.1, 0.5)
    
    return min(weight, 3.0)  # Cap at 3x weight

def should_notify_expert(user_data: Dict[str, Any], opportunity_domain: str) -> bool:
    """Determine if expert should be notified about opportunity."""
    expertise_domains = user_data.get('expertise_domains', [])
    reputation = user_data.get('reputation_score', 0)
    
    # Check domain match
    domain_match = any(domain.lower() in opportunity_domain.lower() 
                      for domain in expertise_domains)
    
    # Require minimum reputation for notifications
    meets_reputation = reputation >= 200
    
    return domain_match and meets_reputation