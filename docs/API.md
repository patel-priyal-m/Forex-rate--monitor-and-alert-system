# API Documentation

Complete REST API reference for the FX Rate Monitoring System.

**Base URL**: `http://localhost:8000`  
**Interactive Docs**: http://localhost:8000/docs (Swagger UI)  
**OpenAPI Spec**: http://localhost:8000/openapi.json

---

## 🎯 Overview

The FastAPI service provides 8 REST endpoints for:
- Querying current and historical exchange rates
- Managing user-defined alerts
- Checking system health

**Features**:
- Automatic request validation
- JSON responses
- OpenAPI/Swagger documentation
- CORS enabled
- Async/await for performance

---

## 📋 Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | System information |
| GET | `/rates` | Get current rates (all pairs) |
| GET | `/rates/{pair}/history` | Get rate history for specific pair |
| POST | `/alerts` | Create new alert |
| GET | `/alerts` | List all active alerts |
| DELETE | `/alerts/{id}` | Delete specific alert |
| GET | `/alerts/history` | Get alert trigger history |
| GET | `/health` | System health check |

---

## 🔌 Endpoints

### 1. Get System Information

Get basic system information and available endpoints.

**Request**:
```http
GET /
```

**Response** (200 OK):
```json
{
  "service": "FX Rate Monitoring API",
  "version": "1.0.0",
  "description": "Real-time foreign exchange rate monitoring with alerts",
  "endpoints": {
    "rates": "/rates",
    "rate_history": "/rates/{pair}/history",
    "alerts": "/alerts",
    "alert_history": "/alerts/history",
    "health": "/health"
  },
  "tracked_pairs": [
    "USD/EUR",
    "USD/GBP",
    "USD/JPY",
    "USD/CAD",
    "USD/AUD",
    "USD/CHF",
    "USD/CNY",
    "USD/INR"
  ]
}
```

**Example**:
```bash
curl http://localhost:8000/
```

---

### 2. Get Current Rates

Retrieve the latest exchange rate for all tracked currency pairs.

**Request**:
```http
GET /rates
```

**Query Parameters**: None

**Response** (200 OK):
```json
{
  "timestamp": "2026-02-04T15:30:00Z",
  "rates": {
    "USD/EUR": {
      "rate": 0.847,
      "volatility": 0.001234,
      "last_updated": "2026-02-04T15:30:00Z"
    },
    "USD/GBP": {
      "rate": 0.789,
      "volatility": 0.001567,
      "last_updated": "2026-02-04T15:30:00Z"
    },
    "USD/JPY": {
      "rate": 110.25,
      "volatility": 0.234567,
      "last_updated": "2026-02-04T15:30:00Z"
    }
    // ... other pairs
  },
  "source": "redis_cache"
}
```

**Response Fields**:
- `timestamp`: Server response timestamp (ISO 8601)
- `rates`: Object with currency pairs as keys
  - `rate`: Current exchange rate (float)
  - `volatility`: Rolling volatility (20-period std dev, float)
  - `last_updated`: When rate was last updated
- `source`: Data source (`redis_cache` or `database`)

**Example**:
```bash
# Get all current rates
curl http://localhost:8000/rates

# With Python requests
import requests
response = requests.get('http://localhost:8000/rates')
rates = response.json()
print(f"USD/EUR rate: {rates['rates']['USD/EUR']['rate']}")
```

**Notes**:
- Data served from Redis cache (sub-millisecond response)
- Falls back to PostgreSQL if cache miss
- Volatility may be `null` if insufficient historical data

---

### 3. Get Rate History

Retrieve historical exchange rates for a specific currency pair.

**Request**:
```http
GET /rates/{pair}/history
```

**Path Parameters**:
- `pair` (string, required): Currency pair (URL-encoded)
  - Format: `USD/EUR` → `USD%2FEUR`
  - Examples: `USD%2FEUR`, `USD%2FGBP`, `USD%2FJPY`

**Query Parameters**:
- `limit` (integer, optional): Maximum number of records
  - Default: `100`
  - Range: `1-1000`
- `offset` (integer, optional): Number of records to skip
  - Default: `0`
  - Use for pagination

**Response** (200 OK):
```json
{
  "pair": "USD/EUR",
  "history": [
    {
      "timestamp": "2026-02-04T15:30:00Z",
      "rate": 0.847
    },
    {
      "timestamp": "2026-02-04T15:00:00Z",
      "rate": 0.848
    },
    {
      "timestamp": "2026-02-04T14:30:00Z",
      "rate": 0.846
    }
    // ... more records
  ],
  "total_records": 156,
  "limit": 100,
  "offset": 0
}
```

**Response Fields**:
- `pair`: Currency pair
- `history`: Array of rate records (ordered newest first)
  - `timestamp`: Rate timestamp (ISO 8601)
  - `rate`: Exchange rate value
- `total_records`: Total available records in database
- `limit`: Applied limit
- `offset`: Applied offset

**Error Response** (404 Not Found):
```json
{
  "detail": "No history found for pair USD/INVALID"
}
```

**Examples**:
```bash
# Get last 100 rates for USD/EUR
curl "http://localhost:8000/rates/USD%2FEUR/history"

# Get last 50 rates
curl "http://localhost:8000/rates/USD%2FEUR/history?limit=50"

# Pagination: Get next 50 rates
curl "http://localhost:8000/rates/USD%2FEUR/history?limit=50&offset=50"

# Python example
import requests

pair = "USD/EUR"
response = requests.get(
    f'http://localhost:8000/rates/{requests.utils.quote(pair, safe="")}/history',
    params={'limit': 100}
)
history = response.json()['history']
```

**Notes**:
- Results ordered by timestamp descending (newest first)
- Data served from PostgreSQL
- URL-encode the pair parameter: `USD/EUR` → `USD%2FEUR`

---

### 4. Create Alert

Create a new alert to monitor when a rate crosses a threshold.

**Request**:
```http
POST /alerts
Content-Type: application/json
```

**Request Body**:
```json
{
  "pair": "USD/EUR",
  "condition": "below",
  "threshold": 0.85
}
```

**Body Fields**:
- `pair` (string, required): Currency pair to monitor
  - Must be one of the tracked pairs
  - Format: `USD/EUR`, `USD/GBP`, etc.
- `condition` (string, required): Trigger condition
  - Allowed values: `"above"` or `"below"`
- `threshold` (float, required): Threshold value
  - Must be positive number

**Response** (201 Created):
```json
{
  "id": 1,
  "pair": "USD/EUR",
  "condition": "below",
  "threshold": 0.85,
  "active": true,
  "created_at": "2026-02-04T15:30:00Z"
}
```

**Response Fields**:
- `id`: Unique alert ID (use for deletion)
- `pair`: Monitored currency pair
- `condition`: Trigger condition
- `threshold`: Threshold value
- `active`: Whether alert is active (always `true` on creation)
- `created_at`: Creation timestamp

**Error Responses**:

400 Bad Request (Invalid pair):
```json
{
  "detail": "Invalid currency pair. Must be one of: USD/EUR, USD/GBP, ..."
}
```

400 Bad Request (Invalid condition):
```json
{
  "detail": "Condition must be 'above' or 'below'"
}
```

422 Unprocessable Entity (Validation error):
```json
{
  "detail": [
    {
      "loc": ["body", "threshold"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```

**Examples**:
```bash
# Alert when USD/EUR goes below 0.85
curl -X POST http://localhost:8000/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "pair": "USD/EUR",
    "condition": "below",
    "threshold": 0.85
  }'

# Alert when USD/JPY goes above 115
curl -X POST http://localhost:8000/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "pair": "USD/JPY",
    "condition": "above",
    "threshold": 115.0
  }'

# Python example
import requests

alert = {
    "pair": "USD/EUR",
    "condition": "below",
    "threshold": 0.85
}
response = requests.post(
    'http://localhost:8000/alerts',
    json=alert
)
alert_id = response.json()['id']
print(f"Created alert with ID: {alert_id}")
```

**Notes**:
- Alert checks run on every rate update (~30s)
- No duplicate checking (can create multiple alerts for same pair)
- Alerts trigger repeatedly while condition is met
- Alert engine uses multiprocessing for parallel checking

---

### 5. List Active Alerts

Get all active (non-deleted) alerts.

**Request**:
```http
GET /alerts
```

**Query Parameters**: None

**Response** (200 OK):
```json
{
  "alerts": [
    {
      "id": 1,
      "pair": "USD/EUR",
      "condition": "below",
      "threshold": 0.85,
      "active": true,
      "created_at": "2026-02-04T15:30:00Z"
    },
    {
      "id": 2,
      "pair": "USD/JPY",
      "condition": "above",
      "threshold": 115.0,
      "active": true,
      "created_at": "2026-02-04T16:00:00Z"
    }
  ],
  "total": 2
}
```

**Response Fields**:
- `alerts`: Array of alert objects
  - `id`: Alert ID
  - `pair`: Monitored pair
  - `condition`: Trigger condition
  - `threshold`: Threshold value
  - `active`: Always `true` (only active alerts returned)
  - `created_at`: Creation timestamp
- `total`: Number of active alerts

**Empty Response** (200 OK):
```json
{
  "alerts": [],
  "total": 0
}
```

**Example**:
```bash
# List all active alerts
curl http://localhost:8000/alerts

# Python example
import requests

response = requests.get('http://localhost:8000/alerts')
alerts = response.json()['alerts']
for alert in alerts:
    print(f"Alert {alert['id']}: {alert['pair']} {alert['condition']} {alert['threshold']}")
```

---

### 6. Delete Alert

Delete (deactivate) a specific alert by ID.

**Request**:
```http
DELETE /alerts/{id}
```

**Path Parameters**:
- `id` (integer, required): Alert ID to delete

**Response** (200 OK):
```json
{
  "message": "Alert 1 deleted successfully",
  "id": 1
}
```

**Error Response** (404 Not Found):
```json
{
  "detail": "Alert with ID 999 not found"
}
```

**Examples**:
```bash
# Delete alert with ID 1
curl -X DELETE http://localhost:8000/alerts/1

# Python example
import requests

alert_id = 1
response = requests.delete(f'http://localhost:8000/alerts/{alert_id}')
print(response.json()['message'])
```

**Notes**:
- Deletion is logical (sets `active=false` in database)
- Alert no longer checked by alert engine
- Alert history remains in database

---

### 7. Get Alert History

Retrieve history of triggered alerts.

**Request**:
```http
GET /alerts/history
```

**Query Parameters**:
- `limit` (integer, optional): Maximum number of records
  - Default: `100`
  - Range: `1-1000`
- `offset` (integer, optional): Number of records to skip
  - Default: `0`

**Response** (200 OK):
```json
{
  "history": [
    {
      "id": 1,
      "alert_id": 1,
      "pair": "USD/EUR",
      "rate": 0.847,
      "message": "Alert triggered: USD/EUR is below 0.85 (current: 0.847)",
      "triggered_at": "2026-02-04T15:31:00Z"
    },
    {
      "id": 2,
      "alert_id": 1,
      "pair": "USD/EUR",
      "rate": 0.846,
      "message": "Alert triggered: USD/EUR is below 0.85 (current: 0.846)",
      "triggered_at": "2026-02-04T15:01:00Z"
    }
  ],
  "total_records": 2,
  "limit": 100,
  "offset": 0
}
```

**Response Fields**:
- `history`: Array of trigger records (ordered newest first)
  - `id`: History record ID
  - `alert_id`: ID of triggered alert
  - `pair`: Currency pair
  - `rate`: Rate when alert triggered
  - `message`: Human-readable message
  - `triggered_at`: Trigger timestamp
- `total_records`: Total trigger events in database
- `limit`: Applied limit
- `offset`: Applied offset

**Empty Response** (200 OK):
```json
{
  "history": [],
  "total_records": 0,
  "limit": 100,
  "offset": 0
}
```

**Examples**:
```bash
# Get last 100 alert triggers
curl http://localhost:8000/alerts/history

# Get last 20 triggers
curl "http://localhost:8000/alerts/history?limit=20"

# Python example
import requests

response = requests.get(
    'http://localhost:8000/alerts/history',
    params={'limit': 50}
)
history = response.json()['history']
for event in history:
    print(f"{event['triggered_at']}: {event['message']}")
```

**Notes**:
- Includes triggers from both active and deleted alerts
- Results ordered by timestamp descending (newest first)
- Useful for analyzing alert frequency and patterns

---

### 8. Health Check

Check system health and connectivity to dependencies.

**Request**:
```http
GET /health
```

**Response** (200 OK - All healthy):
```json
{
  "status": "healthy",
  "timestamp": "2026-02-04T15:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5.2
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 0.8
    }
  }
}
```

**Response** (503 Service Unavailable - Degraded):
```json
{
  "status": "degraded",
  "timestamp": "2026-02-04T15:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5.2
    },
    "redis": {
      "status": "unhealthy",
      "error": "Connection refused"
    }
  }
}
```

**Response Fields**:
- `status`: Overall system status
  - `"healthy"`: All dependencies OK
  - `"degraded"`: One or more dependencies down
- `timestamp`: Check timestamp
- `checks`: Health of individual dependencies
  - `status`: `"healthy"` or `"unhealthy"`
  - `response_time_ms`: Response time (if healthy)
  - `error`: Error message (if unhealthy)

**Example**:
```bash
# Check health
curl http://localhost:8000/health

# Python example
import requests

response = requests.get('http://localhost:8000/health')
if response.status_code == 200:
    print("System is healthy")
else:
    print(f"System is degraded: {response.json()}")
```

**Notes**:
- Returns 200 if all checks pass
- Returns 503 if any check fails
- Use for monitoring and alerts
- Lightweight checks (no complex queries)

---

## 🔐 Authentication

**Current State**: No authentication (development setup)

**Production Recommendations**:

### API Key Authentication
```python
# Header-based
headers = {
    'X-API-Key': 'your-api-key-here'
}
requests.get('http://api.example.com/rates', headers=headers)
```

### JWT Token Authentication
```python
# Bearer token
headers = {
    'Authorization': 'Bearer eyJhbGc...'
}
requests.get('http://api.example.com/rates', headers=headers)
```

---

## ⚠️ Error Handling

### Standard Error Response Format

All errors follow this structure:
```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful GET/DELETE |
| 201 | Created | Successful POST (alert created) |
| 400 | Bad Request | Invalid input data |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Dependency down (health check) |

### Common Error Scenarios

**Invalid Currency Pair**:
```json
// POST /alerts with invalid pair
{
  "detail": "Invalid currency pair. Must be one of: USD/EUR, USD/GBP, USD/JPY, USD/CAD, USD/AUD, USD/CHF, USD/CNY, USD/INR"
}
```

**Validation Error**:
```json
// POST /alerts with negative threshold
{
  "detail": [
    {
      "loc": ["body", "threshold"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```

**Resource Not Found**:
```json
// DELETE /alerts/999 (doesn't exist)
{
  "detail": "Alert with ID 999 not found"
}
```

---

## 🧪 Testing the API

### Using curl

```bash
# Basic requests
curl http://localhost:8000/
curl http://localhost:8000/rates
curl http://localhost:8000/health

# Rate history
curl "http://localhost:8000/rates/USD%2FEUR/history?limit=10"

# Create alert
curl -X POST http://localhost:8000/alerts \
  -H "Content-Type: application/json" \
  -d '{"pair":"USD/EUR","condition":"below","threshold":0.85}'

# List alerts
curl http://localhost:8000/alerts

# Delete alert
curl -X DELETE http://localhost:8000/alerts/1

# Alert history
curl "http://localhost:8000/alerts/history?limit=20"
```

### Using Python requests

```python
import requests

BASE_URL = 'http://localhost:8000'

# Get current rates
response = requests.get(f'{BASE_URL}/rates')
rates = response.json()
print(rates)

# Get rate history
pair = "USD/EUR"
response = requests.get(
    f'{BASE_URL}/rates/{requests.utils.quote(pair, safe="")}/history',
    params={'limit': 50}
)
history = response.json()

# Create alert
alert = {
    "pair": "USD/EUR",
    "condition": "below",
    "threshold": 0.85
}
response = requests.post(f'{BASE_URL}/alerts', json=alert)
alert_id = response.json()['id']

# List alerts
response = requests.get(f'{BASE_URL}/alerts')
alerts = response.json()['alerts']

# Delete alert
response = requests.delete(f'{BASE_URL}/alerts/{alert_id}')

# Get alert history
response = requests.get(f'{BASE_URL}/alerts/history')
history = response.json()['history']
```

### Using Swagger UI

1. Open http://localhost:8000/docs
2. Click on any endpoint to expand
3. Click "Try it out"
4. Fill in parameters
5. Click "Execute"
6. View response

**Benefits**:
- Interactive testing
- Request/response examples
- Schema validation
- No coding required

---

## 📊 Response Times

Typical response times (local development):

| Endpoint | Avg Response Time | Data Source |
|----------|-------------------|-------------|
| `GET /` | ~5ms | Static |
| `GET /rates` | ~2ms | Redis |
| `GET /rates/{pair}/history` | ~50ms | PostgreSQL |
| `POST /alerts` | ~30ms | PostgreSQL |
| `GET /alerts` | ~20ms | PostgreSQL |
| `DELETE /alerts/{id}` | ~25ms | PostgreSQL |
| `GET /alerts/history` | ~40ms | PostgreSQL |
| `GET /health` | ~10ms | Redis + PostgreSQL |

**Factors Affecting Performance**:
- Network latency
- Database query complexity
- Number of records
- Server load

---

## 🔄 Rate Limiting

**Current State**: No rate limiting

**Production Recommendations**:
```python
# Example with slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/rates")
@limiter.limit("100/minute")
async def get_rates():
    # ...
```

Suggested limits:
- Public endpoints: 100 requests/minute
- Alert management: 20 requests/minute
- Administrative: 1000 requests/minute

---

## 📚 Related Documentation

- **[Architecture](ARCHITECTURE.md)**: System design and data flow
- **[Quick Start](QUICKSTART.md)**: Get the system running
- **[Kibana Setup](KIBANA_SETUP.md)**: Dashboard visualization
- **[Troubleshooting](TROUBLESHOOTING.md)**: Common issues

---

## 💡 Usage Examples

### Example 1: Monitor EUR/USD Rate

```python
import requests
import time

BASE_URL = 'http://localhost:8000'

# Create alert for rate below 0.85
alert = requests.post(f'{BASE_URL}/alerts', json={
    "pair": "USD/EUR",
    "condition": "below",
    "threshold": 0.85
}).json()

print(f"Created alert {alert['id']}")

# Poll current rate every 30 seconds
while True:
    response = requests.get(f'{BASE_URL}/rates')
    rate = response.json()['rates']['USD/EUR']['rate']
    print(f"Current USD/EUR rate: {rate}")
    
    if rate < 0.85:
        print("Alert condition met!")
        # Check alert history
        history = requests.get(f'{BASE_URL}/alerts/history').json()
        print(f"Alert triggered {len(history['history'])} times")
    
    time.sleep(30)
```

### Example 2: Historical Analysis

```python
import requests
import pandas as pd
import matplotlib.pyplot as plt

BASE_URL = 'http://localhost:8000'

# Get last 1000 rates for USD/EUR
response = requests.get(
    f'{BASE_URL}/rates/USD%2FEUR/history',
    params={'limit': 1000}
)
history = response.json()['history']

# Convert to DataFrame
df = pd.DataFrame(history)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp')

# Plot
plt.figure(figsize=(12, 6))
plt.plot(df['timestamp'], df['rate'])
plt.title('USD/EUR Exchange Rate History')
plt.xlabel('Time')
plt.ylabel('Rate')
plt.grid(True)
plt.show()
```

### Example 3: Alert Dashboard

```python
import requests
from datetime import datetime

BASE_URL = 'http://localhost:8000'

def display_dashboard():
    # Get active alerts
    alerts = requests.get(f'{BASE_URL}/alerts').json()['alerts']
    
    # Get alert history
    history = requests.get(f'{BASE_URL}/alerts/history', params={'limit': 10}).json()['history']
    
    # Get current rates
    rates = requests.get(f'{BASE_URL}/rates').json()['rates']
    
    print("=" * 60)
    print("FX RATE MONITORING DASHBOARD")
    print("=" * 60)
    
    print(f"\nActive Alerts: {len(alerts)}")
    for alert in alerts:
        print(f"  {alert['id']}: {alert['pair']} {alert['condition']} {alert['threshold']}")
    
    print(f"\nRecent Alert Triggers: {len(history)}")
    for event in history[:5]:
        timestamp = datetime.fromisoformat(event['triggered_at'].replace('Z', '+00:00'))
        print(f"  {timestamp.strftime('%Y-%m-%d %H:%M')}: {event['message']}")
    
    print("\nCurrent Rates:")
    for pair, data in sorted(rates.items()):
        print(f"  {pair}: {data['rate']:.4f} (σ={data['volatility']:.6f})")

# Run dashboard
display_dashboard()
```

---

**API Version**: 1.0.0  
**Last Updated**: February 2026  
**Author**: Priyal
