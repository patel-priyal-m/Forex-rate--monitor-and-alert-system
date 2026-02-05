# System Architecture

Comprehensive architecture documentation for the FX Rate Monitoring System.

## 🎯 Overview

The system implements a **microservices architecture** using Docker containers, with Kafka as the central message broker. It demonstrates real-time data processing, multi-level parallelism, and production-grade monitoring capabilities.

---

## 📐 High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                     External Services                               │
│  ┌──────────────────────────────────────────────────┐              │
│  │  exchangerate-api.com (FX Rate Provider)         │              │
│  └──────────────────────────────────────────────────┘              │
└────────────────────────┬───────────────────────────────────────────┘
                         │ HTTP GET (every 30s)
                         ▼
┌────────────────────────────────────────────────────────────────────┐
│                     Producer Service                                │
│  ┌──────────────────────────────────────────────────┐              │
│  │  fx-producer                                     │              │
│  │  - Fetch 166 currencies                          │              │
│  │  - Transform to tracked pairs (8)                │              │
│  │  - Publish JSON to Kafka                         │              │
│  └──────────────────────────────────────────────────┘              │
└────────────────────────┬───────────────────────────────────────────┘
                         │ Kafka Producer
                         ▼
┌────────────────────────────────────────────────────────────────────┐
│                     Message Broker Layer                            │
│  ┌──────────────────────────────────────────────────┐              │
│  │  Apache Kafka (KRaft Mode)                       │              │
│  │  - Topic: fx-rates                               │              │
│  │  - Topic: fx-alerts                              │              │
│  │  - No Zookeeper dependency                       │              │
│  └──────────────────────────────────────────────────┘              │
└────────┬──────────────────────────────────────┬────────────────────┘
         │ Kafka Consumer                       │ Kafka Consumer
         ▼                                      ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│   Consumer Service           │    │   Alert Engine Service       │
│  ┌────────────────────────┐  │    │  ┌────────────────────────┐  │
│  │  fx-consumer           │  │    │  │  alert-engine          │  │
│  │  - Process rates       │  │    │  │  - Monitor thresholds  │  │
│  │  - Multiprocessing(4)  │  │    │  │  - Multiprocessing(2)  │  │
│  │  - Calculate volatility│  │    │  │  - Trigger alerts      │  │
│  │  - Cross-rate calc     │  │    │  │  - Log history         │  │
│  └────────────────────────┘  │    │  └────────────────────────┘  │
└────────┬─────┬──────┬────────┘    └───────┬──────┬───────────────┘
         │     │      │                     │      │
         ▼     ▼      ▼                     ▼      ▼
┌─────────┐ ┌────┐ ┌──────────────┐  ┌─────────┐ ┌──────────────┐
│PostgreSQL│ │Redis│ │Elasticsearch │  │PostgreSQL│ │Elasticsearch │
│ (Rates) │ │Cache│ │  (Rates)     │  │ (Alerts)│ │  (Alerts)    │
└─────────┘ └────┘ └──────────────┘  └─────────┘ └──────────────┘
                           │                              │
                           └──────────┬───────────────────┘
                                      ▼
                           ┌──────────────────┐
                           │     Kibana       │
                           │   Dashboards     │
                           │  (Port: 5601)    │
                           └──────────────────┘
                                      ▲
                           ┌──────────┴───────┐
                           │                  │
                      ┌────────┐         ┌────────┐
                      │ Users  │         │FastAPI │
                      │Browser │         │REST API│
                      └────────┘         │ :8000  │
                                         └────────┘
                                              │
                                              ▼
                                  ┌────────────────────┐
                                  │PostgreSQL + Redis  │
                                  │   (Read Access)    │
                                  └────────────────────┘
```

---

## 🔧 Component Details

### 1. Producer Service (fx-producer)

**Purpose**: Fetch FX rates from external API and publish to Kafka

**Technology**:
- Python 3.11
- `requests` library for HTTP calls
- `confluent-kafka` producer

**Flow**:
1. Every 30 seconds, fetch exchange rates from API
2. Extract tracked currency pairs (8 configured pairs)
3. Create JSON message with timestamp, base currency, rates
4. Publish to Kafka topic `fx-rates`
5. Log success/failure

**Message Format**:
```json
{
  "timestamp": "2026-02-04T10:30:00Z",
  "base": "USD",
  "rates": {
    "USD/EUR": 0.847,
    "USD/GBP": 0.789,
    "USD/JPY": 110.25,
    "USD/CAD": 1.258,
    "USD/AUD": 1.312,
    "USD/CHF": 0.912,
    "USD/CNY": 6.456,
    "USD/INR": 74.123
  },
  "source": "exchangerate-api.com"
}
```

**Configuration**:
- `TRACKED_CURRENCIES`: Currency codes to monitor
- `KAFKA_TOPIC`: Target Kafka topic
- Fetch interval: 30 seconds (configurable)

---

### 2. Kafka Message Broker

**Purpose**: Decouple producers and consumers, enable scalability

**Technology**:
- Apache Kafka 3.5 (KRaft mode)
- No Zookeeper required
- Docker: `confluentinc/cp-kafka:7.5.0`

**Topics**:
1. **fx-rates**: Rate updates from producer
   - Partitions: 1
   - Replication: 1 (single-node setup)
   - Retention: 7 days

2. **fx-alerts**: Triggered alerts from alert-engine
   - Partitions: 1
   - Replication: 1
   - Retention: 30 days

**Why KRaft Mode?**
- Simplified architecture (no Zookeeper)
- Faster startup time
- Better scalability
- Production-ready since Kafka 3.3+

**Ports**:
- `9092`: External access (host)
- `29092`: Internal access (Docker network)

---

### 3. Consumer Service (fx-consumer)

**Purpose**: Process rate messages and persist data

**Technology**:
- Python 3.11
- `confluent-kafka` consumer
- `multiprocessing.Pool(4)` for parallel processing
- SQLAlchemy ORM
- Redis client
- Elasticsearch client

**Processing Pipeline**:

```
Message Received
    ↓
1. Store in PostgreSQL (historical persistence)
   - Table: fx_rates (timestamp, pair, rate)
    ↓
2. Cache in Redis (fast access)
   - Key pattern: rate:{pair}
   - TTL: 3600 seconds
    ↓
3. Calculate Volatility (rolling std dev)
   - Window: 20 rates
   - Store in Redis: volatility:{pair}
    ↓
4. Index to Elasticsearch (visualization)
   - Index: fx-rates
   - Bulk API for performance
    ↓
5. Calculate Cross-Rates (multiprocessing)
   - Pool(4) parallel workers
   - 28 cross-rates from 8 pairs
   - Store in Redis: cross_rate:{pair}
    ↓
Processing Complete (~24ms total)
```

**Multiprocessing Strategy**:
```python
# 4 worker processes calculate cross-rates in parallel
pool = Pool(processes=4)

# Example: 8 pairs → 28 combinations
# USD/EUR + USD/GBP → EUR/GBP
# Split across 4 workers for 4x speedup
results = pool.map(calculate_cross_rate, combinations)
```

**Consumer Group**: `rate-processor-group`
- Ensures at-least-once delivery
- Offset tracking for fault tolerance

---

### 4. Alert Engine Service (alert-engine)

**Purpose**: Monitor rates and trigger user-defined alerts

**Technology**:
- Python 3.11
- `multiprocessing.Pool(2)` for parallel alert checking
- PostgreSQL for alert definitions and history

**Flow**:
```
1. Subscribe to fx-rates topic
    ↓
2. For each message, query active alerts from DB
    ↓
3. Check alerts in parallel (Pool(2))
   - Compare current rate vs threshold
   - Conditions: "above" or "below"
    ↓
4. If triggered:
   - Log to alert_history table
   - Index to Elasticsearch (fx-alerts)
   - Publish to fx-alerts Kafka topic
    ↓
5. Rate limiting: Cooldown period per alert
```

**Multiprocessing Example**:
```python
# 2 workers check different alerts simultaneously
pool = Pool(processes=2)

# Each worker gets subset of alerts to check
alert_checks = [(alert_id, pair, condition, threshold, rate), ...]
results = pool.map(check_alert, alert_checks)
```

**Database Schema**:
```sql
-- User-defined alerts
CREATE TABLE user_alerts (
    id SERIAL PRIMARY KEY,
    pair VARCHAR(10),
    condition VARCHAR(10), -- 'above' or 'below'
    threshold FLOAT,
    active BOOLEAN DEFAULT TRUE
);

-- Alert trigger history
CREATE TABLE alert_history (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER REFERENCES user_alerts(id),
    pair VARCHAR(10),
    rate FLOAT,
    message TEXT,
    triggered_at TIMESTAMP
);
```

---

### 5. PostgreSQL Database

**Purpose**: Persistent storage for rates and alerts

**Technology**:
- PostgreSQL 15 (Alpine)
- Port: 5432

**Schema**:

```sql
-- Historical FX rates
CREATE TABLE fx_rates (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    pair VARCHAR(10) NOT NULL,
    rate FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pair_timestamp (pair, timestamp DESC)
);

-- User-defined alerts
CREATE TABLE user_alerts (
    id SERIAL PRIMARY KEY,
    pair VARCHAR(10) NOT NULL,
    condition VARCHAR(10) NOT NULL,
    threshold FLOAT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alert trigger history
CREATE TABLE alert_history (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER REFERENCES user_alerts(id),
    pair VARCHAR(10) NOT NULL,
    rate FLOAT NOT NULL,
    message TEXT,
    triggered_at TIMESTAMP NOT NULL
);
```

**Indexes**:
- `fx_rates`: (pair, timestamp DESC) for fast historical queries
- `user_alerts`: (active) for filtering active alerts
- `alert_history`: (triggered_at DESC) for recent alerts

---

### 6. Redis Cache

**Purpose**: Fast access to current rates and volatility

**Technology**:
- Redis 7 (Alpine)
- Port: 6379

**Data Structures**:

```
# Current rates (string)
rate:USD/EUR → "0.847"
rate:USD/GBP → "0.789"
TTL: 3600 seconds

# Rate history (list, FIFO, max 20)
history:USD/EUR → ["0.847", "0.848", "0.846", ...]

# Volatility (string)
volatility:USD/EUR → "0.001234"
TTL: 3600 seconds

# Cross-rates (string)
cross_rate:EUR/GBP → "0.9316"
TTL: 3600 seconds
```

**Why Redis?**
- Sub-millisecond read latency
- Automatic expiration (TTL)
- List operations for sliding window
- Reduces database load

---

### 7. Elasticsearch

**Purpose**: Time-series data storage for Kibana

**Technology**:
- Elasticsearch 8.11.0
- Port: 9200
- Single-node cluster

**Indices**:

**fx-rates** (rate updates):
```json
{
  "mappings": {
    "properties": {
      "timestamp": {"type": "date"},
      "pair": {"type": "keyword"},
      "rate": {"type": "float"},
      "volatility": {"type": "float"},
      "source": {"type": "keyword"}
    }
  }
}
```

**fx-alerts** (triggered alerts):
```json
{
  "mappings": {
    "properties": {
      "triggered_at": {"type": "date"},
      "alert_id": {"type": "integer"},
      "pair": {"type": "keyword"},
      "condition": {"type": "keyword"},
      "threshold": {"type": "float"},
      "current_rate": {"type": "float"},
      "message": {"type": "text"}
    }
  }
}
```

**Bulk Indexing**:
- Consumer indexes 8 rates per message using bulk API
- ~10ms per batch
- Reduces network overhead vs individual inserts

---

### 8. Kibana

**Purpose**: Real-time visualization and dashboards

**Technology**:
- Kibana 8.11.0
- Port: 5601

**Features**:
- Data views for fx-rates and fx-alerts indices
- Time-series line charts
- Metric visualizations
- Alert history tables
- Auto-refresh (30s)

**Access**: http://localhost:5601

See [Kibana Setup Guide](KIBANA_SETUP.md) for dashboard creation.

---

### 9. FastAPI REST Service

**Purpose**: HTTP API for querying data and managing alerts

**Technology**:
- FastAPI (async Python web framework)
- Uvicorn ASGI server
- Port: 8000

**Architecture**:
```
HTTP Request
    ↓
FastAPI Router
    ↓
Business Logic
    ↓
┌────────────┬────────────┐
│ PostgreSQL │   Redis    │
│  (SQLAlch.)│  (Client)  │
└────────────┴────────────┘
    ↓
JSON Response
```

**Features**:
- Automatic OpenAPI/Swagger docs
- Async database queries
- CORS enabled
- Health check endpoint

**Access**: http://localhost:8000/docs

See [API Documentation](API.md) for endpoints.

---

## 🔄 Data Flow Scenarios

### Scenario 1: Rate Update

```
1. [00:00] Producer fetches rates from API
2. [00:01] Producer publishes to Kafka fx-rates topic
3. [00:01] Consumer receives message
4. [00:01] Consumer stores in PostgreSQL (parallel)
5. [00:01] Consumer caches in Redis (parallel)
6. [00:01] Consumer calculates volatility
7. [00:01] Consumer indexes to Elasticsearch
8. [00:01] Consumer calculates cross-rates (Pool(4))
9. [00:01] Alert Engine checks thresholds (Pool(2))
10. [00:01] Kibana displays updated dashboard

Total: ~24ms processing time
```

### Scenario 2: Alert Creation & Trigger

```
1. User creates alert via API: POST /alerts
   {
     "pair": "USD/EUR",
     "condition": "below",
     "threshold": 0.85
   }

2. API stores in PostgreSQL user_alerts table

3. On next rate update (30s):
   a. Alert Engine queries active alerts
   b. Checks USD/EUR rate (0.847) vs threshold (0.85)
   c. Condition met: 0.847 < 0.85
   d. Triggers alert:
      - Logs to alert_history
      - Indexes to Elasticsearch fx-alerts
      - Publishes to Kafka fx-alerts topic

4. Alert visible in:
   - API: GET /alerts/history
   - Kibana: Alert History dashboard
```

### Scenario 3: Historical Query

```
User Request: GET /rates/USD%2FEUR/history?limit=100

1. FastAPI receives request
2. Query PostgreSQL:
   SELECT * FROM fx_rates 
   WHERE pair = 'USD/EUR'
   ORDER BY timestamp DESC
   LIMIT 100

3. Return JSON with timestamps and rates
4. Response time: ~50ms
```

---

## 🎯 Design Patterns

### 1. Producer-Consumer Pattern
- **Producer**: Fetches and publishes data
- **Message Broker**: Kafka decouples services
- **Consumers**: Process independently

**Benefits**:
- Loose coupling
- Scalability (add more consumers)
- Fault tolerance (message persistence)

### 2. Multiprocessing Pool Pattern
```python
# CPU-bound tasks distributed across workers
with Pool(4) as pool:
    results = pool.map(calculate, data_chunks)
```

**Used For**:
- Cross-rate calculations (CPU-intensive)
- Alert checking (parallel I/O)

### 3. Cache-Aside Pattern
```python
# Check cache first
rate = redis.get(f"rate:{pair}")
if rate is None:
    # Cache miss - query database
    rate = db.query(pair)
    redis.set(f"rate:{pair}", rate, ex=3600)
return rate
```

### 4. Health Check Pattern
All services expose health endpoints:
- Kafka: `curl localhost:9092`
- PostgreSQL: `psql -c "SELECT 1"`
- Redis: `redis-cli PING`
- API: `GET /health`

### 5. Graceful Degradation
```python
try:
    es_client.index(data)
except Exception:
    logger.warning("Elasticsearch unavailable, continuing...")
    # System continues without ES indexing
```

---

## 📊 Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| Message Processing | ~24ms | Consumer end-to-end |
| API Response Time | <50ms | Average for GET requests |
| Cross-rate Calculation | ~4ms | 28 rates with Pool(4) |
| ES Bulk Indexing | ~10ms | 8 documents |
| Data Ingestion Rate | 8 rates/30s | Configurable |
| Database Writes | ~5ms | PostgreSQL insert |
| Redis Operations | <1ms | Get/Set operations |

**Bottlenecks**:
- External API rate limits (30s minimum interval)
- PostgreSQL write throughput (can scale with read replicas)
- Single Kafka partition (can add partitions for parallelism)

**Optimization Opportunities**:
- Batch database inserts
- Connection pooling
- Redis pipelining
- Kafka partition strategy

---

## 🔐 Security Considerations

**Current State** (Development):
- No authentication (local development)
- Elasticsearch security disabled
- PostgreSQL local access only

**Production Recommendations**:
1. **API Authentication**
   - JWT tokens
   - API keys
   - OAuth2

2. **Database Security**
   - SSL/TLS connections
   - Encrypted passwords
   - Network isolation

3. **Kafka Security**
   - SASL authentication
   - SSL encryption
   - ACLs for topics

4. **Elasticsearch Security**
   - Enable X-Pack security
   - Role-based access control
   - API keys for Kibana

---

## 📈 Scalability

### Horizontal Scaling

**Add More Consumers**:
```bash
docker compose up -d --scale fx-consumer=3
```
- Kafka automatically distributes partitions
- Increases throughput 3x

**Add Kafka Partitions**:
```bash
kafka-topics --alter --topic fx-rates --partitions 3
```
- Enables parallel message processing

### Vertical Scaling

**Increase Resources**:
```yaml
# docker-compose.yml
services:
  postgres:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

### Database Scaling

**Read Replicas**:
- PostgreSQL streaming replication
- Read queries → replicas
- Write queries → primary

**Partitioning**:
```sql
-- Partition by month
CREATE TABLE fx_rates_2026_02 PARTITION OF fx_rates
FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

---

## 🧪 Testing Strategy

### Unit Tests
```bash
pytest tests/test_producer.py
pytest tests/test_consumer.py
```

### Integration Tests
```bash
# Test full pipeline
pytest tests/test_integration.py
```

### Load Tests
```bash
# Simulate high message volume
python tests/load_test.py --rate 100 --duration 300
```

---

## 📚 Technology Choices

| Component | Technology | Why? |
|-----------|-----------|------|
| Message Broker | Kafka | Industry standard, high throughput |
| Database | PostgreSQL | ACID, complex queries, reliability |
| Cache | Redis | Sub-ms latency, data structures |
| API | FastAPI | Async, auto-docs, performance |
| Visualization | Kibana | Time-series focus, Elasticsearch integration |
| Container | Docker | Portability, reproducibility |
| Language | Python | Ecosystem, readability, productivity |

---

## 🔍 Monitoring & Observability

**Metrics to Track**:
- Message lag (Kafka consumer)
- Processing time per message
- Database query time
- Redis hit rate
- API response times
- Error rates

**Tools**:
- Docker stats: `docker stats`
- Kafka consumer lag: `kafka-consumer-groups --describe`
- PostgreSQL queries: `pg_stat_statements`
- Redis info: `redis-cli INFO stats`
- API metrics: FastAPI middleware

---

## 📖 Related Documentation

- **[Quick Start](QUICKSTART.md)**: Get the system running
- **[API Documentation](API.md)**: REST endpoint details
- **[Kibana Setup](KIBANA_SETUP.md)**: Dashboard configuration
- **[Troubleshooting](TROUBLESHOOTING.md)**: Common issues

---

**Last Updated**: February 2026  
**Author**: Priyal
