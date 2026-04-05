export interface AuthConfig {
  login_enabled: boolean;
  subscription_enabled: boolean;
}

export interface UserProfile {
  character_id: number;
  character_name: string;
  subscriptions: SubscriptionInfo[];
  features: string[];
}

export interface SubscriptionInfo {
  product_slug: string;
  product_name: string;
  features: string[];
  expires_at: string;
  days_remaining: number;
}

export interface AccountInfo {
  account_id: number;
  primary_character_id: number;
  primary_character_name: string;
  tier: string;
  subscription_id: number | null;
  expires_at: string | null;
  corporation_id: number | null;
  alliance_id: number | null;
  characters: LinkedCharacter[];
  created_at: string;
  last_login: string;
}

export interface LinkedCharacter {
  character_id: number;
  character_name: string;
  is_primary: boolean;
}

export interface TierPricing {
  tier: string;
  base_price_isk: number;
  per_pilot_isk: number;
  duration_days: number;
  is_active: boolean;
}

export interface TierInfo {
  tier: string;
  subscription_id: number | null;
  expires_at: string | null;
}

export interface SubscriptionDetail {
  effective_tier: string;
  subscription: {
    id: number;
    tier: string;
    paid_by: number;
    corporation_id: number | null;
    alliance_id: number | null;
    status: string;
    expires_at: string;
    auto_renew: boolean;
    created_at: string;
  } | null;
  payments: PaymentRecord[];
}

export interface PaymentRecord {
  id: number;
  reference_code: string;
  amount: number;
  status: string;
  verified_at: string | null;
  created_at: string;
}

export interface SubscribeResponse {
  reference_code: string;
  amount_isk: number;
  per_pilot_isk: number;
  billing_character: string;
  tier: string;
  duration_days: number;
  instructions: string;
}

export interface CorpInfo {
  corporation_id: number;
  role: string | null;
  has_management_access: boolean;
  subscription?: {
    id: number;
    tier: string;
    status: string;
    expires_at: string;
    paid_by: number;
    auto_renew: boolean;
  } | null;
  members?: number;
  roles?: Array<{
    character_id: number;
    character_name: string;
    role: string;
    granted_at: string;
  }>;
}

export const TIER_HIERARCHY: Record<string, number> = {
  free: 0,
  pilot: 1,
  corporation: 2,
  alliance: 3,
  coalition: 4,
};

export const TIER_COLORS: Record<string, string> = {
  free: '#8b949e',
  pilot: '#00d4ff',
  corporation: '#ffcc00',
  alliance: '#ff4444',
  coalition: '#a855f7',
};

export const TIER_LABELS: Record<string, string> = {
  free: 'Free',
  pilot: 'Pilot',
  corporation: 'Corporation',
  alliance: 'Alliance',
  coalition: 'Coalition',
};

// --- Module-based gating types ---

export interface OrgPlan {
  type: 'corporation' | 'alliance';
  plan: string;
  has_seat: boolean;
  heavy_seats: number;
  seats_used: number;
  expires_at: string | null;
}

export interface ModulePricing {
  module_name: string;
  display_name: string;
  category: string;
  base_price_isk: number;
  duration_days: number;
  is_active: boolean;
}

export interface ModuleInfo {
  modules: string[];
  org_plan: OrgPlan | null;
}

export const MODULE_NAMES: Record<string, string> = {
  warfare_intel: 'Warfare Intel',
  war_economy: 'War Economy',
  wormhole_intel: 'Wormhole Intel',
  doctrine_intel: 'Doctrine Intel',
  battle_analysis: 'Battle Analysis',
  character_suite: 'Character Suite',
  market_analysis: 'Market Analysis',
  production_suite: 'Production Suite',
  corp_intel: 'Corporation Intel',
  alliance_intel: 'Alliance Intel',
  powerbloc_intel: 'PowerBloc Intel',
};

export const MODULE_COLORS: Record<string, string> = {
  warfare_intel: '#f85149',
  war_economy: '#d29922',
  wormhole_intel: '#a855f7',
  doctrine_intel: '#3fb950',
  battle_analysis: '#ff6a00',
  character_suite: '#00d4ff',
  market_analysis: '#58a6ff',
  production_suite: '#ff6a00',
  corp_intel: '#ffcc00',
  alliance_intel: '#ff4444',
  powerbloc_intel: '#a855f7',
};

export const MODULE_PRICES: Record<string, string> = {
  warfare_intel: '100M',
  war_economy: '100M',
  wormhole_intel: '100M',
  doctrine_intel: '100M',
  battle_analysis: '100M',
  character_suite: '150M',
  market_analysis: '150M',
  production_suite: '150M',
  corp_intel: '50M',
  alliance_intel: '75M',
  powerbloc_intel: '100M',
};

// Entity module group matching (same as backend)
export const ENTITY_MODULE_GROUPS: Record<string, string[]> = {
  corp_intel: ['corp_intel_1', 'corp_intel_5', 'corp_intel_unlimited'],
  alliance_intel: ['alliance_intel_1', 'alliance_intel_5', 'alliance_intel_unlimited'],
  powerbloc_intel: ['powerbloc_intel_1', 'powerbloc_intel_5', 'powerbloc_intel_unlimited'],
};

// --- Character Management Types ---

export interface TokenHealth {
  character_id: number;
  character_name: string;
  is_valid: boolean;
  status: 'valid' | 'expired' | 'incomplete' | 'expiring' | 'missing';
  scopes: string[];
  missing_scopes: string[];
  scope_groups: Record<string, 'full' | 'partial' | 'none'>;
  expires_in_hours: number;
  last_refresh: string | null;
}

export interface AccountSummary {
  account_id: number;
  total_isk: number;
  total_sp: number;
  characters: CharacterSummaryEntry[];
}

export interface CharacterSummaryEntry {
  character_id: number;
  name: string;
  is_primary: boolean;
  isk: number;
  sp: number;
  location: string | null;
  ship: string | null;
  skill_queue_length: number;
  skill_queue_finish: string | null;
  token_health: string;
}

// --- Org Management Types (Phase 2) ---

export interface OrgMember {
  account_id: number;
  primary_character_id: number;
  primary_character_name: string;
  effective_tier: string;
  last_login: string | null;
  role: string | null;
  token_status: 'valid' | 'expired' | 'missing';
}

export interface OrgOverview {
  corporation_id: number;
  member_count: number;
  token_coverage_pct: number;
  active_7d: number;
  role_distribution: Record<string, number>;
}

export interface OrgPermission {
  role: string;
  permission: string;
  granted: boolean;
}

export interface OrgPermissionsResponse {
  permissions: OrgPermission[];
  all_permissions: string[];
  all_roles: string[];
}

export interface AuditLogEntry {
  id: number;
  corporation_id: number;
  actor_character_id: number;
  actor_name: string;
  action: string;
  target_type: string | null;
  target_id: string | null;
  target_name: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface AuditLogResponse {
  total: number;
  entries: AuditLogEntry[];
  limit: number;
  offset: number;
}
