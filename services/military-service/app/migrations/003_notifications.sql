CREATE TABLE IF NOT EXISTS notification_configs (
    id              SERIAL PRIMARY KEY,
    corporation_id  BIGINT NOT NULL,
    channel_type    VARCHAR(20) DEFAULT 'discord',
    webhook_url     TEXT NOT NULL,
    event_types     TEXT[] NOT NULL,
    ping_role       VARCHAR(100),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notification_log (
    id              SERIAL PRIMARY KEY,
    config_id       INT REFERENCES notification_configs(id),
    event_type      VARCHAR(50) NOT NULL,
    reference_id    INT,
    sent_at         TIMESTAMPTZ DEFAULT NOW(),
    success         BOOLEAN DEFAULT TRUE,
    error_message   TEXT,
    UNIQUE (config_id, event_type, reference_id)
);

CREATE INDEX IF NOT EXISTS idx_notif_config_corp ON notification_configs(corporation_id);
CREATE INDEX IF NOT EXISTS idx_notif_log_config ON notification_log(config_id);
