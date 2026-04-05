-- Migration 075: Fleet Sessions
-- HR Module - Fleet participation tracking and activity monitoring

CREATE TABLE IF NOT EXISTS fleet_sessions (
    id              SERIAL PRIMARY KEY,
    fleet_id        BIGINT,
    fleet_name      VARCHAR(255),
    character_id    BIGINT NOT NULL,
    character_name  VARCHAR(255),
    ship_type_id    INTEGER,
    ship_name       VARCHAR(255),
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ,
    solar_system_id INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Character fleet history (recent first)
CREATE INDEX idx_fleet_sessions_character
    ON fleet_sessions (character_id, start_time DESC);

-- Fleet lookup
CREATE INDEX idx_fleet_sessions_fleet
    ON fleet_sessions (fleet_id, start_time DESC)
    WHERE fleet_id IS NOT NULL;

-- Time range queries for activity reports
CREATE INDEX idx_fleet_sessions_time
    ON fleet_sessions (start_time DESC);

-- Login/activity tracking (last seen)
CREATE TABLE IF NOT EXISTS character_activity_log (
    id              SERIAL PRIMARY KEY,
    character_id    BIGINT NOT NULL,
    event_type      VARCHAR(50) NOT NULL CHECK (event_type IN ('login', 'logout', 'fleet_join', 'fleet_leave', 'kill', 'death')),
    details         JSONB DEFAULT '{}',
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Character activity timeline
CREATE INDEX idx_activity_log_character
    ON character_activity_log (character_id, recorded_at DESC);

-- Event type filtering
CREATE INDEX idx_activity_log_type
    ON character_activity_log (event_type, recorded_at DESC);

COMMENT ON TABLE fleet_sessions IS 'Fleet participation records for activity tracking';
COMMENT ON TABLE character_activity_log IS 'General activity events (login, fleet, kills) for member monitoring';
