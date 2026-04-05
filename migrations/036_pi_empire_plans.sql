-- Migration: 036_pi_empire_plans.sql
-- PI Empire Plans - Multi-character coordinated production plans

-- Empire plan table
CREATE TABLE IF NOT EXISTS pi_empire_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    target_product_id INT NOT NULL,
    target_product_name VARCHAR(255),
    home_system_id INT,
    home_system_name VARCHAR(255),
    total_planets INT NOT NULL DEFAULT 18,
    extraction_planets INT NOT NULL DEFAULT 12,
    factory_planets INT NOT NULL DEFAULT 6,
    poco_tax_rate DECIMAL(5,4) NOT NULL DEFAULT 0.10,
    status VARCHAR(50) NOT NULL DEFAULT 'planning',
    estimated_monthly_output INT,
    estimated_monthly_profit DECIMAL(20,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT check_planet_total CHECK (extraction_planets + factory_planets <= total_planets),
    CONSTRAINT check_status CHECK (status IN ('planning', 'active', 'paused', 'completed'))
);

-- Character assignments within an empire plan
CREATE TABLE IF NOT EXISTS pi_empire_plan_assignments (
    id SERIAL PRIMARY KEY,
    plan_id INT NOT NULL REFERENCES pi_empire_plans(id) ON DELETE CASCADE,
    character_id BIGINT NOT NULL,
    character_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'extractor',
    planets JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT check_role CHECK (role IN ('extractor', 'factory', 'hybrid'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_empire_plans_status ON pi_empire_plans(status);
CREATE INDEX IF NOT EXISTS idx_empire_plan_assignments_plan ON pi_empire_plan_assignments(plan_id);
CREATE INDEX IF NOT EXISTS idx_empire_plan_assignments_char ON pi_empire_plan_assignments(character_id);

-- Comments
COMMENT ON TABLE pi_empire_plans IS 'Multi-character PI production plans for P4 products';
COMMENT ON TABLE pi_empire_plan_assignments IS 'Character role assignments within empire plans';
