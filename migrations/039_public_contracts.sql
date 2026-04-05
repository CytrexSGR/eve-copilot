-- Migration: 039_public_contracts.sql
-- Description: Public contracts scanner for finding profitable opportunities
-- Date: 2026-01-23

-- Public contracts cache (from ESI /contracts/public/{region_id}/)
CREATE TABLE IF NOT EXISTS public_contracts (
    contract_id BIGINT PRIMARY KEY,
    region_id INTEGER NOT NULL,
    type VARCHAR(20) NOT NULL,  -- 'item_exchange', 'courier', 'auction'
    issuer_id BIGINT NOT NULL,
    issuer_corporation_id BIGINT NOT NULL,
    assignee_id BIGINT,
    title TEXT,

    -- Location info
    start_location_id BIGINT,
    end_location_id BIGINT,

    -- Pricing
    price NUMERIC(20, 2),
    reward NUMERIC(20, 2),
    collateral NUMERIC(20, 2),
    buyout NUMERIC(20, 2),
    volume FLOAT,

    -- Status
    date_issued TIMESTAMP WITH TIME ZONE,
    date_expired TIMESTAMP WITH TIME ZONE,
    days_to_complete INTEGER,
    for_corporation BOOLEAN DEFAULT FALSE,

    -- Analysis
    estimated_value NUMERIC(20, 2),  -- Calculated from items
    profit_potential NUMERIC(20, 2), -- price - estimated_value (for item_exchange)
    profit_margin FLOAT,             -- profit / estimated_value * 100

    -- Metadata
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_public_contracts_region ON public_contracts(region_id);
CREATE INDEX IF NOT EXISTS idx_public_contracts_type ON public_contracts(type);
CREATE INDEX IF NOT EXISTS idx_public_contracts_profit ON public_contracts(profit_potential DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_public_contracts_expired ON public_contracts(date_expired);

-- Contract items cache
CREATE TABLE IF NOT EXISTS public_contract_items (
    id SERIAL PRIMARY KEY,
    contract_id BIGINT NOT NULL REFERENCES public_contracts(contract_id) ON DELETE CASCADE,
    type_id INTEGER NOT NULL,
    quantity BIGINT NOT NULL,
    is_included BOOLEAN NOT NULL,  -- true = offered, false = requested
    is_blueprint_copy BOOLEAN DEFAULT FALSE,
    material_efficiency INTEGER,
    time_efficiency INTEGER,
    runs INTEGER,

    -- Pricing (calculated)
    unit_price NUMERIC(20, 2),
    total_price NUMERIC(20, 2),

    UNIQUE(contract_id, type_id, is_included)
);

CREATE INDEX IF NOT EXISTS idx_contract_items_contract ON public_contract_items(contract_id);
CREATE INDEX IF NOT EXISTS idx_contract_items_type ON public_contract_items(type_id);

-- Profitable opportunities view
CREATE OR REPLACE VIEW v_profitable_contracts AS
SELECT
    pc.contract_id,
    pc.region_id,
    rm.region_name,
    pc.type,
    pc.title,
    pc.price,
    pc.estimated_value,
    pc.profit_potential,
    pc.profit_margin,
    pc.volume,
    pc.date_expired,
    pc.issuer_id,
    -- Calculate hours remaining
    EXTRACT(EPOCH FROM (pc.date_expired - NOW())) / 3600 as hours_remaining,
    -- Station names (if in our cache)
    start_loc.station_name as start_location_name,
    end_loc.station_name as end_location_name
FROM public_contracts pc
LEFT JOIN region_name_cache rm ON pc.region_id = rm.region_id
LEFT JOIN station_name_cache start_loc ON pc.start_location_id = start_loc.station_id
LEFT JOIN station_name_cache end_loc ON pc.end_location_id = end_loc.station_id
WHERE pc.date_expired > NOW()
  AND pc.profit_potential > 0
ORDER BY pc.profit_potential DESC;

-- Courier contracts view
CREATE OR REPLACE VIEW v_courier_contracts AS
SELECT
    pc.contract_id,
    pc.region_id,
    rm.region_name,
    pc.title,
    pc.reward,
    pc.collateral,
    pc.volume,
    pc.days_to_complete,
    pc.start_location_id,
    pc.end_location_id,
    pc.date_expired,
    -- Calculate ISK/m3
    CASE WHEN pc.volume > 0 THEN pc.reward / pc.volume ELSE 0 END as isk_per_m3,
    -- Calculate reward/collateral ratio
    CASE WHEN pc.collateral > 0 THEN (pc.reward / pc.collateral) * 100 ELSE 0 END as reward_collateral_pct,
    EXTRACT(EPOCH FROM (pc.date_expired - NOW())) / 3600 as hours_remaining
FROM public_contracts pc
LEFT JOIN region_name_cache rm ON pc.region_id = rm.region_id
WHERE pc.type = 'courier'
  AND pc.date_expired > NOW()
ORDER BY isk_per_m3 DESC;

-- Region name cache (if not exists)
CREATE TABLE IF NOT EXISTS region_name_cache (
    region_id INTEGER PRIMARY KEY,
    region_name VARCHAR(100) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Station name cache (if not exists)
CREATE TABLE IF NOT EXISTS station_name_cache (
    station_id BIGINT PRIMARY KEY,
    station_name VARCHAR(200) NOT NULL,
    system_id INTEGER,
    region_id INTEGER,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE public_contracts IS 'Cache of public contracts from ESI for opportunity scanning';
COMMENT ON TABLE public_contract_items IS 'Items in public contracts for value estimation';
COMMENT ON VIEW v_profitable_contracts IS 'Contracts with positive profit potential sorted by profit';
COMMENT ON VIEW v_courier_contracts IS 'Courier contracts sorted by ISK/m3';
