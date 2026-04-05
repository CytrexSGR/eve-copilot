import { Activity, Trash2 } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '../ui/sheet'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { EventList } from './EventList'
import { useCopilot } from '../../contexts/CopilotContext'

interface EventPanelProps {
  children?: React.ReactNode
}

export function EventPanel({ children }: EventPanelProps) {
  const { events, isEventPanelOpen, toggleEventPanel, clearEvents } = useCopilot()

  const eventCount = events.length

  const defaultTrigger = (
    <Button variant="outline" size="sm" className="gap-2">
      <Activity className="h-4 w-4" />
      <span>Events</span>
      {eventCount > 0 && (
        <Badge variant="secondary" className="ml-1 px-1.5 py-0 text-xs">
          {eventCount > 99 ? '99+' : eventCount}
        </Badge>
      )}
    </Button>
  )

  return (
    <Sheet open={isEventPanelOpen} onOpenChange={toggleEventPanel}>
      <SheetTrigger asChild>{children || defaultTrigger}</SheetTrigger>
      <SheetContent side="right" className="flex flex-col w-[400px] sm:max-w-[400px]">
        <SheetHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <SheetTitle>Agent Events</SheetTitle>
            {eventCount > 0 && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={clearEvents}
                title="Clear events"
              >
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">Clear events</span>
              </Button>
            )}
          </div>
        </SheetHeader>
        <div className="flex-1 overflow-hidden mt-4">
          <EventList events={events} />
        </div>
      </SheetContent>
    </Sheet>
  )
}
