# AI Opportunity Browser

An AI-native platform that combines autonomous agent-based discovery with community-driven validation to surface market-proven opportunities specifically solvable by AI technologies.

## 🚀 Features

- **Autonomous AI Agents**: Specialized agents for monitoring, analysis, research, trend detection, and capability assessment
- **Multi-Source Data Intelligence**: Reddit, GitHub, social media, job boards, research papers, and news APIs
- **Community Validation**: Expert verification and crowd-sourced validation workflows
- **Business Intelligence**: Market sizing, ROI projections, and implementation guidance
- **Multi-Provider AI Support**: OpenAI, Anthropic, Google, Cohere, and local models

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  Agentic AI Layer │───▶│ Processing Pipeline │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ User Interface  │◀───│  Core Platform   │───▶│ Vector Database │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python 3.11+
- **Frontend**: Next.js 14 with App Router, TypeScript, Tailwind CSS
- **Databases**: PostgreSQL, Redis, Pinecone (Vector DB)
- **AI/ML**: LangChain, Multiple LLM providers, Transformers
- **Task Queue**: Celery
- **Containerization**: Docker, Docker Compose
- **Testing**: pytest, pytest-asyncio

## 📋 Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Docker and Docker Compose
- Git

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ai-opportunity-browser
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys and configuration
# At minimum, set:
# - SECRET_KEY
# - OPENAI_API_KEY (or other AI provider keys)
# - PINECONE_API_KEY and PINECONE_ENVIRONMENT
```

### 3. Install Dependencies

```bash
# Install Python dependencies
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
pip install -r requirements.txt

# Install frontend dependencies
cd ui
npm install
cd ..
```

### 4. Start Development Environment

**Option 1: Using Makefile (Recommended)**
```bash
# Start databases
make dev-up

# In another terminal, start the API server
make dev-api

# In a third terminal, start the frontend
cd ui && npm run dev
```

**Option 2: Manual Startup**
```bash
# Start databases
docker-compose up -d postgres redis

# Start backend API (in new terminal)
source venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (in new terminal)
cd ui
npm run dev
```

**Option 3: Use the Convenience Script**
```bash
# Start both backend and frontend servers
./start-servers.sh
```

## 📚 Access the Application

Once the servers are running, visit:
- **Frontend Application**: http://localhost:3001
- **Backend API**: http://localhost:8000
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc

## 🧪 Testing

**Backend Tests**
```bash
# Run all backend tests
make test

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_api.py
```

**Frontend Tests**
```bash
# Run frontend tests
cd ui
npm test

# Run with coverage
npm run test:coverage

# Run linting
npm run lint

# Type checking
npm run type-check
```

## 🔧 Development

### Code Quality

```bash
# Format code
make format

# Run linting
make lint

# Run type checking
mypy .
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Adding New Data Sources

1. Create a new plugin in `data-ingestion/plugins/`
2. Inherit from `DataSourcePlugin` base class
3. Implement required methods: `initialize()`, `fetch_data()`
4. Register the plugin in the plugin manager

### Adding New AI Agents

1. Create agent class in `agents/` directory
2. Inherit from base `Agent` class
3. Implement agent-specific logic
4. Register with `AgentOrchestrator`

## 🌍 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `SECRET_KEY` | JWT secret key | Yes |
| `PINECONE_API_KEY` | Pinecone vector database key | Yes |
| `OPENAI_API_KEY` | OpenAI API key | No* |
| `ANTHROPIC_API_KEY` | Anthropic API key | No* |
| `GEMINI_API_KEY` | Google Gemini API key | No* |
| `GITHUB_ACCESS_TOKEN` | GitHub API access token | No |
| `REDDIT_CLIENT_ID` | Reddit API client ID | No |
| `REDDIT_CLIENT_SECRET` | Reddit API client secret | No |
| `PRODUCTHUNT_ACCESS_TOKEN` | ProductHunt API token | No |
| `DEFAULT_LLM_PROVIDER` | Default AI provider | No |

*At least one AI provider key is required

## 📁 Project Structure

```
ai-opportunity-browser/
├── api/                    # FastAPI application
├── agents/                 # AI agents
├── data-ingestion/         # Data collection and processing
├── shared/                 # Shared utilities and models
├── ui/                     # Next.js frontend application
│   ├── src/
│   │   ├── app/           # Next.js App Router pages
│   │   ├── components/    # React components
│   │   ├── stores/        # Zustand state management
│   │   └── services/      # API service layer
│   ├── package.json       # Frontend dependencies
│   └── tailwind.config.js # Tailwind CSS configuration
├── scripts/                # Database and deployment scripts
├── tests/                  # Backend test files
├── .kiro/                  # Project specifications
├── docker-compose.yml      # Development environment
├── Dockerfile.dev          # Development container
├── requirements.txt        # Python dependencies
├── start-servers.sh        # Convenience startup script
└── README.md              # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write tests for new features
- Update documentation for API changes
- Use type hints for all functions
- Keep functions small and focused

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` endpoint when running
- **Issues**: Create an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions

## 🗺️ Roadmap

- [x] Core infrastructure and data models
- [x] Multi-provider AI integration  
- [x] Data ingestion plugins (Reddit, GitHub)
- [x] AI agent orchestration system
- [x] Community validation system
- [x] Business intelligence features
- [x] Web interface (Next.js frontend)
- [ ] Advanced analytics dashboard
- [ ] Mobile application
- [ ] Marketplace features
- [ ] Real-time collaboration tools

---

Built with ❤️ using FastAPI and modern AI technologies.