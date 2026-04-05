-- migrations/046_map_views.sql
-- Map view presets for snapshot generation

CREATE TABLE IF NOT EXISTS map_views (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    map_type VARCHAR(20) NOT NULL CHECK (map_type IN ('ectmap', 'sovmap', 'capitalmap')),
    region VARCHAR(100),
    width INT DEFAULT 1920,
    height INT DEFAULT 1080,
    params JSONB NOT NULL DEFAULT '{}',
    auto_snapshot BOOLEAN DEFAULT FALSE,
    snapshot_schedule VARCHAR(50),
    last_snapshot_at TIMESTAMP WITH TIME ZONE,
    last_snapshot_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_map_views_map_type ON map_views(map_type);
CREATE INDEX idx_map_views_auto_snapshot ON map_views(auto_snapshot) WHERE auto_snapshot = TRUE;

-- Default views
INSERT INTO map_views (name, description, map_type, region, params) VALUES
('delve-sov', 'Delve Sovereignty', 'ectmap', 'Delve', '{"colorMode": "alliance", "showBattles": true, "showKills": false}'),
('catch-battles', 'Catch Active Battles', 'ectmap', 'Catch', '{"colorMode": "alliance", "showBattles": true, "showKills": true}'),
('nullsec-adm', 'Nullsec ADM Overview', 'sovmap', NULL, '{"colorMode": "adm", "showJammers": true}'),
('capital-ops', 'Capital Operations', 'capitalmap', NULL, '{"showJammers": true, "showTimers": true}');
