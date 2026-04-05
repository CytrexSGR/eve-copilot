-- migrations/030_skill_plans.sql
-- Phase 5b: Skill Planner tables

-- Skill Plans (belongs to character, usable by all)
CREATE TABLE IF NOT EXISTS skill_plans (
    id SERIAL PRIMARY KEY,
    character_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Skills in plan
CREATE TABLE IF NOT EXISTS skill_plan_items (
    id SERIAL PRIMARY KEY,
    plan_id INT REFERENCES skill_plans(id) ON DELETE CASCADE,
    skill_type_id INT NOT NULL,
    target_level INT NOT NULL CHECK (target_level BETWEEN 1 AND 5),
    sort_order INT NOT NULL,
    notes TEXT,
    UNIQUE(plan_id, skill_type_id, target_level)
);

-- Remap points in plan
CREATE TABLE IF NOT EXISTS skill_plan_remaps (
    id SERIAL PRIMARY KEY,
    plan_id INT REFERENCES skill_plans(id) ON DELETE CASCADE,
    after_item_id INT REFERENCES skill_plan_items(id) ON DELETE SET NULL,
    perception INT NOT NULL DEFAULT 20 CHECK (perception BETWEEN 17 AND 27),
    memory INT NOT NULL DEFAULT 20 CHECK (memory BETWEEN 17 AND 27),
    willpower INT NOT NULL DEFAULT 20 CHECK (willpower BETWEEN 17 AND 27),
    intelligence INT NOT NULL DEFAULT 20 CHECK (intelligence BETWEEN 17 AND 27),
    charisma INT NOT NULL DEFAULT 19 CHECK (charisma BETWEEN 17 AND 27),
    CHECK (perception + memory + willpower + intelligence + charisma = 99)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_skill_plans_character ON skill_plans(character_id);
CREATE INDEX IF NOT EXISTS idx_skill_plan_items_plan ON skill_plan_items(plan_id);
CREATE INDEX IF NOT EXISTS idx_skill_plan_items_order ON skill_plan_items(plan_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_skill_plan_remaps_plan ON skill_plan_remaps(plan_id);
