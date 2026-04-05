import { Plus, Target } from 'lucide-react'
import { Button } from '../ui/button'
import { ScrollArea } from '../ui/scroll-area'
import { PlanCard } from './PlanCard'
import { useCopilot } from '../../contexts/CopilotContext'
import { agentApi } from '../../api/agent'

interface PlanPanelProps {
  onCreatePlan?: () => void
}

export function PlanPanel({ onCreatePlan }: PlanPanelProps) {
  const { plans, selectedPlanId, selectPlan, refreshPlans } = useCopilot()

  const handlePause = async (planId: number) => {
    try {
      await agentApi.updatePlan(planId, { status: 'paused' })
      await refreshPlans()
    } catch (error) {
      console.error('Failed to pause plan:', error)
    }
  }

  const handleCancel = async (planId: number) => {
    try {
      await agentApi.updatePlan(planId, { status: 'cancelled' })
      await refreshPlans()
    } catch (error) {
      console.error('Failed to cancel plan:', error)
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold">Plans</h2>
        {onCreatePlan && (
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={onCreatePlan}
          >
            <Plus className="h-4 w-4" />
            <span className="sr-only">Create plan</span>
          </Button>
        )}
      </div>

      {/* Plan list */}
      <ScrollArea className="flex-1">
        {plans.length > 0 ? (
          <div className="space-y-3 p-4">
            {plans.map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                isSelected={selectedPlanId === plan.id}
                onSelect={() => selectPlan(plan.id)}
                onPause={() => handlePause(plan.id)}
                onCancel={() => handleCancel(plan.id)}
              />
            ))}
          </div>
        ) : (
          /* Empty state */
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <div className="rounded-full bg-muted p-3 mb-3">
              <Target className="h-6 w-6 text-muted-foreground" />
            </div>
            <h3 className="text-sm font-medium mb-1">No active plans</h3>
            <p className="text-xs text-muted-foreground mb-4">
              Create a plan to track your EVE goals
            </p>
            {onCreatePlan && (
              <Button variant="outline" size="sm" onClick={onCreatePlan}>
                <Plus className="mr-2 h-4 w-4" />
                Create Plan
              </Button>
            )}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
