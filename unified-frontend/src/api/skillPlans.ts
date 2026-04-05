import { apiClient } from './client'

// === Types ===

export interface SkillPlan {
  id: number
  character_id: number
  name: string
  description: string | null
  created_at: string
  updated_at: string
  skill_count?: number
}

export interface SkillPlanItem {
  id: number
  plan_id: number
  skill_type_id: number
  skill_name: string
  target_level: number
  sort_order: number
  notes: string | null
}

export interface SkillPlanRemap {
  id: number
  plan_id: number
  after_item_id: number | null
  perception: number
  memory: number
  willpower: number
  intelligence: number
  charisma: number
}

export interface PlanWithItems extends SkillPlan {
  items: SkillPlanItem[]
  remaps: SkillPlanRemap[]
}

export interface CalculatedItem {
  item_id: number
  skill_type_id: number
  skill_name: string
  from_level: number
  to_level: number
  sp_required: number
  training_time_seconds: number
  training_time_formatted: string
  cumulative_seconds: number
  cumulative_formatted: string
  primary_attribute: string
  secondary_attribute: string
}

export interface RemapSuggestion {
  after_item_id: number | null
  after_skill_name: string
  new_attributes: Record<string, number>
  time_saved_seconds: number
  time_saved_formatted: string
}

export interface PlanCalculation {
  plan_id: number
  character_id: number
  items: CalculatedItem[]
  total_training_time_seconds: number
  total_training_time_formatted: string
  current_attributes: Record<string, number>
  implant_bonuses: Record<string, number>
  optimal_attributes: Record<string, number>
  remap_suggestions: RemapSuggestion[]
}

export interface ShipRequirements {
  ship_type_id: number
  ship_name: string
  mastery_level: number
  required_skills: Array<{
    skill_type_id: number
    skill_name: string
    level: number
  }>
}

// === API Functions ===

export const skillPlansApi = {
  /**
   * List all skill plans, optionally filtered by character
   */
  list: async (characterId?: number): Promise<SkillPlan[]> => {
    const params = characterId ? { character_id: characterId } : undefined
    const response = await apiClient.get<SkillPlan[]>('/skills/plans', { params })
    return response.data
  },

  /**
   * Get a skill plan with all items and remaps
   */
  get: async (planId: number): Promise<PlanWithItems> => {
    const response = await apiClient.get<PlanWithItems>(`/skills/plans/${planId}`)
    return response.data
  },

  /**
   * Create a new skill plan
   */
  create: async (characterId: number, name: string, description?: string): Promise<SkillPlan> => {
    const response = await apiClient.post<SkillPlan>('/skills/plans', {
      character_id: characterId,
      name,
      description,
    })
    return response.data
  },

  /**
   * Update an existing skill plan
   */
  update: async (planId: number, data: { name?: string; description?: string }): Promise<SkillPlan> => {
    const response = await apiClient.put<SkillPlan>(`/skills/plans/${planId}`, data)
    return response.data
  },

  /**
   * Delete a skill plan
   */
  delete: async (planId: number): Promise<void> => {
    await apiClient.delete(`/skills/plans/${planId}`)
  },

  /**
   * Add a single item to a skill plan
   */
  addItem: async (planId: number, skillTypeId: number, targetLevel: number): Promise<SkillPlanItem> => {
    const response = await apiClient.post<SkillPlanItem>(`/skills/plans/${planId}/items`, {
      skill_type_id: skillTypeId,
      target_level: targetLevel,
    })
    return response.data
  },

  /**
   * Add multiple items to a skill plan in a single request
   */
  addItemsBatch: async (planId: number, items: Array<{ skill_type_id: number; target_level: number }>): Promise<SkillPlanItem[]> => {
    const response = await apiClient.post<SkillPlanItem[]>(`/skills/plans/${planId}/items/batch`, items)
    return response.data
  },

  /**
   * Update a skill plan item
   */
  updateItem: async (planId: number, itemId: number, data: { target_level?: number; notes?: string }): Promise<SkillPlanItem> => {
    const response = await apiClient.put<SkillPlanItem>(`/skills/plans/${planId}/items/${itemId}`, data)
    return response.data
  },

  /**
   * Delete a skill plan item
   */
  deleteItem: async (planId: number, itemId: number): Promise<void> => {
    await apiClient.delete(`/skills/plans/${planId}/items/${itemId}`)
  },

  /**
   * Reorder items within a skill plan
   */
  reorder: async (planId: number, itemIds: number[]): Promise<void> => {
    await apiClient.post(`/skills/plans/${planId}/reorder`, { item_ids: itemIds })
  },

  /**
   * Calculate training times and remap suggestions for a plan
   */
  calculate: async (planId: number, characterId: number): Promise<PlanCalculation> => {
    const response = await apiClient.get<PlanCalculation>(`/skills/plans/${planId}/calculate`, {
      params: { character_id: characterId },
    })
    return response.data
  },

  /**
   * Get ship skill requirements for creating a skill plan
   */
  getShipRequirements: async (typeId: number, masteryLevel: number = 4): Promise<ShipRequirements> => {
    const response = await apiClient.get<ShipRequirements>(`/skills/requirements/ship/${typeId}`, {
      params: { mastery_level: masteryLevel },
    })
    return response.data
  },
}
