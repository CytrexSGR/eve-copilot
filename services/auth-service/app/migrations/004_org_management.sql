-- Migration 004: Org Management (Permissions + Audit Log)

-- Permission matrix per corp + role
CREATE TABLE IF NOT EXISTS org_permissions (
    id SERIAL PRIMARY KEY,
    corporation_id BIGINT NOT NULL,
    role TEXT NOT NULL,
    permission TEXT NOT NULL,
    granted BOOLEAN DEFAULT true,
    UNIQUE(corporation_id, role, permission)
);
CREATE INDEX IF NOT EXISTS idx_org_permissions_corp ON org_permissions(corporation_id);

-- Audit log for all org actions
CREATE TABLE IF NOT EXISTS org_audit_log (
    id BIGSERIAL PRIMARY KEY,
    corporation_id BIGINT NOT NULL,
    actor_character_id BIGINT NOT NULL,
    actor_name TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    target_name TEXT,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_log_corp ON org_audit_log(corporation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON org_audit_log(actor_character_id);
