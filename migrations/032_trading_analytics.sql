-- migrations/032_trading_analytics.sql
-- Phase 6.2: Advanced Trading Analytics

-- Aggregated P&L per item (materialized from transactions)
CREATE TABLE IF NOT EXISTS trade_pnl_summary (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    corporation_id BIGINT,  -- NULL for personal trades
    type_id INT NOT NULL,
    type_name VARCHAR(255),

    -- Quantities
    total_bought INT DEFAULT 0,
    total_sold INT DEFAULT 0,
    current_inventory INT DEFAULT 0,

    -- Values
    total_buy_value NUMERIC(20,2) DEFAULT 0,
    total_sell_value NUMERIC(20,2) DEFAULT 0,
    realized_pnl NUMERIC(20,2) DEFAULT 0,

    -- Averages
    avg_buy_price NUMERIC(20,2) DEFAULT 0,
    avg_sell_price NUMERIC(20,2) DEFAULT 0,

    -- Metrics
    margin_percent NUMERIC(8,4) DEFAULT 0,
    roi_percent NUMERIC(8,4) DEFAULT 0,

    -- Timestamps
    first_trade_at TIMESTAMP,
    last_trade_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(character_id, corporation_id, type_id)
);

CREATE INDEX IF NOT EXISTS idx_trade_pnl_char ON trade_pnl_summary(character_id);
CREATE INDEX IF NOT EXISTS idx_trade_pnl_corp ON trade_pnl_summary(corporation_id) WHERE corporation_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_trade_pnl_pnl ON trade_pnl_summary(realized_pnl DESC);

-- Velocity tracking (daily aggregates)
CREATE TABLE IF NOT EXISTS trade_velocity (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    corporation_id BIGINT,
    type_id INT NOT NULL,
    trade_date DATE NOT NULL,

    buy_quantity INT DEFAULT 0,
    sell_quantity INT DEFAULT 0,
    buy_value NUMERIC(20,2) DEFAULT 0,
    sell_value NUMERIC(20,2) DEFAULT 0,

    UNIQUE(character_id, corporation_id, type_id, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_velocity_date ON trade_velocity(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_velocity_char_date ON trade_velocity(character_id, trade_date DESC);

-- Competition tracking
CREATE TABLE IF NOT EXISTS market_competitors (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    type_id INT NOT NULL,
    region_id INT NOT NULL,

    competitor_order_count INT DEFAULT 0,
    our_position INT,  -- 1 = best price, 2 = second best, etc.
    undercut_count_24h INT DEFAULT 0,
    avg_time_to_undercut_minutes INT,

    checked_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(character_id, type_id, region_id)
);

-- Trading alerts configuration
CREATE TABLE IF NOT EXISTS trading_alerts (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    alert_type VARCHAR(50) NOT NULL,  -- 'margin_low', 'undercut', 'price_drop', 'goal_reached'

    -- Alert configuration
    type_id INT,  -- NULL = all items
    threshold_value NUMERIC(20,2),
    threshold_percent NUMERIC(8,4),

    -- State
    is_enabled BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMP,
    trigger_count INT DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Trading goals
CREATE TABLE IF NOT EXISTS trading_goals (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,

    goal_type VARCHAR(50) NOT NULL,  -- 'daily_profit', 'weekly_profit', 'monthly_profit'
    target_value NUMERIC(20,2) NOT NULL,
    current_value NUMERIC(20,2) DEFAULT 0,

    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    is_achieved BOOLEAN DEFAULT false,
    achieved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Corp transaction cache (ESI data)
CREATE TABLE IF NOT EXISTS corp_transactions_cache (
    id SERIAL PRIMARY KEY,
    corporation_id BIGINT NOT NULL,
    division INT NOT NULL,
    transaction_id BIGINT NOT NULL,

    date TIMESTAMP NOT NULL,
    type_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price NUMERIC(20,2) NOT NULL,
    is_buy BOOLEAN NOT NULL,
    location_id BIGINT NOT NULL,
    client_id BIGINT,

    cached_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(corporation_id, division, transaction_id)
);

CREATE INDEX IF NOT EXISTS idx_corp_txn_date ON corp_transactions_cache(corporation_id, date DESC);

-- Corp orders cache
CREATE TABLE IF NOT EXISTS corp_orders_cache (
    id SERIAL PRIMARY KEY,
    corporation_id BIGINT NOT NULL,
    order_id BIGINT NOT NULL,

    type_id INT NOT NULL,
    is_buy_order BOOLEAN NOT NULL,
    price NUMERIC(20,2) NOT NULL,
    volume_total INT NOT NULL,
    volume_remain INT NOT NULL,
    location_id BIGINT NOT NULL,
    region_id INT NOT NULL,
    issued TIMESTAMP NOT NULL,
    duration INT NOT NULL,

    cached_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(corporation_id, order_id)
);

CREATE INDEX IF NOT EXISTS idx_corp_orders_type ON corp_orders_cache(corporation_id, type_id);

-- Portfolio snapshots for historical tracking
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    snapshot_date DATE NOT NULL,

    wallet_balance NUMERIC(20,2) DEFAULT 0,
    sell_order_value NUMERIC(20,2) DEFAULT 0,
    buy_order_escrow NUMERIC(20,2) DEFAULT 0,
    total_liquid NUMERIC(20,2) DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(character_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_char_date ON portfolio_snapshots(character_id, snapshot_date DESC);
