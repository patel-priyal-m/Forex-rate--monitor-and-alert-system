# Deployment Guide

Complete guide for deploying the FX Rate Monitoring System in different environments.

## Table of Contents
1. [Local Development](#local-development)
2. [Docker Compose (Production)](#docker-compose-production)
3. [Cloud Deployment](#cloud-deployment)
4. [Kubernetes](#kubernetes)
5. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Local Development

### Prerequisites
- Python 3.11+
- Docker Desktop
- Git

### Setup

1. **Clone Repository**
   ```bash
   git clone https://github.com/your-username/Forex-rate--monitor-and-alert-system.git
   cd Forex-rate--monitor-and-alert-system
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Start Infrastructure Services**
   ```bash
   # Start only infrastructure (Kafka, PostgreSQL, Redis, Elasticsearch)
   docker compose up -d kafka postgres redis elasticsearch kibana
   ```

6. **Run Application Components**
   ```bash
   # Terminal 1: Start Producer
   python producer/fx_producer.py
   
   # Terminal 2: Start Consumer
   python consumer/rate_processor.py
   
   # Terminal 3: Start Alert Engine
   python consumer/alert_engine.py
   
   # Terminal 4: Start API
   uvicorn api.main:app --reload --port 8000
   ```

---

## Docker Compose (Production)

### Full Stack Deployment

1. **Prepare Environment**
   ```bash
   cp .env.example .env
   nano .env  # Update production values
   ```

2. **Start All Services**
   ```bash
   docker compose up -d
   ```

3. **Verify Deployment**
   ```bash
   # Check all containers are running
   docker compose ps
   
   # Check logs
   docker compose logs -f
   
   # Test API
   curl http://localhost:8000/health
   ```

4. **Scale Services** (Optional)
   ```bash
   # Scale consumers for higher throughput
   docker compose up -d --scale fx-consumer=3
   ```

### Production Configuration

**Update `.env` for production:**
```bash
# Strong passwords
POSTGRES_PASSWORD=<generate-strong-password>
REDIS_PASSWORD=<generate-strong-password>

# Production settings
LOG_LEVEL=WARNING
ENVIRONMENT=production
DEBUG=False

# Performance tuning
CROSS_RATE_WORKERS=8
ALERT_WORKERS=4
DB_POOL_SIZE=10
```

---

## Cloud Deployment

### AWS Deployment (ECS/Fargate)

1. **Build and Push Images**
   ```bash
   # Build images
   docker compose build
   
   # Tag for ECR
   docker tag fx-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/fx-api:latest
   docker tag fx-producer:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/fx-producer:latest
   docker tag fx-consumer:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/fx-consumer:latest
   
   # Push to ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/fx-api:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/fx-producer:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/fx-consumer:latest
   ```

2. **Set Up Managed Services**
   - **RDS PostgreSQL**: Create PostgreSQL 15 instance
   - **ElastiCache Redis**: Create Redis 7 cluster
   - **MSK**: Create managed Kafka cluster
   - **OpenSearch**: Create Elasticsearch domain

3. **Deploy ECS Tasks**
   - Create ECS cluster
   - Create task definitions for each service
   - Create services with load balancers
   - Configure auto-scaling

4. **Configure Networking**
   - VPC with public/private subnets
   - Security groups for service communication
   - NAT gateway for outbound traffic
   - Application Load Balancer for API

### Azure Deployment (Container Instances)

1. **Create Resource Group**
   ```bash
   az group create --name fx-monitoring --location eastus
   ```

2. **Deploy Managed Services**
   ```bash
   # PostgreSQL
   az postgres flexible-server create \
     --resource-group fx-monitoring \
     --name fx-postgres \
     --version 15
   
   # Redis
   az redis create \
     --resource-group fx-monitoring \
     --name fx-redis \
     --sku Basic
   ```

3. **Deploy Containers**
   ```bash
   az container create \
     --resource-group fx-monitoring \
     --name fx-api \
     --image <your-registry>/fx-api:latest \
     --ports 8000 \
     --environment-variables \
       POSTGRES_HOST=<postgres-host> \
       REDIS_HOST=<redis-host>
   ```

### GCP Deployment (Cloud Run)

1. **Build and Push to GCR**
   ```bash
   gcloud builds submit --tag gcr.io/<project-id>/fx-api
   gcloud builds submit --tag gcr.io/<project-id>/fx-producer
   gcloud builds submit --tag gcr.io/<project-id>/fx-consumer
   ```

2. **Deploy Services**
   ```bash
   # API Service
   gcloud run deploy fx-api \
     --image gcr.io/<project-id>/fx-api \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   
   # Producer as Cloud Run Jobs
   gcloud run jobs create fx-producer \
     --image gcr.io/<project-id>/fx-producer \
     --region us-central1
   ```

---

## Kubernetes

### Deploy to Kubernetes Cluster

1. **Create Namespace**
   ```bash
   kubectl create namespace fx-monitoring
   ```

2. **Create Secrets**
   ```bash
   kubectl create secret generic fx-secrets \
     --from-literal=postgres-password=<password> \
     --from-literal=redis-password=<password> \
     -n fx-monitoring
   ```

3. **Deploy Services**
   ```bash
   kubectl apply -f k8s/postgres.yaml
   kubectl apply -f k8s/redis.yaml
   kubectl apply -f k8s/kafka.yaml
   kubectl apply -f k8s/elasticsearch.yaml
   kubectl apply -f k8s/producer.yaml
   kubectl apply -f k8s/consumer.yaml
   kubectl apply -f k8s/api.yaml
   ```

4. **Verify Deployment**
   ```bash
   kubectl get pods -n fx-monitoring
   kubectl get services -n fx-monitoring
   ```

5. **Access API**
   ```bash
   kubectl port-forward svc/fx-api 8000:8000 -n fx-monitoring
   ```

---

## Monitoring & Maintenance

### Health Checks

**API Health Check:**
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-02-05T00:00:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "elasticsearch": "healthy"
  }
}
```

### Log Monitoring

**Docker Compose:**
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f fx-consumer

# Last 100 lines
docker compose logs --tail=100 fx-api
```

**Kubernetes:**
```bash
# Pod logs
kubectl logs -f <pod-name> -n fx-monitoring

# Stream logs from all pods
kubectl logs -f -l app=fx-consumer -n fx-monitoring
```

### Metrics & Alerts

1. **Prometheus Integration**
   - Add Prometheus exporters
   - Configure scrape targets
   - Set up alerting rules

2. **CloudWatch (AWS)**
   - Enable container insights
   - Create custom metrics
   - Set up alarms

3. **Key Metrics to Monitor**
   - Message processing rate
   - API response times
   - Database connection pool usage
   - Redis cache hit rate
   - Error rates

### Backup & Recovery

**Database Backup:**
```bash
# PostgreSQL backup
docker compose exec postgres pg_dump -U fxuser fxrates > backup.sql

# Restore
docker compose exec -T postgres psql -U fxuser fxrates < backup.sql
```

**Elasticsearch Backup:**
```bash
# Create snapshot repository
curl -X PUT "localhost:9200/_snapshot/backup" -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/backup"
  }
}'

# Create snapshot
curl -X PUT "localhost:9200/_snapshot/backup/snapshot_1?wait_for_completion=true"
```

### Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

### Maintenance Tasks

**Weekly:**
- Check service health
- Review error logs
- Monitor disk usage
- Verify backups

**Monthly:**
- Update dependencies
- Review security advisories
- Optimize database indices
- Clean up old data

**Quarterly:**
- Security audit
- Performance tuning
- Load testing
- Documentation updates

---

## Best Practices

1. **Security**
   - Use strong passwords
   - Enable TLS/SSL
   - Implement authentication
   - Regular security updates

2. **Performance**
   - Monitor resource usage
   - Scale horizontally when needed
   - Use connection pooling
   - Implement caching strategies

3. **Reliability**
   - Regular backups
   - Health checks
   - Graceful degradation
   - Circuit breakers

4. **Observability**
   - Centralized logging
   - Distributed tracing
   - Metrics collection
   - Alerting rules

---

## Support

- **Documentation**: See [docs/](docs/) folder
- **Issues**: GitHub Issues
- **Questions**: Open a discussion on GitHub

---

**Last Updated**: February 2026
