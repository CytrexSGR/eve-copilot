-- Wormhole commodity price history for sparklines and trend analysis
-- Stores daily snapshots of gas, blue loot, and polymer prices

CREATE TABLE IF NOT EXISTS wh_commodity_price_history (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    type_id INTEGER NOT NULL,
    category VARCHAR(20) NOT NULL,  -- 'gas', 'blue_loot', 'polymer'
    sell_price NUMERIC(20,2),
    buy_price NUMERIC(20,2),
    daily_volume INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for efficient queries
CREATE INDEX IF NOT EXISTS idx_wh_price_history_type_date
    ON wh_commodity_price_history(type_id, snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_wh_price_history_date
    ON wh_commodity_price_history(snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_wh_price_history_category
    ON wh_commodity_price_history(category);

-- Unique constraint to prevent duplicate snapshots
CREATE UNIQUE INDEX IF NOT EXISTS idx_wh_price_history_unique
    ON wh_commodity_price_history(type_id, snapshot_date);

-- View for 7-day price history (for sparklines)
CREATE OR REPLACE VIEW v_wh_price_sparkline AS
SELECT
    type_id,
    category,
    array_agg(sell_price ORDER BY snapshot_date ASC) as prices_7d,
    array_agg(snapshot_date ORDER BY snapshot_date ASC) as dates_7d,
    MIN(sell_price) as min_price,
    MAX(sell_price) as max_price,
    AVG(sell_price) as avg_price
FROM wh_commodity_price_history
WHERE snapshot_date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY type_id, category;

-- View for 30-day average (for historical context)
CREATE OR REPLACE VIEW v_wh_price_30d_avg AS
SELECT
    type_id,
    category,
    AVG(sell_price) as avg_30d,
    STDDEV(sell_price) as stddev_30d,
    COUNT(*) as data_points
FROM wh_commodity_price_history
WHERE snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY type_id, category;
