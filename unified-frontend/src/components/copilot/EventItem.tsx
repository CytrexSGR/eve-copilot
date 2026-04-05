import {
  Play,
  CheckCircle,
  FileText,
  XCircle,
  Zap,
  Cog,
  Loader2,
  AlertCircle,
  Clock,
} from 'lucide-react'
import { cn } from '../../lib/utils'
import type { AgentEvent, AgentEventType } from '../../types/agent-events'

interface EventItemProps {
  event: AgentEvent
}

interface EventConfig {
  icon: React.ElementType
  colorClass: string
  label: string
}

const EVENT_CONFIG: Record<AgentEventType, EventConfig> = {
  session_started: {
    icon: Play,
    colorClass: 'text-success',
    label: 'Session Started',
  },
  session_ended: {
    icon: CheckCircle,
    colorClass: 'text-muted-foreground',
    label: 'Session Ended',
  },
  session_error: {
    icon: XCircle,
    colorClass: 'text-destructive',
    label: 'Session Error',
  },
  planning_started: {
    icon: FileText,
    colorClass: 'text-primary',
    label: 'Planning Started',
  },
  plan_proposed: {
    icon: FileText,
    colorClass: 'text-warning',
    label: 'Plan Proposed',
  },
  plan_approved: {
    icon: CheckCircle,
    colorClass: 'text-success',
    label: 'Plan Approved',
  },
  plan_rejected: {
    icon: XCircle,
    colorClass: 'text-destructive',
    label: 'Plan Rejected',
  },
  plan_modified: {
    icon: FileText,
    colorClass: 'text-primary',
    label: 'Plan Modified',
  },
  execution_started: {
    icon: Zap,
    colorClass: 'text-primary',
    label: 'Execution Started',
  },
  execution_paused: {
    icon: Clock,
    colorClass: 'text-warning',
    label: 'Execution Paused',
  },
  execution_resumed: {
    icon: Zap,
    colorClass: 'text-primary',
    label: 'Execution Resumed',
  },
  execution_cancelled: {
    icon: XCircle,
    colorClass: 'text-destructive',
    label: 'Execution Cancelled',
  },
  tool_call_started: {
    icon: Cog,
    colorClass: 'text-primary',
    label: 'Tool Call Started',
  },
  tool_call_completed: {
    icon: CheckCircle,
    colorClass: 'text-success',
    label: 'Tool Call Completed',
  },
  tool_call_failed: {
    icon: XCircle,
    colorClass: 'text-destructive',
    label: 'Tool Call Failed',
  },
  step_started: {
    icon: Loader2,
    colorClass: 'text-primary',
    label: 'Step Started',
  },
  step_completed: {
    icon: CheckCircle,
    colorClass: 'text-success',
    label: 'Step Completed',
  },
  step_failed: {
    icon: XCircle,
    colorClass: 'text-destructive',
    label: 'Step Failed',
  },
  task_completed: {
    icon: CheckCircle,
    colorClass: 'text-success',
    label: 'Task Completed',
  },
  task_failed: {
    icon: XCircle,
    colorClass: 'text-destructive',
    label: 'Task Failed',
  },
  approval_required: {
    icon: AlertCircle,
    colorClass: 'text-warning',
    label: 'Approval Required',
  },
  clarification_needed: {
    icon: AlertCircle,
    colorClass: 'text-warning',
    label: 'Clarification Needed',
  },
  token: {
    icon: Clock,
    colorClass: 'text-muted-foreground',
    label: 'Token',
  },
}

const DEFAULT_CONFIG: EventConfig = {
  icon: Clock,
  colorClass: 'text-muted-foreground',
  label: 'Event',
}

function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return timestamp
  }
}

function getPayloadInfo(event: AgentEvent): string | null {
  const payload = event.payload as Record<string, unknown> | null
  if (!payload) return null

  // Tool name for tool events
  if ('tool_name' in payload && payload.tool_name) {
    return String(payload.tool_name)
  }

  // Title for plan events
  if ('title' in payload && payload.title) {
    return String(payload.title)
  }

  // Error message
  if ('error' in payload && payload.error) {
    return String(payload.error)
  }

  return null
}

export function EventItem({ event }: EventItemProps) {
  const config = EVENT_CONFIG[event.type as AgentEventType] || DEFAULT_CONFIG
  const Icon = config.icon
  const isSpinning = event.type === 'step_started'
  const payloadInfo = getPayloadInfo(event)

  return (
    <div className="flex items-start gap-3 py-2 px-1">
      <div className={cn('mt-0.5 flex-shrink-0', config.colorClass)}>
        <Icon
          className={cn('h-4 w-4', isSpinning && 'animate-spin')}
          aria-hidden="true"
        />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-sm font-medium truncate">{config.label}</span>
          <span className="text-xs text-muted-foreground flex-shrink-0">
            {formatTimestamp(event.timestamp)}
          </span>
        </div>
        {payloadInfo && (
          <p className="text-xs text-muted-foreground truncate mt-0.5">
            {payloadInfo}
          </p>
        )}
      </div>
    </div>
  )
}
