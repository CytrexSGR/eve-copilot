-- migrations/031_market_portfolio.sql
-- Phase 6: Market & Portfolio Tracking

-- Portfolio value snapshots (daily)
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    snapshot_date DATE NOT NULL,
    wallet_balance NUMERIC(20,2) NOT NULL DEFAULT 0,
    sell_order_value NUMERIC(20,2) NOT NULL DEFAULT 0,
    buy_order_escrow NUMERIC(20,2) NOT NULL DEFAULT 0,
    total_liquid NUMERIC(20,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(character_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_char_date
    ON portfolio_snapshots(character_id, snapshot_date DESC);

-- Undercut notification tracking (prevent spam - max 1 per order per day)
CREATE TABLE IF NOT EXISTS undercut_notifications (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    order_id BIGINT NOT NULL,
    type_id INT NOT NULL,
    your_price NUMERIC(20,2) NOT NULL,
    competitor_price NUMERIC(20,2) NOT NULL,
    undercut_percent NUMERIC(5,2) NOT NULL,
    notified_at TIMESTAMP DEFAULT NOW(),
    notified_date DATE GENERATED ALWAYS AS (DATE(notified_at)) STORED,
    UNIQUE(character_id, order_id, notified_date)
);

CREATE INDEX IF NOT EXISTS idx_undercut_char_date
    ON undercut_notifications(character_id, notified_at DESC);

-- Global app settings (JSON storage for notifications, etc.)
CREATE TABLE IF NOT EXISTS app_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default notification settings
INSERT INTO app_settings (key, value) VALUES
('notifications', '{
    "discord_webhook": null,
    "alerts": {
        "market_undercuts": false,
        "pi_expiry": false,
        "skill_complete": false,
        "low_wallet": false
    },
    "check_frequency_minutes": 15,
    "low_wallet_threshold": 100000000
}'::jsonb)
ON CONFLICT (key) DO NOTHING;
