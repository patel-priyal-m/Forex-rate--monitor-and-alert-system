# Kibana Dashboard Setup Guide

## Phase 4: Real-time Monitoring with Kibana

This guide walks you through setting up professional Kibana dashboards for monitoring FX rates in real-time.

## 🎯 Overview

Kibana provides production-ready visualization capabilities for:
- **Real-time Rate Monitoring**: Live updates of currency exchange rates
- **Volatility Tracking**: Monitor market volatility across currency pairs
- **Alert History**: Visualize triggered alerts and alert patterns
- **Time-Series Analysis**: Analyze rate trends over time

## 📊 Data Indices

The system creates two Elasticsearch indices:

1. **fx-rates**: Stores all FX rate updates with volatility
   - `timestamp` (date): When the rate was recorded
   - `pair` (keyword): Currency pair (e.g., "USD/EUR")
   - `rate` (float): Exchange rate value
   - `volatility` (float): Rolling standard deviation (20-period)
   - `source` (keyword): Data source (default: "api")

2. **fx-alerts**: Stores triggered alert events
   - `triggered_at` (date): Alert trigger timestamp
   - `alert_id` (integer): Alert ID
   - `pair` (keyword): Currency pair
   - `condition` (keyword): Alert condition ("above"/"below")
   - `threshold` (float): Threshold value
   - `current_rate` (float): Rate when alert triggered
   - `message` (text): Alert message

## 🚀 Quick Start

### 1. Access Kibana

Open your browser and navigate to:
```
http://localhost:5601
```

**Note**: Kibana may take 30-60 seconds to fully start up on first launch.

### 2. Create Data Views (Index Patterns)

Data Views tell Kibana which indices to query.

#### Create FX Rates Data View

1. Click **☰ Menu** → **Stack Management** → **Data Views**
2. Click **Create data view**
3. Configure:
   - **Name**: `FX Rates`
   - **Index pattern**: `fx-rates*`
   - **Timestamp field**: `timestamp`
4. Click **Save data view to Kibana**

#### Create FX Alerts Data View

1. Click **Create data view** again
2. Configure:
   - **Name**: `FX Alerts`
   - **Index pattern**: `fx-alerts*`
   - **Timestamp field**: `triggered_at`
3. Click **Save data view to Kibana**

### 3. Explore Your Data

Before creating dashboards, let's explore the data:

1. Click **☰ Menu** → **Discover**
2. Select **FX Rates** data view from dropdown
3. You should see real-time data flowing in every 30 seconds
4. Adjust time range (top-right) to see different time windows

### 4. Create Visualizations

#### Visualization 1: Current Rates Table

**Purpose**: Show latest rate for each currency pair

1. Click **☰ Menu** → **Visualize Library** → **Create visualization**
2. Select **FX Rates** data view
3. Select **Table** visualization type
4. Configure:
   - **Rows**: 
     - Field: `pair.keyword`
     - Order by: Metric (Latest timestamp)
     - Size: 10
   - **Metrics**:
     - Add metric: **Last value** of `rate`
     - Add metric: **Last value** of `volatility`
     - Label them appropriately
5. **Save**: Name it "Current FX Rates"

#### Visualization 2: Rate History Line Chart

**Purpose**: Track rate changes over time for all pairs

1. **Create visualization** → **FX Rates** data view
2. Select **Line** chart
3. Configure:
   - **Horizontal axis**: `timestamp` (Date histogram)
   - **Vertical axis**: `Average` of `rate`
   - **Breakdown**: `pair.keyword` (shows separate line per pair)
4. **Save**: Name it "FX Rate History"

#### Visualization 3: Volatility Gauge

**Purpose**: Show current volatility level

1. **Create visualization** → **FX Rates** data view
2. Select **Metric** visualization
3. Configure:
   - **Metric**: `Average` of `volatility`
   - **Breakdown**: `pair.keyword`
4. **Save**: Name it "FX Volatility Metrics"

#### Visualization 4: Alert Timeline

**Purpose**: Visualize when alerts were triggered

1. **Create visualization** → **FX Alerts** data view
2. Select **Vertical bar** chart
3. Configure:
   - **Horizontal axis**: `triggered_at` (Date histogram, interval: Auto)
   - **Vertical axis**: Count
   - **Breakdown**: `pair.keyword`
4. **Save**: Name it "Alert History Timeline"

#### Visualization 5: Alert Details Table

**Purpose**: Show recent triggered alerts with details

1. **Create visualization** → **FX Alerts** data view
2. Select **Table** visualization
3. Configure:
   - **Rows**: `triggered_at` (Date, Top 20, newest first)
   - **Metrics**: Show all fields (pair, condition, threshold, current_rate, message)
4. **Save**: Name it "Recent Alerts"

### 5. Create Dashboard

Combine all visualizations into a single dashboard:

1. Click **☰ Menu** → **Dashboard** → **Create dashboard**
2. Click **Add from library**
3. Add all saved visualizations:
   - Current FX Rates (table)
   - FX Rate History (line chart)
   - FX Volatility Metrics (metric cards)
   - Alert History Timeline (bar chart)
   - Recent Alerts (table)
4. Arrange visualizations by dragging and resizing
5. Click **Save**: Name it "FX Monitoring Dashboard"

### 6. Configure Auto-Refresh

Enable real-time updates:

1. Open your dashboard
2. Click the **🕐 time picker** (top-right)
3. Click **Refresh every** → Select **30 seconds**
4. Set time range to **Last 1 hour** or **Last 15 minutes**

Your dashboard will now update automatically!

## 💡 Recommended Dashboard Layout

```
┌──────────────────────────────────────────────────────────┐
│  Current FX Rates Table  │  FX Volatility Metrics       │
│  (latest values)         │  (gauge cards)                │
├──────────────────────────────────────────────────────────┤
│                                                           │
│           FX Rate History Line Chart                     │
│           (time-series, all pairs)                       │
│                                                           │
├──────────────────────────────────────────────────────────┤
│  Alert History Timeline                                  │
│  (bar chart by time)                                     │
├──────────────────────────────────────────────────────────┤
│  Recent Alerts Table                                     │
│  (detailed alert log)                                    │
└──────────────────────────────────────────────────────────┘
```

## 🔧 Advanced Features

### Add Filters

Click **Add filter** to focus on specific currency pairs:
```
pair.keyword is "USD/EUR"
```

### Create Alerts in Kibana

1. **☰ Menu** → **Stack Management** → **Rules and Connectors**
2. Create threshold alerts based on volatility or rate changes
3. Configure notifications (requires additional setup)

### Use Time Shift Comparisons

Compare current rates to previous periods:
1. In visualizations, use **Time shift** feature
2. Compare "now" vs "1 day ago" or "1 week ago"

### Export Data

From Discover or visualizations:
1. Click **Share** → **CSV Reports**
2. Generate reports for analysis

## 🎨 Dashboard Customization Tips

1. **Color Coding**: 
   - Use red/yellow/green for volatility levels
   - Different colors per currency pair

2. **Panel Titles**: 
   - Clear, descriptive titles
   - Include time ranges in titles if relevant

3. **Tooltips**: 
   - Enable hover tooltips for detailed info
   - Show exact values on charts

4. **Dark Mode**: 
   - **☰ Menu** → **Stack Management** → **Advanced Settings**
   - Search for "theme" → Select dark theme

## 📈 Monitoring Best Practices

1. **Set appropriate time ranges**: 
   - Last 15 minutes: For immediate monitoring
   - Last 1 hour: For recent trends
   - Last 24 hours: For daily patterns

2. **Use multiple dashboards**:
   - Overview dashboard (all pairs)
   - Detail dashboards (per currency pair)
   - Alert-focused dashboard

3. **Regular checks**:
   - Monitor alert frequency
   - Check volatility patterns
   - Identify unusual rate movements

## 🐛 Troubleshooting

### No data appearing?

1. Check Elasticsearch has data:
   ```bash
   curl http://localhost:9200/fx-rates/_count
   ```

2. Verify consumer is running:
   ```bash
   docker compose logs fx-consumer --tail=50
   ```

3. Check data view time range matches your data

### Dashboard not updating?

1. Verify auto-refresh is enabled (top-right corner)
2. Check producer is running and generating data
3. Refresh browser (Ctrl+F5)

### Visualizations showing errors?

1. Verify field names match exactly (case-sensitive)
2. Check data view is pointing to correct index pattern
3. Ensure timestamp field is correctly configured

## 🎓 Learning Resources

- **Kibana Lens**: Modern drag-and-drop visualization builder
- **KQL (Kibana Query Language)**: Advanced filtering
- **Canvas**: Create custom pixel-perfect dashboards
- **Maps**: Geospatial visualizations (if you add location data)

## 📝 Next Steps

1. ✅ Create data views for both indices
2. ✅ Build individual visualizations
3. ✅ Combine into dashboard
4. ✅ Enable auto-refresh
5. 🎯 Monitor your FX rates in real-time!

**Demo Tip**: For your RBC interview, show:
- Live data flowing into dashboard
- Create an alert via API, then show it appear in Kibana
- Explain how multiprocessing enables real-time processing
- Demonstrate the full data pipeline: Producer → Kafka → Consumer → Elasticsearch → Kibana

---

## 🚀 Quick Commands Reference

```bash
# Check Elasticsearch status
docker compose ps elasticsearch

# View consumer logs
docker compose logs -f fx-consumer

# Check data count
curl http://localhost:9200/fx-rates/_count

# View recent documents
curl "http://localhost:9200/fx-rates/_search?size=5&sort=timestamp:desc"

# Access Kibana
http://localhost:5601

# Access FastAPI
http://localhost:8000/docs
```

Happy monitoring! 🎉
