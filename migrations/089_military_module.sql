-- Migration 089: Military Module — Discord Relay Configs + Fleet PAP Tracking
-- Phase 6 of Management Suite Expansion

-- =============================================================================
-- Discord Relay Configurations
-- =============================================================================

CREATE TABLE IF NOT EXISTS discord_relay_configs (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    webhook_url         TEXT NOT NULL,
    filter_regions      BIGINT[] DEFAULT '{}',
    filter_alliances    BIGINT[] DEFAULT '{}',
    notify_types        TEXT[] NOT NULL DEFAULT '{timer_created,battle_started,high_value_kill}',
    ping_role_id        VARCHAR(50),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    min_isk_threshold   NUMERIC(18,2) DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Active relays for notification dispatch
CREATE INDEX idx_discord_relay_active ON discord_relay_configs (is_active)
    WHERE is_active = TRUE;

COMMENT ON TABLE discord_relay_configs IS 'Discord webhook relay configurations for automated notifications';
COMMENT ON COLUMN discord_relay_configs.notify_types IS 'Array of: timer_created, timer_expiring, battle_started, structure_attack, high_value_kill';
COMMENT ON COLUMN discord_relay_configs.ping_role_id IS 'Discord role ID for @role mentions in notifications';

-- =============================================================================
-- Fleet Operations (PAP Tracking)
-- =============================================================================

CREATE TABLE IF NOT EXISTS fleet_operations (
    id              SERIAL PRIMARY KEY,
    fleet_name      VARCHAR(255) NOT NULL,
    fc_character_id BIGINT,
    fc_name         VARCHAR(255),
    doctrine_id     INTEGER,
    start_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time        TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Active fleets lookup
CREATE INDEX idx_fleet_ops_active ON fleet_operations (is_active, start_time DESC)
    WHERE is_active = TRUE;

-- History
CREATE INDEX idx_fleet_ops_time ON fleet_operations (start_time DESC);

-- Fleet Snapshots (periodic fleet state captures)
CREATE TABLE IF NOT EXISTS fleet_snapshots (
    id              SERIAL PRIMARY KEY,
    operation_id    INTEGER NOT NULL REFERENCES fleet_operations(id) ON DELETE CASCADE,
    snapshot_time   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    member_count    INTEGER NOT NULL DEFAULT 0,
    raw_data        JSONB NOT NULL DEFAULT '[]'
);

CREATE INDEX idx_fleet_snapshots_op ON fleet_snapshots (operation_id, snapshot_time DESC);

-- Fleet Participation (per-pilot aggregated stats)
CREATE TABLE IF NOT EXISTS fleet_participation (
    id              SERIAL PRIMARY KEY,
    operation_id    INTEGER NOT NULL REFERENCES fleet_operations(id) ON DELETE CASCADE,
    character_id    BIGINT NOT NULL,
    character_name  VARCHAR(255),
    ship_type_id    INTEGER,
    ship_name       VARCHAR(255),
    solar_system_id INTEGER,
    first_seen      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    snapshot_count  INTEGER NOT NULL DEFAULT 1,
    UNIQUE (operation_id, character_id)
);

CREATE INDEX idx_fleet_participation_op ON fleet_participation (operation_id);
CREATE INDEX idx_fleet_participation_char ON fleet_participation (character_id, operation_id);

COMMENT ON TABLE fleet_operations IS 'Registered fleet operations for PAP tracking';
COMMENT ON TABLE fleet_snapshots IS 'Periodic fleet member snapshots for participation calculation';
COMMENT ON TABLE fleet_participation IS 'Aggregated per-pilot participation stats per fleet op';
