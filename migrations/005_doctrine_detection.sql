-- migrations/005_doctrine_detection.sql
-- Doctrine detection tables

-- Known doctrine templates
CREATE TABLE IF NOT EXISTS doctrine_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    ship_type_ids INT[] NOT NULL,
    weapon_group_ids INT[],
    tank_type VARCHAR(20) NOT NULL,
    role VARCHAR(20) NOT NULL,
    engagement_range VARCHAR(20),
    typical_dps_min INT,
    typical_dps_max INT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed common doctrines
INSERT INTO doctrine_templates (name, display_name, ship_type_ids, weapon_group_ids, tank_type, role, engagement_range, typical_dps_min, typical_dps_max) VALUES
('ferox_fleet', 'Ferox Fleet', ARRAY[37480], ARRAY[74,75], 'shield', 'dps', 'long', 400, 500),
('muninn_fleet', 'Muninn Fleet', ARRAY[12015], ARRAY[55], 'armor', 'dps', 'long', 480, 580),
('eagle_fleet', 'Eagle Fleet', ARRAY[12011], ARRAY[74], 'shield', 'dps', 'long', 350, 450),
('cerberus_fleet', 'Cerberus Fleet', ARRAY[11993], ARRAY[507], 'shield', 'dps', 'long', 400, 550),
('sacrilege_fleet', 'Sacrilege Fleet', ARRAY[12023], ARRAY[507], 'armor', 'dps', 'medium', 400, 500),
('nightmare_fleet', 'Nightmare Fleet', ARRAY[17736], ARRAY[53], 'armor', 'dps', 'sniper', 600, 800),
('machariel_fleet', 'Machariel Fleet', ARRAY[17738], ARRAY[55], 'armor', 'dps', 'medium', 700, 900),
('hurricane_fleet', 'Hurricane Fleet', ARRAY[24690], ARRAY[55], 'armor', 'dps', 'medium', 500, 650),
('drake_fleet', 'Drake Fleet', ARRAY[24698], ARRAY[507], 'shield', 'dps', 'medium', 300, 400),
('osprey_logi', 'Osprey Logistics', ARRAY[620], NULL, 'shield', 'logi', 'medium', 0, 0),
('scimitar_logi', 'Scimitar Logistics', ARRAY[11978], NULL, 'shield', 'logi', 'long', 0, 0),
('guardian_logi', 'Guardian Logistics', ARRAY[11987], NULL, 'armor', 'logi', 'medium', 0, 0),
('huginn_support', 'Huginn Support', ARRAY[12013], NULL, 'shield', 'support', 'long', 100, 200),
('lachesis_support', 'Lachesis Support', ARRAY[12021], NULL, 'armor', 'support', 'long', 100, 200)
ON CONFLICT (name) DO NOTHING;

-- Detected doctrines by alliance (clustered fittings)
CREATE TABLE IF NOT EXISTS detected_doctrines (
    id SERIAL PRIMARY KEY,
    alliance_id INT NOT NULL,
    doctrine_template_id INT REFERENCES doctrine_templates(id),
    doctrine_name VARCHAR(100),
    is_known_doctrine BOOLEAN DEFAULT TRUE,
    ship_type_id INT NOT NULL,
    fit_hash VARCHAR(64),
    sightings INT DEFAULT 1,
    first_seen TIMESTAMP NOT NULL,
    last_seen TIMESTAMP NOT NULL,
    avg_dps NUMERIC(8,2),
    tank_type VARCHAR(20),
    weapon_type VARCHAR(50),
    engagement_range VARCHAR(20),
    example_fitting JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(alliance_id, fit_hash)
);

CREATE INDEX IF NOT EXISTS idx_dd_alliance ON detected_doctrines(alliance_id);
CREATE INDEX IF NOT EXISTS idx_dd_last_seen ON detected_doctrines(last_seen);

-- Fleet compositions detected from killmail attackers
CREATE TABLE IF NOT EXISTS fleet_compositions (
    id SERIAL PRIMARY KEY,
    killmail_id BIGINT,
    primary_alliance_id INT,
    estimated_fleet_size INT NOT NULL,
    doctrine_mix JSONB NOT NULL,
    dps_count INT DEFAULT 0,
    logi_count INT DEFAULT 0,
    support_count INT DEFAULT 0,
    capital_count INT DEFAULT 0,
    logi_ratio NUMERIC(4,3),
    support_ratio NUMERIC(4,3),
    estimated_total_dps NUMERIC(10,2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fc_alliance ON fleet_compositions(primary_alliance_id);
CREATE INDEX IF NOT EXISTS idx_fc_killmail ON fleet_compositions(killmail_id);
