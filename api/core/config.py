"""
Configuration management for the AI Opportunity Browser API.

This module handles all configuration settings using Pydantic Settings
for type validation and environment variable management.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    APP_NAME: str = "AI Opportunity Browser API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    
    # Security settings
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", description="Secret key for JWT tokens")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiration in minutes")
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="Allowed hosts for production"
    )
    
    # Database settings
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/ai_opportunity_browser",
        description="PostgreSQL database URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, description="Database max overflow connections")
    
    # Redis settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis cache URL"
    )
    REDIS_EXPIRE_SECONDS: int = Field(default=3600, description="Default Redis expiration time")
    
    # Vector database settings
    PINECONE_API_KEY: Optional[str] = Field(default=None, description="Pinecone API key")
    PINECONE_ENVIRONMENT: str = Field(default="us-west1-gcp", description="Pinecone environment")
    PINECONE_INDEX_NAME: str = Field(default="ai-opportunities", description="Pinecone index name")
    
    # Rate limiting settings
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Rate limit requests per minute")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="Rate limit window in seconds")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    ENABLE_STRUCTURED_LOGGING: bool = Field(default=True, description="Enable structured JSON logging")
    
    # Tracing settings
    ENABLE_TRACING: bool = Field(default=True, description="Enable distributed tracing")
    ENABLE_CONSOLE_TRACING: bool = Field(default=False, description="Enable console trace output")
    JAEGER_ENDPOINT: Optional[str] = Field(default=None, description="Jaeger collector endpoint")
    JAEGER_AGENT_HOST: str = Field(default="localhost", description="Jaeger agent host")
    JAEGER_AGENT_PORT: int = Field(default=6831, description="Jaeger agent port")
    OTLP_ENDPOINT: Optional[str] = Field(default=None, description="OTLP endpoint for trace export")
    OTLP_API_KEY: Optional[str] = Field(default=None, description="OTLP API key for authentication")
    
    # External API settings
    REDDIT_CLIENT_ID: Optional[str] = Field(default=None, description="Reddit API client ID")
    REDDIT_CLIENT_SECRET: Optional[str] = Field(default=None, description="Reddit API client secret")
    GITHUB_TOKEN: Optional[str] = Field(default=None, description="GitHub API token")
    
    # AI/ML settings
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key")
    
    # External API tokens
    GITHUB_ACCESS_TOKEN: Optional[str] = Field(default=None, description="GitHub access token")
    PRODUCTHUNT_ACCESS_TOKEN: Optional[str] = Field(default=None, description="ProductHunt access token")
    
    # Security settings
    ENABLE_ZERO_TRUST: bool = Field(default=True, description="Enable zero trust security architecture")
    ENABLE_THREAT_DETECTION: bool = Field(default=True, description="Enable threat detection middleware")
    MAX_REQUEST_SIZE: int = Field(default=10 * 1024 * 1024, description="Maximum request size in bytes")
    BRUTE_FORCE_THRESHOLD: int = Field(default=5, description="Failed login attempts before blocking")
    BRUTE_FORCE_WINDOW: int = Field(default=300, description="Brute force detection window in seconds")
    
    # Service authentication secrets (should be set via environment variables)
    API_SERVICE_SECRET: Optional[str] = Field(default=None, description="API service secret")
    DATA_INGESTION_SECRET: Optional[str] = Field(default=None, description="Data ingestion service secret")
    AGENT_ORCHESTRATOR_SECRET: Optional[str] = Field(default=None, description="Agent orchestrator secret")
    MONITORING_SERVICE_SECRET: Optional[str] = Field(default=None, description="Monitoring service secret")
    VALIDATION_SERVICE_SECRET: Optional[str] = Field(default=None, description="Validation service secret")
    ANALYTICS_SERVICE_SECRET: Optional[str] = Field(default=None, description="Analytics service secret")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql://", 1)
    
    @property
    def database_url_async(self) -> str:
        """Get asynchronous database URL."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()