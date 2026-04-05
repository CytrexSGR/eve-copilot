-- =====================================================
-- SKILL ANALYSIS LLM INFRASTRUCTURE
-- Migration: 010_skill_analysis_llm.sql
-- Created: 2026-01-12
-- Purpose: Tables and views for recurring LLM skill analysis
-- =====================================================

-- =====================================================
-- 1. SNAPSHOT TABLES (Track skill progress over time)
-- =====================================================

-- Skill snapshots for historical tracking
DROP TABLE IF EXISTS character_skill_snapshots CASCADE;
CREATE TABLE character_skill_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    total_sp BIGINT NOT NULL,
    unallocated_sp INTEGER DEFAULT 0,
    skill_count INTEGER NOT NULL,
    level_5_count INTEGER DEFAULT 0,
    level_4_count INTEGER DEFAULT 0,
    -- Top categories as JSON for flexibility
    top_categories JSONB,
    -- Skill details as JSON (compressed storage)
    skills_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(snapshot_date, character_id)
);

CREATE INDEX idx_skill_snapshots_char_date ON character_skill_snapshots(character_id, snapshot_date DESC);
CREATE INDEX idx_skill_snapshots_date ON character_skill_snapshots(snapshot_date DESC);

-- SP progress tracking (daily deltas)
DROP TABLE IF EXISTS character_sp_progress CASCADE;
CREATE TABLE character_sp_progress (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    sp_gained BIGINT DEFAULT 0,
    skills_gained INTEGER DEFAULT 0,
    level_5_gained INTEGER DEFAULT 0,
    training_time_hours NUMERIC(10,2),
    active_queue_items INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, character_id)
);

CREATE INDEX idx_sp_progress_char_date ON character_sp_progress(character_id, date DESC);

-- =====================================================
-- 2. LLM ANALYSIS TABLES
-- =====================================================

-- Analysis report types
DROP TYPE IF EXISTS analysis_type CASCADE;
CREATE TYPE analysis_type AS ENUM (
    'individual_assessment',    -- Single character analysis
    'team_composition',         -- Team synergy analysis
    'training_priorities',      -- What to train next
    'role_optimization',        -- Role assignment optimization
    'gap_analysis',            -- Skills the team is missing
    'weekly_summary',          -- Weekly progress summary
    'monthly_review'           -- Monthly comprehensive review
);

-- LLM Analysis Reports
DROP TABLE IF EXISTS skill_analysis_reports CASCADE;
CREATE TABLE skill_analysis_reports (
    id SERIAL PRIMARY KEY,
    report_type analysis_type NOT NULL,
    report_date TIMESTAMP NOT NULL DEFAULT NOW(),
    -- Which characters are covered (NULL = all)
    character_ids INTEGER[],
    -- Input data snapshot (what was sent to LLM)
    input_data JSONB NOT NULL,
    -- LLM response
    analysis_text TEXT NOT NULL,
    -- Structured recommendations extracted from analysis
    recommendations JSONB,
    -- Key metrics at time of analysis
    metrics JSONB,
    -- LLM metadata
    model_used VARCHAR(64),
    tokens_used INTEGER,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analysis_reports_type ON skill_analysis_reports(report_type, report_date DESC);
CREATE INDEX idx_analysis_reports_chars ON skill_analysis_reports USING GIN(character_ids);

-- Training recommendations (extracted from LLM analysis)
DROP TABLE IF EXISTS skill_training_recommendations CASCADE;
CREATE TABLE skill_training_recommendations (
    id SERIAL PRIMARY KEY,
    report_id INTEGER REFERENCES skill_analysis_reports(id) ON DELETE CASCADE,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL,
    skill_name VARCHAR(128) NOT NULL,
    current_level INTEGER NOT NULL,
    target_level INTEGER NOT NULL,
    priority INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 5), -- 1=highest
    reason TEXT,
    estimated_training_days NUMERIC(10,2),
    category VARCHAR(64),
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_training_recs_char ON skill_training_recommendations(character_id, priority);
CREATE INDEX idx_training_recs_pending ON skill_training_recommendations(character_id) WHERE NOT is_completed;

-- =====================================================
-- 3. TEAM ANALYSIS TABLES
-- =====================================================

-- Team role assignments (LLM recommended)
DROP TABLE IF EXISTS team_role_assignments CASCADE;
CREATE TABLE team_role_assignments (
    id SERIAL PRIMARY KEY,
    report_id INTEGER REFERENCES skill_analysis_reports(id) ON DELETE CASCADE,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    primary_role VARCHAR(64) NOT NULL,
    secondary_role VARCHAR(64),
    role_fit_score NUMERIC(3,2) CHECK (role_fit_score BETWEEN 0 AND 1),
    strengths TEXT[],
    weaknesses TEXT[],
    synergies JSONB, -- Which other chars they work well with
    recommended_ships TEXT[],
    recommended_activities TEXT[],
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_role_assignments_char ON team_role_assignments(character_id);

-- Team composition scenarios
DROP TABLE IF EXISTS team_compositions CASCADE;
CREATE TABLE team_compositions (
    id SERIAL PRIMARY KEY,
    report_id INTEGER REFERENCES skill_analysis_reports(id) ON DELETE CASCADE,
    scenario_name VARCHAR(128) NOT NULL,
    scenario_type VARCHAR(64), -- 'mining_fleet', 'mission_team', 'pvp_gang', etc.
    character_roles JSONB NOT NULL, -- {char_id: role}
    effectiveness_score NUMERIC(3,2),
    description TEXT,
    requirements TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 4. LLM-OPTIMIZED VIEWS FOR DATA EXTRACTION
-- =====================================================

-- View: Character data optimized for LLM input
DROP VIEW IF EXISTS v_llm_character_profile CASCADE;
CREATE VIEW v_llm_character_profile AS
SELECT
    c.character_id,
    c.character_name,
    cs.total_sp,
    cs.unallocated_sp,
    (SELECT COUNT(*) FROM character_skills WHERE character_id = c.character_id) as skill_count,
    (SELECT COUNT(*) FROM character_skills WHERE character_id = c.character_id AND active_skill_level = 5) as level_5_count,
    (SELECT COUNT(*) FROM character_skills WHERE character_id = c.character_id AND active_skill_level = 4) as level_4_count,
    -- Top 5 categories as JSON
    (SELECT jsonb_agg(jsonb_build_object(
        'category', skill_category,
        'sp', category_sp,
        'skills', skills_trained,
        'avg_level', avg_level,
        'level_5', level_5_count
    ) ORDER BY sp_rank)
    FROM v_character_specializations
    WHERE character_name = c.character_name AND sp_rank <= 5) as top_categories,
    -- Current training queue
    (SELECT jsonb_agg(jsonb_build_object(
        'skill', skill_name,
        'to_level', finished_level,
        'finish_date', finish_date
    ) ORDER BY queue_position)
    FROM character_skill_queue
    WHERE character_id = c.character_id) as skill_queue,
    -- Role recommendation if exists
    r.primary_role,
    r.secondary_role,
    r.recommended_ships,
    r.best_for
FROM characters c
LEFT JOIN (
    SELECT character_id,
           SUM(skillpoints_in_skill) as total_sp,
           0 as unallocated_sp
    FROM character_skills
    GROUP BY character_id
) cs ON c.character_id = cs.character_id
LEFT JOIN character_role_recommendations r ON c.character_id = r.character_id;

-- View: Team overview for LLM
DROP VIEW IF EXISTS v_llm_team_overview CASCADE;
CREATE VIEW v_llm_team_overview AS
SELECT
    jsonb_build_object(
        'team_total_sp', SUM(total_sp),
        'character_count', COUNT(*),
        'avg_sp_per_char', ROUND(AVG(total_sp)),
        'total_skills', SUM(skill_count),
        'total_level_5', SUM(level_5_count)
    ) as team_stats,
    jsonb_agg(jsonb_build_object(
        'name', character_name,
        'sp', total_sp,
        'skills', skill_count,
        'level_5', level_5_count,
        'primary_role', primary_role,
        'secondary_role', secondary_role,
        'top_categories', top_categories
    ) ORDER BY total_sp DESC) as characters
FROM v_llm_character_profile;

-- View: Skill gaps for LLM
DROP VIEW IF EXISTS v_llm_skill_gaps CASCADE;
CREATE VIEW v_llm_skill_gaps AS
SELECT
    skill_category,
    COUNT(*) as gap_count,
    jsonb_agg(jsonb_build_object(
        'skill', skill_name,
        'best_level', best_level,
        'skill_id', skill_id
    ) ORDER BY skill_name) as missing_skills
FROM v_team_skill_gaps
WHERE skill_category IS NOT NULL
GROUP BY skill_category
ORDER BY gap_count DESC;

-- View: Skill comparison matrix for LLM
DROP VIEW IF EXISTS v_llm_skill_comparison CASCADE;
CREATE VIEW v_llm_skill_comparison AS
SELECT
    skill_category,
    jsonb_agg(jsonb_build_object(
        'skill', skill_name,
        'artallus', COALESCE(artallus, 0),
        'cytrex', COALESCE(cytrex, 0),
        'cytricia', COALESCE(cytricia, 0)
    ) ORDER BY skill_name) as skills
FROM v_skill_matrix_level5
WHERE skill_category IS NOT NULL
GROUP BY skill_category
ORDER BY skill_category;

-- View: Recent SP progress for LLM
DROP VIEW IF EXISTS v_llm_recent_progress CASCADE;
CREATE VIEW v_llm_recent_progress AS
SELECT
    c.character_name,
    COALESCE(
        (SELECT jsonb_agg(jsonb_build_object(
            'date', p.date,
            'sp_gained', p.sp_gained,
            'skills_gained', p.skills_gained
        ) ORDER BY p.date DESC)
        FROM character_sp_progress p
        WHERE p.character_id = c.character_id
        AND p.date >= CURRENT_DATE - INTERVAL '30 days'),
        '[]'::jsonb
    ) as progress_30d
FROM characters c;

-- =====================================================
-- 5. FUNCTIONS FOR SNAPSHOT CREATION
-- =====================================================

-- Function: Create daily skill snapshot
CREATE OR REPLACE FUNCTION create_skill_snapshot(p_character_id INTEGER, p_date DATE DEFAULT CURRENT_DATE)
RETURNS INTEGER AS $$
DECLARE
    v_snapshot_id INTEGER;
    v_total_sp BIGINT;
    v_skill_count INTEGER;
    v_level_5_count INTEGER;
    v_level_4_count INTEGER;
    v_top_categories JSONB;
    v_skills_json JSONB;
BEGIN
    -- Get aggregated stats
    SELECT
        COALESCE(SUM(skillpoints_in_skill), 0),
        COUNT(*),
        COUNT(*) FILTER (WHERE active_skill_level = 5),
        COUNT(*) FILTER (WHERE active_skill_level = 4)
    INTO v_total_sp, v_skill_count, v_level_5_count, v_level_4_count
    FROM character_skills
    WHERE character_id = p_character_id;

    -- Get top categories
    SELECT jsonb_agg(jsonb_build_object(
        'category', skill_category,
        'sp', category_sp,
        'skills', skills_trained
    ) ORDER BY category_sp DESC)
    INTO v_top_categories
    FROM (
        SELECT skill_category, category_sp, skills_trained
        FROM v_character_skill_categories
        WHERE character_id = p_character_id
        ORDER BY category_sp DESC
        LIMIT 10
    ) t;

    -- Get skills as JSON
    SELECT jsonb_agg(jsonb_build_object(
        'id', skill_id,
        'name', skill_name,
        'level', active_skill_level,
        'sp', skillpoints_in_skill
    ))
    INTO v_skills_json
    FROM character_skills
    WHERE character_id = p_character_id;

    -- Insert or update snapshot
    INSERT INTO character_skill_snapshots (
        snapshot_date, character_id, total_sp, skill_count,
        level_5_count, level_4_count, top_categories, skills_json
    ) VALUES (
        p_date, p_character_id, v_total_sp, v_skill_count,
        v_level_5_count, v_level_4_count, v_top_categories, v_skills_json
    )
    ON CONFLICT (snapshot_date, character_id) DO UPDATE SET
        total_sp = EXCLUDED.total_sp,
        skill_count = EXCLUDED.skill_count,
        level_5_count = EXCLUDED.level_5_count,
        level_4_count = EXCLUDED.level_4_count,
        top_categories = EXCLUDED.top_categories,
        skills_json = EXCLUDED.skills_json,
        created_at = NOW()
    RETURNING id INTO v_snapshot_id;

    RETURN v_snapshot_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Calculate SP progress
CREATE OR REPLACE FUNCTION calculate_sp_progress(p_character_id INTEGER, p_date DATE DEFAULT CURRENT_DATE)
RETURNS INTEGER AS $$
DECLARE
    v_progress_id INTEGER;
    v_current_sp BIGINT;
    v_previous_sp BIGINT;
    v_current_skills INTEGER;
    v_previous_skills INTEGER;
    v_current_l5 INTEGER;
    v_previous_l5 INTEGER;
BEGIN
    -- Get current stats
    SELECT total_sp, skill_count, level_5_count
    INTO v_current_sp, v_current_skills, v_current_l5
    FROM character_skill_snapshots
    WHERE character_id = p_character_id AND snapshot_date = p_date;

    -- Get previous day stats
    SELECT total_sp, skill_count, level_5_count
    INTO v_previous_sp, v_previous_skills, v_previous_l5
    FROM character_skill_snapshots
    WHERE character_id = p_character_id AND snapshot_date = p_date - 1;

    -- Calculate and store progress
    INSERT INTO character_sp_progress (
        date, character_id, sp_gained, skills_gained, level_5_gained
    ) VALUES (
        p_date,
        p_character_id,
        COALESCE(v_current_sp - v_previous_sp, 0),
        COALESCE(v_current_skills - v_previous_skills, 0),
        COALESCE(v_current_l5 - v_previous_l5, 0)
    )
    ON CONFLICT (date, character_id) DO UPDATE SET
        sp_gained = EXCLUDED.sp_gained,
        skills_gained = EXCLUDED.skills_gained,
        level_5_gained = EXCLUDED.level_5_gained,
        created_at = NOW()
    RETURNING id INTO v_progress_id;

    RETURN v_progress_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Create snapshots for all characters
CREATE OR REPLACE FUNCTION create_all_snapshots(p_date DATE DEFAULT CURRENT_DATE)
RETURNS TABLE(character_id INTEGER, snapshot_id INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT c.character_id, create_skill_snapshot(c.character_id, p_date)
    FROM characters c;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 6. COMMENTS
-- =====================================================

COMMENT ON TABLE character_skill_snapshots IS 'Daily snapshots of character skills for historical tracking';
COMMENT ON TABLE character_sp_progress IS 'Daily SP gain tracking';
COMMENT ON TABLE skill_analysis_reports IS 'LLM-generated analysis reports';
COMMENT ON TABLE skill_training_recommendations IS 'Training recommendations extracted from LLM analysis';
COMMENT ON TABLE team_role_assignments IS 'LLM-recommended role assignments';
COMMENT ON TABLE team_compositions IS 'Team composition scenarios for different activities';

COMMENT ON VIEW v_llm_character_profile IS 'Character data formatted for LLM input';
COMMENT ON VIEW v_llm_team_overview IS 'Team overview formatted for LLM input';
COMMENT ON VIEW v_llm_skill_gaps IS 'Skill gaps formatted for LLM input';
COMMENT ON VIEW v_llm_skill_comparison IS 'Skill comparison matrix formatted for LLM input';

COMMENT ON FUNCTION create_skill_snapshot IS 'Creates a daily skill snapshot for a character';
COMMENT ON FUNCTION calculate_sp_progress IS 'Calculates SP progress vs previous day';
COMMENT ON FUNCTION create_all_snapshots IS 'Creates snapshots for all characters';
