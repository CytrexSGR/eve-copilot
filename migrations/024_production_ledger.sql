-- migrations/024_production_ledger.sql
-- Production Ledger for multi-stage project tracking

-- Main ledger (project)
CREATE TABLE IF NOT EXISTS production_ledger (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    target_type_id INTEGER,
    target_type_name VARCHAR(255),
    target_quantity INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'planning',
    tax_profile_id INTEGER REFERENCES tax_profiles(id),
    facility_id INTEGER REFERENCES facility_profiles(id),
    total_material_cost BIGINT DEFAULT 0,
    total_job_cost BIGINT DEFAULT 0,
    total_cost BIGINT DEFAULT 0,
    expected_revenue BIGINT DEFAULT 0,
    expected_profit BIGINT DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Production stages
CREATE TABLE IF NOT EXISTS ledger_stages (
    id SERIAL PRIMARY KEY,
    ledger_id INTEGER REFERENCES production_ledger(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    stage_order INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    material_cost BIGINT DEFAULT 0,
    job_cost BIGINT DEFAULT 0,
    completed_at TIMESTAMP,
    UNIQUE(ledger_id, stage_order)
);

-- Jobs per stage
CREATE TABLE IF NOT EXISTS ledger_jobs (
    id SERIAL PRIMARY KEY,
    ledger_id INTEGER REFERENCES production_ledger(id) ON DELETE CASCADE,
    stage_id INTEGER REFERENCES ledger_stages(id) ON DELETE CASCADE,
    type_id INTEGER NOT NULL,
    type_name VARCHAR(255),
    blueprint_type_id INTEGER,
    quantity INTEGER NOT NULL,
    runs INTEGER NOT NULL,
    me_level INTEGER DEFAULT 0,
    te_level INTEGER DEFAULT 0,
    facility_id INTEGER REFERENCES facility_profiles(id),
    material_cost BIGINT DEFAULT 0,
    job_cost BIGINT DEFAULT 0,
    production_time INTEGER,
    status VARCHAR(20) DEFAULT 'planned',
    esi_job_id BIGINT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Aggregated materials
CREATE TABLE IF NOT EXISTS ledger_materials (
    id SERIAL PRIMARY KEY,
    ledger_id INTEGER REFERENCES production_ledger(id) ON DELETE CASCADE,
    type_id INTEGER NOT NULL,
    type_name VARCHAR(255),
    total_needed BIGINT NOT NULL,
    total_acquired BIGINT DEFAULT 0,
    estimated_cost BIGINT DEFAULT 0,
    source VARCHAR(20) DEFAULT 'buy',
    UNIQUE(ledger_id, type_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ledger_character ON production_ledger(character_id);
CREATE INDEX IF NOT EXISTS idx_ledger_status ON production_ledger(status);
CREATE INDEX IF NOT EXISTS idx_ledger_jobs_stage ON ledger_jobs(stage_id);
CREATE INDEX IF NOT EXISTS idx_ledger_materials_ledger ON ledger_materials(ledger_id);

COMMENT ON TABLE production_ledger IS 'Multi-stage production projects (e.g., Capital Ships)';
COMMENT ON TABLE ledger_stages IS 'Production stages within a ledger (e.g., Components, Assembly)';
COMMENT ON TABLE ledger_jobs IS 'Individual manufacturing jobs within stages';
COMMENT ON TABLE ledger_materials IS 'Aggregated material requirements across all stages';
