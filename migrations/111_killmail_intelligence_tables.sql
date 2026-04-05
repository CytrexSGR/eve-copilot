-- Migration 111: Killmail Intelligence Cache Tables
-- Precomputed intelligence data for temporal doctrine tracking, hunting opportunities, and pilot risk

-- Temporal doctrine cache (precomputed per entity per time window)
CREATE TABLE doctrine_temporal_cache (
    entity_type VARCHAR(20) NOT NULL,
    entity_id BIGINT NOT NULL,
    window_type VARCHAR(20) NOT NULL,
    cluster_id INTEGER NOT NULL,
    ship_type_id INTEGER NOT NULL,
    composition JSONB NOT NULL DEFAULT '{}',
    representative_fit JSONB,
    ehp_profile JSONB,
    resist_profile JSONB,
    observation_count INTEGER NOT NULL DEFAULT 0,
    confidence_level VARCHAR(20) NOT NULL DEFAULT 'ANOMALY',
    first_seen TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (entity_type, entity_id, window_type, cluster_id)
);

CREATE INDEX idx_dtc_entity ON doctrine_temporal_cache(entity_type, entity_id);
CREATE INDEX idx_dtc_confidence ON doctrine_temporal_cache(confidence_level);

-- Hunting opportunity scores (precomputed per system)
CREATE TABLE hunting_opportunity_scores (
    solar_system_id INTEGER PRIMARY KEY,
    region_id INTEGER NOT NULL,
    score FLOAT NOT NULL DEFAULT 0,
    activity_score FLOAT,
    vulnerability_score FLOAT,
    value_score FLOAT,
    risk_score FLOAT,
    adm_military FLOAT,
    adm_industry FLOAT,
    npc_kills_per_day FLOAT,
    player_deaths_per_week FLOAT,
    peak_hours JSONB,
    owner_alliance_id BIGINT,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_hos_score ON hunting_opportunity_scores(score DESC);
CREATE INDEX idx_hos_region ON hunting_opportunity_scores(region_id);

-- Pilot risk scores (precomputed per pilot per corp)
CREATE TABLE pilot_risk_scores (
    character_id BIGINT NOT NULL,
    corporation_id BIGINT NOT NULL,
    awox_score FLOAT DEFAULT 0,
    awox_signals JSONB DEFAULT '{}',
    performance_category VARCHAR(20) DEFAULT 'NORMAL',
    isk_efficiency FLOAT DEFAULT 0,
    contribution_score FLOAT DEFAULT 0,
    fleet_role VARCHAR(20),
    improvement_trend FLOAT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (character_id, corporation_id)
);

CREATE INDEX idx_prs_corp ON pilot_risk_scores(corporation_id);
CREATE INDEX idx_prs_awox ON pilot_risk_scores(awox_score DESC);
