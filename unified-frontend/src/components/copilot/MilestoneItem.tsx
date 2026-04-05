import { Circle, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'
import { cn } from '../../lib/utils'
import type { Milestone } from '../../api/agent'

interface MilestoneItemProps {
  milestone: Milestone
  isLast: boolean
}

export function MilestoneItem({ milestone, isLast }: MilestoneItemProps) {
  const StatusIcon = () => {
    switch (milestone.status) {
      case 'pending':
        return <Circle className="h-4 w-4 text-muted-foreground" />
      case 'in_progress':
        return <Loader2 className="h-4 w-4 text-primary animate-spin" />
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-destructive" />
      default:
        return <Circle className="h-4 w-4 text-muted-foreground" />
    }
  }

  // Extended milestone type to support progress tracking
  const extendedMilestone = milestone as Milestone & {
    target_value?: number
    current_value?: number
  }

  const hasProgress =
    extendedMilestone.target_value !== undefined &&
    extendedMilestone.target_value > 0

  const progressPercent = hasProgress
    ? Math.min(
        100,
        Math.round(
          ((extendedMilestone.current_value || 0) /
            extendedMilestone.target_value!) *
            100
        )
      )
    : 0

  return (
    <div className="relative flex gap-3">
      {/* Vertical connector line */}
      {!isLast && (
        <div className="absolute left-[7px] top-6 h-[calc(100%-8px)] w-[2px] bg-border" />
      )}

      {/* Status icon */}
      <div className="relative z-10 flex-shrink-0 mt-0.5">
        <StatusIcon />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pb-4">
        <p
          className={cn(
            'text-sm font-medium leading-tight',
            milestone.status === 'completed' && 'line-through text-muted-foreground'
          )}
        >
          {milestone.title}
        </p>

        {milestone.description && (
          <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
            {milestone.description}
          </p>
        )}

        {/* Progress bar */}
        {hasProgress && (
          <div className="mt-2 space-y-1">
            <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              {extendedMilestone.current_value || 0} /{' '}
              {extendedMilestone.target_value}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
