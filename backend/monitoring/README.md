# Monitoring Dashboards

This directory contains configuration for monitoring dashboards and alerting.

## Overview

The ORIGIN Learning Platform uses the following monitoring stack:

- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Alertmanager**: Alert routing and notification

## Dashboards

### 1. API Performance Dashboard

Monitors API endpoint performance:
- Request rate by endpoint
- Response time (p50, p95, p99)
- Error rate by endpoint
- Request duration histogram

**Key Metrics:**
- `http_request_duration_seconds`: API response times
- `http_requests_total`: Total requests by endpoint
- `http_request_errors_total`: Errors by endpoint

**Alerts:**
- API p95 response time > 500ms
- Error rate > 5%

### 2. External Service Availability Dashboard

Monitors external service health:
- GitHub API availability and latency
- LinkedIn API availability and latency
- OpenAI API availability and latency
- Pinecone availability and latency

**Key Metrics:**
- `external_service_up`: Service availability (0 or 1)
- `external_service_latency_seconds`: Service latency
- `external_service_errors_total`: Errors by service

**Alerts:**
- External service down for > 5 minutes
- External service latency > 2 seconds

### 3. Retry Success Rate Dashboard

Monitors retry logic effectiveness:
- Retry attempts by service
- Retry success rate
- Circuit breaker state changes

**Key Metrics:**
- `retry_attempts_total`: Total retry attempts
- `retry_success_total`: Successful retries
- `circuit_breaker_state`: Circuit breaker state (0=closed, 1=open, 2=half-open)

**Alerts:**
- Retry success rate < 50%
- Circuit breaker open for > 10 minutes

### 4. User Impact Dashboard

Monitors user-facing issues:
- User-impacting errors (authentication, onboarding, matching)
- Failed portfolio analyses
- Failed squad matches
- Failed notifications

**Key Metrics:**
- `user_errors_total`: User-facing errors by type
- `portfolio_analysis_failures_total`: Failed portfolio analyses
- `squad_matching_failures_total`: Failed squad matches
- `notification_delivery_failures_total`: Failed notifications

**Alerts:**
- User error rate > 1%
- Portfolio analysis failure rate > 10%
- Squad matching failure rate > 5%

### 5. Background Jobs Dashboard

Monitors Celery background jobs:
- Task execution rate
- Task duration by type
- Task failure rate
- Queue length by priority

**Key Metrics:**
- `celery_task_duration_seconds`: Task execution time
- `celery_task_total`: Total tasks by type
- `celery_task_failures_total`: Failed tasks
- `celery_queue_length`: Queue length by priority

**Alerts:**
- Task failure rate > 10%
- Queue length > 1000

### 6. Database Performance Dashboard

Monitors database performance:
- Query duration (p50, p95, p99)
- Connection pool usage
- Slow queries (> 100ms)

**Key Metrics:**
- `db_query_duration_seconds`: Query execution time
- `db_connections_active`: Active connections
- `db_slow_queries_total`: Slow queries

**Alerts:**
- Query p95 > 100ms
- Connection pool > 80% utilized

## Setup Instructions

### 1. Install Prometheus

```bash
# Download and install Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
tar xvfz prometheus-2.40.0.linux-amd64.tar.gz
cd prometheus-2.40.0.linux-amd64

# Copy configuration
cp monitoring/prometheus.yml .

# Start Prometheus
./prometheus --config.file=prometheus.yml
```

### 2. Install Grafana

```bash
# Install Grafana
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo apt-get update
sudo apt-get install grafana

# Start Grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

### 3. Configure Dashboards

1. Access Grafana at http://localhost:3000 (default credentials: admin/admin)
2. Add Prometheus as a data source
3. Import dashboard JSON files from `monitoring/dashboards/`

### 4. Configure Alerting

1. Set up Alertmanager
2. Configure alert routing in `monitoring/alertmanager.yml`
3. Set up notification channels (email, Slack, PagerDuty)

## Metrics Instrumentation

### Python (FastAPI)

```python
from prometheus_client import Counter, Histogram, Gauge

# Request counter
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Response time histogram
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Active connections gauge
db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)
```

### Middleware Integration

Add Prometheus middleware to FastAPI:

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)
```

## Alert Configuration

Alerts are defined in `monitoring/alerts.yml` and include:

- **Critical**: Immediate action required (page on-call)
- **Warning**: Investigation needed (notify team)
- **Info**: Informational only (log)

## Dashboard Access

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Alertmanager**: http://localhost:9093

## Maintenance

- Review dashboards weekly
- Update alert thresholds based on actual performance
- Archive old metrics after 90 days
- Test alerting monthly
