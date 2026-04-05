import { api } from './client';
import type {
  ProductionSimulation, QuickProfitCheck, CompareResult, MaterialChain,
  ManufacturingOpportunity, EconomicsDetail, RegionEconomics,
  InventionDetail, DecryptorComparisonResult,
  ReactionFormula, ReactionProfitability,
  PICharacterSummary, PIColonyGraph, PIProfitability, PIAdvisorResponse,
  PlanetRecommendationResponse,
  PIRequirementsResponse,
  ReactionRequirementsResponse,
  ProductionProject, ProjectDetail, ProjectItem, ProjectMaterialDecision, ProjectShoppingList,
  PIPlan, PIPlanListItem, PIPlanNodeStatus, PIAddTargetResult, PIPlanNode,
  PISchematicFormula,
  EmpireAnalysis,
} from '../../types/production';

// Map backend simulate response to frontend ProductionSimulation shape
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformSimulation(raw: any): ProductionSimulation {
  const mapMaterial = (m: { type_id: number; name: string; quantity: number; unit_price: number; total_cost: number }) => ({
    material_id: m.type_id,
    material_name: m.name,
    quantity: m.quantity,
    unit_price: m.unit_price,
    total_cost: m.total_cost,
  });
  return {
    type_id: raw.product?.type_id ?? 0,
    type_name: raw.product?.name ?? '',
    runs: raw.parameters?.runs ?? 1,
    me: raw.parameters?.me_level ?? 0,
    te: raw.parameters?.te_level ?? 0,
    bom: (raw.bill_of_materials?.materials ?? []).map(mapMaterial),
    financial_analysis: {
      production_cost: raw.financials?.build_cost ?? 0,
      sell_price: raw.financials?.revenue ?? 0,
      profit: raw.financials?.profit ?? 0,
      roi: raw.financials?.roi ?? 0,
    },
    production_time: {
      base_time: raw.production_time?.base_seconds ?? 0,
      te_factor: 1 - ((raw.parameters?.te_level ?? 0) / 100),
      actual_time: raw.production_time?.actual_seconds ?? 0,
    },
    shopping_list: (raw.shopping_list ?? []).map(mapMaterial),
    warnings: raw.warnings ?? [],
  };
}

// Map string facility names to DB integer IDs
const FACILITY_NAME_TO_ID: Record<string, number> = {
  npc: 1,
  raitaru: 145,
  azbel: 147,
  sotiyo: 148,
  tatara: 150,
};

// --- Calculator ---
export const productionApi = {
  simulate: (params: {
    type_id: number;
    runs?: number;
    me?: number;
    te?: number;
    region_id?: number;
  }) => api.post('/production/simulate', params).then(r => transformSimulation(r.data)),

  simulateGet: (typeId: number, params: { runs?: number; me?: number; te?: number; region_id?: number } = {}) =>
    api.get(`/production/simulate/${typeId}`, { params }).then(r => transformSimulation(r.data)),

  profitCheck: (typeId: number, params: { runs?: number; me?: number; region_id?: number } = {}) =>
    api.get<QuickProfitCheck>(`/production/profit-check/${typeId}`, { params }).then(r => r.data),

  getChain: (typeId: number, params: { quantity?: number; format?: string } = {}) =>
    api.get<MaterialChain>(`/production/chains/${typeId}`, { params }).then(r => r.data),

  getMaterials: (typeId: number, params: { me?: number; runs?: number } = {}) =>
    api.get<{ type_id: number; materials: Array<{ material_id: number; material_name: string; base_qty: number; adjusted_qty: number }> }>(
      `/production/chains/${typeId}/materials`, { params }
    ).then(r => r.data),

  compare: (params: {
    type_id: number;
    facility_ids: string[];
    me: number;
    te: number;
    runs: number;
    region_id?: number;
  }) => {
    const intIds = params.facility_ids.map(id => FACILITY_NAME_TO_ID[id] ?? parseInt(id, 10)).filter(id => !isNaN(id));
    return api.post<CompareResult>('/production/compare', { ...params, facility_ids: intIds }).then(r => r.data);
  },
};

// --- Economics ---
export const economicsApi = {
  getOpportunities: (params: { region_id?: number; min_roi?: number; min_profit?: number; min_volume?: number; limit?: number } = {}) =>
    api.get<{ opportunities: ManufacturingOpportunity[] }>('/production/economics/opportunities', { params }).then(r => r.data),

  getDetail: (typeId: number, params: { region_id?: number; me?: number; te?: number } = {}) =>
    api.get<EconomicsDetail>(`/production/economics/${typeId}`, { params }).then(r => r.data),

  getRegions: (typeId: number) =>
    api.get<RegionEconomics>(`/production/economics/${typeId}/regions`).then(r => r.data),
};

// --- Invention ---
export const inventionApi = {
  getDetail: (typeId: number, params: { decryptor_type_id?: number; region_id?: number } = {}) =>
    api.get<InventionDetail>(`/production/invention/${typeId}`, { params }).then(r => r.data),

  getDecryptors: (typeId: number, params: { region_id?: number } = {}) =>
    api.get<DecryptorComparisonResult>(`/production/invention/${typeId}/decryptors`, { params }).then(r => r.data),
};

// --- Reactions ---
export const reactionsApi = {
  getAll: () =>
    api.get<ReactionFormula[]>('/reactions').then(r => r.data),

  search: (q: string) =>
    api.get<ReactionFormula[]>('/reactions/search', { params: { q } }).then(r => r.data),

  getDetail: (reactionTypeId: number) =>
    api.get<ReactionFormula>(`/reactions/${reactionTypeId}`).then(r => r.data),

  getProfit: (reactionTypeId: number, params: { region_id?: number; time_bonus?: number; material_bonus?: number } = {}) =>
    api.get<ReactionProfitability>(`/reactions/${reactionTypeId}/profit`, { params }).then(r => r.data),

  getProfitable: (params: { min_roi?: number; limit?: number; region_id?: number; time_bonus?: number; material_bonus?: number } = {}) =>
    api.get<ReactionProfitability[]>('/reactions/profitable', { params }).then(r => r.data),

  getItemReactionRequirements: (typeId: number) =>
    api.get<ReactionRequirementsResponse>(`/production/reaction-requirements/${typeId}`).then(r => r.data),
};

// --- PI ---
export const piApi = {
  getCharacterSummary: (characterId: number) =>
    api.get<PICharacterSummary>(`/pi/characters/${characterId}/summary`).then(r => r.data),

  getColonyGraph: (characterId: number, planetId: number) =>
    api.get<PIColonyGraph>(`/pi/characters/${characterId}/colonies/${planetId}/graph`).then(r => r.data),

  getOpportunities: (params: { min_roi?: number; min_profit?: number; limit?: number } = {}) =>
    api.get<PIProfitability[]>('/pi/opportunities', { params }).then(r => r.data),

  getProfitability: (typeId: number, params: { region_id?: number } = {}) =>
    api.get<PIProfitability>(`/pi/profitability/${typeId}`, { params }).then(r => r.data),

  getAdvisor: (characterId: number, params: { tier?: number; limit?: number; region_id?: number } = {}) =>
    api.get<PIAdvisorResponse>(`/pi/advisor/${characterId}`, { params }).then(r => r.data),

  recommendPlanets: (params: { system_name: string; jump_range?: number; planet_type?: string; min_security?: number }) =>
    api.get<PlanetRecommendationResponse>('/pi/planets/recommend', { params }).then(r => r.data),

  getItemPIRequirements: (typeId: number) =>
    api.get<PIRequirementsResponse>(`/production/pi-requirements/${typeId}`).then(r => r.data),

  // Formulas (all schematics)
  getFormulas: (tier?: number) =>
    api.get<PISchematicFormula[]>('/pi/formulas', { params: tier ? { tier } : {} }).then(r => r.data),

  // Chain Planner
  createPlan: (name: string) =>
    api.post<PIPlan>('/pi/plans', { name }).then(r => r.data),

  listPlans: (status?: string) =>
    api.get<PIPlanListItem[]>('/pi/plans', { params: status ? { status } : {} }).then(r => r.data),

  getPlan: (planId: number) =>
    api.get<PIPlan>(`/pi/plans/${planId}`).then(r => r.data),

  deletePlan: (planId: number) =>
    api.delete(`/pi/plans/${planId}`).then(r => r.data),

  updatePlanStatus: (planId: number, status: string) =>
    api.patch(`/pi/plans/${planId}/status`, { status }).then(r => r.data),

  addTarget: (planId: number, typeId: number, quantityPerHour: number = 1.0) =>
    api.post<PIAddTargetResult>(`/pi/plans/${planId}/targets`, {
      type_id: typeId, quantity_per_hour: quantityPerHour,
    }).then(r => r.data),

  removeTarget: (planId: number, typeId: number) =>
    api.delete(`/pi/plans/${planId}/targets/${typeId}`).then(r => r.data),

  assignNode: (planId: number, nodeId: number, characterId: number | null, planetId: number | null) =>
    api.patch<PIPlanNode>(`/pi/plans/${planId}/nodes/${nodeId}/assign`, {
      character_id: characterId, planet_id: planetId,
    }).then(r => r.data),

  getStatusCheck: (planId: number) =>
    api.get<PIPlanNodeStatus[]>(`/pi/plans/${planId}/status-check`).then(r => r.data),

  getEmpireAnalysis: (characterIds: number[], regionId?: number) =>
    api.get<EmpireAnalysis>("/pi/empire/analysis", {
      params: { character_ids: characterIds.join(","), ...(regionId ? { region_id: regionId } : {}) },
    }).then(r => r.data),
};

// --- Projects ---
export const projectApi = {
  list: (characterId: number, corporationId?: number) =>
    api.get<ProductionProject[]>('/production/projects', {
      params: { character_id: characterId, ...(corporationId ? { corporation_id: corporationId } : {}) },
    }).then(r => r.data),

  create: (data: { creator_character_id: number; name: string; description?: string; corporation_id?: number }) =>
    api.post<ProjectDetail>('/production/projects', data).then(r => r.data),

  get: (projectId: number) =>
    api.get<ProjectDetail>(`/production/projects/${projectId}`).then(r => r.data),

  update: (projectId: number, data: { name?: string; description?: string; status?: string }) =>
    api.put<ProjectDetail>(`/production/projects/${projectId}`, data).then(r => r.data),

  delete: (projectId: number) =>
    api.delete(`/production/projects/${projectId}`).then(r => r.data),

  addItem: (projectId: number, data: { type_id: number; quantity?: number; me_level?: number; te_level?: number }) =>
    api.post<ProjectItem>(`/production/projects/${projectId}/items`, data).then(r => r.data),

  updateItem: (projectId: number, itemId: number, data: { quantity?: number; me_level?: number; te_level?: number; status?: string }) =>
    api.put<ProjectItem>(`/production/projects/${projectId}/items/${itemId}`, data).then(r => r.data),

  deleteItem: (projectId: number, itemId: number) =>
    api.delete(`/production/projects/${projectId}/items/${itemId}`).then(r => r.data),

  getDecisions: (itemId: number) =>
    api.get<ProjectMaterialDecision[]>(`/production/projects/items/${itemId}/decisions`).then(r => r.data),

  saveDecisions: (itemId: number, decisions: ProjectMaterialDecision[]) =>
    api.put<ProjectMaterialDecision[]>(`/production/projects/items/${itemId}/decisions`, { decisions }).then(r => r.data),

  getShoppingList: (projectId: number) =>
    api.get<ProjectShoppingList>(`/production/projects/${projectId}/shopping-list`).then(r => r.data),
};
