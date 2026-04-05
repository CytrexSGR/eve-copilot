import { api } from '../api';

// Types
export interface PICharacter {
  character_id: number;
  character_name: string;
}

export interface PIColony {
  planet_id: number;
  planet_type: string;
  solar_system_id: number;
  solar_system_name: string;
  upgrade_level: number;
  num_pins: number;
  last_update: string;
}

export interface PIPin {
  pin_id: number;
  type_id: number;
  type_name: string;
  latitude: number;
  longitude: number;
  expiry_time?: string | null;
  schematic_id?: number | null;
  schematic_name?: string | null;
  product_type_id?: number | null;
  product_name?: string | null;
  qty_per_cycle?: number | null;
  cycle_time?: number | null;
}

export interface PIRoute {
  route_id: number;
  source_pin_id: number;
  destination_pin_id: number;
  content_type_id: number;
  content_name: string;
  quantity: number;
}

export interface PIColonyDetailResponse {
  colony: PIColony;
  pins: PIPin[];
  routes: PIRoute[];
}

export interface PIProfitability {
  type_id: number;
  type_name: string;
  tier: number;
  schematic_id: number;
  cycle_time: number;
  output_quantity: number;
  input_cost: number;
  output_value: number;
  profit_per_run: number;
  profit_per_hour: number;
  roi_percent: number;
}

export interface PIChainNode {
  type_id: number;
  type_name: string;
  tier: number;
  quantity_needed: number;
  schematic_id?: number;
  children: PIChainNode[];
}

// API Functions
export async function getCharacters(): Promise<PICharacter[]> {
  const response = await api.get('/api/auth/characters');
  return response.data.characters;
}

export async function getColonies(characterId: number): Promise<PIColony[]> {
  const response = await api.get(`/api/pi/characters/${characterId}/colonies`);
  return response.data;
}

export async function syncColonies(characterId: number): Promise<PIColony[]> {
  const response = await api.post(`/api/pi/characters/${characterId}/colonies/sync`);
  return response.data;
}

export async function getColonyDetail(characterId: number, planetId: number): Promise<PIColonyDetailResponse> {
  const response = await api.get(`/api/pi/characters/${characterId}/colonies/${planetId}`);
  return response.data;
}

export async function getOpportunities(params?: {
  tier?: number;
  limit?: number;
  min_roi?: number;
}): Promise<PIProfitability[]> {
  const response = await api.get('/api/pi/opportunities', { params });
  return response.data;
}

export async function getProductionChain(typeId: number): Promise<PIChainNode> {
  const response = await api.get(`/api/pi/chain/${typeId}`);
  return response.data;
}

export async function getProfitability(typeId: number): Promise<PIProfitability> {
  const response = await api.get(`/api/pi/profitability/${typeId}`);
  return response.data;
}

export interface PISystem {
  system_id: number;
  system_name: string;
  region_id: number;
  region_name: string;
  security: number;
  planet_types: string[];
  planet_count: number;
}

export async function searchSystems(params?: {
  region_id?: number;
  min_security?: number;
  planet_types?: string[];
  limit?: number;
}): Promise<PISystem[]> {
  const queryParams: Record<string, string> = {};
  if (params?.region_id) queryParams.region_id = String(params.region_id);
  if (params?.min_security !== undefined) queryParams.min_security = String(params.min_security);
  if (params?.planet_types?.length) queryParams.planet_types = params.planet_types.join(',');
  if (params?.limit) queryParams.limit = String(params.limit);

  const response = await api.get('/api/pi/systems/search', { params: queryParams });
  return response.data;
}

// Optimizer Types
export interface PICharacterSkills {
  character_id: number;
  interplanetary_consolidation: number;
  command_center_upgrades: number;
  max_planets: number;
  updated_at?: string;
}

export interface PICharacterSlots {
  character_id: number;
  character_name: string;
  max_planets: number;
  used_planets: number;
  free_planets: number;
}

export interface PIRecommendation {
  type_id: number;
  type_name: string;
  tier: number;
  profit_per_hour: number;
  roi_percent: number;
  required_planet_types: string[];
  planets_needed: number;
  complexity_score: number;
  feasible: boolean;
  reason?: string;
}

export interface PIProject {
  project_id: number;
  character_id: number;
  name: string;
  strategy: string;
  target_product_type_id?: number;
  target_profit_per_hour?: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface PIProjectColony {
  id: number;
  project_id: number;
  planet_id: number;
  planet_type?: string;
  role?: string;
  expected_output_type_id?: number;
  expected_output_per_hour?: number;
  actual_output_per_hour?: number;
  last_sync?: string;
}

export interface PIProjectDetail {
  project: PIProject;
  colonies: PIProjectColony[];
  total_expected_output: number;
  total_actual_output: number;
  variance_percent: number;
  expiring_extractors: number;
}

export interface PISystemPlanet {
  planet_id: number;
  system_id: number;
  system_name: string;
  planet_type: string;
  planet_index: number;
}

// Optimizer API Functions
export async function getCharacterSkills(characterId: number): Promise<PICharacterSkills> {
  const response = await api.get(`/api/pi/characters/${characterId}/skills`);
  return response.data;
}

export async function syncCharacterSkills(characterId: number): Promise<PICharacterSkills> {
  const response = await api.post(`/api/pi/characters/${characterId}/skills/sync`);
  return response.data;
}

export async function getCharacterSlots(characterIds: number[]): Promise<PICharacterSlots[]> {
  const response = await api.get('/api/pi/slots', {
    params: { character_ids: characterIds.join(',') }
  });
  return response.data;
}

export async function getOptimizationRecommendations(params: {
  character_ids: number[];
  system_id?: number;
  mode?: 'market_driven' | 'vertical';
  limit?: number;
  region_id?: number;
}): Promise<PIRecommendation[]> {
  const queryParams: Record<string, string> = {
    character_ids: params.character_ids.join(','),
    system_id: String(params.system_id || 30002811),
    mode: params.mode || 'market_driven',
  };
  if (params.limit !== undefined) queryParams.limit = String(params.limit);
  if (params.region_id !== undefined) queryParams.region_id = String(params.region_id);

  const response = await api.get('/api/pi/optimize', { params: queryParams });
  return response.data;
}

export async function getSystemPlanets(systemId: number): Promise<PISystemPlanet[]> {
  const response = await api.get(`/api/pi/systems/${systemId}/planets`);
  return response.data;
}

export async function getProjects(params?: {
  character_id?: number;
  status?: string;
}): Promise<PIProject[]> {
  const response = await api.get('/api/pi/projects', { params });
  return response.data;
}

export async function createProject(params: {
  character_id: number;
  name: string;
  strategy: string;
  target_product_type_id?: number;
  target_profit_per_hour?: number;
}): Promise<PIProject> {
  const response = await api.post('/api/pi/projects', params);
  return response.data;
}

export async function getProjectDetail(projectId: number): Promise<PIProjectDetail> {
  const response = await api.get(`/api/pi/projects/${projectId}`);
  return response.data;
}

export async function updateProjectStatus(projectId: number, status: string): Promise<PIProject> {
  const response = await api.patch(`/api/pi/projects/${projectId}/status`, { status });
  return response.data;
}

export async function deleteProject(projectId: number): Promise<void> {
  await api.delete(`/api/pi/projects/${projectId}`);
}

export async function syncProjectTracking(projectId: number): Promise<PIProjectDetail> {
  const response = await api.post(`/api/pi/projects/${projectId}/sync`);
  return response.data;
}

// Material Assignment Types
export interface PIMaterialAssignment {
  id: number;
  project_id: number;
  material_type_id: number;
  material_name?: string;
  tier: number;
  colony_id?: number;
  colony_name?: string;
  planet_type?: string;
  status: 'active' | 'planned' | 'unassigned';
  is_auto_assigned: boolean;
  // Output tracking fields (from ESI sync)
  actual_output_per_hour?: number | null;
  expected_output_per_hour?: number | null;
  output_percentage?: number | null;
  // SOLL planning fields
  soll_output_per_hour?: number | null;
  soll_notes?: string | null;
  soll_variance_percent?: number | null;
}

// SOLL Planning Types
export interface PIProjectSollSummary {
  project_id: number;
  total_soll_output: number;
  total_ist_output: number;
  overall_variance_percent: number;
  materials_on_target: number;
  materials_under_target: number;
  materials_over_target: number;
  materials_no_soll: number;
}

export interface PIMultiCharacterSummary {
  total_characters: number;
  total_colonies: number;
  total_extractors: number;
  total_factories: number;
  total_max_planets: number;
  total_used_planets: number;
  total_free_planets: number;
  products: Array<{
    type_id: number;
    type_name: string;
    output_per_hour: number;
    character_count: number;
  }>;
  characters: Array<{
    character_id: number;
    character_name: string;
    colonies: number;
    extractors: number;
    factories: number;
    max_planets: number;
    used_planets: number;
  }>;
}

export interface PIPlanetRecommendation {
  target_type_id: number;
  target_name: string;
  p0_requirements: Array<{
    material_type_id: number;
    material_name: string;
    quantity_needed: number;
    available_planet_types: string[];
    is_covered: boolean;
  }>;
  current_planet_types: string[];
  covered_materials: string[];
  missing_materials: string[];
  recommendations: Array<{
    planet_type: string;
    covers_materials: string[];
    coverage_count: number;
    priority: 'high' | 'medium' | 'low';
  }>;
}

// API Functions for Assignments
export async function getProjectAssignments(projectId: number): Promise<PIMaterialAssignment[]> {
  const response = await api.get(`/api/pi/projects/${projectId}/assignments`);
  return response.data;
}

export async function updateMaterialAssignment(
  projectId: number,
  materialTypeId: number,
  colonyId: number | null
): Promise<void> {
  await api.put(`/api/pi/projects/${projectId}/assignments/${materialTypeId}`, {
    colony_id: colonyId
  });
}

export async function autoAssignMaterials(projectId: number): Promise<PIMaterialAssignment[]> {
  const response = await api.post(`/api/pi/projects/${projectId}/assignments/auto`);
  return response.data;
}

// SOLL Planning API
export async function updateMaterialSoll(
  projectId: number,
  materialTypeId: number,
  sollOutputPerHour: number | null,
  sollNotes?: string | null
): Promise<void> {
  await api.patch(`/api/pi/projects/${projectId}/assignments/${materialTypeId}/soll`, {
    soll_output_per_hour: sollOutputPerHour,
    soll_notes: sollNotes
  });
}

export async function getProjectSollSummary(projectId: number): Promise<PIProjectSollSummary> {
  const response = await api.get(`/api/pi/projects/${projectId}/soll-summary`);
  return response.data;
}

// Multi-Character API
export async function getMultiCharacterSummary(characterIds: number[]): Promise<PIMultiCharacterSummary> {
  const response = await api.get('/api/pi/multi-character/summary', {
    params: { character_ids: characterIds.join(',') }
  });
  return response.data;
}

// Planet Recommendations API
export async function getPlanetRecommendations(
  targetTypeId: number,
  currentTypes?: string[]
): Promise<PIPlanetRecommendation> {
  const params: Record<string, string> = {};
  if (currentTypes?.length) params.current_types = currentTypes.join(',');

  const response = await api.get(`/api/pi/recommendations/planets/${targetTypeId}`, { params });
  return response.data;
}

// Make-or-Buy Analysis Types
export type MakeOrBuyRecommendation = 'MAKE' | 'BUY';

export interface PISchematicInput {
  type_id: number;
  type_name: string;
  quantity: number;
}

export interface MakeOrBuyResult {
  type_id: number;
  type_name: string;
  tier: number;
  quantity: number;
  market_price: number;
  make_cost: number;
  recommendation: MakeOrBuyRecommendation;
  savings_isk: number;
  savings_percent: number;
  inputs: PISchematicInput[];
  p0_cost: number | null;
}

// Make-or-Buy Analysis API Functions
export async function analyzeMakeOrBuy(
  typeId: number,
  quantity: number = 1,
  regionId: number = 10000002,
  includeP0Cost: boolean = false
): Promise<MakeOrBuyResult> {
  const params = new URLSearchParams({
    quantity: quantity.toString(),
    region_id: regionId.toString(),
    include_p0_cost: includeP0Cost.toString(),
  });
  const response = await api.get(`/api/pi/make-or-buy/${typeId}?${params}`);
  return response.data;
}

export async function analyzeMakeOrBuyBatch(
  items: Array<{ type_id: number; quantity?: number }>,
  regionId: number = 10000002
): Promise<MakeOrBuyResult[]> {
  const response = await api.post('/api/pi/make-or-buy/batch', {
    items,
    region_id: regionId,
  });
  return response.data;
}
