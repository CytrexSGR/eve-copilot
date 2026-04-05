-- Migration 105: Production Projects
-- Production project container
CREATE TABLE production_projects (
    id SERIAL PRIMARY KEY,
    creator_character_id INTEGER NOT NULL,
    corporation_id INTEGER,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_pp_creator ON production_projects(creator_character_id);
CREATE INDEX idx_pp_corp ON production_projects(corporation_id) WHERE corporation_id IS NOT NULL;
CREATE INDEX idx_pp_status ON production_projects(status);

-- Items within a project
CREATE TABLE project_items (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES production_projects(id) ON DELETE CASCADE,
    type_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    me_level INTEGER NOT NULL DEFAULT 0,
    te_level INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    added_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_pi_project ON project_items(project_id);

-- Buy/make decisions per material
CREATE TABLE project_material_decisions (
    id SERIAL PRIMARY KEY,
    project_item_id INTEGER NOT NULL REFERENCES project_items(id) ON DELETE CASCADE,
    material_type_id INTEGER NOT NULL,
    decision VARCHAR(10) NOT NULL DEFAULT 'buy',
    quantity INTEGER NOT NULL,
    UNIQUE(project_item_id, material_type_id)
);

CREATE INDEX idx_pmd_item ON project_material_decisions(project_item_id);
