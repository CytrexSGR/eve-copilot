-- Migration 090: Sovereignty Resource Topology
-- Phase 7 — System topology, resource balance, skyhook/metenox tracking

-- =============================================================================
-- Sun Power Lookup (estimated values — CCP doesn't expose exact numbers)
-- =============================================================================

CREATE TABLE IF NOT EXISTS sun_power_values (
    sun_type_id     INTEGER PRIMARY KEY,
    sun_name        VARCHAR(100) NOT NULL,
    base_power      INTEGER NOT NULL,
    category        VARCHAR(20) NOT NULL  -- blue, yellow, orange, red, white, other
);

-- Power values based on EVE lore: Blue > Yellow > Orange > Red
-- Range 500-1000 as per CCP patch notes
INSERT INTO sun_power_values (sun_type_id, sun_name, base_power, category) VALUES
-- Blue suns (highest power: 900-1000)
(3801, 'Sun A0 (Blue Small)', 950, 'blue'),
(45034, 'Sun A0 (Blue Small)', 950, 'blue'),
(45035, 'Sun B0 (Blue)', 1000, 'blue'),
(9,     'Sun B0 (Blue)', 1000, 'blue'),
(45042, 'Sun O1 (Blue Bright)', 1000, 'blue'),
(10,    'Sun O1 (Blue Bright)', 1000, 'blue'),
-- Yellow suns (medium-high: 750-850)
(6,     'Sun G5 (Yellow)', 800, 'yellow'),
(45030, 'Sun G5 (Yellow)', 800, 'yellow'),
(45047, 'Sun G5 (Yellow)', 800, 'yellow'),
(3797,  'Sun G5 (Pink)', 780, 'yellow'),
(45036, 'Sun G5 (Pink)', 780, 'yellow'),
-- Orange/Pink suns (medium: 600-750)
(7,     'Sun K7 (Orange)', 650, 'orange'),
(45032, 'Sun K7 (Orange)', 650, 'orange'),
(45031, 'Sun K7 (Orange)', 650, 'orange'),
(3798,  'Sun K5 (Orange Bright)', 700, 'orange'),
(45037, 'Sun K5 (Orange Bright)', 700, 'orange'),
(3799,  'Sun G3 (Pink Small)', 720, 'orange'),
(45038, 'Sun G3 (Pink Small)', 720, 'orange'),
(3800,  'Sun M0 (Orange radiant)', 600, 'orange'),
(45039, 'Sun M0 (Orange radiant)', 600, 'orange'),
(45040, 'Sun M0 (Orange radiant)', 600, 'orange'),
-- Red suns (low: 500-600)
(8,     'Sun K5 (Red Giant)', 550, 'red'),
(45033, 'Sun K5 (Red Giant)', 550, 'red'),
(3802,  'Sun K3 (Yellow Small)', 620, 'red'),
(45041, 'Sun K3 (Yellow Small)', 620, 'red'),
-- White/Other (medium: 650-700)
(45043, 'Sun F0 (White)', 700, 'white'),
(11,    'Sun F0 (White)', 700, 'white'),
(45044, 'Sun White Dwarf', 500, 'white'),
(45045, 'Sun Pulsar', 900, 'other'),
(45046, 'Sun Wolf-Rayet', 850, 'other')
ON CONFLICT (sun_type_id) DO NOTHING;

-- =============================================================================
-- Planet Power/Workforce Values (per planet type)
-- =============================================================================

CREATE TABLE IF NOT EXISTS planet_resource_values (
    planet_type     VARCHAR(30) PRIMARY KEY,
    power_output    INTEGER NOT NULL DEFAULT 0,
    workforce_output INTEGER NOT NULL DEFAULT 0,
    reagent_type    VARCHAR(50),  -- magmatic_gas, superionic_ice, NULL
    reagent_output  INTEGER NOT NULL DEFAULT 0,
    description     TEXT
);

INSERT INTO planet_resource_values (planet_type, power_output, workforce_output, reagent_type, reagent_output, description) VALUES
('Plasma',    100, 0, NULL, 0,             'Highest power planet'),
('Storm',     65,  0, NULL, 0,             'Medium power planet'),
('Gas',       30,  0, NULL, 0,             'Low power planet'),
('Temperate', 0,   4000, NULL, 0,          'Highest workforce planet'),
('Oceanic',   0,   3000, NULL, 0,          'Medium workforce planet'),
('Barren',    0,   2000, NULL, 0,          'Low workforce planet'),
('Lava',      0,   0, 'magmatic_gas', 55,  'Produces Magmatic Gas reagent'),
('Ice',       0,   0, 'superionic_ice', 55, 'Produces Superionic Ice reagent'),
('Shattered', 0,   0, NULL, 0,             'No Equinox resources')
ON CONFLICT (planet_type) DO NOTHING;

-- =============================================================================
-- System Topology (seeded from SDE)
-- =============================================================================

CREATE TABLE IF NOT EXISTS system_topology (
    system_id       INTEGER PRIMARY KEY,
    system_name     VARCHAR(100) NOT NULL,
    constellation_id INTEGER NOT NULL,
    region_id       INTEGER NOT NULL,
    security        NUMERIC(6,4) NOT NULL DEFAULT 0,
    sun_type_id     INTEGER,
    base_power      INTEGER NOT NULL DEFAULT 0,
    -- Planet counts per type
    cnt_plasma      SMALLINT NOT NULL DEFAULT 0,
    cnt_storm       SMALLINT NOT NULL DEFAULT 0,
    cnt_gas         SMALLINT NOT NULL DEFAULT 0,
    cnt_lava        SMALLINT NOT NULL DEFAULT 0,
    cnt_ice         SMALLINT NOT NULL DEFAULT 0,
    cnt_temperate   SMALLINT NOT NULL DEFAULT 0,
    cnt_oceanic     SMALLINT NOT NULL DEFAULT 0,
    cnt_barren      SMALLINT NOT NULL DEFAULT 0,
    -- Computed maximum potential
    max_potential_power INTEGER GENERATED ALWAYS AS (
        base_power + cnt_plasma * 100 + cnt_storm * 65 + cnt_gas * 30
    ) STORED,
    max_potential_workforce INTEGER GENERATED ALWAYS AS (
        cnt_temperate * 4000 + cnt_oceanic * 3000 + cnt_barren * 2000
    ) STORED
);

CREATE INDEX idx_system_topology_region ON system_topology (region_id);
CREATE INDEX idx_system_topology_security ON system_topology (security);

-- Seed from SDE (nullsec + lowsec systems only)
INSERT INTO system_topology (
    system_id, system_name, constellation_id, region_id, security, sun_type_id, base_power,
    cnt_plasma, cnt_storm, cnt_gas, cnt_lava, cnt_ice, cnt_temperate, cnt_oceanic, cnt_barren
)
SELECT
    ss."solarSystemID",
    ss."solarSystemName",
    ss."constellationID",
    ss."regionID",
    COALESCE(ss.security, 0),
    ss."sunTypeID",
    COALESCE(spv.base_power, 600),  -- default 600 for unknown sun types
    COALESCE(pc.cnt_plasma, 0),
    COALESCE(pc.cnt_storm, 0),
    COALESCE(pc.cnt_gas, 0),
    COALESCE(pc.cnt_lava, 0),
    COALESCE(pc.cnt_ice, 0),
    COALESCE(pc.cnt_temperate, 0),
    COALESCE(pc.cnt_oceanic, 0),
    COALESCE(pc.cnt_barren, 0)
FROM "mapSolarSystems" ss
LEFT JOIN sun_power_values spv ON ss."sunTypeID" = spv.sun_type_id
LEFT JOIN (
    SELECT
        md."solarSystemID",
        COUNT(*) FILTER (WHERE t."typeName" = 'Planet (Plasma)') AS cnt_plasma,
        COUNT(*) FILTER (WHERE t."typeName" = 'Planet (Storm)') AS cnt_storm,
        COUNT(*) FILTER (WHERE t."typeName" = 'Planet (Gas)') AS cnt_gas,
        COUNT(*) FILTER (WHERE t."typeName" = 'Planet (Lava)') AS cnt_lava,
        COUNT(*) FILTER (WHERE t."typeName" = 'Planet (Ice)') AS cnt_ice,
        COUNT(*) FILTER (WHERE t."typeName" = 'Planet (Temperate)') AS cnt_temperate,
        COUNT(*) FILTER (WHERE t."typeName" = 'Planet (Oceanic)') AS cnt_oceanic,
        COUNT(*) FILTER (WHERE t."typeName" = 'Planet (Barren)') AS cnt_barren
    FROM "mapDenormalize" md
    JOIN "invTypes" t ON md."typeID" = t."typeID"
    JOIN "invGroups" g ON t."groupID" = g."groupID"
    WHERE g."groupName" = 'Planet'
    GROUP BY md."solarSystemID"
) pc ON ss."solarSystemID" = pc."solarSystemID"
WHERE ss.security < 0.5  -- Nullsec and Lowsec only
  AND ss."regionID" < 11000000  -- Exclude wormhole regions
ON CONFLICT (system_id) DO NOTHING;

-- =============================================================================
-- Resource Balance (dynamic — updated by ESI sync)
-- =============================================================================

CREATE TABLE IF NOT EXISTS system_resource_balance (
    system_id           INTEGER PRIMARY KEY REFERENCES system_topology(system_id),
    owner_alliance_id   BIGINT,
    owner_alliance_name VARCHAR(200),
    -- Generated resources (from online skyhooks)
    generated_power     INTEGER NOT NULL DEFAULT 0,
    generated_workforce INTEGER NOT NULL DEFAULT 0,
    -- Consumed by upgrades
    load_power          INTEGER NOT NULL DEFAULT 0,
    load_workforce      INTEGER NOT NULL DEFAULT 0,
    -- Net balance (positive = surplus, negative = deficit)
    net_power           INTEGER GENERATED ALWAYS AS (generated_power - load_power) STORED,
    net_workforce       INTEGER GENERATED ALWAYS AS (generated_workforce - load_workforce) STORED,
    -- Workforce transfers
    workforce_import    INTEGER NOT NULL DEFAULT 0,
    workforce_export    INTEGER NOT NULL DEFAULT 0,
    -- Status
    is_power_compliant  BOOLEAN GENERATED ALWAYS AS (generated_power >= load_power) STORED,
    installed_upgrades  JSONB NOT NULL DEFAULT '[]',
    last_updated        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_resource_balance_alliance ON system_resource_balance (owner_alliance_id);

-- =============================================================================
-- Skyhook Status
-- =============================================================================

CREATE TABLE IF NOT EXISTS skyhook_status (
    structure_id    BIGINT PRIMARY KEY,
    system_id       INTEGER NOT NULL,
    planet_id       BIGINT,
    planet_type     VARCHAR(30),
    type_id         INTEGER,
    structure_name  VARCHAR(255),
    power_output    INTEGER NOT NULL DEFAULT 0,
    workforce_output INTEGER NOT NULL DEFAULT 0,
    reagent_type    VARCHAR(50),
    reagent_rate    INTEGER NOT NULL DEFAULT 0,
    reagent_stock   JSONB NOT NULL DEFAULT '{}',
    vulnerability_start TIMESTAMPTZ,
    vulnerability_end   TIMESTAMPTZ,
    last_siphon_alert   TIMESTAMPTZ,
    state           VARCHAR(20) NOT NULL DEFAULT 'unknown',
    last_updated    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_skyhook_system ON skyhook_status (system_id);
CREATE INDEX idx_skyhook_state ON skyhook_status (state);

-- =============================================================================
-- Metenox Drills
-- =============================================================================

CREATE TABLE IF NOT EXISTS metenox_drills (
    structure_id    BIGINT PRIMARY KEY,
    system_id       INTEGER NOT NULL,
    moon_id         BIGINT,
    structure_name  VARCHAR(255),
    moon_composition JSONB NOT NULL DEFAULT '{}',
    fuel_blocks_qty INTEGER NOT NULL DEFAULT 0,
    magmatic_gas_qty INTEGER NOT NULL DEFAULT 0,
    fuel_expires    TIMESTAMPTZ,
    daily_yield_m3  NUMERIC(12,2) NOT NULL DEFAULT 0,
    accumulated_ore JSONB NOT NULL DEFAULT '{}',
    output_bay_used_m3 NUMERIC(12,2) NOT NULL DEFAULT 0,
    output_bay_capacity_m3 NUMERIC(12,2) NOT NULL DEFAULT 500000,
    state           VARCHAR(20) NOT NULL DEFAULT 'unknown',
    last_asset_sync TIMESTAMPTZ,
    last_updated    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_metenox_system ON metenox_drills (system_id);

-- =============================================================================
-- Sov Hub Upgrades Reference (from community data)
-- =============================================================================

CREATE TABLE IF NOT EXISTS sov_upgrade_types (
    type_id         INTEGER PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    category        VARCHAR(30) NOT NULL,  -- strategic, military, industrial
    power_cost      INTEGER NOT NULL DEFAULT 0,
    workforce_cost  INTEGER NOT NULL DEFAULT 0,
    reagent_type    VARCHAR(50),
    reagent_rate    INTEGER NOT NULL DEFAULT 0,
    description     TEXT
);

-- Seed known upgrade costs
INSERT INTO sov_upgrade_types (type_id, name, category, power_cost, workforce_cost, reagent_type, reagent_rate, description) VALUES
-- Strategic
(1, 'Cynosural Suppression', 'strategic', 250, 4500, 'magmatic_gas', 40, 'System-wide cyno jamming'),
(2, 'Advanced Logistics Network', 'strategic', 500, 18100, NULL, 0, 'Ansiblex jump gate'),
(3, 'Cynosural Navigation', 'strategic', 200, 3200, NULL, 0, 'Pharolux cyno beacon'),
(4, 'Supercapital Construction Facilities', 'strategic', 700, 25000, 'superionic_ice', 90, 'Build supers/titans'),
-- Military
(10, 'Minor Threat Detection Array 1', 'military', 100, 700, NULL, 0, 'Pirate detection level 1'),
(11, 'Minor Threat Detection Array 2', 'military', 200, 1400, NULL, 0, 'Pirate detection level 2'),
(12, 'Minor Threat Detection Array 3', 'military', 300, 2100, NULL, 0, 'Pirate detection level 3'),
(13, 'Major Threat Detection Array 1', 'military', 400, 2700, NULL, 0, 'Major pirate detection 1'),
(14, 'Major Threat Detection Array 2', 'military', 800, 5000, NULL, 0, 'Major pirate detection 2'),
(15, 'Major Threat Detection Array 3', 'military', 1300, 7300, NULL, 0, 'Major pirate detection 3'),
-- Industrial
(20, 'Metenox Moon Drill', 'industrial', 300, 5000, 'magmatic_gas', 55, 'Automated moon mining'),
(21, 'Tritanium Prospecting Array 1', 'industrial', 500, 6400, NULL, 0, 'Ore anomalies tier 1'),
(22, 'Tritanium Prospecting Array 2', 'industrial', 900, 9500, NULL, 0, 'Ore anomalies tier 2'),
(23, 'Tritanium Prospecting Array 3', 'industrial', 1350, 12700, NULL, 0, 'Ore anomalies tier 3')
ON CONFLICT (type_id) DO NOTHING;

COMMENT ON TABLE system_topology IS 'System resource topology seeded from SDE — power/workforce capacity';
COMMENT ON TABLE system_resource_balance IS 'Dynamic resource balance per system (updated by ESI sync)';
COMMENT ON TABLE skyhook_status IS 'Orbital Skyhook status and cargo monitoring';
COMMENT ON TABLE metenox_drills IS 'Metenox Moon Drill fuel and yield tracking';
COMMENT ON TABLE sov_upgrade_types IS 'Sovereignty Hub upgrade reference data (power/workforce costs)';
