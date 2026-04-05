import { apiClient } from './client'
import type {
  CharactersResponse,
  WalletResponse,
  SkillsResponse,
  SkillQueueResponse,
  CharacterInfo,
  PortraitResponse,
  AssetListResponse,
  LocationResponse,
  ShipResponse,
  IndustryResponse,
  ValuedAssetListResponse,
  CorporationInfo,
} from '@/types/character'

interface AuthUrlResponse {
  auth_url: string
}

// Type for batch summary response
export interface CharacterBatchData {
  character_id: number
  character_name: string
  info: {
    character_id: number
    name: string
    corporation_id: number
    birthday: string
    alliance_id: number | null
  }
  wallet: { balance: number }
  skills: { total_sp: number; unallocated_sp: number; skills: unknown[] }
  skillqueue: { queue: unknown[] }
  location: {
    solar_system_id: number
    solar_system_name: string
    station_id?: number
    station_name?: string
    structure_id?: number
  }
  ship: {
    ship_type_id: number
    ship_type_name: string
    ship_item_id: number
  }
  industry: { jobs: unknown[]; active_jobs?: number }
}

export interface CharacterBatchResponse {
  characters: CharacterBatchData[]
  count: number
}

export const charactersApi = {
  /**
   * Get all authenticated characters
   */
  getAll: async (): Promise<CharactersResponse> => {
    const response = await apiClient.get<CharactersResponse>('/auth/characters')
    return response.data
  },

  /**
   * Get all character data in a single batch request (optimized)
   * Returns info, wallet, skills, skillqueue, location, ship, industry for all characters
   */
  getAllSummary: async (): Promise<CharacterBatchResponse> => {
    const response = await apiClient.get<CharacterBatchResponse>('/character/summary/all')
    return response.data
  },

  /**
   * Get EVE SSO login URL to add a new character
   */
  getLoginUrl: async (): Promise<string> => {
    const currentUrl = window.location.origin + '/auth/callback'
    const response = await apiClient.get<AuthUrlResponse>('/auth/login', {
      params: { redirect_url: currentUrl }
    })
    return response.data.auth_url
  },

  /**
   * Start EVE SSO login flow to add a new character
   */
  addCharacter: async (): Promise<void> => {
    const authUrl = await charactersApi.getLoginUrl()
    window.location.href = authUrl
  },

  /**
   * Get character wallet balance
   */
  getWallet: async (characterId: number): Promise<WalletResponse> => {
    const response = await apiClient.get<WalletResponse>(`/character/${characterId}/wallet`)
    return response.data
  },

  /**
   * Get character skills
   */
  getSkills: async (characterId: number): Promise<SkillsResponse> => {
    const response = await apiClient.get<SkillsResponse>(`/character/${characterId}/skills`)
    return response.data
  },

  /**
   * Get character skill queue
   */
  getSkillQueue: async (characterId: number): Promise<SkillQueueResponse> => {
    const response = await apiClient.get<SkillQueueResponse>(`/character/${characterId}/skillqueue`)
    return response.data
  },

  /**
   * Get character public info
   */
  getInfo: async (characterId: number): Promise<CharacterInfo> => {
    const response = await apiClient.get<CharacterInfo>(`/character/${characterId}/info`)
    return response.data
  },

  /**
   * Get character portrait URLs
   */
  getPortrait: async (characterId: number): Promise<PortraitResponse> => {
    const response = await apiClient.get<PortraitResponse>(`/character/${characterId}/portrait`)
    return response.data
  },

  /**
   * Get character assets
   */
  getAssets: async (characterId: number): Promise<AssetListResponse> => {
    const response = await apiClient.get<AssetListResponse>(`/character/${characterId}/assets`)
    return response.data
  },

  /**
   * Get character location
   */
  getLocation: async (characterId: number): Promise<LocationResponse> => {
    const response = await apiClient.get<LocationResponse>(`/character/${characterId}/location`)
    return response.data
  },

  /**
   * Get character ship
   */
  getShip: async (characterId: number): Promise<ShipResponse> => {
    const response = await apiClient.get<ShipResponse>(`/character/${characterId}/ship`)
    return response.data
  },

  /**
   * Get character industry jobs
   */
  getIndustry: async (characterId: number): Promise<IndustryResponse> => {
    const response = await apiClient.get<IndustryResponse>(`/character/${characterId}/industry`)
    return response.data
  },

  /**
   * Get character valued assets (with market prices)
   */
  getValuedAssets: async (characterId: number): Promise<ValuedAssetListResponse> => {
    const response = await apiClient.get<ValuedAssetListResponse>(`/character/${characterId}/assets/valued`)
    return response.data
  },

  /**
   * Get corporation info from ESI
   */
  getCorporation: async (corporationId: number): Promise<CorporationInfo> => {
    const response = await fetch(`https://esi.evetech.net/latest/corporations/${corporationId}/`)
    if (!response.ok) throw new Error('Failed to fetch corporation')
    const data = await response.json()
    return {
      corporation_id: corporationId,
      name: data.name,
      ticker: data.ticker,
      member_count: data.member_count,
      alliance_id: data.alliance_id,
    }
  },

  /**
   * Get alliance info from ESI
   */
  getAlliance: async (allianceId: number): Promise<{ alliance_id: number; name: string; ticker: string }> => {
    const response = await fetch(`https://esi.evetech.net/latest/alliances/${allianceId}/`)
    if (!response.ok) throw new Error('Failed to fetch alliance')
    const data = await response.json()
    return {
      alliance_id: allianceId,
      name: data.name,
      ticker: data.ticker,
    }
  },
}
