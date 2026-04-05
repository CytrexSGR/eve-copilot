# Grafana Dashboards - Maintenance Guide

## Overview

All Grafana dashboards are provisioned via Infrastructure as Code using JSON files. This ensures:
- **Version Control:** All dashboard changes tracked in git
- **Reproducibility:** Dashboards auto-deploy on Grafana restart
- **Team Collaboration:** Changes reviewed via pull requests
- **Zero Manual Work:** No need to create dashboards via UI

---

## Directory Structure

```
docker/grafana/provisioning/
├── datasources/
│   └── datasources.yml          # Prometheus + Loki datasources
└── dashboards/
    ├── dashboard.yml             # Provider configuration
    └── json/                     # Dashboard JSON files
        ├── service-overview.json
        ├── http-performance.json
        ├── system-resources.json
        └── business-metrics.json
```

---

## Current Dashboards

### 1. Service Overview
**File:** `json/service-overview.json`
**UID:** `eve-service-overview`
**Purpose:** High-level health and performance monitoring for all 11 microservices

**Panels:**
- Service Health Status (all services, green/red)
- Request Rate by Service (time series)
- Error Rate by Service (5xx errors)
- P95 Latency by Service
- P99 Latency by Service (gauge with thresholds)
- Service Versions (table)
- Top 10 Slowest Endpoints

**Variables:**
- `$service` - Multi-select service filter
- `$tier` - Multi-select tier filter (gateway/backend/stream/jobs/ai-tools)

---

### 2. HTTP Performance
**File:** `json/http-performance.json`
**UID:** `eve-http-performance`
**Purpose:** Deep HTTP metrics analysis for performance troubleshooting

**Panels:**
- Total Request Rate (stat)
- Requests by Method (pie chart)
- Requests by Status Code (bar gauge, color-coded)
- Request Latency Heatmap
- Request Size Distribution (P50/P90/P99)
- Response Size Distribution (P50/P90/P99)
- Top 15 Endpoints by Request Volume
- Top 15 Slowest Endpoints (P99 latency)
- Top 10 Endpoints by Error Rate

**Variables:**
- `$service` - Multi-select service filter
- `$status_code` - Status code filter (All/2xx/4xx/5xx)

---

### 3. System Resources (Placeholder)
**File:** `json/system-resources.json`
**UID:** `eve-system-resources`
**Purpose:** Database and cache metrics (requires instrumentation)

**Status:** 🟡 **Metrics defined but not yet instrumented**

**Pending Metrics:**
- Database connection pool usage
- Query duration percentiles
- Cache hit rate
- Cache operations by type

**To Implement:**
1. Add database decorators to track query duration
2. Instrument connection pool in database clients
3. Add Redis/cache operation tracking
4. Replace placeholder panels with real queries

---

### 4. Business Metrics (Placeholder)
**File:** `json/business-metrics.json`
**UID:** `eve-business-metrics`
**Purpose:** EVE Online business KPIs (requires instrumentation)

**Status:** 🔴 **Not yet instrumented**

**Pending Metrics:**
- Active battles count
- Kill feed rate (kills/minute)
- ISK destroyed total
- Market orders tracked
- Manufacturing jobs active

**To Implement:**
1. Add Prometheus metrics to business logic in services
2. Instrument battle detection, market tracking, etc.
3. Replace placeholder panels with real queries

---

## Adding a New Dashboard

### Method 1: Create in UI, Export to Git

1. **Create in Grafana UI:**
   - Navigate to http://localhost:3200
   - Login: admin/<GRAFANA_PASSWORD>
   - Click "+" → "Dashboard"
   - Add panels, configure queries
   - Test thoroughly

2. **Export to JSON:**
   - Click dashboard settings (gear icon)
   - Share → Export → "Export for sharing externally"
   - Save to file: `dashboard-name.json`

3. **Move to Provisioning Directory:**
   ```bash
   cd /home/cytrex/eve_copilot
   mv ~/Downloads/dashboard-name.json docker/grafana/provisioning/dashboards/json/
   ```

4. **Commit to Git:**
   ```bash
   git add docker/grafana/provisioning/dashboards/json/dashboard-name.json
   git commit -m "feat: add Dashboard Name for monitoring XYZ"
   git push origin main
   ```

5. **Restart Grafana (optional):**
   ```bash
   docker compose restart grafana
   ```
   *Note: Dashboard auto-reloads every 10 seconds, but restart ensures immediate visibility.*

---

### Method 2: Create JSON Manually

For advanced users or automated dashboard generation:

1. **Create JSON file:**
   ```json
   {
     "title": "My Dashboard",
     "uid": "my-dashboard-uid",
     "tags": ["microservices", "custom"],
     "timezone": "browser",
     "schemaVersion": 38,
     "version": 1,
     "panels": [
       {
         "id": 1,
         "title": "Panel Title",
         "type": "timeseries",
         "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
         "targets": [
           {
             "expr": "your_prometheus_query",
             "legendFormat": "{{label}}",
             "refId": "A"
           }
         ]
       }
     ]
   }
   ```

2. **Validate JSON:**
   ```bash
   python3 -m json.tool dashboard.json > /dev/null && echo "Valid" || echo "Invalid"
   ```

3. **Move to provisioning directory and commit (same as Method 1 steps 3-5)**

---

## Modifying Existing Dashboards

### Option A: Edit in UI, Re-export

1. **Load dashboard in Grafana UI**
2. **Make changes** (add panels, modify queries, etc.)
3. **Export updated JSON** (Share → Export)
4. **Replace old file:**
   ```bash
   mv ~/Downloads/service-overview.json docker/grafana/provisioning/dashboards/json/
   ```
5. **Commit changes:**
   ```bash
   git add docker/grafana/provisioning/dashboards/json/service-overview.json
   git commit -m "feat: add P90 latency panel to Service Overview"
   git push origin main
   ```

### Option B: Edit JSON Directly

1. **Edit JSON file:**
   ```bash
   nano docker/grafana/provisioning/dashboards/json/service-overview.json
   ```
2. **Validate JSON:**
   ```bash
   python3 -m json.tool service-overview.json > /dev/null
   ```
3. **Restart Grafana** (or wait 10 seconds for auto-reload)
4. **Verify in UI**
5. **Commit changes**

**Warning:** Editing JSON directly is error-prone. Prefer UI method for complex changes.

---

## Adding New Metrics

### 1. Define Metric in Shared Library

**File:** `shared/eve_shared/metrics.py`

```python
from prometheus_client import Counter, Histogram, Gauge, Info

# Example: Add business metric
eve_battles_active = Gauge(
    'eve_battles_active',
    'Number of active battles'
)

eve_kills_total = Counter(
    'eve_kills_total',
    'Total kills processed',
    ['system']
)
```

### 2. Instrument Service Code

**Example:** Track battle creation in war-intel-service

```python
from eve_shared.metrics import eve_battles_active, eve_kills_total

# When battle is created:
eve_battles_active.inc()

# When kill is processed:
eve_kills_total.labels(system=kill['system_name']).inc()
```

### 3. Verify Metric in Prometheus

1. Navigate to http://localhost:9090
2. Query: `eve_battles_active`
3. Verify data appears

### 4. Add Panel to Dashboard

- Query: `eve_battles_active`
- Visualization: Stat or Time Series
- Export and commit updated dashboard JSON

---

## Troubleshooting

### Dashboard Not Loading

**Symptom:** Dashboard doesn't appear in Grafana UI after adding JSON file.

**Checks:**
1. **JSON Syntax:** Validate with `python3 -m json.tool dashboard.json`
2. **File Location:** Must be in `docker/grafana/provisioning/dashboards/json/`
3. **File Permissions:** Should be readable (644)
4. **Grafana Logs:**
   ```bash
   docker compose logs grafana | grep -i dashboard
   ```
5. **Restart Grafana:**
   ```bash
   docker compose restart grafana
   ```

**Common Errors:**
- "Dashboard title cannot be empty" → JSON structure wrong (missing title at root level)
- "UNIQUE constraint failed" → Dashboard with same title already exists
- "Invalid JSON" → Syntax error (missing comma, bracket, etc.)

---

### Panel Shows "No data"

**Symptom:** Panel loads but displays "No data"

**Checks:**
1. **Prometheus Query:** Test in Prometheus UI (http://localhost:9090)
2. **Time Range:** Ensure time range has data
3. **Label Filters:** Check if `$service` variable is filtering out all data
4. **Metric Exists:** Verify metric is being collected: `curl http://localhost:8002/metrics | grep metric_name`

---

### Dashboard Shows Old Data

**Symptom:** Changes to JSON file don't appear in UI

**Solutions:**
1. **Wait 10 seconds** (auto-reload interval)
2. **Hard refresh browser:** Ctrl+Shift+R
3. **Restart Grafana:**
   ```bash
   docker compose restart grafana
   ```
4. **Clear Grafana cache:** Delete dashboard in UI, wait for re-provision

---

## Provider Configuration

**File:** `docker/grafana/provisioning/dashboards/dashboard.yml`

```yaml
apiVersion: 1

providers:
  - name: 'EVE Co-Pilot Dashboards'
    orgId: 1
    type: file
    disableDeletion: false      # Allow manual deletion
    updateIntervalSeconds: 10   # Auto-reload every 10 seconds
    allowUiUpdates: true        # Allow UI editing (won't persist)
    options:
      path: /etc/grafana/provisioning/dashboards/json
      foldersFromFilesStructure: false
```

**Key Settings:**
- `updateIntervalSeconds: 10` - Dashboards reload automatically
- `allowUiUpdates: true` - Can edit in UI, but changes won't persist to files
- `disableDeletion: false` - Can delete dashboards manually in UI

**To Persist UI Changes:**
1. Make changes in UI
2. Export to JSON
3. Replace file in `docker/grafana/provisioning/dashboards/json/`
4. Commit to git

---

## Best Practices

### Dashboard Design

1. **Keep It Simple:** 6-10 panels max, clear focus
2. **Use Templates:** Add `$service`, `$tier` variables for filtering
3. **Color Coding:** Green (good), Yellow (warning), Red (critical)
4. **Consistent Layout:** 12 or 24 column grid
5. **Descriptive Titles:** "P95 Latency by Service" not "Latency"

### PromQL Queries

1. **Use rate() for Counters:** `rate(http_requests_total[5m])`
2. **Use Percentiles:** `histogram_quantile(0.95, ...)`
3. **Label Filtering:** `{service=~"$service"}` for template variables
4. **Limit Results:** `topk(10, ...)` to prevent cardinality explosion
5. **Aggregation:** `sum(...) by (service)` to reduce time series

### Git Workflow

1. **Descriptive Commits:** "feat: add P90 latency to Service Overview"
2. **Test Before Commit:** Verify dashboard loads in Grafana
3. **Small Changes:** One dashboard per commit when possible
4. **Review:** Use `git diff` to review JSON changes

---

## Metrics Instrumentation Guide

### Database Metrics (Future Implementation)

**Goal:** Track database connection pool and query performance

**Steps:**
1. Add decorator to database operations:
   ```python
   from eve_shared.metrics import db_query_duration_seconds, db_queries_total

   @observe_db_query("service-name", "operation-name")
   async def get_user(user_id: int):
       # Query logic
       pass
   ```

2. Instrument connection pool:
   ```python
   from eve_shared.metrics import db_connections_active, db_connections_idle

   # In connection pool manager:
   db_connections_active.set(pool.active_count())
   db_connections_idle.set(pool.idle_count())
   ```

3. Update System Resources dashboard with real queries

---

### Cache Metrics (Future Implementation)

**Goal:** Track Redis/cache hit rate and operations

**Steps:**
1. Wrap Redis operations:
   ```python
   from eve_shared.metrics import cache_operations_total, cache_hits_total

   async def get_cached(key: str):
       result = await redis.get(key)
       if result:
           cache_hits_total.labels(service="service-name").inc()
       cache_operations_total.labels(service="service-name", operation="get").inc()
       return result
   ```

2. Update System Resources dashboard

---

### Business Metrics (Future Implementation)

**Goal:** Track EVE-specific KPIs

**Example Metrics:**
```python
# In war-intel-service
eve_battles_active = Gauge('eve_battles_active', 'Active battles')
eve_kills_total = Counter('eve_kills_total', 'Total kills', ['system'])
eve_isk_destroyed_total = Counter('eve_isk_destroyed_total', 'Total ISK destroyed')

# In market-service
eve_market_orders = Gauge('eve_market_orders', 'Tracked orders', ['type'])
eve_price_updates = Counter('eve_price_updates', 'Price updates', ['item'])

# In production-service
eve_production_jobs = Gauge('eve_production_jobs', 'Manufacturing jobs', ['status'])
```

**Update Business Metrics dashboard with real queries**

---

## Grafana Resources

- **Official Docs:** https://grafana.com/docs/grafana/latest/
- **Dashboard JSON Schema:** https://grafana.com/docs/grafana/latest/dashboards/json-model/
- **PromQL Guide:** https://prometheus.io/docs/prometheus/latest/querying/basics/
- **Panel Types:** https://grafana.com/docs/grafana/latest/panels-visualizations/

---

**Last Updated:** 2026-02-02 (Grafana Dashboard Provisioning Implementation)
