# AI Opportunity Browser

AI-native platform combining autonomous agent-based discovery with community-driven validation to surface market-proven opportunities specifically solvable by AI technologies.

## 🚀 Features

### Core Capabilities
- **Proper DSPy Integration**: Complete implementation following the DSPy integration plan with MarketResearchSignature, CompetitiveAnalysisSignature, and SynthesisSignature
- **Real Market Data Integration**: Connects to data ingestion system with Reddit, GitHub, and other market signal sources
- **Data-Driven Opportunity Generation**: Uses actual market signals, pain points, and feature requests from real sources
- **Dual-Mode Operation**: Proper DSPy pipeline with real data + fallback custom orchestrator for compatibility
- **Market Validation**: Each generated opportunity includes data source validation and engagement metrics

### AI & Analysis
- **5 Specialized AI Agents**: MonitoringAgent, AnalysisAgent, ResearchAgent, TrendAgent, and CapabilityAgent
- **3-Step DSPy Pipeline**: Market Research → Competitive Analysis → Synthesis with real data flow
- **Enhanced Output Parsing**: Handles both DSPy structured output and custom formats
- **Deep Dive Feature**: Initiate in-depth analysis on any opportunity from its detail page

### Data & Sources
- **Real-time Data Sources**: Reddit discussions, GitHub issues, Hacker News, Y Combinator
- **Market Signal Processing**: Pain point detection, feature request analysis, engagement scoring
- **Data Quality Scoring**: Comprehensive quality assessment and duplicate detection

### Platform Features
- **Community Validation**: User scoring and validation system with reputation tracking
- **Business Intelligence**: ROI projections, market analysis, competitive intelligence
- **Modern Frontend**: Next.js 14 with TypeScript, Tailwind CSS, and Shadcn/ui
- **Production Ready**: Comprehensive authentication, monitoring, and security

## 🏗️ Architecture

### DSPy Integration (Latest Implementation)
The system now implements **proper DSPy integration** as specified in the integration plan:

- **DSPy Signatures**: 
  - `MarketResearchSignature`: Analyzes real market data from ingestion sources
  - `CompetitiveAnalysisSignature`: Processes competitive intelligence from market signals  
  - `SynthesisSignature`: Creates opportunities with market validation data

- **Data Pipeline**: Connects DSPy to the data ingestion system for real Reddit/GitHub analysis
- **Orchestrator**: Dual-mode operation with proper DSPy pipeline + custom orchestrator fallback
- **Market Data Integration**: Fetches real market signals, engagement metrics, and pain points

### System Architecture
- **Backend**: FastAPI with async/await, PostgreSQL, Redis, Pinecone vector DB
- **Data Ingestion**: Plugin architecture with Reddit, GitHub, and other source connectors
- **AI Pipeline**: DSPy framework with Gemini/OpenAI/Anthropic model support
- **Frontend**: Next.js 14 App Router with TypeScript and Tailwind CSS
- **Caching**: In-memory DSPy content cache for detail page integration

## 📋 Prerequisites

- **Python 3.11+**
- **Node.js 18+** 
- **PostgreSQL 13+**
- **Redis 6+**
- **Git**

## 🔧 Quick Setup

### 1. Clone the Repository

```bash
git clone https://github.com/justQrius/Ai_opportunity_browser.git
cd Ai_opportunity_browser
```

### 2. Backend Setup

```bash
# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env file with your API keys (see API Keys section below)
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd ui

# Install Node.js dependencies
npm install

# Copy environment template and configure
cp .env.example .env.local
# Edit .env.local file with your configuration
```

### 4. Database Setup

```bash
# Start PostgreSQL and Redis services
# Ubuntu/Debian:
sudo systemctl start postgresql redis-server

# macOS with Homebrew:
brew services start postgresql redis

# Create database
createdb ai_opportunity_browser

# Run database migrations
alembic upgrade head
```

### 5. Start the Application

```bash
# Start backend (from root directory)
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Start frontend (in new terminal, from ui/ directory)
cd ui
npm run dev
```

🎉 **Application URLs:**
- **Frontend**: http://localhost:3004
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔑 API Keys Configuration

The application requires several API keys for data sources. Create accounts and obtain keys from:

### Required APIs

#### 1. **GitHub API** (Free)
- **Purpose**: Access AI repositories, trending developer tools, startup projects
- **Get Key**: https://github.com/settings/tokens
- **Permissions**: `public_repo`, `read:user`
- **Rate Limit**: 5,000 requests/hour

#### 2. **Reddit API** (Free)
- **Purpose**: Monitor r/artificial, r/MachineLearning, r/startups, r/entrepreneur
- **Get Key**: https://www.reddit.com/prefs/apps
- **Type**: Create "script" application
- **Rate Limit**: 60 requests/minute

#### 3. **OpenAI API** (Optional - for enhanced AI features)
- **Purpose**: Advanced opportunity analysis and text generation
- **Get Key**: https://platform.openai.com/api-keys
- **Usage**: Pay-per-use ($0.0015-0.02 per 1K tokens)

#### 4. **Google Gemini API** (Optional - for enhanced AI features)
- **Purpose**: Alternative AI model for analysis
- **Get Key**: https://makersuite.google.com/app/apikey
- **Usage**: Free tier available

### Configure API Keys

Edit your `.env` file:

```bash
# Required APIs
GITHUB_ACCESS_TOKEN=your_github_personal_access_token_here
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here

# Optional AI APIs (for enhanced features)
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_google_gemini_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_opportunity_browser
REDIS_URL=redis://localhost:6379/0

# Application Settings
SECRET_KEY=your-secret-key-change-in-production-make-it-long-and-random
DEBUG=true
ENVIRONMENT=development
```

## 🧪 Development Commands

### Backend Commands
```bash
# Run API server
uvicorn api.main:app --reload

# Run tests  
pytest

# Database migration
alembic upgrade head

# Start with Docker
docker-compose up
```

### Frontend Commands
```bash
cd ui

# Development server
npm run dev

# Production build
npm run build

# Run tests
npm test

# Type checking
npm run type-check

# Linting
npm run lint

# Storybook (component library)
npm run storybook
```

## 📁 Project Structure

```
├── api/                    # FastAPI backend
│   ├── routers/           # API endpoints
│   ├── middleware/        # Security, logging, CORS
│   └── core/             # Configuration, dependencies
├── agents/                # DSPy-powered AI pipeline and agent modules
├── shared/               # Shared models, schemas, services
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic schemas
│   └── services/         # Business logic
├── data-ingestion/       # Plugin architecture for data sources
├── tests/                # Comprehensive test suite
├── ui/                   # Next.js 14 frontend
│   ├── src/app/          # Next.js App Router pages
│   ├── src/components/   # React components
│   ├── src/services/     # API service layer
│   └── src/stores/       # Zustand state management
├── monitoring/           # Grafana, Prometheus configuration
└── scripts/              # Utility and demo scripts
```

## 🚀 Usage Guide

### 1. **Browse Opportunities**
- Visit http://localhost:3004/opportunities
- Use search and filters to find relevant opportunities
- Sort by validation score, market size, or creation date

### 2. **View Opportunity Details**
- Click on any opportunity to see detailed analysis
- Review AI agent analysis and business intelligence
- Check community validation and discussions

### 3. **Initiate a Deep Dive**
- Navigate to any opportunity's detail page.
- Click the "Deep Dive" button to trigger a dynamic, multi-agent analysis of the opportunity.
- A notification will appear confirming the start of the workflow, and another will appear upon completion.

### 4. **User Authentication**
- Register at http://localhost:3004/auth/register
- Login at http://localhost:3004/auth/login
- Access personalized recommendations and collections

## 🐛 Troubleshooting

### Common Issues

#### Backend won't start
```bash
# Check Python version
python3 --version  # Should be 3.11+

# Check if all dependencies installed
pip install -r requirements.txt

# Check database connection
psql -d ai_opportunity_browser -c "SELECT 1;"
```

#### Frontend won't start
```bash
# Check Node version
node --version  # Should be 18+

# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Check for port conflicts
lsof -ti:3004
```

#### API Keys not working
- **GitHub**: Ensure token has correct permissions
- **Reddit**: Verify client ID/secret match your app
- **Rate Limits**: Check if you've exceeded API limits

### Getting Help

- **Issues**: [GitHub Issues](https://github.com/justQrius/Ai_opportunity_browser/issues)
- **Discussions**: [GitHub Discussions](https://github.com/justQrius/Ai_opportunity_browser/discussions)

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open Pull Request**

### Code Standards
- **Python**: Follow PEP 8, use type hints
- **TypeScript**: Strict mode, proper typing
- **Testing**: Write tests for new features
- **Documentation**: Update README and docstrings

## 🔒 Security Features

- **JWT Authentication**: Secure user authentication
- **Rate Limiting**: API rate limiting and throttling
- **CORS Protection**: Configurable CORS policies
- **Input Validation**: Comprehensive request validation
- **SQL Injection Protection**: Parameterized queries

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI**: Modern, fast web framework for Python
- **Next.js**: The React framework for production
- **Shadcn/ui**: Beautiful component library
- **PostgreSQL**: Powerful, open source object-relational database
- **Redis**: In-memory data structure store

---

**Built with ❤️ by [justQrius](https://github.com/justQrius)**

⭐ **Star this repo if you find it useful!**