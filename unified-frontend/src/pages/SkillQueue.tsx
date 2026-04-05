import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useLocation } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { charactersApi } from '@/api/characters'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { cn } from '@/lib/utils'
import type { SkillQueueItem } from '@/types/character'
import {
  Clock,
  Calendar,
  ListOrdered,
  Zap,
  CheckCircle2,
  BookOpen,
  Rocket,
  ChevronDown,
  ChevronUp,
  Unlock,
  ClipboardList,
} from 'lucide-react'

// Skills sub-navigation tabs
const skillsTabs = [
  { title: 'Browser', href: '/skills', icon: BookOpen },
  { title: 'Queue', href: '/skills/queue', icon: ListOrdered },
  { title: 'Mastery', href: '/skills/mastery', icon: Rocket },
  { title: 'Planner', href: '/skills/planner', icon: ClipboardList },
]

function SkillsNav() {
  const location = useLocation()
  return (
    <div className="flex gap-2 mb-4">
      {skillsTabs.map((tab) => {
        const isActive = location.pathname === tab.href
        const Icon = tab.icon
        return (
          <Link
            key={tab.href}
            to={tab.href}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              isActive
                ? 'bg-primary text-primary-foreground'
                : 'bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground'
            )}
          >
            <Icon className="h-4 w-4" />
            {tab.title}
          </Link>
        )
      })}
    </div>
  )
}

// Roman numerals
const ROMAN = ['0', 'I', 'II', 'III', 'IV', 'V']

/**
 * Format duration to human readable
 */
function formatDuration(ms: number): string {
  if (ms <= 0) return '0s'

  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) {
    const remainingHours = hours % 24
    return `${days}d ${remainingHours}h`
  }
  if (hours > 0) {
    const remainingMinutes = minutes % 60
    return `${hours}h ${remainingMinutes}m`
  }
  if (minutes > 0) {
    return `${minutes}m`
  }
  return `${seconds}s`
}

/**
 * Format date to locale string
 */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Calculate time remaining from now to finish date
 */
function getTimeRemaining(finishDate: string): number {
  return new Date(finishDate).getTime() - Date.now()
}

/**
 * Format SP value
 */
function formatSP(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`
  return value.toString()
}

/**
 * Currently training hero card
 */
function CurrentlyTraining({ skill }: { skill: SkillQueueItem }) {
  const [expanded, setExpanded] = useState(false)
  const progress = skill.training_progress || 0
  const timeRemaining = getTimeRemaining(skill.finish_date)

  return (
    <Card
      className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border-blue-500/30 cursor-pointer"
      onClick={() => setExpanded(!expanded)}
    >
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-blue-400" />
            Currently Training
          </span>
          {expanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="text-xl font-bold">
              {skill.skill_name}
              <Badge variant="outline" className="ml-2 text-blue-400">
                {ROMAN[skill.finished_level]}
              </Badge>
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              {formatSP(skill.training_start_sp)} / {formatSP(skill.level_end_sp)} SP
              <span className="ml-2">({formatSP(skill.sp_remaining)} remaining)</span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-lg font-mono text-blue-400">
              {formatDuration(timeRemaining)}
            </div>
            <div className="text-xs text-muted-foreground">
              {formatDate(skill.finish_date)}
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full h-3 bg-secondary rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="text-xs text-muted-foreground mt-1 text-center">
          {progress.toFixed(1)}% complete
        </div>

        {/* Expanded content */}
        {expanded && (
          <div className="mt-4 pt-4 border-t border-border/50 space-y-3">
            {/* Description */}
            {skill.skill_description && (
              <p className="text-sm text-muted-foreground leading-relaxed">
                {skill.skill_description}
              </p>
            )}

            {/* Unlocks at this level */}
            {skill.unlocks_at_level && skill.unlocks_at_level.length > 0 && (
              <div>
                <div className="text-sm font-medium flex items-center gap-2 mb-2">
                  <Unlock className="h-4 w-4 text-green-400" />
                  Unlocks at Level {ROMAN[skill.finished_level]}:
                </div>
                <div className="grid grid-cols-2 gap-2 max-h-32 overflow-auto">
                  {skill.unlocks_at_level.map((unlock, i) => (
                    <div
                      key={i}
                      className="text-xs bg-secondary/50 rounded px-2 py-1 flex items-center justify-between"
                    >
                      <span className="truncate">{unlock.type_name}</span>
                      <Badge variant="outline" className="text-[10px] ml-1">
                        {unlock.category_name}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

/**
 * Queue table row - expandable
 */
function QueueRow({ skill, index }: { skill: SkillQueueItem; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const isFirst = index === 0
  const timeRemaining = getTimeRemaining(skill.finish_date)
  const isComplete = timeRemaining <= 0

  return (
    <>
      <tr
        className={cn(
          'border-b border-border/50 transition-colors cursor-pointer hover:bg-secondary/30',
          isFirst && 'bg-blue-500/5',
          expanded && 'bg-secondary/20'
        )}
        onClick={() => setExpanded(!expanded)}
      >
        <td className="py-3 px-4 text-center text-muted-foreground">
          {skill.queue_position + 1}
        </td>
        <td className="py-3 px-4">
          <div className="flex items-center gap-2">
            <span className="font-medium">{skill.skill_name}</span>
            {expanded ? (
              <ChevronUp className="h-3 w-3 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-3 w-3 text-muted-foreground" />
            )}
          </div>
        </td>
        <td className="py-3 px-4 text-center">
          <Badge variant="outline">
            {ROMAN[skill.finished_level - 1] || '0'} → {ROMAN[skill.finished_level]}
          </Badge>
        </td>
        <td className="py-3 px-4 text-right">
          {isComplete ? (
            <span className="text-green-400 flex items-center justify-end gap-1">
              <CheckCircle2 className="h-4 w-4" />
              Complete
            </span>
          ) : isFirst ? (
            <span className="text-blue-400">{formatDuration(timeRemaining)} (active)</span>
          ) : (
            <span className="text-muted-foreground">{formatDate(skill.finish_date)}</span>
          )}
        </td>
      </tr>
      {/* Expanded row */}
      {expanded && (
        <tr className="bg-secondary/10">
          <td colSpan={4} className="px-4 py-3">
            <div className="space-y-3">
              {/* Description */}
              {skill.skill_description && (
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {skill.skill_description}
                </p>
              )}

              {/* SP Details */}
              <div className="flex gap-6 text-sm">
                <div>
                  <span className="text-muted-foreground">SP: </span>
                  <span>{formatSP(skill.level_start_sp)} → {formatSP(skill.level_end_sp)}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Remaining: </span>
                  <span>{formatSP(skill.sp_remaining)}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Start: </span>
                  <span>{formatDate(skill.start_date)}</span>
                </div>
              </div>

              {/* Unlocks at this level */}
              {skill.unlocks_at_level && skill.unlocks_at_level.length > 0 && (
                <div>
                  <div className="text-sm font-medium flex items-center gap-2 mb-2">
                    <Unlock className="h-4 w-4 text-green-400" />
                    Unlocks at Level {ROMAN[skill.finished_level]}:
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {skill.unlocks_at_level.slice(0, 10).map((unlock, i) => (
                      <Badge
                        key={i}
                        variant="outline"
                        className="text-xs"
                      >
                        {unlock.type_name}
                      </Badge>
                    ))}
                    {skill.unlocks_at_level.length > 10 && (
                      <Badge variant="outline" className="text-xs text-muted-foreground">
                        +{skill.unlocks_at_level.length - 10} more
                      </Badge>
                    )}
                  </div>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

/**
 * Skill Queue Page
 */
export function SkillQueue() {
  const { selectedCharacter } = useCharacterContext()

  // Fetch skill queue
  const { data, isLoading, error } = useQuery({
    queryKey: ['skill-queue', selectedCharacter?.character_id],
    queryFn: () => charactersApi.getSkillQueue(selectedCharacter!.character_id),
    enabled: !!selectedCharacter?.character_id,
    refetchInterval: 60000, // Refresh every minute
  })

  // Calculate totals
  const stats = useMemo(() => {
    if (!data?.queue || data.queue.length === 0) {
      return { totalTime: 0, finishDate: null, count: 0 }
    }

    const lastSkill = data.queue[data.queue.length - 1]
    const finishDate = lastSkill?.finish_date
    const totalTime = finishDate ? getTimeRemaining(finishDate) : 0

    return {
      totalTime,
      finishDate,
      count: data.queue.length,
    }
  }, [data])

  const currentSkill = data?.queue?.[0]

  if (!selectedCharacter) {
    return (
      <div className="flex-1 p-6">
        <Header title="Skill Queue" />
        <div className="text-muted-foreground mt-8 text-center">
          Select a character to view skill queue
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex-1 p-6">
        <Header title="Skill Queue" />
        <div className="text-red-400 mt-8">Error loading skill queue: {String(error)}</div>
      </div>
    )
  }

  return (
    <div className="flex-1 p-6 overflow-auto">
      <Header title="Skills" />
      <SkillsNav />

      {/* Stats summary */}
      <div className="grid grid-cols-3 gap-4 mt-6">
        <Card>
          <CardContent className="py-4 px-4 flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/20">
              <ListOrdered className="h-5 w-5 text-blue-400" />
            </div>
            <div>
              <div className="text-2xl font-bold">{stats.count}</div>
              <div className="text-xs text-muted-foreground">Skills in Queue</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 px-4 flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/20">
              <Clock className="h-5 w-5 text-purple-400" />
            </div>
            <div>
              <div className="text-2xl font-bold font-mono">
                {stats.totalTime > 0 ? formatDuration(stats.totalTime) : '-'}
              </div>
              <div className="text-xs text-muted-foreground">Total Time</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 px-4 flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/20">
              <Calendar className="h-5 w-5 text-green-400" />
            </div>
            <div>
              <div className="text-2xl font-bold">
                {stats.finishDate ? formatDate(stats.finishDate) : '-'}
              </div>
              <div className="text-xs text-muted-foreground">Completes</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Currently training */}
      {isLoading ? (
        <Skeleton className="h-40 w-full mt-6" />
      ) : currentSkill ? (
        <div className="mt-6">
          <CurrentlyTraining skill={currentSkill} />
        </div>
      ) : null}

      {/* Queue table */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-lg">Training Queue</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-4 space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : !data?.queue || data.queue.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              Skill queue is empty
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-border text-left text-sm text-muted-foreground">
                  <th className="py-3 px-4 w-16 text-center">#</th>
                  <th className="py-3 px-4">Skill</th>
                  <th className="py-3 px-4 w-32 text-center">Level</th>
                  <th className="py-3 px-4 w-48 text-right">Time / Finish</th>
                </tr>
              </thead>
              <tbody>
                {data.queue.map((skill, index) => (
                  <QueueRow key={skill.skill_id + '-' + skill.finished_level} skill={skill} index={index} />
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
