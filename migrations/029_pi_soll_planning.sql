-- migrations/029_pi_soll_planning.sql
-- SOLL (planned) output tracking for PI material assignments

-- Add SOLL fields to material assignments
ALTER TABLE pi_material_assignments
    ADD COLUMN IF NOT EXISTS soll_output_per_hour DECIMAL(20,2),
    ADD COLUMN IF NOT EXISTS soll_notes TEXT;

-- Planning history for tracking changes
CREATE TABLE IF NOT EXISTS pi_planning_history (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES pi_projects(project_id) ON DELETE CASCADE,
    material_type_id INT NOT NULL,
    old_soll_output DECIMAL(20,2),
    new_soll_output DECIMAL(20,2),
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT NOW(),
    reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_pi_planning_history_project
    ON pi_planning_history(project_id);

COMMENT ON COLUMN pi_material_assignments.soll_output_per_hour IS 'Planned output per hour (user-defined target)';
COMMENT ON COLUMN pi_material_assignments.soll_notes IS 'User notes for this material plan';
COMMENT ON TABLE pi_planning_history IS 'Audit trail of SOLL target changes';
