import { apiClient } from './client'

// ============ Skill Browser Types ============

export interface SkillInfo {
  type_id: number
  type_name: string
  description: string
  rank: number
  primary_attribute: string
  secondary_attribute: string
  trained_level: number | null
  skillpoints: number | null
}

export interface SkillGroup {
  group_id: number
  group_name: string
  skill_count: number
  skills: SkillInfo[]
}

export interface SkillBrowserResponse {
  groups: SkillGroup[]
  total_skills: number
}

// ============ Ship Mastery Types ============

export interface MissingSkill {
  skill: string
  skill_id: number
  have: number
  need: number
}

export interface ShipMasteryResponse {
  character: string
  character_id: number
  ship: string
  ship_class: string
  ship_type_id: number
  mastery_level: number
  mastery_name: string
  can_fly_effectively: boolean
  missing_for_next_level: MissingSkill[]
}

export interface FlyableShip {
  ship: string
  type_id: number
  mastery: number
}

export interface FlyableShipsResponse {
  character: string
  flyable_ships: Record<string, FlyableShip[]>
}

export interface ShipSearchResult {
  typeID: number
  typeName: string
  groupName: string
}

export interface ShipSearchResponse {
  search_term: string
  results: ShipSearchResult[]
}

// ============ API Functions ============

export const skillsApi = {
  getBrowser: async (characterId?: number): Promise<SkillBrowserResponse> => {
    const response = await apiClient.get<SkillBrowserResponse>('/skills/browser', {
      params: characterId ? { character_id: characterId } : undefined
    })
    return response.data
  },

  getFlyableShips: async (characterId: number, shipClass?: string): Promise<FlyableShipsResponse> => {
    const response = await apiClient.get<FlyableShipsResponse>(
      `/mastery/character/${characterId}/flyable`,
      { params: shipClass ? { ship_class: shipClass } : undefined }
    )
    return response.data
  },

  getShipMastery: async (characterId: number, shipTypeId: number): Promise<ShipMasteryResponse> => {
    const response = await apiClient.get<ShipMasteryResponse>(
      `/mastery/character/${characterId}/ship/${shipTypeId}`
    )
    return response.data
  },

  searchShips: async (name: string): Promise<ShipSearchResponse> => {
    const response = await apiClient.get<ShipSearchResponse>('/mastery/search', {
      params: { name }
    })
    return response.data
  },
}
