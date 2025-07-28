# Contributing to AI Opportunity Browser

Thank you for your interest in contributing to the AI Opportunity Browser! This document provides guidelines and standards for development.

## 🎯 Development Philosophy

- **AI-First**: Every feature should leverage AI capabilities effectively
- **Modular Design**: Components should be loosely coupled and highly cohesive
- **Test-Driven**: Write tests before implementing features
- **Documentation**: Code should be self-documenting with clear docstrings
- **Performance**: Optimize for scalability and real-time processing

## 📋 Before You Start

1. Read the [README.md](README.md) for setup instructions
2. Review the [design document](.kiro/specs/ai-opportunity-browser/design.md)
3. Check existing [issues](https://github.com/your-repo/issues) and [pull requests](https://github.com/your-repo/pulls)
4. Set up your development environment

## 🔧 Development Setup

### Environment Setup

```bash
# Clone and setup
git clone <repository-url>
cd ai-opportunity-browser
cp .env.example .env

# Install pre-commit hooks
pre-commit install

# Start development environment
make dev-up
```

### Code Quality Tools

We use several tools to maintain code quality:

- **Black**: Code formatting
- **Flake8**: Linting
- **MyPy**: Type checking
- **pytest**: Testing
- **pre-commit**: Git hooks

## 📝 Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with these specific guidelines:

#### Code Formatting

```python
# Use Black for automatic formatting
# Line length: 88 characters (Black default)
# Use double quotes for strings
# Use trailing commas in multi-line structures

# Good
def process_opportunity(
    opportunity: Opportunity,
    validation_score: float,
    metadata: Dict[str, Any],
) -> ProcessedOpportunity:
    """Process an opportunity with validation."""
    pass

# Bad
def process_opportunity(opportunity: Opportunity, validation_score: float, metadata: Dict[str, Any]) -> ProcessedOpportunity:
    pass
```

#### Type Hints

Always use type hints for function parameters and return values:

```python
from typing import List, Dict, Optional, Union
from datetime import datetime

def analyze_market_signals(
    signals: List[MarketSignal],
    timeframe: Optional[datetime] = None,
) -> Dict[str, Union[float, int]]:
    """Analyze market signals and return metrics."""
    pass
```

#### Docstrings

Use Google-style docstrings:

```python
def validate_opportunity(opportunity: Opportunity, user: User) -> ValidationResult:
    """Validate an opportunity using community input.
    
    Args:
        opportunity: The opportunity to validate
        user: The user performing validation
        
    Returns:
        ValidationResult containing score and feedback
        
    Raises:
        ValidationError: If validation fails
        PermissionError: If user lacks validation permissions
    """
    pass
```

#### Error Handling

Use specific exception types and proper error handling:

```python
# Good
try:
    result = await api_client.fetch_data()
except APIRateLimitError:
    logger.warning("Rate limit exceeded, retrying in 60s")
    await asyncio.sleep(60)
    result = await api_client.fetch_data()
except APIConnectionError as e:
    logger.error(f"Connection failed: {e}")
    raise ServiceUnavailableError("External API unavailable")

# Bad
try:
    result = await api_client.fetch_data()
except Exception as e:
    print(f"Error: {e}")
    return None
```

### Async/Await Guidelines

- Use `async`/`await` for I/O operations
- Don't use `async` for CPU-bound operations
- Use `asyncio.gather()` for concurrent operations
- Handle async context managers properly

```python
# Good
async def process_multiple_sources(sources: List[str]) -> List[Data]:
    """Process multiple data sources concurrently."""
    tasks = [fetch_source_data(source) for source in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]

# Bad
async def process_multiple_sources(sources: List[str]) -> List[Data]:
    results = []
    for source in sources:
        result = await fetch_source_data(source)  # Sequential, not concurrent
        results.append(result)
    return results
```

## 🏗️ Architecture Guidelines

### Service Layer Pattern

Organize code into clear layers:

```
api/
├── routers/          # FastAPI route handlers
├── services/         # Business logic
├── models/           # Database models
├── schemas/          # Pydantic schemas
└── dependencies/     # Dependency injection
```

### Dependency Injection

Use FastAPI's dependency injection system:

```python
from fastapi import Depends
from api.dependencies import get_db, get_current_user

@router.post("/opportunities/")
async def create_opportunity(
    opportunity_data: OpportunityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Opportunity:
    """Create a new opportunity."""
    return await opportunity_service.create(db, opportunity_data, current_user)
```

### Plugin Architecture

When creating new plugins, follow the established pattern:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any

class DataSourcePlugin(ABC):
    """Base class for data source plugins."""
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the plugin with configuration."""
        pass
    
    @abstractmethod
    async def fetch_data(self, params: Dict[str, Any]) -> List[RawData]:
        """Fetch data from the source."""
        pass
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass
```

## 🧪 Testing Guidelines

### Test Structure

Organize tests to mirror the source code structure:

```
tests/
├── unit/             # Unit tests
├── integration/      # Integration tests
├── e2e/             # End-to-end tests
├── fixtures/        # Test fixtures
└── conftest.py      # pytest configuration
```

### Writing Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from api.services.opportunity_service import OpportunityService

class TestOpportunityService:
    """Test suite for OpportunityService."""
    
    @pytest.fixture
    async def opportunity_service(self):
        """Create opportunity service instance."""
        return OpportunityService()
    
    @pytest.mark.asyncio
    async def test_create_opportunity_success(
        self, 
        opportunity_service: OpportunityService,
        mock_db_session: AsyncMock,
    ):
        """Test successful opportunity creation."""
        # Arrange
        opportunity_data = OpportunityCreate(title="Test", description="Test desc")
        
        # Act
        result = await opportunity_service.create(mock_db_session, opportunity_data)
        
        # Assert
        assert result.title == "Test"
        assert result.description == "Test desc"
```

### Test Coverage

- Aim for 80%+ test coverage
- Focus on critical business logic
- Test error conditions and edge cases
- Use mocks for external dependencies

## 🔄 Git Workflow

### Branch Naming

- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `hotfix/description` - Critical fixes
- `refactor/description` - Code refactoring

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add Reddit data source plugin
fix: resolve rate limiting in GitHub API client
docs: update API documentation for validation endpoints
test: add unit tests for opportunity scoring
refactor: extract common database utilities
```

### Pull Request Process

1. Create feature branch from `main`
2. Implement changes with tests
3. Ensure all checks pass (tests, linting, type checking)
4. Update documentation if needed
5. Create pull request with clear description
6. Address review feedback
7. Squash and merge when approved

## 📊 Performance Guidelines

### Database Queries

- Use async database operations
- Implement proper indexing
- Use pagination for large datasets
- Avoid N+1 query problems

```python
# Good - Single query with join
opportunities = await db.execute(
    select(Opportunity)
    .options(selectinload(Opportunity.market_signals))
    .where(Opportunity.user_id == user_id)
)

# Bad - N+1 queries
opportunities = await db.execute(select(Opportunity))
for opp in opportunities:
    signals = await db.execute(
        select(MarketSignal).where(MarketSignal.opportunity_id == opp.id)
    )
```

### Caching Strategy

- Cache expensive computations
- Use Redis for session and temporary data
- Implement cache invalidation properly

```python
from api.cache import cache_manager

@cache_manager.cached(expire=3600)  # 1 hour cache
async def get_market_analysis(opportunity_id: str) -> MarketAnalysis:
    """Get cached market analysis."""
    return await expensive_analysis_operation(opportunity_id)
```

### AI Model Usage

- Implement request batching where possible
- Use appropriate model sizes for tasks
- Implement fallback mechanisms
- Monitor token usage and costs

## 🚀 Deployment Guidelines

### Environment Configuration

- Use environment variables for configuration
- Never commit secrets to version control
- Use different configurations for dev/staging/prod
- Document all required environment variables

### Docker Best Practices

- Use multi-stage builds for production
- Minimize image size
- Use non-root users
- Implement health checks

## 📚 Documentation

### API Documentation

- Use FastAPI's automatic documentation
- Add detailed descriptions to endpoints
- Include example requests/responses
- Document error codes and responses

### Code Documentation

- Write clear docstrings for all public functions
- Include type hints
- Document complex algorithms
- Keep documentation up to date

## 🐛 Debugging

### Logging

Use structured logging with correlation IDs:

```python
import structlog

logger = structlog.get_logger(__name__)

async def process_opportunity(opportunity_id: str):
    """Process opportunity with proper logging."""
    logger.info(
        "Processing opportunity",
        opportunity_id=opportunity_id,
        user_id=current_user.id,
    )
    
    try:
        result = await complex_processing(opportunity_id)
        logger.info(
            "Opportunity processed successfully",
            opportunity_id=opportunity_id,
            processing_time=result.processing_time,
        )
        return result
    except Exception as e:
        logger.error(
            "Opportunity processing failed",
            opportunity_id=opportunity_id,
            error=str(e),
            exc_info=True,
        )
        raise
```

## 🤝 Code Review Guidelines

### For Authors

- Keep PRs small and focused
- Write clear PR descriptions
- Include tests for new functionality
- Update documentation as needed
- Respond promptly to feedback

### For Reviewers

- Focus on logic, not style (automated tools handle style)
- Check for security issues
- Verify test coverage
- Consider performance implications
- Be constructive in feedback

## 📞 Getting Help

- **Technical Questions**: Create a GitHub Discussion
- **Bug Reports**: Create a GitHub Issue
- **Feature Requests**: Create a GitHub Issue with feature template
- **Security Issues**: Email security@yourproject.com

---

Thank you for contributing to AI Opportunity Browser! 🚀