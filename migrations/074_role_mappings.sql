-- Migration 074: Role Mappings
-- HR Module - ESI corporation roles to web permissions mapping

CREATE TABLE IF NOT EXISTS role_mappings (
    id              SERIAL PRIMARY KEY,
    esi_role        VARCHAR(100) NOT NULL,
    web_permission  VARCHAR(100) NOT NULL,
    priority        SMALLINT NOT NULL DEFAULT 0,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Unique mapping per esi_role+web_permission
CREATE UNIQUE INDEX idx_role_mappings_unique
    ON role_mappings (esi_role, web_permission)
    WHERE active = TRUE;

-- Lookup by ESI role
CREATE INDEX idx_role_mappings_esi_role
    ON role_mappings (esi_role) WHERE active = TRUE;

-- Role sync audit log
CREATE TABLE IF NOT EXISTS role_sync_log (
    id              SERIAL PRIMARY KEY,
    character_id    BIGINT NOT NULL,
    character_name  VARCHAR(255),
    esi_roles       JSONB NOT NULL DEFAULT '[]',
    added_roles     JSONB NOT NULL DEFAULT '[]',
    removed_roles   JSONB NOT NULL DEFAULT '[]',
    escalation      BOOLEAN NOT NULL DEFAULT FALSE,
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fast lookup for character role history
CREATE INDEX idx_role_sync_character
    ON role_sync_log (character_id, synced_at DESC);

-- Escalation alerts (recent first)
CREATE INDEX idx_role_sync_escalation
    ON role_sync_log (synced_at DESC)
    WHERE escalation = TRUE;

COMMENT ON TABLE role_mappings IS 'Maps ESI corporation roles to web application permissions';
COMMENT ON TABLE role_sync_log IS 'Audit log of role synchronization events with escalation detection';
COMMENT ON COLUMN role_sync_log.escalation IS 'True if privilege escalation was detected';
