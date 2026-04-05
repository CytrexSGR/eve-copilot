import { formatDuration } from '@/lib/utils'
import type { SkillQueueItem } from '@/types/character'
import { Badge } from '@/components/ui/badge'
import { Clock, AlertTriangle } from 'lucide-react'

interface SkillQueueProgressProps {
  currentSkill?: SkillQueueItem
  skillsInQueue: number
}

export function SkillQueueProgress({ currentSkill, skillsInQueue }: SkillQueueProgressProps) {
  if (!currentSkill) {
    return (
      <div className="flex items-center gap-2 text-warning">
        <AlertTriangle className="h-4 w-4" />
        <span className="text-sm font-medium">Queue Empty!</span>
      </div>
    )
  }

  const now = new Date()
  const finishDate = new Date(currentSkill.finish_date)
  const startDate = new Date(currentSkill.start_date)

  const totalDuration = finishDate.getTime() - startDate.getTime()
  const elapsed = now.getTime() - startDate.getTime()
  const progress = Math.min(100, Math.max(0, (elapsed / totalDuration) * 100))

  const remainingSeconds = Math.max(0, Math.floor((finishDate.getTime() - now.getTime()) / 1000))

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium truncate flex-1">
          {currentSkill.skill_name} {currentSkill.finished_level}
        </span>
        <Badge variant="secondary" className="ml-2">
          {skillsInQueue} in queue
        </Badge>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-secondary rounded-full overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        <Clock className="h-3 w-3" />
        <span>{formatDuration(remainingSeconds)} remaining</span>
      </div>
    </div>
  )
}
