# ORIGIN Learning Platform - Setup Guide

This guide will help you set up the ORIGIN Learning Platform development environment.

## Quick Start

The fastest way to get started is using Docker Compose:

```bash
# 1. Clone the repository
git clone <repository-url>
cd origin-learning-platform

# 2. Set up environment files
make setup

# 3. Edit configuration files
# Edit backend/.env with your API keys and configuration
# Edit mobile/.env with your configuration

# 4. Start all services
make start

# 5. Run database migrations
make migrate

# 6. Access the application
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/api/v1/docs
```

## Detailed Setup Instructions

### 1. Prerequisites

Install the following tools:

- **Docker Desktop** (recommended for easiest setup)
  - Download from: https://www.docker.com/products/docker-desktop
  - Includes Docker and Docker Compose

- **Node.js 18+** (for mobile development)
  - Download from: https://nodejs.org/
  - Verify: `node --version`

- **Python 3.11+** (optional, for local backend development)
  - Download from: https://www.python.org/
  - Verify: `python --version`

- **Git**
  - Download from: https://git-scm.com/
  - Verify: `git --version`

### 2. Clone and Configure

```bash
# Clone the repository
git clone <repository-url>
cd origin-learning-platform

# Copy environment files
cp backend/.env.example backend/.env
cp mobile/.env.example mobile/.env
```

### 3. Configure Backend Environment

Edit `backend/.env` and set the following required variables:

```bash
# Security - IMPORTANT: Change in production!
SECRET_KEY=your-super-secret-key-at-least-32-characters-long

# OpenAI API (required for Guild Master AI)
OPENAI_API_KEY=sk-your-openai-api-key

# Pinecone (required for vector matching)
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-pinecone-environment

# GitHub API (optional, for portfolio analysis)
GITHUB_TOKEN=ghp_your-github-token

# LinkedIn API (optional, for portfolio analysis)
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret

# Firebase (optional, for real-time chat)
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_CREDENTIALS_PATH=/path/to/firebase-credentials.json

# AWS S3 (optional, for file storage)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_S3_BUCKET=origin-attachments
```

### 4. Configure Mobile Environment

Edit `mobile/.env`:

```bash
# API Configuration
API_BASE_URL=http://localhost:8000/api/v1

# Firebase Configuration (for push notifications)
FIREBASE_API_KEY=your-firebase-api-key
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_APP_ID=your-firebase-app-id
```

### 5. Start Services

#### Option A: Using Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

This starts:
- PostgreSQL database on port 5432
- Redis cache on port 6379
- FastAPI backend on port 8000
- Celery worker for background tasks
- Celery beat for scheduled tasks

#### Option B: Local Development

**Start PostgreSQL and Redis:**
```bash
# macOS with Homebrew
brew services start postgresql@15
brew services start redis

# Ubuntu/Debian
sudo systemctl start postgresql
sudo systemctl start redis-server
```

**Start Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn app.main:app --reload
```

**Start Celery (in separate terminals):**
```bash
# Terminal 1: Celery worker
celery -A app.core.celery_app worker --loglevel=info

# Terminal 2: Celery beat
celery -A app.core.celery_app beat --loglevel=info
```

### 6. Initialize Database

```bash
# Run migrations
make migrate

# Or manually:
docker-compose exec backend alembic upgrade head
```

### 7. Verify Backend Setup

```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"0.1.0","service":"origin-backend"}

# View API documentation
open http://localhost:8000/api/v1/docs
```

### 8. Set Up Mobile App

```bash
cd mobile

# Install dependencies
npm install

# iOS only (macOS required)
cd ios
pod install
cd ..

# Start Metro bundler
npm start
```

**Run on iOS:**
```bash
npm run ios
```

**Run on Android:**
```bash
npm run android
```

## External Services Setup

### OpenAI API

1. Sign up at https://platform.openai.com/
2. Create an API key
3. Add to `backend/.env`: `OPENAI_API_KEY=sk-...`

### Pinecone Vector Database

1. Sign up at https://www.pinecone.io/
2. Create a new index:
   - Name: `origin-embeddings`
   - Dimensions: 384 (for Sentence Transformers)
   - Metric: cosine
3. Get API key and environment
4. Add to `backend/.env`

### GitHub API (Optional)

1. Go to https://github.com/settings/tokens
2. Generate new token with `repo` scope
3. Add to `backend/.env`: `GITHUB_TOKEN=ghp_...`

### Firebase (Optional)

1. Create project at https://console.firebase.google.com/
2. Enable Realtime Database
3. Enable Cloud Messaging
4. Download service account credentials
5. Add configuration to `.env` files

## Development Workflow

### Running Tests

```bash
# All tests
make test

# Backend only
make test-backend

# Mobile only
make test-mobile

# With coverage
make coverage
```

### Code Quality

```bash
# Lint code
make lint

# Format code
make format

# Type check
make type-check
```

### Database Operations

```bash
# Create new migration
make migration

# Apply migrations
make migrate

# Open database shell
make db-shell
```

### Viewing Logs

```bash
# All services
make logs

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery_worker
```

## Troubleshooting

### Port Already in Use

If ports 5432, 6379, or 8000 are already in use:

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change ports in docker-compose.yml
```

### Database Connection Error

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Restart PostgreSQL
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### Redis Connection Error

```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping
# Should return: PONG
```

### Migration Errors

```bash
# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
make migrate
```

### Mobile Build Errors

```bash
# Clear cache
cd mobile
npm start -- --reset-cache

# Reinstall dependencies
rm -rf node_modules
npm install

# iOS: Clean build
cd ios
pod deintegrate
pod install
cd ..
```

## Next Steps

After setup is complete:

1. Review the [API Documentation](http://localhost:8000/api/v1/docs)
2. Check the [Design Document](.kiro/specs/origin-learning-platform/design.md)
3. Review the [Implementation Tasks](.kiro/specs/origin-learning-platform/tasks.md)
4. Start implementing features following the task list

## Getting Help

- Check the [README.md](README.md) for architecture overview
- Review the [Requirements](.kiro/specs/origin-learning-platform/requirements.md)
- Check existing issues and documentation
- Contact the development team

## Production Deployment

For production deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md) (to be created).

Key considerations:
- Use strong `SECRET_KEY`
- Enable HTTPS/TLS
- Configure proper CORS origins
- Set up monitoring and logging
- Use managed database services
- Configure auto-scaling
- Set up backup procedures
