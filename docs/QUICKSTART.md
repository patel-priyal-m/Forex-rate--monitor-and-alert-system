# Quick Start Guide

Get the FX Rate Monitoring System running in 5 minutes.

## Prerequisites Check

Before starting, verify you have:

```bash
# Docker and Docker Compose
docker --version        # Should be 20.10+
docker compose version  # Should be 2.0+

# Available ports
netstat -an | findstr "5432 6379 9092 8000 9200 5601"
# Should return empty (ports available)

# System resources
# Minimum: 8GB RAM, 20GB disk space
```

## Step-by-Step Setup

### 1. Get the Code

```bash
git clone https://github.com/your-username/Forex-rate--monitor-and-alert-system.git
cd Forex-rate--monitor-and-alert-system
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Optional: Edit .env to customize
# Default values work for local development
notepad .env  # Windows
```

**Key Settings** (defaults work out of the box):
- `TRACKED_CURRENCIES=EUR,GBP,JPY,CAD,AUD,CHF,CNY,INR` - 8 pairs to monitor
- `LOG_LEVEL=INFO` - Logging verbosity
- All ports configured for local development

### 3. Start All Services

```bash
# Build and start all 9 containers
docker compose up -d

# Expected output:
# [+] Running 9/9
#  ✔ Container fx-kafka           Started
#  ✔ Container fx-postgres        Started
#  ✔ Container fx-redis           Started
#  ✔ Container fx-elasticsearch   Started
#  ✔ Container fx-producer        Started
#  ✔ Container fx-consumer        Started
#  ✔ Container fx-kibana          Started
#  ✔ Container fx-api             Started
#  ✔ Container alert-engine       Started
```

### 4. Wait for Services to Initialize

Services need ~30-60 seconds to become healthy.

```bash
# Check status (wait for all "healthy")
docker compose ps

# Should show all services as "healthy":
# NAME               STATUS
# fx-kafka           Up (healthy)
# fx-postgres        Up (healthy)
# fx-redis           Up (healthy)
# fx-elasticsearch   Up (healthy)
# fx-kibana          Up (healthy)
# fx-producer        Up (healthy)
# fx-consumer        Up (healthy)
# fx-api             Up (healthy)
# alert-engine       Up (healthy)
```

### 5. Verify Data Flow

```bash
# Watch consumer processing rates
docker compose logs -f fx-consumer

# You should see:
# ✅ Stored 8 rates in PostgreSQL
# ✅ Cached 8 rates in Redis
# ✅ Calculated volatility for 8 pairs
# ✅ Indexed 8 rates to Elasticsearch
# ✅ Calculated 28 cross-rates
# ⏱️  Total Processing Time: 0.024s
```

Press `Ctrl+C` to stop following logs.

### 6. Access the System

Open in your browser:

1. **Kibana Dashboard**: http://localhost:5601
   - Real-time visualizations
   - See [Kibana Setup Guide](KIBANA_SETUP.md) for dashboard creation

2. **FastAPI Swagger UI**: http://localhost:8000/docs
   - Interactive API documentation
   - Test all endpoints

3. **API Health Check**: http://localhost:8000/health
   - Verify all connections

## Quick Verification

### Test the API

```bash
# Get system info
curl http://localhost:8000/

# Get current rates
curl http://localhost:8000/rates | json_pp

# Get rate history for USD/EUR
curl http://localhost:8000/rates/USD%2FEUR/history | json_pp

# Create an alert
curl -X POST http://localhost:8000/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "pair": "USD/EUR",
    "condition": "below",
    "threshold": 0.85
  }'

# List active alerts
curl http://localhost:8000/alerts | json_pp
```

### Check Elasticsearch Data

```bash
# Count documents
curl http://localhost:9200/fx-rates/_count

# View sample data
curl "http://localhost:9200/fx-rates/_search?size=2&sort=timestamp:desc" | json_pp
```

### View Logs

```bash
# All services
docker compose logs

# Specific service (follow mode)
docker compose logs -f fx-consumer
docker compose logs -f fx-api
docker compose logs -f alert-engine

# Last 50 lines
docker compose logs --tail=50 fx-consumer
```

## What Happens After Start?

1. **Kafka** starts and creates `fx-rates` topic
2. **PostgreSQL** initializes database and tables
3. **Redis** starts in-memory cache
4. **Elasticsearch** creates indices (`fx-rates`, `fx-alerts`)
5. **Kibana** connects to Elasticsearch
6. **Producer** fetches FX rates every 30 seconds
7. **Consumer** processes rates with multiprocessing
8. **Alert Engine** monitors for threshold breaches
9. **FastAPI** exposes REST endpoints

**Data flows every 30 seconds**: API → Producer → Kafka → Consumer → [PostgreSQL, Redis, Elasticsearch] → Kibana

## Next Steps

Now that the system is running:

1. **Create Kibana Dashboards**: Follow [Kibana Setup Guide](KIBANA_SETUP.md)
2. **Explore the API**: Visit http://localhost:8000/docs
3. **Test Alerts**: Create alerts and watch them trigger
4. **Review Architecture**: See [Architecture Guide](ARCHITECTURE.md)

## Common Issues

### Ports Already in Use

```bash
# Find process using port (example: 5432)
netstat -ano | findstr :5432

# Stop conflicting service or change port in .env
```

### Services Not Starting

```bash
# Check Docker is running
docker ps

# View error logs
docker compose logs <service-name>

# Restart all services
docker compose restart

# Clean start (removes volumes!)
docker compose down -v
docker compose up -d
```

### Out of Memory

```bash
# Check Docker resources
docker stats

# Increase Docker Desktop memory:
# Settings → Resources → Memory → 8GB minimum
```

### No Data Appearing

```bash
# Verify producer is fetching
docker compose logs fx-producer | findstr "Fetched"

# Verify consumer is processing
docker compose logs fx-consumer | findstr "Stored"

# Check Kafka topic has messages
docker exec fx-kafka kafka-console-consumer \
  --bootstrap-server localhost:29092 \
  --topic fx-rates \
  --from-beginning \
  --max-messages 1
```

## Stopping the System

```bash
# Stop all containers (preserves data)
docker compose down

# Stop and remove volumes (fresh start next time)
docker compose down -v

# Stop specific service
docker compose stop fx-consumer
```

## Restarting

```bash
# Start previously created containers
docker compose start

# Or rebuild and start
docker compose up -d --build
```

## You're Ready! 🎉

Your FX Rate Monitoring System is now running. Head to:
- **Kibana**: http://localhost:5601 - Create your dashboard
- **API Docs**: http://localhost:8000/docs - Explore endpoints
- **View Logs**: `docker compose logs -f fx-consumer` - Watch live processing

Need help? Check the [Troubleshooting Guide](TROUBLESHOOTING.md).
