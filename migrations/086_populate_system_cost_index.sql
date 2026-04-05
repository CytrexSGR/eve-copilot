-- Migration 086: Populate system_cost_index from industry_cost_indices
-- Phase 4: Pivot activity-per-row format into aggregated system-level columns

INSERT INTO system_cost_index (
    system_id, system_name,
    manufacturing_index, reaction_index, copying_index,
    invention_index, research_te_index, research_me_index,
    updated_at
)
SELECT
    ici.solar_system_id,
    ms."solarSystemName",
    COALESCE(MAX(CASE WHEN ici.activity = 'manufacturing' THEN ici.cost_index END), 0) AS manufacturing_index,
    COALESCE(MAX(CASE WHEN ici.activity = 'reaction' THEN ici.cost_index END), 0) AS reaction_index,
    COALESCE(MAX(CASE WHEN ici.activity = 'copying' THEN ici.cost_index END), 0) AS copying_index,
    COALESCE(MAX(CASE WHEN ici.activity = 'invention' THEN ici.cost_index END), 0) AS invention_index,
    COALESCE(MAX(CASE WHEN ici.activity = 'researching_time_efficiency' THEN ici.cost_index END), 0) AS research_te_index,
    COALESCE(MAX(CASE WHEN ici.activity = 'researching_material_efficiency' THEN ici.cost_index END), 0) AS research_me_index,
    MAX(ici.fetched_at)
FROM industry_cost_indices ici
LEFT JOIN "mapSolarSystems" ms ON ms."solarSystemID" = ici.solar_system_id
GROUP BY ici.solar_system_id, ms."solarSystemName"
ON CONFLICT (system_id) DO UPDATE SET
    system_name = EXCLUDED.system_name,
    manufacturing_index = EXCLUDED.manufacturing_index,
    reaction_index = EXCLUDED.reaction_index,
    copying_index = EXCLUDED.copying_index,
    invention_index = EXCLUDED.invention_index,
    research_te_index = EXCLUDED.research_te_index,
    research_me_index = EXCLUDED.research_me_index,
    updated_at = EXCLUDED.updated_at;
