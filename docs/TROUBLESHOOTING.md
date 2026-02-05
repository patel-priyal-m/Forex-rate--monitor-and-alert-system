# Troubleshooting Guide

Common issues and solutions for the FX Rate Monitoring System.

## 🔍 Diagnostic Commands

Before troubleshooting, gather information:

```bash
# Check all service status
docker compose ps

# View logs for specific service
docker compose logs <service-name>

# Check resource usage
docker stats

# Test network connectivity
docker compose exec fx-consumer ping elasticsearch

# Check Elasticsearch health
curl http://localhost:9200/_cluster/health
```

---

## 🐛 Common Issues

### 1. Services Won't Start

#### Symptom
```
ERROR: cannot start service fx-kafka: port 9092 is already in use
```

#### Solution
```bash
# Find process using the port
netstat -ano | findstr :9092

# Kill the process or change port in .env
```

#### Alternative: Change Ports
Edit `.env`:
```bash
# Use different ports
KAFKA_PORT=9093
POSTGRES_PORT=5433
```

---

### 2. Docker Out of Memory

#### Symptom
```
Container killed: out of memory
```

#### Solution
Increase Docker Desktop resources:
1. Docker Desktop → Settings → Resources
2. Set Memory to minimum 8GB
3. Set CPUs to 4+
4. Click "Apply & Restart"

---

### 3. Kafka Not Accepting Connections

#### Symptom
```
KafkaException: Failed to connect to broker
```

#### Solutions

**Check Kafka is healthy:**
```bash
docker compose ps kafka
# Should show "healthy"
```

**View Kafka logs:**
```bash
docker compose logs kafka
```

**Restart Kafka:**
```bash
docker compose restart kafka
# Wait 30 seconds for health check
```

**Verify Kafka is reachable:**
```bash
docker compose exec fx-producer ping kafka
```

---

### 4. PostgreSQL Connection Failed

#### Symptom
```
sqlalchemy.exc.OperationalError: could not connect to server
```

#### Solutions

**Check PostgreSQL status:**
```bash
docker compose ps postgres
```

**Check credentials match .env:**
```bash
# In .env
POSTGRES_USER=fxuser
POSTGRES_PASSWORD=fxpassword
POSTGRES_DB=fxrates

# Test connection
docker compose exec postgres psql -U fxuser -d fxrates -c "SELECT 1;"
```

**Reset database:**
```bash
docker compose down postgres
docker volume rm forex-rate--monitor-and-alert-system_postgres-data
docker compose up -d postgres
```

---

### 5. Redis Connection Issues

#### Symptom
```
redis.exceptions.ConnectionError: Connection refused
```

#### Solutions

**Check Redis status:**
```bash
docker compose ps redis
```

**Test Redis connection:**
```bash
docker compose exec redis redis-cli ping
# Should return: PONG
```

**View keys in Redis:**
```bash
docker compose exec redis redis-cli KEYS "*"
```

---

### 6. Elasticsearch Not Starting

#### Symptom
```
max virtual memory areas vm.max_map_count [65530] is too low
```

#### Solution (Windows with WSL2)

```powershell
# In PowerShell (as Administrator)
wsl -d docker-desktop
sysctl -w vm.max_map_count=262144
exit
```

**Permanent fix:**
```bash
# In WSL2
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

#### Solution (Linux)
```bash
sudo sysctl -w vm.max_map_count=262144
```

---

### 7. Kibana Won't Start

#### Symptom
```
Kibana server is not ready yet
```

#### Solutions

**Wait longer:**
Kibana takes 30-60 seconds on first start.

**Check Elasticsearch is healthy:**
```bash
curl http://localhost:9200/_cluster/health
```

**View Kibana logs:**
```bash
docker compose logs kibana
```

**Restart both services:**
```bash
docker compose restart elasticsearch kibana
```

---

### 8. No Data in Kibana

#### Symptom
No documents found when creating data view.

#### Solutions

**Verify Elasticsearch has data:**
```bash
curl http://localhost:9200/fx-rates/_count
```

**Check consumer is indexing:**
```bash
docker compose logs fx-consumer | findstr "Indexed"
```

**Verify time range in Kibana:**
1. Open Kibana → Discover
2. Check time picker (top-right)
3. Set to "Last 1 hour" or "Last 15 minutes"

**Manually index test data:**
```bash
curl -X POST http://localhost:9200/fx-rates/_doc \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S)'",
    "pair": "USD/EUR",
    "rate": 0.85,
    "volatility": 0.001,
    "source": "test"
  }'
```

---

### 9. API Returns 500 Errors

#### Symptom
```
Internal Server Error (500)
```

#### Solutions

**Check API logs:**
```bash
docker compose logs fx-api
```

**Test database connection:**
```bash
curl http://localhost:8000/health
```

**Restart API:**
```bash
docker compose restart fx-api
```

**Check PostgreSQL is accessible:**
```bash
docker compose exec fx-api ping postgres
```

---

### 10. Producer Not Fetching Rates

#### Symptom
```
Failed to fetch FX rates: HTTP 429
```

#### Solutions

**Rate limiting:**
The free API has limits. Wait a few minutes.

**Check API key (if using paid tier):**
Edit `producer/fx_producer.py` and add your key.

**Verify internet connectivity:**
```bash
docker compose exec fx-producer ping api.exchangerate-api.com
```

**View producer logs:**
```bash
docker compose logs fx-producer
```

---

### 11. Consumer Not Processing Messages

#### Symptom
Consumer running but no rate updates shown.

#### Solutions

**Check Kafka topic has messages:**
```bash
docker compose exec fx-kafka kafka-console-consumer \
  --bootstrap-server localhost:29092 \
  --topic fx-rates \
  --from-beginning \
  --max-messages 1
```

**Verify consumer is subscribed:**
```bash
docker compose logs fx-consumer | findstr "Subscribed"
```

**Check consumer group lag:**
```bash
docker compose exec fx-kafka kafka-consumer-groups \
  --bootstrap-server localhost:29092 \
  --describe \
  --group rate-processor-group
```

**Reset consumer offset:**
```bash
docker compose stop fx-consumer
docker compose exec fx-kafka kafka-consumer-groups \
  --bootstrap-server localhost:29092 \
  --group rate-processor-group \
  --reset-offsets \
  --to-earliest \
  --topic fx-rates \
  --execute
docker compose start fx-consumer
```

---

### 12. Alert Engine Not Triggering Alerts

#### Symptom
Created alerts via API but not triggering.

#### Solutions

**Verify alert-engine is running:**
```bash
docker compose ps alert-engine
```

**Check alert criteria:**
```bash
# Get current rate
curl http://localhost:8000/rates

# Ensure threshold will be crossed
# Example: If USD/EUR is 0.847, set alert for "below 0.85"
```

**View alert-engine logs:**
```bash
docker compose logs -f alert-engine
```

**Check database has active alerts:**
```bash
curl http://localhost:8000/alerts
```

---

### 13. Multiprocessing Not Working

#### Symptom
```
OSError: [Errno 24] Too many open files
```

#### Solution (Linux/Mac)
```bash
# Increase file descriptor limit
ulimit -n 4096
```

#### Solution (Windows)
Usually not an issue. If persists:
```bash
# Reduce pool size in consumer/rate_processor.py
self.pool = Pool(processes=2)  # Instead of 4
```

---

### 14. Build Fails During docker compose up

#### Symptom
```
ERROR: failed to solve: process "/bin/sh -c pip install" did not complete successfully
```

#### Solutions

**Clear Docker cache:**
```bash
docker builder prune -af
docker compose build --no-cache
docker compose up -d
```

**Check disk space:**
```bash
docker system df
```

**Clean up old images:**
```bash
docker system prune -a
```

---

### 15. Containers Keep Restarting

#### Symptom
```
STATUS: Restarting (1) Less than a second ago
```

#### Solutions

**View crash logs:**
```bash
docker compose logs <service-name>
```

**Common causes:**
- Missing environment variable
- Database not ready (needs depends_on)
- Port conflict
- Out of memory

**Stop restart loop:**
```bash
# Temporarily remove restart policy
docker compose stop <service-name>
docker compose logs <service-name>
# Fix issue, then:
docker compose start <service-name>
```

---

## 🧹 Clean Slate Reset

When all else fails, start fresh:

```bash
# Stop all services
docker compose down

# Remove ALL data (including volumes)
docker compose down -v

# Remove images
docker compose down --rmi all

# Clean Docker system
docker system prune -af
docker volume prune -f

# Rebuild from scratch
docker compose up -d --build

# Wait for services to initialize
sleep 60
docker compose ps
```

---

## 📊 Monitoring Commands

### Check Service Health

```bash
# All services
docker compose ps

# Specific service details
docker inspect fx-consumer

# Resource usage
docker stats --no-stream
```

### Database Queries

```bash
# PostgreSQL
docker compose exec postgres psql -U fxuser -d fxrates -c "SELECT COUNT(*) FROM fx_rates;"

# Redis
docker compose exec redis redis-cli INFO stats

# Elasticsearch
curl http://localhost:9200/_cat/indices?v
curl http://localhost:9200/fx-rates/_count
```

### Network Debugging

```bash
# Test connectivity between services
docker compose exec fx-consumer ping postgres
docker compose exec fx-consumer ping redis
docker compose exec fx-consumer ping elasticsearch
docker compose exec fx-consumer ping kafka

# Check network
docker network ls
docker network inspect forex-rate--monitor-and-alert-system_fx-network
```

---

## 🆘 Still Having Issues?

### Collect Debug Info

```bash
# Create debug log file
docker compose ps > debug.log
docker compose logs >> debug.log
docker stats --no-stream >> debug.log

# Check the log file for errors
notepad debug.log
```

### Report Issue

Include in your issue report:
1. Output of `docker compose ps`
2. Relevant logs from `docker compose logs <service>`
3. Your `.env` file (remove sensitive data)
4. Docker version: `docker --version`
5. OS and version
6. Steps to reproduce

---

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Kafka Troubleshooting](https://kafka.apache.org/documentation/#troubleshooting)
- [Elasticsearch Common Issues](https://www.elastic.co/guide/en/elasticsearch/reference/current/troubleshooting.html)
- [FastAPI Debugging](https://fastapi.tiangolo.com/tutorial/debugging/)

---

**💡 Tip**: Most issues are resolved by restarting the affected service or increasing Docker resources.
