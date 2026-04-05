-- migrations/027_pi_optimizer.sql
-- PI Optimizer tables for character skills, system planets, and projects

-- Character PI skills cache (from ESI)
CREATE TABLE IF NOT EXISTS pi_character_skills (
    character_id BIGINT PRIMARY KEY,
    interplanetary_consolidation INT DEFAULT 0,  -- Skill ID 2495
    command_center_upgrades INT DEFAULT 0,       -- Skill ID 2505
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Preloaded system planets (Isikemi default + configurable)
CREATE TABLE IF NOT EXISTS pi_system_planets (
    planet_id BIGINT PRIMARY KEY,
    system_id BIGINT NOT NULL,
    system_name VARCHAR(100),
    planet_type VARCHAR(20) NOT NULL,
    planet_index INT,
    UNIQUE(system_id, planet_index)
);

-- Insert Isikemi planets (validated data)
INSERT INTO pi_system_planets (planet_id, system_id, system_name, planet_type, planet_index)
VALUES
    (40086933, 30002811, 'Isikemi', 'plasma', 1),
    (40086935, 30002811, 'Isikemi', 'temperate', 2),
    (40086937, 30002811, 'Isikemi', 'gas', 3),
    (40086940, 30002811, 'Isikemi', 'gas', 4),
    (40086943, 30002811, 'Isikemi', 'temperate', 5),
    (40086945, 30002811, 'Isikemi', 'temperate', 6),
    (40086947, 30002811, 'Isikemi', 'gas', 7)
ON CONFLICT (planet_id) DO NOTHING;

-- PI Projects
CREATE TABLE IF NOT EXISTS pi_projects (
    project_id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    name VARCHAR(200) NOT NULL,
    strategy VARCHAR(20) NOT NULL CHECK (strategy IN ('market_driven', 'vertical')),
    target_product_type_id INT,
    target_profit_per_hour DECIMAL(20,2),
    status VARCHAR(20) DEFAULT 'planning' CHECK (status IN ('planning', 'active', 'paused', 'completed')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Project colony assignments
CREATE TABLE IF NOT EXISTS pi_project_colonies (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES pi_projects(project_id) ON DELETE CASCADE,
    planet_id BIGINT NOT NULL,
    role VARCHAR(50),
    expected_output_type_id INT,
    expected_output_per_hour DECIMAL(20,2),
    actual_output_per_hour DECIMAL(20,2),
    last_sync TIMESTAMP,
    UNIQUE(project_id, planet_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pi_projects_character ON pi_projects(character_id);
CREATE INDEX IF NOT EXISTS idx_pi_projects_status ON pi_projects(status);
CREATE INDEX IF NOT EXISTS idx_pi_project_colonies_project ON pi_project_colonies(project_id);
CREATE INDEX IF NOT EXISTS idx_pi_system_planets_system ON pi_system_planets(system_id);

-- Comments
COMMENT ON TABLE pi_character_skills IS 'Character PI skill levels from ESI (cached)';
COMMENT ON TABLE pi_system_planets IS 'Planets in systems configured for PI optimization';
COMMENT ON TABLE pi_projects IS 'PI optimization projects for tracking colony setups';
COMMENT ON TABLE pi_project_colonies IS 'Colony assignments within PI projects';
COMMENT ON COLUMN pi_character_skills.interplanetary_consolidation IS 'Skill ID 2495: max planets = 1 + level';
COMMENT ON COLUMN pi_character_skills.command_center_upgrades IS 'Skill ID 2505: CC tier = level';
