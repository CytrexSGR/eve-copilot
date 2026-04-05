import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { skillsApi, type FlyableShip } from '@/api/skills'
import { skillPlansApi } from '@/api/skillPlans'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { cn } from '@/lib/utils'
import {
  Search,
  Rocket,
  Star,
  AlertTriangle,
  CheckCircle2,
  BookOpen,
  ListOrdered,
  ClipboardList,
  Plus,
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

// Mastery level colors
const MASTERY_COLORS: Record<number, { color: string; bg: string }> = {
  0: { color: 'text-gray-500', bg: 'bg-gray-500/20' },
  1: { color: 'text-blue-400', bg: 'bg-blue-500/20' },
  2: { color: 'text-green-400', bg: 'bg-green-500/20' },
  3: { color: 'text-purple-400', bg: 'bg-purple-500/20' },
  4: { color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  5: { color: 'text-orange-400', bg: 'bg-orange-500/20' },
}

/**
 * Render mastery stars
 */
function MasteryStars({ level }: { level: number }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          className={cn(
            'h-4 w-4',
            i < level ? 'fill-yellow-400 text-yellow-400' : 'text-gray-600'
          )}
        />
      ))}
    </div>
  )
}

/**
 * Get ship icon URL
 */
function getShipIconUrl(typeId: number, size: 64 | 128 = 64): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

/**
 * Ship card in grid
 */
function ShipCard({
  ship,
  onClick,
}: {
  ship: FlyableShip
  onClick: () => void
}) {
  return (
    <Card
      className="cursor-pointer hover:bg-secondary/30 transition-colors"
      onClick={onClick}
    >
      <CardContent className="p-4 flex flex-col items-center text-center">
        <img
          src={getShipIconUrl(ship.type_id, 64)}
          alt={ship.ship}
          className="w-16 h-16 rounded-lg border border-border mb-2"
          loading="lazy"
          onError={(e) => {
            e.currentTarget.src = 'https://images.evetech.net/types/670/icon?size=64'
          }}
        />
        <div className="font-medium text-sm truncate w-full">{ship.ship}</div>
        <div className="mt-2">
          <MasteryStars level={ship.mastery} />
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Ship class sidebar item
 */
function ClassItem({
  className,
  count,
  isSelected,
  onClick,
}: {
  className: string
  count: number
  isSelected: boolean
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
      <span className="truncate text-sm">{className}</span>
      <Badge variant="outline" className={cn(
        'text-xs',
        isSelected ? 'border-primary-foreground/30' : ''
      )}>
        {count}
      </Badge>
    </button>
  )
}

/**
 * Ship detail modal
 */
function ShipDetailModal({
  open,
  onClose,
  characterId,
  shipTypeId,
  shipName,
}: {
  open: boolean
  onClose: () => void
  characterId: number
  shipTypeId: number
  shipName: string
}) {
  const queryClient = useQueryClient()
  const [selectedPlanId, setSelectedPlanId] = useState<string>('')

  const { data, isLoading } = useQuery({
    queryKey: ['ship-mastery', characterId, shipTypeId],
    queryFn: () => skillsApi.getShipMastery(characterId, shipTypeId),
    enabled: open && !!characterId && !!shipTypeId,
  })

  // Fetch skill plans for the dropdown
  const { data: plansData } = useQuery({
    queryKey: ['skill-plans'],
    queryFn: () => skillPlansApi.list(),
    enabled: open,
  })

  // Mutation for adding skills batch to a plan
  const addSkillsMutation = useMutation({
    mutationFn: (skills: { skill_type_id: number; target_level: number }[]) =>
      skillPlansApi.addItemsBatch(parseInt(selectedPlanId), skills),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skill-plans'] })
      queryClient.invalidateQueries({ queryKey: ['skill-plan', parseInt(selectedPlanId)] })
      setSelectedPlanId('')
    },
  })

  const handleAddToPlan = () => {
    if (!selectedPlanId || !data?.missing_for_next_level) return
    const skills = data.missing_for_next_level.map((skill) => ({
      skill_type_id: skill.skill_id,
      target_level: skill.need,
    }))
    addSkillsMutation.mutate(skills)
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <img
              src={getShipIconUrl(shipTypeId, 64)}
              alt={shipName}
              className="w-12 h-12 rounded-lg border border-border"
            />
            <div>
              <div>{shipName}</div>
              {data && (
                <div className="text-sm font-normal text-muted-foreground">
                  {data.ship_class}
                </div>
              )}
            </div>
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : data ? (
          <div className="space-y-4">
            {/* Mastery level */}
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Mastery Level</span>
              <div className="flex items-center gap-2">
                <MasteryStars level={data.mastery_level} />
                <Badge className={cn(
                  MASTERY_COLORS[data.mastery_level]?.bg,
                  MASTERY_COLORS[data.mastery_level]?.color
                )}>
                  {data.mastery_name}
                </Badge>
              </div>
            </div>

            {/* Can fly effectively */}
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Can Fly Effectively</span>
              {data.can_fly_effectively ? (
                <span className="text-green-400 flex items-center gap-1">
                  <CheckCircle2 className="h-4 w-4" />
                  Yes
                </span>
              ) : (
                <span className="text-yellow-400 flex items-center gap-1">
                  <AlertTriangle className="h-4 w-4" />
                  Missing Skills
                </span>
              )}
            </div>

            {/* Missing skills for next level */}
            {data.missing_for_next_level && data.missing_for_next_level.length > 0 && (
              <div>
                <div className="text-sm font-medium mb-2">Missing for next level:</div>
                <div className="space-y-1 max-h-40 overflow-auto">
                  {data.missing_for_next_level.map((skill, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between text-sm bg-secondary/50 rounded px-2 py-1"
                    >
                      <span className="truncate">{skill.skill}</span>
                      <Badge variant="outline" className="text-xs">
                        {skill.have} → {skill.need}
                      </Badge>
                    </div>
                  ))}
                </div>

                {/* Add to Plan */}
                {plansData && plansData.length > 0 && (
                  <div className="mt-4 flex gap-2">
                    <Select value={selectedPlanId} onValueChange={setSelectedPlanId}>
                      <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Select a plan..." />
                      </SelectTrigger>
                      <SelectContent>
                        {plansData.map((plan) => (
                          <SelectItem key={plan.id} value={String(plan.id)}>
                            {plan.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      size="sm"
                      onClick={handleAddToPlan}
                      disabled={!selectedPlanId || addSkillsMutation.isPending}
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      Add All
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

/**
 * Ship Mastery Page
 */
export function ShipMastery() {
  const { selectedCharacter } = useCharacterContext()
  const [selectedClass, setSelectedClass] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [minMastery, setMinMastery] = useState(1)
  const [selectedShip, setSelectedShip] = useState<FlyableShip | null>(null)

  // Fetch flyable ships
  const { data, isLoading, error } = useQuery({
    queryKey: ['flyable-ships', selectedCharacter?.character_id],
    queryFn: () => skillsApi.getFlyableShips(selectedCharacter!.character_id),
    enabled: !!selectedCharacter?.character_id,
    staleTime: 5 * 60 * 1000,
  })

  // Calculate counts per class and filter ships
  const { classCounts, filteredShips, totalShips, highMasteryCount, shipClasses } = useMemo(() => {
    if (!data?.flyable_ships) {
      return { classCounts: {}, filteredShips: [], totalShips: 0, highMasteryCount: 0, shipClasses: [] }
    }

    const counts: Record<string, number> = {}
    let allShips: FlyableShip[] = []
    let highCount = 0
    let total = 0

    for (const [className, ships] of Object.entries(data.flyable_ships)) {
      counts[className] = ships.length
      total += ships.length
      allShips = allShips.concat(ships.map(s => ({ ...s, _class: className } as FlyableShip & { _class: string })))
      highCount += ships.filter(s => s.mastery >= 4).length
    }

    // Filter by class
    let filtered = selectedClass
      ? data.flyable_ships[selectedClass] || []
      : allShips

    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(s => s.ship.toLowerCase().includes(query))
    }

    // Filter by mastery
    filtered = filtered.filter(s => s.mastery >= minMastery)

    // Sort by mastery descending, then name
    filtered = [...filtered].sort((a, b) => {
      if (b.mastery !== a.mastery) return b.mastery - a.mastery
      return a.ship.localeCompare(b.ship)
    })

    return {
      classCounts: counts,
      filteredShips: filtered,
      totalShips: total,
      highMasteryCount: highCount,
      shipClasses: Object.keys(data.flyable_ships).sort(),
    }
  }, [data, selectedClass, searchQuery, minMastery])

  if (!selectedCharacter) {
    return (
      <div className="flex-1 p-6">
        <Header title="Ship Mastery" />
        <div className="text-muted-foreground mt-8 text-center">
          Select a character to view ship mastery
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex-1 p-6">
        <Header title="Ship Mastery" />
        <div className="text-red-400 mt-8">Error loading ships: {String(error)}</div>
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
          <CardContent className="py-3 px-4 flex items-center gap-3">
            <Rocket className="h-5 w-5 text-blue-400" />
            <div>
              <div className="text-2xl font-bold">{totalShips}</div>
              <div className="text-xs text-muted-foreground">Flyable Ships</div>
            </div>
          </CardContent>
        </Card>
        <Card className="flex-1">
          <CardContent className="py-3 px-4 flex items-center gap-3">
            <Star className="h-5 w-5 text-yellow-400 fill-yellow-400" />
            <div>
              <div className="text-2xl font-bold text-yellow-400">{highMasteryCount}</div>
              <div className="text-xs text-muted-foreground">Mastery 4+</div>
            </div>
          </CardContent>
        </Card>
        <Card className="flex-1">
          <CardContent className="py-3 px-4 flex items-center gap-3">
            <div className="text-2xl font-bold">{Object.keys(classCounts).length}</div>
            <div className="text-xs text-muted-foreground">Ship Classes</div>
          </CardContent>
        </Card>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden px-6 pb-6 gap-4">
        {/* Sidebar - Ship Classes */}
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
                  {/* All ships option */}
                  <button
                    onClick={() => setSelectedClass(null)}
                    className={cn(
                      'w-full text-left px-3 py-2 rounded-lg transition-colors flex items-center justify-between',
                      selectedClass === null
                        ? 'bg-primary text-primary-foreground'
                        : 'hover:bg-secondary/50 text-muted-foreground hover:text-foreground'
                    )}
                  >
                    <span className="text-sm font-medium">All Ships</span>
                    <Badge variant="outline" className={cn(
                      'text-xs',
                      selectedClass === null ? 'border-primary-foreground/30' : ''
                    )}>
                      {totalShips}
                    </Badge>
                  </button>

                  {/* Class list */}
                  {shipClasses.map(className => (
                    <ClassItem
                      key={className}
                      className={className}
                      count={classCounts[className] || 0}
                      isSelected={selectedClass === className}
                      onClick={() => setSelectedClass(className)}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Main area - Ships grid */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Search and filter */}
          <div className="flex gap-3 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search ships..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <select
              value={minMastery}
              onChange={(e) => setMinMastery(Number(e.target.value))}
              className="px-3 py-2 rounded-lg bg-secondary border border-border text-sm"
            >
              <option value={1}>Mastery 1+</option>
              <option value={2}>Mastery 2+</option>
              <option value={3}>Mastery 3+</option>
              <option value={4}>Mastery 4+</option>
              <option value={5}>Mastery 5</option>
            </select>
          </div>

          {/* Ships grid */}
          <Card className="flex-1 overflow-hidden">
            <CardContent className="p-4 h-full overflow-auto">
              {isLoading ? (
                <div className="grid grid-cols-4 gap-4">
                  {Array.from({ length: 12 }).map((_, i) => (
                    <Skeleton key={i} className="h-32 w-full" />
                  ))}
                </div>
              ) : filteredShips.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                  No ships found
                </div>
              ) : (
                <div className="grid grid-cols-4 gap-4">
                  {filteredShips.map(ship => (
                    <ShipCard
                      key={ship.type_id}
                      ship={ship}
                      onClick={() => setSelectedShip(ship)}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Ship detail modal */}
      {selectedShip && selectedCharacter && (
        <ShipDetailModal
          open={!!selectedShip}
          onClose={() => setSelectedShip(null)}
          characterId={selectedCharacter.character_id}
          shipTypeId={selectedShip.type_id}
          shipName={selectedShip.ship}
        />
      )}
    </div>
  )
}
