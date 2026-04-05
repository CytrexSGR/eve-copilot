-- migrations/054_market_prices_trading_metrics.sql
-- Add trading metrics columns for risk assessment

ALTER TABLE market_prices
ADD COLUMN IF NOT EXISTS avg_daily_volume INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS price_volatility NUMERIC(8,4) DEFAULT 0,
ADD COLUMN IF NOT EXISTS trend_7d NUMERIC(8,4) DEFAULT 0,
ADD COLUMN IF NOT EXISTS days_to_sell_100 NUMERIC(10,2) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS risk_score INTEGER DEFAULT 50,
ADD COLUMN IF NOT EXISTS metrics_updated_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_market_prices_risk
ON market_prices(region_id, risk_score)
WHERE risk_score IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_market_prices_volume
ON market_prices(region_id, avg_daily_volume DESC)
WHERE avg_daily_volume > 0;

COMMENT ON COLUMN market_prices.avg_daily_volume IS '30-day average daily volume from ESI history';
COMMENT ON COLUMN market_prices.price_volatility IS 'Price standard deviation as percentage (30d)';
COMMENT ON COLUMN market_prices.trend_7d IS '7-day price trend as percentage';
COMMENT ON COLUMN market_prices.days_to_sell_100 IS 'Days to sell 100 units at current volume';
COMMENT ON COLUMN market_prices.risk_score IS 'Risk score 0-100 (lower = safer)';
