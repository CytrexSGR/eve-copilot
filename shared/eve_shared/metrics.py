"""Prometheus metrics for EVE Co-Pilot services."""

from prometheus_client import Counter, Histogram, Gauge, Info

# HTTP Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['service', 'method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['service', 'method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_request_size_bytes = Histogram(
    'http_request_size_bytes',
    'HTTP request size',
    ['service', 'method', 'endpoint']
)

http_response_size_bytes = Histogram(
    'http_response_size_bytes',
    'HTTP response size',
    ['service', 'method', 'endpoint']
)

# Database Metrics
db_queries_total = Counter(
    'db_queries_total',
    'Total database queries',
    ['service', 'operation', 'status']
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['service', 'operation'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0)
)

db_connections = Gauge(
    'db_connections',
    'Database connection pool status',
    ['service', 'state']  # state: active, idle, waiting
)

# Cache Metrics
cache_operations_total = Counter(
    'cache_operations_total',
    'Cache operations',
    ['service', 'operation', 'result']  # operation: get/set, result: hit/miss
)

# Service Info
service_info = Info(
    'service_info',
    'Service information'
)

# SaaS Business Metrics
saas_subscriptions_active = Gauge(
    'saas_subscriptions_active',
    'Active subscriptions by tier',
    ['tier']
)

saas_subscriptions_transitions = Counter(
    'saas_subscriptions_transitions_total',
    'Subscription status transitions',
    ['from_status', 'to_status']
)

saas_payments_total = Counter(
    'saas_payments_total',
    'Total payment events',
    ['status']
)

saas_payments_isk = Counter(
    'saas_payments_isk_total',
    'Total ISK received from payments',
    ['tier']
)

saas_feature_gate_decisions = Counter(
    'saas_feature_gate_decisions_total',
    'Feature gate allow/deny decisions',
    ['decision', 'required_tier']
)

saas_tier_resolutions = Counter(
    'saas_tier_resolutions_total',
    'Tier resolution requests',
    ['source']
)
