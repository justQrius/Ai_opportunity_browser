#!/usr/bin/env python3
"""
Basic logging test without OpenTelemetry dependencies.

This script tests the core logging functionality without requiring
the full OpenTelemetry stack to be installed.
"""

import asyncio
import uuid
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Test basic structured logging
    import structlog
    
    # Configure basic structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.dev.ConsoleRenderer(colors=True)
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logger = structlog.get_logger(__name__)
    
    print("🚀 Basic Logging Test")
    print("=" * 40)
    
    # Test basic logging
    logger.info("Starting basic logging test")
    logger.info("Processing user request", user_id="user_123", action="view_opportunities")
    logger.warning("Rate limit approaching", current_requests=95, limit=100)
    logger.error("Database connection failed", error="Connection timeout", retry_count=3)
    
    # Test logging with extra context
    logger.info(
        "Opportunity created successfully",
        opportunity_id="opp_456",
        title="AI-powered customer service",
        market_size="$2.5B",
        validation_score=8.5
    )
    
    print("\n✅ Basic logging test completed successfully!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please install required dependencies: pip install structlog")
    sys.exit(1)
except Exception as e:
    print(f"❌ Test failed: {e}")
    sys.exit(1)


if __name__ == "__main__":
    pass