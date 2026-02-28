# AgentLens v0.2.0 — Deployment Guide

## Quick Start

### Docker (Production)

```bash
# Pull latest image
docker pull tranhoangtu/agentlens:0.2.0

# Run container
docker run -p 3000:3000 tranhoangtu/agentlens:0.2.0

# Access dashboard
open http://localhost:3000
```

### Docker Compose (Local Development)

```bash
cd agentlens
docker-compose up
```

**Services:**
- Dashboard: http://localhost:5173 (React dev server)
- Server: http://localhost:8000 (FastAPI)
- API Docs: http://localhost:8000/docs (Swagger UI)

### PyPI Installation (SDK Only)

```bash
pip install agentlens-observe==0.2.0

# Verify installation
python -c "import agentlens; print(agentlens.__version__)"
```

## Server Deployment

### Prerequisites
- Docker Engine 20.10+ OR Python 3.11+
- 512MB RAM minimum
- 1GB disk space for SQLite

### Environment Variables

```bash
# Optional — defaults provided
SERVER_URL="http://localhost:3000"
DATABASE_URL="sqlite:///./agentlens.db"     # SQLite only (v0.2.0)
LOG_LEVEL="INFO"                             # DEBUG, INFO, WARNING, ERROR
PORT=3000                                    # API + Dashboard port
```

### Docker Deployment

**Dockerfile (Multi-Stage Build)**
```dockerfile
# Stage 1: Build React dashboard
FROM node:20-alpine AS builder

WORKDIR /app
COPY dashboard ./dashboard
RUN cd dashboard && \
    npm ci && \
    npm run build

# Stage 2: Runtime (Python + FastAPI)
FROM python:3.11-slim

WORKDIR /app

# Copy built React app
COPY --from=builder /app/dashboard/dist ./server/static

# Install Python dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
  CMD python -c "import requests; requests.get('http://localhost:3000/api/health')"

EXPOSE 3000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
```

**Build & Run:**
```bash
docker build -t agentlens:0.2.0 .
docker run -p 3000:3000 -v agentlens_db:/app/data agentlens:0.2.0
```

**Data Persistence:**
```bash
# Named volume
docker volume create agentlens_db
docker run -p 3000:3000 -v agentlens_db:/app/data agentlens:0.2.0

# Or bind mount
docker run -p 3000:3000 -v ~/agentlens_data:/app/data agentlens:0.2.0
```

### Python Deployment (Without Docker)

**Requirements:**
- Python 3.11+
- Node 18+ (for dashboard build)

**Steps:**

1. **Install dependencies**
```bash
cd server
pip install -r requirements.txt
```

2. **Build dashboard**
```bash
cd dashboard
npm install
npm run build
cp -r dist ../server/static/
```

3. **Run server**
```bash
cd server
uvicorn main:app --host 0.0.0.0 --port 3000
```

4. **Verify**
```bash
curl http://localhost:3000/api/health
# {"status": "ok"}
```

### Kubernetes Deployment

**agentlens-deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentlens
  labels:
    app: agentlens
spec:
  replicas: 1
  selector:
    matchLabels:
      app: agentlens
  template:
    metadata:
      labels:
        app: agentlens
    spec:
      containers:
      - name: agentlens
        image: tranhoangtu/agentlens:0.2.0
        ports:
        - containerPort: 3000
        env:
        - name: LOG_LEVEL
          value: "INFO"
        volumeMounts:
        - name: db
          mountPath: /app/data
        livenessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 30
      volumes:
      - name: db
        emptyDir: {}  # Or use PersistentVolumeClaim for production
---
apiVersion: v1
kind: Service
metadata:
  name: agentlens
spec:
  selector:
    app: agentlens
  ports:
  - port: 80
    targetPort: 3000
  type: LoadBalancer
```

**Deploy:**
```bash
kubectl apply -f agentlens-deployment.yaml
kubectl port-forward svc/agentlens 3000:80
```

## SDK Deployment

### Installation

```bash
# From PyPI
pip install agentlens-observe==0.2.0

# From source
cd sdk
pip install -e .

# With dev dependencies
pip install -e ".[dev]"
```

### Configuration

**Minimal Setup**
```python
import agentlens

agentlens.configure(server_url="http://localhost:3000")

@agentlens.trace(name="MyAgent")
def run_agent(query: str) -> str:
    with agentlens.span("search", "tool_call") as s:
        result = search(query)
        s.set_output(result)
    return result
```

**Advanced Configuration**
```python
agentlens.configure(
    server_url="http://agentlens.example.com",
    batch_size=100,        # Flush every 100 traces
    batch_interval=10.0,   # Or every 10 seconds
)

# Add exporters
from agentlens.exporters.otel import AgentLensOTelExporter
agentlens.add_exporter(AgentLensOTelExporter(
    otel_endpoint="http://localhost:4317"
))
```

### Framework Integration

**LangChain**
```python
from agentlens.integrations.langchain import AgentLensCallbackHandler

agent.run("task", callbacks=[AgentLensCallbackHandler()])
```

**CrewAI**
```python
from agentlens.integrations.crewai import patch_crewai

patch_crewai()  # Auto-instruments all crews
crew.kickoff(inputs={...})
```

**AutoGen**
```python
from agentlens.integrations.autogen import patch_autogen

patch_autogen()  # Auto-instruments all conversations
```

**LlamaIndex**
```python
from agentlens.integrations.llamaindex import AgentLensCallbackHandler
from llama_index.core import Settings
from llama_index.core.callbacks import CallbackManager

Settings.callback_manager = CallbackManager([AgentLensCallbackHandler()])
```

**Google ADK**
```python
from agentlens.integrations.google_adk import patch_google_adk

patch_google_adk()  # Auto-instruments agents
```

## Production Checklist

### Security
- [ ] HTTPS enabled (reverse proxy with SSL/TLS)
- [ ] CORS configured for trusted origins only
- [ ] Remove `/docs` endpoint (Swagger UI) from production
- [ ] Rate limiting on API endpoints
- [ ] No debug logs in production (LOG_LEVEL=WARNING)
- [ ] Database backups enabled
- [ ] Credentials stored in environment variables (not committed)

### Performance
- [ ] GZip compression enabled (FastAPI middleware)
- [ ] Database indexes verified (run `init_db()`)
- [ ] React bundle split into 4 chunks
- [ ] Virtualized table for 1000+ rows
- [ ] Caching headers set on static assets

### Monitoring
- [ ] Health check endpoint configured (/api/health)
- [ ] Structured logging with timestamps
- [ ] Metrics exported (Prometheus compatible)
- [ ] Slow query alerts (>1s response time)

### Backup & Recovery
- [ ] Daily SQLite backups (WAL checkpoint)
- [ ] Retention policy (30 days default)
- [ ] Disaster recovery procedure documented
- [ ] Test restore from backup monthly

### Updates
- [ ] Plan upgrade window (low traffic hours)
- [ ] Test new version in staging first
- [ ] Backup database before upgrade
- [ ] Monitor logs for errors post-upgrade

## Scaling Considerations

### Current (v0.2.0 — SQLite)
**Limits:**
- ~10K traces/day
- ~100K total spans
- Single machine deployment
- Recommended max: 10 concurrent SDK clients

**Bottlenecks:**
- SQLite write contention
- Single process (no horizontal scaling)
- Limited concurrent connections

### Future (v0.3.0+ — PostgreSQL)
```python
# Expected configuration:
DATABASE_URL="postgresql://user:pass@db:5432/agentlens"

# Benefits:
# - Unlimited concurrent connections
# - Horizontal scaling (multiple API instances)
# - Connection pooling (pgbouncer)
# - Full-text search optimization
```

### Upgrade Path

1. **Assess current load**
   ```bash
   sqlite3 agentlens.db "SELECT COUNT(*) FROM trace;"
   ```

2. **When to migrate to PostgreSQL:**
   - >50K total spans
   - >100 concurrent SDK clients
   - >1,000 traces/day
   - Multi-region deployment needed

3. **Migration process:**
   - Export SQLite data via API
   - Set up PostgreSQL backend
   - Point new instances to PostgreSQL
   - Decommission SQLite

## Monitoring & Logging

### Health Check
```bash
curl http://localhost:3000/api/health
# {"status": "ok"}
```

### Logs
```bash
# Docker logs
docker logs -f <container_id>

# Kubernetes logs
kubectl logs deployment/agentlens -f

# Check for errors
grep "ERROR" /var/log/agentlens/app.log
```

### Key Metrics
- **Request latency:** P50, P95, P99 response times
- **Error rate:** 5xx responses per minute
- **Database:** Query execution time, connection pool usage
- **SDK:** Batch queue depth, flush interval adherence

### Alerts
```python
# Alert on high error rate
if error_rate > 1%:
    send_alert("High AgentLens error rate")

# Alert on slow queries
if query_time > 1000:
    send_alert(f"Slow query: {query_time}ms")

# Alert on database size
if db_size > 5_000_000_000:  # 5GB
    send_alert("Database approaching disk limit")
```

## Troubleshooting

### Issue: Server won't start
```bash
# Check port availability
lsof -i :3000

# Check Python version
python --version  # Must be 3.11+

# Check dependencies
pip list | grep -E "fastapi|sqlmodel"
```

### Issue: Database locked
```bash
# SQLite WAL issue — restart container
docker restart <container_id>

# Or remove WAL files
rm agentlens.db-wal agentlens.db-shm
```

### Issue: Slow trace listings
```bash
# Check indexes
sqlite3 agentlens.db ".indices"

# Verify compound indexes exist
sqlite3 agentlens.db ".schema trace"

# Rebuild indexes if needed
sqlite3 agentlens.db "REINDEX;"
```

### Issue: SDK traces not appearing
```python
# Verify configuration
print(agentlens._tracer._transport._server_url)
# Should be your server URL

# Check network
curl http://server:3000/api/health

# Increase logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Tuning

### Database
```python
# WAL mode (default)
PRAGMA journal_mode = WAL;

# Increase cache size
PRAGMA cache_size = -64000;  # 64MB

# Optimize for reads
PRAGMA query_only = TRUE;
```

### API
```python
# Connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    db_url,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
)
```

### Frontend
```typescript
// Code splitting (Vite config)
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        'react-flow': ['react-flow-renderer'],
        'recharts': ['recharts'],
      }
    }
  }
}
```

## Support & Resources

- **GitHub Issues:** github.com/tranhoangtu-it/agentlens/issues
- **Documentation:** docs/ directory
- **Discord:** Join community (coming soon)
- **Email:** support@agentlens.io
