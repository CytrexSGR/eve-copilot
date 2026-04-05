-- migrations/005_war_economy.sql
-- War Economy Extension for War Room
-- Adds fuel tracking, supercap timers, and market manipulation detection

BEGIN;

-- ============================================================
-- ISOTOPE FUEL TRACKING
-- ============================================================
CREATE TABLE IF NOT EXISTS war_economy_fuel_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_time TIMESTAMP NOT NULL DEFAULT NOW(),
    region_id INTEGER NOT NULL,
    isotope_type_id INTEGER NOT NULL,

    -- Market Data
    total_volume INTEGER NOT NULL,
    average_price NUMERIC(15,2),
    sell_orders INTEGER,
    buy_orders INTEGER,

    -- Analysis
    baseline_7d_volume INTEGER,
    volume_delta_percent NUMERIC(5,2),
    anomaly_detected BOOLEAN DEFAULT FALSE,
    anomaly_severity VARCHAR(20),

    created_at TIMESTAMP DEFAULT NOW(),

    -- Prevent duplicate snapshots
    UNIQUE(snapshot_time, region_id, isotope_type_id)
);

CREATE INDEX IF NOT EXISTS idx_wef_time_region ON war_economy_fuel_snapshots(snapshot_time DESC, region_id);
CREATE INDEX IF NOT EXISTS idx_wef_isotope_time ON war_economy_fuel_snapshots(isotope_type_id, snapshot_time DESC);
CREATE INDEX IF NOT EXISTS idx_wef_anomaly ON war_economy_fuel_snapshots(anomaly_detected, snapshot_time DESC)
    WHERE anomaly_detected = TRUE;

-- ============================================================
-- SUPERCAPITAL CONSTRUCTION TIMERS
-- ============================================================
CREATE TABLE IF NOT EXISTS war_economy_supercap_timers (
    id SERIAL PRIMARY KEY,

    structure_id BIGINT,
    solar_system_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL,
    ship_type_id INTEGER NOT NULL,

    alliance_id INTEGER,
    alliance_name VARCHAR(100),
    corporation_id INTEGER,
    corporation_name VARCHAR(100),

    build_start_date DATE NOT NULL,
    estimated_completion_date DATE NOT NULL,
    material_efficiency INTEGER DEFAULT 10,
    time_efficiency INTEGER DEFAULT 20,

    status VARCHAR(20) NOT NULL DEFAULT 'active',
    status_updated_at TIMESTAMP DEFAULT NOW(),

    confidence_level VARCHAR(20) DEFAULT 'unconfirmed',
    intel_source VARCHAR(100),
    notes TEXT,

    reported_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_west_status ON war_economy_supercap_timers(status, estimated_completion_date);
CREATE INDEX IF NOT EXISTS idx_west_system ON war_economy_supercap_timers(solar_system_id);
CREATE INDEX IF NOT EXISTS idx_west_region ON war_economy_supercap_timers(region_id);
CREATE INDEX IF NOT EXISTS idx_west_alliance ON war_economy_supercap_timers(alliance_id);

-- ============================================================
-- MARKET MANIPULATION ALERTS
-- ============================================================
CREATE TABLE IF NOT EXISTS war_economy_manipulation_alerts (
    id SERIAL PRIMARY KEY,

    type_id INTEGER NOT NULL,
    type_name VARCHAR(100),
    region_id INTEGER NOT NULL,
    region_name VARCHAR(100),

    current_price NUMERIC(15,2) NOT NULL,
    baseline_price NUMERIC(15,2) NOT NULL,
    price_change_percent NUMERIC(6,2) NOT NULL,

    current_volume INTEGER NOT NULL,
    baseline_volume INTEGER NOT NULL,
    volume_change_percent NUMERIC(6,2) NOT NULL,

    z_score NUMERIC(5,2) NOT NULL,

    severity VARCHAR(20) NOT NULL,
    manipulation_type VARCHAR(50),

    related_conflicts TEXT[],
    related_sov_timers INTEGER,

    status VARCHAR(20) DEFAULT 'new',
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,

    detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wem_detection ON war_economy_manipulation_alerts(detected_at DESC, status);
CREATE INDEX IF NOT EXISTS idx_wem_type_region ON war_economy_manipulation_alerts(type_id, region_id);
CREATE INDEX IF NOT EXISTS idx_wem_severity ON war_economy_manipulation_alerts(severity, detected_at DESC)
    WHERE status = 'new';

-- ============================================================
-- SYSTEM TRACKING PRIORITY LOG
-- ============================================================
CREATE TABLE IF NOT EXISTS war_economy_priority_log (
    id SERIAL PRIMARY KEY,
    system_id INTEGER NOT NULL,
    system_name VARCHAR(100),

    priority_score INTEGER NOT NULL,
    priority_rank INTEGER,

    active_events JSONB,
    event_count INTEGER DEFAULT 0,

    poll_frequency_seconds INTEGER,
    last_polled_at TIMESTAMP,
    next_poll_at TIMESTAMP,

    snapshot_time TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wep_system_time ON war_economy_priority_log(system_id, snapshot_time DESC);
CREATE INDEX IF NOT EXISTS idx_wep_score ON war_economy_priority_log(priority_score DESC, snapshot_time DESC);

COMMIT;

-- Verify tables created
\dt war_economy_*
