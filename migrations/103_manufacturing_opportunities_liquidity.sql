-- migrations/103_manufacturing_opportunities_liquidity.sql
-- Add volume/liquidity columns to manufacturing_opportunities for realistic opportunity scoring

ALTER TABLE manufacturing_opportunities
ADD COLUMN IF NOT EXISTS avg_daily_volume INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS sell_volume INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS risk_score INTEGER DEFAULT 50,
ADD COLUMN IF NOT EXISTS days_to_sell NUMERIC(10,2) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS net_profit NUMERIC(20,2) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS net_roi NUMERIC(10,2) DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_mfg_opp_volume
ON manufacturing_opportunities(avg_daily_volume DESC);

COMMENT ON COLUMN manufacturing_opportunities.avg_daily_volume IS '30-day avg daily volume from market_prices';
COMMENT ON COLUMN manufacturing_opportunities.sell_volume IS 'Current sell order volume in The Forge';
COMMENT ON COLUMN manufacturing_opportunities.risk_score IS 'Risk score 0-100 from market_prices (lower = safer)';
COMMENT ON COLUMN manufacturing_opportunities.days_to_sell IS 'Estimated days to sell 100 units';
COMMENT ON COLUMN manufacturing_opportunities.net_profit IS 'Profit after broker fee (1.5%) + sales tax (3.6%)';
COMMENT ON COLUMN manufacturing_opportunities.net_roi IS 'ROI after fees';
