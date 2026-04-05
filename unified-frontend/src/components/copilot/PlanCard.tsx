import { MoreVertical, Pause, X } from 'lucide-react'
import { Card, CardContent, CardHeader } from '../ui/card'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Progress } from '../ui/progress'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu'
import { cn } from '../../lib/utils'
import { MilestoneList } from './MilestoneList'
import type { Plan } from '../../api/agent'

interface PlanCardProps {
  plan: Plan
  isSelected: boolean
  onSelect: () => void
  onPause?: () => void
  onCancel?: () => void
}

const GOAL_TYPE_EMOJI: Record<string, string> = {
  ship: '\u{1F680}',      // Rocket
  isk: '\u{1F4B0}',       // Money bag
  skill: '\u{1F4DA}',     // Books
  production: '\u{1F3ED}', // Factory
  pi: '\u{1F30D}',        // Earth globe
  custom: '\u2728',       // Sparkles
}

const STATUS_VARIANT: Record<
  Plan['status'],
  'default' | 'secondary' | 'destructive' | 'outline' | 'warning' | 'success'
> = {
  draft: 'secondary',
  active: 'default',
  paused: 'warning',
  completed: 'success',
  cancelled: 'destructive',
}

export function PlanCard({
  plan,
  isSelected,
  onSelect,
  onPause,
  onCancel,
}: PlanCardProps) {
  // Extract goal type from goal string (e.g., "ship:Golem" -> "ship")
  const goalType = plan.goal?.split(':')[0] || 'custom'
  const emoji = GOAL_TYPE_EMOJI[goalType] || GOAL_TYPE_EMOJI.custom

  // Calculate progress from milestones
  const milestones = plan.milestones || []
  const completedMilestones = milestones.filter(
    (m) => m.status === 'completed'
  ).length
  const progressPercent =
    milestones.length > 0
      ? Math.round((completedMilestones / milestones.length) * 100)
      : 0

  // Parse target date if it exists in the description or as a separate field
  const extendedPlan = plan as Plan & { target_date?: string }
  const targetDate = extendedPlan.target_date

  const handleCardClick = (e: React.MouseEvent) => {
    // Don't trigger select when clicking dropdown
    if ((e.target as HTMLElement).closest('[data-dropdown-trigger]')) {
      return
    }
    onSelect()
  }

  return (
    <Card
      className={cn(
        'cursor-pointer transition-all hover:border-primary/50',
        isSelected && 'border-primary ring-1 ring-primary'
      )}
      onClick={handleCardClick}
    >
      <CardHeader className="p-4 pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-start gap-2 min-w-0">
            <span className="text-lg flex-shrink-0" role="img" aria-label={goalType}>
              {emoji}
            </span>
            <div className="min-w-0">
              <h3 className="font-medium text-sm leading-tight truncate">
                {plan.title}
              </h3>
              {plan.description && (
                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                  {plan.description}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Badge variant={STATUS_VARIANT[plan.status]} className="text-xs">
              {plan.status}
            </Badge>
            {(onPause || onCancel) && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    data-dropdown-trigger
                    onClick={(e) => e.stopPropagation()}
                  >
                    <MoreVertical className="h-4 w-4" />
                    <span className="sr-only">Plan actions</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {onPause && plan.status === 'active' && (
                    <DropdownMenuItem onClick={onPause}>
                      <Pause className="mr-2 h-4 w-4" />
                      Pause
                    </DropdownMenuItem>
                  )}
                  {onCancel && plan.status !== 'cancelled' && plan.status !== 'completed' && (
                    <DropdownMenuItem
                      onClick={onCancel}
                      className="text-destructive focus:text-destructive"
                    >
                      <X className="mr-2 h-4 w-4" />
                      Cancel
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-4 pt-2 space-y-3">
        {/* Progress bar */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Progress</span>
            <span>{progressPercent}%</span>
          </div>
          <Progress value={progressPercent} className="h-1.5" />
        </div>

        {/* Target date */}
        {targetDate && (
          <p className="text-xs text-muted-foreground">
            Target:{' '}
            {new Date(targetDate).toLocaleDateString(undefined, {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            })}
          </p>
        )}

        {/* Milestones */}
        {milestones.length > 0 && (
          <MilestoneList milestones={milestones} />
        )}
      </CardContent>
    </Card>
  )
}
