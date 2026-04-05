/** Price data from /api/market/price/{type_id} — snake_case fields */
export interface MarketPrice {
  type_id: number;
  sell_price: number;
  buy_price: number;
  adjusted_price: number | null;
  average_price: number | null;
  region_id: number;
  source: string;
  last_updated: string;
}

/** Search result from /api/items/search — camelCase fields (different from market!) */
export interface ItemSearchResult {
  typeID: number;
  typeName: string;
  groupName: string;
}

/** Item detail from /api/items/{type_id} — camelCase fields */
export interface ItemDetail {
  typeID: number;
  typeName: string;
  description: string;
  volume: number;
  mass: number;
  groupID: number;
  groupName: string;
  categoryID: number;
  categoryName: string;
  marketGroupID: number | null;
}

/** Hot items organized by category — keys are string type_ids */
export interface HotItemCategories {
  [category: string]: Record<string, MarketPrice>;
}

export const TRADE_HUBS = [
  { regionId: 10000002, name: 'Jita', shortName: 'Jita' },
  { regionId: 10000043, name: 'Amarr', shortName: 'Amarr' },
  { regionId: 10000030, name: 'Rens', shortName: 'Rens' },
  { regionId: 10000032, name: 'Dodixie', shortName: 'Dodixie' },
  { regionId: 10000042, name: 'Hek', shortName: 'Hek' },
] as const;

/**
 * Static name map for hot items (these are fixed SDE type_ids).
 * The hot-items/categories endpoint only returns price data keyed by type_id,
 * NOT type names. Since the ~52 hot items are a fixed set, we map them here
 * to avoid N extra API calls.
 */
export const HOT_ITEM_NAMES: Record<number, string> = {
  // Minerals
  34: 'Tritanium', 35: 'Pyerite', 36: 'Mexallon', 37: 'Isogen',
  38: 'Nocxium', 39: 'Zydrine', 40: 'Megacyte', 11399: 'Morphite',
  // Isotopes
  16274: 'Helium Isotopes', 17887: 'Oxygen Isotopes',
  17888: 'Nitrogen Isotopes', 17889: 'Hydrogen Isotopes',
  // Fuel Blocks
  4051: 'Nitrogen Fuel Block', 4246: 'Hydrogen Fuel Block',
  4247: 'Helium Fuel Block', 4312: 'Oxygen Fuel Block',
  // Moon Materials
  16633: 'Hydrocarbons', 16634: 'Atmospheric Gases',
  16635: 'Evaporite Deposits', 16636: 'Silicates',
  16637: 'Tungsten', 16638: 'Titanium', 16639: 'Scandium',
  16640: 'Cobalt', 16641: 'Chromium', 16642: 'Vanadium',
  16643: 'Cadmium', 16644: 'Platinum', 16646: 'Caesium',
  16647: 'Technetium', 16648: 'Hafnium', 16649: 'Mercury',
  16650: 'Promethium', 16651: 'Neodymium', 16652: 'Dysprosium',
  16653: 'Thulium',
  // Production Materials (Salvage)
  25589: 'Armor Plates', 25592: 'Fried Interface Circuit',
  25595: 'Tripped Power Circuit', 25590: 'Alloyed Tritanium Bar',
  25591: 'Burned Logic Circuit', 25593: 'Conductive Polymer',
  25594: 'Contaminated Lorentz Fluid', 25596: 'Ward Console',
  25597: 'Smashed Trigger Unit', 25598: 'Charred Micro Circuit',
  25600: 'Thruster Console', 25601: 'Damaged Artificial Neural Network',
  25602: 'Scorched Telemetry Processor', 25603: 'Contaminated Nanite Compound',
  25604: 'Malfunctioning Shield Emitter',
};

// --- Phase C: Market Suite Types ---

/** Market statistics from /api/market/stats/{region_id}/{type_id} */
export interface MarketStats {
  type_id: number;
  region_id: number;
  lowest_sell: number;
  highest_buy: number;
  sell_volume: number;
  buy_volume: number;
  spread_percent: number;
  avg_daily_volume?: number;
  price_volatility?: number;
  trend_7d?: number;
  days_to_sell_100?: number;
  risk_score?: number;
}

/** Regional price comparison from /api/market/compare/{type_id} */
export interface RegionalComparison {
  type_id: number;
  type_name: string;
  prices_by_region: Record<string, { sell_price: number; buy_price: number; volume: number }>;
  best_buy_region: string | null;
  best_buy_price: number | null;
  best_sell_region: string | null;
  best_sell_price: number | null;
}

/** Arbitrage route item */
export interface ArbitrageItem {
  type_id: number;
  type_name: string;
  buy_price_source: number;
  sell_price_dest: number;
  quantity: number;
  volume: number;
  profit_per_unit: number;
  total_profit: number;
  // Fee-adjusted fields
  gross_margin_pct: number | null;
  net_profit_per_unit: number | null;
  net_margin_pct: number | null;
  total_fees_per_unit: number | null;
  net_total_profit: number | null;
  // V2 fields
  avg_daily_volume: number | null;
  days_to_sell: number | null;
  turnover: string;
  competition: string;
}

/** Arbitrage route */
export interface ArbitrageRoute {
  destination_region: string;
  destination_hub: string;
  jumps: number;
  safety: string;
  items: ArbitrageItem[];
  summary: {
    total_items: number;
    total_volume: number;
    total_buy_cost: number;
    total_sell_value: number;
    total_profit: number;
    profit_per_jump: number;
    roi_percent: number;
    // Fee-adjusted
    net_total_profit: number | null;
    net_roi_percent: number | null;
    net_profit_per_jump: number | null;
  };
  logistics: {
    recommended_ship: string;
    round_trip_time: string;
    profit_per_hour: number;
    net_profit_per_hour: number | null;
  };
  avg_days_to_sell: number | null;
  route_risk: string;
}

/** Arbitrage routes response */
export interface ArbitrageRoutesResponse {
  start_region: string;
  cargo_capacity: number;
  routes: ArbitrageRoute[];
  generated_at: string;
  fee_assumptions: {
    broker_fee_pct: number;
    sales_tax_pct: number;
    skill_assumption: string;
  } | null;
}

/** Hunter scan result item */
export interface HunterOpportunity {
  product_id: number;
  blueprint_id: number;
  product_name: string;
  category: string;
  group_name: string;
  difficulty: number;
  material_cost: number;
  sell_price: number;
  profit: number;
  roi: number;
  volume_available: number;
  avg_daily_volume: number;
  sell_volume: number;
  risk_score: number;
  days_to_sell: number | null;
  net_profit: number;
  net_roi: number;
}

/** Hunter scan response */
export interface HunterScanResponse {
  scan_id: string;
  results: HunterOpportunity[];
  summary: {
    total_scanned: number;
    profitable: number;
    avg_roi: number;
  };
  cached: boolean;
  last_updated: string;
}

/** Trading opportunity */
export interface TradingOpportunity {
  item_id: number;
  item_name: string;
  buy_hub: string;
  sell_hub: string;
  buy_price: number;
  sell_price: number;
  profit_per_unit: number;
  roi: number;
  volume: number;
  days_to_sell: number;
  risk_score: number;
}

/** Portfolio snapshot */
export interface PortfolioSnapshot {
  character_id: number;
  snapshot_date: string;
  wallet_balance: number;
  sell_order_value: number;
  buy_order_escrow: number;
  total_liquid: number;
}

/** Portfolio history */
export interface PortfolioHistory {
  character_id: number;
  snapshots: PortfolioSnapshot[];
  period_days: number;
  growth_absolute: number;
  growth_percent: number;
}

/** Aggregated order with market status */
export interface AggregatedOrder {
  order_id: number;
  character_id: number;
  character_name: string;
  type_id: number;
  type_name: string;
  is_buy_order: boolean;
  price: number;
  volume_remain: number;
  volume_total: number;
  location_name: string;
  region_name: string;
  issued: string;
  duration: number;
  market_status: {
    current_best_buy: number;
    current_best_sell: number;
    is_outbid: boolean;
    outbid_by: number;
    spread_percent: number;
  };
}

/** Aggregated orders response */
export interface AggregatedOrdersResponse {
  summary: {
    total_characters: number;
    total_buy_orders: number;
    total_sell_orders: number;
    total_isk_in_buy_orders: number;
    total_isk_in_sell_orders: number;
    outbid_count: number;
    undercut_count: number;
  };
  by_character: Array<{
    character_id: number;
    character_name: string;
    buy_orders: number;
    sell_orders: number;
    isk_in_escrow: number;
    isk_in_sell_orders: number;
  }>;
  orders: AggregatedOrder[];
  generated_at: string;
}

/** Trading P&L report */
export interface TradingPnLReport {
  character_id: number;
  period_days?: number;
  realized_pnl?: number;
  total_realized_pnl?: number;
  unrealized_pnl?: number;
  total_unrealized_pnl?: number;
  total_pnl: number;
  total_trades?: number;
  items?: Array<{
    type_id: number;
    type_name: string;
    realized: number;
    unrealized: number;
    total: number;
    trades: number;
  }>;
  item_pnl?: Array<{
    type_id: number;
    type_name: string;
    realized: number;
    unrealized: number;
    total: number;
    trades: number;
  }>;
  top_winners: Array<{ type_id: number; type_name: string; total: number }>;
  top_losers: Array<{ type_id: number; type_name: string; total: number }>;
}

/** Trading summary */
export interface TradingSummary {
  character_id: number;
  total_buy_volume: number;
  total_sell_volume: number;
  active_orders: number;
  total_isk_traded: number;
  avg_margin: number;
}
