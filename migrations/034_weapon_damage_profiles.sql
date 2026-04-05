-- Weapon damage type profiles for accurate damage classification
-- Migration: 034_weapon_damage_profiles.sql
-- Created: 2026-02-01

CREATE TABLE IF NOT EXISTS weapon_damage_profiles (
    weapon_type_id INTEGER PRIMARY KEY,
    weapon_name TEXT NOT NULL,
    weapon_group TEXT NOT NULL,
    primary_damage_type VARCHAR(20) NOT NULL,  -- EM, Thermal, Kinetic, Explosive, Mixed
    em_pct DECIMAL(5,2) DEFAULT 0.0,
    thermal_pct DECIMAL(5,2) DEFAULT 0.0,
    kinetic_pct DECIMAL(5,2) DEFAULT 0.0,
    explosive_pct DECIMAL(5,2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_weapon_damage_weapon_type
ON weapon_damage_profiles(weapon_type_id);

CREATE INDEX IF NOT EXISTS idx_weapon_damage_primary_type
ON weapon_damage_profiles(primary_damage_type);

-- Ensure damage percentages sum to ~100%
CREATE OR REPLACE FUNCTION check_damage_sum() RETURNS TRIGGER AS $$
BEGIN
    IF (NEW.em_pct + NEW.thermal_pct + NEW.kinetic_pct + NEW.explosive_pct) < 90.0 OR
       (NEW.em_pct + NEW.thermal_pct + NEW.kinetic_pct + NEW.explosive_pct) > 110.0 THEN
        RAISE WARNING 'Damage percentages for weapon_type_id % sum to %%, expected ~100%%',
            NEW.weapon_type_id,
            (NEW.em_pct + NEW.thermal_pct + NEW.kinetic_pct + NEW.explosive_pct);
    END IF
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_damage_sum_trigger
BEFORE INSERT OR UPDATE ON weapon_damage_profiles
FOR EACH ROW EXECUTE FUNCTION check_damage_sum();

COMMENT ON TABLE weapon_damage_profiles IS 'Weapon damage type profiles for accurate damage classification in kill analysis';
COMMENT ON COLUMN weapon_damage_profiles.primary_damage_type IS 'Primary damage type: EM, Thermal, Kinetic, Explosive, or Mixed';
COMMENT ON COLUMN weapon_damage_profiles.em_pct IS 'EM damage percentage (0-100)';
COMMENT ON COLUMN weapon_damage_profiles.thermal_pct IS 'Thermal damage percentage (0-100)';
COMMENT ON COLUMN weapon_damage_profiles.kinetic_pct IS 'Kinetic damage percentage (0-100)';
COMMENT ON COLUMN weapon_damage_profiles.explosive_pct IS 'Explosive damage percentage (0-100)';
