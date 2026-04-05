-- migrations/022_system_cost_index.sql
-- System Cost Index Cache from ESI

CREATE TABLE IF NOT EXISTS system_cost_index (
    system_id BIGINT PRIMARY KEY,
    system_name VARCHAR(100),
    manufacturing_index DECIMAL(8,6) DEFAULT 0,  -- 0.000000 - 0.500000
    reaction_index DECIMAL(8,6) DEFAULT 0,
    copying_index DECIMAL(8,6) DEFAULT 0,
    invention_index DECIMAL(8,6) DEFAULT 0,
    research_te_index DECIMAL(8,6) DEFAULT 0,
    research_me_index DECIMAL(8,6) DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE system_cost_index IS 'Cached System Cost Index from ESI /industry/systems/';
