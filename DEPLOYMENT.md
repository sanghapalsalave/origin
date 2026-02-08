# ORIGIN Learning Platform - Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Database Setup](#database-setup)
4. [Docker Deployment](#docker-deployment)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software
- Docker 20.10+
- Docker Compose 2.0+
- PostgreSQL 15+
- Redis 7+
- Node.js 18+ (for mobile app)
- Python 3.11+ (for backend)

### Required Services
- Pinecone account (vector database)
- OpenAI API key (LLM features)
- Firebase project (chat and notifications)
- AWS account (file storage)
- Sentry account (error tracking, optional)

## Environment Configuration

### 1. Backend Environment Variables

Copy the example environment file:
```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and fill in all required values:

**Critical Variables:**
- `SECRET_KEY`: Generate with `openssl rand -hex 32`
- `JWT_SECRET_KEY`: Generate with `openssl rand -hex 32`
- `POSTGRES_PASSWORD`: Strong password for database
- `PINECONE_API_KEY`: From Pinecone dashboard
- `OPENAI_API_KEY`: From OpenAI dashboard
- `FIREBASE_*`: From Firebase project settings

### 2. Mobile Environment Variables

Copy the example environment file:
```bash
cp mobile/.env.example mobile/.env
```

Edit `mobile/.env`:
```
API_BASE_URL=https://api.origin-learning.com/api/v1
FIREBASE_API_KEY=your-firebase-api-key
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_APP_ID=your-firebase-app-id
```

### 3. Production Environment

For production, use environment-specific files:
- `backend/.env.production`
- `docker-compose.prod.yml`

**Security Best Practices:**
- Never commit `.env` files to version control
- Use secrets management (AWS Secrets Manager, HashiCorp Vault)
- Rotate secrets regularly
- Use strong passwords (minimum 32 characters)

## Database Setup

### 1. Initialize Database

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Run migrations
docker-compose exec backend alembic upgrade head
```

### 2. Create Initial Data (Optional)

```bash
# Create admin user
docker-compose exec backend python scripts/create_admin.py

# Seed test data (development only)
docker-compose exec backend python scripts/seed_data.py
```

### 3. Backup and Restore

**Backup:**
```bash
docker-compose exec postgres pg_dump -U origin origin_db > backup.sql
```

**Restore:**
```bash
docker-compose exec -T postgres psql -U origin origin_db < backup.sql
```

## Docker Deployment

### Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Staging

```bash
# Build and deploy
docker-compose -f docker-compose.staging.yml up -d --build

# Run migrations
docker-compose -f docker-compose.staging.yml exec backend alembic upgrade head
```

### Production

```bash
# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Run migrations
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# Deploy with zero downtime
docker-compose -f docker-compose.prod.yml up -d --no-deps --scale backend=2
sleep 30
docker-compose -f docker-compose.prod.yml up -d --no-deps --remove-orphans
```

## CI/CD Pipeline

### GitHub Actions Workflows

1. **CI Pipeline** (`.github/workflows/ci.yml`)
   - Runs on every push and PR
   - Linting, type checking, tests
   - Code coverage reporting
   - Security scanning

2. **CD Staging** (`.github/workflows/cd-staging.yml`)
   - Deploys to staging on push to `develop`
   - Automatic deployment
   - Smoke tests

3. **CD Production** (`.github/workflows/cd-production.yml`)
   - Deploys to production on push to `main` or tags
   - Requires manual approval (2 approvers)
   - Blue-green deployment
   - Automatic rollback on failure

### Required Secrets

Configure in GitHub Settings > Secrets:

```
REGISTRY_URL=your-container-registry
REGISTRY_USERNAME=your-username
REGISTRY_PASSWORD=your-password

STAGING_HOST=staging.origin-learning.com
STAGING_USERNAME=deploy
STAGING_SSH_KEY=<private-key>
STAGING_URL=https://staging.origin-learning.com

PRODUCTION_HOST=api.origin-learning.com
PRODUCTION_USERNAME=deploy
PRODUCTION_SSH_KEY=<private-key>
PRODUCTION_URL=https://api.origin-learning.com

APPROVERS=user1,user2
SLACK_WEBHOOK=https://hooks.slack.com/...
```

## Monitoring

### Health Checks

- **Basic**: `GET /health`
- **Detailed**: `GET /health/detailed`
- **Readiness**: `GET /health/readiness`
- **Liveness**: `GET /health/liveness`

### Prometheus Metrics

Access metrics at: `http://localhost:8000/metrics`

### Grafana Dashboards

1. Start Grafana:
```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

2. Access: `http://localhost:3000` (admin/admin)

3. Import dashboards from `backend/monitoring/dashboards/`

### Logs

**View logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

**Structured logging:**
All logs are in JSON format with request IDs for correlation.

## Troubleshooting

### Common Issues

**1. Database connection failed**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection
docker-compose exec postgres psql -U origin -d origin_db -c "SELECT 1"
```

**2. Redis connection failed**
```bash
# Check Redis is running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping
```

**3. Celery tasks not running**
```bash
# Check Celery workers
docker-compose ps celery_worker_high celery_worker_default

# View Celery logs
docker-compose logs -f celery_worker_high

# Check Flower dashboard
open http://localhost:5555
```

**4. High memory usage**
```bash
# Check container stats
docker stats

# Restart services
docker-compose restart backend celery_worker_high
```

**5. Slow API responses**
```bash
# Check performance metrics
curl http://localhost:8000/metrics | grep http_request_duration

# Check database queries
docker-compose exec postgres psql -U origin -d origin_db -c "SELECT * FROM pg_stat_activity"
```

### Rollback Procedure

**1. Identify last working version:**
```bash
docker images | grep origin-backend
```

**2. Rollback:**
```bash
# Update docker-compose to use previous version
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

**3. Rollback database (if needed):**
```bash
# Downgrade one migration
docker-compose exec backend alembic downgrade -1

# Downgrade to specific version
docker-compose exec backend alembic downgrade <revision>
```

### Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Check health: `curl http://localhost:8000/health/detailed`
3. Check monitoring dashboards
4. Contact DevOps team

## Performance Tuning

### Backend
- Adjust worker count: `--workers 4` in Dockerfile
- Tune database connection pool: `SQLALCHEMY_POOL_SIZE`
- Enable caching: Redis configuration

### Celery
- Adjust concurrency: `--concurrency=8`
- Tune prefetch multiplier: `worker_prefetch_multiplier`
- Scale workers: `docker-compose up -d --scale celery_worker_default=3`

### Database
- Enable query caching
- Add indexes for slow queries
- Tune PostgreSQL configuration

### Redis
- Increase max memory: `maxmemory 2gb`
- Set eviction policy: `maxmemory-policy allkeys-lru`

## Security Checklist

- [ ] All secrets in environment variables (not hardcoded)
- [ ] TLS 1.3 enabled for all endpoints
- [ ] Database passwords rotated
- [ ] API keys rotated
- [ ] Firewall rules configured
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Security headers enabled
- [ ] Audit logging enabled
- [ ] Backups automated
- [ ] Monitoring alerts configured
- [ ] Incident response plan documented
