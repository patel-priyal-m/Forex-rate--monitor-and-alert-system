# Foreign Exchange Rate Monitoring System

A real-time FX rate monitoring system demonstrating enterprise-grade architecture with Kafka streaming, microservices, and Docker containerization.

## 🎯 Project Overview

This system fetches live foreign exchange rates, streams them through Kafka, processes the data, and provides monitoring capabilities. Built as a learning project to demonstrate skills in distributed systems, message streaming, and cloud-native architecture.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Environment                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌─────────────────┐                │
│  │   Producer   │─────►│  Kafka (KRaft)  │                │
│  │  Container   │      │   Port: 9092    │                │
│  │              │      └────────┬────────┘                │
│  │ - Fetch FX   │               │                          │
│  │   rates API  │               │                          │
│  │ - Publish to │               │                          │
│  │   Kafka      │               │                          │
│  └──────────────┘               │                          │
│                                 │                          │
│                                 ▼                          │
│                        ┌─────────────────┐                │
│                        │    Consumer     │                │
│                        │   Container     │                │
│                        │                 │                │
│                        │ - Read from     │                │
│                        │   Kafka         │                │
│                        │ - Process rates │                │
│                        │ - Display data  │                │
│                        └────┬────────┬───┘                │
│                             │        │                    │
│                             ▼        ▼                    │
│                    ┌───────────┐  ┌──────┐               │
│                    │PostgreSQL │  │Redis │               │
│                    │Port: 5432 │  │:6379 │               │
│                    └───────────┘  └──────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Message Broker** | Apache Kafka (KRaft mode) | Real-time message streaming |
| **Kafka Client** | confluent-kafka-python | High-performance Python client |
| **Database** | PostgreSQL 15 | Historical data storage |
| **Cache** | Redis 7 | Latest rates caching |
| **API** | FastAPI | REST endpoints (Phase 3) |
| **Dashboard** | Streamlit | Interactive UI (Phase 4) |
| **Container** | Docker & Docker Compose | Service orchestration |
| **Language** | Python 3.11 | Application logic |

## 📊 Data Flow

1. **Producer** fetches rates from `exchangerate-api.com` every 30 seconds
2. **Publishes** to Kafka topic `fx-rates` with JSON format
3. **Consumer** subscribes to topic and processes messages
4. **Displays** formatted rate updates in real-time
5. **(Phase 2)** Stores historical data in PostgreSQL
6. **(Phase 2)** Caches latest rates in Redis

## 🚀 Quick Start

### Prerequisites

- Docker Desktop installed and running
- Docker Compose v2.0+
- Git
- 8GB RAM minimum

### 1. Clone Repository

```bash
git clone https://github.com/your-username/Forex-rate--monitor-and-alert-system.git
cd Forex-rate--monitor-and-alert-system
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` if needed (default values work for local development).

### 3. Start All Services

```bash
docker-compose up --build
```

This will:
- ✅ Start Kafka broker (KRaft mode, no Zookeeper)
- ✅ Start PostgreSQL database
- ✅ Start Redis cache
- ✅ Build and start FX Producer
- ✅ Build and start FX Consumer

### 4. View Logs

**Producer logs:**
```bash
docker-compose logs -f fx-producer
```

**Consumer logs:**
```bash
docker-compose logs -f fx-consumer
```

**All services:**
```bash
docker-compose logs -f
```

### 5. Stop Services

```bash
docker-compose down
```

**To remove volumes (delete all data):**
```bash
docker-compose down -v
```

## 📝 Sample Output

### Producer Output:
```
2026-02-04 15:30:45 - INFO - Starting FX Producer...
2026-02-04 15:30:45 - INFO - Kafka: kafka:29092, Topic: fx-rates
2026-02-04 15:30:45 - INFO - Fetching rates from https://api.exchangerate-api.com/v4/latest/USD
2026-02-04 15:30:46 - INFO - Successfully fetched rates for 160 currencies
2026-02-04 15:30:46 - INFO - Published message with 8 rates at 2026-02-04T15:30:45.123456Z
2026-02-04 15:30:46 - INFO - Waiting 30 seconds until next fetch...
```

### Consumer Output:
```
============================================================
📊 FX Rate Update Received
============================================================
🕐 Timestamp: 2026-02-04T15:30:45.123456Z
💵 Base Currency: USD
📡 Source: exchangerate-api.com
📈 Rates (8 pairs):
   USD/AUD      =     1.5200
   USD/CAD      =     1.3500
   USD/CHF      =     0.8800
   USD/CNY      =     7.2400
   USD/EUR      =     0.9200
   USD/GBP      =     0.7900
   USD/INR      =    83.1500
   USD/JPY      =   149.5000
============================================================
```

## 🔧 Configuration

### Environment Variables

Edit `.env` file:

```bash
# Kafka Configuration
KAFKA_TOPIC=fx-rates                    # Topic name
KAFKA_GROUP_ID=rate-processor-group     # Consumer group

# API Configuration
FX_API_URL=https://api.exchangerate-api.com/v4/latest/USD
FETCH_INTERVAL=30                       # Seconds between fetches

# Tracked Currencies
TRACKED_CURRENCIES=EUR,GBP,JPY,CAD,AUD,CHF,CNY,INR

# Logging
LOG_LEVEL=INFO                          # DEBUG, INFO, WARNING, ERROR
```

## 🧪 Testing

### Verify Kafka is Running

```bash
docker exec -it fx-kafka kafka-topics --bootstrap-server localhost:9092 --list
```

Should show topic: `fx-rates`

### Check Messages in Topic

```bash
docker exec -it fx-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic fx-rates \
  --from-beginning
```

### Check PostgreSQL Connection

```bash
docker exec -it fx-postgres psql -U fxuser -d fxdb -c "\dt"
```

### Check Redis Connection

```bash
docker exec -it fx-redis redis-cli ping
```

## 🐛 Troubleshooting

### Producer not starting

**Issue:** `Failed to create Kafka producer`

**Solution:**
```bash
# Wait for Kafka to be ready (30-60 seconds after docker-compose up)
docker-compose logs kafka

# Check healthcheck status
docker ps
```

### Consumer not receiving messages

**Issue:** Consumer shows no output

**Solution:**
```bash
# Check producer is publishing
docker-compose logs fx-producer | grep "Published"

# Check Kafka has messages
docker exec -it fx-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic fx-rates \
  --max-messages 1
```

### Port already in use

**Issue:** `Bind for 0.0.0.0:9092 failed: port is already allocated`

**Solution:**
```bash
# Change ports in .env
POSTGRES_PORT=5433  # Instead of 5432
REDIS_PORT=6380     # Instead of 6379

# Or stop conflicting services
docker ps  # Find containers using those ports
docker stop <container_id>
```

## 📁 Project Structure

```
Forex-rate--monitor-and-alert-system/
├── .env                    # Environment configuration
├── .env.example           # Environment template
├── .gitignore             # Git exclusions
├── docker-compose.yml     # Service orchestration
├── requirements.txt       # Python dependencies
├── README.md              # This file
│
├── producer/
│   ├── Dockerfile         # Producer container
│   ├── __init__.py        # Package marker
│   └── fx_producer.py     # Fetch & publish rates
│
├── consumer/
│   ├── Dockerfile         # Consumer container
│   ├── __init__.py        # Package marker
│   └── rate_processor.py  # Process messages
│
├── api/                   # Phase 3: FastAPI endpoints
│   └── __init__.py
│
├── dashboard/             # Phase 4: Streamlit dashboard
│
└── tests/                 # Phase 5: Unit & integration tests
    └── __init__.py
```

## 🎓 Learning Objectives

This project demonstrates:

### ✅ Phase 1 (Complete)
- [x] Docker containerization
- [x] Kafka KRaft mode (no Zookeeper)
- [x] Producer-Consumer pattern
- [x] confluent-kafka Python client
- [x] Environment-based configuration
- [x] Graceful shutdown handling
- [x] Structured logging

### 🔜 Phase 2 (Next)
- [ ] PostgreSQL integration with SQLAlchemy
- [ ] Redis caching
- [ ] Multiprocessing for parallel processing
- [ ] Database schema design
- [ ] Connection pooling

### 🔜 Phase 3
- [ ] FastAPI REST endpoints
- [ ] API documentation (Swagger)
- [ ] Rate querying endpoints
- [ ] Alert configuration API

### 🔜 Phase 4
- [ ] Streamlit dashboard
- [ ] Real-time charts with Plotly
- [ ] Interactive rate monitoring
- [ ] Alert visualization

### 🔜 Phase 5
- [ ] Unit tests with pytest
- [ ] Integration tests
- [ ] Test coverage >80%
- [ ] CI/CD pipeline

### 🔜 Phase 6
- [ ] Performance optimization
- [ ] Security hardening
- [ ] Deployment documentation
- [ ] Final polish

## 🔑 Key Concepts

### Kafka KRaft Mode
- No Zookeeper dependency (simpler architecture)
- Single node setup for development
- Production-ready for Kafka 3.x+

### confluent-kafka Benefits
- 5-10x faster than kafka-python
- Production-grade reliability
- Better error handling
- Idempotent producer (prevents duplicates)

### Message Delivery Guarantees
- **At-least-once:** Current setup (auto-commit)
- Messages may be reprocessed on failure
- Suitable for most applications

### Consumer Groups
- Multiple consumers share workload
- Each message delivered to one consumer in group
- Different groups receive all messages (broadcast)

## 🌟 Future Enhancements

- [ ] Alert engine for rate thresholds
- [ ] Email/SMS notifications
- [ ] Historical rate analysis
- [ ] ML-based rate prediction
- [ ] Multi-currency support
- [ ] Kubernetes deployment
- [ ] Prometheus metrics
- [ ] Grafana dashboards

## 📚 Resources

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [confluent-kafka Python](https://docs.confluent.io/kafka-clients/python/current/overview.html)
- [Docker Compose](https://docs.docker.com/compose/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Streamlit](https://streamlit.io/)

## 📄 License

MIT License - Feel free to use for learning and portfolio purposes.

## 👤 Author

**Priya**
- Built for RBC interview preparation
- Demonstrates distributed systems, streaming, and microservices architecture

---

**Status:** Phase 1 Complete ✅ | Ready for Phase 2 Integration
