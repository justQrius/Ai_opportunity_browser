"""
Database connection and session management for the AI Opportunity Browser.

This module provides database connectivity, session management, and health checks
for PostgreSQL, Redis, and vector database connections.
"""

import asyncio
import time
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
import logging

from sqlalchemy import create_engine, text, pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import redis.asyncio as redis
from redis.exceptions import RedisError

from api.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global connection objects
_sync_engine = None
_async_engine = None
_session_factory = None
_async_session_factory = None
_redis_client = None


def get_sync_engine():
    """Get or create synchronous database engine."""
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(
            settings.database_url_sync,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.DEBUG
        )
    return _sync_engine


def get_async_engine():
    """Get or create asynchronous database engine."""
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            settings.database_url_async,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.DEBUG
        )
    return _async_engine


def get_session_factory():
    """Get or create synchronous session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_sync_engine()
        _session_factory = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False
        )
    return _session_factory


def get_async_session_factory():
    """Get or create asynchronous session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_async_engine()
        _async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
    return _async_session_factory


async def get_redis_client():
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
    return _redis_client


@asynccontextmanager
async def get_db_session():
    """Get database session context manager."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db_session():
    """Get synchronous database session context manager."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def check_database_health() -> Dict[str, Any]:
    """Check PostgreSQL database health and connectivity."""
    start_time = time.time()
    
    try:
        # Test with synchronous engine for health checks
        engine = get_sync_engine()
        
        with engine.connect() as conn:
            # Simple query to test connectivity
            result = conn.execute(text("SELECT 1 as health_check"))
            health_value = result.fetchone()[0]
            
            if health_value == 1:
                response_time = (time.time() - start_time) * 1000
                
                # Get additional database info
                db_info = conn.execute(text("SELECT version()")).fetchone()[0]
                
                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "message": "Database connection successful",
                    "database_info": db_info.split(',')[0],  # Just the version part
                    "pool_size": settings.DATABASE_POOL_SIZE,
                    "pool_checked_in": engine.pool.checkedin(),
                    "pool_checked_out": engine.pool.checkedout(),
                    "pool_overflow": engine.pool.overflow(),
                }
            else:
                return {
                    "status": "unhealthy",
                    "response_time_ms": (time.time() - start_time) * 1000,
                    "message": "Database query returned unexpected result",
                    "error": f"Expected 1, got {health_value}"
                }
                
    except SQLAlchemyError as e:
        return {
            "status": "unhealthy",
            "response_time_ms": (time.time() - start_time) * 1000,
            "message": "Database connection failed",
            "error": str(e),
            "error_type": "SQLAlchemyError"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "response_time_ms": (time.time() - start_time) * 1000,
            "message": "Unexpected database error",
            "error": str(e),
            "error_type": type(e).__name__
        }


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis cache health and connectivity."""
    start_time = time.time()
    
    try:
        redis_client = await get_redis_client()
        
        # Test basic connectivity
        await redis_client.ping()
        
        # Test set/get operations
        test_key = "health_check_test"
        test_value = f"health_check_{int(time.time())}"
        
        await redis_client.set(test_key, test_value, ex=10)  # Expire in 10 seconds
        retrieved_value = await redis_client.get(test_key)
        
        if retrieved_value == test_value:
            # Clean up test key
            await redis_client.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000
            
            # Get Redis info
            info = await redis_client.info()
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "message": "Redis connection successful",
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
        else:
            return {
                "status": "unhealthy",
                "response_time_ms": (time.time() - start_time) * 1000,
                "message": "Redis set/get test failed",
                "error": f"Expected {test_value}, got {retrieved_value}"
            }
            
    except RedisError as e:
        return {
            "status": "unhealthy",
            "response_time_ms": (time.time() - start_time) * 1000,
            "message": "Redis connection failed",
            "error": str(e),
            "error_type": "RedisError"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "response_time_ms": (time.time() - start_time) * 1000,
            "message": "Unexpected Redis error",
            "error": str(e),
            "error_type": type(e).__name__
        }


async def check_vector_db_health() -> Dict[str, Any]:
    """Check vector database (Pinecone) health and connectivity."""
    start_time = time.time()
    
    try:
        # Check if Pinecone API key is configured
        if not settings.PINECONE_API_KEY:
            return {
                "status": "not_configured",
                "response_time_ms": (time.time() - start_time) * 1000,
                "message": "Pinecone API key not configured",
                "note": "Vector database will be configured in later phases"
            }
        
        # TODO: Implement actual Pinecone connectivity check
        # This will be implemented when Pinecone integration is added
        return {
            "status": "not_implemented",
            "response_time_ms": (time.time() - start_time) * 1000,
            "message": "Vector database connectivity check not yet implemented",
            "note": "Will be implemented in Phase 3 (Data Ingestion)"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "response_time_ms": (time.time() - start_time) * 1000,
            "message": "Vector database check failed",
            "error": str(e),
            "error_type": type(e).__name__
        }


async def initialize_connections():
    """Initialize all database connections."""
    logger.info("Initializing database connections...")
    
    try:
        # Initialize PostgreSQL
        engine = get_sync_engine()
        logger.info("PostgreSQL engine initialized")
        
        # Initialize Redis
        redis_client = await get_redis_client()
        await redis_client.ping()
        logger.info("Redis connection initialized")
        
        logger.info("All database connections initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database connections: {e}")
        raise


async def close_connections():
    """Close all database connections."""
    global _sync_engine, _async_engine, _redis_client
    
    logger.info("Closing database connections...")
    
    try:
        # Close Redis connection
        if _redis_client:
            await _redis_client.close()
            _redis_client = None
            logger.info("Redis connection closed")
        
        # Close async engine
        if _async_engine:
            await _async_engine.dispose()
            _async_engine = None
            logger.info("Async database engine closed")
        
        # Close sync engine
        if _sync_engine:
            _sync_engine.dispose()
            _sync_engine = None
            logger.info("Sync database engine closed")
        
        logger.info("All database connections closed successfully")
        
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


# Dependency injection functions for FastAPI
async def get_db():
    """FastAPI dependency for database session."""
    async with get_db_session() as session:
        yield session


async def get_redis():
    """FastAPI dependency for Redis client."""
    return await get_redis_client()