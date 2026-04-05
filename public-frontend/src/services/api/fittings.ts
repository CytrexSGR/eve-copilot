import { api } from './client';
import type {
  ESIFitting, CustomFitting, SaveFittingRequest,
  FittingItem, FittingStats, ShipSummary, ShipDetail,
  ModuleSummary, ChargeSummary, FittingChargeMap, GroupSummary,
  MarketGroupNode,
  FighterInput, FleetBoostInput, ProjectedEffectInput,
  T3DMode, BoostPreset, BuffDefinition,
} from '../../types/fittings';

// --- Fittings CRUD ---
export const fittingApi = {
  getCharacterFittings: (characterId: number) =>
    api.get<ESIFitting[]>(`/fittings/${characterId}`).then(r => r.data),

  getFittingStats: (shipTypeId: number, items: FittingItem[], charges?: FittingChargeMap, characterId?: number, targetProfile?: string, simulationMode?: boolean, includeImplants?: boolean, moduleStates?: Record<number, string>, boosters?: Array<{ type_id: number; side_effects_enabled: number[] }>, modeTypeId?: number, fighters?: FighterInput[], fleetBoosts?: FleetBoostInput[], projectedEffects?: ProjectedEffectInput[], targetProjected?: ProjectedEffectInput[]) => {
    const body: Record<string, unknown> = {
      ship_type_id: shipTypeId,
      items,
      ...(charges && Object.keys(charges).length > 0 ? { charges } : {}),
      ...(characterId ? { character_id: characterId } : {}),
      ...(targetProfile ? { target_profile: targetProfile } : {}),
      ...(simulationMode ? { simulation_mode: true } : {}),
      ...(includeImplants === false ? { include_implants: false } : {}),
      ...(moduleStates && Object.keys(moduleStates).length > 0 ? { module_states: moduleStates } : {}),
      ...(boosters && boosters.length > 0 ? { boosters } : {}),
    };
    if (modeTypeId) body.mode_type_id = modeTypeId;
    if (fighters && fighters.length > 0) body.fighters = fighters;
    if (fleetBoosts && fleetBoosts.length > 0) body.fleet_boosts = fleetBoosts;
    if (projectedEffects && projectedEffects.length > 0) body.projected_effects = projectedEffects;
    if (targetProjected && targetProjected.length > 0) body.target_projected = targetProjected;
    return api.post<FittingStats>('/fittings/stats', body).then(r => r.data);
  },

  saveCustomFitting: (fitting: SaveFittingRequest) =>
    api.post<CustomFitting>('/fittings/save', fitting).then(r => r.data),

  updateCustomFitting: (id: number, update: SaveFittingRequest) =>
    api.put<CustomFitting>(`/fittings/custom/${id}`, update).then(r => r.data),

  deleteCustomFitting: (id: number) =>
    api.delete(`/fittings/custom/${id}`).then(r => r.data),

  getCustomFittingById: (fittingId: number) =>
    api.get<CustomFitting>(`/fittings/detail/${fittingId}`).then(r => r.data),

  getCustomFittings: (characterId: number, shipTypeId?: number) =>
    api.get<CustomFitting[]>(`/fittings/custom/${characterId}`, {
      params: shipTypeId ? { ship_type_id: shipTypeId } : undefined,
    }).then(r => r.data),

  getSharedFittings: (params?: { ship_type_id?: number; tag?: string; search?: string; limit?: number; offset?: number }) =>
    api.get<CustomFitting[]>('/fittings/shared', { params }).then(r => r.data),

  compareFittings: (fittings: Array<{ ship_type_id: number; items: FittingItem[]; charges?: FittingChargeMap; module_states?: Record<number, string> }>) =>
    api.post<{ comparisons: FittingStats[] }>('/fittings/compare', { fittings }).then(r => r.data),
};

// --- SDE Browser ---
export const sdeApi = {
  getShips: (params?: { search?: string; group?: string; group_id?: number; limit?: number; offset?: number }) =>
    api.get<ShipSummary[]>('/sde/ships', { params }).then(r => r.data),

  getShipGroups: () =>
    api.get<GroupSummary[]>('/sde/ship-groups').then(r => r.data),

  getShipDetail: (typeId: number) =>
    api.get<ShipDetail>(`/sde/ships/${typeId}`).then(r => r.data),

  getModules: (params?: { slot_type?: string; search?: string; group?: string; group_id?: number; category?: string; ship_type_id?: number; limit?: number; offset?: number }) =>
    api.get<ModuleSummary[]>('/sde/modules', { params }).then(r => r.data),

  getModuleGroups: (params?: { slot_type?: string; category?: string; ship_type_id?: number }) =>
    api.get<GroupSummary[]>('/sde/module-groups', { params }).then(r => r.data),

  resolveTypeNames: (names: string[]) =>
    api.post<{ type_id: number; type_name: string }[]>('/sde/resolve-names', names).then(r => r.data),

  getCharges: (weaponTypeId: number) =>
    api.get<ChargeSummary[]>('/sde/charges', { params: { weapon_type_id: weaponTypeId } }).then(r => r.data),

  getDrones: (params?: { search?: string; limit?: number }) =>
    api.get<ModuleSummary[]>('/sde/modules', {
      params: { ...params, group: 'drone' },
    }).then(r => r.data),

  searchCharges: (params?: { search?: string; limit?: number }) =>
    api.get<ModuleSummary[]>('/sde/modules', {
      params: { ...params, category: 'charge' },
    }).then(r => r.data),

  getMarketTreeChildren: (params: {
    category_root: number;
    parent_id?: number;
    slot_type?: string;
    ship_type_id?: number;
  }) => api.get<MarketGroupNode[]>('/sde/market-tree/children', { params }).then(r => r.data),

  getMarketTreeItems: (params: {
    market_group_id: number;
    category_root: number;
    slot_type?: string;
    ship_type_id?: number;
  }) => api.get<(ShipSummary | ModuleSummary | ChargeSummary)[]>('/sde/market-tree/items', { params }).then(r => r.data),

  async getModes(shipTypeId: number): Promise<T3DMode[]> {
    const { data } = await api.get(`/sde/modes/${shipTypeId}`);
    return data;
  },
};

// --- Boost & Projected API ---
export const boostApi = {
  async getBoostPresets(): Promise<Record<string, BoostPreset[]>> {
    const { data } = await api.get('/fittings/boost-presets');
    return data;
  },
  async getBoostDefinitions(): Promise<Record<string, BuffDefinition>> {
    const { data } = await api.get('/fittings/boost-definitions');
    return data;
  },
  async getProjectedPresets(): Promise<Record<string, ProjectedEffectInput[]>> {
    const { data } = await api.get('/fittings/projected-presets');
    return data;
  },
};

// --- Type Name Cache (resolves type_id → name) ---
const typeNameCache = new Map<number, string>();

export function cacheTypeName(typeId: number, name: string): void {
  typeNameCache.set(typeId, name);
}

export function getCachedTypeName(typeId: number): string | undefined {
  return typeNameCache.get(typeId);
}

export async function resolveTypeNames(typeIds: number[]): Promise<Map<number, string>> {
  const result = new Map<number, string>();
  const uncached: number[] = [];

  for (const id of typeIds) {
    const cached = typeNameCache.get(id);
    if (cached) {
      result.set(id, cached);
    } else {
      uncached.push(id);
    }
  }

  if (uncached.length > 0) {
    try {
      const resp = await api.get<{ types: Record<string, string> }>('/dogma/types/names', {
        params: { ids: uncached.join(',') },
      });
      for (const [idStr, name] of Object.entries(resp.data.types)) {
        const id = Number(idStr);
        typeNameCache.set(id, name);
        result.set(id, name);
      }
    } catch {
      for (const id of uncached) {
        result.set(id, `Type #${id}`);
      }
    }
  }

  return result;
}
