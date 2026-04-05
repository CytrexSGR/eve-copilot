-- migrations/028_pi_material_assignments.sql
-- Material to colony assignments for PI projects

CREATE TABLE IF NOT EXISTS pi_material_assignments (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES pi_projects(project_id) ON DELETE CASCADE,
    material_type_id INT NOT NULL,
    tier INT NOT NULL CHECK (tier >= 0 AND tier <= 4),
    colony_id INT REFERENCES pi_project_colonies(id) ON DELETE SET NULL,
    is_auto_assigned BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, material_type_id)
);

CREATE INDEX IF NOT EXISTS idx_pi_material_assignments_project
    ON pi_material_assignments(project_id);

COMMENT ON TABLE pi_material_assignments IS 'Links production chain materials to project colonies';
COMMENT ON COLUMN pi_material_assignments.tier IS 'PI tier 0-4 (P0 raw to P4 advanced)';
COMMENT ON COLUMN pi_material_assignments.is_auto_assigned IS 'True if system assigned, false if user modified';
