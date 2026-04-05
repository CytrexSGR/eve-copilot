import { useEffect, useRef } from 'react'
import { ScrollArea } from '../ui/scroll-area'
import { EventItem } from './EventItem'
import type { AgentEvent } from '../../types/agent-events'

interface EventListProps {
  events: AgentEvent[]
}

export function EventList({ events }: EventListProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [events.length])

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        No events yet
      </div>
    )
  }

  return (
    <ScrollArea className="h-full" ref={scrollRef}>
      <div className="space-y-1 pr-4">
        {events.map((event) => (
          <EventItem key={event.id} event={event} />
        ))}
      </div>
    </ScrollArea>
  )
}
