-- =====================================================
-- CHARACTER SKILL ANALYSIS VIEWS
-- Created: 2026-01-12
-- Purpose: Analyze character skills for optimal deployment
-- =====================================================

-- 1. View: Skills with category information
DROP VIEW IF EXISTS v_character_skills_detailed CASCADE;
CREATE VIEW v_character_skills_detailed AS
SELECT
    cs.character_id,
    c.character_name,
    cs.skill_id,
    cs.skill_name,
    cs.active_skill_level,
    cs.trained_skill_level,
    cs.skillpoints_in_skill,
    g."groupName" as skill_category,
    g."groupID" as category_id
FROM character_skills cs
JOIN characters c ON cs.character_id = c.character_id
LEFT JOIN "invTypes" t ON cs.skill_id = t."typeID"
LEFT JOIN "invGroups" g ON t."groupID" = g."groupID";

-- 2. View: Skills per category per character
DROP VIEW IF EXISTS v_character_skill_categories CASCADE;
CREATE VIEW v_character_skill_categories AS
SELECT
    character_id,
    character_name,
    skill_category,
    COUNT(*) as skills_trained,
    SUM(skillpoints_in_skill) as category_sp,
    ROUND(AVG(active_skill_level)::numeric, 1) as avg_level,
    MAX(active_skill_level) as max_level,
    SUM(CASE WHEN active_skill_level = 5 THEN 1 ELSE 0 END) as level_5_count
FROM v_character_skills_detailed
WHERE skill_category IS NOT NULL
GROUP BY character_id, character_name, skill_category;

-- 3. View: Character specialization summary
DROP VIEW IF EXISTS v_character_specializations CASCADE;
CREATE VIEW v_character_specializations AS
SELECT
    character_name,
    skill_category,
    skills_trained,
    category_sp,
    avg_level,
    level_5_count,
    RANK() OVER (PARTITION BY character_name ORDER BY category_sp DESC) as sp_rank
FROM v_character_skill_categories
ORDER BY character_name, sp_rank;

-- 4. View: Skill comparison matrix (who has what at level 4+)
DROP VIEW IF EXISTS v_skill_matrix_level5 CASCADE;
CREATE VIEW v_skill_matrix_level5 AS
SELECT
    skill_name,
    skill_category,
    MAX(CASE WHEN character_name = 'Artallus' THEN active_skill_level END) as artallus,
    MAX(CASE WHEN character_name = 'Cytrex' THEN active_skill_level END) as cytrex,
    MAX(CASE WHEN character_name = 'Cytricia' THEN active_skill_level END) as cytricia
FROM v_character_skills_detailed
GROUP BY skill_name, skill_category, skill_id
HAVING MAX(active_skill_level) >= 4
ORDER BY skill_category, skill_name;

-- 5. View: Unique skills per character (skills only one has at high level)
DROP VIEW IF EXISTS v_unique_capabilities CASCADE;
CREATE VIEW v_unique_capabilities AS
WITH skill_owners AS (
    SELECT
        skill_id,
        skill_name,
        skill_category,
        character_name,
        active_skill_level,
        COUNT(*) OVER (PARTITION BY skill_id) as owners_count
    FROM v_character_skills_detailed
    WHERE active_skill_level >= 4
)
SELECT
    character_name,
    skill_name,
    skill_category,
    active_skill_level
FROM skill_owners
WHERE owners_count = 1
ORDER BY character_name, skill_category, skill_name;

-- 6. View: Team gaps (skills no one has at level 4+)
DROP VIEW IF EXISTS v_team_skill_gaps CASCADE;
CREATE VIEW v_team_skill_gaps AS
SELECT
    t."typeID" as skill_id,
    t."typeName" as skill_name,
    g."groupName" as skill_category,
    COALESCE(MAX(cs.active_skill_level), 0) as best_level
FROM "invTypes" t
JOIN "invGroups" g ON t."groupID" = g."groupID"
LEFT JOIN character_skills cs ON t."typeID" = cs.skill_id
WHERE g."categoryID" = 16
  AND g."groupName" NOT IN ('Fake Skills')
  AND t.published = true
GROUP BY t."typeID", t."typeName", g."groupName"
HAVING COALESCE(MAX(cs.active_skill_level), 0) < 4
ORDER BY g."groupName", t."typeName";

-- 7. View: Production & Industry capabilities
DROP VIEW IF EXISTS v_production_capabilities CASCADE;
CREATE VIEW v_production_capabilities AS
SELECT
    character_name,
    skill_name,
    active_skill_level,
    CASE
        WHEN skill_name LIKE '%Efficiency%' THEN 'Effizienz'
        WHEN skill_name LIKE '%Science%' OR skill_name LIKE '%Research%' THEN 'Forschung'
        WHEN skill_name LIKE '%Processing%' OR skill_name LIKE '%Reprocessing%' THEN 'Verarbeitung'
        WHEN skill_name LIKE '%Production%' OR skill_name LIKE '%Manufacturing%' THEN 'Produktion'
        WHEN skill_name LIKE '%Blueprint%' OR skill_name LIKE '%Copying%' THEN 'Blueprints'
        WHEN skill_name LIKE '%Invention%' THEN 'Invention'
        ELSE 'Sonstiges'
    END as subcategory
FROM v_character_skills_detailed
WHERE skill_category IN ('Production', 'Science', 'Resource Processing')
ORDER BY character_name, subcategory, active_skill_level DESC;

-- 8. View: Combat capabilities
DROP VIEW IF EXISTS v_combat_capabilities CASCADE;
CREATE VIEW v_combat_capabilities AS
SELECT
    character_name,
    skill_category,
    COUNT(*) as skills,
    SUM(skillpoints_in_skill) as sp,
    ROUND(AVG(active_skill_level)::numeric, 1) as avg_level,
    SUM(CASE WHEN active_skill_level = 5 THEN 1 ELSE 0 END) as lvl5_count
FROM v_character_skills_detailed
WHERE skill_category IN ('Gunnery', 'Missiles', 'Drones', 'Spaceship Command',
                          'Shields', 'Armor', 'Navigation', 'Electronic Systems',
                          'Engineering', 'Targeting')
GROUP BY character_name, skill_category
ORDER BY character_name, sp DESC;

-- 9. View: Character summary with role recommendations
DROP VIEW IF EXISTS v_character_summary CASCADE;
CREATE VIEW v_character_summary AS
WITH top_categories AS (
    SELECT
        character_name,
        skill_category,
        category_sp,
        ROW_NUMBER() OVER (PARTITION BY character_name ORDER BY category_sp DESC) as rn
    FROM v_character_skill_categories
),
totals AS (
    SELECT
        c.character_id,
        c.character_name,
        COUNT(cs.skill_id) as total_skills,
        SUM(cs.skillpoints_in_skill) as total_sp,
        SUM(CASE WHEN cs.active_skill_level = 5 THEN 1 ELSE 0 END) as level_5_count
    FROM characters c
    LEFT JOIN character_skills cs ON c.character_id = cs.character_id
    GROUP BY c.character_id, c.character_name
)
SELECT
    t.character_id,
    t.character_name,
    t.total_skills,
    t.total_sp,
    t.level_5_count,
    tc1.skill_category as top1_category,
    tc1.category_sp as top1_sp,
    tc2.skill_category as top2_category,
    tc2.category_sp as top2_sp,
    tc3.skill_category as top3_category,
    tc3.category_sp as top3_sp
FROM totals t
LEFT JOIN top_categories tc1 ON t.character_name = tc1.character_name AND tc1.rn = 1
LEFT JOIN top_categories tc2 ON t.character_name = tc2.character_name AND tc2.rn = 2
LEFT JOIN top_categories tc3 ON t.character_name = tc3.character_name AND tc3.rn = 3
ORDER BY t.total_sp DESC;

-- Add comments
COMMENT ON VIEW v_character_skills_detailed IS 'All character skills with category information';
COMMENT ON VIEW v_character_skill_categories IS 'Skills aggregated by category per character';
COMMENT ON VIEW v_character_specializations IS 'Character specializations ranked by SP';
COMMENT ON VIEW v_skill_matrix_level5 IS 'Skill comparison matrix for high-level skills';
COMMENT ON VIEW v_unique_capabilities IS 'Skills only one character has at level 4+';
COMMENT ON VIEW v_team_skill_gaps IS 'Skills no character has trained to level 4+';
COMMENT ON VIEW v_production_capabilities IS 'Production/Industry skill breakdown';
COMMENT ON VIEW v_combat_capabilities IS 'Combat skill category breakdown';
COMMENT ON VIEW v_character_summary IS 'Character overview with top specializations';
