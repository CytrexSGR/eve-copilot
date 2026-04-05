"""EVE Online business metrics for Prometheus.

EVE-specific KPIs tracked across the application:
- Active battles
- Kill processing rate
- ISK destroyed/lost
- Market orders tracked
- Production jobs by status

NOTE: High-cardinality labels (system_name, attacker_alliance, victim_alliance)
were removed to prevent Prometheus series explosion. Per-entity breakdowns
are tracked in PostgreSQL, not in Prometheus counters.
"""

from prometheus_client import Gauge, Counter

# Battle Metrics
eve_battles_active = Gauge(
    'eve_battles_active',
    'Number of currently active battles'
)

eve_battles_total = Counter(
    'eve_battles_total',
    'Total number of battles detected',
    ['region_name']
)

# Kill Metrics
eve_kills_total = Counter(
    'eve_kills_total',
    'Total killmails processed'
)

eve_kills_processing_rate = Gauge(
    'eve_kills_processing_rate',
    'Killmails processed per second'
)

# ISK Metrics (in billions)
eve_isk_destroyed_total = Counter(
    'eve_isk_destroyed_total',
    'Total ISK destroyed in billions'
)

eve_isk_lost_total = Counter(
    'eve_isk_lost_total',
    'Total ISK lost in billions'
)

# Market Metrics
eve_market_orders_total = Gauge(
    'eve_market_orders_total',
    'Total market orders tracked',
    ['character_id', 'order_type']  # order_type: buy/sell
)

eve_market_volume_isk = Gauge(
    'eve_market_volume_isk',
    'Total market order volume in ISK',
    ['character_id', 'region_id']
)

# Production Metrics
eve_production_jobs = Gauge(
    'eve_production_jobs',
    'Production jobs by status',
    ['character_id', 'status']  # status: active/paused/delivered
)

eve_production_revenue_isk = Counter(
    'eve_production_revenue_isk',
    'Production revenue in ISK',
    ['character_id', 'activity_type']  # activity_type: manufacturing/research/etc
)

# Asset Metrics
eve_character_assets_isk = Gauge(
    'eve_character_assets_isk',
    'Character total asset value in ISK',
    ['character_id']
)

# Wallet Metrics
eve_wallet_balance_isk = Gauge(
    'eve_wallet_balance_isk',
    'Character wallet balance in ISK',
    ['character_id']
)

eve_wallet_transactions_total = Counter(
    'eve_wallet_transactions_total',
    'Wallet transactions processed',
    ['character_id', 'transaction_type']  # transaction_type: buy/sell/bounty/etc
)


# Helper functions for common patterns

def track_battle_created(system_name: str, region_name: str):
    """Track when a new battle is created."""
    eve_battles_total.labels(
        region_name=region_name
    ).inc()


def track_kill_processed(
    attacker_alliance: str,
    victim_alliance: str,
    isk_value: float
):
    """Track a killmail being processed.

    Args:
        attacker_alliance: Name of attacking alliance (kept for API compat, not used as label)
        victim_alliance: Name of victim alliance (kept for API compat, not used as label)
        isk_value: ISK value of the kill in ISK (will be converted to billions)
    """
    eve_kills_total.inc()

    # Track ISK destroyed (convert to billions)
    isk_billions = isk_value / 1_000_000_000
    eve_isk_destroyed_total.inc(isk_billions)
    eve_isk_lost_total.inc(isk_billions)


def update_active_battles_count(count: int):
    """Update the active battles gauge."""
    eve_battles_active.set(count)


def update_kill_processing_rate(rate: float):
    """Update the kills/second processing rate."""
    eve_kills_processing_rate.set(rate)


def update_market_orders(character_id: int, buy_count: int, sell_count: int):
    """Update market order counts for a character."""
    eve_market_orders_total.labels(
        character_id=str(character_id),
        order_type="buy"
    ).set(buy_count)

    eve_market_orders_total.labels(
        character_id=str(character_id),
        order_type="sell"
    ).set(sell_count)


def update_production_jobs(character_id: int, active: int, paused: int, delivered: int):
    """Update production job counts for a character."""
    eve_production_jobs.labels(
        character_id=str(character_id),
        status="active"
    ).set(active)

    eve_production_jobs.labels(
        character_id=str(character_id),
        status="paused"
    ).set(paused)

    eve_production_jobs.labels(
        character_id=str(character_id),
        status="delivered"
    ).set(delivered)
