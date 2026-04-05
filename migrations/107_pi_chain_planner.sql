-- PI Chain Planner: Graph-based production chain management
-- 3 new tables for plan → nodes → edges DAG structure

CREATE TABLE pi_plans (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'planning',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE pi_plan_nodes (
    id                  SERIAL PRIMARY KEY,
    plan_id             INT NOT NULL REFERENCES pi_plans(id) ON DELETE CASCADE,
    type_id             INT NOT NULL,
    type_name           VARCHAR(200) NOT NULL,
    tier                SMALLINT NOT NULL,
    is_target           BOOLEAN NOT NULL DEFAULT FALSE,
    soll_qty_per_hour   FLOAT NOT NULL DEFAULT 0,
    character_id        INT,
    planet_id           BIGINT,
    UNIQUE(plan_id, type_id)
);

CREATE INDEX idx_pi_plan_nodes_plan ON pi_plan_nodes(plan_id);

CREATE TABLE pi_plan_edges (
    id              SERIAL PRIMARY KEY,
    plan_id         INT NOT NULL REFERENCES pi_plans(id) ON DELETE CASCADE,
    source_node_id  INT NOT NULL REFERENCES pi_plan_nodes(id) ON DELETE CASCADE,
    target_node_id  INT NOT NULL REFERENCES pi_plan_nodes(id) ON DELETE CASCADE,
    quantity_ratio  FLOAT NOT NULL
);

CREATE INDEX idx_pi_plan_edges_plan ON pi_plan_edges(plan_id);
CREATE INDEX idx_pi_plan_edges_source ON pi_plan_edges(source_node_id);
CREATE INDEX idx_pi_plan_edges_target ON pi_plan_edges(target_node_id);
