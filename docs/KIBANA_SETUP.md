# Kibana Dashboard Setup Guide

## Real-time Monitoring with Kibana

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

### 4. Create Your First Dashboard

Let's build a complete dashboard with 6 visualizations step-by-step.

#### Step 1: Create a New Dashboard

1. Click **☰ Menu** → **Dashboard**
2. Click **Create dashboard**
3. Click **Save** (top-right)
4. Name it: `FX Monitor - Main Dashboard`
5. Click **Save**

Now let's add visualizations!

---

#### Visualization 1: FX Rates Time Series (Line Chart)

**This shows all 8 currency pairs over time**

1. Click **Create visualization** button
2. Select **Lens** (modern visualization editor)
3. In the left panel, drag **timestamp** to the horizontal axis
4. Drag **rate** to the vertical axis
5. Drag **pair** to **Break down by**
6. Click **Save and return**
7. Title: `FX Rates - Time Series`

---

#### Visualization 2: Current FX Rates (Metric Cards)

**Shows current values for each currency pair**

1. Click **Create visualization**
2. Select **Lens**
3. Change chart type to **Metric** (top bar)
4. Drag **rate** to the metric area
5. Change aggregation to **Average**
6. Drag **pair** to **Break down by**
7. Click **Save and return**
8. Title: `Current FX Rates`

---

#### Visualization 3: Volatility Bar Chart

**Compare volatility across currency pairs**

1. Click **Create visualization**
2. Select **Lens**
3. Change chart type to **Bar vertical**
4. Drag **pair** to horizontal axis
5. Drag **volatility** to vertical axis
6. Change aggregation to **Average**
7. Click **Save and return**
8. Title: `FX Volatility by Pair`

---

#### Visualization 4: Rates Data Table

**Table view with sortable columns**

1. Click **Create visualization**
2. Select **Lens**
3. Change chart type to **Table**
4. Drag **pair** to **Rows**
5. Drag **rate** to **Metrics** (set to Average)
6. Drag **volatility** to **Metrics** (set to Average)
7. Drag **timestamp** to **Metrics** (set to Max - shows latest)
8. Click **Save and return**
9. Title: `FX Rates Data Table`

---

#### Visualization 5: Alert Distribution (Pie Chart)

**Which pairs trigger the most alerts?**

1. Switch Data View to **FX Alerts** (top-left dropdown)
2. Click **Create visualization**
3. Select **Lens**
4. Change chart type to **Donut**
5. Drag **pair** to **Slice by**
6. Metric shows **Count** by default (perfect!)
7. Click **Save and return**
8. Title: `Alert Distribution`

---

#### Visualization 6: Alerts Timeline

**When do alerts trigger?**

1. Stay on **FX Alerts** data view
2. Click **Create visualization**
3. Select **Lens**
4. Change chart type to **Bar vertical stacked**
5. Drag **triggered_at** to horizontal axis
6. Drag **condition** to **Break down by**
7. Metric shows **Count** (default)
8. Click **Save and return**
9. Title: `Alerts Timeline`

---

### 5. Arrange Your Dashboard

1. **Resize panels**: Drag corners to resize
2. **Move panels**: Drag title bars to reposition
3. **Suggested layout**:
   - **Top row**: FX Rates Time Series (full width)
   - **Middle row**: Current FX Rates (left), Volatility Bar Chart (right)
   - **Bottom left**: Rates Data Table, Alert Distribution  
   - **Bottom right**: Alerts Timeline

4. Click **Save** when done

---

### 6. Configure Auto-Refresh

Make your dashboard update automatically:

1. Click the **calendar icon** (top-right)
2. Set time range: **Last 1 hour**
3. Click **Refresh every** dropdown
4. Select **30 seconds**
5. Dashboard now auto-refreshes! 🎉

---

### 7. What You Should See

After setup, your dashboard shows:

- ✅ **8 currency pairs** updating every 30 seconds
- ✅ **Real-time line chart** with trends
- ✅ **Current values** for each pair
- ✅ **Volatility comparison** across pairs
- ✅ **Alert history** (if you've created alerts via API)
- ✅ **Data table** with sortable columns

**If you don't see data:**
```powershell
# Check document count
(Invoke-RestMethod -Uri "http://localhost:9200/fx-rates/_count").count

# Should return 500+. If 0, check consumer logs:
docker compose logs fx-consumer --tail 50
```

---

### 8. Advanced: More Visualization Ideas

Once comfortable, try creating:

**1. Volatility Heatmap**
- Chart type: **Heatmap**
- X-axis: timestamp (1-hour buckets)
- Y-axis: pair
- Cell value: Average volatility
- **Use**: Spot volatility spikes across pairs

**2. Rate Change Gauge**
- Chart type: **Gauge**
- Metric: rate
- Goal: Use Lens formula to calculate % change
- **Use**: Monitor if rates move beyond thresholds

**3. Alert Frequency Table**
- Data View: FX Alerts
- Chart type: Table
- Rows: pair, condition
- Metrics: Count, Max triggered_at
- **Use**: See which alerts fire most often

---

#### Visualization 1: Current Rates Table (Alternative Method)

**If you prefer the classic visualization builder:**

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

**Demonstration Ideas**:
- Show live data flowing into dashboard
- Create an alert via API, then watch it appear in Kibana
- Explain multiprocessing architecture enabling real-time processing
- Walk through the full data pipeline: Producer → Kafka → Consumer → Elasticsearch → Kibana

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
