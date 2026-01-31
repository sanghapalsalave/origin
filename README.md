# ORIGIN Learning Platform

A mobile-first adaptive learning platform that connects learners through AI-managed guilds. The platform matches users into small squads based on cognitive compatibility, manages curriculum through an AI Guild Master, and ensures accountability through a reputation-based mastery system.

## Architecture

- **Backend**: Python FastAPI with microservices architecture
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache & Queue**: Redis for caching and Celery for background tasks
- **Mobile**: React Native with TypeScript
- **AI Services**: OpenAI GPT-4o/Gemini 1.5 Pro, Sentence Transformers, Pinecone
- **Real-time**: Firebase/Supabase for chat

## Project Structure

```
.
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Core configuration
│   │   ├── db/             # Database configuration
│   │   ├── models/         # SQLAlchemy models
│   │   ├── services/       # Business logic services
│   │   ├── tasks/          # Celery background tasks
│   │   └── main.py         # Application entry point
│   ├── alembic/            # Database migrations
│   ├── tests/              # Backend tests
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile          # Backend container
├── mobile/                  # React Native mobile app
│   ├── src/
│   │   ├── api/            # API client
│   │   ├── components/     # React components
│   │   ├── navigation/     # Navigation configuration
│   │   ├── screens/        # Screen components
│   │   ├── stores/         # Zustand state management
│   │   └── theme/          # Theme configuration
│   ├── package.json        # Node dependencies
│   └── App.tsx             # App entry point
└── docker-compose.yml      # Local development setup
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for mobile development)
- Python 3.11+ (for local backend development)
- PostgreSQL 15+ (if not using Docker)
- Redis 7+ (if not using Docker)

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd origin-learning-platform
   ```

2. **Configure environment variables**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

   This will start:
   - PostgreSQL database (port 5432)
   - Redis cache (port 6379)
   - FastAPI backend (port 8000)
   - Celery worker
   - Celery beat scheduler

4. **Run database migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

5. **Access the API**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/api/v1/docs
   - Health Check: http://localhost:8000/health

### Mobile Setup

1. **Install dependencies**
   ```bash
   cd mobile
   npm install
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install iOS dependencies (macOS only)**
   ```bash
   cd ios
   pod install
   cd ..
   ```

4. **Run the app**
   ```bash
   # iOS
   npm run ios

   # Android
   npm run android
   ```

### Local Development (without Docker)

1. **Install Python dependencies**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

2. **Start PostgreSQL and Redis**
   ```bash
   # Using Homebrew on macOS
   brew services start postgresql@15
   brew services start redis

   # Or using system package manager
   ```

3. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

4. **Start the backend**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Start Celery worker (in another terminal)**
   ```bash
   celery -A app.core.celery_app worker --loglevel=info
   ```

6. **Start Celery beat (in another terminal)**
   ```bash
   celery -A app.core.celery_app beat --loglevel=info
   ```

## Development

### Running Tests

**Backend:**
```bash
cd backend
pytest
pytest --cov=app tests/  # With coverage
```

**Mobile:**
```bash
cd mobile
npm test
```

### Code Quality

**Backend:**
```bash
# Linting
flake8 app/

# Type checking
mypy app/

# Formatting
black app/
```

**Mobile:**
```bash
# Linting
npm run lint

# Type checking
npm run type-check
```

### Database Migrations

**Create a new migration:**
```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

**Apply migrations:**
```bash
alembic upgrade head
```

**Rollback migration:**
```bash
alembic downgrade -1
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## Environment Variables

### Backend (.env)

Key variables to configure:
- `SECRET_KEY`: Strong secret key for JWT tokens
- `POSTGRES_*`: Database connection details
- `REDIS_*`: Redis connection details
- `OPENAI_API_KEY`: OpenAI API key for Guild Master AI
- `GITHUB_TOKEN`: GitHub API token for portfolio analysis
- `PINECONE_API_KEY`: Pinecone API key for vector search
- `FIREBASE_*` or `SUPABASE_*`: Real-time chat configuration

### Mobile (.env)

Key variables to configure:
- `API_BASE_URL`: Backend API URL
- `FIREBASE_*`: Firebase configuration for push notifications and chat

## Contributing

1. Create a feature branch
2. Make your changes
3. Write tests
4. Run linters and type checkers
5. Submit a pull request

## License

[License information]

## Support

For questions or issues, please contact [support information]
