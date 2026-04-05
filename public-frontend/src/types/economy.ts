// Economy-related types for EVE Intel Public Frontend

// ==================== War Profiteering Types ====================

export interface WarProfiteering {
  period: string;
  global: {
    total_opportunity_value: number;
    total_items_destroyed: number;
    unique_item_types: number;
    most_valuable_item: string;
  };
  items: Array<{
    item_type_id: number;
    item_name: string;
    quantity_destroyed: number;
    market_price: number;
    opportunity_value: number;
  }>;
  categories?: Array<{
    category_name: string;
    total_destroyed: number;
    total_value: number;
  }>;
}

// ==================== War Economy Types ====================

export interface WarEconomyItem {
  item_type_id: number;
  item_name: string;
  quantity_destroyed: number;
  market_price: number;
  opportunity_value?: number;
  demand_value?: number;
}

export interface ShipClassComposition {
  count: number;
  percentage: number;
}

export interface TopHull {
  ship_name: string;
  ship_class: string;
  losses: number;
  percentage: number;
}

export interface FleetComposition {
  region_id: number;
  region_name: string;
  total_ships_lost: number;
  composition: Record<string, ShipClassComposition>;
  doctrine_hints: string[];
  top_hulls?: TopHull[];
  class_summary?: Record<string, { count: number; percentage: number }>;
}

export interface RegionalDemand {
  region_id: number;
  region_name: string;
  kills: number;
  isk_destroyed: number;
  top_demanded_items: WarEconomyItem[];
  ship_classes: Record<string, number>;
  demand_score: number;
}

export interface WarEconomy {
  timestamp: string;
  period: string;
  regional_demand: RegionalDemand[];
  hot_items: WarEconomyItem[];
  fleet_compositions: FleetComposition[];
  global_summary: {
    total_regions_active: number;
    total_kills_24h: number;
    total_isk_destroyed: number;
    hottest_region: {
      region_id: number;
      region_name: string;
      kills: number;
    } | null;
    total_opportunity_value: number;
  };
  error?: string;
}

export interface WarEconomyAnalysis {
  summary: string;
  insights: string[];
  recommendations: string[];
  doctrine_alert?: string | null;
  risk_warnings: string[];
  generated_at: string;
  error?: string;
}

// ==================== Trade Routes Types ====================

export interface TradeRoutes {
  period: string;
  global: {
    total_routes: number;
    dangerous_routes: number;
    avg_danger_score: number;
    gate_camps_detected: number;
  };
  routes: Array<{
    origin_system: string;
    destination_system: string;
    jumps: number;
    danger_score: number;
    total_kills: number;
    total_isk_destroyed: number;
    systems: Array<{
      system_id: number;
      system_name: string;
      security_status: number;
      danger_score: number;
      kills_24h: number;
      isk_destroyed_24h: number;
      is_gate_camp: boolean;
      battle_id?: number;
    }>;
  }>;
}

// ==================== Extended Hot Items Types ====================

export interface RegionalPrices {
  jita: number;
  amarr: number;
  rens: number;
  dodixie: number;
  hek: number;
}

export interface DestructionZone {
  region_id: number;
  region_name: string;
  quantity: number;
  percentage: number;
}

export interface ExtendedHotItem {
  type_id: number;
  name: string;
  group: string;
  quantity_destroyed: number;
  opportunity_value: number;
  regional_prices: RegionalPrices;
  best_buy: { hub: string; price: number };
  best_sell: { hub: string; price: number };
  spread_percent: number;
  destruction_zones: DestructionZone[];
  trend_7d: number;
  suggested_margin: number;
}

export interface ExtendedHotItemsResponse {
  items: ExtendedHotItem[];
  total_opportunity_value: number;
  item_count: number;
  period: string;
}

// ==================== Warzone Routes Types ====================

export interface CargoItem {
  type_id: number;
  name: string;
  jita_price: number;
  estimated_sell_price: number;
  quantity_destroyed: number;
  suggested_quantity: number;
  potential_profit: number;
  markup_percent: number;
}

export interface WarzoneRoute {
  region_id: number;
  region_name: string;
  kills_24h: number;
  active_battles: number;
  status_level: 'gank' | 'brawl' | 'battle' | 'hellcamp';
  jumps_from_jita: number;
  estimated_travel_hours: number;
  items: CargoItem[];
  cargo_items: number;
  total_buy_cost: number;
  total_potential_revenue: number;
  estimated_profit: number;
  roi_percent: number;
  isk_per_hour: number;
}

export interface WarzoneRoutesResponse {
  routes: WarzoneRoute[];
  warzone_count: number;
  total_potential_profit: number;
  period: string;
}

// ==================== Fuel Market Intelligence Types ====================

export interface FuelTrendSnapshot {
  timestamp: string;
  volume: number;
  baseline: number;
  delta_percent: number;
  price: number;
  anomaly: boolean;
  severity: 'normal' | 'low' | 'medium' | 'high' | 'critical';
}

export interface FuelTrend {
  isotope_id: number;
  isotope_name: string;
  snapshots: FuelTrendSnapshot[];
}

export interface FuelTrendsResponse {
  region_id: number;
  hours: number;
  trends: FuelTrend[];
}

// ==================== Supercapital Construction Types ====================

export interface SupercapTimer {
  id: number;
  ship_type_id: number;
  ship_name: string;
  solar_system_id: number;
  system_name: string;
  region_name: string;
  alliance_name: string | null;
  build_start_date: string;
  estimated_completion: string;
  days_remaining: number;
  hours_remaining: number;
  status: string;
  confidence_level: string;
  notes: string | null;
  strike_window: string;
  alert_level: 'critical' | 'high' | 'medium' | 'low';
}

export interface SupercapTimersResponse {
  count: number;
  timers: SupercapTimer[];
}

// ==================== Market Manipulation Types ====================

export interface ManipulationAlert {
  type_id: number;
  type_name: string;
  region_id: number;
  region_name: string;
  current_price: number;
  baseline_price: number;
  price_change_percent: number;
  current_volume: number;
  baseline_volume: number;
  volume_change_percent: number;
  z_score: number;
  severity: string;
  manipulation_type: 'price_spike' | 'volume_anomaly' | 'combined';
  detected_at: string;
  context: string;
}

export interface ManipulationAlertsResponse {
  region_id: number;
  count: number;
  alerts: ManipulationAlert[];
}

// ==================== Economic Overview Types ====================

export interface EconomicOverview {
  region_id: number;
  region_name: string;
  fuel_anomalies: number;
  manipulation_alerts: number;
  active_supercap_timers: number;
  summary: {
    fuel_status: string;
    market_status: string;
    threat_level: string;
  };
}

// ==================== Doctrine Detection Types ====================

export interface ShipComposition {
  type_id: number;
  type_name: string;
  ratio: number;
}

export interface DoctrineTemplate {
  id: number;
  doctrine_name: string;
  alliance_id: number | null;
  alliance_name: string | null;
  region_id: number;
  region_name: string | null;
  composition: Record<string, number>; // type_id -> ratio (legacy)
  composition_with_names: ShipComposition[] | null;
  confidence_score: number;
  observation_count: number;
  first_seen: string;
  last_seen: string;
  total_pilots_avg: number;
  primary_doctrine_type: string | null;
  created_at: string;
  updated_at: string;
}

export interface DoctrineListResponse {
  doctrines: DoctrineTemplate[];
  total: number;
}

export interface ItemOfInterest {
  id: number;
  doctrine_id: number;
  type_id: number;
  item_name: string;
  item_category: 'ammunition' | 'fuel' | 'module';
  consumption_rate: number | null;
  priority: number;
  created_at: string;
}

export interface ItemsListResponse {
  items: ItemOfInterest[];
}

export interface ReclusterResponse {
  doctrines_created: number;
  doctrines_updated: number;
  hours_back: number;
  completed_at: string;
}

// ==================== Production Materials Types ====================

export interface ProductionMaterial {
  type_id: number;
  type_name: string;
  quantity: number;
}

export interface ItemWithMaterials {
  id: number;
  doctrine_id: number;
  type_id: number;
  item_name: string;
  item_category: 'ammunition' | 'fuel' | 'module' | 'drone';
  consumption_rate: number | null;
  priority: number;
  materials: ProductionMaterial[];
  blueprint_id: number | null;
  blueprint_name: string | null;
  produced_quantity: number;
}

export interface ItemsMaterialsResponse {
  items: ItemWithMaterials[];
  total_materials: Record<number, ProductionMaterial>;
}

// ==================== Capital Intel Enhanced Types ====================

export interface CapitalHourlyActivity {
  hour: number;
  engagements: number;
}

export interface RecentCapitalKill {
  killmail_id: number;
  timestamp: string;
  attacker_ship: string;
  victim_ship: string;
  pilots_involved: number;
  solar_system: string;
  region: string;
  victim_alliance: string | null;
}

export interface AllianceCapitalDetailExtended {
  alliance_id: number;
  days: number;
  summary: {
    total_engagements: number;
    unique_corps: number;
    regions_active: number;
    ship_types: number;
  };
  race_distribution: Record<string, number>;
  ships: Array<{
    ship_name: string;
    race: string;
    ship_class: string;
    engagements: number;
    corps_using: number;
  }>;
  top_corps: Array<{
    corporation_id: number;
    corporation_name: string;
    engagements: number;
    ship_types: number;
    ships_used: string[];
  }>;
  regions: Array<{
    region: string;
    ops: number;
    last_seen: string | null;
  }>;
  daily_activity: Array<{
    day: string;
    engagements: number;
  }>;
  hourly_activity: CapitalHourlyActivity[];
  recent_kills: RecentCapitalKill[];
}
