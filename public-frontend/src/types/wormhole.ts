export interface WormholeSummary {
  active_systems_30d: number;
  known_residents: number;
  kills_24h: number;
  isk_destroyed_24h: number;
  evictions_7d: number;
  activity_level: 'LOW' | 'MODERATE' | 'HIGH';
  last_activity: string | null;
}

export interface WormholeThreat {
  type: 'CAPITAL' | 'HUNTER' | 'SPIKE';
  severity: 'critical' | 'warning' | 'info';
  system_id: number;
  system_name: string;
  wormhole_class: number;
  description: string;
  timestamp: string;
}

export interface WHStatic {
  code: string;
  destination: string;
}

export interface WHResident {
  corporation_id: number;
  name: string;
  ticker: string;
  kills: number;
  losses: number;
  last_seen: string | null;
  is_npc?: boolean;
}

export interface ShipBreakdown {
  capital: string[];
  battleship: string[];
  cruiser: string[];
  destroyer: string[];
  frigate: string[];
  other: string[];
  threats: string[];
}

export interface ScoreBreakdown {
  activity: number;
  recency: number;
  weakness: number;
}

export interface SystemEffect {
  name: string;
  icon: string;
  bonus: string;
  color: string;
}

export interface PrimeTime {
  dominant: 'EU' | 'US' | 'AU' | 'Unknown';
  eu_pct: number;
  us_pct: number;
  au_pct: number;
}

export interface RecentKill {
  killmail_id: number;
  time: string | null;
  value: number;
  ship: string;
  ship_class: string;
  victim: string;
  corp: string;
}

export interface StructureIntel {
  total_lost: number;
  total_value: number;
  citadels: number;
  engineering: number;
  refineries: number;
  recent: Array<{
    type: string;
    time: string | null;
    value: number;
  }>;
}

export interface HunterAlliance {
  alliance_id: number;
  name: string;
  kills: number;
}

export interface ResidentAlliance {
  alliance_id: number;
  name: string;
  corps: number;
  kills: number;
}

export interface WormholeOpportunity {
  system_id: number;
  system_name: string;
  wormhole_class: number;
  statics: WHStatic[];
  opportunity_score: number;
  score_breakdown: ScoreBreakdown;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
  kills_7d: number;
  kills_24h: number;
  isk_destroyed_7d: number;
  isk_destroyed_24h: number;
  last_activity: string | null;
  is_hot: boolean;
  resident_corps: number;
  residents: WHResident[];
  ships: ShipBreakdown;
  recent_ships: string[];
  // Enhanced intel
  effect: SystemEffect | null;
  prime_time: PrimeTime | null;
  recent_kills: RecentKill[];
  structures: StructureIntel | null;
  // Power bloc intel
  hunters: HunterAlliance[];
  resident_alliances: ResidentAlliance[];
}

export interface WormholeEviction {
  battle_id: number;
  system_id: number;
  system_name: string;
  wormhole_class: number;
  total_kills: number;
  total_isk_destroyed: number;
  started_at: string;
  ended_at: string | null;
}

export interface WormholeMarketSignals {
  timeframe_days: number;
  evictions: {
    count: number;
    total_isk_destroyed: number;
    loot_dump_expected: boolean;
  };
  capital_losses: {
    total_count: number;
    total_isk: number;
    by_type: Array<{
      type: string;
      losses: number;
      isk_value: number;
    }>;
    replacement_demand_estimate: number;
  };
  ship_demand: Array<{
    ship_name: string;
    ship_class: string;
    losses: number;
    isk_value: number;
  }>;
  active_groups: {
    alliances: number;
    corporations: number;
  };
}

export interface WormholeActivity {
  system_id: number;
  system_name: string;
  wormhole_class: number;
  kills_24h: number;
  kills_7d: number;
  kills_30d: number;
  isk_destroyed_24h: number;
  last_kill_time: string | null;
}

export type WormholeTabId = 'residents' | 'hunters' | 'market' | 'thera-router';

// Enhanced Market Types
export interface CommodityPrice {
  type_id: number;
  name: string;
  tier: 'high' | 'mid' | 'low';
  sell_price: number;
  buy_price: number;
  spread: number;
  trend_7d: number;
  trend_direction: 'up' | 'down' | 'stable';
  daily_volume: number;
  npc_buy?: number;
  class?: string;
  unit_volume?: number;
  isk_per_m3?: number;
}

export interface CommodityPrices {
  gas: CommodityPrice[];
  blue_loot: CommodityPrice[];
  polymers: CommodityPrice[];
  updated_at: string;
}

export interface EvictionVictim {
  name: string;
  alliance_id: number | null;
  corporation_id: number | null;
  losses: number;
  isk_lost: number;
}

export interface StructureLoss {
  type: string;
  count: number;
  value: number;
}

export interface EvictionIntel {
  battle_id: number;
  system_id: number;
  system_name: string;
  wh_class: number | null;
  timestamp: string;
  hours_ago: number;
  total_kills: number;
  isk_destroyed: number;
  estimated_loot: number;
  loot_status: 'imminent' | 'expected' | 'dumped';
  loot_eta: string;
  victims: EvictionVictim[];
  structures_lost: StructureLoss[];
}

export interface SupplyDisruption {
  corporation_id: number;
  corporation_name: string;
  alliance_id: number | null;
  alliance_name: string;
  systems_affected: number;
  impact_level: 'high' | 'medium' | 'low';
  last_seen: string | null;
  predicted_effects: string[];
}

export interface MarketIndex {
  gas_trend: number;
  loot_trend: number;
  overall_trend: number;
  market_status: 'bullish' | 'bearish' | 'stable';
  recommendation: string;
  updated_at: string;
}

export interface PriceHistoryItem {
  prices: number[];
  dates: string[];
  min_price: number;
  max_price: number;
  avg_price: number;
  pct_vs_avg: number;
  data_points: number;
}

export type PriceHistory = Record<number, PriceHistoryItem>;

export interface PriceContextItem {
  avg_30d: number;
  pct_vs_30d: number;
  data_points: number;
}

export type PriceContext = Record<number, PriceContextItem>;
