-- Migration: 056_battle_events.sql
-- Purpose: Create tables for real-time battle event detection system
-- Description: Tracks EVE Online battle events like capital kills, hot zones, and high-value kills
--              for display in a frontend ticker

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

-- Severity levels for battle events
CREATE TYPE battle_event_severity AS ENUM (
    'critical',  -- Titan/Supercarrier kills
    'high',      -- Hot zone shifts, war escalations, capital kills, ISK spikes
    'medium',    -- New conflicts, alliance engagements, efficiency changes
    'low'        -- Regional activity, dread/carrier/FAX kills
);

-- Types of battle events that can be detected
CREATE TYPE battle_event_type AS ENUM (
    -- Critical severity
    'titan_killed',
    'supercarrier_killed',
    -- High severity
    'hot_zone_shift',
    'war_escalation',
    'capital_killed',
    'isk_spike',
    -- Medium severity
    'new_conflict',
    'alliance_engagement',
    'efficiency_change',
    -- Low severity
    'regional_activity',
    'dread_killed',
    'carrier_killed',
    'fax_killed'
);

-- ============================================================================
-- TABLES
-- ============================================================================

-- Main table for storing detected battle events
CREATE TABLE battle_events (
    id SERIAL PRIMARY KEY,
    event_type battle_event_type NOT NULL,
    severity battle_event_severity NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    -- Location information (nullable for non-location-specific events)
    system_id INTEGER,
    system_name VARCHAR(100),
    region_id INTEGER,
    region_name VARCHAR(100),
    -- Alliance information (nullable)
    alliance_id INTEGER,
    alliance_name VARCHAR(100),
    -- Additional event data stored as JSON
    event_data JSONB DEFAULT '{}',
    -- Timestamps
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    event_time TIMESTAMP WITH TIME ZONE,
    -- Unique hash for deduplication (prevents duplicate events)
    event_hash VARCHAR(64) UNIQUE
);

COMMENT ON TABLE battle_events IS 'Stores detected battle events for the real-time event ticker. Events are automatically cleaned up after 24 hours.';
COMMENT ON COLUMN battle_events.event_hash IS 'SHA256 hash of event details for deduplication';
COMMENT ON COLUMN battle_events.event_data IS 'Additional event-specific data stored as JSON';
COMMENT ON COLUMN battle_events.detected_at IS 'When the event was detected by the system';
COMMENT ON COLUMN battle_events.event_time IS 'When the event actually occurred (if known)';

-- Table for storing state snapshots used for change detection
CREATE TABLE battle_state_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_type VARCHAR(50) NOT NULL,
    snapshot_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE battle_state_snapshots IS 'Stores state snapshots for detecting changes between polling intervals. Only the last 2 snapshots per type are retained.';
COMMENT ON COLUMN battle_state_snapshots.snapshot_type IS 'Type of snapshot (e.g., hot_zones, capital_activity, alliance_efficiency)';
COMMENT ON COLUMN battle_state_snapshots.snapshot_data IS 'The actual snapshot data as JSON';

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Index for fetching recent events (most common query)
CREATE INDEX idx_battle_events_detected_at ON battle_events (detected_at DESC);

-- Index for filtering by severity
CREATE INDEX idx_battle_events_severity ON battle_events (severity);

-- Index for filtering by event type
CREATE INDEX idx_battle_events_type ON battle_events (event_type);

-- Index for filtering by system (partial index - excludes NULL values)
CREATE INDEX idx_battle_events_system_id ON battle_events (system_id) WHERE system_id IS NOT NULL;

-- Index for filtering by alliance (partial index - excludes NULL values)
CREATE INDEX idx_battle_events_alliance_id ON battle_events (alliance_id) WHERE alliance_id IS NOT NULL;

-- Composite index for snapshot cleanup queries
CREATE INDEX idx_battle_state_snapshots_type_created ON battle_state_snapshots (snapshot_type, created_at DESC);

-- ============================================================================
-- CLEANUP FUNCTION
-- ============================================================================

-- Function to clean up old events and snapshots
CREATE OR REPLACE FUNCTION cleanup_battle_events()
RETURNS void AS $$
BEGIN
    -- Delete events older than 24 hours
    DELETE FROM battle_events
    WHERE detected_at < NOW() - INTERVAL '24 hours';

    -- Keep only the last 2 snapshots per type
    DELETE FROM battle_state_snapshots
    WHERE id NOT IN (
        SELECT id FROM (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY snapshot_type ORDER BY created_at DESC) as rn
            FROM battle_state_snapshots
        ) ranked
        WHERE rn <= 2
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_battle_events() IS 'Removes battle events older than 24 hours and keeps only the last 2 snapshots per snapshot type';
