-- Migration: 042_fuel_tracking.sql
-- Description: Fuel tracking for corporation structures
-- Date: 2026-01-23

-- Structure fuel consumption rates (per hour)
CREATE TABLE IF NOT EXISTS structure_fuel_rates (
    structure_type_id INTEGER PRIMARY KEY,
    structure_type_name VARCHAR(100) NOT NULL,
    base_fuel_rate INTEGER NOT NULL,  -- Fuel blocks per hour
    service_module_rate INTEGER DEFAULT 0,  -- Additional per service module
    notes TEXT
);

-- Insert common structure fuel rates
INSERT INTO structure_fuel_rates (structure_type_id, structure_type_name, base_fuel_rate, notes) VALUES
-- Citadels
(35832, 'Astrahus', 12, 'Medium citadel'),
(35833, 'Fortizar', 24, 'Large citadel'),
(35834, 'Keepstar', 36, 'XL citadel'),
-- Engineering Complexes
(35825, 'Raitaru', 12, 'Medium EC'),
(35826, 'Azbel', 24, 'Large EC'),
(35827, 'Sotiyo', 36, 'XL EC'),
-- Refineries
(35835, 'Athanor', 12, 'Medium refinery'),
(35836, 'Tatara', 24, 'Large refinery'),
-- Flex Structures
(47512, 'Ansiblex Jump Gate', 30, 'Jump gate fuel'),
(35840, 'Pharolux Cyno Beacon', 10, 'Cyno beacon'),
(37534, 'Tenebrex Cyno Jammer', 30, 'Cyno jammer')
ON CONFLICT (structure_type_id) DO NOTHING;

-- Corporation structures cache
CREATE TABLE IF NOT EXISTS corp_structures (
    structure_id BIGINT PRIMARY KEY,
    corporation_id INTEGER NOT NULL,

    -- Structure info
    structure_type_id INTEGER,
    structure_type_name VARCHAR(100),
    name VARCHAR(200),

    -- Location
    system_id INTEGER,
    system_name VARCHAR(100),
    region_id INTEGER,
    region_name VARCHAR(100),

    -- Fuel status
    fuel_expires TIMESTAMP WITH TIME ZONE,
    fuel_blocks_remaining INTEGER,  -- Calculated estimate
    days_remaining FLOAT,  -- Calculated

    -- Services (affects fuel consumption)
    services JSONB,  -- Array of service module states
    state VARCHAR(50),  -- 'online', 'anchoring', 'reinforced', etc.

    -- Sync metadata
    last_synced TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sync_source VARCHAR(50) DEFAULT 'esi',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_corp_structures_corp ON corp_structures(corporation_id);
CREATE INDEX IF NOT EXISTS idx_corp_structures_fuel ON corp_structures(fuel_expires);
CREATE INDEX IF NOT EXISTS idx_corp_structures_system ON corp_structures(system_id);

-- Fuel alerts configuration
CREATE TABLE IF NOT EXISTS fuel_alert_config (
    id SERIAL PRIMARY KEY,
    corporation_id INTEGER NOT NULL,

    -- Alert thresholds (in days)
    critical_days INTEGER DEFAULT 3,
    warning_days INTEGER DEFAULT 7,
    notice_days INTEGER DEFAULT 14,

    -- Notification settings
    discord_webhook VARCHAR(500),
    notify_on_critical BOOLEAN DEFAULT TRUE,
    notify_on_warning BOOLEAN DEFAULT TRUE,
    notify_on_notice BOOLEAN DEFAULT FALSE,

    -- Filters
    structure_types INTEGER[],  -- Only alert for these types (null = all)
    min_structure_value NUMERIC,  -- Ignore cheap structures

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(corporation_id)
);

-- Fuel history for tracking consumption patterns
CREATE TABLE IF NOT EXISTS fuel_history (
    id SERIAL PRIMARY KEY,
    structure_id BIGINT NOT NULL REFERENCES corp_structures(structure_id) ON DELETE CASCADE,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fuel_expires TIMESTAMP WITH TIME ZONE,
    days_remaining FLOAT,
    state VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_fuel_history_structure ON fuel_history(structure_id, recorded_at);

-- View for low fuel structures
CREATE OR REPLACE VIEW v_low_fuel_structures AS
SELECT
    cs.structure_id,
    cs.name,
    cs.structure_type_name,
    cs.corporation_id,
    cs.system_name,
    cs.region_name,
    cs.fuel_expires,
    cs.days_remaining,
    cs.state,
    CASE
        WHEN cs.days_remaining IS NULL THEN 'unknown'
        WHEN cs.days_remaining <= 3 THEN 'critical'
        WHEN cs.days_remaining <= 7 THEN 'warning'
        WHEN cs.days_remaining <= 14 THEN 'notice'
        ELSE 'ok'
    END as fuel_status,
    sfr.base_fuel_rate
FROM corp_structures cs
LEFT JOIN structure_fuel_rates sfr ON cs.structure_type_id = sfr.structure_type_id
WHERE cs.state = 'online' OR cs.state IS NULL
ORDER BY cs.days_remaining ASC NULLS FIRST;

COMMENT ON TABLE structure_fuel_rates IS 'Fuel consumption rates by structure type';
COMMENT ON TABLE corp_structures IS 'Corporation structure tracking with fuel status';
COMMENT ON TABLE fuel_alert_config IS 'Per-corporation fuel alert settings';
COMMENT ON VIEW v_low_fuel_structures IS 'Structures sorted by fuel urgency';
