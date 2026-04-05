-- Migration: 041_moon_mining_intel.sql
-- Description: Moon mining observer data and value tracking
-- Date: 2026-01-23

-- Moon ore types with rarity classifications
CREATE TABLE IF NOT EXISTS moon_ore_types (
    type_id INTEGER PRIMARY KEY,
    type_name VARCHAR(100) NOT NULL,
    rarity VARCHAR(10) NOT NULL,  -- 'R4', 'R8', 'R16', 'R32', 'R64', 'ubiquitous', 'common', 'uncommon', 'rare', 'exceptional'
    base_value NUMERIC(20, 2),  -- ISK per unit (estimated)
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert moon ore classifications
INSERT INTO moon_ore_types (type_id, type_name, rarity) VALUES
-- R64 (most valuable)
(45513, 'Monazite', 'R64'),
(45512, 'Xenotime', 'R64'),
(45511, 'Loparite', 'R64'),
(45510, 'Ytterbite', 'R64'),
-- R32
(45506, 'Cinnabar', 'R32'),
(45507, 'Pollucite', 'R32'),
(45508, 'Zircon', 'R32'),
(45509, 'Carnotite', 'R32'),
-- R16
(45502, 'Otavite', 'R16'),
(45503, 'Sperrylite', 'R16'),
(45504, 'Vanadinite', 'R16'),
(45505, 'Chromite', 'R16'),
-- R8
(45498, 'Cobaltite', 'R8'),
(45499, 'Euxenite', 'R8'),
(45500, 'Scheelite', 'R8'),
(45501, 'Titanite', 'R8'),
-- R4 (least valuable moon ores)
(45494, 'Zeolites', 'R4'),
(45495, 'Sylvite', 'R4'),
(45496, 'Bitumite', 'R4'),
(45497, 'Coesite', 'R4')
ON CONFLICT (type_id) DO NOTHING;

-- Mining observer cache (corporation mining structures)
CREATE TABLE IF NOT EXISTS moon_mining_observers (
    observer_id BIGINT PRIMARY KEY,
    corporation_id INTEGER NOT NULL,
    observer_type VARCHAR(50) NOT NULL,  -- 'moon_drill'
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Structure info
    structure_name VARCHAR(200),
    system_id INTEGER,
    system_name VARCHAR(100),
    region_id INTEGER,

    -- Mining stats
    total_mined_volume BIGINT DEFAULT 0,
    last_extraction TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_moon_observers_corp ON moon_mining_observers(corporation_id);
CREATE INDEX IF NOT EXISTS idx_moon_observers_system ON moon_mining_observers(system_id);

-- Mining ledger entries (who mined what)
CREATE TABLE IF NOT EXISTS moon_mining_ledger (
    id SERIAL PRIMARY KEY,
    observer_id BIGINT NOT NULL REFERENCES moon_mining_observers(observer_id) ON DELETE CASCADE,

    -- Miner info
    character_id INTEGER NOT NULL,
    character_name VARCHAR(100),
    corporation_id INTEGER,

    -- Mining data
    type_id INTEGER NOT NULL,
    quantity BIGINT NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Calculated values
    estimated_value NUMERIC(20, 2),

    UNIQUE(observer_id, character_id, type_id, last_updated)
);

CREATE INDEX IF NOT EXISTS idx_moon_ledger_observer ON moon_mining_ledger(observer_id);
CREATE INDEX IF NOT EXISTS idx_moon_ledger_character ON moon_mining_ledger(character_id);
CREATE INDEX IF NOT EXISTS idx_moon_ledger_type ON moon_mining_ledger(type_id);

-- Aggregated view for moon value reporting
CREATE OR REPLACE VIEW v_moon_mining_summary AS
SELECT
    mo.observer_id,
    mo.structure_name,
    mo.system_name,
    mo.corporation_id,
    mot.rarity,
    ml.type_id,
    mot.type_name,
    SUM(ml.quantity) as total_quantity,
    SUM(ml.estimated_value) as total_value,
    COUNT(DISTINCT ml.character_id) as miner_count
FROM moon_mining_ledger ml
JOIN moon_mining_observers mo ON ml.observer_id = mo.observer_id
LEFT JOIN moon_ore_types mot ON ml.type_id = mot.type_id
WHERE ml.last_updated > NOW() - INTERVAL '30 days'
GROUP BY mo.observer_id, mo.structure_name, mo.system_name, mo.corporation_id,
         mot.rarity, ml.type_id, mot.type_name;

-- Top miners view
CREATE OR REPLACE VIEW v_top_moon_miners AS
SELECT
    ml.character_id,
    ml.character_name,
    ml.corporation_id,
    SUM(ml.quantity) as total_mined,
    SUM(ml.estimated_value) as total_value,
    COUNT(DISTINCT ml.type_id) as ore_types_mined,
    COUNT(DISTINCT ml.observer_id) as structures_used
FROM moon_mining_ledger ml
WHERE ml.last_updated > NOW() - INTERVAL '30 days'
GROUP BY ml.character_id, ml.character_name, ml.corporation_id
ORDER BY total_value DESC;

COMMENT ON TABLE moon_ore_types IS 'Moon ore classifications and rarity values';
COMMENT ON TABLE moon_mining_observers IS 'Corporation mining observers (Athanors/Tataras with moon drills)';
COMMENT ON TABLE moon_mining_ledger IS 'Individual mining records from observers';
