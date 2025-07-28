# Technology Stack & Build System

## Core Tech Stack
- **Backend Framework**: FastAPI with Python 3.11+
- **Databases**: PostgreSQL (primary), Redis (cache), Pinecone (vector DB)
- **AI/ML**: LangChain, multiple LLM providers, Transformers, sentence-transformers
- **Task Queue**: Celery for background processing
- **Containerization**: Docker & Docker Compose
- **Testing**: pytest with pytest-asyncio for async testing

## AI Provider Support
- OpenAI (GPT models)
- Anthropic (Claude)
- Google (Gemini)
- Cohere
- Together AI
- Local/Open Source models via Transformers

## Key Libraries & Frameworks
- **Web Framework**: FastAPI, Uvicorn, Pydantic for data validation
- **Database**: SQLAlchemy (async/sync), Alembic for migrations
- **Authentication**: python-jose, passlib with bcrypt
- **Data Processing**: pandas, numpy, scikit-learn, beautifulsoup4
- **External APIs**: praw (Reddit), aiohttp, requests
- **Development**: black (formatting), flake8 (linting), mypy (type checking)

## Common Commands

### Development Environment
```bash
# Start development environment
make dev-up          # Start databases (PostgreSQL, Redis)
make dev-api         # Start API server
make dev-down        # Stop all services

# Alternative manual setup
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
docker-compose up -d postgres redis
uvicorn api.main:app --reload
```

### Testing & Quality
```bash
make test           # Run all tests
pytest --cov=.     # Run with coverage
make lint          # Run flake8 linting
make format        # Format code with black
mypy .             # Type checking
```

### Database Operations
```bash
# Database migrations
alembic revision --autogenerate -m "Description"
alembic upgrade head
alembic downgrade -1
```

## Environment Configuration
- Copy `.env.example` to `.env` and configure:
  - Database URLs (PostgreSQL, Redis)
  - AI provider API keys
  - Security settings (SECRET_KEY, JWT settings)
  - CORS and rate limiting settings

## Architecture Patterns
- **Async-first**: All database operations and external API calls use async/await
- **Dependency Injection**: FastAPI's dependency system for database sessions, auth
- **Agent-based Architecture**: Specialized AI agents inherit from BaseAgent class
- **Plugin System**: Data ingestion uses plugin architecture for extensibility
- **Multi-provider AI**: Abstracted AI provider interface supporting multiple LLM services