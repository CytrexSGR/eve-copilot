-- PI Logistics Tables for Cross-Account Transfer Tracking
-- Migration: 038_pi_logistics.sql

-- Track scheduled transfers between characters
CREATE TABLE IF NOT EXISTS pi_transfers (
    id SERIAL PRIMARY KEY,
    plan_id INT REFERENCES pi_empire_plans(id) ON DELETE CASCADE,
    from_character_id BIGINT NOT NULL,
    to_character_id BIGINT NOT NULL,
    material_type_id INT NOT NULL,
    material_name VARCHAR(255),
    quantity INT NOT NULL,
    volume_m3 DECIMAL(20,2),
    method VARCHAR(50) DEFAULT 'contract',  -- contract, direct_trade, corp_hangar
    station_id BIGINT,
    station_name VARCHAR(255),
    frequency_hours INT DEFAULT 48,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, in_progress, completed
    last_transfer_at TIMESTAMP,
    next_transfer_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Track pickup runs
CREATE TABLE IF NOT EXISTS pi_pickup_runs (
    id SERIAL PRIMARY KEY,
    plan_id INT REFERENCES pi_empire_plans(id) ON DELETE CASCADE,
    character_id BIGINT NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    planets_visited INT DEFAULT 0,
    total_volume_m3 DECIMAL(20,2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Hub station selection per plan
CREATE TABLE IF NOT EXISTS pi_hub_stations (
    id SERIAL PRIMARY KEY,
    plan_id INT REFERENCES pi_empire_plans(id) ON DELETE CASCADE,
    station_id BIGINT NOT NULL,
    station_name VARCHAR(255),
    system_id BIGINT,
    system_name VARCHAR(255),
    security DECIMAL(3,2),
    is_primary BOOLEAN DEFAULT true,
    selected_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(plan_id, station_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pi_transfers_plan ON pi_transfers(plan_id);
CREATE INDEX IF NOT EXISTS idx_pi_transfers_status ON pi_transfers(status);
CREATE INDEX IF NOT EXISTS idx_pi_pickup_runs_plan ON pi_pickup_runs(plan_id);
CREATE INDEX IF NOT EXISTS idx_pi_hub_stations_plan ON pi_hub_stations(plan_id);
