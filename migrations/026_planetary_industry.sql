-- migrations/026_planetary_industry.sql
-- Planetary Industry (PI) tables for character colony data synced from ESI

-- Character PI colonies (ESI sync cache)
CREATE TABLE IF NOT EXISTS pi_colonies (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    planet_id BIGINT NOT NULL,
    planet_type VARCHAR(50),
    solar_system_id BIGINT,
    upgrade_level INT DEFAULT 0,  -- Command Center level 0-5
    num_pins INT DEFAULT 0,
    last_update TIMESTAMP,        -- ESI field
    last_sync TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(character_id, planet_id)
);

-- Buildings on colonies
CREATE TABLE IF NOT EXISTS pi_pins (
    id SERIAL PRIMARY KEY,
    colony_id INT REFERENCES pi_colonies(id) ON DELETE CASCADE,
    pin_id BIGINT NOT NULL,
    type_id BIGINT NOT NULL,
    schematic_id BIGINT,          -- What's being produced, NULL for extractors
    latitude FLOAT,
    longitude FLOAT,
    install_time TIMESTAMP,
    expiry_time TIMESTAMP,
    last_cycle_start TIMESTAMP,
    product_type_id BIGINT,       -- For extractors: what's being extracted
    qty_per_cycle INT,
    cycle_time INT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(colony_id, pin_id)
);

-- Material flow between pins
CREATE TABLE IF NOT EXISTS pi_routes (
    id SERIAL PRIMARY KEY,
    colony_id INT REFERENCES pi_colonies(id) ON DELETE CASCADE,
    route_id BIGINT NOT NULL,
    source_pin_id BIGINT,
    destination_pin_id BIGINT,
    content_type_id BIGINT,
    quantity INT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(colony_id, route_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pi_colonies_character ON pi_colonies(character_id);
CREATE INDEX IF NOT EXISTS idx_pi_pins_colony ON pi_pins(colony_id);
CREATE INDEX IF NOT EXISTS idx_pi_pins_expiry ON pi_pins(expiry_time) WHERE expiry_time IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pi_routes_colony ON pi_routes(colony_id);

-- Comments
COMMENT ON TABLE pi_colonies IS 'Character PI colonies synced from ESI';
COMMENT ON TABLE pi_pins IS 'PI buildings (extractors, factories, storage) on colonies';
COMMENT ON TABLE pi_routes IS 'Material flow routes between PI pins';
COMMENT ON COLUMN pi_colonies.upgrade_level IS 'Command Center level 0-5';
COMMENT ON COLUMN pi_pins.schematic_id IS 'Production schematic ID (NULL for extractors)';
COMMENT ON COLUMN pi_pins.product_type_id IS 'For extractors: the resource being extracted';
