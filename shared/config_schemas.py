"""
Configuration Schemas for AI Opportunity Browser

This module defines configuration schemas with validation rules and metadata
for all configuration keys used throughout the application.
"""

from typing import List, Dict, Any
from .config_service import ConfigMetadata, ConfigType, ConfigScope


# Application Configuration Schema
APPLICATION_CONFIG_SCHEMA: Dict[str, ConfigMetadata] = {
    "APP_NAME": ConfigMetadata(
        description="Application name displayed in UI and logs",
        config_type=ConfigType.STRING,
        default_value="AI Opportunity Browser API",
        required=True
    ),
    "VERSION": ConfigMetadata(
        description="Application version",
        config_type=ConfigType.STRING,
        default_value="1.0.0",
        required=True
    ),
    "ENVIRONMENT": ConfigMetadata(
        description="Deployment environment",
        config_type=ConfigType.STRING,
        default_value="development",
        required=True,
        allowed_values=["development", "staging", "production", "testing"]
    ),
    "DEBUG": ConfigMetadata(
        description="Enable debug mode with verbose logging",
        config_type=ConfigType.BOOLEAN,
        default_value=True,
        required=True
    ),
    "HOST": ConfigMetadata(
        description="Server host address",
        config_type=ConfigType.STRING,
        default_value="0.0.0.0",
        required=True
    ),
    "PORT": ConfigMetadata(
        description="Server port number",
        config_type=ConfigType.INTEGER,
        default_value=8000,
        required=True,
        min_value=1024,
        max_value=65535
    )
}

# Security Configuration Schema
SECURITY_CONFIG_SCHEMA: Dict[str, ConfigMetadata] = {
    "SECRET_KEY": ConfigMetadata(
        description="Secret key for JWT token signing and encryption",
        config_type=ConfigType.SECRET,
        default_value="your-secret-key-change-in-production",
        required=True,
        sensitive=True
    ),
    "ALGORITHM": ConfigMetadata(
        description="JWT signing algorithm",
        config_type=ConfigType.STRING,
        default_value="HS256",
        required=True,
        allowed_values=["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
    ),
    "ACCESS_TOKEN_EXPIRE_MINUTES": ConfigMetadata(
        description="Access token expiration time in minutes",
        config_type=ConfigType.INTEGER,
        default_value=30,
        required=True,
        min_value=5,
        max_value=1440  # 24 hours
    ),
    "REFRESH_TOKEN_EXPIRE_DAYS": ConfigMetadata(
        description="Refresh token expiration time in days",
        config_type=ConfigType.INTEGER,
        default_value=7,
        required=False,
        min_value=1,
        max_value=30
    ),
    "PASSWORD_MIN_LENGTH": ConfigMetadata(
        description="Minimum password length requirement",
        config_type=ConfigType.INTEGER,
        default_value=8,
        required=False,
        min_value=6,
        max_value=128
    ),
    "MAX_LOGIN_ATTEMPTS": ConfigMetadata(
        description="Maximum login attempts before account lockout",
        config_type=ConfigType.INTEGER,
        default_value=5,
        required=False,
        min_value=3,
        max_value=10
    ),
    "ACCOUNT_LOCKOUT_MINUTES": ConfigMetadata(
        description="Account lockout duration in minutes",
        config_type=ConfigType.INTEGER,
        default_value=15,
        required=False,
        min_value=5,
        max_value=60
    )
}

# Database Configuration Schema
DATABASE_CONFIG_SCHEMA: Dict[str, ConfigMetadata] = {
    "DATABASE_URL": ConfigMetadata(
        description="PostgreSQL database connection URL",
        config_type=ConfigType.STRING,
        default_value="postgresql://postgres:postgres@localhost:5432/ai_opportunity_browser",
        required=True,
        sensitive=True
    ),
    "DATABASE_POOL_SIZE": ConfigMetadata(
        description="Database connection pool size",
        config_type=ConfigType.INTEGER,
        default_value=10,
        required=False,
        min_value=1,
        max_value=50
    ),
    "DATABASE_MAX_OVERFLOW": ConfigMetadata(
        description="Maximum overflow connections beyond pool size",
        config_type=ConfigType.INTEGER,
        default_value=20,
        required=False,
        min_value=0,
        max_value=100
    ),
    "DATABASE_POOL_TIMEOUT": ConfigMetadata(
        description="Database connection timeout in seconds",
        config_type=ConfigType.INTEGER,
        default_value=30,
        required=False,
        min_value=5,
        max_value=300
    ),
    "DATABASE_POOL_RECYCLE": ConfigMetadata(
        description="Database connection recycle time in seconds",
        config_type=ConfigType.INTEGER,
        default_value=3600,
        required=False,
        min_value=300,
        max_value=86400
    )
}

# Redis Configuration Schema
REDIS_CONFIG_SCHEMA: Dict[str, ConfigMetadata] = {
    "REDIS_URL": ConfigMetadata(
        description="Redis connection URL for caching and sessions",
        config_type=ConfigType.STRING,
        default_value="redis://localhost:6379/0",
        required=True,
        sensitive=True
    ),
    "REDIS_EXPIRE_SECONDS": ConfigMetadata(
        description="Default Redis key expiration time in seconds",
        config_type=ConfigType.INTEGER,
        default_value=3600,
        required=False,
        min_value=60,
        max_value=86400
    ),
    "REDIS_MAX_CONNECTIONS": ConfigMetadata(
        description="Maximum Redis connection pool size",
        config_type=ConfigType.INTEGER,
        default_value=10,
        required=False,
        min_value=1,
        max_value=100
    ),
    "REDIS_SOCKET_TIMEOUT": ConfigMetadata(
        description="Redis socket timeout in seconds",
        config_type=ConfigType.INTEGER,
        default_value=5,
        required=False,
        min_value=1,
        max_value=30
    )
}

# Vector Database Configuration Schema
VECTOR_DB_CONFIG_SCHEMA: Dict[str, ConfigMetadata] = {
    "PINECONE_API_KEY": ConfigMetadata(
        description="Pinecone API key for vector database operations",
        config_type=ConfigType.SECRET,
        default_value=None,
        required=False,
        sensitive=True
    ),
    "PINECONE_ENVIRONMENT": ConfigMetadata(
        description="Pinecone environment region",
        config_type=ConfigType.STRING,
        default_value="us-west1-gcp",
        required=False,
        allowed_values=["us-west1-gcp", "us-east1-gcp", "asia-northeast1-gcp", "eu-west1-gcp"]
    ),
    "PINECONE_INDEX_NAME": ConfigMetadata(
        description="Pinecone index name for storing vectors",
        config_type=ConfigType.STRING,
        default_value="ai-opportunities",
        required=False
    ),
    "VECTOR_DIMENSION": ConfigMetadata(
        description="Vector embedding dimension size",
        config_type=ConfigType.INTEGER,
        default_value=1536,
        required=False,
        allowed_values=[384, 512, 768, 1024, 1536, 2048]
    ),
    "VECTOR_SIMILARITY_THRESHOLD": ConfigMetadata(
        description="Minimum similarity threshold for vector matching",
        config_type=ConfigType.FLOAT,
        default_value=0.7,
        required=False,
        min_value=0.0,
        max_value=1.0
    )
}

# Rate Limiting Configuration Schema
RATE_LIMITING_CONFIG_SCHEMA: Dict[str, ConfigMetadata] = {
    "RATE_LIMIT_REQUESTS": ConfigMetadata(
        description="Maximum requests per time window",
        config_type=ConfigType.INTEGER,
        default_value=100,
        required=False,
        min_value=10,
        max_value=10000
    ),
    "RATE_LIMIT_WINDOW": ConfigMetadata(
        description="Rate limiting time window in seconds",
        config_type=ConfigType.INTEGER,
        default_value=60,
        required=False,
        min_value=1,
        max_value=3600
    ),
    "RATE_LIMIT_BURST": ConfigMetadata(
        description="Burst allowance for rate limiting",
        config_type=ConfigType.INTEGER,
        default_value=20,
        required=False,
        min_value=1,
        max_value=1000
    ),
    "RATE_LIMIT_ENABLED": ConfigMetadata(
        description="Enable or disable rate limiting",
        config_type=ConfigType.BOOLEAN,
        default_value=True,
        required=False
    )
}

# External API Configuration Schema
EXTERNAL_API_CONFIG_SCHEMA: Dict[str, ConfigMetadata] = {
    "REDDIT_CLIENT_ID": ConfigMetadata(
        description="Reddit API client ID for data ingestion",
        config_type=ConfigType.SECRET,
        default_value=None,
        required=False,
        sensitive=True
    ),
    "REDDIT_CLIENT_SECRET": ConfigMetadata(
        description="Reddit API client secret",
        config_type=ConfigType.SECRET,
        default_value=None,
        required=False,
        sensitive=True
    ),
    "GITHUB_TOKEN": ConfigMetadata(
        description="GitHub API personal access token",
        config_type=ConfigType.SECRET,
        default_value=None,
        required=False,
        sensitive=True
    ),
    "OPENAI_API_KEY": ConfigMetadata(
        description="OpenAI API key for AI model access",
        config_type=ConfigType.SECRET,
        default_value=None,
        required=False,
        sensitive=True
    ),
    "ANTHROPIC_API_KEY": ConfigMetadata(
        description="Anthropic API key for Claude model access",
        config_type=ConfigType.SECRET,
        default_value=None,
        required=False,
        sensitive=True
    ),
    "GOOGLE_API_KEY": ConfigMetadata(
        description="Google API key for Gemini model access",
        config_type=ConfigType.SECRET,
        default_value=None,
        required=False,
        sensitive=True
    ),
    "COHERE_API_KEY": ConfigMetadata(
        description="Cohere API key for model access",
        config_type=ConfigType.SECRET,
        default_value=None,
        required=False,
        sensitive=True
    )
}

# AI/ML Configuration Schema
AI_ML_CONFIG_SCHEMA: Dict[str, ConfigMetadata] = {
    "DEFAULT_AI_PROVIDER": ConfigMetadata(
        description="Default AI provider for model operations",
        config_type=ConfigType.STRING,
        default_value="openai",
        required=False,
        allowed_values=["openai", "anthropic", "google", "cohere", "local"]
    ),
    "DEFAULT_EMBEDDING_MODEL": ConfigMetadata(
        description="Default model for text embeddings",
        config_type=ConfigType.STRING,
        default_value="text-embedding-ada-002",
        required=False
    ),
    "DEFAULT_CHAT_MODEL": ConfigMetadata(
        description="Default model for chat completions",
        config_type=ConfigType.STRING,
        default_value="gpt-3.5-turbo",
        required=False
    ),
    "MAX_TOKENS_PER_REQUEST": ConfigMetadata(
        description="Maximum tokens per AI model request",
        config_type=ConfigType.INTEGER,
        default_value=4000,
        required=False,
        min_value=100,
        max_value=32000
    ),
    "AI_REQUEST_TIMEOUT": ConfigMetadata(
        description="AI model request timeout in seconds",
        config_type=ConfigType.INTEGER,
        default_value=30,
        required=False,
        min_value=5,
        max_value=300
    ),
    "AI_MAX_RETRIES": ConfigMetadata(
        description="Maximum retries for failed AI requests",
        config_type=ConfigType.INTEGER,
        default_value=3,
        required=False,
        min_value=0,
        max_value=10
    )
}

# Event Bus Configuration Schema
EVENT_BUS_CONFIG_SCHEMA: Dict[str, ConfigMetadata] = {
    "EVENT_BUS_TYPE": ConfigMetadata(
        description="Event bus implementation type",
        config_type=ConfigType.STRING,
        default_value="redis",
        required=False,
        allowed_values=["redis", "kafka", "memory"]
    ),
    "ENABLE_EVENT_HANDLERS": ConfigMetadata(
        description="Enable automatic event handler registration",
        config_type=ConfigType.BOOLEAN,
        default_value=True,
        required=False
    ),
    "ENABLED_EVENT_HANDLERS": ConfigMetadata(
        description="Comma-separated list of enabled event handlers",
        config_type=ConfigType.LIST,
        default_value=["all"],
        required=False
    ),
    "EVENT_TTL_SECONDS": ConfigMetadata(
        description="Event time-to-live in seconds for replay capability",
        config_type=ConfigType.INTEGER,
        default_value=604800,  # 7 days
        required=False,
        min_value=3600,
        max_value=2592000  # 30 days
    ),
    "EVENT_MAX_RETRIES": ConfigMetadata(
        description="Maximum retries for failed event processing",
        config_type=ConfigType.INTEGER,
        default_value=3,
        required=False,
        min_value=0,
        max_value=10
    ),
    "ENABLE_EVENT_SOURCING": ConfigMetadata(
        description="Enable event sourcing for audit trails",
        config_type=ConfigType.BOOLEAN,
        default_value=True,
        required=False
    ),
    "ENABLE_EVENT_REPLAY": ConfigMetadata(
        description="Enable event replay capabilities",
        config_type=ConfigType.BOOLEAN,
        default_value=True,
        required=False
    )
}

# Agent Configuration Schema
AGENT_CONFIG_SCHEMA: Dict[str, ConfigMetadata] = {
    "AGENT_MAX_CONCURRENT": ConfigMetadata(
        description="Maximum number of concurrent agents",
        config_type=ConfigType.INTEGER,
        default_value=10,
        required=False,
        min_value=1,
        max_value=100
    ),
    "AGENT_TASK_TIMEOUT": ConfigMetadata(
        description="Agent task timeout in seconds",
        config_type=ConfigType.INTEGER,
        default_value=300,
        required=False,
        min_value=30,
        max_value=3600
    ),
    "AGENT_HEALTH_CHECK_INTERVAL": ConfigMetadata(
        description="Agent health check interval in seconds",
        config_type=ConfigType.INTEGER,
        default_value=60,
        required=False,
        min_value=10,
        max_value=300
    ),
    "AGENT_RESTART_DELAY": ConfigMetadata(
        description="Delay before restarting failed agents in seconds",
        config_type=ConfigType.INTEGER,
        default_value=30,
        required=False,
        min_value=5,
        max_value=300
    ),
    "AGENT_MAX_RESTARTS": ConfigMetadata(
        description="Maximum agent restart attempts",
        config_type=ConfigType.INTEGER,
        default_value=3,
        required=False,
        min_value=0,
        max_value=10
    )
}

# Data Ingestion Configuration Schema
DATA_INGESTION_CONFIG_SCHEMA: Dict[str, ConfigMetadata] = {
    "INGESTION_BATCH_SIZE": ConfigMetadata(
        description="Batch size for data ingestion processing",
        config_type=ConfigType.INTEGER,
        default_value=100,
        required=False,
        min_value=10,
        max_value=1000
    ),
    "INGESTION_INTERVAL_MINUTES": ConfigMetadata(
        description="Data ingestion interval in minutes",
        config_type=ConfigType.INTEGER,
        default_value=15,
        required=False,
        min_value=1,
        max_value=1440
    ),
    "MAX_SIGNAL_AGE_HOURS": ConfigMetadata(
        description="Maximum age of market signals to process in hours",
        config_type=ConfigType.INTEGER,
        default_value=24,
        required=False,
        min_value=1,
        max_value=168  # 7 days
    ),
    "DUPLICATE_DETECTION_THRESHOLD": ConfigMetadata(
        description="Similarity threshold for duplicate detection",
        config_type=ConfigType.FLOAT,
        default_value=0.85,
        required=False,
        min_value=0.5,
        max_value=1.0
    ),
    "QUALITY_SCORE_THRESHOLD": ConfigMetadata(
        description="Minimum quality score for signal processing",
        config_type=ConfigType.FLOAT,
        default_value=0.6,
        required=False,
        min_value=0.0,
        max_value=1.0
    )
}

# Logging Configuration Schema
LOGGING_CONFIG_SCHEMA: Dict[str, ConfigMetadata] = {
    "LOG_LEVEL": ConfigMetadata(
        description="Application logging level",
        config_type=ConfigType.STRING,
        default_value="INFO",
        required=False,
        allowed_values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    ),
    "LOG_FORMAT": ConfigMetadata(
        description="Log message format string",
        config_type=ConfigType.STRING,
        default_value="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        required=False
    ),
    "LOG_FILE_PATH": ConfigMetadata(
        description="Path to log file (optional)",
        config_type=ConfigType.STRING,
        default_value=None,
        required=False
    ),
    "LOG_MAX_BYTES": ConfigMetadata(
        description="Maximum log file size in bytes",
        config_type=ConfigType.INTEGER,
        default_value=10485760,  # 10MB
        required=False,
        min_value=1048576,  # 1MB
        max_value=104857600  # 100MB
    ),
    "LOG_BACKUP_COUNT": ConfigMetadata(
        description="Number of log file backups to keep",
        config_type=ConfigType.INTEGER,
        default_value=5,
        required=False,
        min_value=1,
        max_value=20
    ),
    "ENABLE_STRUCTURED_LOGGING": ConfigMetadata(
        description="Enable structured JSON logging",
        config_type=ConfigType.BOOLEAN,
        default_value=False,
        required=False
    )
}

# CORS Configuration Schema
CORS_CONFIG_SCHEMA: Dict[str, ConfigMetadata] = {
    "ALLOWED_ORIGINS": ConfigMetadata(
        description="List of allowed CORS origins",
        config_type=ConfigType.LIST,
        default_value=["http://localhost:3000", "http://localhost:8080"],
        required=False
    ),
    "ALLOWED_HOSTS": ConfigMetadata(
        description="List of allowed host headers",
        config_type=ConfigType.LIST,
        default_value=["localhost", "127.0.0.1"],
        required=False
    ),
    "ALLOWED_METHODS": ConfigMetadata(
        description="List of allowed HTTP methods",
        config_type=ConfigType.LIST,
        default_value=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        required=False
    ),
    "ALLOWED_HEADERS": ConfigMetadata(
        description="List of allowed HTTP headers",
        config_type=ConfigType.LIST,
        default_value=["*"],
        required=False
    ),
    "ALLOW_CREDENTIALS": ConfigMetadata(
        description="Allow credentials in CORS requests",
        config_type=ConfigType.BOOLEAN,
        default_value=True,
        required=False
    )
}

# Combine all schemas
ALL_CONFIG_SCHEMAS: Dict[str, ConfigMetadata] = {
    **APPLICATION_CONFIG_SCHEMA,
    **SECURITY_CONFIG_SCHEMA,
    **DATABASE_CONFIG_SCHEMA,
    **REDIS_CONFIG_SCHEMA,
    **VECTOR_DB_CONFIG_SCHEMA,
    **RATE_LIMITING_CONFIG_SCHEMA,
    **EXTERNAL_API_CONFIG_SCHEMA,
    **AI_ML_CONFIG_SCHEMA,
    **EVENT_BUS_CONFIG_SCHEMA,
    **AGENT_CONFIG_SCHEMA,
    **DATA_INGESTION_CONFIG_SCHEMA,
    **LOGGING_CONFIG_SCHEMA,
    **CORS_CONFIG_SCHEMA
}

# Environment-specific configuration overrides
ENVIRONMENT_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "development": {
        "DEBUG": True,
        "LOG_LEVEL": "DEBUG",
        "RATE_LIMIT_REQUESTS": 1000,
        "ENABLE_STRUCTURED_LOGGING": False
    },
    "staging": {
        "DEBUG": False,
        "LOG_LEVEL": "INFO",
        "RATE_LIMIT_REQUESTS": 500,
        "ENABLE_STRUCTURED_LOGGING": True
    },
    "production": {
        "DEBUG": False,
        "LOG_LEVEL": "WARNING",
        "RATE_LIMIT_REQUESTS": 100,
        "ENABLE_STRUCTURED_LOGGING": True,
        "AGENT_MAX_CONCURRENT": 20,
        "DATABASE_POOL_SIZE": 20,
        "REDIS_MAX_CONNECTIONS": 20
    },
    "testing": {
        "DEBUG": True,
        "LOG_LEVEL": "DEBUG",
        "RATE_LIMIT_ENABLED": False,
        "ENABLE_EVENT_HANDLERS": False,
        "DATABASE_POOL_SIZE": 5
    }
}


def get_schema_by_category(category: str) -> Dict[str, ConfigMetadata]:
    """Get configuration schema by category."""
    schemas = {
        "application": APPLICATION_CONFIG_SCHEMA,
        "security": SECURITY_CONFIG_SCHEMA,
        "database": DATABASE_CONFIG_SCHEMA,
        "redis": REDIS_CONFIG_SCHEMA,
        "vector_db": VECTOR_DB_CONFIG_SCHEMA,
        "rate_limiting": RATE_LIMITING_CONFIG_SCHEMA,
        "external_api": EXTERNAL_API_CONFIG_SCHEMA,
        "ai_ml": AI_ML_CONFIG_SCHEMA,
        "event_bus": EVENT_BUS_CONFIG_SCHEMA,
        "agent": AGENT_CONFIG_SCHEMA,
        "data_ingestion": DATA_INGESTION_CONFIG_SCHEMA,
        "logging": LOGGING_CONFIG_SCHEMA,
        "cors": CORS_CONFIG_SCHEMA
    }
    
    return schemas.get(category, {})


def get_environment_overrides(environment: str) -> Dict[str, Any]:
    """Get configuration overrides for a specific environment."""
    return ENVIRONMENT_OVERRIDES.get(environment, {})


def get_required_configs() -> List[str]:
    """Get list of required configuration keys."""
    return [
        key for key, metadata in ALL_CONFIG_SCHEMAS.items()
        if metadata.required
    ]


def get_sensitive_configs() -> List[str]:
    """Get list of sensitive configuration keys."""
    return [
        key for key, metadata in ALL_CONFIG_SCHEMAS.items()
        if metadata.sensitive
    ]