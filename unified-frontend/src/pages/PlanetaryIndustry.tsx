import { useState, useMemo } from 'react'
import { useQueries, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useCharacters } from '@/hooks/useCharacters'
import { piApi, type PIColony, type PIOpportunity } from '@/api/pi'
import { cn } from '@/lib/utils'
import type { Character } from '@/types/character'
import {
  Globe2,
  Factory,
  Flame,
  Droplets,
  Wind,
  Mountain,
  Leaf,
  Snowflake,
  Zap,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  TrendingUp,
  Clock,
  Loader2,
} from 'lucide-react'

/**
 * Planet type icons and colors
 */
const PLANET_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  barren: { icon: Mountain, color: 'text-stone-400', bg: 'bg-stone-500/20' },
  gas: { icon: Wind, color: 'text-cyan-400', bg: 'bg-cyan-500/20' },
  ice: { icon: Snowflake, color: 'text-blue-300', bg: 'bg-blue-500/20' },
  lava: { icon: Flame, color: 'text-orange-400', bg: 'bg-orange-500/20' },
  oceanic: { icon: Droplets, color: 'text-blue-400', bg: 'bg-blue-500/20' },
  plasma: { icon: Zap, color: 'text-purple-400', bg: 'bg-purple-500/20' },
  storm: { icon: Wind, color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  temperate: { icon: Leaf, color: 'text-green-400', bg: 'bg-green-500/20' },
}

/**
 * Get planet icon and styling
 */
function getPlanetConfig(planetType: string) {
  return PLANET_CONFIG[planetType.toLowerCase()] || { icon: Globe2, color: 'text-gray-400', bg: 'bg-gray-500/20' }
}

/**
 * Format relative time
 */
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffDays > 0) return `${diffDays}d ago`
  if (diffHours > 0) return `${diffHours}h ago`
  return 'Just now'
}

/**
 * Format ISK value
 */
function formatISK(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return value.toFixed(0)
}

/**
 * Colony card component
 */
function ColonyCard({
  colony,
  onClick,
}: {
  colony: PIColony
  onClick: () => void
}) {
  const config = getPlanetConfig(colony.planet_type)
  const PlanetIcon = config.icon

  return (
    <button
      onClick={onClick}
      className="w-full text-left p-3 rounded-lg hover:bg-secondary/50 transition-colors border border-transparent hover:border-border"
    >
      <div className="flex items-center gap-3">
        <div className={cn('p-2 rounded-lg', config.bg)}>
          <PlanetIcon className={cn('h-5 w-5', config.color)} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium capitalize">{colony.planet_type}</span>
            <Badge variant="outline" className="text-xs">
              Lvl {colony.upgrade_level}
            </Badge>
          </div>
          <div className="text-xs text-muted-foreground">
            {colony.solar_system_name} • {colony.num_pins} pins
          </div>
        </div>
        <div className="text-xs text-muted-foreground">
          <Clock className="h-3 w-3 inline mr-1" />
          {formatRelativeTime(colony.last_update)}
        </div>
      </div>
    </button>
  )
}

/**
 * Character PI group
 */
function CharacterPIGroup({
  character,
  colonies,
  defaultExpanded = false,
  onColonyClick,
  onSync,
  isSyncing,
}: {
  character: Character
  colonies: PIColony[]
  defaultExpanded?: boolean
  onColonyClick: (colony: PIColony) => void
  onSync: () => void
  isSyncing: boolean
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  const portraitUrl = `https://images.evetech.net/characters/${character.character_id}/portrait?size=64`

  // Group colonies by planet type
  const planetCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    colonies.forEach((c) => {
      counts[c.planet_type] = (counts[c.planet_type] || 0) + 1
    })
    return counts
  }, [colonies])

  return (
    <Card className="overflow-hidden">
      <button className="w-full text-left" onClick={() => setIsExpanded(!isExpanded)}>
        <CardHeader className="pb-3 cursor-pointer hover:bg-secondary/30 transition-colors">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isExpanded ? (
                <ChevronDown className="h-5 w-5 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-5 w-5 text-muted-foreground" />
              )}
              <Avatar className="h-8 w-8">
                <AvatarImage src={portraitUrl} alt={character.character_name} />
                <AvatarFallback>{character.character_name.slice(0, 2).toUpperCase()}</AvatarFallback>
              </Avatar>
              <CardTitle className="text-base font-medium">{character.character_name}</CardTitle>
            </div>
            <div className="flex items-center gap-2">
              {Object.entries(planetCounts).map(([type, count]) => {
                const config = getPlanetConfig(type)
                const Icon = config.icon
                return (
                  <Badge key={type} variant="outline" className={cn('text-xs', config.color)}>
                    <Icon className="h-3 w-3 mr-1" />
                    {count}
                  </Badge>
                )
              })}
              <Badge variant="secondary" className="text-xs">
                {colonies.length} planets
              </Badge>
            </div>
          </div>
        </CardHeader>
      </button>

      {isExpanded && (
        <CardContent className="pt-0">
          <div className="flex justify-end mb-2">
            <button
              onClick={(e) => {
                e.stopPropagation()
                onSync()
              }}
              disabled={isSyncing}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
            >
              {isSyncing ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <RefreshCw className="h-3 w-3" />
              )}
              Sync from ESI
            </button>
          </div>
          <div className="border-t border-border">
            {colonies.length === 0 ? (
              <div className="py-6 text-center text-muted-foreground">
                No PI colonies found
              </div>
            ) : (
              <div className="divide-y divide-border">
                {colonies.map((colony) => (
                  <ColonyCard
                    key={colony.planet_id}
                    colony={colony}
                    onClick={() => onColonyClick(colony)}
                  />
                ))}
              </div>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  )
}

/**
 * Opportunity card
 */
function OpportunityCard({ opportunity }: { opportunity: PIOpportunity }) {
  const tierColors: Record<number, string> = {
    1: 'bg-gray-500/20 text-gray-400',
    2: 'bg-blue-500/20 text-blue-400',
    3: 'bg-purple-500/20 text-purple-400',
    4: 'bg-yellow-500/20 text-yellow-400',
  }

  return (
    <div className="p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors">
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-sm truncate">{opportunity.type_name}</span>
        <Badge className={cn('text-xs', tierColors[opportunity.tier] || tierColors[1])}>
          P{opportunity.tier}
        </Badge>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-muted-foreground">Profit/h:</span>
          <span className="ml-1 text-green-400 font-mono">{formatISK(opportunity.profit_per_hour)}</span>
        </div>
        <div>
          <span className="text-muted-foreground">ROI:</span>
          <span className="ml-1 text-green-400 font-mono">{opportunity.roi_percent.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  )
}

/**
 * Hook to fetch PI data for all characters
 */
function useAllCharacterPI(characters: Character[]) {
  const queries = useQueries({
    queries: characters.map((char) => ({
      queryKey: ['pi', 'colonies', char.character_id],
      queryFn: () => piApi.getColonies(char.character_id),
      staleTime: 5 * 60 * 1000,
      enabled: char.character_id > 0,
    })),
  })

  const isLoading = queries.some((q) => q.isLoading)
  const isError = queries.some((q) => q.isError)

  const characterColonies = useMemo(() => {
    // Show ALL characters, not just those with colonies
    // Alliance commanders need to see everyone's PI status
    return queries.map((q, index) => ({
      character: characters[index],
      colonies: q.data || [],
      isLoading: q.isLoading,
    }))
  }, [queries, characters])

  const totalColonies = characterColonies.reduce((sum, c) => sum + c.colonies.length, 0)
  const totalPins = characterColonies.reduce(
    (sum, c) => sum + c.colonies.reduce((s, col) => s + col.num_pins, 0),
    0
  )

  return { characterColonies, isLoading, isError, totalColonies, totalPins }
}

/**
 * Loading skeleton
 */
function PISkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2].map((i) => (
        <Card key={i}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Skeleton className="h-8 w-8 rounded-full" />
                <Skeleton className="h-5 w-32" />
              </div>
              <div className="flex gap-2">
                <Skeleton className="h-5 w-16" />
                <Skeleton className="h-5 w-20" />
              </div>
            </div>
          </CardHeader>
        </Card>
      ))}
    </div>
  )
}

/**
 * Main Planetary Industry page
 */
export function PlanetaryIndustry() {
  const navigate = useNavigate()
  const { data: charactersData, isLoading: isLoadingChars } = useCharacters()
  const characters = charactersData?.characters ?? []
  const { characterColonies, isLoading: isLoadingPI, totalColonies, totalPins } =
    useAllCharacterPI(characters)

  const [syncingCharId, setSyncingCharId] = useState<number | null>(null)

  // Fetch profitable PI products
  const { data: opportunities } = useQuery({
    queryKey: ['pi', 'opportunities'],
    queryFn: () => piApi.getOpportunities(undefined, 6),
    staleTime: 10 * 60 * 1000,
  })

  const isLoading = isLoadingChars || isLoadingPI

  const handleColonyClick = (colony: PIColony, characterId: number) => {
    navigate(`/pi/colony/${characterId}/${colony.planet_id}`)
  }

  const handleSync = async (characterId: number) => {
    setSyncingCharId(characterId)
    try {
      await piApi.syncColonies(characterId)
      // Invalidate queries would be better, but for now just refresh
      window.location.reload()
    } catch (error) {
      console.error('Failed to sync colonies:', error)
    } finally {
      setSyncingCharId(null)
    }
  }

  // Count planets by type across all characters
  const planetTypeCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    characterColonies.forEach(({ colonies }) => {
      colonies.forEach((c) => {
        counts[c.planet_type] = (counts[c.planet_type] || 0) + 1
      })
    })
    return counts
  }, [characterColonies])

  return (
    <div>
      <Header title="Planetary Industry" subtitle="Colony management & production" />

      <div className="p-6 space-y-6">
        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-500/20">
                  <Globe2 className="h-5 w-5 text-green-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold">{totalColonies}</div>
                  <div className="text-xs text-muted-foreground">Total Colonies</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/20">
                  <Factory className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold">{totalPins}</div>
                  <div className="text-xs text-muted-foreground">Total Pins</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Planet type breakdown */}
          {Object.entries(planetTypeCounts)
            .slice(0, 2)
            .map(([type, count]) => {
              const config = getPlanetConfig(type)
              const Icon = config.icon
              return (
                <Card key={type}>
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-3">
                      <div className={cn('p-2 rounded-lg', config.bg)}>
                        <Icon className={cn('h-5 w-5', config.color)} />
                      </div>
                      <div>
                        <div className="text-2xl font-bold">{count}</div>
                        <div className="text-xs text-muted-foreground capitalize">{type}</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Character Colonies */}
          <div className="lg:col-span-2 space-y-4">
            <h2 className="text-lg font-semibold">Your Colonies</h2>

            {isLoading ? (
              <PISkeleton />
            ) : characterColonies.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Globe2 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No PI Colonies</h3>
                  <p className="text-muted-foreground">
                    None of your characters have planetary colonies set up.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {characterColonies.map(({ character, colonies }, index) => (
                  <CharacterPIGroup
                    key={character.character_id}
                    character={character}
                    colonies={colonies}
                    defaultExpanded={index === 0}
                    onColonyClick={(colony) => handleColonyClick(colony, character.character_id)}
                    onSync={() => handleSync(character.character_id)}
                    isSyncing={syncingCharId === character.character_id}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Profitable Products Sidebar */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-400" />
              Profitable Products
            </h2>

            <Card>
              <CardContent className="pt-4">
                {opportunities && opportunities.length > 0 ? (
                  <div className="space-y-2">
                    {opportunities.map((opp) => (
                      <OpportunityCard key={opp.type_id} opportunity={opp} />
                    ))}
                  </div>
                ) : (
                  <div className="py-6 text-center text-muted-foreground">
                    Loading opportunities...
                  </div>
                )}
              </CardContent>
            </Card>

            <button
              onClick={() => navigate('/pi/profitability')}
              className="w-full py-2 px-4 rounded-lg bg-primary/20 text-primary hover:bg-primary/30 transition-colors text-sm"
            >
              View All Opportunities →
            </button>

            <button
              onClick={() => navigate('/pi/projects')}
              className="w-full py-2 px-4 rounded-lg bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 transition-colors text-sm"
            >
              Projects →
            </button>

            <button
              onClick={() => navigate('/pi/make-or-buy')}
              className="w-full py-2 px-4 rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors text-sm"
            >
              Make or Buy Analysis →
            </button>

            <button
              onClick={() => navigate('/pi/empire')}
              className="w-full py-2 px-4 rounded-lg bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 transition-colors text-sm"
            >
              Empire Dashboard →
            </button>

            <button
              onClick={() => navigate('/pi/empire/overview')}
              className="w-full py-2 px-4 rounded-lg bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 transition-colors text-sm"
            >
              Multi-Character Overview →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
