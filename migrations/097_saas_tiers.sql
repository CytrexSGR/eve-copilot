-- 097_saas_tiers.sql
-- SaaS Feature-Gating: Tier subscriptions, platform roles, tier-based payments

-- Tier subscriptions (tier-native model for SaaS)
CREATE TABLE IF NOT EXISTS tier_subscriptions (
    id              SERIAL PRIMARY KEY,
    tier            TEXT NOT NULL CHECK (tier IN ('pilot', 'corporation', 'alliance', 'coalition')),
    paid_by         BIGINT NOT NULL,
    corporation_id  BIGINT,
    alliance_id     BIGINT,
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'grace', 'expired', 'cancelled')),
    expires_at      TIMESTAMPTZ NOT NULL,
    auto_renew      BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tier_sub_paid_by ON tier_subscriptions (paid_by);
CREATE INDEX IF NOT EXISTS idx_tier_sub_corp ON tier_subscriptions (corporation_id) WHERE corporation_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tier_sub_alliance ON tier_subscriptions (alliance_id) WHERE alliance_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tier_sub_active ON tier_subscriptions (status) WHERE status IN ('active', 'grace');

-- Platform roles for corp/alliance management
CREATE TABLE IF NOT EXISTS platform_roles (
    corporation_id  BIGINT NOT NULL,
    character_id    BIGINT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('admin', 'officer', 'member')),
    granted_by      BIGINT NOT NULL,
    granted_at      TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (corporation_id, character_id)
);

CREATE INDEX IF NOT EXISTS idx_platform_roles_char ON platform_roles (character_id);

-- Tier payments (ISK transfer verification)
CREATE TABLE IF NOT EXISTS tier_payments (
    id              SERIAL PRIMARY KEY,
    character_id    BIGINT NOT NULL,
    amount          BIGINT NOT NULL,
    reference_code  TEXT NOT NULL,
    esi_journal_id  BIGINT UNIQUE,
    subscription_id INTEGER REFERENCES tier_subscriptions(id),
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'verified', 'failed', 'refunded')),
    verified_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tier_payments_code ON tier_payments (reference_code);
CREATE INDEX IF NOT EXISTS idx_tier_payments_char ON tier_payments (character_id);
CREATE INDEX IF NOT EXISTS idx_tier_payments_pending ON tier_payments (status) WHERE status = 'pending';

-- Tier pricing config
CREATE TABLE IF NOT EXISTS tier_pricing (
    tier            TEXT PRIMARY KEY CHECK (tier IN ('pilot', 'corporation', 'alliance', 'coalition')),
    base_price_isk  BIGINT NOT NULL,
    per_pilot_isk   BIGINT NOT NULL DEFAULT 0,
    duration_days   INTEGER NOT NULL DEFAULT 30,
    is_active       BOOLEAN DEFAULT true,
    updated_at      TIMESTAMPTZ DEFAULT now()
);

INSERT INTO tier_pricing (tier, base_price_isk, per_pilot_isk, duration_days) VALUES
    ('pilot',       500000000,    0,         30),
    ('corporation', 5000000000,   0,         30),
    ('alliance',    10000000000,  25000000,  30),
    ('coalition',   200000000000, 0,         30)
ON CONFLICT (tier) DO NOTHING;

-- Service wallet config (holding character for ISK)
CREATE TABLE IF NOT EXISTS service_wallets (
    id              SERIAL PRIMARY KEY,
    character_id    BIGINT NOT NULL,
    character_name  TEXT NOT NULL,
    is_active       BOOLEAN DEFAULT true,
    last_journal_ref BIGINT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Tier resolution cache (fallback if Redis down)
CREATE TABLE IF NOT EXISTS character_tier_cache (
    character_id    BIGINT PRIMARY KEY,
    effective_tier  TEXT NOT NULL DEFAULT 'free',
    corporation_id  BIGINT,
    alliance_id     BIGINT,
    updated_at      TIMESTAMPTZ DEFAULT now()
);
