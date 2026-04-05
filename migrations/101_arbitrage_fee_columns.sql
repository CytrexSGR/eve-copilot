-- migrations/101_arbitrage_fee_columns.sql
-- Add fee-adjusted profit columns to arbitrage cache tables.

-- Per-item net profit data
ALTER TABLE arbitrage_route_items
ADD COLUMN IF NOT EXISTS gross_margin_pct NUMERIC(8, 2),
ADD COLUMN IF NOT EXISTS net_profit_per_unit NUMERIC(15, 2),
ADD COLUMN IF NOT EXISTS net_margin_pct NUMERIC(8, 2),
ADD COLUMN IF NOT EXISTS total_fees_per_unit NUMERIC(15, 2),
ADD COLUMN IF NOT EXISTS net_total_profit NUMERIC(20, 2);

-- Per-route net profit data
ALTER TABLE arbitrage_routes
ADD COLUMN IF NOT EXISTS net_total_profit NUMERIC(20, 2),
ADD COLUMN IF NOT EXISTS net_roi_percent NUMERIC(8, 2),
ADD COLUMN IF NOT EXISTS net_profit_per_hour NUMERIC(20, 2),
ADD COLUMN IF NOT EXISTS net_profit_per_jump NUMERIC(15, 2),
ADD COLUMN IF NOT EXISTS broker_fee_pct NUMERIC(4, 2) DEFAULT 1.50,
ADD COLUMN IF NOT EXISTS sales_tax_pct NUMERIC(4, 2) DEFAULT 3.60;

CREATE INDEX IF NOT EXISTS idx_arb_routes_net_profit
ON arbitrage_routes (from_region_id, net_total_profit DESC);
