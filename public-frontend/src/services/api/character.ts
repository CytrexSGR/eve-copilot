import { api } from './client';
import type {
  CharacterSummaryResponse,
  SkillData,
  SkillQueue,
  ValuedAssetData,
  IndustryData,
} from '../../types/character';

export interface CharacterImplant {
  type_id: number;
  type_name: string;
  slot: number;
  perception_bonus: number;
  memory_bonus: number;
  willpower_bonus: number;
  intelligence_bonus: number;
  charisma_bonus: number;
}

export interface CharacterImplants {
  character_id: number;
  implants: CharacterImplant[];
}

export const characterApi = {
  /** Batch load characters with summary data. Pass IDs to fetch only specific characters. */
  getSummaryAll: (characterIds?: number[]) =>
    api.get<CharacterSummaryResponse>('/character/summary/all', {
      params: characterIds?.length ? { ids: characterIds.join(',') } : undefined,
    }).then(r => r.data),

  /** Full skill list for a character */
  getSkills: (characterId: number) =>
    api.get<SkillData>(`/character/${characterId}/skills`).then(r => r.data),

  /** Current skill queue */
  getSkillQueue: (characterId: number) =>
    api.get<SkillQueue>(`/character/${characterId}/skillqueue`).then(r => r.data),

  /** Valued assets with location summaries */
  getAssets: (characterId: number) =>
    api.get<ValuedAssetData>(`/character/${characterId}/assets/valued`).then(r => r.data),

  /** Industry jobs */
  getIndustry: (characterId: number) =>
    api.get<IndustryData>(`/character/${characterId}/industry`).then(r => r.data),

  /** Character implants */
  getImplants: (characterId: number) =>
    api.get<CharacterImplants>(`/character/${characterId}/implants`).then(r => r.data),
};
