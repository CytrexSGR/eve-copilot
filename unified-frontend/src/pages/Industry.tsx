import { useMemo, useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { charactersApi } from '@/api/characters'
import { cn } from '@/lib/utils'
import type { Character, IndustryJob } from '@/types/character'
import {
  Factory,
  FlaskConical,
  Copy,
  Microscope,
  Atom,
  Clock,
  ChevronDown,
  ChevronRight,
  Users,
  Hammer,
} from 'lucide-react'

/**
 * Activity ID to name and icon mapping
 */
const ACTIVITY_MAP: Record<number, { name: string; icon: React.ElementType; color: string }> = {
  1: { name: 'Manufacturing', icon: Hammer, color: 'text-green-400' },
  3: { name: 'TE Research', icon: Clock, color: 'text-blue-400' },
  4: { name: 'ME Research', icon: Microscope, color: 'text-purple-400' },
  5: { name: 'Copying', icon: Copy, color: 'text-yellow-400' },
  7: { name: 'Reverse Engineering', icon: FlaskConical, color: 'text-orange-400' },
  8: { name: 'Invention', icon: Atom, color: 'text-cyan-400' },
  9: { name: 'Reactions', icon: Factory, color: 'text-red-400' },
}

/**
 * Format duration from seconds to human readable
 */
function formatDuration(seconds: number): string {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  if (days > 0) {
    return `${days}d ${hours}h`
  }
  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }
  return `${minutes}m`
}

/**
 * Get EVE Online item icon URL
 */
function getItemIconUrl(typeId: number, size: 32 | 64 = 32): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

interface CharacterIndustryGroup {
  character_id: number
  character_name: string
  portrait_url: string
  jobs: IndustryJob[]
  total_jobs: number
  active_jobs: number
}

/**
 * Single job item display
 */
function JobItem({ job }: { job: IndustryJob }) {
  const activity = ACTIVITY_MAP[job.activity_id] || { name: 'Unknown', icon: Factory, color: 'text-muted-foreground' }
  const Icon = activity.icon

  return (
    <div className="flex items-center gap-3 py-3 px-3 rounded-md hover:bg-secondary/30 transition-colors border-b border-border last:border-0">
      <div className="flex-shrink-0">
        <img
          src={getItemIconUrl(job.blueprint_type_id, 32)}
          alt="Blueprint"
          className="w-10 h-10 rounded"
          loading="lazy"
          onError={(e) => {
            e.currentTarget.style.display = 'none'
          }}
        />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate">{job.blueprint_type_name || `Blueprint #${job.blueprint_type_id}`}</span>
          <Badge variant="outline" className={cn('text-xs', activity.color)}>
            <Icon className="h-3 w-3 mr-1" />
            {activity.name}
          </Badge>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatDuration(job.duration)}
          </span>
          <span>Job #{job.job_id}</span>
        </div>
      </div>

      <div className="flex-shrink-0">
        <Badge
          variant={job.status === 'active' ? 'default' : 'secondary'}
          className={cn(
            job.status === 'active' && 'bg-green-500/20 text-green-400 border-green-500/30'
          )}
        >
          {job.status}
        </Badge>
      </div>
    </div>
  )
}

/**
 * Character group with collapsible jobs
 */
function CharacterGroup({
  group,
  defaultExpanded = false,
}: {
  group: CharacterIndustryGroup
  defaultExpanded?: boolean
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

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
                <AvatarImage src={group.portrait_url} alt={group.character_name} />
                <AvatarFallback>{group.character_name.slice(0, 2).toUpperCase()}</AvatarFallback>
              </Avatar>
              <CardTitle className="text-base font-medium">{group.character_name}</CardTitle>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="default" className="bg-green-500/20 text-green-400 border-green-500/30">
                {group.active_jobs} active
              </Badge>
              <Badge variant="secondary" className="text-xs">
                {group.total_jobs} total
              </Badge>
            </div>
          </div>
        </CardHeader>
      </button>

      {isExpanded && (
        <CardContent className="pt-0">
          <div className="border-t border-border">
            {group.jobs.length === 0 ? (
              <div className="py-6 text-center text-muted-foreground">
                No active industry jobs
              </div>
            ) : (
              group.jobs.map((job) => <JobItem key={job.job_id} job={job} />)
            )}
          </div>
        </CardContent>
      )}
    </Card>
  )
}

/**
 * Hook to fetch industry jobs for all characters
 */
function useAllCharacterIndustry(characters: Character[]) {
  const queries = useQueries({
    queries: characters.map((char) => ({
      queryKey: ['character', char.character_id, 'industry'],
      queryFn: () => charactersApi.getIndustry(char.character_id),
      staleTime: 60 * 1000, // 1 minute - jobs update frequently
      enabled: char.character_id > 0,
    })),
  })

  const isLoading = queries.some((q) => q.isLoading)
  const isError = queries.some((q) => q.isError)

  const groups: CharacterIndustryGroup[] = useMemo(() => {
    return queries
      .map((q, index) => ({
        query: q,
        character: characters[index],
      }))
      .filter((item) => item.query.data)
      .map((item) => ({
        character_id: item.character.character_id,
        character_name: item.character.character_name,
        portrait_url: `https://images.evetech.net/characters/${item.character.character_id}/portrait?size=64`,
        jobs: item.query.data!.jobs,
        total_jobs: item.query.data!.total_jobs,
        active_jobs: item.query.data!.active_jobs,
      }))
  }, [queries, characters])

  return { groups, isLoading, isError }
}

/**
 * Loading skeleton
 */
function IndustrySkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <Card key={i}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Skeleton className="h-8 w-8 rounded-full" />
                <Skeleton className="h-5 w-32" />
              </div>
              <div className="flex gap-2">
                <Skeleton className="h-5 w-20" />
                <Skeleton className="h-5 w-16" />
              </div>
            </div>
          </CardHeader>
        </Card>
      ))}
    </div>
  )
}

/**
 * Empty state
 */
function EmptyState() {
  return (
    <Card>
      <CardContent className="py-12">
        <div className="flex flex-col items-center justify-center text-center">
          <Factory className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-2">No Industry Jobs</h3>
          <p className="text-muted-foreground max-w-sm">
            None of your characters have active industry jobs.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Main Industry page
 */
export function Industry() {
  const { characters, selectedCharacter, isLoading: isLoadingChars } = useCharacterContext()
  const { groups: allGroups, isLoading: isLoadingJobs } = useAllCharacterIndustry(characters)

  const isLoading = isLoadingChars || isLoadingJobs

  // Filter groups based on selected character
  const groups = useMemo(() => {
    if (!selectedCharacter) return allGroups
    return allGroups.filter((g) => g.character_id === selectedCharacter.character_id)
  }, [allGroups, selectedCharacter])

  // Calculate totals for filtered groups
  const totalActiveJobs = groups.reduce((sum, g) => sum + g.active_jobs, 0)
  const totalJobs = groups.reduce((sum, g) => sum + g.total_jobs, 0)
  const charactersWithJobs = groups.filter((g) => g.jobs.length > 0).length

  // Count jobs by activity for filtered groups
  const jobsByActivity = useMemo(() => {
    const counts: Record<number, number> = {}
    for (const group of groups) {
      for (const job of group.jobs) {
        counts[job.activity_id] = (counts[job.activity_id] || 0) + 1
      }
    }
    return counts
  }, [groups])

  if (isLoading) {
    return (
      <div>
        <Header title="Industry" subtitle="Manufacturing & Research" />
        <div className="p-6">
          <IndustrySkeleton />
        </div>
      </div>
    )
  }

  return (
    <div>
      <Header title="Industry" subtitle="Manufacturing & Research" />

      <div className="p-6 space-y-4">
        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-500/20">
                  <Factory className="h-5 w-5 text-green-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold">{totalActiveJobs}</div>
                  <div className="text-xs text-muted-foreground">Active Jobs</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/20">
                  <Users className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold">{charactersWithJobs}</div>
                  <div className="text-xs text-muted-foreground">Characters Working</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Activity breakdown */}
          {Object.entries(jobsByActivity).slice(0, 2).map(([activityId, count]) => {
            const activity = ACTIVITY_MAP[Number(activityId)]
            if (!activity) return null
            const Icon = activity.icon
            return (
              <Card key={activityId}>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-3">
                    <div className={cn('p-2 rounded-lg', `bg-${activity.color.split('-')[1]}-500/20`)}>
                      <Icon className={cn('h-5 w-5', activity.color)} />
                    </div>
                    <div>
                      <div className="text-2xl font-bold">{count}</div>
                      <div className="text-xs text-muted-foreground">{activity.name}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Character Groups */}
        {groups.length === 0 || totalJobs === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-3">
            {groups
              .filter((g) => g.jobs.length > 0)
              .map((group, index) => (
                <CharacterGroup
                  key={group.character_id}
                  group={group}
                  defaultExpanded={index === 0}
                />
              ))}
          </div>
        )}
      </div>
    </div>
  )
}
