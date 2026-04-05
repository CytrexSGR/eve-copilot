-- migrations/035_ai_copilot_persistence.sql
-- AI Copilot Persistence Layer

-- Übergeordnete Pläne/Ziele
CREATE TABLE IF NOT EXISTS ai_plans (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    goal_type VARCHAR(50) NOT NULL, -- 'ship', 'isk', 'skill', 'production', 'pi', 'custom'
    target_data JSONB DEFAULT '{}',
    target_date TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'completed', 'paused', 'cancelled'
    progress_pct INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Plan Milestones mit Auto-Tracking
CREATE TABLE IF NOT EXISTS ai_plan_milestones (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER REFERENCES ai_plans(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    sequence_order INTEGER DEFAULT 0,
    tracking_type VARCHAR(30), -- 'skill', 'wallet', 'shopping_list', 'ledger', 'pi_project', 'manual', 'esi'
    tracking_config JSONB DEFAULT '{}',
    target_value NUMERIC,
    current_value NUMERIC DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'blocked'
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Plan-Resource Verknüpfungen
CREATE TABLE IF NOT EXISTS ai_plan_resources (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER REFERENCES ai_plans(id) ON DELETE CASCADE,
    resource_type VARCHAR(30) NOT NULL, -- 'shopping_list', 'ledger', 'pi_project', 'fitting'
    resource_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Persistenter AI Kontext
CREATE TABLE IF NOT EXISTS ai_context (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL,
    context_key VARCHAR(100) NOT NULL,
    context_value JSONB NOT NULL,
    source VARCHAR(50) DEFAULT 'user_stated', -- 'user_stated', 'inferred', 'system'
    confidence NUMERIC DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    UNIQUE(character_id, context_key)
);

-- Session Summaries für Kontext-Handoff
CREATE TABLE IF NOT EXISTS ai_session_summaries (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    character_id INTEGER NOT NULL,
    summary TEXT NOT NULL,
    key_decisions JSONB DEFAULT '[]',
    open_questions JSONB DEFAULT '[]',
    active_plan_ids INTEGER[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ai_plans_character ON ai_plans(character_id);
CREATE INDEX IF NOT EXISTS idx_ai_plans_status ON ai_plans(status);
CREATE INDEX IF NOT EXISTS idx_ai_plan_milestones_plan ON ai_plan_milestones(plan_id);
CREATE INDEX IF NOT EXISTS idx_ai_context_character ON ai_context(character_id);
CREATE INDEX IF NOT EXISTS idx_ai_session_summaries_character ON ai_session_summaries(character_id);
CREATE INDEX IF NOT EXISTS idx_ai_session_summaries_session ON ai_session_summaries(session_id);
