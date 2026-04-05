import { apiClient } from './client'
import type {
  ESIFitting,
  CustomFitting,
  FittingStats,
  FittingItem,
  ShipSummary,
  ShipDetail,
  ModuleSummary,
} from '@/types/fittings'

// --- ESI Fittings ---

export async function getCharacterFittings(characterId: number): Promise<ESIFitting[]> {
  const { data } = await apiClient.get<ESIFitting[]>(`/fittings/${characterId}`)
  return data
}

// --- Combined Stats ---

export async function getFittingStats(
  shipTypeId: number,
  items: FittingItem[],
  ammoTypeId?: number
): Promise<FittingStats> {
  const { data } = await apiClient.post<FittingStats>('/fittings/stats', {
    ship_type_id: shipTypeId,
    items,
    ammo_type_id: ammoTypeId,
  })
  return data
}

// --- Custom Fittings CRUD ---

export async function saveCustomFitting(fitting: {
  name: string
  description?: string
  ship_type_id: number
  items: FittingItem[]
  tags?: string[]
  is_public?: boolean
  creator_character_id: number
}): Promise<CustomFitting> {
  const { data } = await apiClient.post<CustomFitting>('/fittings/save', fitting)
  return data
}

export async function updateCustomFitting(
  fittingId: number,
  update: {
    name?: string
    description?: string
    items?: FittingItem[]
    tags?: string[]
    is_public?: boolean
  }
): Promise<CustomFitting> {
  const { data } = await apiClient.put<CustomFitting>(`/fittings/custom/${fittingId}`, update)
  return data
}

export async function deleteCustomFitting(fittingId: number): Promise<void> {
  await apiClient.delete(`/fittings/custom/${fittingId}`)
}

export async function getCustomFittings(
  characterId: number,
  shipTypeId?: number
): Promise<CustomFitting[]> {
  const params: Record<string, number> = {}
  if (shipTypeId) params.ship_type_id = shipTypeId
  const { data } = await apiClient.get<CustomFitting[]>(`/fittings/custom/${characterId}`, { params })
  return data
}

export async function getSharedFittings(options?: {
  ship_type_id?: number
  tag?: string
  search?: string
  limit?: number
  offset?: number
}): Promise<CustomFitting[]> {
  const params: Record<string, string | number> = {}
  if (options?.ship_type_id) params.ship_type_id = options.ship_type_id
  if (options?.tag) params.tag = options.tag
  if (options?.search) params.search = options.search
  if (options?.limit) params.limit = options.limit
  if (options?.offset) params.offset = options.offset
  const { data } = await apiClient.get<CustomFitting[]>('/fittings/shared', { params })
  return data
}

// --- SDE Browser ---

export async function getShips(options?: {
  search?: string
  group?: string
  limit?: number
  offset?: number
}): Promise<ShipSummary[]> {
  const params: Record<string, string | number> = {}
  if (options?.search) params.search = options.search
  if (options?.group) params.group = options.group
  if (options?.limit) params.limit = options.limit
  if (options?.offset) params.offset = options.offset
  const { data } = await apiClient.get<ShipSummary[]>('/sde/ships', { params })
  return data
}

export async function getShipDetail(shipTypeId: number): Promise<ShipDetail> {
  const { data } = await apiClient.get<ShipDetail>(`/sde/ships/${shipTypeId}`)
  return data
}

export async function getModules(options?: {
  slot_type?: string
  search?: string
  group?: string
  limit?: number
  offset?: number
}): Promise<ModuleSummary[]> {
  const params: Record<string, string | number> = {}
  if (options?.slot_type) params.slot_type = options.slot_type
  if (options?.search) params.search = options.search
  if (options?.group) params.group = options.group
  if (options?.limit) params.limit = options.limit
  if (options?.offset) params.offset = options.offset
  const { data } = await apiClient.get<ModuleSummary[]>('/sde/modules', { params })
  return data
}

export async function resolveTypeNames(
  names: string[]
): Promise<{ type_id: number; type_name: string }[]> {
  const { data } = await apiClient.post<{ type_id: number; type_name: string }[]>(
    '/sde/resolve-names',
    names
  )
  return data
}
