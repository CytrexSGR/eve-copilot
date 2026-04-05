import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useLocation } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { skillsApi, type SkillInfo, type SkillGroup } from '@/api/skills'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { cn } from '@/lib/utils'
import {
  Search,
  BookOpen,
  Brain,
  Eye,
  Heart,
  Flame,
  ListOrdered,
  Rocket,
  ChevronDown,
  ChevronUp,
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

// Attribute icons and colors
const ATTRIBUTE_CONFIG: Record<string, { icon: React.ElementType; color: string }> = {
  intelligence: { icon: Brain, color: 'text-cyan-400' },
  memory: { icon: BookOpen, color: 'text-blue-400' },
  perception: { icon: Eye, color: 'text-red-400' },
  willpower: { icon: Flame, color: 'text-purple-400' },
  charisma: { icon: Heart, color: 'text-green-400' },
}

// Level colors
const LEVEL_COLORS: Record<number, string> = {
  0: 'text-gray-500',
  1: 'text-blue-400',
  2: 'text-blue-400',
  3: 'text-blue-400',
  4: 'text-blue-400',
  5: 'text-yellow-400',
}

// Roman numerals
const ROMAN = ['0', 'I', 'II', 'III', 'IV', 'V']

// Filter options
type FilterOption = 'all' | 'trained' | 'uninjected'

/**
 * Format SP value
 */
function formatSP(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`
  return value.toString()
}

/**
 * Calculate training time for a skill level
 */
function calculateTrainingTime(rank: number, fromLevel: number, toLevel: number, spPerMinute: number = 27): string {
  // SP required per level: 250 * rank * sqrt(32)^(level-1)
  const spForLevel = (level: number) => Math.ceil(250 * rank * Math.pow(Math.sqrt(32), level - 1))
  const spNeeded = spForLevel(toLevel) - (fromLevel > 0 ? spForLevel(fromLevel) : 0)
  const minutes = spNeeded / spPerMinute

  if (minutes < 60) return `${Math.ceil(minutes)}m`
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h ${Math.ceil(minutes % 60)}m`
  const days = Math.floor(minutes / 1440)
  const hours = Math.floor((minutes % 1440) / 60)
  return `${days}d ${hours}h`
}

/**
 * Single skill card - expandable with description
 */
function SkillCard({ skill }: { skill: SkillInfo }) {
  const [expanded, setExpanded] = useState(false)
  const level = skill.trained_level ?? 0
  const levelColor = LEVEL_COLORS[level] || LEVEL_COLORS[0]
  const primaryAttr = ATTRIBUTE_CONFIG[skill.primary_attribute] || ATTRIBUTE_CONFIG.perception
  const secondaryAttr = ATTRIBUTE_CONFIG[skill.secondary_attribute] || ATTRIBUTE_CONFIG.willpower
  const PrimaryIcon = primaryAttr.icon
  const SecondaryIcon = secondaryAttr.icon

  // Training time to next level
  const nextLevel = Math.min(level + 1, 5)
  const timeToNext = level < 5 ? calculateTrainingTime(skill.rank, level, nextLevel) : null

  return (
    <Card
      className={cn(
        "transition-colors cursor-pointer",
        expanded ? "bg-secondary/30" : "hover:bg-secondary/20"
      )}
      onClick={() => setExpanded(!expanded)}
    >
      <CardContent className="py-3 px-4">
        {/* Header row */}
        <div className="flex items-center justify-between gap-4">
          {/* Skill name and level */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium">{skill.type_name}</span>
              {level > 0 && (
                <Badge variant="outline" className={cn('text-xs', levelColor)}>
                  {ROMAN[level]}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1" title={`${skill.primary_attribute} / ${skill.secondary_attribute}`}>
                <PrimaryIcon className={cn('h-3 w-3', primaryAttr.color)} />
                <SecondaryIcon className={cn('h-3 w-3', secondaryAttr.color)} />
              </span>
              <span>Rank {skill.rank}</span>
              {skill.skillpoints !== null && skill.skillpoints > 0 && (
                <span>{formatSP(skill.skillpoints)} SP</span>
              )}
              {timeToNext && level < 5 && (
                <span className="text-blue-400">→ {ROMAN[nextLevel]} in ~{timeToNext}</span>
              )}
            </div>
          </div>

          {/* Right side: status + expand icon */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {level === 5 ? (
              <Badge className="bg-yellow-500/20 text-yellow-400">Maxed</Badge>
            ) : level > 0 ? (
              <Badge className="bg-blue-500/20 text-blue-400">Trained</Badge>
            ) : (
              <Badge variant="outline" className="text-gray-500">Not Injected</Badge>
            )}
            {expanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        </div>

        {/* Expanded content */}
        {expanded && (
          <div className="mt-3 pt-3 border-t border-border space-y-3">
            {/* Description */}
            {skill.description && (
              <p className="text-sm text-muted-foreground leading-relaxed">
                {skill.description}
              </p>
            )}

            {/* Training details */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Primary: </span>
                <span className={primaryAttr.color}>{skill.primary_attribute}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Secondary: </span>
                <span className={secondaryAttr.color}>{skill.secondary_attribute}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Training Multiplier: </span>
                <span>{skill.rank}x</span>
              </div>
              {skill.skillpoints !== null && (
                <div>
                  <span className="text-muted-foreground">Current SP: </span>
                  <span>{skill.skillpoints.toLocaleString()}</span>
                </div>
              )}
            </div>

            {/* Level progression */}
            {level < 5 && (
              <div className="pt-2">
                <div className="text-xs text-muted-foreground mb-2">Training Time per Level:</div>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map((lvl) => (
                    <div
                      key={lvl}
                      className={cn(
                        "flex-1 text-center py-1 rounded text-xs",
                        lvl <= level
                          ? "bg-blue-500/20 text-blue-400"
                          : "bg-secondary text-muted-foreground"
                      )}
                    >
                      <div className="font-medium">{ROMAN[lvl]}</div>
                      <div className="text-[10px]">
                        {lvl <= level ? '✓' : calculateTrainingTime(skill.rank, lvl - 1, lvl)}
                      </div>
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
 * Category sidebar item
 */
function CategoryItem({
  group,
  isSelected,
  trainedCount,
  onClick,
}: {
  group: SkillGroup
  isSelected: boolean
  trainedCount: number
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left px-3 py-2 rounded-lg transition-colors flex items-center justify-between',
        isSelected
          ? 'bg-primary text-primary-foreground'
          : 'hover:bg-secondary/50 text-muted-foreground hover:text-foreground'
      )}
    >
      <span className="truncate text-sm">{group.group_name}</span>
      <span className={cn(
        'text-xs',
        isSelected ? 'text-primary-foreground/70' : 'text-muted-foreground'
      )}>
        {trainedCount}/{group.skill_count}
      </span>
    </button>
  )
}

/**
 * Skill Browser Page
 */
export function SkillBrowser() {
  const { selectedCharacter } = useCharacterContext()
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filter, setFilter] = useState<FilterOption>('all')

  // Fetch skills
  const { data, isLoading, error } = useQuery({
    queryKey: ['skills-browser', selectedCharacter?.character_id],
    queryFn: () => skillsApi.getBrowser(selectedCharacter?.character_id),
    staleTime: 5 * 60 * 1000,
  })

  // Calculate trained counts per group
  const groupTrainedCounts = useMemo(() => {
    if (!data) return {}
    const counts: Record<number, number> = {}
    for (const group of data.groups) {
      counts[group.group_id] = group.skills.filter(s => (s.trained_level ?? 0) > 0).length
    }
    return counts
  }, [data])

  // Filter skills
  const filteredSkills = useMemo(() => {
    if (!data) return []

    let skills: SkillInfo[] = []

    // Get skills from selected group or all
    if (selectedGroupId === null) {
      skills = data.groups.flatMap(g => g.skills)
    } else {
      const group = data.groups.find(g => g.group_id === selectedGroupId)
      skills = group?.skills || []
    }

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      skills = skills.filter(s => s.type_name.toLowerCase().includes(query))
    }

    // Apply trained/uninjected filter
    if (filter === 'trained') {
      skills = skills.filter(s => (s.trained_level ?? 0) > 0)
    } else if (filter === 'uninjected') {
      skills = skills.filter(s => (s.trained_level ?? 0) === 0)
    }

    return skills
  }, [data, selectedGroupId, searchQuery, filter])

  // Calculate totals
  const totalTrained = useMemo(() => {
    if (!data) return 0
    return data.groups.reduce((sum, g) =>
      sum + g.skills.filter(s => (s.trained_level ?? 0) > 0).length, 0
    )
  }, [data])

  if (error) {
    return (
      <div className="flex-1 p-6">
        <Header title="Skill Browser" />
        <div className="text-red-400 mt-8">Error loading skills: {String(error)}</div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden">
      <div className="p-6 pb-0">
        <Header title="Skills" />
        <SkillsNav />
      </div>

      {/* Stats summary */}
      <div className="px-6 py-4 flex gap-4">
        <Card className="flex-1">
          <CardContent className="py-3 px-4">
            <div className="text-2xl font-bold">{data?.total_skills || 0}</div>
            <div className="text-xs text-muted-foreground">Total Skills</div>
          </CardContent>
        </Card>
        <Card className="flex-1">
          <CardContent className="py-3 px-4">
            <div className="text-2xl font-bold text-blue-400">{totalTrained}</div>
            <div className="text-xs text-muted-foreground">Trained</div>
          </CardContent>
        </Card>
        <Card className="flex-1">
          <CardContent className="py-3 px-4">
            <div className="text-2xl font-bold">{data?.groups.length || 0}</div>
            <div className="text-xs text-muted-foreground">Categories</div>
          </CardContent>
        </Card>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden px-6 pb-6 gap-4">
        {/* Sidebar - Categories */}
        <div className="w-56 flex-shrink-0 flex flex-col">
          <Card className="flex-1 overflow-hidden flex flex-col">
            <CardContent className="p-3 flex-1 overflow-auto">
              {isLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <Skeleton key={i} className="h-9 w-full" />
                  ))}
                </div>
              ) : (
                <div className="space-y-1">
                  {/* All skills option */}
                  <button
                    onClick={() => setSelectedGroupId(null)}
                    className={cn(
                      'w-full text-left px-3 py-2 rounded-lg transition-colors flex items-center justify-between',
                      selectedGroupId === null
                        ? 'bg-primary text-primary-foreground'
                        : 'hover:bg-secondary/50 text-muted-foreground hover:text-foreground'
                    )}
                  >
                    <span className="text-sm font-medium">All Skills</span>
                    <span className={cn(
                      'text-xs',
                      selectedGroupId === null ? 'text-primary-foreground/70' : 'text-muted-foreground'
                    )}>
                      {totalTrained}/{data?.total_skills || 0}
                    </span>
                  </button>

                  {/* Category list */}
                  {data?.groups.map(group => (
                    <CategoryItem
                      key={group.group_id}
                      group={group}
                      isSelected={selectedGroupId === group.group_id}
                      trainedCount={groupTrainedCounts[group.group_id] || 0}
                      onClick={() => setSelectedGroupId(group.group_id)}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Main area - Skills list */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Search and filter */}
          <div className="flex gap-3 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search skills..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as FilterOption)}
              className="px-3 py-2 rounded-lg bg-secondary border border-border text-sm"
            >
              <option value="all">All</option>
              <option value="trained">Trained</option>
              <option value="uninjected">Not Injected</option>
            </select>
          </div>

          {/* Skills list */}
          <Card className="flex-1 overflow-hidden">
            <CardContent className="p-3 h-full overflow-auto">
              {isLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 15 }).map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : filteredSkills.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                  No skills found
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredSkills.map(skill => (
                    <SkillCard key={skill.type_id} skill={skill} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
