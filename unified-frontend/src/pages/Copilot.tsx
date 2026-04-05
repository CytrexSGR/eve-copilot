import { Activity, Power } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PlanPanel } from '@/components/copilot/PlanPanel'
import { ChatInterface } from '@/components/copilot/ChatInterface'
import { EventPanel } from '@/components/copilot/EventPanel'
import { useCopilot } from '@/contexts/CopilotContext'
import { useAgentWebSocket } from '@/hooks/useAgentWebSocket'

export default function Copilot() {
  const {
    session,
    isConnected,
    endSession,
    addEvent,
    events,
  } = useCopilot()

  // WebSocket connection for real-time events
  useAgentWebSocket({
    sessionId: session?.session_id ?? null,
    onEvent: addEvent,
  })

  return (
    <div className="flex h-[calc(100vh-64px)] flex-col overflow-hidden">
      {/* Header */}
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-border bg-background/95 backdrop-blur px-6">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">AI Copilot</h1>
          {session && (
            <div className="flex items-center gap-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  isConnected ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              <span className="text-sm text-muted-foreground">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          )}
        </div>

        {session && (
          <div className="flex items-center gap-2">
            <EventPanel>
              <Button variant="outline" size="sm" className="gap-2">
                <Activity className="h-4 w-4" />
                <span>Events</span>
                {events.length > 0 && (
                  <span className="ml-1 rounded-full bg-secondary px-1.5 py-0 text-xs">
                    {events.length > 99 ? '99+' : events.length}
                  </span>
                )}
              </Button>
            </EventPanel>
            <Button
              variant="outline"
              size="icon"
              onClick={endSession}
              title="End session"
            >
              <Power className="h-4 w-4" />
            </Button>
          </div>
        )}
      </header>

      {/* Main content - 2 column layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left panel - Plans */}
        <div className="w-[250px] shrink-0 border-r border-border bg-card">
          <PlanPanel />
        </div>

        {/* Center - Chat */}
        <div className="flex-1 overflow-hidden">
          <ChatInterface />
        </div>
      </div>
    </div>
  )
}
