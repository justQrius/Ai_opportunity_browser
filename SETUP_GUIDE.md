# 🚀 AI Opportunity Browser - Complete Setup Guide

This guide will walk you through setting up the AI Opportunity Browser from scratch. Follow these steps carefully to get the application running locally.

## 📋 Prerequisites Checklist

Before starting, ensure you have the following installed:

- [ ] **Python 3.11+** - `python3 --version`
- [ ] **Node.js 18+** - `node --version`  
- [ ] **PostgreSQL 13+** - `psql --version`
- [ ] **Redis 6+** - `redis-server --version`
- [ ] **Git** - `git --version`

## 🔧 Step-by-Step Setup

### Step 1: Clone and Navigate

```bash
# Clone the repository
git clone https://github.com/justQrius/Ai_opportunity_browser.git
cd Ai_opportunity_browser

# Verify you're in the right directory
ls -la  # Should see api/, ui/, shared/, agents/ directories
```

### Step 2: Backend Environment Setup

```bash
# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate     # Windows

# Verify activation (should show venv path)
which python

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify key packages installed
python -c "import fastapi, sqlalchemy, redis; print('✅ Core packages installed')"
```

### Step 3: Database Setup

#### PostgreSQL Setup

```bash
# Start PostgreSQL service
sudo systemctl start postgresql    # Linux
brew services start postgresql     # macOS
# Windows: Start from Services panel

# Create database
createdb ai_opportunity_browser

# Test database connection
psql -d ai_opportunity_browser -c "SELECT version();"
```

#### Redis Setup

```bash
# Start Redis service
sudo systemctl start redis-server  # Linux  
brew services start redis          # macOS
# Windows: Start from Services panel

# Test Redis connection
redis-cli ping  # Should return PONG
```

### Step 4: Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit the .env file with your settings
nano .env  # or your preferred editor
```

**Required configurations in `.env`:**

```bash
# Database (update if needed)
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/ai_opportunity_browser"
REDIS_URL="redis://localhost:6379/0"

# Security (IMPORTANT: Change this!)
SECRET_KEY="your-unique-secret-key-minimum-32-characters-long"

# CORS (add your frontend port)
ALLOWED_ORIGINS=["http://localhost:3004", "http://localhost:3000"]
```

### Step 5: API Keys Setup

The application needs API keys to function. Here's how to get them:

#### GitHub API (Required)

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a name: "AI Opportunity Browser"
4. Select scopes: `public_repo`, `read:user`
5. Click "Generate token"
6. Copy the token and add to `.env`:

```bash
GITHUB_ACCESS_TOKEN="ghp_your_token_here"
```

#### Reddit API (Required)

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Fill out the form:
   - **Name**: AI Opportunity Browser
   - **App type**: script
   - **Description**: Data collection for AI opportunities
   - **About URL**: (leave blank)
   - **Redirect URI**: http://localhost:8000
4. Click "Create app"
5. Copy the Client ID (under the app name) and Secret
6. Add to `.env`:

```bash
REDDIT_CLIENT_ID="your_client_id_here"
REDDIT_CLIENT_SECRET="your_client_secret_here"
```

#### AI APIs (Optional but Recommended)

**OpenAI API:**
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key and add to `.env`:
```bash
OPENAI_API_KEY="sk-your_openai_key_here"
```

**Google Gemini API:**
1. Go to https://makersuite.google.com/app/apikey
2. Click "Create API key"
3. Copy the key and add to `.env`:
```bash
GEMINI_API_KEY="your_gemini_key_here"
```

### Step 6: Database Migration

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run database migrations
alembic upgrade head

# Verify tables were created
psql -d ai_opportunity_browser -c "\dt"
```

### Step 7: Frontend Setup

```bash
# Navigate to frontend directory
cd ui

# Install Node.js dependencies
npm install

# Create frontend environment file
cp .env.example .env.local

# Edit frontend environment (usually defaults are fine)
nano .env.local
```

**Frontend `.env.local` should contain:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
PORT=3004
```

### Step 8: Test Backend

```bash
# Navigate back to root directory
cd ..

# Make sure virtual environment is activated
source venv/bin/activate

# Start backend server
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Test in another terminal:**
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test opportunities endpoint
curl http://localhost:8000/api/v1/opportunities/

# Open API documentation in browser
# http://localhost:8000/docs
```

### Step 9: Test Frontend

```bash
# In a new terminal, navigate to frontend
cd ui

# Start frontend development server
npm run dev
```

**Test in browser:**
- Open http://localhost:3004
- You should see the AI Opportunity Browser interface
- Try navigating to different pages

### Step 10: Verify Full Integration

1. **Backend Health**: http://localhost:8000/health
2. **API Docs**: http://localhost:8000/docs
3. **Frontend**: http://localhost:3004
4. **Opportunities Page**: http://localhost:3004/opportunities
5. **Individual Opportunity**: http://localhost:3004/opportunities/ai-chatbot-001

## 🧪 Testing Your Setup

### Backend Tests

```bash
# Make sure you're in root directory with venv activated
source venv/bin/activate

# Run basic tests
python -c "
import requests
response = requests.get('http://localhost:8000/health')
print('Backend Status:', response.status_code)
print('Response:', response.json())
"

# Test database connection
python -c "
from shared.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('✅ Database connected successfully')
"
```

### Frontend Tests

```bash
cd ui

# Run type checking
npm run type-check

# Run linting
npm run lint

# Test build
npm run build
```

## 🚨 Common Issues & Solutions

### Issue: "ModuleNotFoundError" when starting backend

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

### Issue: Database connection error

**Solution:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS

# Check database exists
psql -l | grep ai_opportunity_browser

# Recreate database if needed
dropdb ai_opportunity_browser
createdb ai_opportunity_browser
alembic upgrade head
```

### Issue: Redis connection error

**Solution:**
```bash
# Check Redis is running
redis-cli ping

# Start Redis if not running
sudo systemctl start redis-server  # Linux
brew services start redis          # macOS

# Check Redis configuration
redis-cli config get "*"
```

### Issue: Frontend can't connect to backend

**Solution:**
```bash
# Check backend is running on correct port
curl http://localhost:8000/health

# Check frontend environment
cat ui/.env.local

# Verify CORS settings in backend .env
grep ALLOWED_ORIGINS .env
```

### Issue: API keys not working

**Solution:**
```bash
# Test GitHub API key
curl -H "Authorization: token YOUR_GITHUB_TOKEN" https://api.github.com/user

# Test Reddit API (check client ID/secret format)
# Client ID should be ~14 chars, Secret should be ~27 chars

# Verify environment variables are loaded
python -c "import os; print('GitHub:', os.getenv('GITHUB_ACCESS_TOKEN', 'NOT_SET')[:10] + '...')"
```

## 🎯 Next Steps

Once your setup is complete:

1. **Explore the Interface**: Browse opportunities, view details, try filtering
2. **Check API Documentation**: Visit http://localhost:8000/docs
3. **Review Logs**: Check terminal output for any errors or warnings
4. **Customize Configuration**: Adjust settings in `.env` files as needed
5. **Add More API Keys**: Set up additional AI providers for enhanced features

## 📞 Getting Help

If you encounter issues:

1. **Check Logs**: Look at terminal output for error messages
2. **Verify Prerequisites**: Ensure all software versions meet requirements
3. **Review Environment**: Double-check `.env` file configurations
4. **Test Components**: Test database, Redis, and API keys individually
5. **GitHub Issues**: Create an issue with detailed error information

## 🔄 Development Workflow

For ongoing development:

```bash
# Daily startup routine
cd Ai_opportunity_browser

# Start backend
source venv/bin/activate
uvicorn api.main:app --reload

# In new terminal, start frontend  
cd ui
npm run dev
```

## 🚀 Production Deployment

For production deployment, see:
- Update environment variables for production
- Use production databases (not local PostgreSQL/Redis)
- Set up proper domain and SSL certificates
- Configure monitoring and logging
- Review security settings

---

**🎉 Congratulations!** You now have a fully functional AI Opportunity Browser running locally. Start exploring AI opportunities and contribute to the community validation process!