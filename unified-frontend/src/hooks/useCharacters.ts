import { useQuery } from '@tanstack/react-query'
import { charactersApi } from '@/api/characters'

/**
 * Hook to fetch all authenticated characters
 */
export function useCharacters() {
  return useQuery({
    queryKey: ['characters'],
    queryFn: charactersApi.getAll,
  })
}

/**
 * Hook to fetch character wallet
 */
export function useCharacterWallet(characterId: number) {
  return useQuery({
    queryKey: ['character', characterId, 'wallet'],
    queryFn: () => charactersApi.getWallet(characterId),
    enabled: !!characterId,
  })
}

/**
 * Hook to fetch character skills
 */
export function useCharacterSkills(characterId: number) {
  return useQuery({
    queryKey: ['character', characterId, 'skills'],
    queryFn: () => charactersApi.getSkills(characterId),
    enabled: !!characterId,
  })
}

/**
 * Hook to fetch character skill queue
 */
export function useCharacterSkillQueue(characterId: number) {
  return useQuery({
    queryKey: ['character', characterId, 'skillqueue'],
    queryFn: () => charactersApi.getSkillQueue(characterId),
    enabled: !!characterId,
  })
}

/**
 * Hook to fetch character info
 */
export function useCharacterInfo(characterId: number) {
  return useQuery({
    queryKey: ['character', characterId, 'info'],
    queryFn: () => charactersApi.getInfo(characterId),
    enabled: !!characterId,
  })
}

/**
 * Hook to fetch character portrait
 */
export function useCharacterPortrait(characterId: number) {
  return useQuery({
    queryKey: ['character', characterId, 'portrait'],
    queryFn: () => charactersApi.getPortrait(characterId),
    enabled: !!characterId,
    staleTime: 1000 * 60 * 60 * 24, // Portraits don't change often - 24h
  })
}

/**
 * Hook to fetch character assets
 */
export function useCharacterAssets(characterId: number) {
  return useQuery({
    queryKey: ['character', characterId, 'assets'],
    queryFn: () => charactersApi.getAssets(characterId),
    enabled: characterId > 0,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook to fetch character location
 */
export function useCharacterLocation(characterId: number) {
  return useQuery({
    queryKey: ['character', characterId, 'location'],
    queryFn: () => charactersApi.getLocation(characterId),
    enabled: characterId > 0,
    staleTime: 60 * 1000, // 1 minute - location changes more frequently
  })
}

/**
 * Hook to fetch character ship
 */
export function useCharacterShip(characterId: number) {
  return useQuery({
    queryKey: ['character', characterId, 'ship'],
    queryFn: () => charactersApi.getShip(characterId),
    enabled: characterId > 0,
    staleTime: 60 * 1000, // 1 minute
  })
}

/**
 * Hook to fetch character industry jobs
 */
export function useCharacterIndustry(characterId: number) {
  return useQuery({
    queryKey: ['character', characterId, 'industry'],
    queryFn: () => charactersApi.getIndustry(characterId),
    enabled: characterId > 0,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}
