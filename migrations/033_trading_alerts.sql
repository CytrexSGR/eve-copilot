-- 033_trading_alerts.sql
-- Trading alerts system with Discord webhook support

-- Alert log table for storing generated alerts (separate from legacy trading_alerts)
CREATE TABLE IF NOT EXISTS trading_alert_log (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    alert_type VARCHAR(50) NOT NULL,  -- margin_low, margin_negative, undercut, outbid, velocity_warning
    severity VARCHAR(20) NOT NULL DEFAULT 'warning',  -- info, warning, critical

    -- Alert details
    type_id INTEGER,
    type_name VARCHAR(255),
    message TEXT NOT NULL,
    details JSONB,  -- Flexible storage for alert-specific data

    -- State tracking
    is_read BOOLEAN DEFAULT FALSE,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,

    -- Discord notification
    discord_sent BOOLEAN DEFAULT FALSE,
    discord_sent_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,  -- Auto-clear after expiry

    -- Prevent duplicate alerts
    alert_hash VARCHAR(64)  -- Hash of alert details for dedup
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_trading_alert_log_character ON trading_alert_log(character_id);
CREATE INDEX IF NOT EXISTS idx_trading_alert_log_type ON trading_alert_log(alert_type);
CREATE INDEX IF NOT EXISTS idx_trading_alert_log_severity ON trading_alert_log(severity);
CREATE INDEX IF NOT EXISTS idx_trading_alert_log_unread ON trading_alert_log(character_id, is_read) WHERE is_read = FALSE;
CREATE INDEX IF NOT EXISTS idx_trading_alert_log_hash ON trading_alert_log(alert_hash);
CREATE INDEX IF NOT EXISTS idx_trading_alert_log_created ON trading_alert_log(created_at DESC);

-- Unique constraint to prevent duplicate alerts within 1 hour
CREATE UNIQUE INDEX IF NOT EXISTS idx_trading_alert_log_unique
ON trading_alert_log(character_id, alert_type, type_id, alert_hash)
WHERE created_at > NOW() - INTERVAL '1 hour';

-- Discord webhook configuration per character
CREATE TABLE IF NOT EXISTS trading_discord_config (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL UNIQUE,

    -- Discord settings
    discord_webhook_url TEXT,
    discord_enabled BOOLEAN DEFAULT FALSE,

    -- Alert preferences
    alert_margin_threshold DECIMAL(5,2) DEFAULT 10.0,  -- Margin % to trigger alerts
    alert_undercut_enabled BOOLEAN DEFAULT TRUE,
    alert_velocity_enabled BOOLEAN DEFAULT TRUE,
    alert_goals_enabled BOOLEAN DEFAULT TRUE,

    -- Notification frequency
    min_alert_interval_minutes INTEGER DEFAULT 15,  -- Don't spam
    quiet_hours_start INTEGER,  -- Hour (0-23) to stop notifications
    quiet_hours_end INTEGER,    -- Hour (0-23) to resume notifications

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trading_discord_config_char ON trading_discord_config(character_id);

-- Alert history for analytics
CREATE TABLE IF NOT EXISTS trading_alert_summary (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    date DATE NOT NULL,

    -- Daily counts by type
    margin_alerts INTEGER DEFAULT 0,
    undercut_alerts INTEGER DEFAULT 0,
    outbid_alerts INTEGER DEFAULT 0,
    velocity_alerts INTEGER DEFAULT 0,
    goal_alerts INTEGER DEFAULT 0,

    -- By severity
    critical_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    info_count INTEGER DEFAULT 0,

    -- Discord stats
    discord_sent_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(character_id, date)
);

CREATE INDEX IF NOT EXISTS idx_trading_alert_summary_char ON trading_alert_summary(character_id);
CREATE INDEX IF NOT EXISTS idx_trading_alert_summary_date ON trading_alert_summary(date DESC);

-- Function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_trading_discord_config_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for auto-update
DROP TRIGGER IF EXISTS trading_discord_config_updated ON trading_discord_config;
CREATE TRIGGER trading_discord_config_updated
    BEFORE UPDATE ON trading_discord_config
    FOR EACH ROW
    EXECUTE FUNCTION update_trading_discord_config_timestamp();

-- Comments
COMMENT ON TABLE trading_alert_log IS 'Trading alert log entries with Discord support';
COMMENT ON TABLE trading_discord_config IS 'Per-character Discord alert configuration';
COMMENT ON TABLE trading_alert_summary IS 'Daily alert statistics for analytics';
