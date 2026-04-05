// unified-frontend/src/types/market.ts

export interface WalletJournalEntry {
  id: number
  date: string
  ref_type: string
  amount: number
  balance: number
  description?: string
  first_party_id?: number
  second_party_id?: number
}

export interface WalletJournal {
  character_id: number
  entries: WalletJournalEntry[]
  total_entries: number
}

export interface WalletTransaction {
  transaction_id: number
  date: string
  type_id: number
  type_name: string
  quantity: number
  unit_price: number
  is_buy: boolean
  location_id: number
  location_name: string
}

export interface WalletTransactions {
  character_id: number
  transactions: WalletTransaction[]
  total_transactions: number
}

export interface OrderUndercutStatus {
  order_id: number
  type_id: number
  type_name: string
  is_buy_order: boolean
  your_price: number
  market_price: number
  undercut_percent: number
  is_undercut: boolean
  location_id: number
  location_name: string
  volume_remain: number
}

export interface UndercutReport {
  character_id: number
  total_orders: number
  undercut_count: number
  outbid_count: number
  checked_at: string
  orders: OrderUndercutStatus[]
}

export interface HeatmapItem {
  type_id: number
  type_name: string
  prices: Record<string, number | null>
}

export interface HeatmapResponse {
  items: HeatmapItem[]
  hubs: string[]
}

export interface PortfolioSnapshot {
  character_id: number
  snapshot_date: string
  wallet_balance: number
  sell_order_value: number
  buy_order_escrow: number
  total_liquid: number
}

export interface PortfolioHistory {
  character_id: number
  snapshots: PortfolioSnapshot[]
  period_days: number
  growth_absolute: number
  growth_percent: number
}

export interface NotificationAlerts {
  market_undercuts: boolean
  pi_expiry: boolean
  skill_complete: boolean
  low_wallet: boolean
}

export interface NotificationSettings {
  discord_webhook: string | null
  alerts: NotificationAlerts
  check_frequency_minutes: number
  low_wallet_threshold: number
}

// Trading Analytics Types

export interface ItemPnL {
  type_id: number
  type_name: string
  total_bought: number
  total_sold: number
  current_inventory: number
  total_buy_value: number
  total_sell_value: number
  realized_pnl: number
  unrealized_pnl: number
  avg_buy_price: number
  avg_sell_price: number
  current_market_price: number
  margin_percent: number
  roi_percent: number
  first_trade_at: string | null
  last_trade_at: string | null
}

export interface TradingPnLReport {
  character_id: number
  corporation_id: number | null
  include_corp: boolean
  total_realized_pnl: number
  total_unrealized_pnl: number
  total_pnl: number
  items: ItemPnL[]
  top_winners: ItemPnL[]
  top_losers: ItemPnL[]
  period_start: string | null
  period_end: string | null
  generated_at: string
}

export interface MarginAlert {
  type_id: number
  type_name: string
  your_price: number
  market_price: number
  margin_percent: number
  alert_type: 'margin_low' | 'margin_negative' | 'spread_collapsed'
  severity: 'warning' | 'critical'
}

export interface TradingSummary {
  character_id: number
  total_realized_pnl: number
  total_unrealized_pnl: number
  total_pnl: number
  items_traded: number
  profitable_items: number
  losing_items: number
  margin_alerts: number
  critical_alerts: number
  top_winner: ItemPnL | null
  top_loser: ItemPnL | null
}

// Velocity Analysis Types

export interface ItemVelocity {
  type_id: number
  type_name: string
  volume_bought_7d: number
  volume_sold_7d: number
  volume_bought_30d: number
  volume_sold_30d: number
  avg_daily_volume: number
  days_to_sell: number | null
  turnover_rate: number
  velocity_class: 'fast' | 'medium' | 'slow' | 'dead' | 'sold_out'
}

export interface VelocityReport {
  character_id: number
  fast_movers: ItemVelocity[]
  slow_movers: ItemVelocity[]
  dead_stock: ItemVelocity[]
  generated_at: string
}

// Competition Tracking Types

export interface CompetitorInfo {
  type_id: number
  type_name: string
  region_id: number
  location_name: string
  our_position: number
  total_competitors: number
  best_price: number
  our_price: number
  price_gap: number
  price_gap_percent: number
  is_buy_order: boolean
  volume_remain: number
  status: 'ok' | 'undercut' | 'outbid'
}

export interface CompetitionReport {
  character_id: number
  total_orders: number
  competitive_orders: number
  undercut_orders: number
  outbid_orders: number
  sell_orders: CompetitorInfo[]
  buy_orders: CompetitorInfo[]
  generated_at: string
}

// Trading Alerts Types

export interface AlertEntry {
  id: number
  character_id: number
  alert_type: string
  severity: 'info' | 'warning' | 'critical'
  type_id: number | null
  type_name: string | null
  message: string
  details: Record<string, unknown> | null
  is_read: boolean
  discord_sent: boolean
  created_at: string
}

export interface AlertConfig {
  character_id: number
  discord_webhook_url: string | null
  discord_enabled: boolean
  alert_margin_threshold: number
  alert_undercut_enabled: boolean
  alert_velocity_enabled: boolean
  alert_goals_enabled: boolean
  min_alert_interval_minutes: number
  quiet_hours_start: number | null
  quiet_hours_end: number | null
}

export interface AlertsResponse {
  character_id: number
  alerts: AlertEntry[]
  unread_count: number
  critical_count: number
  warning_count: number
}

// Trading Goals Types

export interface TradingGoal {
  id: number
  character_id: number
  goal_type: 'daily' | 'weekly' | 'monthly'
  target_type: 'profit' | 'volume' | 'trades' | 'roi'
  target_value: number
  current_value: number
  period_start: string
  period_end: string
  is_achieved: boolean
  achieved_at: string | null
  is_active: boolean
  notify_on_progress: boolean
  notify_on_completion: boolean
  type_id: number | null
  type_name: string | null
  created_at: string
}

export interface GoalProgress {
  goal: TradingGoal
  progress_percent: number
  remaining: number
  days_remaining: number
  on_track: boolean
  projected_value: number
}

export interface GoalsResponse {
  character_id: number
  active_goals: GoalProgress[]
  completed_today: number
  completed_this_week: number
  completed_this_month: number
  total_achievements: number
}

// Risk Management Types

export interface ConcentrationRisk {
  type_id: number
  type_name: string
  value: number
  percent_of_portfolio: number
  order_count: number
  is_concentrated: boolean
  risk_level: 'low' | 'medium' | 'high' | 'critical'
}

export interface LiquidityRisk {
  type_id: number
  type_name: string
  your_volume: number
  market_daily_volume: number
  days_to_sell: number | null
  liquidity_score: number
  risk_level: 'low' | 'medium' | 'high' | 'critical'
}

export interface RiskSummary {
  total_portfolio_value: number
  total_orders: number
  concentration_score: number
  liquidity_score: number
  overall_risk_level: 'low' | 'medium' | 'high' | 'critical'
  top_concentration_risks: ConcentrationRisk[]
  top_liquidity_risks: LiquidityRisk[]
  recommendations: string[]
}

// Trading History Types

export interface TradeEntry {
  transaction_id: number
  date: string
  type_id: number
  type_name: string
  quantity: number
  unit_price: number
  total_value: number
  is_buy: boolean
  location_name: string
  client_id: number | null
}

export interface DailyStats {
  date: string
  buy_count: number
  sell_count: number
  buy_volume: number
  sell_volume: number
  buy_value: number
  sell_value: number
  profit_estimate: number
  unique_items: number
}

export interface HourlyPattern {
  hour: number
  trade_count: number
  avg_value: number
  buy_percentage: number
}

export interface DayOfWeekPattern {
  day: number
  day_name: string
  trade_count: number
  avg_value: number
  profit_estimate: number
}

export interface ItemPerformance {
  type_id: number
  type_name: string
  buy_count: number
  sell_count: number
  total_bought: number
  total_sold: number
  avg_buy_price: number
  avg_sell_price: number
  margin_percent: number
  total_profit: number
  trade_frequency: number
}

export interface TradingHistory {
  character_id: number
  period_days: number
  total_trades: number
  total_buy_value: number
  total_sell_value: number
  estimated_profit: number
  recent_trades: TradeEntry[]
  daily_stats: DailyStats[]
  hourly_patterns: HourlyPattern[]
  day_of_week_patterns: DayOfWeekPattern[]
  top_items: ItemPerformance[]
  best_trading_hours: number[]
  best_trading_days: string[]
  insights: string[]
}

// ============================================
// Multi-Account Order Types
// ============================================

export interface CharacterOrderSummary {
  character_id: number
  character_name: string
  buy_orders: number
  sell_orders: number
  order_slots_used: number
  order_slots_max: number
  isk_in_escrow: number
  isk_in_sell_orders: number
}

export interface AggregatedOrderMarketStatus {
  current_best_buy: number
  current_best_sell: number
  is_outbid: boolean
  outbid_by: number
  spread_percent: number
}

export interface AggregatedOrder {
  order_id: number
  character_id: number
  character_name: string
  type_id: number
  type_name: string
  is_buy_order: boolean
  price: number
  volume_remain: number
  volume_total: number
  location_name: string
  region_name: string
  issued: string
  duration: number
  market_status: AggregatedOrderMarketStatus
}

export interface AggregatedOrdersSummary {
  total_characters: number
  total_buy_orders: number
  total_sell_orders: number
  total_isk_in_buy_orders: number
  total_isk_in_sell_orders: number
  outbid_count: number
  undercut_count: number
}

export interface AggregatedOrdersResponse {
  summary: AggregatedOrdersSummary
  by_character: CharacterOrderSummary[]
  orders: AggregatedOrder[]
  generated_at: string
}

// ============================================
// Station Trading Types
// ============================================

export interface TradingOpportunityCompetition {
  buy_orders: number
  sell_orders: number
  update_frequency: 'low' | 'medium' | 'high'
}

export interface TradingOpportunity {
  type_id: number
  type_name: string
  best_buy: number
  best_sell: number
  spread: number
  margin_percent: number
  daily_volume: number
  weekly_volume: number
  profit_per_unit: number
  daily_potential: number
  capital_required: number
  roi_daily: number
  competition: TradingOpportunityCompetition
  recommendation: 'excellent' | 'good' | 'moderate' | 'risky'
  reason: string
}

export interface TradingOpportunitiesResponse {
  region_id: number
  region_name: string
  opportunities: TradingOpportunity[]
  generated_at: string
}

// ============================================
// Arbitrage Route Types
// ============================================

export interface ArbitrageItem {
  type_id: number
  type_name: string
  buy_price_source: number
  sell_price_dest: number
  quantity: number
  volume: number
  profit_per_unit: number
  total_profit: number
  // V2 fields
  avg_daily_volume: number | null
  days_to_sell: number | null
  turnover: 'instant' | 'fast' | 'moderate' | 'slow' | 'unknown'
  competition: 'low' | 'medium' | 'high' | 'extreme'
}

export interface ArbitrageRouteSummary {
  total_items: number
  total_volume: number
  total_buy_cost: number
  total_sell_value: number
  total_profit: number
  profit_per_jump: number
  roi_percent: number
}

export interface ArbitrageRouteLogistics {
  recommended_ship: string
  round_trip_time: string
  profit_per_hour: number
}

export interface ArbitrageRoute {
  destination_region: string
  destination_hub: string
  jumps: number
  safety: 'safe' | 'caution' | 'dangerous'
  items: ArbitrageItem[]
  summary: ArbitrageRouteSummary
  logistics: ArbitrageRouteLogistics
  // V2 fields
  avg_days_to_sell: number | null
  route_risk: 'low' | 'medium' | 'high'
}

export interface ArbitrageRoutesResponse {
  start_region: string
  cargo_capacity: number
  routes: ArbitrageRoute[]
  generated_at: string
}

// ============================================
// Station Trading V2 Types
// ============================================

export interface TradingStrategy {
  style: 'active' | 'semi-active' | 'passive'
  turnover: 'instant' | 'fast' | 'moderate' | 'slow' | 'unknown'
  competition: 'low' | 'medium' | 'high' | 'extreme'
  update_frequency: string
  order_duration: string
  tips: string[]
}

export interface TradingOpportunityV2 {
  type_id: number
  type_name: string
  best_buy: number
  best_sell: number
  spread: number
  margin_percent: number
  profit_per_unit: number
  daily_potential: number
  capital_required: number
  roi_daily: number

  // Categories
  primary_index: string | null
  sub_index: string | null

  // Liquidity
  avg_daily_volume: number | null
  days_to_sell_100: number | null
  volume_vs_capital_ratio: number

  // Stability
  price_volatility: number
  trend_7d: number

  // Risk
  risk_score: number
  risk_factors: string[]

  // Existing
  competition: TradingOpportunityCompetition
  recommendation: 'excellent' | 'good' | 'moderate' | 'risky'
  reason: string

  // Trading strategy
  strategy: TradingStrategy
}

export interface CategoryInfo {
  name: string
  count: number
}

export interface TradingOpportunitiesV2Response {
  region_id: number
  region_name: string
  filters_applied: {
    primary_index: string | null
    sub_indices: string[] | null
    min_capital: number
    max_capital: number | null
    max_days_to_sell: number | null
    min_margin: number
  }
  opportunities: TradingOpportunityV2[]
  available_categories: Record<string, CategoryInfo[]>
  generated_at: string
}

export interface SimulationResult {
  type_id: number
  type_name: string
  investment: number
  units: number
  unit_price: number
  expected_profit: number
  days_to_sell: number | null
  roi_percent: number
  risk_score: number
  breakdown: {
    buy_price: number
    sell_price: number
    spread: number
    broker_fee: number
    sales_tax: number
    gross_profit: number
    net_profit: number
  }
}

export interface AllocationRequest {
  budget: number
  strategy: 'max_profit' | 'balanced' | 'min_risk'
  max_per_item?: number
  max_days_to_sell?: number
  primary_index?: string
  sub_indices?: string[]
}

export interface ItemAllocation {
  type_id: number
  type_name: string
  investment: number
  units: number
  expected_profit_per_day: number
  days_to_sell: number | null
  risk_score: number
  allocation_percent: number
}

export interface AllocationResult {
  allocations: ItemAllocation[]
  total_invested: number
  expected_daily_profit: number
  average_days_to_sell: number
  average_risk_score: number
  reserve: number
}
