import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { Search, Plus, Ship, AlertCircle, CheckCircle2 } from 'lucide-react'
import { skillsApi, type ShipSearchResult } from '@/api/skills'
import { skillPlansApi } from '@/api/skillPlans'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { cn } from '@/lib/utils'

interface AddShipModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  planId: number
  existingSkillIds?: Set<number>
}

const MASTERY_NAMES: Record<number, string> = {
  0: 'Basic',
  1: 'Standard',
  2: 'Improved',
  3: 'Advanced',
  4: 'Elite',
}

const MASTERY_COLORS: Record<number, string> = {
  0: 'text-gray-400',
  1: 'text-green-400',
  2: 'text-blue-400',
  3: 'text-purple-400',
  4: 'text-yellow-400',
}

export function AddShipModal({
  open,
  onOpenChange,
  planId,
  existingSkillIds = new Set(),
}: AddShipModalProps) {
  const queryClient = useQueryClient()
  const { selectedCharacter } = useCharacterContext()
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [selectedShip, setSelectedShip] = useState<ShipSearchResult | null>(null)
  const [_targetMastery, setTargetMastery] = useState<number>(1)

  // Debounce search
  const handleSearchChange = (value: string) => {
    setSearchQuery(value)
    // Simple debounce
    const timer = setTimeout(() => {
      if (value.length >= 2) {
        setDebouncedQuery(value)
      } else {
        setDebouncedQuery('')
      }
    }, 300)
    return () => clearTimeout(timer)
  }

  // Search ships
  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ['ship-search', debouncedQuery],
    queryFn: () => skillsApi.searchShips(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
  })

  // Get mastery for selected ship
  const { data: masteryData, isLoading: isLoadingMastery } = useQuery({
    queryKey: ['ship-mastery', selectedCharacter?.character_id, selectedShip?.typeID],
    queryFn: () => {
      if (!selectedCharacter || !selectedShip) throw new Error('Missing data')
      return skillsApi.getShipMastery(selectedCharacter.character_id, selectedShip.typeID)
    },
    enabled: !!selectedCharacter && !!selectedShip,
  })

  // Filter missing skills that aren't already in the plan
  const missingSkills = useMemo(() => {
    if (!masteryData?.missing_for_next_level) return []
    return masteryData.missing_for_next_level.filter(
      (skill) => !existingSkillIds.has(skill.skill_id)
    )
  }, [masteryData, existingSkillIds])

  // Skills already in plan
  const alreadyInPlan = useMemo(() => {
    if (!masteryData?.missing_for_next_level) return []
    return masteryData.missing_for_next_level.filter(
      (skill) => existingSkillIds.has(skill.skill_id)
    )
  }, [masteryData, existingSkillIds])

  // Add skills mutation
  const addSkills = useMutation({
    mutationFn: async () => {
      if (!missingSkills.length) throw new Error('No skills to add')
      const items = missingSkills.map((skill) => ({
        skill_type_id: skill.skill_id,
        target_level: skill.need,
      }))
      return skillPlansApi.addItemsBatch(planId, items)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skill-plan-calc'] })
      queryClient.invalidateQueries({ queryKey: ['skill-plan', planId] })
      handleClose()
    },
  })

  const handleSelectShip = (ship: ShipSearchResult) => {
    setSelectedShip(ship)
    setTargetMastery(1) // Reset to standard mastery
  }

  const handleClose = () => {
    setSelectedShip(null)
    setSearchQuery('')
    setDebouncedQuery('')
    setTargetMastery(1)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Ship className="h-5 w-5" />
            Add Ship Requirements to Plan
          </DialogTitle>
        </DialogHeader>

        {!selectedCharacter ? (
          <div className="flex items-center gap-2 p-4 bg-destructive/10 rounded-md text-destructive">
            <AlertCircle className="h-5 w-5" />
            <span>Please select a character first to check ship mastery.</span>
          </div>
        ) : !selectedShip ? (
          <>
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search ships (min 2 characters)..."
                value={searchQuery}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="pl-9"
                autoFocus
              />
            </div>

            {/* Search Results */}
            <ScrollArea className="flex-1 min-h-[300px] max-h-[400px] border rounded-md">
              {isSearching ? (
                <div className="p-4 space-y-2">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : !debouncedQuery ? (
                <div className="p-8 text-center text-muted-foreground">
                  Type at least 2 characters to search for ships.
                </div>
              ) : !searchResults?.results?.length ? (
                <div className="p-8 text-center text-muted-foreground">
                  No ships found matching "{debouncedQuery}".
                </div>
              ) : (
                <div className="p-2">
                  {searchResults.results.map((ship) => (
                    <button
                      key={ship.typeID}
                      onClick={() => handleSelectShip(ship)}
                      className={cn(
                        'w-full text-left p-3 rounded-md transition-colors',
                        'hover:bg-secondary/50 flex items-center justify-between'
                      )}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="font-medium truncate">{ship.typeName}</div>
                        <div className="text-xs text-muted-foreground">{ship.groupName}</div>
                      </div>
                      <Ship className="h-4 w-4 text-muted-foreground" />
                    </button>
                  ))}
                </div>
              )}
            </ScrollArea>
          </>
        ) : (
          <>
            {/* Selected Ship */}
            <div className="p-4 bg-secondary/30 rounded-md">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-lg">{selectedShip.typeName}</h3>
                  <p className="text-sm text-muted-foreground">{selectedShip.groupName}</p>
                </div>
                <Button variant="ghost" size="sm" onClick={() => setSelectedShip(null)}>
                  Change
                </Button>
              </div>

              {isLoadingMastery ? (
                <div className="mt-4 space-y-2">
                  <Skeleton className="h-4 w-48" />
                  <Skeleton className="h-4 w-32" />
                </div>
              ) : masteryData ? (
                <div className="mt-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">Current Mastery:</span>
                    <Badge
                      variant="outline"
                      className={MASTERY_COLORS[masteryData.mastery_level] || 'text-gray-400'}
                    >
                      {masteryData.mastery_name || MASTERY_NAMES[masteryData.mastery_level] || 'None'}
                    </Badge>
                  </div>
                  {masteryData.can_fly_effectively ? (
                    <div className="flex items-center gap-2 text-green-400 text-sm">
                      <CheckCircle2 className="h-4 w-4" />
                      Can fly effectively
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-yellow-400 text-sm">
                      <AlertCircle className="h-4 w-4" />
                      Missing skills to fly effectively
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            {/* Missing Skills */}
            <div className="flex-1 overflow-hidden">
              <h4 className="font-medium mb-2">
                Skills for Next Mastery Level
                {masteryData && (
                  <span className="text-muted-foreground ml-2">
                    ({MASTERY_NAMES[(masteryData.mastery_level + 1) as keyof typeof MASTERY_NAMES] || 'Next'})
                  </span>
                )}
              </h4>

              <ScrollArea className="h-[200px] border rounded-md">
                {isLoadingMastery ? (
                  <div className="p-4 space-y-2">
                    {[...Array(3)].map((_, i) => (
                      <Skeleton key={i} className="h-10 w-full" />
                    ))}
                  </div>
                ) : !masteryData?.missing_for_next_level?.length ? (
                  <div className="p-4 text-center text-muted-foreground">
                    {masteryData?.mastery_level === 4
                      ? 'Elite mastery achieved! No more skills needed.'
                      : 'No missing skills found.'}
                  </div>
                ) : (
                  <div className="p-2 space-y-1">
                    {masteryData.missing_for_next_level.map((skill) => {
                      const inPlan = existingSkillIds.has(skill.skill_id)
                      return (
                        <div
                          key={skill.skill_id}
                          className={cn(
                            'flex items-center justify-between p-2 rounded-md',
                            inPlan ? 'bg-secondary/30 opacity-60' : 'bg-secondary/10'
                          )}
                        >
                          <span className={cn('font-medium', inPlan && 'line-through')}>
                            {skill.skill}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-muted-foreground">
                              {skill.have} → {skill.need}
                            </span>
                            {inPlan && (
                              <Badge variant="outline" className="text-xs">
                                In Plan
                              </Badge>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </ScrollArea>

              {alreadyInPlan.length > 0 && missingSkills.length > 0 && (
                <p className="text-xs text-muted-foreground mt-2">
                  {alreadyInPlan.length} skill(s) already in plan will be skipped.
                </p>
              )}
            </div>
          </>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={() => addSkills.mutate()}
            disabled={
              !selectedShip ||
              !masteryData ||
              missingSkills.length === 0 ||
              addSkills.isPending
            }
          >
            <Plus className="h-4 w-4 mr-2" />
            {addSkills.isPending
              ? 'Adding...'
              : missingSkills.length > 0
              ? `Add ${missingSkills.length} Skill${missingSkills.length > 1 ? 's' : ''}`
              : 'No Skills to Add'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
