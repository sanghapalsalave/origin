# Load Testing Guide

## Overview

Load testing for the ORIGIN Learning Platform using Locust.

## Installation

```bash
pip install locust
```

## Running Tests

### Basic Load Test

Test with 100 concurrent users:

```bash
cd backend/load_tests
locust -f locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10
```

Access web UI at: http://localhost:8089

### Headless Mode

Run without web UI:

```bash
locust -f locustfile.py --host=http://localhost:8000 \
  --users 1000 --spawn-rate 50 --run-time 10m --headless
```

### Specific User Classes

Test only portfolio analysis:

```bash
locust -f locustfile.py --host=http://localhost:8000 \
  PortfolioAnalysisUser --users 50 --spawn-rate 5
```

## Test Scenarios

### 1. Normal Load (1000 users)

Simulates typical usage:

```bash
locust -f locustfile.py --host=http://localhost:8000 \
  --users 1000 --spawn-rate 50 --run-time 30m
```

**Expected Results:**
- API p95 response time < 500ms
- Error rate < 1%
- Throughput > 100 req/s

### 2. Peak Load (5000 users)

Simulates peak traffic:

```bash
locust -f locustfile.py --host=http://localhost:8000 \
  --users 5000 --spawn-rate 100 --run-time 30m
```

**Expected Results:**
- API p95 response time < 1s
- Error rate < 5%
- Throughput > 500 req/s

### 3. Stress Test (10000 users)

Tests system limits:

```bash
locust -f locustfile.py --host=http://localhost:8000 \
  --users 10000 --spawn-rate 200 --run-time 30m
```

**Expected Results:**
- System remains stable
- Graceful degradation
- No crashes

### 4. Portfolio Analysis Load

Tests heavy operations:

```bash
locust -f locustfile.py --host=http://localhost:8000 \
  PortfolioAnalysisUser --users 100 --spawn-rate 10 --run-time 15m
```

**Expected Results:**
- Portfolio analysis < 5 seconds
- No timeouts
- Queue processing works

### 5. Squad Matching Load

Tests matching algorithm:

```bash
locust -f locustfile.py --host=http://localhost:8000 \
  SquadMatchingUser --users 200 --spawn-rate 20 --run-time 15m
```

**Expected Results:**
- Squad matching < 3 seconds
- Correct matches
- No duplicate assignments

## Performance Thresholds

| Operation | Threshold | Critical |
|-----------|-----------|----------|
| API Response (p95) | < 500ms | < 1s |
| Portfolio Analysis | < 5s | < 10s |
| Squad Matching | < 3s | < 5s |
| Syllabus Generation | < 10s | < 20s |
| Chat Message Delivery | < 2s | < 5s |

## Monitoring During Tests

### 1. System Metrics

```bash
# CPU and memory
docker stats

# Database connections
docker-compose exec postgres psql -U origin -d origin_db \
  -c "SELECT count(*) FROM pg_stat_activity"

# Redis memory
docker-compose exec redis redis-cli INFO memory
```

### 2. Application Metrics

```bash
# API metrics
curl http://localhost:8000/metrics

# Celery queue length
docker-compose exec redis redis-cli LLEN celery
```

### 3. Logs

```bash
# Backend logs
docker-compose logs -f backend

# Celery logs
docker-compose logs -f celery_worker_high
```

## Analyzing Results

### Locust Web UI

1. Response times (p50, p95, p99)
2. Requests per second
3. Failure rate
4. Response time distribution

### Export Results

```bash
# Generate HTML report
locust -f locustfile.py --host=http://localhost:8000 \
  --users 1000 --spawn-rate 50 --run-time 10m \
  --html=report.html --headless
```

## Optimization Tips

### If Response Times Are High:

1. **Scale workers:**
   ```bash
   docker-compose up -d --scale backend=4
   ```

2. **Increase database connections:**
   ```python
   SQLALCHEMY_POOL_SIZE = 20
   SQLALCHEMY_MAX_OVERFLOW = 40
   ```

3. **Enable caching:**
   - Redis caching for frequent queries
   - CDN for static assets

4. **Optimize queries:**
   - Add indexes
   - Use query optimization
   - Implement pagination

### If Error Rate Is High:

1. **Check logs:**
   ```bash
   docker-compose logs --tail=100 backend
   ```

2. **Increase timeouts:**
   ```python
   TIMEOUT = 60  # seconds
   ```

3. **Add rate limiting:**
   ```python
   RATE_LIMIT_PER_MINUTE = 120
   ```

### If System Crashes:

1. **Increase resources:**
   - More CPU/memory
   - Scale horizontally

2. **Add circuit breakers:**
   - Prevent cascade failures
   - Graceful degradation

3. **Implement backpressure:**
   - Queue limits
   - Request throttling

## Continuous Load Testing

### Scheduled Tests

Run load tests nightly:

```bash
# Add to cron
0 2 * * * cd /opt/origin-platform/backend/load_tests && \
  locust -f locustfile.py --host=http://localhost:8000 \
  --users 1000 --spawn-rate 50 --run-time 30m \
  --html=/var/reports/load-test-$(date +\%Y\%m\%d).html --headless
```

### CI/CD Integration

Add to GitHub Actions:

```yaml
- name: Run load tests
  run: |
    pip install locust
    cd backend/load_tests
    locust -f locustfile.py --host=${{ secrets.STAGING_URL }} \
      --users 100 --spawn-rate 10 --run-time 5m --headless
```

## Troubleshooting

### Connection Refused

- Check backend is running: `docker-compose ps backend`
- Check port is correct: `8000`
- Check firewall rules

### High Failure Rate

- Check error logs
- Verify test data is valid
- Check database capacity

### Slow Response Times

- Check system resources
- Monitor database queries
- Check external API latency

## Best Practices

1. **Start small:** Begin with 10-50 users
2. **Ramp up gradually:** Increase spawn rate slowly
3. **Monitor continuously:** Watch metrics during tests
4. **Test realistic scenarios:** Use production-like data
5. **Document results:** Track performance over time
6. **Fix issues:** Address bottlenecks before production
