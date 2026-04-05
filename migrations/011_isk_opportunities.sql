-- =====================================================
-- ISK OPPORTUNITY ANALYSIS
-- Migration: 011_isk_opportunities.sql
-- Created: 2026-01-12
-- Purpose: Analyze ISK-making capabilities based on skills
-- =====================================================

-- View: ISK-Making Opportunities by Character
DROP VIEW IF EXISTS v_isk_opportunities CASCADE;
CREATE VIEW v_isk_opportunities AS
WITH skill_scores AS (
    -- Calculate activity scores based on relevant skills
    SELECT
        c.character_id,
        c.character_name,

        -- TRADING Score (Market skills)
        COALESCE((
            SELECT SUM(
                CASE cs.skill_name
                    WHEN 'Trade' THEN cs.active_skill_level * 2
                    WHEN 'Retail' THEN cs.active_skill_level * 2
                    WHEN 'Wholesale' THEN cs.active_skill_level * 3
                    WHEN 'Tycoon' THEN cs.active_skill_level * 4
                    WHEN 'Accounting' THEN cs.active_skill_level * 3
                    WHEN 'Broker Relations' THEN cs.active_skill_level * 3
                    WHEN 'Advanced Broker Relations' THEN cs.active_skill_level * 4
                    WHEN 'Margin Trading' THEN cs.active_skill_level * 2
                    WHEN 'Daytrading' THEN cs.active_skill_level * 2
                    WHEN 'Marketing' THEN cs.active_skill_level * 2
                    WHEN 'Procurement' THEN cs.active_skill_level * 2
                    WHEN 'Visibility' THEN cs.active_skill_level * 1
                    ELSE 0
                END
            )
            FROM character_skills cs
            WHERE cs.character_id = c.character_id
        ), 0) as trading_score,

        -- MINING Score
        COALESCE((
            SELECT SUM(
                CASE
                    WHEN cs.skill_name = 'Mining' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Astrogeology' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name = 'Mining Upgrades' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Ice Harvesting' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name = 'Gas Cloud Harvesting' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name = 'Mining Frigate' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Mining Barge' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name = 'Exhumers' THEN cs.active_skill_level * 4
                    WHEN cs.skill_name = 'Industrial Command Ships' THEN cs.active_skill_level * 4
                    WHEN cs.skill_name = 'Capital Industrial Ships' THEN cs.active_skill_level * 5
                    WHEN cs.skill_name = 'Mining Director' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name LIKE '%Reprocessing%' THEN cs.active_skill_level * 1
                    ELSE 0
                END
            )
            FROM character_skills cs
            WHERE cs.character_id = c.character_id
        ), 0) as mining_score,

        -- PRODUCTION Score (Manufacturing)
        COALESCE((
            SELECT SUM(
                CASE
                    WHEN cs.skill_name = 'Industry' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Advanced Industry' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name = 'Mass Production' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name = 'Advanced Mass Production' THEN cs.active_skill_level * 4
                    WHEN cs.skill_name = 'Supply Chain Management' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name LIKE '%Construction' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Reactions' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name = 'Mass Reactions' THEN cs.active_skill_level * 3
                    ELSE 0
                END
            )
            FROM character_skills cs
            WHERE cs.character_id = c.character_id
        ), 0) as production_score,

        -- RESEARCH Score (Invention/Copying)
        COALESCE((
            SELECT SUM(
                CASE
                    WHEN cs.skill_name = 'Science' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Research' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Laboratory Operation' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Advanced Laboratory Operation' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name = 'Metallurgy' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name LIKE '%Encryption%' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name LIKE 'Research Project%' THEN cs.active_skill_level * 2
                    ELSE 0
                END
            )
            FROM character_skills cs
            WHERE cs.character_id = c.character_id
        ), 0) as research_score,

        -- MISSION Score (PvE Combat)
        COALESCE((
            SELECT SUM(
                CASE
                    WHEN cs.skill_name LIKE '%Missiles%' AND cs.active_skill_level >= 4 THEN cs.active_skill_level * 2
                    WHEN cs.skill_name LIKE '%Turret%' AND cs.active_skill_level >= 4 THEN cs.active_skill_level * 2
                    WHEN cs.skill_name LIKE '%Drone%' AND cs.active_skill_level >= 4 THEN cs.active_skill_level * 1
                    WHEN cs.skill_name LIKE '%Battleship%' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name LIKE '%Cruiser%' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Marauders' THEN cs.active_skill_level * 5
                    WHEN cs.skill_name LIKE 'Caldari Subsystems' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Social' THEN cs.active_skill_level * 1
                    WHEN cs.skill_name = 'Connections' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Negotiation' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Security Connections' THEN cs.active_skill_level * 2
                    ELSE 0
                END
            )
            FROM character_skills cs
            WHERE cs.character_id = c.character_id
        ), 0) as mission_score,

        -- EXPLORATION Score
        COALESCE((
            SELECT SUM(
                CASE
                    WHEN cs.skill_name = 'Astrometrics' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name LIKE 'Astrometric%' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Hacking' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name = 'Archaeology' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name = 'Covert Ops' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name LIKE '%Scanning%' THEN cs.active_skill_level * 2
                    ELSE 0
                END
            )
            FROM character_skills cs
            WHERE cs.character_id = c.character_id
        ), 0) as exploration_score,

        -- HAULING Score
        COALESCE((
            SELECT SUM(
                CASE
                    WHEN cs.skill_name = 'Transport Ships' THEN cs.active_skill_level * 4
                    WHEN cs.skill_name LIKE '%Industrial%' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name LIKE '%Freighter%' THEN cs.active_skill_level * 5
                    WHEN cs.skill_name = 'Jump Drive Calibration' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name = 'Jump Fuel Conservation' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Evasive Maneuvering' THEN cs.active_skill_level * 1
                    ELSE 0
                END
            )
            FROM character_skills cs
            WHERE cs.character_id = c.character_id
        ), 0) as hauling_score,

        -- PI Score (Planetary Interaction)
        COALESCE((
            SELECT SUM(
                CASE
                    WHEN cs.skill_name = 'Command Center Upgrades' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name = 'Interplanetary Consolidation' THEN cs.active_skill_level * 3
                    WHEN cs.skill_name = 'Planetology' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Advanced Planetology' THEN cs.active_skill_level * 2
                    WHEN cs.skill_name = 'Remote Sensing' THEN cs.active_skill_level * 1
                    WHEN cs.skill_name = 'Customs Code Expertise' THEN cs.active_skill_level * 2
                    ELSE 0
                END
            )
            FROM character_skills cs
            WHERE cs.character_id = c.character_id
        ), 0) as pi_score

    FROM characters c
)
SELECT
    character_id,
    character_name,

    -- Raw scores
    trading_score,
    mining_score,
    production_score,
    research_score,
    mission_score,
    exploration_score,
    hauling_score,
    pi_score,

    -- Best activity for this character
    CASE GREATEST(trading_score, mining_score, production_score, research_score,
                  mission_score, exploration_score, hauling_score, pi_score)
        WHEN trading_score THEN 'Trading'
        WHEN mining_score THEN 'Mining'
        WHEN production_score THEN 'Production'
        WHEN research_score THEN 'Research'
        WHEN mission_score THEN 'Missions'
        WHEN exploration_score THEN 'Exploration'
        WHEN hauling_score THEN 'Hauling'
        WHEN pi_score THEN 'Planetary Interaction'
        ELSE 'Unknown'
    END as best_activity,

    -- Ranking of activities
    ARRAY[
        CASE WHEN trading_score > 0 THEN 'Trading: ' || trading_score END,
        CASE WHEN mining_score > 0 THEN 'Mining: ' || mining_score END,
        CASE WHEN production_score > 0 THEN 'Production: ' || production_score END,
        CASE WHEN research_score > 0 THEN 'Research: ' || research_score END,
        CASE WHEN mission_score > 0 THEN 'Missions: ' || mission_score END,
        CASE WHEN exploration_score > 0 THEN 'Exploration: ' || exploration_score END,
        CASE WHEN hauling_score > 0 THEN 'Hauling: ' || hauling_score END,
        CASE WHEN pi_score > 0 THEN 'PI: ' || pi_score END
    ] as activity_scores

FROM skill_scores
ORDER BY character_name;

-- View: Team ISK Strategy
DROP VIEW IF EXISTS v_team_isk_strategy CASCADE;
CREATE VIEW v_team_isk_strategy AS
WITH best_per_activity AS (
    SELECT
        'Trading' as activity,
        (SELECT character_name FROM v_isk_opportunities ORDER BY trading_score DESC LIMIT 1) as best_char,
        (SELECT MAX(trading_score) FROM v_isk_opportunities) as best_score
    UNION ALL
    SELECT
        'Mining',
        (SELECT character_name FROM v_isk_opportunities ORDER BY mining_score DESC LIMIT 1),
        (SELECT MAX(mining_score) FROM v_isk_opportunities)
    UNION ALL
    SELECT
        'Production',
        (SELECT character_name FROM v_isk_opportunities ORDER BY production_score DESC LIMIT 1),
        (SELECT MAX(production_score) FROM v_isk_opportunities)
    UNION ALL
    SELECT
        'Research',
        (SELECT character_name FROM v_isk_opportunities ORDER BY research_score DESC LIMIT 1),
        (SELECT MAX(research_score) FROM v_isk_opportunities)
    UNION ALL
    SELECT
        'Missions',
        (SELECT character_name FROM v_isk_opportunities ORDER BY mission_score DESC LIMIT 1),
        (SELECT MAX(mission_score) FROM v_isk_opportunities)
    UNION ALL
    SELECT
        'Exploration',
        (SELECT character_name FROM v_isk_opportunities ORDER BY exploration_score DESC LIMIT 1),
        (SELECT MAX(exploration_score) FROM v_isk_opportunities)
    UNION ALL
    SELECT
        'Hauling',
        (SELECT character_name FROM v_isk_opportunities ORDER BY hauling_score DESC LIMIT 1),
        (SELECT MAX(hauling_score) FROM v_isk_opportunities)
    UNION ALL
    SELECT
        'Planetary Interaction',
        (SELECT character_name FROM v_isk_opportunities ORDER BY pi_score DESC LIMIT 1),
        (SELECT MAX(pi_score) FROM v_isk_opportunities)
)
SELECT
    activity,
    best_char,
    best_score,
    CASE
        WHEN best_score >= 50 THEN 'Excellent'
        WHEN best_score >= 30 THEN 'Good'
        WHEN best_score >= 15 THEN 'Moderate'
        WHEN best_score > 0 THEN 'Basic'
        ELSE 'Not Skilled'
    END as capability_level,
    CASE activity
        WHEN 'Trading' THEN 'Station Trading, Regional Arbitrage, Market Manipulation'
        WHEN 'Mining' THEN 'Ore Mining, Ice Mining, Moon Mining, Gas Harvesting'
        WHEN 'Production' THEN 'T1/T2 Manufacturing, Reactions, Component Building'
        WHEN 'Research' THEN 'BPC Copying, Invention, ME/TE Research'
        WHEN 'Missions' THEN 'L4 Security, Burner Missions, Epic Arcs'
        WHEN 'Exploration' THEN 'Relic/Data Sites, Combat Sites, Wormholes'
        WHEN 'Hauling' THEN 'Courier Contracts, Trade Hub Runs, JF Services'
        WHEN 'Planetary Interaction' THEN 'P1-P4 Production, Factory Planets'
        ELSE ''
    END as activities
FROM best_per_activity
ORDER BY best_score DESC;

COMMENT ON VIEW v_isk_opportunities IS 'ISK-making capability scores per character';
COMMENT ON VIEW v_team_isk_strategy IS 'Best character for each ISK-making activity';
