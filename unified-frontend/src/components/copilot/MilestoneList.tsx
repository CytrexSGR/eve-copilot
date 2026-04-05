import { useState } from 'react'
import { ChevronRight } from 'lucide-react'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '../ui/collapsible'
import { cn } from '../../lib/utils'
import { MilestoneItem } from './MilestoneItem'
import type { Milestone } from '../../api/agent'

interface MilestoneListProps {
  milestones: Milestone[]
  defaultOpen?: boolean
}

export function MilestoneList({
  milestones,
  defaultOpen = false,
}: MilestoneListProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  // Sort milestones by order_index
  const sortedMilestones = [...milestones].sort(
    (a, b) => a.order_index - b.order_index
  )

  const completedCount = milestones.filter(
    (m) => m.status === 'completed'
  ).length
  const totalCount = milestones.length

  if (totalCount === 0) {
    return null
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger className="flex w-full items-center gap-2 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ChevronRight
          className={cn(
            'h-4 w-4 transition-transform duration-200',
            isOpen && 'rotate-90'
          )}
        />
        <span>
          {completedCount}/{totalCount} milestones
        </span>
      </CollapsibleTrigger>
      <CollapsibleContent className="pl-6 pt-2">
        <div className="space-y-0">
          {sortedMilestones.map((milestone, index) => (
            <MilestoneItem
              key={milestone.id}
              milestone={milestone}
              isLast={index === sortedMilestones.length - 1}
            />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
