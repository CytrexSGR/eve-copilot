import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { skillPlansApi } from '@/api/skillPlans'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { cn } from '@/lib/utils'
import { AddSkillModal } from '@/components/skills/AddSkillModal'
import {
  BookOpen,
  ListOrdered,
  Rocket,
  ClipboardList,
  Plus,
  Trash2,
  Clock,
  Zap,
  GripVertical,
} from 'lucide-react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

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

// Sortable skill item
function SortableSkillItem({ item, onDelete }: { item: any; onDelete: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: item.item_id,
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-3 p-3 bg-secondary/30 rounded-lg border border-border/50"
    >
      <button {...attributes} {...listeners} className="cursor-grab text-muted-foreground hover:text-foreground">
        <GripVertical className="h-4 w-4" />
      </button>
      <div className="flex-1">
        <div className="font-medium">{item.skill_name}</div>
        <div className="text-sm text-muted-foreground">
          {ROMAN[item.from_level]} → {ROMAN[item.to_level]}
        </div>
      </div>
      <div className="text-right">
        <div className="text-sm font-mono">{item.training_time_formatted}</div>
        <div className="text-xs text-muted-foreground">{item.sp_required?.toLocaleString()} SP</div>
      </div>
      <Button variant="ghost" size="sm" onClick={onDelete}>
        <Trash2 className="h-4 w-4 text-red-400" />
      </Button>
    </div>
  )
}

export function SkillPlanner() {
  const { selectedCharacter } = useCharacterContext()
  const queryClient = useQueryClient()
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null)
  const [showNewPlanDialog, setShowNewPlanDialog] = useState(false)
  const [showAddSkillModal, setShowAddSkillModal] = useState(false)
  const [newPlanName, setNewPlanName] = useState('')

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  // Fetch plans
  const { data: plans, isLoading: plansLoading } = useQuery({
    queryKey: ['skill-plans'],
    queryFn: () => skillPlansApi.list(),
  })

  // Fetch selected plan calculation
  const { data: calculation, isLoading: calcLoading } = useQuery({
    queryKey: ['skill-plan-calc', selectedPlanId, selectedCharacter?.character_id],
    queryFn: () => skillPlansApi.calculate(selectedPlanId!, selectedCharacter!.character_id),
    enabled: !!selectedPlanId && !!selectedCharacter,
  })

  // Create plan mutation
  const createPlan = useMutation({
    mutationFn: () => skillPlansApi.create(selectedCharacter!.character_id, newPlanName),
    onSuccess: (plan) => {
      queryClient.invalidateQueries({ queryKey: ['skill-plans'] })
      setSelectedPlanId(plan.id)
      setShowNewPlanDialog(false)
      setNewPlanName('')
    },
  })

  // Delete plan mutation
  const deletePlan = useMutation({
    mutationFn: (planId: number) => skillPlansApi.delete(planId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skill-plans'] })
      setSelectedPlanId(null)
    },
  })

  // Delete item mutation
  const deleteItem = useMutation({
    mutationFn: ({ planId, itemId }: { planId: number; itemId: number }) =>
      skillPlansApi.deleteItem(planId, itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skill-plan-calc'] })
    },
  })

  // Reorder mutation
  const reorderItems = useMutation({
    mutationFn: ({ planId, itemIds }: { planId: number; itemIds: number[] }) =>
      skillPlansApi.reorder(planId, itemIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skill-plan-calc'] })
    },
  })

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id || !calculation || !selectedPlanId) return

    const oldIndex = calculation.items.findIndex((i) => i.item_id === active.id)
    const newIndex = calculation.items.findIndex((i) => i.item_id === over.id)
    const newOrder = arrayMove(calculation.items, oldIndex, newIndex)

    reorderItems.mutate({
      planId: selectedPlanId,
      itemIds: newOrder.map((i) => i.item_id),
    })
  }

  if (!selectedCharacter) {
    return (
      <div className="flex-1 p-6">
        <Header title="Skill Planner" />
        <div className="text-muted-foreground mt-8 text-center">
          Select a character to use the skill planner
        </div>
      </div>
    )
  }

  const selectedPlan = plans?.find((p) => p.id === selectedPlanId)

  return (
    <div className="flex-1 p-6 overflow-auto">
      <Header title="Skills" />
      <SkillsNav />

      <div className="flex gap-6 mt-6">
        {/* Plan List Sidebar */}
        <Card className="w-64 flex-shrink-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center justify-between">
              My Plans
              <Button size="sm" variant="ghost" onClick={() => setShowNewPlanDialog(true)}>
                <Plus className="h-4 w-4" />
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {plansLoading ? (
              <Skeleton className="h-20 w-full" />
            ) : plans?.length === 0 ? (
              <div className="text-sm text-muted-foreground text-center py-4">
                No plans yet
              </div>
            ) : (
              plans?.map((plan) => (
                <button
                  key={plan.id}
                  onClick={() => setSelectedPlanId(plan.id)}
                  className={cn(
                    'w-full text-left p-2 rounded-lg transition-colors',
                    selectedPlanId === plan.id
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-secondary/50'
                  )}
                >
                  <div className="font-medium text-sm">{plan.name}</div>
                  <div className="text-xs opacity-70">{plan.skill_count || 0} skills</div>
                </button>
              ))
            )}
          </CardContent>
        </Card>

        {/* Plan Editor */}
        <div className="flex-1">
          {!selectedPlanId ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                Select a plan or create a new one
              </CardContent>
            </Card>
          ) : calcLoading ? (
            <Skeleton className="h-96 w-full" />
          ) : calculation ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>{selectedPlan?.name}</span>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">
                      <Clock className="h-3 w-3 mr-1" />
                      {calculation.total_training_time_formatted}
                    </Badge>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setShowAddSkillModal(true)}
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      Add Skill
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => deletePlan.mutate(selectedPlanId)}
                    >
                      <Trash2 className="h-4 w-4 text-red-400" />
                    </Button>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {/* Remap suggestions */}
                {calculation.remap_suggestions.length > 0 && (
                  <div className="mb-4 p-3 bg-blue-500/10 rounded-lg border border-blue-500/30">
                    <div className="flex items-center gap-2 text-blue-400 text-sm font-medium mb-2">
                      <Zap className="h-4 w-4" />
                      Remap Suggestion
                    </div>
                    {calculation.remap_suggestions.map((r, i) => (
                      <div key={i} className="text-sm">
                        After {r.after_skill_name}: Save {r.time_saved_formatted}
                      </div>
                    ))}
                  </div>
                )}

                {/* Skill list */}
                {calculation.items.length === 0 ? (
                  <div className="text-center text-muted-foreground py-8">
                    No skills in plan. Add skills to get started.
                  </div>
                ) : (
                  <DndContext
                    sensors={sensors}
                    collisionDetection={closestCenter}
                    onDragEnd={handleDragEnd}
                  >
                    <SortableContext
                      items={calculation.items.map((i) => i.item_id)}
                      strategy={verticalListSortingStrategy}
                    >
                      <div className="space-y-2">
                        {calculation.items.map((item) => (
                          <SortableSkillItem
                            key={item.item_id}
                            item={item}
                            onDelete={() =>
                              deleteItem.mutate({ planId: selectedPlanId, itemId: item.item_id })
                            }
                          />
                        ))}
                      </div>
                    </SortableContext>
                  </DndContext>
                )}
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>

      {/* New Plan Dialog */}
      <Dialog open={showNewPlanDialog} onOpenChange={setShowNewPlanDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Plan</DialogTitle>
          </DialogHeader>
          <Input
            placeholder="Plan name..."
            value={newPlanName}
            onChange={(e) => setNewPlanName(e.target.value)}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowNewPlanDialog(false)}>
              Cancel
            </Button>
            <Button onClick={() => createPlan.mutate()} disabled={!newPlanName.trim()}>
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Skill Modal */}
      {selectedPlanId && (
        <AddSkillModal
          open={showAddSkillModal}
          onOpenChange={setShowAddSkillModal}
          planId={selectedPlanId}
          existingSkillIds={new Set(calculation?.items?.map((i: any) => i.skill_type_id) || [])}
        />
      )}
    </div>
  )
}
