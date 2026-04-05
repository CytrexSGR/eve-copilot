import { useQuery } from '@tanstack/react-query'
import { charactersApi, CharacterBatchData } from '@/api/characters'
import type { CharacterSummary, Character, CorporationInfo } from '@/types/character'

// Cache for corporation/alliance names to avoid redundant ESI calls
const corpCache = new Map<number, CorporationInfo>()
const allianceCache = new Map<number, { name: string; ticker: string }>()

/**
 * Hook to fetch aggregated summary data for multiple characters
 * Uses a single batch request to get all data at once (optimized from 31 requests to 1)
 */
export function useCharacterSummaries(characters: Character[]) {
  // Single batch query for all character data
  const batchQuery = useQuery({
    queryKey: ['characters', 'summary', 'all'],
    queryFn: () => charactersApi.getAllSummary(),
    staleTime: 60 * 1000, // 1 minute
    enabled: characters.length > 0,
  })

  // Get unique corporation IDs from batch data
  const corporationIds = [...new Set(
    (batchQuery.data?.characters ?? [])
      .map((c) => c.info?.corporation_id)
      .filter((id): id is number => !!id)
  )]

  // Fetch corporation info for each unique corp (still need ESI for corp details)
  const corpQuery = useQuery({
    queryKey: ['corporations', corporationIds],
    queryFn: async () => {
      const results: CorporationInfo[] = []
      for (const id of corporationIds) {
        if (corpCache.has(id)) {
          results.push(corpCache.get(id)!)
        } else {
          try {
            const corp = await charactersApi.getCorporation(id)
            corpCache.set(id, corp)
            results.push(corp)
          } catch {
            // Skip failed corp lookups
          }
        }
      }
      return results
    },
    enabled: corporationIds.length > 0,
    staleTime: 30 * 60 * 1000, // 30 minutes
  })

  // Get unique alliance IDs
  const allianceIds = [...new Set(
    (corpQuery.data ?? [])
      .map((c) => c.alliance_id)
      .filter((id): id is number => !!id)
  )]

  // Fetch alliance info
  const allianceQuery = useQuery({
    queryKey: ['alliances', allianceIds],
    queryFn: async () => {
      const results: { alliance_id: number; name: string; ticker: string }[] = []
      for (const id of allianceIds) {
        if (allianceCache.has(id)) {
          results.push({ alliance_id: id, ...allianceCache.get(id)! })
        } else {
          try {
            const alliance = await charactersApi.getAlliance(id)
            allianceCache.set(id, alliance)
            results.push(alliance)
          } catch {
            // Skip failed alliance lookups
          }
        }
      }
      return results
    },
    enabled: allianceIds.length > 0,
    staleTime: 30 * 60 * 1000, // 30 minutes
  })

  const isLoading = batchQuery.isLoading || corpQuery.isLoading
  const isError = batchQuery.isError

  // Build corp lookup map
  const corpMap = new Map<number, CorporationInfo>()
  ;(corpQuery.data ?? []).forEach((corp) => {
    corpMap.set(corp.corporation_id, corp)
  })

  // Build alliance lookup map
  const allianceMap = new Map<number, { name: string; ticker: string }>()
  ;(allianceQuery.data ?? []).forEach((alliance) => {
    allianceMap.set(alliance.alliance_id, alliance)
  })

  // Build summaries from batch data
  const summaries: CharacterSummary[] = (batchQuery.data?.characters ?? []).map((charData: CharacterBatchData) => {
    const corp = charData.info?.corporation_id ? corpMap.get(charData.info.corporation_id) : undefined
    const alliance = corp?.alliance_id ? allianceMap.get(corp.alliance_id) : undefined

    // Find current training skill
    const queue = charData.skillqueue?.queue as Array<{ finish_date: string; skill_name?: string; finished_level?: number }> ?? []
    const currentSkill = queue.find((item) => {
      const finishDate = new Date(item.finish_date)
      return finishDate > new Date()
    })

    return {
      character_id: charData.character_id,
      character_name: charData.character_name,
      portrait_url: `https://images.evetech.net/characters/${charData.character_id}/portrait?size=128`,
      wallet_balance: charData.wallet?.balance ?? 0,
      total_sp: charData.skills?.total_sp ?? 0,
      unallocated_sp: charData.skills?.unallocated_sp ?? 0,
      current_skill: currentSkill,
      skills_in_queue: queue.length,
      location: charData.location ? {
        solar_system_id: charData.location.solar_system_id,
        solar_system_name: charData.location.solar_system_name,
        station_id: charData.location.station_id,
        station_name: charData.location.station_name,
        structure_id: charData.location.structure_id,
      } : undefined,
      ship: charData.ship ? {
        ship_type_id: charData.ship.ship_type_id,
        ship_name: charData.ship.ship_type_name,
        ship_item_id: charData.ship.ship_item_id,
      } : undefined,
      active_industry_jobs: charData.industry?.active_jobs ?? (charData.industry?.jobs?.length ?? 0),
      corporation_id: charData.info?.corporation_id,
      corporation_name: corp?.name,
      corporation_ticker: corp?.ticker,
      alliance_id: corp?.alliance_id,
      alliance_name: alliance?.name,
    }
  })

  // Get unique corporations for the corp section
  const corporations = [...corpMap.values()]

  const refetch = () => {
    batchQuery.refetch()
    corpQuery.refetch()
    allianceQuery.refetch()
  }

  return {
    data: summaries,
    corporations,
    isLoading,
    isError,
    refetch,
  }
}
