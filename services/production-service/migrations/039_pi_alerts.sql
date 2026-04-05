-- 039_pi_alerts.sql
-- PI Alerts system for extractor/storage/pickup monitoring

-- PI Alert log table
CREATE TABLE IF NOT EXISTS pi_alert_log (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    alert_type VARCHAR(50) NOT NULL,  -- extractor_depleting, extractor_stopped, storage_full, pickup_reminder
    severity VARCHAR(20) NOT NULL DEFAULT 'warning',  -- warning, critical

    -- Alert context
    planet_id BIGINT,
    planet_name VARCHAR(255),
    pin_id BIGINT,
    product_type_id INTEGER,
    product_name VARCHAR(255),

    -- Alert details
    message TEXT NOT NULL,
    details JSONB,  -- hours_remaining, fill_percent, etc.

    -- State tracking
    is_read BOOLEAN DEFAULT FALSE,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,

    -- Discord notification
    discord_sent BOOLEAN DEFAULT FALSE,
    discord_sent_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,  -- Auto-clear after expiry (24h default)

    -- Deduplication hash
    alert_hash VARCHAR(64)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pi_alert_log_character ON pi_alert_log(character_id);
CREATE INDEX IF NOT EXISTS idx_pi_alert_log_type ON pi_alert_log(alert_type);
CREATE INDEX IF NOT EXISTS idx_pi_alert_log_severity ON pi_alert_log(severity);
CREATE INDEX IF NOT EXISTS idx_pi_alert_log_unread ON pi_alert_log(character_id, is_read) WHERE is_read = FALSE;
CREATE INDEX IF NOT EXISTS idx_pi_alert_log_created ON pi_alert_log(created_at DESC);

-- Unique constraint to prevent duplicate alerts within 6 hours
CREATE UNIQUE INDEX IF NOT EXISTS idx_pi_alert_log_unique
ON pi_alert_log(character_id, alert_type, planet_id, pin_id, alert_hash)
WHERE created_at > NOW() - INTERVAL '6 hours';

-- PI Discord webhook configuration per character (uses existing discord config if present)
CREATE TABLE IF NOT EXISTS pi_alert_config (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL UNIQUE,

    -- Discord settings
    discord_webhook_url TEXT,
    discord_enabled BOOLEAN DEFAULT TRUE,

    -- Alert thresholds
    extractor_warning_hours INTEGER DEFAULT 12,  -- Alert when < X hours remaining
    extractor_critical_hours INTEGER DEFAULT 4,   -- Critical when < X hours
    storage_warning_percent INTEGER DEFAULT 75,   -- Alert when > X% full
    storage_critical_percent INTEGER DEFAULT 90,  -- Critical when > X% full

    -- Alert preferences (enable/disable per type)
    alert_extractor_depleting BOOLEAN DEFAULT TRUE,
    alert_extractor_stopped BOOLEAN DEFAULT TRUE,
    alert_storage_full BOOLEAN DEFAULT TRUE,
    alert_factory_idle BOOLEAN DEFAULT TRUE,
    alert_pickup_reminder BOOLEAN DEFAULT TRUE,

    -- Pickup schedule
    pickup_reminder_hours INTEGER DEFAULT 48,  -- Remind every X hours
    last_pickup_reminder_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Function to clean up old alerts (older than 7 days)
CREATE OR REPLACE FUNCTION cleanup_old_pi_alerts() RETURNS void AS $$
BEGIN
    DELETE FROM pi_alert_log
    WHERE created_at < NOW() - INTERVAL '7 days'
       OR (expires_at IS NOT NULL AND expires_at < NOW());
END;
$$ LANGUAGE plpgsql;
