# Deep Research Agent (REX) - Deployment Guide

## Overview
This guide provides comprehensive instructions for deploying the Deep Research Agent (REX) system in various environments, from local development to production Kubernetes clusters. It covers all deployment methods, configuration options, and operational procedures.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Docker Compose Deployment](#docker-compose-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Helm Chart Deployment](#helm-chart-deployment)
6. [Configuration Management](#configuration-management)
7. [Environment Variables](#environment-variables)
8. [Security Hardening](#security-hardening)
9. [Monitoring & Observability Setup](#monitoring--observability-setup)
10. [Backup & Disaster Recovery](#backup--disaster-recovery)
11. [Scaling Procedures](#scaling-procedures)
12. [Troubleshooting](#troubleshooting)
13. [Upgrade Procedures](#upgrade-procedures)
14. [Rollback Procedures](#rollback-procedures)
15. [Operational Runbooks](#operational-runbooks)

## Prerequisites

### Software Requirements
- **Docker Engine**: 20.10+
- **Docker Compose**: v2.0+
- **kubectl**: 1.20+ (for Kubernetes)
- **Helm**: 3.0+ (for Helm charts)
- **Git**: For cloning repository
- **Make**: For build automation (optional)
- **Node.js**: 18+ (for frontend development)
- **Python**: 3.11+ (for backend development)

### Hardware Requirements (Minimum)
- **Development/Local Testing**: 
  - CPU: 4 cores
  - RAM: 8 GB
  - Storage: 20 GB SSD
- **Production (Small Scale)**:
  - CPU: 8 cores
  - RAM: 16 GB
  - Storage: 50 GB SSD
- **Production (Medium Scale)**:
  - CPU: 16 cores
  - RAM: 32 GB
  - Storage: 100 GB SSD
- **Production (Large Scale)**:
  - CPU: 32+ cores
  - RAM: 64+ GB
  - Storage: 200+ GB SSD

### Network Requirements
- **Ports** (adjust based on deployment):
  - 8000: Backend API (internal)
  - 80: API Gateway / HTTP
  - 443: HTTPS (when TLS terminated at ingress)
  - 3000: Frontend (when exposed directly)
  - 9090: Prometheus metrics
  - 16686: Jaeger UI (for distributed tracing)
  - 5601: Kibana (for log viewing)
  - 9200: Elasticsearch (for logs)
  - 6379: Redis
  - 5432: PostgreSQL
  - 11434: Ollama

### Required Services
- **PostgreSQL**: 15+ (for agent state and metadata)
- **Redis**: 7+ (for caching and session storage)
- **Ollama**: Latest (for local LLM inference)
- **Supabase** (optional): For pgvector memory storage
- **Elasticsearch**: 8+ (for log aggregation)
- **Jaeger**: Latest (for distributed tracing)
- **Prometheus**: Latest (for metrics collection)
- **Grafana**: Latest (for dashboards)
- **Alertmanager**: Latest (for alerting)

## Local Development Setup

### Step 1: Clone Repository
```bash
git clone https://github.com/your-org/rex-agent.git
cd rex-agent
```

### Step 2: Environment Setup
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your local settings
# For local development, most defaults work fine
```

### Step 3: Install Dependencies
#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r dev-requirements.txt  # For development tools
```

#### Frontend
```bash
cd ../frontend
npm install
```

### Step 4: Start Required Services
```bash
# Start infrastructure services
docker-compose -f docker-compose.dev.yml up -d postgres redis ollama

# Verify services are healthy
docker-compose -f docker-compose.dev.yml ps
```

### Step 5: Start Development Servers
#### Backend
```bash
cd backend
# In development mode with auto-reload
python start_server.py --dev
# Or for debugging
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend
```bash
cd ../frontend
npm run dev
```

### Step 6: Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api/v1
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Health Check**: http://localhost:8000/health

### Step 7: Run Tests
```bash
# Backend tests
cd backend
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v

# Frontend tests
cd ../frontend
npm run test:unit
npm run test:e2e
```

## Docker Compose Deployment

### Development Docker Compose
Use `docker-compose.dev.yml` for development with hot-reloading and debugging capabilities.

### Production Docker Compose
Use `docker-compose.yml` for production-like deployment with optimized images.

#### Step 1: Prepare Environment
```bash
# Copy production environment example
cp .env.example .env.production

# Edit .env.production with production values:
# - Set strong passwords for databases
# - Configure Ollama models
# - Adjust resource limits
# - Set appropriate timeouts
```

#### Step 2: Deploy Stack
```bash
docker-compose -f docker-compose.yml --env-file .env.production up -d
```

#### Step 3: Verify Deployment
```bash
# Check all services are running
docker-compose -f docker-compose.yml ps

# Check logs for any errors
docker-compose -f docker-compose.yml logs -f

# Verify health endpoints
curl http://localhost/health
curl http://localhost/api/v1/health
```

#### Step 4: Access the Application
- **Frontend**: http://localhost
- **Backend API**: http://localhost/api/v1
- **API Docs**: http://localhost/docs
- **Metrics**: http://localhost:9090/metrics
- **Health Check**: http://localhost/health

#### Step 5: Scale Services (Optional)
```bash
# Scale searcher agents to 5 instances
docker-compose -f docker-compose.yml up -d --scale searcher-agent=5

# Scale synthesizer agents to 4 instances
docker-compose -f docker-compose.yml up -d --scale synthesizer-agent=4
```

### Docker Compose File Explanation

#### Key Services
- **postgres**: PostgreSQL database for persistent storage
- **redis**: Redis for caching and session storage
- **ollama**: Ollama service for local LLM inference
- **agent-registry**: Central agent registration and discovery service
- **planner-agent, searcher-agent, etc.**: Specialized agent services
- **api-gateway**: Nginx-based API gateway and load balancer
- **frontend**: Next.js frontend application
- **prometheus**: Metrics collection and storage
- **grafana**: Dashboard visualization
- **elasticsearch**: Log storage and search
- **kibana**: Log visualization interface

#### Volumes
- **postgres_data**: Persistent PostgreSQL data
- **ollama_data**: Ollama models and data
- **prometheus_data**: Prometheus metrics storage
- **grafana_data**: Grafana dashboards and configuration

#### Networks
- **backend**: Internal service communication
- **frontend**: Frontend access
- **monitoring**: Monitoring and observability services

## Kubernetes Deployment

### Step 1: Prepare Namespace and Secrets
```bash
# Create namespace
kubectl create namespace rex-research

# Create secrets from literal values or files
kubectl create secret generic rex-secrets \
  --namespace rex-research \
  --from-literal=SUPABASE_URL="your-supabase-url" \
  --from-literal=SUPABASE_KEY="your-supabase-key" \
  --from-literal=REDIS_URL="redis://redis-service.rex-research.svc.cluster.local:6379" \
  --from-literal=N8N_WEBHOOK_SECRET="your-webhook-secret" \
  --from-literal=JWT_SECRET="your-jwt-secret-256-bit" \
  --from-literal=POSTGRES_PASSWORD="secure-postgres-password" \
  --from-literal=POSTGRES_USER="rex_user" \
  --from-literal=POSTGRES_DB="rex_db"

# Optional: Create TLS secrets for HTTPS
kubectl create secret tls rex-tls \
  --namespace rex-research \
  --cert=/path/to/tls.crt \
  --key=/path/to/tls.key
```

### Step 2: Apply ConfigMap
```bash
kubectl apply -f k8s/configmap.yaml -n rex-research
```

### Step 3: Deploy Storage Layer
```bash
# Deploy PostgreSQL (using Helm chart or manual)
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install rex-postgres bitnami/postgresql \
  --namespace rex-research \
  --set auth.username=rex_user \
  --set auth.password=secure-postgres-password \
  --set auth.database=rex_db \
  --set primary.persistence.size=20Gi

# Deploy Redis
helm install rex-redis bitnami/redis \
  --namespace rex-research \
  --set architecture=standalone \
  --set auth.password=redis-password \
  --set persistence.size=5Gi

# Deploy Ollama (community chart or manual)
# Note: Ollama doesn't have an official Helm chart, use community or manual deployment
```

### Step 4: Deploy Core Services
```bash
# Apply all Kubernetes manifests
kubectl apply -f k8s/ -n rex-research

# Or deploy incrementally
kubectl apply -f k8s/deployment-agent-registry.yaml -n rex-research
kubectl apply -f k8s/deployment-planner-agent.yaml -n rex-research
kubectl apply -f k8s/deployment-searcher-agent.yaml -n rex-research
# ... continue for all agent types
kubectl apply -f k8s/service-api-gateway.yaml -n rex-research
kubectl apply -f k8s/service-frontend.yaml -n rex-research
kubectl apply -f k8s/hpa-planner-agent.yaml -n rex-research
# ... continue for all HPAs
```

### Step 5: Verify Deployment
```bash
# Check all pods are running
kubectl get pods -n rex-research

# Check services
kubectl get services -n rex-research

# Check ingress (if configured)
kubectl get ingress -n rex-research

# Test health endpoint
kubectl port-forward svc/api-gateway 8080:80 -n rex-research &
curl http://localhost:8080/health

# Access frontend
kubectl port-forward svc/frontend 3000:3000 -n rex-research &
# Then visit http://localhost:3000 in browser
```

### Step 6: Configure Monitoring
```bash
# Deploy Prometheus Operator (if not already present)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install rex-prometheus prometheus-community/kube-prometheus-stack \
  --namespace rex-research \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false

# Deploy Elasticsearch, Fluentd, Kibana (EFK stack)
# Or use your preferred logging solution
```

## Helm Chart Deployment

### Step 1: Prepare Values File
```bash
# Copy example values file
cp helm-chart/values.example.yaml helm-chart/values.production.yaml

# Edit values.production.yaml with your settings:
# - replica counts for each agent type
# - resource limits and requests
# - image tags and pull policies
# - service configurations
# - ingress settings
# - monitoring configurations
```

### Step 2: Install Release
```bash
# Add repository if needed (for local chart, use path)
helm install rex-research ./helm-chart \
  --namespace rex-research \
  --create-namespace \
  -f helm-chart/values.production.yaml
```

### Step 3: Verify Installation
```bash
# Check release status
helm status rex-research -n rex-research

# List deployed resources
helm list -n rex-research
kubectl get all -n rex-research

# Test deployment
kubectl port-forward svc/rex-research-api-gateway 8080:80 -n rex-research &
curl http://localhost:8080/health
```

### Step 4: Upgrade Release
```bash
# Make changes to values file or chart
# Then upgrade
helm upgrade rex-research ./helm-chart \
  --namespace rex-research \
  -f helm-chart/values.production.yaml
```

### Step 5: Uninstall Release
```bash
helm uninstall rex-research -n rex-research
# Remember to manually delete PVCs if needed:
# kubectl delete pvc -n rex-research --all
```

## Configuration Management

### Hierarchical Configuration Approach
REX uses a layered configuration approach:
1. **Defaults**: Hardcoded defaults in code
2. **Environment Variables**: Override defaults
3. **Configuration Files**: Optional JSON/YAML files
4. **Consul/Etcd**: Distributed configuration (enterprise)
5. **Runtime Overrides**: API-based configuration changes

### Environment Variables Reference
See `API_REFERENCE.md` for complete list, but key ones include:

#### Core Settings
- `API_HOST`: Backend host (default: 0.0.0.0)
- `API_PORT`: Backend port (default: 8000)
- `FRONTEND_PORT`: Frontend port (default: 3000)
- `ENVIRONMENT`: development|staging|production

#### LLM Settings
- `OLLAMA_HOST`: Ollama service URL
- `PLANNER_MODEL`: Model for planning agent
- `REPORT_MODEL`: Model for report generation
- `LLM_TIMEOUT`: Seconds before LLM timeout (default: 180)

#### Search Settings
- `MAX_SEARCH_WORKERS`: Parallel search workers (default: 8)
- `SEARCHER_TIMEOUT`: Overall search timeout (default: 60s)
- `QUERY_TIMEOUT`: Per-query timeout (default: 15s)
- `CACHE_ENABLED`: Enable/disable caching (default: true)
- `CACHE_TTL`: Cache TTL in seconds (default: 86400)

#### Security Settings
- `API_KEY_REQUIRED`: Require API key authentication (default: false)
- `JWT_SECRET`: Secret for JWT signing
- `RATE_LIMIT_ENABLED`: Enable rate limiting (default: true)
- `RATE_LIMIT_REQUESTS_PER_MINUTE`: Requests per minute (default: 100)
- `CORS_ORIGINS`: Comma-separated list of allowed origins

#### Agent Orchestration
- `AGENT_REGISTRY_ENABLED`: Enable agent registry (default: true)
- `AGENT_HEARTBEAT_TIMEOUT`: Seconds before agent considered stale (default: 300)
- `MAX_CONCURRENT_AGENTS`: Maximum total agents (default: 21)
- `LOAD_BALANCING_STRATEGY`: round_robin|least_loaded|weighted

#### Monitoring Settings
- `ENABLE_TRACING`: Enable distributed tracing (default: false)
- `TRACING_ENDPOINT`: Jaeger endpoint (host:port)
- `LOG_LEVEL`: DEBUG|INFO|WARN|ERROR
- `ENABLE_METRICS`: Enable Prometheus metrics (default: true)
- `METRICS_PORT`: Port for metrics endpoint (default: 9090)

#### Storage Settings
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase anon/public key
- `REDIS_URL`: Redis connection string
- `DATABASE_URL`: PostgreSQL connection string

#### n8n Integration
- `N8N_ENABLED`: Enable n8n webhook integration (default: false)
- `N8N_WEBHOOK_URL`: n8n webhook URL
- `N8N_WEBHOOK_SECRET`: Secret for webhook verification
- `N8N_TIMEOUT`: Webhook timeout in seconds (default: 30)

### Configuration Validation
On startup, the system validates critical configuration:
- Required variables are present
- Values are within acceptable ranges
- Dependent variables are consistent
- Invalid configuration causes startup failure with clear error message

Example validation in `backend/config/validation.py`:
```python
def validate_configuration(settings):
    errors = []
    
    # Check required services in production
    if settings.ENVIRONMENT == "production":
        if not settings.SUPABASE_URL and not settings.DATABASE_URL:
            errors.append("Either SUPABASE_URL or DATABASE_URL must be set in production")
        
        if not settings.JWT_SECRET or len(settings.JWT_SECRET) < 32:
            errors.append("JWT_SECRET must be at least 32 characters in production")
        
        if settings.API_KEY_REQUIRED and not settings.API_KEYS:
            errors.append("API_KEY_REQUIRED is true but no API_KEYS configured")
    
    # Validate numeric ranges
    if settings.LLM_TIMEOUT < 30:
        errors.append("LLM_TIMEOUT must be at least 30 seconds")
    
    if settings.MAX_SEARCH_WORKERS < 1 or settings.MAX_SEARCH_WORKERS > 32:
        errors.append("MAX_SEARCH_WORKERS must be between 1 and 32")
    
    if settings.AGENT_HEARTBEAT_TIMEOUT < 30:
        errors.append("AGENT_HEARTBEAT_TIMEOUT must be at least 30 seconds")
    
    if errors:
        raise ConfigurationError(f"Configuration validation failed: {', '.join(errors)}")
    
    return True
```

## Security Hardening

### Network Security
1. **Service Mesh** (Optional but recommended for production):
   - Install Istio or Linkerd for mutual TLS
   - Configure authorization policies
   - Implement rate limiting at mesh level

2. **Network Policies** (Kubernetes):
   ```yaml
   # Example: Deny all ingress by default
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: deny-all-ingress
     namespace: rex-research
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
   ```

3. **Ingress Controls**:
   - Use cloud provider LB or ingress-nginx with WAF
   - Implement IP whitelisting for admin endpoints
   - Use geographic restrictions where appropriate
   - Implement bot management

### Application Security
1. **Input Validation**:
   - All API endpoints use Pydantic models for validation
   - Custom validators for complex business rules
   - Sanitization of user inputs to prevent injection
   - Length limits on all string fields

2. **Output Encoding**:
   - HTML escaping in templates where user data is displayed
   - JSON encoding for API responses
   - Proper content-type headers

3. **Authentication & Authorization**:
   - JWT-based authentication with refresh tokens
   - Role-Based Access Control (RBAC)
   - API key support for service-to-service communication
   - Session management with proper expiration
   - Password hashing with bcrypt/scrypt for any user passwords

4. **Security Headers**:
   ```python
   # Example middleware
   @app.middleware("http")
   async def add_security_headers(request, call_next):
       response = await call_next(request)
       response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
       response.headers["X-Content-Type-Options"] = "nosniff"
       response.headers["X-Frame-Options"] = "DENY"
       response.headers["X-XSS-Protection"] = "1; mode=block"
       response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
       response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
       return response
   ```

### Data Protection
1. **Encryption at Rest**:
   - PostgreSQL: Transparent Data Encryption (TDE) or pgcrypto
   - Redis: Encrypted Redis or application-level encryption
   - File storage: Encrypted volumes or S3 with SSE-S3/SSE-KMS
   - Backups: Always encrypted with key management

2. **Encryption in Transit**:
   - TLS 1.3 for all service communication
   - Mutual TLS for service-to-service (when using service mesh)
   - HTTPS for all external endpoints
   - SSH for administrative access

3. **Key Management**:
   - Use cloud KMS (AWS KMS, Azure Key Vault, Google Cloud KMS)
   - HashiCorp Vault for on-premises
   - Regular key rotation (90-day cycle recommended)
   - Separation of duties for key access

### Monitoring & Alerting for Security
1. **Security-Focused Metrics**:
   - Failed authentication attempts
   - Authorization failures
   - Input validation errors
   - Rate limiting triggers
   - Suspicious request patterns

2. **Log Monitoring**:
   - Centralized logging with security event tagging
   - Real-time alerting on security events
   - Regular log review procedures
   - Retention of security logs for compliance

3. **Vulnerability Management**:
   - Regular dependency scanning (OWASP Dependency-Check, Snyk)
   - Container image scanning (Trivy, Clair)
   - Infrastructure as Code scanning (Checkov, tfsec)
   - Regular penetration testing (quarterly recommended)
   - Bug bounty program (optional but recommended)

## Monitoring & Observability Setup

### Metrics Collection (Prometheus)
1. **Backend Metrics**:
   - Automatic instrumentation of FastAPI endpoints
   - Custom metrics for agent operations
   - Business metrics (job completion rates, etc.)
   - Resource utilization metrics

2. **Service Discovery**:
   - Prometheus scrapes Kubernetes services via ServiceMonitor
   - For non-Kubernetes deployments, use static configs or file SD

3. **Recording Rules**:
   ```yaml
   # Example recording rules for common queries
   groups:
   - name: rex-research.rules
     interval: 30s
     rules:
     - record: job:research_duration:avg5m
       expr: avg_over_time(research_duration_seconds[5m])
     - record: agent:load:avg_by_type
       expr: avg by(agent_type) (agent_load)
   ```

### Distributed Tracing (Jaeger)
1. **Instrumentation**:
   - Automatic instrumentation of HTTP clients/requests
   - Manual spans for complex operations
   - Context propagation across service boundaries
   - Baggage for carrying user/context information

2. **Sampling Strategies**:
   - Adaptive sampling based on traffic
   - Rate-limiting sampling for high-volume services
   - Probabilistic sampling with dynamic adjustment

3. **Storage**:
   - Jaeger uses Cassandra or Elasticsearch for storage
   - Configure appropriate retention (typically 7-30 days)
   - Monitor storage usage and set up alerts

### Log Aggregation (ELK/EFK Stack)
1. **Log Collection**:
   - Fluentd/Fluent Bit agents on each node
   - Application logs via stdout/stderr (container best practice)
   - Structured logging in JSON format
   - Include trace IDs and span IDs for correlation

2. **Indexing Strategy**:
   - Daily indices: rex-logs-YYYY.MM.DD
   - Index lifecycle management (ILM) policies
   - Rollover after size/time threshold
   - Delete old indices based on retention policy

3. **Dashboards**:
   - Pre-built dashboards for common views
   - Custom dashboards for specific use cases
   - Alerting based on log patterns
   - Log exploration and search capabilities

### Visualization (Grafana)
1. **Dashboard Provisioning**:
   - Use Grafana's provisioning system for consistent dashboards
   - Store dashboard definitions in version control
   - Automatically apply on startup

2. **Key Dashboards**:
   - System Overview: Overall health and performance
   - Agent Performance: Per-agent metrics and load
   - Research Workflow: End-to-end job metrics
   - Resource Utilization: CPU, memory, disk, network
   - Error Analysis: Error rates and patterns
   - Business Metrics: Job completion, user activity, etc.

3. **Alerting Rules**:
   - Define rules in Grafana or Alertmanager
   - Notification channels: email, Slack, PagerDuty, webhook
   - Escalation policies and routing
   - Silence and inhibition rules

### Health Checks
1. **Liveness Probes**:
   - Determine if container should be restarted
   - Simple endpoint that indicates basic liveness
   - Example: `/health/liveness` - returns 200 if process is running

2. **Readiness Probes**:
   - Determine if container should receive traffic
   - Checks dependencies and internal readiness
   - Example: `/health/readiness` - checks DB, cache, etc.

3. **Startup Probes**:
   - For slow-starting applications
   - Gives extra time during initial startup
   - Disables liveness/readiness checks until success

### Example Health Endpoints
```python
# In backend/main.py or health module
@app.get("/health/liveness")
async def liveness_check():
    """Simple liveness check - just verifies the process is running"""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health/readiness")
async def readiness_check():
    """Readiness check - verifies dependencies are available"""
    checks = []
    overall_status = "ready"
    
    # Check database
    try:
        # Simple query to verify DB connection
        db.execute("SELECT 1")
        checks.append({"name": "database", "status": "passed"})
    except Exception as e:
        checks.append({"name": "database", "status": "failed", "message": str(e)})
        overall_status = "not ready"
    
    # Check Redis
    try:
        redis.ping()
        checks.append({"name": "redis", "status": "passed"})
    except Exception as e:
        checks.append({"name": "redis", "status": "failed", "message": str(e)})
        overall_status = "not ready"
    
    # Check Ollama
    try:
        # Simple request to verify Ollama is responding
        response = requests.get(f"{settings.OLLAMA_HOST}/api/version", timeout=5)
        if response.status_code == 200:
            checks.append({"name": "ollama", "status": "passed"})
        else:
            checks.append({"name": "ollama", "status": "failed", "message": f"HTTP {response.status_code}"})
            overall_status = "not ready"
    except Exception as e:
        checks.append({"name": "ollama", "status": "failed", "message": str(e)})
        overall_status = "not ready"
    
    status_code = 200 if overall_status == "ready" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

## Backup & Disaster Recovery

### Backup Strategy
#### Database Backups (PostgreSQL)
```bash
# Logical backup (pg_dump)
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backups/rex/postgres"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/rex_postgres_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Create logical backup
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
  -h "${POSTGRES_HOST}" \
  -U "${POSTGRES_USER}" \
  -d "${POSTGRES_DB}" \
  | gzip > "$BACKUP_FILE"

# Verify backup
gunzip -t "$BACKUP_FILE"

# Apply retention
find "$BACKUP_DIR" -name "rex_postgres_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "PostgreSQL backup completed: $BACKUP_FILE"
```

```bash
# Physical backup (pg_basebackup) - for point-in-time recovery
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backups/rex/postgres_base"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR_SPECIFIC="${BACKUP_DIR}/baseback_${TIMESTAMP}"
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

# Create base backup
PGPASSWORD="${POSTGRES_PASSWORD}" pg_basebackup \
  -h "${POSTGRES_HOST}" \
  -U "${POSTGRES_USER}" \
  -D "$BACKUP_DIR_SPECIFIC" \
  -Ft \
  -z \
  -P \
  -R

# Apply retention (keep base backups and WAL archives)
find "$BACKUP_DIR" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} +

echo "PostgreSQL base backup completed: $BACKUP_DIR_SPECIFIC"
```

#### Redis Backups
```bash
# Redis RDB snapshot backup
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backups/rex/redis"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/rex_redis_${TIMESTAMP}.rdb"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Trigger BGSAVE and wait for completion
redis-cli BGSAVE
# Poll until background save is done
while [ "$(redis-cli LASTSAVE)" -eq "$(redis-cli LASTSAVE)" ]; do
  sleep 1
done

# Copy the RDB file
# Note: In containerized environment, you may need to exec into container
docker exec redis-container cp /data/dump.rdb "$BACKUP_FILE"

# Apply retention
find "$BACKUP_DIR" -name "rex_redis_*.rdb" -mtime +$RETENTION_DAYS -delete

echo "Redis backup completed: $BACKUP_FILE"
```

#### Application Data Backups
```bash
# Backup uploads, exports, configurations
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backups/rex/application"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/rex_application_${TIMESTAMP}.tar.gz"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Backup application data
tar -czf "$BACKUP_FILE" \
  --exclude='*.log' \
  ./backend/uploads/ \
  ./backend/exports/ \
  ./backend/.env \
  ./frontend/.env.local \
  ./backend/agents/ \
  ./backend/config/

# Apply retention
find "$BACKUP_DIR" -name "rex_application_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Application backup completed: $BACKUP_FILE"
```

### Disaster Recovery Procedures

#### RPO/RTO Targets
- **RPO (Recovery Point Objective)**: 4 hours
- **RTO (Recovery Time Objective)**: 2 hours

#### Recovery Steps
1. **Assessment Phase** (0-15 minutes):
   - Determine scope and cause of outage
   - Verify backup availability and integrity
   - Notify stakeholders
   - Prepare recovery environment

2. **Infrastructure Provisioning** (15-45 minutes):
   - Provision new infrastructure or use standby
   - Configure networking and security
   - Install required software (Docker, kubectl, etc.)

3. **Data Restoration** (45-105 minutes):
   - Restore PostgreSQL from latest backup
   - Apply WAL archives for PITR if needed
   - Restore Redis data
   - Restore application data and configurations
   - Verify data integrity

4. **Service Restoration** (105-135 minutes):
   - Start infrastructure services in dependency order
   - Validate service health
   - Deploy application services
   - Verify service-to-service communication

5. **Validation Phase** (135-150 minutes):
   - Run smoke tests
   - Validate end-to-end functionality
   - Check performance baselines
   - Confirm data consistency

6. **Cutover** (150-165 minutes):
   - Update DNS/load balancer to point to recovered system
   - Monitor for issues
   - Notify stakeholders of completion

7. **Post-Recovery** (165+ minutes):
   - Conduct detailed incident review
   - Update recovery procedures based on lessons learned
   - Replenish any consumed backup resources
   - Implement preventive measures

#### Backup Validation Schedule
- **Daily**: Verify backup completion logs
- **Weekly**: Test restore of non-critical data
- **Monthly**: Full restore test to isolated environment
- **Quarterly**: Disaster recovery drill
- **Annually**: Comprehensive DR test with business stakeholders

### Point-in-Time Recovery (PostgreSQL)
```bash
# For recovering to specific timestamp
#!/bin/bash
set -euo pipefail

# Parameters
TARGET_TIME="2026-08-26 10:30:00"  # UTC time to recover to
BACKUP_BASE="/backups/rex/postgres_base"
WAL_ARCHIVE="/var/lib/postgresql/wal_archive"
DATA_DIR="/var/lib/postgresql/data"
POSTGRES_USER="rex_user"
POSTGRES_DB="rex_db"

# Stop PostgreSQL service
systemctl stop postgresql

# Clear data directory
rm -rf "$DATA_DIR"/*
mkdir -p "$DATA_DIR"

# Copy latest base backup
LATEST_BACKUP=$(ls -t "$BACKUP_BASE" | head -n 1)
cp -r "$BACKUP_BASE/$LATEST_BACKUP"/* "$DATA_DIR/"

# Create recovery.conf
cat > "$DATA_DIR/recovery.conf" <<EOF
restore_command = 'cp $WAL_ARCHIVE/%f %p'
recovery_target_time = '$TARGET_TIME'
recovery_target_action = 'pause'
EOF

# Set proper ownership
chown -R postgres:postgres "$DATA_DIR"

# Start PostgreSQL
systemctl start postgresql

# Verify recovery
# After startup, check that recovery reached target time
# Then promote to primary if needed
pg_ctl promote -D "$DATA_DIR"

# Remove recovery.conf after promotion
rm -f "$DATA_DIR/recovery.conf"

echo "Point-in-time recovery completed to $TARGET_TIME"
```

## Scaling Procedures

### Horizontal Scaling (Adding Agent Instances)
#### Docker Compose
```bash
# Scale searcher agents from 5 to 8
docker-compose -f docker-compose.yml up -d --scale searcher-agent=8

# Verify new instances are healthy
docker-compose -f docker-compose.yml ps
docker-compose -f docker-compose.yml logs -f searcher-agent
```

#### Kubernetes
```bash
# Scale planner deployment from 3 to 5 replicas
kubectl scale deployment planner-agent --replicas=5 -n rex-research

# Verify rollout
kubectl rollout status deployment/planner-agent -n rex-research
kubectl get pods -l app=planner-agent -n rex-research

# Or use declarative approach (edit deployment yaml)
# kubectl apply -f k8s/deployment-planner-agent.yaml -n rex-research
```

#### Helm Chart
```bash
# Update values file to increase replica count
# Edit helm-chart/values.production.yaml:
# plannerAgent:
#   replicaCount: 5  # changed from 3
# searcherAgent:
#   replicaCount: 8  # changed from 5

# Then upgrade
helm upgrade rex-research ./helm-chart \
  --namespace rex-research \
  -f helm-chart/values.production.yaml
```

### Vertical Scaling (Increasing Resources per Instance)
#### Docker Compose
```bash
# Edit docker-compose.yml to increase resources
# For example, increase searcher agent memory:
# searcher-agent:
#   deploy:
#     resources:
#       limits:
#         cpus: "3.0"  # increased from 2.0
#         memory: "6GB"  # increased from 4GB

# Then restart services
docker-compose -f docker-compose.yml up -d --force-recreate searcher-agent
```

#### Kubernetes
```bash
# Edit deployment to increase resources
# In k8s/deployment-searcher-agent.yaml:
# resources:
#   requests:
#     memory: "2Gi"  # increased from 1Gi
#     cpu: "1000m"   # increased from 500m
#   limits:
#     memory: "4Gi"  # increased from 2Gi
#     cpu: "2000m"   # increased from 1000m

# Apply changes
kubectl apply -f k8s/deployment-searcher-agent.yaml -n rex-research
# This triggers a rolling update
```

### Database Scaling
#### PostgreSQL Read Replicas
```bash
# Using Bitnami PostgreSQL chart with replication
helm install rex-postgres-primary bitnami/postgresql \
  --namespace rex-research \
  --set architecture=replication \
  --set replica.replicaCount=2 \
  --set auth.username=rex_user \
  --set auth.password=secure-postgres-password \
  --set auth.database=rex_db

# Application needs to be configured to use:
# - Primary for writes: rex-postgres-primary
# - Reads can be load-balanced across primary and replicas
```

#### Connection Pooling
- Use PgBouncer or similar for connection pooling
- Configure appropriate pool sizes based on concurrent agents
- Monitor pool usage and adjust as needed

### Caching Scaling
#### Redis Cluster
```bash
# For production, consider Redis Cluster
helm install rex-redis bitnami/redis-cluster \
  --namespace rex-research \
  --set cluster.enabled=true \
  --set cluster.nodeCount=6 \
  --set auth.password=redis-password
```

#### Cache Warming Strategies
- Pre-populate cache with common queries during off-peak hours
- Implement cache-aside or read-through patterns
- Monitor cache hit rates and adjust TTL values
- Use cache tags or namespaces for selective invalidation

## Troubleshooting

### Common Issues and Solutions

#### 1. Container Fails to Start
**Symptoms**: Container exits immediately, CrashLoopBackOff in K8s
**Diagnosis**:
```bash
# Docker Compose
docker-compose logs -f <service-name>

# Kubernetes
kubectl logs <pod-name> -n rex-research
kubectl describe pod <pod-name> -n rex-research
```

**Common Causes**:
- Missing environment variables
- Port conflicts
- Dependency service unavailable
- Configuration errors
- Insufficient resources

**Solutions**:
- Verify all required environment variables are set
- Check for port conflicts with `netstat -tulpn` or `ss -tulpn`
- Ensure dependencies (postgres, redis, ollama) are healthy
- Validate configuration files
- Adjust resource requests/limits

#### 2. Database Connection Errors
**Symptoms**: SQLAlchemy errors, connection timeouts, authentication failures
**Diagnosis**:
```bash
# Test database connectivity
PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "SELECT version();"

# Check Kubernetes service
kubectl get svc postgres -n rex-research
kubectl describe svc postgres -n rex-research
```

**Common Causes**:
- Incorrect connection string
- Database not running or inaccessible
- Authentication failure
- Network policies blocking access
- Connection pool exhaustion

**Solutions**:
- Verify connection parameters in environment variables
- Check database service status and endpoints
- Reset passwords if needed
- Review network policies and security groups
- Increase max_connections in PostgreSQL config
- Implement connection pooling

#### 3. Ollama Connection Issues
**Symptoms**: LLM timeout errors, connection refused, model not found
**Diagnosis**:
```bash
# Test Ollama connectivity
curl -f http://localhost:11434/api/version
curl -f http://localhost:11434/api/tags  # List available models
curl -f http://localhost:11434/api/generate -d '{"model": "phi3:mini", "prompt": "test", "stream": false}'

# Check container status
docker-compose logs -f ollama
# or
kubectl logs -l app=ollama -n rex-research
```

**Common Causes**:
- Ollama service not running
- Model not pulled or not available
- Insufficient resources (RAM/VRAM) for model
- Network connectivity issues
- Incorrect OLLAMA_HOST configuration

**Solutions**:
- Ensure Ollama service is running
- Pull required models: `ollama pull phi3:mini` and `ollama pull qwen2.5:3b`
- Check system resources (especially RAM)
- Verify network policies allow access to Ollama service
- Correct OLLAMA_HOST environment variable
- Consider using smaller models if resources are limited

#### 4. Search API Failures
**Symptoms**: Empty search results, timeout errors, API errors
**Diagnosis**:
```bash
# Test individual search APIs
# Example for DuckDuckGo (no key needed)
curl -f "https://api.duckduckgo.com/?q=test&format=json"

# Check backend logs for specific API errors
docker-compose logs -f backend | grep -i "search\|api\|timeout"
# or
kubectl logs -l app=backend -n rex-research | grep -i "search\|api\|timeout"
```

**Common Causes**:
- API key missing or invalid
- Rate limiting by search provider
- Network connectivity issues
- Service-specific outages
- Incorrect timeout configuration
- Proxy or firewall blocking requests

**Solutions**:
- Verify API keys are set correctly in environment variables
- Implement exponential backoff for rate-limited APIs
- Check network connectivity and DNS resolution
- Monitor service status pages for providers
- Adjust timeout values based on observed performance
- Configure proxy settings if required
- Implement fallback mechanisms (multiple API providers)

#### 5. High Memory Usage
**Symptoms**: Container OOMKilled, high memory alerts, swap usage
**Diagnosis**:
```bash
# Check memory usage
docker stats <container-name>
# or
kubectl top pods -n rex-research

# Check for memory leaks in logs
docker-compose logs -f backend | grep -i "memory\|oom\|leak"
# or
kubectl logs -l app=backend -n rex-research | grep -i "memory\|oom\|leak"
```

**Common Causes**:
- Memory leaks in application code
- Insufficient resource limits
- Caching without proper eviction
- Large data processing without streaming
- Retaining references to large objects
- Inefficient data structures or algorithms

**Solutions**:
- Profile application for memory leaks (use memory_profiler, objgraph)
- Increase memory limits if justified by actual usage
- Implement proper cache eviction policies (LRU, LFU)
- Use streaming processing for large datasets
- Ensure objects are properly dereferenced
- Optimize data structures and algorithms
- Consider using Redis for external caching instead of in-memory

#### 6. Performance Degradation
**Symptoms**: Increased response times, low throughput, high latency
**Diagnosis**:
```bash
# Check response times
curl -w "%{time_total}\n" -o /dev/null -s "http://localhost/health"

# Check resource utilization
docker stats
# or
kubectl top pods -n rex-research

# Check for bottlenecks in logs
docker-compose logs -f backend | grep -i "slow\|timeout\|delay"
# or
kubectl logs -l app=backend -n rex-research | grep -i "slow\|timeout\|delay"
```

**Common Causes**:
- Database query performance issues
- Lack of indexing
- Lock contention or deadlocks
- Inefficient algorithms
- Resource saturation (CPU, memory, network, disk)
- External service slowdowns
- Improper caching strategy

**Solutions**:
- Analyze slow queries and add appropriate indexes
- Review and optimize database schema
- Implement query timeout and cancellation
- Profile application for CPU hotspots
- Scale resources based on bottleneck identification
- Monitor external service performance and implement fallbacks
- Review caching strategy and adjust TTL/preloading
- Consider implementing async processing for long-running tasks

#### 7. Communication Failures Between Agents
**Symptoms**: Message loss, delayed processing, timeouts
**Diagnosis**:
```bash
# Check message queue health
# For RabbitMQ
docker-compose logs -f rabbitmq
# or check Kubernetes service

# Check network connectivity between services
kubectl exec <pod-name> -n rex-research -- nc -zv <service-host> <port>

# Check agent logs for communication errors
docker-compose logs -f backend | grep -i "message\|queue\|timeout\|connection"
# or
kubectl logs -l app=backend -n rex-research | grep -i "message\|queue\|timeout\|connection"
```

**Common Causes**:
- Message queue not running or unhealthy
- Network policies blocking inter-service communication
- Message serialization/deserialization errors
- Message size limits exceeded
- Consumer processing too slowly
- Dead letter queues filling up
- Incorrect routing keys or bindings

**Solutions**:
- Verify message queue service health
- Review and adjust network policies
- Implement proper error handling for serialization
- Check and increase message size limits if needed
- Scale consumers based on processing time
- Monitor and clean dead letter queues
- Verify routing configuration and bindings
- Consider implementing idempotency for message processing

## Upgrade Procedures

### Pre-Upgrade Checklist
1. **Review Changelog**: Read release notes for breaking changes
2. **Backup**: Perform full backup of all data
3. **Test Environment**: Test upgrade in staging environment first
4. **Rollback Plan**: Ensure rollback procedure is tested and ready
5. **Notify Stakeholders**: Inform users of planned maintenance window
6. **Check Dependencies**: Verify compatibility with dependent services
7. **Resource Planning**: Ensure adequate resources for upgrade process
8. **Security Scan**: Run security scan on new version before deployment

### Minor Version Upgrade (e.g., 2.0.x → 2.1.x)
#### Docker Compose
```bash
# Pull new images
docker-compose pull

# Stop services
docker-compose down

# Backup data (if volumes used)
# For named volumes, backup the actual data directory

# Start new version
docker-compose up -d

# Verify services
docker-compose ps
docker-compose logs -f

# Run smoke tests
# Check health endpoints
# Test basic functionality
```

#### Kubernetes
```bash
# Option 1: Update image tags in deployment manifests
# Edit k8s/deployment-*.yaml files to new image tags
# Then apply
kubectl apply -f k8s/ -n rex-research

# Option 2: Use Helm upgrade with new values
# If using Helm chart with image tags in values
helm upgrade rex-research ./helm-chart \
  --namespace rex-research \
  -f helm-chart/values.production.yaml \
  --set image.tag=new-version-tag

# Monitor rollout
kubectl rollout status deployment/<deployment-name> -n rex-research
kubectl get pods -n rex-research

# Run smoke tests
```

#### Helm Chart
```bash
# If chart version changed
helm repo update
helm upgrade rex-research ./helm-chart \
  --namespace rex-research \
  -f helm-chart/values.production.yaml

# Monitor and test as above
```

### Major Version Upgrade (e.g., 2.x → 3.x)
Major upgrades may involve:
- Database schema changes
- Breaking API changes
- Configuration format changes
- Dependency updates
- Architecture changes

#### General Procedure
1. **Read Migration Guide**: Thoroughly review the official migration guide
2. **Full Backup**: Perform verified backup of all systems
3. **Staging Test**: Execute upgrade in identical staging environment
4. **Schema Migration**: Run any required database migrations
5. **Configuration Update**: Update configuration files as required
6. **Dependency Check**: Verify all dependencies meet new requirements
7. **Canary Deployment**: Deploy to small subset of production traffic
8. **Gradual Rollout**: Increase traffic to new version gradually
9. **Full Cutover**: Switch all traffic to new version
10. **Post-Upgrade Validation**: Comprehensive testing and monitoring

#### Database Migration Example
```bash
# Assuming migration scripts are provided
#!/bin/bash
set -euo pipefail

# Backup first
./backup-database.sh

# Run migration scripts in order
# These would be provided with the release
for migration in ./migrations/*.sql; do
  echo "Applying migration: $migration"
  PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -f "$migration"
done

# Verify migration
echo "Running post-migration verification..."
# Run verification scripts or manual checks

echo "Database migration completed successfully"
```

### Configuration Migration
When configuration format changes:
```bash
# Example: Converting from .env to YAML or vice versa
#!/bin/bash
set -euo pipefail

# Backup original
cp .env .env.backup.timestamp

# Use migration tool or script
# This would be provided with the release
python migrate_config.py --input .env --output config.yaml

# Verify conversion
diff -u <(./validate_config.py .env) <(./validate_config.py config.yaml)

# Replace original
mv config.yaml .env
```

## Rollback Procedures

### When to Rollback
- Critical errors affecting core functionality
- Security vulnerabilities introduced
- Data corruption or loss
- Performance degradation beyond acceptable thresholds
- Failed health checks across multiple instances
- Rollback triggered by monitoring/alerting

### Rollback Decision Criteria
1. **Impact Assessment**: How many users/systems affected?
2. **Severity**: Is it causing data loss, security issues, or major outage?
3. **Recovery Time**: Can fix be deployed faster than rollback?
4. **Risk**: Does rollback introduce additional risk?
5. **Stakeholder Input**: Input from product, security, ops teams

### Docker Compose Rollback
```bash
# Assuming you kept previous images or have them in registry
# Stop current version
docker-compose down

# If using tagged images and want to revert to specific tag:
# Edit docker-compose.yml to change image tags back
# searcher-agent:
#   image: rex-backend:previous-tag  # instead of current-tag

# Start previous version
docker-compose up -d

# Verify services are healthy
docker-compose ps
docker-compose logs -f

# Run validation tests
```

### Kubernetes Rollback
```bash
# Option 1: Rollback to previous deployment revision
kubectl rollout undo deployment/<deployment-name> -n rex-research
# To rollback to specific revision:
# kubectl rollout undo deployment/<deployment-name> --to-revision=3 -n rex-research

# Monitor rollback
kubectl rollout status deployment/<deployment-name> -n rex-research
kubectl get pods -n rex-research

# Option 2: Manually apply previous manifests
# If you have Git history or saved manifests
kubectl apply -f k8s/previous-version/ -n rex-research

# Option 3: Helm rollback
# If using Helm
helm rollback rex-research <revision-number> -n rex-research
# To rollback to previous revision:
# helm rollback rex-research -n rex-research

# Monitor and test
```

### Helm Chart Rollback
```bash
# Rollback to previous release
helm rollback rex-research -n rex-research

# Or to specific revision
helm rollback rex-research <revision-number> -n rex-research

# Verify rollout
helm status rex-research -n rex-research
kubectl get pods -n rex-research

# Run validation tests
```

### Data Rollback (when applicable)
```bash
# For logical backups
#!/bin/bash
set -euo pipefail

# Stop services to prevent further changes
# In production, consider doing this during maintenance window
docker-compose down
# or scale to zero in K8s

# Restore database from backup
# Assuming backup file is rex_postgres_20260826_103000.sql.gz
gunzip -c /backups/rex/postgres/rex_postgres_20260826_103000.sql.gz |
  PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}"

# Restore Redis data if applicable
# Copy RDB file to Redis data directory and restart

# Restart services
docker-compose up -d
# or scale back to desired replica count in K8s

# Verify data integrity and application functionality
echo "Data rollback completed"
```

## Operational Runbooks

### Daily Operations Checklist
```markdown
# Daily Operations Checklist for REX System

## Morning Checks (Start of Shift)
[ ] Verify all services are healthy:
    - kubectl get pods -n rex-research (no CrashLoopBackOff)
    - kubectl get services -n rex-research (all have endpoints)
    - curl http://<lb-address>/health (returns healthy)

[ ] Check key metrics:
    - Grafana dashboard shows normal patterns
    - No critical alerts firing
    - Job completion rates within expected range

[ ] Review overnight logs:
    - No recurring errors in application logs
    - No security alerts in security logs
    - Backup jobs completed successfully

[ ] Check resource utilization:
    - CPU, memory, disk, network within normal ranges
    - No signs of resource exhaustion
    - Autoscaling behaving as expected

## Ongoing Monitoring
[ ] Monitor alerting systems:
    - Acknowledge and respond to alerts per runbook
    - Escalate when necessary per escalation policy

[ ] Check for deployment activities:
    - Verify any scheduled deployments completed successfully
    - Monitor for post-deployment anomalies

[ ] Validate backup status:
    - Confirm last backup completed successfully
    - Verify backup integrity if possible

[ ] Check capacity planning indicators:
    - Review trends in resource usage
    - Note any approaching limits

## Evening Checks (End of Shift)
[ ] Verify system stability:
    - No increasing error rates
    - No degrading performance trends
    - All services responsive

[ ] Prepare handoff notes:
    - Document any ongoing investigations
    - Note any pending actions or follow-ups
    - Highlight any areas of concern for next shift

[ ] Check security dashboards:
    - Review authentication attempts
    - Check for suspicious activities
    - Verify no policy violations
```

### Incident Response Runbook
```markdown
# Incident Response Runbook for REX System

## Phase 1: Detection (0-5 minutes)
[ ] Alert received from monitoring system
[ ] Initial triage:
    - What is the alert telling us?
    - Which systems are affected?
    - What is the perceived impact?
[ ] Initial assessment:
    - Is this affecting users?
    - Is data at risk?
    - Is this a security incident?
[ ] Notify on-call engineer and team lead
[ ] Create incident channel (Slack, Teams, etc.)
[ ] Start incident timeline documentation

## Phase 2: Analysis (5-20 minutes)
[ ] Gather information:
    - Check monitoring dashboards
    - Review recent logs
    - Check deployment history
    - Verify infrastructure status
[ ] Determine scope:
    - How many users affected?
    - Which services degraded or down?
    - Is this isolated or widespread?
[ ] Form initial hypothesis:
    - What is the likely cause?
    - What evidence supports this?
    - What needs to be verified?
[ ] Decide on investigation approach:
    - Logs vs metrics vs tracing
    - Which services to investigate first
    - Need for reproduction steps?

## Phase 3: Mitigation (20-60 minutes)
[ ] Immediate actions based on hypothesis:
    - Scale resources if resource exhaustion
    - Restart services if stuck or unresponsive
    - Failover to standby if available
    - Block malicious IPs if attack in progress
    - Enable maintenance mode if data corruption suspected
[ ] Communicate status:
    - Update stakeholders every 5-10 minutes
    - Provide estimated time to resolution
    - Be transparent about uncertainty
[ ] Verify mitigation effectiveness:
    - Check if alert conditions are improving
    - Monitor for side effects of mitigation
    - Be prepared to revert if making things worse

## Phase 4: Resolution (60-120 minutes)
[ ] Root cause analysis:
    - Continue investigation until root cause found
    - Verify fix addresses the underlying issue
    - Implement permanent fix
    - Test fix in isolation if possible
[ ] Full system validation:
    - Verify all affected systems restored
    - Check for data integrity or loss
    - Confirm performance returned to baseline
    - Ensure no regression in other areas
[ ] Gradual restoration:
    - If used maintenance mode, gradually restore traffic
    - Monitor for issues during restoration
    - Confirm all systems nominal
[ ] Close incident:
    - Document root cause and resolution
    - Update runbooks if needed
    - Conduct brief retrospective with involved parties
    - Reset monitoring to normal state

## Phase 5: Post-Incident (120+ minutes)
[ ] Detailed retrospective:
    - What happened and why?
    - What did we do well?
    - What could we improve?
    - What are the action items?
[ ] Update documentation:
    - Runbooks, playbooks, architecture docs
    - Configuration guides
    - Troubleshooting guides
[ ] Implement action items:
    - Assign owners and due dates
    - Track to completion
    - Verify effectiveness
[ ] Share learnings:
    - Team meeting or newsletter
    - Blog post or internal wiki
    - Consider external sharing if appropriate
[ ] Archive incident:
    - Store all relevant logs, metrics, and documentation
    - Link to incident in tracking system
    - Follow retention policy
```

### Performance Optimization Runbook
```markdown
# Performance Optimization Runbook for REX System

## Phase 1: Baseline Establishment
[ ] Define performance goals:
    - Target response times for different operations
    - Throughput requirements
    - Resource utilization targets
[ ] Establish baseline measurements:
    - Run performance tests under controlled conditions
    - Collect metrics during peak usage
    - Identify current bottlenecks
[ ] Document current configuration:
    - Resource allocations
    - Configuration settings
    - Architecture diagram

## Phase 2: Bottleneck Identification
[ ] Monitor key metrics:
    - Response times and latency distributions
    - Resource utilization (CPU, memory, disk, network)
    - Error rates and retry counts
    - Queue depths and processing times
[ ] Profile application:
    - CPU profiling to find hotspots
    - Memory profiling to find leaks
    - I/O profiling to find bottlenecks
[ ] Analyze logs:
    - Look for slow operations, timeouts, retries
    - Check for garbage collection issues
    - Review database query performance
[ ] Check dependencies:
    - Monitor external service performance
    - Verify database indexing and query plans
    - Test network latency and bandwidth

## Phase 3: Optimization Implementation
[ ] Address resource bottlenecks:
    - Scale compute resources if CPU bound
    - Increase memory if memory bound
    - Optimize storage if I/O bound
    - Improve networking if network bound
[ ] Optimize application code:
    - Refactor hotspots identified in profiling
    - Implement better algorithms or data structures
    - Add caching where appropriate
    - Optimize database queries and indexing
[ ] Optimize architecture:
    - Implement read replicas for database
    - Use CDN for static assets
    - Implement async processing for long tasks
    - Review and optimize service boundaries
[ ] Optimize caching:
    - Review cache hit rates and TTL values
    - Implement cache warming strategies
    - Consider cache hierarchy (local -> Redis -> CDN)
    - Use cache tags for selective invalidation

## Phase 4: Validation and Tuning
[ ] Performance testing:
    - Run load tests to verify improvements
    - Test at various load levels
    - Measure against established goals
[ ] Monitor production impact:
    - Gradually roll out changes
    - Watch for regressions or side effects
    - Collect feedback from users and monitoring
[ ] Fine-tune parameters:
    - Adjust timeouts, limits, thresholds based on results
    - Optimize cache sizes and eviction policies
    - Tune database and connection pool settings
[ ] Update baseline:
    - Document new performance characteristics
    - Update capacity planning models
    - Archive previous baseline for comparison

## Phase 5: Continuous Improvement
[ ] Establish regular review cycle:
    - Weekly performance review
    - Monthly capacity planning
    - Quarterly architecture review
[ ] Implement monitoring for regressions:
    - Alert on performance degradation
    - Track trends in key metrics
    - Regular performance testing in staging
[ ] Stay current with technology:
    - Evaluate new versions of dependencies
    - Consider architectural improvements
    - Benchmark alternative approaches
```

### Security Incident Runbook
```markdown
# Security Incident Runbook for REX System

## Phase 1: Identification
[ ] Alert received from security monitoring
[ ] Initial classification:
    - Type of incident (malware, unauthorized access, data leak, etc.)
    - Affected systems and data
    - Initial severity assessment
[ ] Preserve evidence:
    - Isolate affected systems if possible
    - Collect volatile memory and disk images
    - Preserve logs and network captures
    - Document everything with timestamps
[ ] Notify security team and management
[ ] Activate security incident response team
[ ] Create secure communication channel

## Phase 2: Containment
[ ] Short-term containment:
    - Block malicious traffic at firewall or WAF
    - Disable compromised accounts
    - Isolate affected network segments
    - Stop the spread without preserving evidence for now
[ ] Backup evidence:
    - Take forensic images of critical systems
    - Preserve logs in write-protected storage
    - Capture network traffic
    - Document system state
[ ] Long-term containment:
    - Apply patches or configuration changes
    - Implement additional monitoring
    - Prepare for system restoration
    - Consider rebuilding from known good state

## Phase 3: Eradication
[ ] Identify and remove root cause:
    - Delete malware and malicious files
    - Close vulnerabilities that were exploited
    - Remove unauthorized access points
    - Clean registry and startup items
    - Reimage systems if necessary
[ ] Validate eradication:
    - Run antivirus and anti-malware scans
    - Check for persistence mechanisms
    - Verify vulnerabilities are patched
    - Confirm no backdoors remain
[ ] Update defenses:
    - Apply security patches and updates
    - Strengthen authentication and authorization
    - Improve monitoring and detection capabilities
    - Implement least privilege principles

## Phase 4: Recovery
[ ] System restoration:
    - Restore systems from clean backups if needed
    - Rebuild applications from known good source
    - Apply latest security patches
    - Implement improved configurations
[ ] Validation:
    - Verify system integrity and functionality
    - Test security controls
    - Confirm no remnants of infection
    - Ensure business processes work correctly
[ ] Gradual restoration:
    - If systems were isolated, gradually restore connectivity
    - Monitor for issues during restoration
    - Confirm all security controls functioning
[ ] Monitoring:
    - Implement enhanced monitoring for recurrence
    - Set up alerts for similar attack patterns
    - Increase logging verbosity temporarily

## Phase 5: Lessons Learned
[ ] Incident documentation:
    - Complete timeline of events
    - Technical details of attack and defense
    - Impact assessment (data, systems, reputation)
    - Response timeline and effectiveness
    - Evidence chain of custody
[ ] Security improvements:
    - Update policies and procedures
    - Enhance technical controls
    - Improve employee training
    - Update incident response plan
    - Consider third-party assessments
[ ] Communication:
    - Internal communication to affected parties
    - External communication if required by law or policy
    - Regulatory notifications if applicable
    - Customer notification if data was compromised
[ ] Archive and retention:
    - Store all incident-related materials securely
    - Follow legal and regulatory retention requirements
    - Link to incident in security tracking system
    - Schedule review of effectiveness of changes
```

## Appendix A: Troubleshooting Commands Reference

### Docker Commands
```bash
# List containers
docker ps
docker ps -a

# View logs
docker logs <container-name>
docker logs -f <container-name>  # Follow logs

# Execute command in container
docker exec -it <container-name> bash
docker exec -it <container-name> <command>

# Inspect container
docker inspect <container-name>

# Check resource usage
docker stats
docker stats <container-name>  # Specific container

# Manage images
docker images
docker rmi <image-id>  # Remove image
docker prune  # Clean up unused resources

# Compose specific
docker-compose ps
docker-compose logs -f <service-name>
docker-compose up -d --scale <service>=<count>
docker-compose down -v  # Remove volumes too
```

### Kubernetes Commands
```bash
# Get resources
kubectl get all -n rex-research
kubectl get pods -n rex-research
kubectl get services -n rex-research
kubectl get deployments -n rex-research
kubectl get configmap -n rex-research
kubectl get secrets -n rex-research

# Describe resources
kubectl describe pod <pod-name> -n rex-research
kubectl describe deployment <deployment-name> -n rex-research
kubectl describe service <service-name> -n rex-research

# Logs
kubectl logs <pod-name> -n rex-research
kubectl logs -f <pod-name> -n rex-research  # Follow logs
kubectl logs <pod-name> -n rex-research -c <container-name>  # Specific container
kubectl logs --since=1h <pod-name> -n rex-research  # Last hour

# Execute commands
kubectl exec -it <pod-name> -n rex-research -- bash
kubectl exec <pod-name> -n rex-research -- <command>
kubectl exec <pod-name> -n rex-research -- cat /path/to/file

# Port forwarding
kubectl port-forward svc/<service-name> <local-port>:<target-port> -n rex-research
kubectl port-forward pod/<pod-name> <local-port>:<target-port> -n rex-research

# Scale resources
kubectl scale deployment <deployment-name> --replicas=<count> -n rex-research
kubectl autoscale deployment <deployment-name> --min=<min> --max=<max> --cpu-percent=<percent> -n rex-research

# Rollbacks
kubectl rollout undo deployment/<deployment-name> -n rex-research
kubectl rollout status deployment/<deployment-name> -n rex-research
kubectl rollout history deployment/<deployment-name> -n rex-research

# Debugging
kubectl top pods -n rex-research
kubectl top nodes
kubectl describe nodes
kubectl get events -n rex-research --sort-by='.lastTimestamp'
```

### Network Commands
```bash
# Check connectivity
ping <host>
traceroute <host>
nc -zv <host> <port>  # Test TCP connection
telnet <host> <port>

# DNS lookup
nslookup <host>
dig <host>
dig <host> ANY

# Socket statistics
ss -tulpn  # Listening TCP/UDP ports
ss -tulnp  # Same with process info
netstat -tulpn
netstat -tulnp

# Firewall (Linux)
sudo iptables -L -v -n
sudo iptables -L -v -n -t nat
sudo ufw status verbose
sudo firewall-cmd --list-all  # firewalld

# Packet capture
tcpdump -i <interface> host <host> and port <port>
tcpdump -i <interface> -w <output-file.pcap>
```

### Database Commands
```bash
# PostgreSQL
psql -h <host> -U <user> -d <db> -c "<command>"
psql -h <host> -U <user> -d <db>  # Interactive shell

# Check connections
SELECT * FROM pg_stat_activity;
SELECT * FROM pg_stat_bgwriter;
SELECT * FROM pg_stat_database;

# Check locks
SELECT * FROM pg_locks;

# Check table sizes
SELECT pg_size_pretty(pg_total_relation_size('tablename'));

# Redis
redis-cli -h <host> -p <port> -a <password>
redis-cli ping
redis-cli info
redis-cli monitor
redis-cli slowlog get 10

# Elasticsearch
curl -X GET "http://localhost:9200/_cluster/health?pretty"
curl -X GET "http://localhost:9200/_cat/nodes?v&h=name,ip,heap.percent,ram.percent,cpu,load_1m,load_5m,load_15m,node.role,master,name"
curl -X GET "http://localhost:9200/_cat/indices?v"
```

### Log Analysis Commands
```bash
# grep with context
grep -i "error" /var/log/rex/app.log
grep -i "error" /var/log/rex/app.log -B 3 -A 3  # 3 lines before and after
grep -i "timeout" /var/log/rex/app.log

# Count occurrences
grep -c "error" /var/log/rex/app.log
grep -c "timeout" /var/log/rex/app.log

# Extract specific fields (JSON logs)
# Assuming jq is installed
jq '.level' /var/log/rex/app.log | sort | uniq -c
jq 'select(.level == "error") | .message' /var/log/rex/app.log
jq 'select(.service == "backend") | .timestamp, .message' /var/log/rex/app.log

# Follow logs and filter
tail -f /var/log/rex/app.log | grep -i "error"
tail -f /var/log/rex/app.log | grep -i "timeout" | grep -i "search"

# Log rotation investigation
ls -lh /var/log/rex/
logrotate -d /etc/logrotate.d/rex  # Dry run
```

## Appendix B: Environment Variables Reference

### Core Settings
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_HOST` | Backend host address | `0.0.0.0` | No |
| `API_PORT` | Backend port | `8000` | No |
| `FRONTEND_PORT` | Frontend port | `3000` | No |
| `ENVIRONMENT` | Deployment environment | `development` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `DEBUG` | Debug mode | `false` | No |

### LLM Settings
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OLLAMA_HOST` | Ollama service URL | `http://127.0.0.1:11434` | No |
| `PLANNER_MODEL` | Model for planner agent | `phi3:mini` | No |
| `REPORT_MODEL` | Model for report generator | `qwen2.5:3b` | No |
| `LLM_TIMEOUT` | LLM timeout in seconds | `180` | No |
| `MAX_TOKENS` | Maximum tokens per LLM call | `4000` | No |
| `TEMPERATURE` | LLM temperature | `0.7` | No |

### Search Settings
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MAX_SEARCH_WORKERS` | Parallel search workers | `8` | No |
| `SEARCHER_TIMEOUT` | Overall search timeout (s) | `60` | No |
| `QUERY_TIMEOUT` | Per-query timeout (s) | `15` | No |
| `CACHE_ENABLED` | Enable/disable caching | `true` | No |
| `CACHE_TTL` | Cache TTL in seconds | `86400` | No |
| `CACHE_TYPE` | Cache backend | `memory` | No |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` | No (if using Redis) |
| `DUCKDUCKGO_ENABLED` | Enable DuckDuckGo fallback | `true` | No |

### API Key Settings (for search APIs)
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TAVILY_API_KEY` | Tavily API key | `` | Yes (if using Tavily) |
| `FIRECRAWL_API_KEY` | Firecrawl API key | `` | Yes (if using Firecrawl) |
| `SERPAPI_KEY` | SerpAPI key | `` | Yes (if using SerpAPI) |
| `LANGSEARCH_API_KEY` | LangSearch API key | `` | Yes (if using LangSearch) |
| `PIXELRAG_API_KEY` | PixelRAG API key | `` | Yes (if using PixelRAG) |

### Security Settings
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_KEY_REQUIRED` | Require API key for endpoints | `false` | No |
| `JWT_SECRET` | Secret for JWT signing | `` | Yes (if API_KEY_REQUIRED=true) |
| `JWT_EXPIRATION_MINUTES` | JWT expiration time | `30` | No |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` | No |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | Requests per minute | `100` | No |
| `RATE_LIMIT_BURST` | Burst allowance | `20` | No |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000,*` | No |
| `TRUSTED_PROXIES` | Comma-separated trusted proxies | `` | No |

### Agent Orchestration Settings
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `AGENT_REGISTRY_ENABLED` | Enable agent registry | `true` | No |
| `AGENT_HEARTBEAT_TIMEOUT` | Stale agent timeout (s) | `300` | No |
| `MAX_CONCURRENT_AGENTS` | Maximum total agents | `21` | No |
| `LOAD_BALANCING_STRATEGY` | Load balancing method | `round_robin` | No |
| `AGENT_HEALTH_CHECK_INTERVAL` | Health check interval (s) | `30` | No |
| `FAILURE_THRESHOLD` | Consecutive failures before marking unhealthy | `3` | No |

### Monitoring Settings
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENABLE_TRACING` | Enable distributed tracing | `false` | No |
| `TRACING_ENDPOINT` | Jaeger endpoint (host:port) | `` | Yes (if ENABLE_TRACING=true) |
| `TRACING_SAMPLERATE` | Trace sampling rate (0.0-1.0) | `0.1` | No |
| `LOG_FORMAT` | Log format | `json` | No |
| `ENABLE_METRICS` | Enable Prometheus metrics | `true` | No |
| `METRICS_PORT` | Metrics endpoint port | `9090` | No |
| `METRICS_PATH` | Metrics endpoint path | `/metrics` | No |
| `HEALTH_CHECK_ENDPOINT` | Health check endpoint path | `/health` | No |

### Storage Settings
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | `` | Yes (if not using SUPABASE) |
| `SUPABASE_URL` | Supabase project URL | `` | Yes (if not using DATABASE_URL) |
| `SUPABASE_KEY` | Supabase anon/public key | `` | Yes (if using SUPABASE) |
| `UPLOAD_DIR` | Directory for file uploads | `./uploads` | No |
| `EXPORT_DIR` | Directory for exports | `./exports` | No |
| `MAX_UPLOAD_SIZE_MB` | Maximum upload size | `10` | No |
| `ALLOWED_UPLOAD_EXTENSIONS` | Comma-separated allowed extensions | `jpg,png,pdf,txt,docx` | No |

### n8n Integration Settings
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `N8N_ENABLED` | Enable n8n webhook integration | `false` | No |
| `N8N_WEBHOOK_URL` | n8n webhook URL | `` | Yes (if N8N_ENABLED=true) |
| `N8N_WEBHOOK_SECRET` | Secret for webhook verification | `` | Yes (if N8N_ENABLED=true) |
| `N8N_TIMEOUT` | Webhook timeout in seconds | `30` | No |
| `N8N_RETRY_ATTEMPTS` | Number of retry attempts | `3` | No |
| `N8N_RETRY_DELAY_SECONDS` | Delay between retries | `5` | No |

### Feature Flags
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `FEATURE_ANALYTICS` | Enable analytics collection | `false` | No |
| `FEATURE_EXPERIMENTS` | Enable experiment framework | `false` | No |
| `FEATURE_WEBSOCKETS` | Enable WebSocket alternative to SSE | `false` | No |
| `FEATURE_GRAPHQL` | Enable GraphQL API | `false` | No |
| `FEATURE_PLUGINS` | Enable plugin system | `false` | No |

## Appendix C: Ports Reference

### Service Ports
| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| Backend API | 8000 | TCP | Main REST API |
| Frontend | 3000 | TCP | Web application |
| API Gateway | 80 | TCP | HTTP entry point |
| HTTPS Gateway | 443 | TCP | HTTPS entry point (with TLS) |
| Prometheus | 9090 | TCP | Metrics collection |
| Grafana | 3000 | TCP | Dashboard (may conflict with frontend) |
| Jaeger UI | 16686 | TCP | Distributed tracing UI |
| Jaeger Agent | 6831 | UDP | Trace agent endpoint |
| Elasticsearch | 9200 | TCP | Log storage and search |
| Kibana | 5601 | TCP | Log visualization |
| PostgreSQL | 5432 | TCP | Primary database |
| Redis | 6379 | TCP | Caching and session storage |
| Ollama | 11434 | TCP | Local LLM inference |
| n8n (if used) | 5678 | TCP | Workflow automation |
| RabbitMQ (if used) | 5672 | TCP | Message queue |
| MongoDB (if used) | 27017 | TCP | Document database |

### Container Port Mapping (Kubernetes/Docker)
| Container Name | Container Port | Host Port (Typical) | Notes |
|----------------|----------------|---------------------|-------|
| backend | 8000 | 8000 (compose), 80 (k8s ingress) | Main API |
| frontend | 3000 | 3000 (compose), 80 (k8s ingress) | Web UI |
| prometheus | 9090 | 9090 | Metrics |
| grafana | 3000 | 3000 | Dashboard |
| jaeger | 16686 | 16686 | UI |
| elasticsearch | 9200 | 9200 | Storage |
| kibana | 5601 | 5601 | Visualization |
| postgres | 5432 | 5432 | Database |
| redis | 6379 | 6379 | Cache |
| ollama | 11434 | 11434 | LLM |
| agent-registry | 8000 | 8000 | Service discovery |
| planner-agent | 8000 | 8001+ | Agent service |
| searcher-agent | 8000 | 8002+ | Agent service |
| ... | ... | ... | ... |

## Appendix C: Health Check Endpoints

### Backend Service
| Endpoint | Method | Description | Expected Response |
|----------|--------|-------------|-------------------|
| `/health/liveness` | GET | Basic liveness check | `{"status": "alive", "timestamp": "..."}` |
| `/health/readiness` | GET | Readiness check (dependencies) | `{"status": "ready|not ready", "checks": [...], "timestamp": "..."}` |
| `/health/startup` | GET | Startup check (for slow start) | `{"status": "started|starting", "timestamp": "..."}` |
| `/health/detailed` | GET | Comprehensive health check | Full system status with all dependencies |
| `/health/simple` | GET | Legacy simple health check | `{"status": "OK"}` or `{"status": "ERROR", "message": "..."}` |

### Frontend Service
| Endpoint | Method | Description | Expected Response |
|----------|--------|-------------|-------------------|
| `/api/health` | GET | Frontend health check | `{"status": "healthy", "timestamp": "..."}` |
| `/ping` | GET | Simple connectivity check | `"pong"` or `200 OK` |

### Agent Services
| Endpoint | Method | Description | Expected Response |
|----------|--------|-------------|-------------------|
| `/health` | GET | Agent health check | `{"status": "healthy|degraded|unhealthy", "agent_type": "...", "load": 0.0-1.0, "timestamp": "..."}` |
| `/metrics` | GET | Prometheus metrics | Prometheus exposition format |
| `/info` | GET | Agent information | `{"agent_id": "...", "agent_type": "...", "version": "...", ...}` |

### Infrastructure Services
| Service | Endpoint | Method | Description |
|---------|----------|--------|-------------|
| PostgreSQL | `SELECT 1;` | SQL | Basic connectivity check |
| Redis | `PING` | Command | Should return `PONG` |
| Ollama | `/api/version` | GET | Should return version info |
| Elasticsearch | `/_cluster/health` | GET | Should return `status: green|yellow` |
| Kafka | `/admin/brokers` | HTTP | Should return broker list |
| RabbitMQ | `/api/overview` | HTTP | Should return overview stats |
| Prometheus | `/-/healthy` | GET | Should return `200 OK` |
| Grafana | `/api/health` | GET | Should return `200 OK` |
| Jaeger | `/` | GET | Should return UI page |

## Appendix D: Disaster Recovery Contact List

### Internal Contacts
| Role | Name | Contact Information | Escalation Path |
|------|------|---------------------|-----------------|
| Primary On-Call | [Name] | [Phone/Slack/Email] | Secondary On-Call |
| Secondary On-Call | [Name] | [Phone/Slack/Email] | Team Lead |
| Team Lead | [Name] | [Phone/Slack/Email] | Engineering Manager |
| Engineering Manager | [Name] | [Phone/Slack/Email] | Director of Engineering |
| Security Lead | [Name] | [Phone/Slack/Email] | CISO |
| Database Administrator | [Name] | [Phone/Slack/Email] | Engineering Manager |
| DevOps Lead | [Name] | [Phone/Slack/Email] | Engineering Manager |
| Product Manager | [Name] | [Phone/Slack/Email] | Director of Product |

### External Contacts
| Service | Contact | Phone | Notes |
|---------|---------|-------|-------|
| Cloud Provider Support | [Provider] Support | [Number] | Account ID: [ID] |
| Internet Service Provider | [ISP] Support | [Number] | Circuit ID: [ID] |
| Domain Registrar | [Registrar] Support | [Number] | Domain: [domain.com] |
| SSL Certificate Provider | [Provider] Support | [Number] | Cert ID: [ID] |
| Third-Party API Provider | [Provider] Support | [Number] | API Key: [Key] |
| Hardware Vendor | [Vendor] Support | [Number] | Serial: [Serial] |
| Emergency Services | Local Emergency | [Number] | Only for physical safety issues |

### Communication Channels
- **Primary**: Slack #rex-incidents
- **Secondary**: Email incident-response@company.com
- **Tertiary**: Phone tree (see contact list)
- **Emergency**: Phone calls and SMS
- **Status Page**: https://status.rex-agent.com
- **Stakeholder Updates**: Email distribution list

## Appendix E: Glossary of Terms

- **Agent**: A specialized service instance performing specific functions in the REX ecosystem (planner, searcher, synthesizer, etc.)
- **Agent Registry**: Central service for discovering, registering, and monitoring agent instances
- **Correlation ID**: Unique identifier used to trace a request across multiple services
- **Event Queue**: Thread-safe queue used for communication between LangGraph nodes and SSE generator
- **Gateway**: Entry point that routes traffic to appropriate services (API Gateway, Ingress Controller)
- **Health Check**: Endpoint or mechanism to determine service availability and health
- **Heartbeat**: Periodic signal from agent to registry indicating liveness
- **Idempotent**: Operation that can be applied multiple times without changing result beyond initial application
- **LangGraph**: Library for creating state machines and agents using graphs
- **Latency**: Time delay between request initiation and response completion
- **Load Balancing**: Distributing workload across multiple computing resources
- **Microservice**: Small, independent service that performs a specific function
- **Orchestration**: Automated arrangement, coordination, and management of complex systems
- **Pod**: Smallest deployable unit in Kubernetes that can contain one or more containers
- **Prometheus**: Open-source monitoring and alerting toolkit
- **Quality of Service (QoS)**: Performance characteristics of a service under specific conditions
- **Race Condition**: Situation where system behavior depends on the sequence or timing of uncontrollable events
- **Rate Limiting**: Controlling the rate of requests sent or received by a network interface
- **Readiness Probe**: Kubernetes mechanism to determine if container is ready to serve traffic
- **Recursive Exploration**: Process of iteratively refining search based on identified knowledge gaps
- **Replica**: Copy of a microservice running to provide redundancy and scalability
- **Rollback**: Reverting to a previous known good state
- **Service Mesh**: Dedicated infrastructure layer for handling service-to-service communication
- **Sidecar**: Container that runs alongside main application container to extend or enhance functionality
- **Stale Agent**: Agent that has not sent heartbeat within expected timeout period
- **State Machine**: Mathematical model of computation used to design algorithms
- **Throughput**: Amount of work processed per unit of time
- **Tracing**: Monitoring and recording of requests as they propagate through a system
- **Worker**: Process or thread that performs work tasks