# AI Opportunity Browser Configuration Reference

This document describes all available configuration options.

## Application

### APP_NAME

- **Description**: Application name displayed in UI and logs
- **Type**: string
- **Default**: AI Opportunity Browser API
- **Required**: Yes

### VERSION

- **Description**: Application version
- **Type**: string
- **Default**: 1.0.0
- **Required**: Yes

### ENVIRONMENT

- **Description**: Deployment environment
- **Type**: string
- **Default**: development
- **Required**: Yes
- **Allowed Values**: development, staging, production, testing

### DEBUG

- **Description**: Enable debug mode with verbose logging
- **Type**: boolean
- **Default**: True
- **Required**: Yes

### HOST

- **Description**: Server host address
- **Type**: string
- **Default**: 0.0.0.0
- **Required**: Yes

### PORT

- **Description**: Server port number
- **Type**: integer
- **Default**: 8000
- **Required**: Yes
- **Minimum**: 1024
- **Maximum**: 65535

## Security

### SECRET_KEY

- **Description**: Secret key for JWT token signing and encryption
- **Type**: secret
- **Default**: your-secret-key-change-in-production
- **Required**: Yes
- **Sensitive**: Yes

### ALGORITHM

- **Description**: JWT signing algorithm
- **Type**: string
- **Default**: HS256
- **Required**: Yes
- **Allowed Values**: HS256, HS384, HS512, RS256, RS384, RS512

### ACCESS_TOKEN_EXPIRE_MINUTES

- **Description**: Access token expiration time in minutes
- **Type**: integer
- **Default**: 30
- **Required**: Yes
- **Minimum**: 5
- **Maximum**: 1440

### PASSWORD_MIN_LENGTH

- **Description**: Minimum password length requirement
- **Type**: integer
- **Default**: 8
- **Required**: No
- **Minimum**: 6
- **Maximum**: 128

### MAX_LOGIN_ATTEMPTS

- **Description**: Maximum login attempts before account lockout
- **Type**: integer
- **Default**: 5
- **Required**: No
- **Minimum**: 3
- **Maximum**: 10

### ACCOUNT_LOCKOUT_MINUTES

- **Description**: Account lockout duration in minutes
- **Type**: integer
- **Default**: 15
- **Required**: No
- **Minimum**: 5
- **Maximum**: 60

## Database

### DATABASE_URL

- **Description**: PostgreSQL database connection URL
- **Type**: string
- **Default**: postgresql://postgres:postgres@localhost:5432/ai_opportunity_browser
- **Required**: Yes
- **Sensitive**: Yes

### DATABASE_POOL_SIZE

- **Description**: Database connection pool size
- **Type**: integer
- **Default**: 10
- **Required**: No
- **Minimum**: 1
- **Maximum**: 50

### DATABASE_MAX_OVERFLOW

- **Description**: Maximum overflow connections beyond pool size
- **Type**: integer
- **Default**: 20
- **Required**: No
- **Minimum**: 0
- **Maximum**: 100

### DATABASE_POOL_TIMEOUT

- **Description**: Database connection timeout in seconds
- **Type**: integer
- **Default**: 30
- **Required**: No
- **Minimum**: 5
- **Maximum**: 300

### DATABASE_POOL_RECYCLE

- **Description**: Database connection recycle time in seconds
- **Type**: integer
- **Default**: 3600
- **Required**: No
- **Minimum**: 300
- **Maximum**: 86400

## Redis

### REDIS_URL

- **Description**: Redis connection URL for caching and sessions
- **Type**: string
- **Default**: redis://localhost:6379/0
- **Required**: Yes
- **Sensitive**: Yes

### REDIS_EXPIRE_SECONDS

- **Description**: Default Redis key expiration time in seconds
- **Type**: integer
- **Default**: 3600
- **Required**: No
- **Minimum**: 60
- **Maximum**: 86400

### REDIS_MAX_CONNECTIONS

- **Description**: Maximum Redis connection pool size
- **Type**: integer
- **Default**: 10
- **Required**: No
- **Minimum**: 1
- **Maximum**: 100

### REDIS_SOCKET_TIMEOUT

- **Description**: Redis socket timeout in seconds
- **Type**: integer
- **Default**: 5
- **Required**: No
- **Minimum**: 1
- **Maximum**: 30

## Vector Database

### PINECONE_API_KEY

- **Description**: Pinecone API key for vector database operations
- **Type**: secret
- **Default**: None
- **Required**: No
- **Sensitive**: Yes

### PINECONE_ENVIRONMENT

- **Description**: Pinecone environment region
- **Type**: string
- **Default**: us-west1-gcp
- **Required**: No
- **Allowed Values**: us-west1-gcp, us-east1-gcp, asia-northeast1-gcp, eu-west1-gcp

### PINECONE_INDEX_NAME

- **Description**: Pinecone index name for storing vectors
- **Type**: string
- **Default**: ai-opportunities
- **Required**: No

### VECTOR_DIMENSION

- **Description**: Vector embedding dimension size
- **Type**: integer
- **Default**: 1536
- **Required**: No
- **Allowed Values**: 384, 512, 768, 1024, 1536, 2048

### VECTOR_SIMILARITY_THRESHOLD

- **Description**: Minimum similarity threshold for vector matching
- **Type**: float
- **Default**: 0.7
- **Required**: No
- **Minimum**: 0.0
- **Maximum**: 1.0

## Rate Limiting

### RATE_LIMIT_REQUESTS

- **Description**: Maximum requests per time window
- **Type**: integer
- **Default**: 100
- **Required**: No
- **Minimum**: 10
- **Maximum**: 10000

### RATE_LIMIT_WINDOW

- **Description**: Rate limiting time window in seconds
- **Type**: integer
- **Default**: 60
- **Required**: No
- **Minimum**: 1
- **Maximum**: 3600

### RATE_LIMIT_BURST

- **Description**: Burst allowance for rate limiting
- **Type**: integer
- **Default**: 20
- **Required**: No
- **Minimum**: 1
- **Maximum**: 1000

### RATE_LIMIT_ENABLED

- **Description**: Enable or disable rate limiting
- **Type**: boolean
- **Default**: True
- **Required**: No

## External APIs

### PINECONE_API_KEY

- **Description**: Pinecone API key for vector database operations
- **Type**: secret
- **Default**: None
- **Required**: No
- **Sensitive**: Yes

### REDDIT_CLIENT_ID

- **Description**: Reddit API client ID for data ingestion
- **Type**: secret
- **Default**: None
- **Required**: No
- **Sensitive**: Yes

### REDDIT_CLIENT_SECRET

- **Description**: Reddit API client secret
- **Type**: secret
- **Default**: None
- **Required**: No
- **Sensitive**: Yes

### GITHUB_TOKEN

- **Description**: GitHub API personal access token
- **Type**: secret
- **Default**: None
- **Required**: No
- **Sensitive**: Yes

### OPENAI_API_KEY

- **Description**: OpenAI API key for AI model access
- **Type**: secret
- **Default**: None
- **Required**: No
- **Sensitive**: Yes

### ANTHROPIC_API_KEY

- **Description**: Anthropic API key for Claude model access
- **Type**: secret
- **Default**: None
- **Required**: No
- **Sensitive**: Yes

### GOOGLE_API_KEY

- **Description**: Google API key for Gemini model access
- **Type**: secret
- **Default**: None
- **Required**: No
- **Sensitive**: Yes

### COHERE_API_KEY

- **Description**: Cohere API key for model access
- **Type**: secret
- **Default**: None
- **Required**: No
- **Sensitive**: Yes

## AI/ML

### DEFAULT_AI_PROVIDER

- **Description**: Default AI provider for model operations
- **Type**: string
- **Default**: openai
- **Required**: No
- **Allowed Values**: openai, anthropic, google, cohere, local

### DEFAULT_EMBEDDING_MODEL

- **Description**: Default model for text embeddings
- **Type**: string
- **Default**: text-embedding-ada-002
- **Required**: No

### DEFAULT_CHAT_MODEL

- **Description**: Default model for chat completions
- **Type**: string
- **Default**: gpt-3.5-turbo
- **Required**: No

### MAX_TOKENS_PER_REQUEST

- **Description**: Maximum tokens per AI model request
- **Type**: integer
- **Default**: 4000
- **Required**: No
- **Minimum**: 100
- **Maximum**: 32000

### AI_REQUEST_TIMEOUT

- **Description**: AI model request timeout in seconds
- **Type**: integer
- **Default**: 30
- **Required**: No
- **Minimum**: 5
- **Maximum**: 300

### AI_MAX_RETRIES

- **Description**: Maximum retries for failed AI requests
- **Type**: integer
- **Default**: 3
- **Required**: No
- **Minimum**: 0
- **Maximum**: 10

## Event Bus

### EVENT_BUS_TYPE

- **Description**: Event bus implementation type
- **Type**: string
- **Default**: redis
- **Required**: No
- **Allowed Values**: redis, kafka, memory

### EVENT_TTL_SECONDS

- **Description**: Event time-to-live in seconds for replay capability
- **Type**: integer
- **Default**: 604800
- **Required**: No
- **Minimum**: 3600
- **Maximum**: 2592000

### EVENT_MAX_RETRIES

- **Description**: Maximum retries for failed event processing
- **Type**: integer
- **Default**: 3
- **Required**: No
- **Minimum**: 0
- **Maximum**: 10

## Agents

### AGENT_MAX_CONCURRENT

- **Description**: Maximum number of concurrent agents
- **Type**: integer
- **Default**: 10
- **Required**: No
- **Minimum**: 1
- **Maximum**: 100

### AGENT_TASK_TIMEOUT

- **Description**: Agent task timeout in seconds
- **Type**: integer
- **Default**: 300
- **Required**: No
- **Minimum**: 30
- **Maximum**: 3600

### AGENT_HEALTH_CHECK_INTERVAL

- **Description**: Agent health check interval in seconds
- **Type**: integer
- **Default**: 60
- **Required**: No
- **Minimum**: 10
- **Maximum**: 300

### AGENT_RESTART_DELAY

- **Description**: Delay before restarting failed agents in seconds
- **Type**: integer
- **Default**: 30
- **Required**: No
- **Minimum**: 5
- **Maximum**: 300

### AGENT_MAX_RESTARTS

- **Description**: Maximum agent restart attempts
- **Type**: integer
- **Default**: 3
- **Required**: No
- **Minimum**: 0
- **Maximum**: 10

## Data Ingestion

### INGESTION_BATCH_SIZE

- **Description**: Batch size for data ingestion processing
- **Type**: integer
- **Default**: 100
- **Required**: No
- **Minimum**: 10
- **Maximum**: 1000

### INGESTION_INTERVAL_MINUTES

- **Description**: Data ingestion interval in minutes
- **Type**: integer
- **Default**: 15
- **Required**: No
- **Minimum**: 1
- **Maximum**: 1440

### MAX_SIGNAL_AGE_HOURS

- **Description**: Maximum age of market signals to process in hours
- **Type**: integer
- **Default**: 24
- **Required**: No
- **Minimum**: 1
- **Maximum**: 168

### DUPLICATE_DETECTION_THRESHOLD

- **Description**: Similarity threshold for duplicate detection
- **Type**: float
- **Default**: 0.85
- **Required**: No
- **Minimum**: 0.5
- **Maximum**: 1.0

### QUALITY_SCORE_THRESHOLD

- **Description**: Minimum quality score for signal processing
- **Type**: float
- **Default**: 0.6
- **Required**: No
- **Minimum**: 0.0
- **Maximum**: 1.0

## Logging

### LOG_LEVEL

- **Description**: Application logging level
- **Type**: string
- **Default**: INFO
- **Required**: No
- **Allowed Values**: DEBUG, INFO, WARNING, ERROR, CRITICAL

### LOG_FORMAT

- **Description**: Log message format string
- **Type**: string
- **Default**: %(asctime)s - %(name)s - %(levelname)s - %(message)s
- **Required**: No

### LOG_FILE_PATH

- **Description**: Path to log file (optional)
- **Type**: string
- **Default**: None
- **Required**: No

### LOG_MAX_BYTES

- **Description**: Maximum log file size in bytes
- **Type**: integer
- **Default**: 10485760
- **Required**: No
- **Minimum**: 1048576
- **Maximum**: 104857600

### LOG_BACKUP_COUNT

- **Description**: Number of log file backups to keep
- **Type**: integer
- **Default**: 5
- **Required**: No
- **Minimum**: 1
- **Maximum**: 20

## CORS

### ALLOWED_ORIGINS

- **Description**: List of allowed CORS origins
- **Type**: list
- **Default**: ['http://localhost:3000', 'http://localhost:8080']
- **Required**: No

### ALLOWED_HOSTS

- **Description**: List of allowed host headers
- **Type**: list
- **Default**: ['localhost', '127.0.0.1']
- **Required**: No

### ALLOWED_METHODS

- **Description**: List of allowed HTTP methods
- **Type**: list
- **Default**: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
- **Required**: No

### ALLOWED_HEADERS

- **Description**: List of allowed HTTP headers
- **Type**: list
- **Default**: ['*']
- **Required**: No

### ALLOW_CREDENTIALS

- **Description**: Allow credentials in CORS requests
- **Type**: boolean
- **Default**: True
- **Required**: No

## Environment-Specific Overrides

### DEVELOPMENT

- **DEBUG**: True
- **LOG_LEVEL**: DEBUG
- **RATE_LIMIT_REQUESTS**: 1000
- **ENABLE_STRUCTURED_LOGGING**: False

### STAGING

- **DEBUG**: False
- **LOG_LEVEL**: INFO
- **RATE_LIMIT_REQUESTS**: 500
- **ENABLE_STRUCTURED_LOGGING**: True

### PRODUCTION

- **DEBUG**: False
- **LOG_LEVEL**: WARNING
- **RATE_LIMIT_REQUESTS**: 100
- **ENABLE_STRUCTURED_LOGGING**: True
- **AGENT_MAX_CONCURRENT**: 20
- **DATABASE_POOL_SIZE**: 20
- **REDIS_MAX_CONNECTIONS**: 20

### TESTING

- **DEBUG**: True
- **LOG_LEVEL**: DEBUG
- **RATE_LIMIT_ENABLED**: False
- **ENABLE_EVENT_HANDLERS**: False
- **DATABASE_POOL_SIZE**: 5

