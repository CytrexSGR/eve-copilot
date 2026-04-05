CREATE TABLE IF NOT EXISTS scheduled_operations (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(200) NOT NULL,
    description     TEXT,
    fc_character_id BIGINT NOT NULL,
    fc_name         VARCHAR(100) NOT NULL,
    doctrine_id     INT,
    doctrine_name   VARCHAR(100),
    formup_system   VARCHAR(100),
    formup_time     TIMESTAMPTZ NOT NULL,
    op_type         VARCHAR(50) DEFAULT 'fleet',
    importance      VARCHAR(20) DEFAULT 'normal',
    max_pilots      INT,
    is_cancelled    BOOLEAN DEFAULT FALSE,
    fleet_operation_id INT REFERENCES fleet_operations(id),
    created_by      BIGINT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    corporation_id  BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sched_ops_corp ON scheduled_operations(corporation_id);
CREATE INDEX IF NOT EXISTS idx_sched_ops_formup ON scheduled_operations(formup_time);
CREATE INDEX IF NOT EXISTS idx_sched_ops_active ON scheduled_operations(is_cancelled, formup_time);
