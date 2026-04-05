-- Migration: 038_sovereignty_structures.sql
-- Description: Sovereignty structures and ADM tracking for capital operations planning
-- Date: 2026-01-23

-- Sovereignty structures from ESI /sovereignty/structures/
CREATE TABLE IF NOT EXISTS sovereignty_structures (
    id SERIAL PRIMARY KEY,
    alliance_id INTEGER NOT NULL,
    solar_system_id INTEGER NOT NULL,
    structure_type_id INTEGER NOT NULL,  -- 32226=TCU, 32458=IHUB
    vulnerability_occupancy_level FLOAT,  -- ADM level (1.0-6.0)
    vulnerable_start_time TIMESTAMP WITH TIME ZONE,
    vulnerable_end_time TIMESTAMP WITH TIME ZONE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(solar_system_id, structure_type_id)
);

CREATE INDEX IF NOT EXISTS idx_sov_structures_alliance ON sovereignty_structures(alliance_id);
CREATE INDEX IF NOT EXISTS idx_sov_structures_system ON sovereignty_structures(solar_system_id);
CREATE INDEX IF NOT EXISTS idx_sov_structures_type ON sovereignty_structures(structure_type_id);

-- Manual intel: Cyno jammers (not available via public ESI)
CREATE TABLE IF NOT EXISTS intel_cyno_jammers (
    id SERIAL PRIMARY KEY,
    solar_system_id INTEGER NOT NULL UNIQUE,
    alliance_id INTEGER,  -- Who deployed it (if known)
    reported_by VARCHAR(100),  -- Who reported the intel
    confirmed BOOLEAN DEFAULT FALSE,
    notes TEXT,
    reported_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,  -- When to consider stale
    last_verified TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_cyno_jammers_system ON intel_cyno_jammers(solar_system_id);
CREATE INDEX IF NOT EXISTS idx_cyno_jammers_alliance ON intel_cyno_jammers(alliance_id);

-- View: ADM levels with system names
CREATE OR REPLACE VIEW v_sovereignty_adm AS
SELECT
    ss.solar_system_id,
    srm.solar_system_name,
    srm.region_id,
    srm.region_name,
    srm.security_status,
    ss.alliance_id,
    COALESCE(anc.alliance_name, 'Unknown') as alliance_name,
    ss.structure_type_id,
    CASE ss.structure_type_id
        WHEN 32226 THEN 'TCU'
        WHEN 32458 THEN 'IHUB'
        ELSE 'Unknown'
    END as structure_type,
    ss.vulnerability_occupancy_level as adm_level,
    ss.vulnerable_start_time,
    ss.vulnerable_end_time,
    ss.last_updated
FROM sovereignty_structures ss
JOIN system_region_map srm ON ss.solar_system_id = srm.solar_system_id
LEFT JOIN alliance_name_cache anc ON ss.alliance_id = anc.alliance_id;

-- View: Cyno jammer intel with system names
CREATE OR REPLACE VIEW v_cyno_jammers AS
SELECT
    cj.id,
    cj.solar_system_id,
    srm.solar_system_name,
    srm.region_id,
    srm.region_name,
    srm.security_status,
    cj.alliance_id,
    COALESCE(anc.alliance_name, 'Unknown') as alliance_name,
    cj.reported_by,
    cj.confirmed,
    cj.notes,
    cj.reported_at,
    cj.expires_at,
    cj.last_verified,
    CASE
        WHEN cj.expires_at IS NOT NULL AND cj.expires_at < NOW() THEN 'expired'
        WHEN cj.confirmed THEN 'confirmed'
        ELSE 'unconfirmed'
    END as status
FROM intel_cyno_jammers cj
JOIN system_region_map srm ON cj.solar_system_id = srm.solar_system_id
LEFT JOIN alliance_name_cache anc ON cj.alliance_id = anc.alliance_id;

COMMENT ON TABLE sovereignty_structures IS 'ESI sovereignty structures (TCU, IHUB) with ADM levels';
COMMENT ON TABLE intel_cyno_jammers IS 'Manual intel for cyno jammers (not available via public ESI)';
COMMENT ON VIEW v_sovereignty_adm IS 'ADM levels with system/region/alliance names';
COMMENT ON VIEW v_cyno_jammers IS 'Cyno jammer intel with system names and status';
