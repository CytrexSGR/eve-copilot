-- Migration: Arbitrage opportunities cache
-- Pre-calculated arbitrage routes for fast API responses

CREATE TABLE IF NOT EXISTS arbitrage_routes (
    id SERIAL PRIMARY KEY,
    from_region_id INTEGER NOT NULL,
    to_region_id INTEGER NOT NULL,
    from_hub_name VARCHAR(50) NOT NULL,
    to_hub_name VARCHAR(50) NOT NULL,
    jumps INTEGER NOT NULL,

    -- Aggregated metrics
    total_items INTEGER NOT NULL DEFAULT 0,
    total_volume NUMERIC(15, 2) NOT NULL DEFAULT 0,
    total_buy_cost NUMERIC(20, 2) NOT NULL DEFAULT 0,
    total_sell_value NUMERIC(20, 2) NOT NULL DEFAULT 0,
    total_profit NUMERIC(20, 2) NOT NULL DEFAULT 0,
    profit_per_jump NUMERIC(15, 2) NOT NULL DEFAULT 0,
    profit_per_hour NUMERIC(20, 2) NOT NULL DEFAULT 0,
    roi_percent NUMERIC(8, 2) NOT NULL DEFAULT 0,

    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(from_region_id, to_region_id)
);

CREATE TABLE IF NOT EXISTS arbitrage_route_items (
    id SERIAL PRIMARY KEY,
    route_id INTEGER NOT NULL REFERENCES arbitrage_routes(id) ON DELETE CASCADE,

    type_id INTEGER NOT NULL,
    type_name VARCHAR(255) NOT NULL,
    buy_price_source NUMERIC(20, 2) NOT NULL,
    sell_price_dest NUMERIC(20, 2) NOT NULL,
    quantity INTEGER NOT NULL,
    volume NUMERIC(15, 2) NOT NULL,
    profit_per_unit NUMERIC(15, 2) NOT NULL,
    total_profit NUMERIC(20, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_arbitrage_routes_from ON arbitrage_routes(from_region_id);
CREATE INDEX IF NOT EXISTS idx_arbitrage_routes_profit ON arbitrage_routes(total_profit DESC);
CREATE INDEX IF NOT EXISTS idx_arbitrage_route_items_route ON arbitrage_route_items(route_id);

COMMENT ON TABLE arbitrage_routes IS 'Pre-calculated arbitrage routes between trade hubs';
COMMENT ON TABLE arbitrage_route_items IS 'Items to haul for each arbitrage route';
