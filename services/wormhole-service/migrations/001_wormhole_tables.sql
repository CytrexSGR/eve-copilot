-- Wormhole Service Tables
-- Extends SDE data with community sources and computed intelligence

-- ============================================================================
-- STATIC DATA TABLES (from Pathfinder community)
-- ============================================================================

-- System Statics: Which static WHs does each J-space system have
CREATE TABLE IF NOT EXISTS wormhole_system_statics (
    id SERIAL PRIMARY KEY,
    system_id BIGINT NOT NULL,
    wormhole_type_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(system_id, wormhole_type_id)
);

CREATE INDEX IF NOT EXISTS idx_wh_statics_system ON wormhole_system_statics(system_id);
CREATE INDEX IF NOT EXISTS idx_wh_statics_type ON wormhole_system_statics(wormhole_type_id);

-- Extended WH type data (scan strength from Pathfinder)
CREATE TABLE IF NOT EXISTS wormhole_type_extended (
    type_id INTEGER PRIMARY KEY,
    type_code VARCHAR(10) NOT NULL,
    scan_wormhole_strength DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- COMPUTED INTELLIGENCE TABLES
-- ============================================================================

-- Resident tracking: Who lives in which WH system
CREATE TABLE IF NOT EXISTS wormhole_residents (
    id SERIAL PRIMARY KEY,
    system_id BIGINT NOT NULL,
    corporation_id BIGINT NOT NULL,
    alliance_id BIGINT,

    -- Activity metrics (rolling 30 days)
    kill_count INTEGER DEFAULT 0,
    loss_count INTEGER DEFAULT 0,
    last_activity TIMESTAMP,
    first_seen TIMESTAMP DEFAULT NOW(),

    -- Confidence scoring
    activity_score DECIMAL(5,2) DEFAULT 0,  -- Higher = more likely resident
    is_confirmed_resident BOOLEAN DEFAULT FALSE,

    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(system_id, corporation_id)
);

CREATE INDEX IF NOT EXISTS idx_wh_residents_system ON wormhole_residents(system_id);
CREATE INDEX IF NOT EXISTS idx_wh_residents_corp ON wormhole_residents(corporation_id);
CREATE INDEX IF NOT EXISTS idx_wh_residents_alliance ON wormhole_residents(alliance_id);
CREATE INDEX IF NOT EXISTS idx_wh_residents_activity ON wormhole_residents(activity_score DESC);

-- System activity aggregates (for heatmap)
CREATE TABLE IF NOT EXISTS wormhole_system_activity (
    system_id BIGINT PRIMARY KEY,
    wormhole_class INTEGER,

    -- Rolling stats
    kills_24h INTEGER DEFAULT 0,
    kills_7d INTEGER DEFAULT 0,
    kills_30d INTEGER DEFAULT 0,

    isk_destroyed_24h BIGINT DEFAULT 0,
    isk_destroyed_7d BIGINT DEFAULT 0,
    isk_destroyed_30d BIGINT DEFAULT 0,

    capital_kills_30d INTEGER DEFAULT 0,
    unique_corps_30d INTEGER DEFAULT 0,
    unique_alliances_30d INTEGER DEFAULT 0,

    last_kill_time TIMESTAMP,
    peak_hour INTEGER,  -- 0-23 UTC hour with most activity

    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wh_activity_class ON wormhole_system_activity(wormhole_class);
CREATE INDEX IF NOT EXISTS idx_wh_activity_kills ON wormhole_system_activity(kills_30d DESC);

-- Eviction tracking (big fights in J-Space)
CREATE TABLE IF NOT EXISTS wormhole_evictions (
    id SERIAL PRIMARY KEY,
    system_id BIGINT NOT NULL,
    battle_id INTEGER REFERENCES battles(battle_id),

    -- Eviction details
    defender_corporation_id BIGINT,
    defender_alliance_id BIGINT,
    attacker_alliance_ids BIGINT[],

    -- Fight stats
    total_kills INTEGER DEFAULT 0,
    total_isk_destroyed BIGINT DEFAULT 0,
    structure_kills INTEGER DEFAULT 0,
    capital_kills INTEGER DEFAULT 0,

    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',  -- active, completed, suspected

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wh_evictions_system ON wormhole_evictions(system_id);
CREATE INDEX IF NOT EXISTS idx_wh_evictions_status ON wormhole_evictions(status);
CREATE INDEX IF NOT EXISTS idx_wh_evictions_date ON wormhole_evictions(started_at DESC);

-- ============================================================================
-- DATA IMPORT TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS wormhole_data_imports (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    import_type VARCHAR(50) NOT NULL,
    records_imported INTEGER DEFAULT 0,
    imported_at TIMESTAMP DEFAULT NOW(),
    checksum VARCHAR(64)
);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Complete WH type info combining SDE + extended data
CREATE OR REPLACE VIEW v_wormhole_types AS
SELECT
    t."typeID" as type_id,
    REPLACE(t."typeName", 'Wormhole ', '') as type_code,
    t."typeName" as type_name,
    COALESCE(ext.scan_wormhole_strength, 0) as scan_strength,
    MAX(CASE WHEN da."attributeID" = 1381 THEN da."valueFloat" END)::INTEGER as target_class,
    MAX(CASE WHEN da."attributeID" = 1382 THEN da."valueFloat" END)::INTEGER as max_stable_time_minutes,
    MAX(CASE WHEN da."attributeID" = 1383 THEN da."valueFloat" END)::BIGINT as max_stable_mass,
    MAX(CASE WHEN da."attributeID" = 1384 THEN da."valueFloat" END)::BIGINT as mass_regeneration,
    MAX(CASE WHEN da."attributeID" = 1385 THEN da."valueFloat" END)::BIGINT as max_jump_mass,
    CASE
        WHEN MAX(CASE WHEN da."attributeID" = 1385 THEN da."valueFloat" END) <= 20000000 THEN 'Frigate'
        WHEN MAX(CASE WHEN da."attributeID" = 1385 THEN da."valueFloat" END) <= 62000000 THEN 'Cruiser'
        WHEN MAX(CASE WHEN da."attributeID" = 1385 THEN da."valueFloat" END) <= 375000000 THEN 'Battleship'
        WHEN MAX(CASE WHEN da."attributeID" = 1385 THEN da."valueFloat" END) <= 1000000000 THEN 'Capital'
        ELSE 'Supercapital'
    END as max_ship_class
FROM "invTypes" t
LEFT JOIN "dgmTypeAttributes" da ON t."typeID" = da."typeID"
LEFT JOIN wormhole_type_extended ext ON t."typeID" = ext.type_id
WHERE t."groupID" = 988
GROUP BY t."typeID", t."typeName", ext.scan_wormhole_strength;

-- J-Space systems with class and statics
CREATE OR REPLACE VIEW v_wormhole_systems AS
SELECT
    ss."solarSystemID" as system_id,
    ss."solarSystemName" as system_name,
    ss."regionID" as region_id,
    r."regionName" as region_name,
    wc."wormholeClassID" as wormhole_class,
    CASE wc."wormholeClassID"
        WHEN 1 THEN 'C1' WHEN 2 THEN 'C2' WHEN 3 THEN 'C3'
        WHEN 4 THEN 'C4' WHEN 5 THEN 'C5' WHEN 6 THEN 'C6'
        WHEN 7 THEN 'High-Sec' WHEN 8 THEN 'Low-Sec' WHEN 9 THEN 'Null-Sec'
        WHEN 12 THEN 'Thera' WHEN 13 THEN 'Shattered'
        WHEN 14 THEN 'Sentinel' WHEN 15 THEN 'Barbican'
        WHEN 16 THEN 'Vidette' WHEN 17 THEN 'Conflux'
        WHEN 18 THEN 'Redoubt' WHEN 25 THEN 'Pochven'
        ELSE 'Unknown'
    END as class_name,
    ss."security" as security_status,
    -- Count statics
    (SELECT COUNT(*) FROM wormhole_system_statics wss
     WHERE wss.system_id = ss."solarSystemID") as static_count
FROM "mapSolarSystems" ss
JOIN "mapLocationWormholeClasses" wc ON ss."solarSystemID" = wc."locationID"
LEFT JOIN "mapRegions" r ON ss."regionID" = r."regionID"
WHERE wc."wormholeClassID" BETWEEN 1 AND 6
   OR wc."wormholeClassID" IN (12, 13, 14, 15, 16, 17, 18);

-- System statics with full type info
CREATE OR REPLACE VIEW v_system_statics AS
SELECT
    wss.system_id,
    ss."solarSystemName" as system_name,
    wc."wormholeClassID" as system_class,
    wt.type_id,
    wt.type_code,
    wt.target_class,
    wt.max_stable_time_minutes,
    wt.max_stable_mass,
    wt.max_jump_mass,
    wt.max_ship_class
FROM wormhole_system_statics wss
JOIN "mapSolarSystems" ss ON wss.system_id = ss."solarSystemID"
JOIN "mapLocationWormholeClasses" wc ON wss.system_id = wc."locationID"
JOIN v_wormhole_types wt ON wss.wormhole_type_id = wt.type_id;

-- Resident summary per system
CREATE OR REPLACE VIEW v_wormhole_resident_summary AS
SELECT
    wr.system_id,
    ss."solarSystemName" as system_name,
    wc."wormholeClassID" as wormhole_class,
    COUNT(DISTINCT wr.corporation_id) as resident_corps,
    COUNT(DISTINCT wr.alliance_id) FILTER (WHERE wr.alliance_id IS NOT NULL) as resident_alliances,
    SUM(wr.kill_count) as total_kills,
    SUM(wr.loss_count) as total_losses,
    MAX(wr.last_activity) as last_activity,
    MAX(wr.activity_score) as top_activity_score
FROM wormhole_residents wr
JOIN "mapSolarSystems" ss ON wr.system_id = ss."solarSystemID"
JOIN "mapLocationWormholeClasses" wc ON wr.system_id = wc."locationID"
GROUP BY wr.system_id, ss."solarSystemName", wc."wormholeClassID";

COMMENT ON TABLE wormhole_system_statics IS 'Static wormhole connections per J-space system (from Pathfinder)';
COMMENT ON TABLE wormhole_residents IS 'Detected residents per J-space system (from killmail analysis)';
COMMENT ON TABLE wormhole_system_activity IS 'Aggregated activity stats per J-space system';
COMMENT ON TABLE wormhole_evictions IS 'Large-scale fights in J-space (potential evictions)';
