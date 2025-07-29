"""
FastAPI main application for AI Opportunity Browser.

This module sets up the FastAPI application with proper configuration,
middleware, and routing for the AI Opportunity Browser platform.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import logging
from typing import Dict, Any

from api.core.config import get_settings
from api.routers import health, auth, opportunities, users, validations, reputation, moderation, recommendations, discussions, business_intelligence, timeline_estimation, user_matching, messaging, events, configuration, feature_flags, metrics, security, audit, agents
from api.middleware.security import SecurityHeadersMiddleware, ThreatDetectionMiddleware, ZeroTrustMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.event_middleware import EventBusMiddleware, EventContextMiddleware
from api.middleware.logging_middleware import LoggingMiddleware, UserContextMiddleware
from shared.observability import setup_observability, ObservabilityConfig, get_observability_manager
from shared.logging_config import get_logger
from shared.security.zero_trust import setup_zero_trust
from shared.security.service_config import setup_service_registry
from shared.security.monitoring import setup_security_monitoring
from agents.orchestrator import AgentOrchestrator
from agents.planner_agent import PlannerAgent
from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent

# Setup observability (logging, tracing, monitoring)
observability_config = ObservabilityConfig(
    service_name="ai-opportunity-browser-api",
    service_version="1.0.0",
    log_level="INFO",
    enable_tracing=True,
    enable_metrics=True,
    jaeger_endpoint=None,  # Will be set from environment
    otlp_endpoint=None     # Will be set from environment
)
setup_observability(observability_config)
logger = get_logger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("🚀 Starting AI Opportunity Browser API")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Initialize database connections
    try:
        from shared.database import initialize_connections
        await initialize_connections()
        logger.info("✅ Database connections initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database connections: {e}")
        # Don't fail startup - let health checks handle it
    
    # Initialize event bus system
    try:
        from shared.event_config import get_event_bus_manager
        event_manager = await get_event_bus_manager()
        logger.info("✅ Event bus system initialized")
        
        # Store event manager in app state for access in endpoints
        app.state.event_manager = event_manager
    except Exception as e:
        logger.error(f"❌ Failed to initialize event bus system: {e}")
        # Don't fail startup - let health checks handle it
    
    # Initialize observability system
    try:
        observability_manager = get_observability_manager()
        app.state.observability = observability_manager
        logger.info("✅ Observability system initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize observability system: {e}")
        # Don't fail startup - let health checks handle it
    
    # Initialize zero trust security architecture
    try:
        # Setup service registry
        service_registry = setup_service_registry()
        app.state.service_registry = service_registry
        
        # Setup zero trust manager with service secrets
        service_secrets = service_registry.get_service_secrets()
        zero_trust_manager = setup_zero_trust(service_secrets)
        app.state.zero_trust_manager = zero_trust_manager
        
        logger.info("✅ Zero trust security architecture initialized")
        logger.info(f"Registered {len(service_secrets)} services for authentication")
        
        # Setup security monitoring
        security_monitor = setup_security_monitoring()
        app.state.security_monitor = security_monitor
        logger.info("✅ Security monitoring system initialized")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize zero trust security: {e}")
        # Don't fail startup - let health checks handle it
    
    # Initialize and start the agent orchestrator
    try:
        orchestrator = AgentOrchestrator()
        orchestrator.register_agent_type("PlannerAgent", PlannerAgent)
        orchestrator.register_agent_type("ResearchAgent", ResearchAgent)
        orchestrator.register_agent_type("AnalysisAgent", AnalysisAgent)
        await orchestrator.start()
        app.state.orchestrator = orchestrator
        logger.info("✅ Agent orchestrator started and agents registered")

        # Deploy initial worker agents
        initial_agents = {
            "PlannerAgent": 1,
            "ResearchAgent": 2,
            "AnalysisAgent": 2,
        }
        for agent_type, count in initial_agents.items():
            for i in range(count):
                try:
                    await orchestrator.deploy_agent(agent_type, agent_id=f"{agent_type}_{i+1}")
                except Exception as e:
                    logger.error(f"Failed to deploy initial agent {agent_type}_{i+1}: {e}")
    except Exception as e:
        logger.error(f"❌ Failed to start agent orchestrator: {e}")

    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AI Opportunity Browser API")
    
    # Shutdown event bus system
    try:
        if hasattr(app.state, 'event_manager'):
            await app.state.event_manager.shutdown()
            logger.info("✅ Event bus system shutdown")
    except Exception as e:
        logger.error(f"❌ Error shutting down event bus system: {e}")

    # Shutdown agent orchestrator
    try:
        if hasattr(app.state, 'orchestrator'):
            await app.state.orchestrator.stop()
            logger.info("✅ Agent orchestrator stopped")
    except Exception as e:
        logger.error(f"❌ Error stopping agent orchestrator: {e}")
    
    # Cleanup database connections
    try:
        from shared.database import close_connections
        await close_connections()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Error closing database connections: {e}")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="AI Opportunity Browser API",
        description="API for discovering, validating, and browsing AI-solvable market opportunities",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan
    )
    
    # Configure CORS
    if settings.ALLOWED_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            allow_headers=["*"],
        )
    
    # Add comprehensive logging middleware (should be early in the chain)
    app.add_middleware(LoggingMiddleware, skip_paths=["/health", "/metrics", "/docs", "/openapi.json"])
    
    # Add user context middleware for JWT token processing
    app.add_middleware(UserContextMiddleware)
    
    # Add zero trust security middleware (temporarily disabled for testing)
    # app.add_middleware(
    #     ZeroTrustMiddleware,
    #     exempt_paths={"/health", "/metrics", "/docs", "/openapi.json", "/", "/api/v1/auth", "/api/v1/opportunities"},
    #     public_paths={"/", "/health", "/docs", "/openapi.json", "/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/opportunities"}
    # )
    
    # Add threat detection middleware
    app.add_middleware(
        ThreatDetectionMiddleware,
        max_request_size=10 * 1024 * 1024,  # 10MB
        blocked_user_agents={"sqlmap", "nmap", "nikto"},
        rate_limit_requests=100,
        rate_limit_window=60
    )
    
    # Add enhanced security headers middleware
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=not settings.DEBUG,  # Only enable HSTS in production
        enable_csp=True
    )
    
    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware)
    
    # Add event bus middleware
    app.add_middleware(EventBusMiddleware, 
                      enable_request_events=True, 
                      enable_health_events=True)
    app.add_middleware(EventContextMiddleware)
    
    # Add trusted host middleware for production
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )
    
    # Add request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Include routers
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(metrics.router, tags=["monitoring"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
    app.include_router(opportunities.router, prefix="/api/v1/opportunities", tags=["opportunities"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
    app.include_router(validations.router, prefix="/api/v1/validations", tags=["validations"])
    app.include_router(reputation.router, prefix="/api/v1/reputation", tags=["reputation"])
    app.include_router(moderation.router, prefix="/api/v1/moderation", tags=["moderation"])
    app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["recommendations"])
    app.include_router(discussions.router, prefix="/api/v1/discussions", tags=["discussions"])
    app.include_router(business_intelligence.router, prefix="/api/v1/business-intelligence", tags=["business intelligence"])
    app.include_router(timeline_estimation.router, prefix="/api/v1/timeline-estimation", tags=["timeline estimation"])
    app.include_router(user_matching.router, prefix="/api/v1/user-matching", tags=["user matching"])
    app.include_router(messaging.router, prefix="/api/v1", tags=["messaging"])
    app.include_router(events.router, prefix="/api/v1/events", tags=["events"])
    app.include_router(configuration.router, prefix="/api/v1/configuration", tags=["configuration"])
    app.include_router(feature_flags.router, prefix="/api/v1/feature-flags", tags=["feature flags"])
    app.include_router(security.router, prefix="/api/v1", tags=["security"])
    app.include_router(audit.router, prefix="/api/v1/audit", tags=["audit"])
    app.include_router(agents.router, prefix="/api/v1", tags=["agents"])
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Global exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    
    return app


# Create the application instance
app = create_application()


@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint providing API information."""
    return {
        "name": "AI Opportunity Browser API",
        "version": "1.0.0",
        "description": "API for discovering, validating, and browsing AI-solvable market opportunities",
        "status": "operational",
        "docs_url": "/docs" if settings.DEBUG else None,
        "health_check": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )