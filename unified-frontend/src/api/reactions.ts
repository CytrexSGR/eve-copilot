// unified-frontend/src/api/reactions.ts

import { apiClient } from './client'
import type {
  ReactionFormula,
  ReactionProfitability,
  ProfitableReaction,
  ReactionType
} from '@/types/reactions'

/**
 * Fetch all reactions, optionally filtered by type
 */
export async function getReactions(type?: ReactionType): Promise<ReactionFormula[]> {
  const params: Record<string, string> = {}
  if (type && type !== 'all') {
    params.reaction_type = type
  }
  const response = await apiClient.get<ReactionFormula[]>('/reactions', { params })
  return response.data
}

/**
 * Fetch a specific reaction by reaction_type_id
 */
export async function getReactionById(reactionTypeId: number): Promise<ReactionFormula> {
  const response = await apiClient.get<ReactionFormula>(`/reactions/${reactionTypeId}`)
  return response.data
}

/**
 * Fetch profitability analysis for a specific reaction
 */
export async function getReactionProfitability(
  reactionTypeId: number,
  regionId: number = 10000002
): Promise<ReactionProfitability> {
  const response = await apiClient.get<ReactionProfitability>(
    `/reactions/${reactionTypeId}/profit`,
    { params: { region_id: regionId } }
  )
  return response.data
}

/**
 * Fetch profitable reactions sorted by ROI
 */
export async function getProfitableReactions(
  limit: number = 20,
  reactionType?: ReactionType,
  regionId: number = 10000002
): Promise<ProfitableReaction[]> {
  const params: Record<string, string | number> = {
    limit,
    region_id: regionId
  }
  if (reactionType && reactionType !== 'all') {
    params.reaction_type = reactionType
  }
  const response = await apiClient.get<ProfitableReaction[]>(
    '/reactions/profitable',
    { params }
  )
  return response.data
}
