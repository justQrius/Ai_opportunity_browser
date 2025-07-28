"""Test configuration and fixtures."""

import pytest
import asyncio
import json
from typing import List, Optional
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from shared.models.base import Base
from shared.models.user import User, UserRole
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.user_interaction import UserInteraction, InteractionType
from shared.auth import hash_password, create_access_token


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create test database session."""
    async_session = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


async def create_test_user(
    db_session: AsyncSession,
    email: str,
    username: str,
    password: str = "testpassword123",
    full_name: Optional[str] = None,
    expertise_domains: Optional[List[str]] = None,
    role: UserRole = UserRole.USER
) -> User:
    """Create a test user."""
    hashed_password = hash_password(password)
    
    expertise_domains_json = None
    if expertise_domains:
        expertise_domains_json = json.dumps(expertise_domains)
    
    user = User(
        email=email,
        username=username,
        hashed_password=hashed_password,
        full_name=full_name or f"Test {username}",
        role=role,
        expertise_domains=expertise_domains_json,
        is_active=True,
        is_verified=True,
        reputation_score=5.0
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


async def create_test_opportunity(
    db_session: AsyncSession,
    title: str,
    description: Optional[str] = None,
    ai_solution_types: Optional[List[str]] = None,
    target_industries: Optional[List[str]] = None,
    implementation_complexity: str = "medium",
    market_size_estimate: str = "medium",
    validation_score: float = 7.0
) -> Opportunity:
    """Create a test opportunity."""
    ai_solution_types_json = None
    if ai_solution_types:
        ai_solution_types_json = json.dumps(ai_solution_types)
    
    target_industries_json = None
    if target_industries:
        target_industries_json = json.dumps(target_industries)
    
    opportunity = Opportunity(
        title=title,
        description=description or f"Test opportunity: {title}",
        ai_solution_types=ai_solution_types_json,
        target_industries=target_industries_json,
        implementation_complexity=implementation_complexity,
        market_size_estimate=market_size_estimate,
        validation_score=validation_score,
        status=OpportunityStatus.VALIDATED
    )
    
    db_session.add(opportunity)
    await db_session.commit()
    await db_session.refresh(opportunity)
    
    return opportunity


def get_auth_headers(user_id: str) -> dict:
    """Get authentication headers for test requests."""
    token = create_access_token({"sub": user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_user():
    """Create mock user for testing."""
    user = User(
        id="test-user-id",
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
        full_name="Test User",
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
        reputation_score=5.0
    )
    return user


@pytest.fixture
def mock_opportunity():
    """Create mock opportunity for testing."""
    opportunity = Opportunity(
        id="test-opportunity-id",
        title="Test AI Opportunity",
        description="A test opportunity for AI solutions",
        ai_solution_types='["nlp", "machine_learning"]',
        target_industries='["healthcare", "fintech"]',
        implementation_complexity="medium",
        market_size_estimate="large",
        validation_score=8.0,
        status=OpportunityStatus.VALIDATED
    )
    return opportunity