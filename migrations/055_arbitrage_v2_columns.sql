-- Migration: Add volume and strategy columns to arbitrage items
-- For realistic quantity calculation based on market volume

ALTER TABLE arbitrage_route_items
ADD COLUMN IF NOT EXISTS avg_daily_volume INTEGER,
ADD COLUMN IF NOT EXISTS days_to_sell NUMERIC(6, 1),
ADD COLUMN IF NOT EXISTS turnover VARCHAR(20) DEFAULT 'unknown',
ADD COLUMN IF NOT EXISTS competition VARCHAR(20) DEFAULT 'medium';

-- Add route-level strategy summary
ALTER TABLE arbitrage_routes
ADD COLUMN IF NOT EXISTS avg_days_to_sell NUMERIC(6, 1),
ADD COLUMN IF NOT EXISTS route_risk VARCHAR(20) DEFAULT 'medium';

COMMENT ON COLUMN arbitrage_route_items.avg_daily_volume IS 'Average daily volume at destination hub';
COMMENT ON COLUMN arbitrage_route_items.days_to_sell IS 'Estimated days to sell quantity based on volume';
COMMENT ON COLUMN arbitrage_route_items.turnover IS 'instant, fast, moderate, slow, unknown';
COMMENT ON COLUMN arbitrage_route_items.competition IS 'low, medium, high, extreme';
