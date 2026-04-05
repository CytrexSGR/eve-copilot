-- Fleet Operations (PAP tracking)
CREATE TABLE IF NOT EXISTS fleet_operations (
    id              SERIAL PRIMARY KEY,
    fleet_name      VARCHAR(255) NOT NULL,
    fc_character_id BIGINT,
    fc_name         VARCHAR(255),
    doctrine_id     INTEGER,
    start_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time        TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    notes           TEXT,
    -- ESI sync fields (new)
    esi_fleet_id    BIGINT,
    sync_active     BOOLEAN DEFAULT FALSE,
    last_sync_at    TIMESTAMPTZ,
    sync_error      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fleet_snapshots (
    id              SERIAL PRIMARY KEY,
    operation_id    INTEGER NOT NULL REFERENCES fleet_operations(id) ON DELETE CASCADE,
    snapshot_time   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    member_count    INTEGER NOT NULL DEFAULT 0,
    raw_data        JSONB NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS fleet_participation (
    id              SERIAL PRIMARY KEY,
    operation_id    INTEGER NOT NULL REFERENCES fleet_operations(id) ON DELETE CASCADE,
    character_id    BIGINT NOT NULL,
    character_name  VARCHAR(255),
    ship_type_id    INTEGER,
    ship_name       VARCHAR(255),
    solar_system_id INTEGER,
    first_seen      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    snapshot_count  INTEGER NOT NULL DEFAULT 1,
    UNIQUE (operation_id, character_id)
);

-- Fleet Doctrines (from migration 082)
CREATE TABLE IF NOT EXISTS fleet_doctrines (
    id              SERIAL PRIMARY KEY,
    corporation_id  BIGINT NOT NULL,
    name            VARCHAR(255) NOT NULL,
    ship_type_id    INTEGER,
    fitting_json    JSONB DEFAULT '{}',
    is_active       BOOLEAN DEFAULT TRUE,
    base_payout     NUMERIC(18,2) DEFAULT 0,
    created_by      BIGINT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Discord Relay Configs (from migration 089)
CREATE TABLE IF NOT EXISTS discord_relay_configs (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    webhook_url         TEXT NOT NULL,
    filter_regions      BIGINT[] DEFAULT '{}',
    filter_alliances    BIGINT[] DEFAULT '{}',
    notify_types        TEXT[] NOT NULL DEFAULT '{timer_created,battle_started,high_value_kill}',
    ping_role_id        VARCHAR(50),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    min_isk_threshold   NUMERIC(18,2) DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fleet_ops_active ON fleet_operations(is_active);
CREATE INDEX IF NOT EXISTS idx_fleet_snapshots_op ON fleet_snapshots(operation_id);
CREATE INDEX IF NOT EXISTS idx_fleet_participation_op ON fleet_participation(operation_id);
CREATE INDEX IF NOT EXISTS idx_fleet_participation_char ON fleet_participation(character_id);
