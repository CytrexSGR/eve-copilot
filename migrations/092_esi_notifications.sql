-- Migration 092: ESI Notifications table
-- Stores ESI character notifications for automated processing
-- (structure attacks, sov reinforcements, timer creation)

CREATE TABLE IF NOT EXISTS esi_notifications (
    notification_id BIGINT PRIMARY KEY,
    character_id BIGINT NOT NULL,
    sender_id BIGINT,
    sender_type VARCHAR(20),          -- character, corporation, alliance, faction, other
    type VARCHAR(100) NOT NULL,        -- e.g. StructureUnderAttack, SovStructureReinforced
    timestamp TIMESTAMPTZ NOT NULL,
    text TEXT,                         -- YAML body from ESI
    is_read BOOLEAN DEFAULT FALSE,
    processed BOOLEAN DEFAULT FALSE,   -- our flag: has this been acted on?
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_esi_notifications_char ON esi_notifications(character_id);
CREATE INDEX IF NOT EXISTS idx_esi_notifications_type ON esi_notifications(type);
CREATE INDEX IF NOT EXISTS idx_esi_notifications_unprocessed ON esi_notifications(processed) WHERE processed = FALSE;
CREATE INDEX IF NOT EXISTS idx_esi_notifications_timestamp ON esi_notifications(timestamp DESC);
