// === Calculator Tab ===

export interface BOMItem {
  material_id: number;
  material_name: string;
  quantity: number;
  unit_price: number;
  total_cost: number;
}

export interface FinancialAnalysis {
  production_cost: number;
  sell_price: number;
  profit: number;
  roi: number;
}

export interface ProductionTime {
  base_time: number;
  te_factor: number;
  actual_time: number;
}

export interface ProductionSimulation {
  type_id: number;
  type_name: string;
  runs: number;
  me: number;
  te: number;
  bom: BOMItem[];
  financial_analysis: FinancialAnalysis;
  production_time: ProductionTime;
  shopping_list: BOMItem[];
  warnings: string[];
}

export interface QuickProfitCheck {
  type_id: number;
  type_name: string;
  production_cost: number;
  sell_price: number;
  profit_per_unit: number;
  roi_percent: number;
  is_profitable: boolean;
}

export interface FacilityComparison {
  facility_id: string;
  facility_name: string;
  material_cost: number;
  install_cost: number;
  total_cost: number;
  production_time_seconds: number;
  production_time_formatted: string;
  material_modifier: number;
  time_modifier: number;
  facility_tax: number;
}

export interface CompareResult {
  type_id: number;
  product_name: string;
  runs: number;
  me: number;
  te: number;
  facilities: FacilityComparison[];
  recommendation: string;
}

export interface ChainNode {
  type_id: number;
  name: string;
  quantity: number;
  is_manufacturable: boolean;
  children: ChainNode[];
}

export interface MaterialChain {
  type_id: number;
  name: string;
  quantity: number;
  chain: ChainNode;
}

// === Economics Tab ===

export interface ManufacturingOpportunity {
  type_id: number;
  type_name: string;
  production_cost: number;
  sell_price: number;
  profit_per_unit: number;
  roi_percent: number;
  daily_volume: number;
}

export interface EconomicsDetail {
  type_id: number;
  type_name: string;
  production_cost: number;
  market_sell: number;
  market_buy: number;
  profit: number;
  roi: number;
  production_time_seconds: number;
  daily_volume: number;
  price_volatility: number;
}

export interface RegionEconomics {
  regions: Array<{
    region_id: number;
    region_name: string;
    production_cost: number;
    sell_price: number;
    profit: number;
    roi: number;
  }>;
  best_region: string;
}

// === Invention Tab ===

export interface InventionInput {
  type_id: number;
  type_name: string;
  quantity: number;
  unit_price: number;
  total_cost: number;
}

export interface InventionDetailInvention {
  inputs: InventionInput[];
  total_input_cost: number;
  base_probability: number;
  adjusted_probability: number;
  base_output_runs: number;
  adjusted_output_runs: number;
  cost_per_bpc: number;
  result_me: number;
  result_te: number;
}

export interface InventionDetailMaterial {
  type_id: number;
  type_name: string;
  base_quantity: number;
  quantity_per_run: number;
  unit_price: number;
  total_cost: number;
}

export interface InventionDetailManufacturing {
  materials: InventionDetailMaterial[];
  material_cost_per_run: number;
  invention_cost_per_run: number;
  total_cost_per_run: number;
}

export interface InventionDetail {
  t2_type_id: number;
  t2_name: string;
  t2_blueprint_id: number;
  t1_blueprint_id: number;
  t1_blueprint_name: string;
  invention: InventionDetailInvention;
  decryptor: number | null;
  manufacturing: InventionDetailManufacturing;
}

export interface DecryptorComparison {
  decryptor: number | null;
  decryptor_name: string;
  result_me: number;
  result_te: number;
  output_runs: number;
  probability: number;
  invention_cost: number;
  total_cost_per_run: number;
}

export interface DecryptorComparisonResult {
  type_id: number;
  comparisons: DecryptorComparison[];
  best_option: DecryptorComparison | null;
}

// === Reactions Tab ===

export interface ReactionInput {
  input_type_id: number;
  input_name: string;
  quantity: number;
}

export interface ReactionFormula {
  reaction_type_id: number;
  reaction_name: string;
  product_type_id: number;
  product_name: string;
  product_quantity: number;
  reaction_time: number;
  reaction_category: string;
  inputs: ReactionInput[];
}

export interface ReactionProfitability {
  reaction_type_id: number;
  reaction_name: string;
  product_name: string;
  input_cost: number;
  output_value: number;
  profit_per_run: number;
  profit_per_hour: number;
  roi_percent: number;
  reaction_time: number;
  runs_per_hour: number;
}

// === PI Tab ===

export interface PIColony {
  id: number;
  character_id: number;
  planet_id: number;
  planet_type: string;
  solar_system_id: number;
  solar_system_name: string;
  last_update: string;
}

export interface PICharacterSummary {
  character_id: number;
  character_name: string;
  total_colonies: number;
  active_extractors: number;
  active_factories: number;
  products: Array<{
    type_id: number;
    type_name: string;
    quantity_per_day: number;
  }>;
  expiring_soon: Array<{
    colony_id: number;
    planet_id: number;
    hours_remaining: number;
  }>;
}

export interface PIGraphNode {
  pin_id: number;
  pin_type: string;
  health: string;
  health_detail: string;
  product_type_id: number | null;
  product_name: string | null;
}

export interface PIGraphEdge {
  source_pin: number;
  dest_pin: number;
  content_type_id: number;
  quantity: number;
}

export interface PIColonyGraph {
  nodes: PIGraphNode[];
  edges: PIGraphEdge[];
  health_summary: {
    ok: number;
    warning: number;
    critical: number;
    stopped: number;
  };
}

export interface PIProfitability {
  type_id: number;
  type_name: string;
  tier: number;
  input_cost: number;
  output_value: number;
  profit_per_hour: number;
  roi_percent: number;
  cycle_time: number;
}

// === PI Advisor ===

export interface PIAdvisorSkills {
  interplanetary_consolidation: number;
  command_center_upgrades: number;
  max_planets: number;
  planetology: number;
  advanced_planetology: number;
}

export interface PIRecipe {
  tier: number;
  output: string;
  inputs: string[];
}

export interface PIChainPrice {
  price: number | null;
  volume_m3: number | null;
  daily_volume: number;
}

export interface PIProductionChain {
  p0_to_p1: Record<string, string>;
  recipes: PIRecipe[];
  prices?: Record<string, PIChainPrice>;
  type_ids?: Record<string, number>;
}

export interface PIP0Material {
  type_id: number;
  type_name: string;
  quantity: number;
  planet_sources: string[];
}

export interface PIOptimalPlanet {
  planet_type: string;
  provides: string[];
}

export interface PILayoutPlanet {
  planet_type: string;
  provides: string[];
  role: string;
  processing: string;
}

export interface PIProductionLayout {
  strategy: string;
  summary: string;
  planets: PILayoutPlanet[];
}

export interface PIAdvisorOpportunity {
  type_id: number;
  type_name: string;
  tier: number;
  schematic_id: number;
  profit_per_hour: number;
  roi_percent: number;
  input_cost: number;
  output_value: number;
  cycle_time: number;
  p0_materials: PIP0Material[];
  required_planet_types: string[];
  market_buy_planets: number;
  market_buy_feasible: boolean;
  self_sufficient_planets: number;
  self_sufficient_feasible: boolean;
  optimal_planets: PIOptimalPlanet[];
  production_layout: PIProductionLayout;
  production_chain: PIProductionChain;
}

export interface PIAdvisorResponse {
  character_id: number;
  character_name: string;
  skills: PIAdvisorSkills;
  existing_colonies: number;
  opportunities: PIAdvisorOpportunity[];
  expiring_soon: Array<{
    colony_id: number;
    planet_id: number;
    planet_type: string;
    solar_system_name: string;
    product_name: string;
    hours_remaining: number;
  }>;
}

// === Planet Recommendations ===

export interface PlanetRecommendationItem {
  planet_id: number;
  planet_name: string;
  planet_type: string;
  system_id: number;
  system_name: string;
  security: number;
  jumps_from_home: number;
  resources: string[];
  recommendation_score: number;
  reason: string;
}

export interface PlanetRecommendationResponse {
  search_center: string;
  search_radius: number;
  systems_searched: number;
  planets_found: number;
  recommendations: PlanetRecommendationItem[];
  by_planet_type: Record<string, number>;
  by_resource: Record<string, string[]>;
}

// === PI Requirements (Item-Focused) ===

export interface PIRequirementChainNode {
  type_id: number;
  type_name: string;
  tier: number;
  quantity_needed: number;
  children: PIRequirementChainNode[];
  planet_sources?: string[];
}

export interface PIRequirementMaterial {
  type_id: number;
  type_name: string;
  tier: number;
  quantity: number;
  unit_price: number;
  total_cost: number;
  pi_chain: PIRequirementChainNode | null;
}

export interface PIRequirementP0 {
  type_id: number;
  type_name: string;
  quantity: number;
  planet_sources: string[];
}

export interface PIRequirementsResponse {
  type_id: number;
  type_name: string;
  pi_materials: PIRequirementMaterial[];
  p0_summary: PIRequirementP0[];
  total_pi_cost: number;
  total_production_cost: number;
  pi_cost_percentage: number;
}

// === Reaction Requirements ===

export interface ReactionChainNode {
  type_id: number;
  type_name: string;
  reaction_type_id?: number;
  reaction_category?: string;
  quantity_needed: number;
  runs_needed?: number;
  is_reaction_product: boolean;
  is_moon_goo: boolean;
  children: ReactionChainNode[];
}

export interface ReactionRequirementMaterial {
  type_id: number;
  type_name: string;
  quantity: number;
  unit_price: number;
  total_cost: number;
  reaction_category: string;
  reaction_chain: ReactionChainNode | null;
}

export interface MoonGooSummary {
  type_id: number;
  type_name: string;
  quantity: number;
}

export interface ReactionRequirementsResponse {
  type_id: number;
  type_name: string;
  reaction_materials: ReactionRequirementMaterial[];
  moon_goo_summary: MoonGooSummary[];
  total_reaction_cost: number;
  total_production_cost: number;
  reaction_cost_percentage: number;
}

// === PI Chain Planner ===

export interface PIPlanNode {
  id: number;
  plan_id: number;
  type_id: number;
  type_name: string;
  tier: number;
  is_target: boolean;
  soll_qty_per_hour: number;
  character_id: number | null;
  planet_id: number | null;
}

export interface PIPlanEdge {
  id: number;
  plan_id: number;
  source_node_id: number;
  target_node_id: number;
  quantity_ratio: number;
}

export interface PIPlan {
  id: number;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
  nodes: PIPlanNode[];
  edges: PIPlanEdge[];
}

export interface PIPlanListItem {
  id: number;
  name: string;
  status: string;
  node_count: number;
  target_count: number;
  assigned_count: number;
  created_at: string;
  updated_at: string;
}

export interface PIPlanNodeStatus extends PIPlanNode {
  ist_qty_per_hour: number;
  status: 'ok' | 'warning' | 'critical' | 'unassigned';
  delta_percent: number;
}

export interface PIAddTargetResult {
  nodes_created: number;
  nodes_merged: number;
  edges_created: number;
}

// === PI Schematic Formulas ===

export interface PISchematicInput {
  type_id: number;
  type_name: string;
  quantity: number;
}

export interface PISchematicFormula {
  schematic_id: number;
  schematic_name: string;
  cycle_time: number;
  tier: number;
  output_type_id: number;
  output_name: string;
  output_quantity: number;
  inputs: PISchematicInput[];
}

// === Shared ===

export const FACILITY_PRESETS = [
  { id: 'npc', name: 'NPC Station', material: 1.0, time: 1.0 },
  { id: 'raitaru', name: 'Raitaru', material: 0.99, time: 0.85 },
  { id: 'azbel', name: 'Azbel', material: 0.98, time: 0.80 },
  { id: 'sotiyo', name: 'Sotiyo', material: 0.97, time: 0.75 },
  { id: 'tatara', name: 'Tatara (Reactions)', material: 0.98, time: 0.75 },
] as const;

export const PI_PLANET_COLORS: Record<string, string> = {
  temperate: '#3fb950',
  barren: '#d29922',
  oceanic: '#00d4ff',
  ice: '#8b949e',
  gas: '#a855f7',
  lava: '#f85149',
  storm: '#ff6a00',
  plasma: '#ff4444',
};

// === Production Projects ===

export interface ProductionProject {
  id: number;
  creator_character_id: number;
  corporation_id: number | null;
  name: string;
  description: string;
  status: 'draft' | 'active' | 'complete';
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectItem {
  id: number;
  project_id: number;
  type_id: number;
  type_name: string;
  quantity: number;
  me_level: number;
  te_level: number;
  status: 'pending' | 'planned' | 'complete';
  added_at: string;
}

export interface ProjectDetail extends ProductionProject {
  items: ProjectItem[];
}

export interface ProjectMaterialDecision {
  material_type_id: number;
  decision: 'buy' | 'make';
  quantity: number;
}

export interface ShoppingListItem {
  type_id: number;
  type_name: string;
  total_quantity: number;
  unit_price: number;
  total_price: number;
  needed_by: string[];
}

export interface ProjectShoppingList {
  items: ShoppingListItem[];
  total_cost: number;
}

// === PI Empire Analysis ===

export interface EmpireProductionEntry {
  type_id: number;
  type_name: string;
  qty_per_hour: number;
  characters: number[];
}

export interface EmpireFactoryEntry extends EmpireProductionEntry {
  tier: number;
}

export interface EmpireCharacter {
  character_id: number;
  character_name: string;
  colonies: number;
  extractors: number;
  factories: number;
}

export interface EmpireP4Input {
  type_id: number;
  type_name: string;
  tier: number;
  qty_per_hour?: number;
  from_production?: boolean;
  market_price?: number | null;
}

export interface EmpireP4Feasibility {
  type_id: number;
  type_name: string;
  inputs_available: number;
  inputs_total: number;
  feasibility_pct: number;
  available_inputs: EmpireP4Input[];
  missing_inputs: EmpireP4Input[];
  profit_per_hour: number | null;
  roi_percent: number | null;
  sell_price: number | null;
  input_cost: number | null;
  missing_buy_cost: number;
}

export interface EmpireAnalysis {
  characters: EmpireCharacter[];
  production_map: Record<string, EmpireProductionEntry>;
  factory_output: Record<string, EmpireFactoryEntry>;
  p4_feasibility: EmpireP4Feasibility[];
}
