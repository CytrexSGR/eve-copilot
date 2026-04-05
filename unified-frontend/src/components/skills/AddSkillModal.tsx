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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { Search, Plus, Check } from 'lucide-react'
import { skillsApi, type SkillInfo } from '@/api/skills'
import { skillPlansApi } from '@/api/skillPlans'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { cn } from '@/lib/utils'

interface AddSkillModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  planId: number
  existingSkillIds?: Set<number>
}

export function AddSkillModal({
  open,
  onOpenChange,
  planId,
  existingSkillIds = new Set(),
}: AddSkillModalProps) {
  const queryClient = useQueryClient()
  const { selectedCharacter } = useCharacterContext()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSkill, setSelectedSkill] = useState<SkillInfo | null>(null)
  const [targetLevel, setTargetLevel] = useState<string>('5')

  // Fetch all skills
  const { data: skillBrowser, isLoading } = useQuery({
    queryKey: ['skill-browser', selectedCharacter?.character_id],
    queryFn: () => skillsApi.getBrowser(selectedCharacter?.character_id),
    enabled: open,
  })

  // Filter skills based on search
  const filteredSkills = useMemo(() => {
    if (!skillBrowser?.groups) return []

    const query = searchQuery.toLowerCase().trim()
    const results: Array<{ skill: SkillInfo; groupName: string }> = []

    for (const group of skillBrowser.groups) {
      for (const skill of group.skills) {
        if (!query || skill.type_name.toLowerCase().includes(query)) {
          results.push({ skill, groupName: group.group_name })
        }
      }
    }

    // Sort alphabetically by skill name
    return results.sort((a, b) => a.skill.type_name.localeCompare(b.skill.type_name))
  }, [skillBrowser, searchQuery])

  // Add skill mutation
  const addSkill = useMutation({
    mutationFn: () => {
      if (!selectedSkill) throw new Error('No skill selected')
      return skillPlansApi.addItem(planId, selectedSkill.type_id, parseInt(targetLevel))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skill-plan-calc'] })
      queryClient.invalidateQueries({ queryKey: ['skill-plan', planId] })
      // Reset and close
      setSelectedSkill(null)
      setSearchQuery('')
      setTargetLevel('5')
      onOpenChange(false)
    },
  })

  const handleSelectSkill = (skill: SkillInfo) => {
    setSelectedSkill(skill)
    // Default to max level, but if already trained, default to next level
    if (skill.trained_level !== null && skill.trained_level < 5) {
      setTargetLevel(String(skill.trained_level + 1))
    } else {
      setTargetLevel('5')
    }
  }

  const handleClose = () => {
    setSelectedSkill(null)
    setSearchQuery('')
    setTargetLevel('5')
    onOpenChange(false)
  }

  const isSkillInPlan = (skillId: number) => existingSkillIds.has(skillId)

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Add Skill to Plan</DialogTitle>
        </DialogHeader>

        {/* Search Input */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search skills..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
            autoFocus
          />
        </div>

        {/* Skill List */}
        <ScrollArea className="flex-1 min-h-[300px] max-h-[400px] border rounded-md">
          {isLoading ? (
            <div className="p-4 space-y-2">
              {[...Array(8)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : filteredSkills.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              {searchQuery ? 'No skills found matching your search.' : 'No skills available.'}
            </div>
          ) : (
            <div className="p-2">
              {filteredSkills.map(({ skill, groupName }) => {
                const inPlan = isSkillInPlan(skill.type_id)
                const isSelected = selectedSkill?.type_id === skill.type_id

                return (
                  <button
                    key={skill.type_id}
                    onClick={() => !inPlan && handleSelectSkill(skill)}
                    disabled={inPlan}
                    className={cn(
                      'w-full text-left p-3 rounded-md transition-colors flex items-center justify-between',
                      isSelected && 'bg-primary/20 border border-primary',
                      !isSelected && !inPlan && 'hover:bg-secondary/50',
                      inPlan && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium truncate">{skill.type_name}</span>
                        {inPlan && (
                          <Badge variant="outline" className="text-xs">
                            <Check className="h-3 w-3 mr-1" />
                            In Plan
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                        <span>{groupName}</span>
                        <span>•</span>
                        <span>Rank {skill.rank}</span>
                        {skill.trained_level !== null && (
                          <>
                            <span>•</span>
                            <span className="text-green-400">Level {skill.trained_level}</span>
                          </>
                        )}
                      </div>
                    </div>
                    {isSelected && (
                      <div className="flex-shrink-0 ml-2">
                        <Check className="h-5 w-5 text-primary" />
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          )}
        </ScrollArea>

        {/* Selected Skill & Level */}
        {selectedSkill && (
          <div className="flex items-center gap-4 p-3 bg-secondary/30 rounded-md">
            <div className="flex-1">
              <span className="font-medium">{selectedSkill.type_name}</span>
              {selectedSkill.trained_level !== null && (
                <span className="text-sm text-muted-foreground ml-2">
                  (Currently Level {selectedSkill.trained_level})
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Train to:</span>
              <Select value={targetLevel} onValueChange={setTargetLevel}>
                <SelectTrigger className="w-20">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[1, 2, 3, 4, 5].map((level) => {
                    const disabled = selectedSkill.trained_level !== null && level <= selectedSkill.trained_level
                    return (
                      <SelectItem key={level} value={String(level)} disabled={disabled}>
                        Level {level}
                      </SelectItem>
                    )
                  })}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={() => addSkill.mutate()}
            disabled={!selectedSkill || addSkill.isPending}
          >
            <Plus className="h-4 w-4 mr-2" />
            {addSkill.isPending ? 'Adding...' : 'Add Skill'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
