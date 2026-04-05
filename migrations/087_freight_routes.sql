-- Migration 087: Freight Routes & Pricing
-- Phase 5: Logistics & Supply Chain

CREATE TABLE IF NOT EXISTS freight_routes (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    start_system_id BIGINT NOT NULL,
    end_system_id   BIGINT NOT NULL,
    route_type      VARCHAR(20) NOT NULL DEFAULT 'jf'
                    CHECK (route_type IN ('highsec', 'lowsec', 'jf', 'wormhole', 'blops')),
    base_price      NUMERIC(15,2) NOT NULL DEFAULT 0,
    rate_per_m3     NUMERIC(12,2) NOT NULL DEFAULT 0,
    collateral_pct  NUMERIC(5,2) NOT NULL DEFAULT 1.00,
    max_volume      NUMERIC(15,2) DEFAULT 360000,  -- JF cargo hold
    max_collateral  NUMERIC(18,2) DEFAULT 3000000000,  -- 3B ISK default
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    notes           TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_freight_routes_systems
    ON freight_routes (start_system_id, end_system_id);
CREATE INDEX IF NOT EXISTS idx_freight_routes_active
    ON freight_routes (is_active) WHERE is_active = TRUE;

-- Seed common routes
-- Jita (30000142) → K-6K16 (30004751) JF route
INSERT INTO freight_routes (name, start_system_id, end_system_id, route_type, base_price, rate_per_m3, collateral_pct, max_volume, max_collateral, notes)
VALUES
    ('Jita → K-6K16 (JF)', 30000142, 30004751, 'jf',
     10000000, 700, 1.50, 360000, 3000000000,
     'Standard JF route to nullsec staging'),
    ('K-6K16 → Jita (JF)', 30004751, 30000142, 'jf',
     10000000, 700, 1.50, 360000, 3000000000,
     'Return JF route to Jita'),
    ('Jita → Amarr (Highsec)', 30000142, 30002187, 'highsec',
     2000000, 200, 1.00, 1000000, 5000000000,
     'Highsec freighter between major trade hubs'),
    ('Jita → Dodixie (Highsec)', 30000142, 30002659, 'highsec',
     3000000, 250, 1.00, 1000000, 5000000000,
     'Highsec freighter to Gallente hub'),
    ('Jita → 1DQ1-A (JF)', 30000142, 30004759, 'jf',
     15000000, 800, 2.00, 360000, 2000000000,
     'JF route to Imperium staging')
ON CONFLICT DO NOTHING;
