-- migrations/021_facility_profiles.sql
-- Facility Profiles for Structure Bonuses

CREATE TABLE IF NOT EXISTS facility_profiles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    system_id BIGINT NOT NULL,
    structure_type VARCHAR(50) DEFAULT 'station',  -- station, engineering_complex, refinery
    me_bonus DECIMAL(4,2) DEFAULT 0,      -- % Material Reduction (0-5)
    te_bonus DECIMAL(4,2) DEFAULT 0,      -- % Time Reduction (0-25)
    cost_bonus DECIMAL(4,2) DEFAULT 0,    -- % Job Cost Reduction (0-5)
    facility_tax DECIMAL(5,2) DEFAULT 0,  -- % Facility Tax (0-50)
    -- Reaction-specific (for Phase 4)
    reaction_me_bonus DECIMAL(4,2) DEFAULT 0,
    reaction_te_bonus DECIMAL(4,2) DEFAULT 0,
    fuel_bonus DECIMAL(4,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_facility_profiles_system ON facility_profiles(system_id);

-- Insert NPC Station default
INSERT INTO facility_profiles (name, system_id, structure_type, facility_tax)
VALUES ('NPC Station (Default)', 30000142, 'station', 10.0)  -- Jita
ON CONFLICT DO NOTHING;

COMMENT ON TABLE facility_profiles IS 'Player-defined facility profiles with structure bonuses';
