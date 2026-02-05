# Foreign Exchange Rate Monitoring System

> A production-ready real-time FX rate monitoring system demonstrating enterprise architecture with Kafka, multiprocessing, and real-time dashboards.

[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11-green)](https://www.python.org/)
[![Kafka](https://img.shields.io/badge/Kafka-3.5-red)](https://kafka.apache.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## 🎯 Overview

Enterprise-grade FX rate monitoring system built to demonstrate:
- **Distributed Systems**: 9-service microservices architecture
- **Multiprocessing**: Parallel processing at 3 levels (cross-rates, alerts, bulk indexing)
- **Real-time Streaming**: Kafka message broker with 30-second data feeds
- **Production Monitoring**: Kibana dashboards with time-series analysis
- **RESTful API**: FastAPI with 8 endpoints for data access and alert management

**Purpose**: Personal project demonstrating distributed systems and real-time data processing

---

## ⚡ Quick Start

### Prerequisites
- Docker Desktop (with Docker Compose)
- 8GB RAM minimum
- Available ports: 5432, 6379, 9092, 8000, 9200, 5601

### Start the System

```bash
# 1. Clone repository
git clone https://github.com/your-username/Forex-rate--monitor-and-alert-system.git
cd Forex-rate--monitor-and-alert-system

# 2. Copy environment file
cp .env.example .env

# 3. Start all services (9 containers)
docker compose up -d

# 4. Wait for services to be healthy (~30 seconds)
docker compose ps

# 5. Access the system
# - Kibana Dashboard: http://localhost:5601
# - FastAPI Swagger: http://localhost:8000/docs
# - Elasticsearch: http://localhost:9200
```

### Verify It's Working

```bash
# Check all services are healthy
docker compose ps

# View consumer processing rates
docker compose logs -f fx-consumer

# Test API
curl http://localhost:8000/health

# Check data in Elasticsearch
curl http://localhost:9200/fx-rates/_count
```

---

## 🏗️ Architecture

### System Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                   FX Rate Monitoring System                       │
│                        (9 Services)                               │
└──────────────────────────────────────────────────────────────────┘

External API → Producer → Kafka → Consumer → [PostgreSQL, Redis, Elasticsearch]
                                       ↓                    ↓
                                  Alert Engine          Kibana (Dashboards)
                                       ↓
                                   REST API (FastAPI)
```

### Services

| Service | Port | Purpose |
|---------|------|---------|
| **fx-producer** | - | Fetch FX rates every 30s |
| **fx-kafka** | 9092 | Message streaming (KRaft mode) |
| **fx-consumer** | - | Process rates (multiprocessing) |
| **fx-postgres** | 5432 | Historical data storage |
| **fx-redis** | 6379 | Rate caching |
| **fx-elasticsearch** | 9200 | Time-series indexing |
| **fx-kibana** | 5601 | Real-time dashboards |
| **fx-api** | 8000 | REST API endpoints |
| **alert-engine** | - | Alert monitoring (multiprocessing) |

---

## 🛠️ Technology Stack

**Core Technologies:**
- **Python 3.11**: Application logic
- **Apache Kafka 3.5**: Message streaming (KRaft mode, no Zookeeper)
- **PostgreSQL 15**: Relational database
- **Redis 7**: In-memory cache
- **Elasticsearch 8.11**: Time-series data store
- **Kibana 8.11**: Visualization platform
- **FastAPI**: Modern async REST framework
- **Docker Compose**: Service orchestration

**Key Libraries:**
- `confluent-kafka==2.3.0`: High-performance Kafka client
- `SQLAlchemy==2.0.23`: Database ORM
- `elasticsearch==8.11.0`: ES client for Kibana
- `multiprocessing`: Built-in Python parallel processing

---

## 📚 Documentation

### Getting Started
- **[Quick Start Guide](docs/QUICKSTART.md)** - Get running in 5 minutes
- **[System Architecture](docs/ARCHITECTURE.md)** - Detailed design and component overview
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

### Technical References
- **[API Documentation](docs/API.md)** - Complete REST API reference with examples
- **[Kibana Setup Guide](docs/KIBANA_SETUP.md)** - Dashboard configuration and visualization

---

## 🎓 Key Learning Demonstrations

### 1. Multiprocessing (3 Levels)
```python
# Level 1: Cross-rate calculations (Consumer)
Pool(4) → Calculate 28 cross-rates in parallel

# Level 2: Alert checking (Alert Engine)
Pool(2) → Check multiple alerts simultaneously

# Level 3: Bulk indexing (Elasticsearch)
Bulk API → Index 8 rates in single request
```

### 2. Distributed Architecture
- **Service Independence**: Each container is independently deployable
- **Health Checks**: Automatic dependency management
- **Graceful Degradation**: System continues if non-critical services fail

### 3. Real-time Data Pipeline
```
30s interval → 8 rates → Kafka → Consumer → 4 destinations → ~24ms
```
- PostgreSQL (persistence)
- Redis (caching)
- Elasticsearch (visualization)
- Cross-rate calculations (enrichment)

---

## 🎯 Key Features

### Real-time Data Pipeline
- Live FX rate fetching (166 currencies)
- Kafka streaming with KRaft mode
- Docker containerization

### Data Storage & Processing
- PostgreSQL historical storage
- Redis caching layer
- **Multiprocessing**: Pool(4) for cross-rate calculations
- Volatility tracking (20-period rolling std dev)

### REST API & Alerting
- **FastAPI**: 8 RESTful endpoints
- Alert management (create, list, delete)
- **Multiprocessing**: Pool(2) for parallel alert checking
- Alert history tracking

### Real-time Visualization
- Elasticsearch time-series storage
- Kibana real-time dashboards
- Auto-refreshing visualizations (30s)
- Alert history analysis

---

## 📊 API Endpoints

**Base URL**: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | System information |
| GET | `/rates` | Current rates (all pairs) |
| GET | `/rates/{pair}/history` | Rate history for pair |
| POST | `/alerts` | Create new alert |
| GET | `/alerts` | List active alerts |
| DELETE | `/alerts/{id}` | Delete alert |
| GET | `/alerts/history` | Alert trigger history |
| GET | `/health` | System health check |

**Interactive Docs**: http://localhost:8000/docs

---

## 📈 Monitoring & Dashboards

### Kibana Dashboard
Access at **http://localhost:5601**

**Features:**
- Real-time rate updates (30s refresh)
- Historical trend analysis
- Volatility tracking
- Alert timeline visualization

**Setup**: Follow [Kibana Setup Guide](docs/KIBANA_SETUP.md)

---

## 🧪 Testing

The project includes comprehensive test coverage for APIs and core utilities.

### Run Tests

```bash
# Install test dependencies (if not already installed)
pip install pytest pytest-cov httpx

# Run all tests with coverage report
pytest

# Run specific test modules
pytest tests/test_api.py          # API endpoint tests
pytest tests/test_utils.py        # Utility function tests

# Run with verbose output
pytest -v

# Generate HTML coverage report
pytest --cov-report=html
# View report: htmlcov/index.html
```

### Test Coverage

**API Tests** (`tests/test_api.py`):
- ✅ Root endpoint information
- ✅ Current rates retrieval
- ✅ Historical rate queries
- ✅ Alert creation/deletion/listing
- ✅ Alert history
- ✅ Health checks
- ✅ Input validation & error handling
- ✅ Complete alert workflow integration

**Unit Tests** (`tests/test_utils.py`):
- ✅ Cross-rate calculation logic
- ✅ Volatility computation
- ✅ Alert checking conditions
- ✅ Edge cases & precision
- ✅ Integration scenarios

**Coverage**: ~80%+ of core application logic

---

## 🔧 Configuration

### Environment Variables

Key variables in `.env`:

```bash
# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
KAFKA_TOPIC=fx-rates

# Database
POSTGRES_DB=fxrates
POSTGRES_USER=fxuser
POSTGRES_PASSWORD=fxpassword

# Redis
REDIS_DB=0

# Tracked Currencies (8 pairs)
TRACKED_CURRENCIES=EUR,GBP,JPY,CAD,AUD,CHF,CNY,INR

# Elasticsearch
ELASTICSEARCH_PORT=9200

# Kibana
KIBANA_PORT=5601

# API
API_PORT=8000
```

See `.env.example` for all options.

---

## 🐛 Troubleshooting

### Services won't start?
```bash
# Check Docker is running
docker ps

# View service logs
docker compose logs fx-consumer

# Restart specific service
docker compose restart fx-consumer
```

### No data in Kibana?
```bash
# Verify Elasticsearch has data
curl http://localhost:9200/fx-rates/_count

# Check consumer is running
docker compose logs fx-consumer --tail=50
```

See [Troubleshooting Guide](docs/TROUBLESHOOTING.md) for more help.

---

## 📦 Project Structure

```
.
├── api/                    # FastAPI REST service
│   ├── main.py            # API endpoints
│   └── Dockerfile
├── consumer/              # Kafka consumers
│   ├── rate_processor.py # Main consumer (multiprocessing)
│   ├── alert_engine.py   # Alert checker (multiprocessing)
│   └── Dockerfile
├── producer/              # FX rate producer
│   ├── fx_producer.py    # Rate fetching
│   └── Dockerfile
├── common/                # Shared utilities
│   ├── database.py       # PostgreSQL models
│   ├── redis_client.py   # Redis wrapper
│   └── elasticsearch_client.py  # ES wrapper
├── docs/                  # Documentation
│   ├── QUICKSTART.md
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── KIBANA_SETUP.md
│   └── TROUBLESHOOTING.md
├── docker-compose.yml     # Service orchestration
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

---

## 💡 Interesting Talking Points

### Technical Highlights

1. **Multiprocessing Architecture**
   - 3 levels of parallel processing
   - Demonstrates understanding of CPU-bound vs I/O-bound operations
   - Real-world performance optimization

2. **Distributed Systems**
   - 9-service microservices architecture
   - Message-driven communication (Kafka)
   - Service independence and fault tolerance

3. **Production-Ready Design**
   - Health checks and monitoring
   - Graceful degradation
   - Industry-standard tools (Kafka, PostgreSQL, Elasticsearch, Kibana)

4. **Full-Stack Implementation**
   - Backend: Python with async/await
   - Database: SQL with ORM
   - Caching: Redis
   - Messaging: Kafka
   - Visualization: Kibana
   - API: FastAPI with OpenAPI docs

### Performance Metrics
- **Processing Time**: ~24ms per message (8 rates)
- **Throughput**: 8 rates indexed every 30 seconds
- **Multiprocessing**: 28 cross-rates calculated in 4ms
- **API Response**: <50ms average

---

## 🤝 Contributing

This is a learning project, but contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file

---

## 🙏 Acknowledgments

- **Exchange Rate API**: [exchangerate-api.com](https://www.exchangerate-api.com/)
- **Confluent Kafka**: High-performance Python client
- **Docker Community**: Container orchestration patterns
- **Elastic Stack**: Elasticsearch and Kibana for visualization

---

## 📞 Contact

**Author**: Priyal  
**Purpose**: Personal project demonstrating distributed systems architecture  
**Date**: February 2026

---

<div align="center">

**⭐ Star this repo if it helped you learn!**

[Quick Start](docs/QUICKSTART.md) • [Architecture](docs/ARCHITECTURE.md) • [API Docs](docs/API.md) • [Kibana Setup](docs/KIBANA_SETUP.md)

</div>
