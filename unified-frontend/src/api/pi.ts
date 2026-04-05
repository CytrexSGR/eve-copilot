import { apiClient } from './client'

export interface PIColony {
  id: number
  character_id: number
  planet_id: number
  planet_type: string
  solar_system_id: number
  solar_system_name: string
  upgrade_level: number
  num_pins: number
  last_update: string
  last_sync: string
}

export interface PIPin {
  pin_id: number
  type_id: number
  type_name: string
  latitude: number
  longitude: number
  schematic_id: number | null
  schematic_name: string | null
  product_type_id: number | null
  product_name: string | null
  expiry_time: string | null
  qty_per_cycle: number | null
  cycle_time: number | null
}

export interface PIRoute {
  route_id: number
  source_pin_id: number
  destination_pin_id: number
  content_type_id: number
  content_type_name: string
  quantity: number
  waypoints: number[]
}

export interface PIColonyDetail {
  colony: PIColony
  pins: PIPin[]
  routes: PIRoute[]
}

export interface PIOpportunity {
  type_id: number
  type_name: string
  tier: number
  schematic_id: number
  input_cost: number
  output_value: number
  profit_per_run: number
  profit_per_hour: number
  roi_percent: number
  cycle_time: number
}

export interface PISchematicInput {
  type_id: number
  type_name: string
  quantity: number
}

export interface PISchematic {
  schematic_id: number
  schematic_name: string
  cycle_time: number
  tier: number
  inputs: PISchematicInput[]
  output_type_id: number
  output_name: string
  output_quantity: number
}

export interface PIChainNode {
  type_id: number
  type_name: string
  tier: number
  quantity: number
  schematic_id?: number
  inputs?: PIChainNode[]
}

export interface PIChainResponse {
  target_type_id: number
  target_name: string
  target_tier: number
  chain: PIChainNode
  total_p0_inputs: Array<{ type_id: number; type_name: string; quantity: number }>
}

export interface PIProfitability {
  type_id: number
  type_name: string
  tier: number
  sell_price: number
  production_cost: number
  profit: number
  roi_percent: number
  daily_profit?: number
}

export type MakeOrBuyRecommendation = 'MAKE' | 'BUY'

export interface MakeOrBuyResult {
  type_id: number
  type_name: string
  tier: number
  quantity: number
  market_price: number
  make_cost: number
  recommendation: MakeOrBuyRecommendation
  savings_isk: number
  savings_percent: number
  inputs: PISchematicInput[]
  p0_cost: number | null
}

export type PIProjectStatus = 'planning' | 'active' | 'paused' | 'completed'

export interface PIProjectListItem {
  project_id: number
  character_id: number
  character_name: string | null
  name: string
  target_product_type_id: number | null
  target_product_name: string | null
  target_tier: number | null
  status: PIProjectStatus
  created_at: string
  assigned_count: number
  total_materials: number
}

export interface PIAssignment {
  id: number
  project_id: number
  material_type_id: number
  material_name: string | null
  tier: number
  colony_id: number | null
  colony_name: string | null
  planet_type: string | null
  status: 'active' | 'planned' | 'unassigned'
  is_auto_assigned: boolean
  actual_output_per_hour: number | null
  expected_output_per_hour: number | null
  output_percentage: number | null
  soll_output_per_hour: number | null
  soll_variance_percent: number | null
}

export interface PIProjectDetail {
  project: {
    project_id: number
    character_id: number
    name: string
    strategy: string
    target_product_type_id: number | null
    target_profit_per_hour: number | null
    status: PIProjectStatus
    created_at: string
    updated_at: string
  }
  colonies: Array<{
    id: number
    project_id: number
    planet_id: number
    role: string | null
    expected_output_type_id: number | null
    expected_output_per_hour: number | null
    actual_output_per_hour: number | null
    last_sync: string | null
  }>
  total_expected_output: number
  total_actual_output: number
  variance_percent: number
  expiring_extractors: number
}

export interface PIProjectCreate {
  character_id: number
  name: string
  target_product_type_id: number
  strategy?: string
}

// Empire Profitability Types
export interface EmpireConfiguration {
  total_planets: number
  extraction_planets: number
  factory_planets: number
  characters: number
  poco_tax_rate: number
  region_id: number
}

export interface P4EmpireProfitability {
  type_id: number
  type_name: string
  tier: number
  monthly_output: number
  sell_price: number
  monthly_revenue: number
  monthly_costs: Record<string, number>
  monthly_profit: number
  profit_per_planet: number
  roi_percent: number
  complexity: 'low' | 'medium' | 'high'
  logistics_score: number
  p0_count: number
  planets_needed: Record<string, number>
  recommendation: 'excellent' | 'good' | 'fair' | 'poor'
}

export interface EmpireProfitabilityResponse {
  configuration: EmpireConfiguration
  products: P4EmpireProfitability[]
  comparison: Record<string, any>
}

// Empire Plan Types
export interface EmpirePlanCreate {
  name: string
  target_product_id: number
  target_product_name?: string
  home_system_id?: number
  home_system_name?: string
  total_planets?: number
  extraction_planets?: number
  factory_planets?: number
  poco_tax_rate?: number
}

export interface EmpirePlanAssignmentCreate {
  character_id: number
  character_name: string
  role: 'extractor' | 'factory' | 'hybrid'
  planets: PlanetAssignment[]
}

export interface PlanetAssignment {
  planet_type: string
  purpose: string
  products: string[]
}

export interface EmpirePlanAssignment {
  id: number
  character_id: number
  character_name: string
  role: 'extractor' | 'factory' | 'hybrid'
  planets: PlanetAssignment[]
}

export interface EmpirePlanListItem {
  plan_id: number
  name: string
  target_product_id: number
  target_product_name: string | null
  status: 'planning' | 'active' | 'paused' | 'completed'
  assignment_count: number
  created_at: string
}

export interface EmpirePlanDetail {
  plan_id: number
  name: string
  target_product: {
    id: number
    name: string
  }
  home_system: {
    id: number
    name: string
  } | null
  configuration: {
    total_planets: number
    extraction_planets: number
    factory_planets: number
    poco_tax_rate: number
  }
  status: 'planning' | 'active' | 'paused' | 'completed'
  estimated_monthly_output: number | null
  estimated_monthly_profit: number | null
  assignments: EmpirePlanAssignment[]
  created_at: string
  updated_at: string
}

// Planet Recommendation Types
export interface PlanetRecommendation {
  planet_id: number
  planet_name: string
  planet_type: string
  system_id: number
  system_name: string
  security: number
  jumps_from_home: number
  resources: string[]
  recommendation_score: number
  reason: string
}

export interface PlanetRecommendationResponse {
  search_center: string
  search_radius: number
  systems_searched: number
  planets_found: number
  recommendations: PlanetRecommendation[]
  by_planet_type: Record<string, number>
  by_resource: Record<string, string[]>
}

export interface PlanetSearchParams {
  system_name: string
  jump_range?: number
  planet_type?: string
  required_resources?: string
  min_security?: number
}

// Multi-Character PI Overview Types
export interface PICharacterOverview {
  character_id: number
  character_name: string
  colonies: number
  extractors: number
  factories: number
  max_planets?: number
  used_planets?: number
  free_planets?: number
}

export interface PIProductOutput {
  type_id: number
  type_name: string
  tier: number
  output_per_hour: number
  output_per_day: number
  character_ids: number[]
}

export interface PIExtractorStatus {
  character_id: number
  character_name: string
  planet_id: number
  planet_name: string
  planet_type: string
  product_type_id: number
  product_name: string
  qty_per_cycle: number
  cycle_time: number
  expiry_time: string | null
  hours_remaining: number | null
  status: 'active' | 'expiring' | 'stopped'
}

export interface PIAlert {
  type: 'extractor_depleting' | 'extractor_stopped' | 'storage_full'
  severity: 'warning' | 'critical'
  character_id: number
  character_name: string
  planet_name: string
  message: string
  expiry_time: string | null
}

export interface PIMultiCharacterSummary {
  total_characters: number
  total_colonies: number
  total_extractors: number
  total_factories: number
  total_max_planets?: number
  total_used_planets?: number
  total_free_planets?: number
  characters: PICharacterOverview[]
  products?: PIProductOutput[]
}

export interface PIMultiCharacterDetail {
  summary: PIMultiCharacterSummary
  extractors: PIExtractorStatus[]
  alerts: PIAlert[]
}

// PI Alert Types

export type PIAlertType =
  | 'extractor_depleting'
  | 'extractor_stopped'
  | 'storage_full'
  | 'storage_almost_full'
  | 'factory_idle'
  | 'pickup_reminder'

export type PIAlertSeverity = 'warning' | 'critical'

export interface PIAlertLog {
  id: number
  character_id: number
  alert_type: PIAlertType
  severity: PIAlertSeverity
  planet_id: number | null
  planet_name: string | null
  pin_id: number | null
  product_type_id: number | null
  product_name: string | null
  message: string
  details: Record<string, unknown> | null
  is_read: boolean
  is_acknowledged: boolean
  discord_sent: boolean
  created_at: string
  expires_at: string | null
}

export interface PIAlertConfig {
  character_id: number
  discord_webhook_url: string | null
  discord_enabled: boolean
  extractor_warning_hours: number
  extractor_critical_hours: number
  storage_warning_percent: number
  storage_critical_percent: number
  alert_extractor_depleting: boolean
  alert_extractor_stopped: boolean
  alert_storage_full: boolean
  alert_factory_idle: boolean
  alert_pickup_reminder: boolean
  pickup_reminder_hours: number
}

export interface PIAlertConfigUpdate {
  discord_webhook_url?: string | null
  discord_enabled?: boolean
  extractor_warning_hours?: number
  extractor_critical_hours?: number
  storage_warning_percent?: number
  storage_critical_percent?: number
  alert_extractor_depleting?: boolean
  alert_extractor_stopped?: boolean
  alert_storage_full?: boolean
  alert_factory_idle?: boolean
  alert_pickup_reminder?: boolean
  pickup_reminder_hours?: number
}

// ==================== Logistics Types ====================

export interface PIPickupStop {
  character_id: number
  character_name: string
  system_id: number
  system_name: string
  planets: number
  estimated_time_minutes: number
  materials_volume_m3: number
}

export interface PIPickupSchedule {
  optimal_frequency_hours: number
  next_pickup: string | null
  route: PIPickupStop[]
  total_time_minutes: number
  total_jumps: number
  total_cargo_volume_m3: number
}

export interface PITransferMaterial {
  type_id?: number
  type_name: string
  quantity: number
  volume_m3: number
}

export interface PITransfer {
  id: number
  from_character_id: number
  from_character_name: string
  to_character_id: number
  to_character_name: string
  materials: PITransferMaterial[]
  total_volume_m3: number
  method: 'contract' | 'direct_trade' | 'corp_hangar'
  station_id: number | null
  station_name: string | null
  frequency_hours: number
}

export interface PIHubStation {
  station_id: number
  station_name: string
  system_id: number
  system_name: string
  security: number
  avg_jumps_to_colonies: number
  reason: string
}

export interface PILogisticsPlan {
  plan_id: number
  pickup_schedule: PIPickupSchedule
  transfers: PITransfer[]
  hub_station: PIHubStation
  estimated_weekly_trips: number
  estimated_weekly_time_hours: number
}

export const piApi = {
  /**
   * Get all colonies for a character
   */
  getColonies: async (characterId: number): Promise<PIColony[]> => {
    const response = await apiClient.get<PIColony[]>(`/pi/characters/${characterId}/colonies`)
    return response.data
  },

  /**
   * Get colony detail with pins and routes
   */
  getColonyDetail: async (characterId: number, planetId: number): Promise<PIColonyDetail> => {
    const response = await apiClient.get<PIColonyDetail>(
      `/pi/characters/${characterId}/colonies/${planetId}`
    )
    return response.data
  },

  /**
   * Sync colonies from ESI
   */
  syncColonies: async (characterId: number): Promise<{ synced: number }> => {
    const response = await apiClient.post<{ synced: number }>(
      `/pi/characters/${characterId}/colonies/sync`
    )
    return response.data
  },

  /**
   * Get PI opportunities (profitable products)
   */
  getOpportunities: async (tier?: number, limit: number = 20): Promise<PIOpportunity[]> => {
    const params: Record<string, string | number> = { limit }
    if (tier !== undefined) params.tier = tier
    const response = await apiClient.get<PIOpportunity[]>('/pi/opportunities', { params })
    return response.data
  },

  /**
   * Get PI schematics/formulas
   */
  getSchematics: async (tier?: number): Promise<PISchematic[]> => {
    const params: Record<string, number> = {}
    if (tier !== undefined) params.tier = tier
    const response = await apiClient.get<PISchematic[]>('/pi/formulas', { params })
    return response.data
  },

  /**
   * Get production chain for a PI product
   */
  getProductionChain: async (typeId: number): Promise<PIChainResponse> => {
    const response = await apiClient.get<PIChainResponse>(`/pi/chain/${typeId}`)
    return response.data
  },

  /**
   * Get profitability for a specific PI product
   */
  getProfitability: async (typeId: number): Promise<PIProfitability> => {
    const response = await apiClient.get<PIProfitability>(`/pi/profitability/${typeId}`)
    return response.data
  },

  /**
   * Get character PI summary
   */
  getCharacterSummary: async (characterId: number): Promise<{
    character_id: number
    total_colonies: number
    total_pins: number
    planets: PIColony[]
  }> => {
    const response = await apiClient.get(`/pi/characters/${characterId}/summary`)
    return response.data
  },

  /**
   * Analyze make-or-buy decision for a PI product
   */
  analyzeMakeOrBuy: async (
    typeId: number,
    quantity: number = 1,
    regionId: number = 10000002,
    includeP0Cost: boolean = false
  ): Promise<MakeOrBuyResult> => {
    const params = new URLSearchParams({
      quantity: quantity.toString(),
      region_id: regionId.toString(),
      include_p0_cost: includeP0Cost.toString(),
    })
    const response = await apiClient.get<MakeOrBuyResult>(`/pi/make-or-buy/${typeId}?${params}`)
    return response.data
  },

  /**
   * Search PI schematics by name
   */
  searchSchematics: async (query: string): Promise<PISchematic[]> => {
    const response = await apiClient.get<PISchematic[]>('/pi/formulas/search', {
      params: { q: query },
    })
    return response.data
  },

  /**
   * Get all PI projects
   */
  getProjects: async (characterId?: number, status?: PIProjectStatus): Promise<PIProjectListItem[]> => {
    const params: Record<string, string | number> = {}
    if (characterId) params.character_id = characterId
    if (status) params.status = status
    const response = await apiClient.get<PIProjectListItem[]>('/pi/projects', { params })
    return response.data
  },

  /**
   * Create a new PI project
   */
  createProject: async (data: PIProjectCreate): Promise<{ project_id: number }> => {
    const response = await apiClient.post('/pi/projects', data)
    return response.data
  },

  /**
   * Get PI project detail
   */
  getProject: async (projectId: number): Promise<PIProjectDetail> => {
    const response = await apiClient.get<PIProjectDetail>(`/pi/projects/${projectId}`)
    return response.data
  },

  /**
   * Update project status
   */
  updateProjectStatus: async (projectId: number, status: PIProjectStatus): Promise<void> => {
    await apiClient.patch(`/pi/projects/${projectId}/status`, null, {
      params: { status },
    })
  },

  /**
   * Delete a project
   */
  deleteProject: async (projectId: number): Promise<void> => {
    await apiClient.delete(`/pi/projects/${projectId}`)
  },

  /**
   * Get project assignments
   */
  getAssignments: async (projectId: number): Promise<PIAssignment[]> => {
    const response = await apiClient.get<PIAssignment[]>(`/pi/projects/${projectId}/assignments`)
    return response.data
  },

  /**
   * Update material assignment
   */
  updateAssignment: async (projectId: number, materialTypeId: number, colonyId: number | null): Promise<void> => {
    await apiClient.put(`/pi/projects/${projectId}/assignments/${materialTypeId}`, {
      colony_id: colonyId,
    })
  },

  /**
   * Auto-assign all materials
   */
  autoAssign: async (projectId: number): Promise<PIAssignment[]> => {
    const response = await apiClient.post<PIAssignment[]>(`/pi/projects/${projectId}/assignments/auto`)
    return response.data
  },

  /**
   * Sync project from ESI
   */
  syncProject: async (projectId: number): Promise<PIProjectDetail> => {
    const response = await apiClient.post<PIProjectDetail>(`/pi/projects/${projectId}/sync`)
    return response.data
  },

  /**
   * Get empire profitability analysis for P4 products
   */
  getEmpireProfitability: async (params?: {
    total_planets?: number
    extraction_planets?: number
    factory_planets?: number
    region_id?: number
    poco_tax?: number
  }): Promise<EmpireProfitabilityResponse> => {
    const response = await apiClient.get<EmpireProfitabilityResponse>(
      '/pi/profitability/empire',
      { params }
    )
    return response.data
  },

  // Empire Plans

  /**
   * Create a new empire plan
   */
  createEmpirePlan: async (plan: EmpirePlanCreate): Promise<{ plan_id: number; status: string }> => {
    const response = await apiClient.post('/pi/empire/plans', plan)
    return response.data
  },

  /**
   * List all empire plans
   */
  listEmpirePlans: async (status?: string): Promise<EmpirePlanListItem[]> => {
    const params = status ? { status } : {}
    const response = await apiClient.get<EmpirePlanListItem[]>('/pi/empire/plans', { params })
    return response.data
  },

  /**
   * Get empire plan details
   */
  getEmpirePlan: async (planId: number): Promise<EmpirePlanDetail> => {
    const response = await apiClient.get<EmpirePlanDetail>(`/pi/empire/plans/${planId}`)
    return response.data
  },

  /**
   * Add character assignment to empire plan
   */
  addPlanAssignment: async (
    planId: number,
    assignment: EmpirePlanAssignmentCreate
  ): Promise<{ assignment_id: number; status: string }> => {
    const response = await apiClient.post(`/pi/empire/plans/${planId}/assignments`, assignment)
    return response.data
  },

  /**
   * Update empire plan status
   */
  updatePlanStatus: async (
    planId: number,
    status: 'planning' | 'active' | 'paused' | 'completed'
  ): Promise<{ status: string }> => {
    const response = await apiClient.patch(`/pi/empire/plans/${planId}/status`, null, {
      params: { status }
    })
    return response.data
  },

  /**
   * Delete an empire plan
   */
  deleteEmpirePlan: async (planId: number): Promise<{ status: string }> => {
    const response = await apiClient.delete(`/pi/empire/plans/${planId}`)
    return response.data
  },

  // Planet Recommendations

  /**
   * Find planets for PI within jump range of a system
   */
  recommendPlanets: async (params: PlanetSearchParams): Promise<PlanetRecommendationResponse> => {
    const response = await apiClient.get<PlanetRecommendationResponse>('/pi/planets/recommend', { params })
    return response.data
  },

  // Multi-Character Overview

  /**
   * Get multi-character PI summary
   */
  getMultiCharacterSummary: async (characterIds: number[]): Promise<PIMultiCharacterSummary> => {
    const response = await apiClient.get<PIMultiCharacterSummary>(
      '/pi/multi-character/summary',
      { params: { character_ids: characterIds.join(',') } }
    )
    return response.data
  },

  /**
   * Get multi-character PI detail with extractors and alerts
   */
  getMultiCharacterDetail: async (characterIds: number[]): Promise<PIMultiCharacterDetail> => {
    const response = await apiClient.get<PIMultiCharacterDetail>(
      '/pi/multi-character/detail',
      { params: { character_ids: characterIds.join(',') } }
    )
    return response.data
  },

  /**
   * Sync all colonies for multiple characters
   */
  syncMultiCharacterColonies: async (characterIds: number[]): Promise<{ synced: number; failed: number }> => {
    const results = await Promise.all(
      characterIds.map(id =>
        apiClient.post(`/pi/characters/${id}/colonies/sync`)
          .then(() => ({ success: true }))
          .catch(() => ({ success: false }))
      )
    )
    return {
      synced: results.filter(r => r.success).length,
      failed: results.filter(r => !r.success).length
    }
  },

  /**
   * Get logistics plan for an empire
   */
  getEmpireLogistics: async (planId: number, frequencyHours: number = 48): Promise<PILogisticsPlan> => {
    const response = await apiClient.get<PILogisticsPlan>(
      `/pi/empire/plans/${planId}/logistics`,
      { params: { frequency_hours: frequencyHours } }
    )
    return response.data
  },

  // Alert methods

  getAlerts: async (
    characterId?: number,
    unreadOnly: boolean = false,
    limit: number = 50
  ): Promise<PIAlertLog[]> => {
    const params = new URLSearchParams()
    if (characterId) params.append('character_id', characterId.toString())
    if (unreadOnly) params.append('unread_only', 'true')
    params.append('limit', limit.toString())
    const response = await apiClient.get<PIAlertLog[]>(`/pi/alerts?${params}`)
    return response.data
  },

  markAlertsRead: async (alertIds: number[]): Promise<{ status: string; updated: number }> => {
    const response = await apiClient.post('/pi/alerts/read', alertIds)
    return response.data
  },

  getAlertConfig: async (characterId: number): Promise<PIAlertConfig> => {
    const response = await apiClient.get<PIAlertConfig>(`/pi/alerts/config/${characterId}`)
    return response.data
  },

  updateAlertConfig: async (
    characterId: number,
    config: PIAlertConfigUpdate
  ): Promise<PIAlertConfig> => {
    const response = await apiClient.put<PIAlertConfig>(`/pi/alerts/config/${characterId}`, config)
    return response.data
  },
}
