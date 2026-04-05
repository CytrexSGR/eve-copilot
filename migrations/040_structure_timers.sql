-- Migration: 040_structure_timers.sql
-- Description: Structure timers for reinforcement tracking
-- Date: 2026-01-23

-- Structure types
CREATE TYPE structure_timer_type AS ENUM (
    'armor',      -- First reinforcement (armor timer)
    'hull',       -- Final reinforcement (hull timer)
    'anchoring',  -- Anchoring timer
    'unanchoring', -- Unanchoring timer
    'online'      -- Online timer
);

-- Structure categories
CREATE TYPE structure_category AS ENUM (
    'tcurfc',     -- Territorial Claim Units, Refinery, Citadel, etc.
    'ihub',       -- Infrastructure Hub
    'poco',       -- Player Owned Customs Office
    'pos',        -- POS (legacy)
    'ansiblex',   -- Ansiblex Jump Gate
    'cyno_beacon', -- Cyno Beacon
    'cyno_jammer' -- Cyno Jammer
);

-- Structure timers table
CREATE TABLE IF NOT EXISTS structure_timers (
    id SERIAL PRIMARY KEY,

    -- Structure identification
    structure_id BIGINT,  -- ESI structure ID if known
    structure_name VARCHAR(200) NOT NULL,
    structure_type_id INTEGER,  -- EVE type ID
    category structure_category NOT NULL,

    -- Location
    system_id INTEGER NOT NULL,
    system_name VARCHAR(100),
    region_id INTEGER,
    region_name VARCHAR(100),

    -- Ownership
    owner_alliance_id INTEGER,
    owner_alliance_name VARCHAR(100),
    owner_corporation_id INTEGER,
    owner_corporation_name VARCHAR(100),

    -- Timer info
    timer_type structure_timer_type NOT NULL,
    timer_start TIMESTAMP WITH TIME ZONE NOT NULL,
    timer_end TIMESTAMP WITH TIME ZONE NOT NULL,  -- Vulnerability window end

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    result VARCHAR(50),  -- 'defended', 'destroyed', 'repaired', 'captured'

    -- Intel source
    source VARCHAR(50) NOT NULL DEFAULT 'manual',  -- 'manual', 'esi', 'zkill'
    reported_by VARCHAR(100),
    notes TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_structure_timers_system ON structure_timers(system_id);
CREATE INDEX IF NOT EXISTS idx_structure_timers_timer_end ON structure_timers(timer_end);
CREATE INDEX IF NOT EXISTS idx_structure_timers_active ON structure_timers(is_active, timer_end);
CREATE INDEX IF NOT EXISTS idx_structure_timers_alliance ON structure_timers(owner_alliance_id);

-- View for upcoming timers
CREATE OR REPLACE VIEW v_upcoming_timers AS
SELECT
    st.*,
    EXTRACT(EPOCH FROM (st.timer_end - NOW())) / 3600 as hours_until,
    CASE
        WHEN st.timer_end - NOW() < INTERVAL '1 hour' THEN 'critical'
        WHEN st.timer_end - NOW() < INTERVAL '3 hours' THEN 'urgent'
        WHEN st.timer_end - NOW() < INTERVAL '24 hours' THEN 'upcoming'
        ELSE 'planned'
    END as urgency,
    -- Check if system is cyno jammed
    CASE WHEN cj.solar_system_id IS NOT NULL THEN TRUE ELSE FALSE END as cyno_jammed
FROM structure_timers st
LEFT JOIN intel_cyno_jammers cj ON st.system_id = cj.solar_system_id
WHERE st.is_active = TRUE
  AND st.timer_end > NOW()
ORDER BY st.timer_end ASC;

-- Timer history for analysis
CREATE TABLE IF NOT EXISTS structure_timer_history (
    id SERIAL PRIMARY KEY,
    timer_id INTEGER REFERENCES structure_timers(id),
    action VARCHAR(50) NOT NULL,  -- 'created', 'updated', 'resolved'
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE structure_timers IS 'Structure reinforcement and anchoring timers';
COMMENT ON VIEW v_upcoming_timers IS 'Active timers sorted by urgency';
