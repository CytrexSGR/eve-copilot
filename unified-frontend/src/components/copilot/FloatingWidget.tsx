import { useState, useRef, useEffect } from 'react'
import {
  MessageCircle,
  X,
  Minimize2,
  Maximize2,
  Bot,
  Play,
} from 'lucide-react'
import { Button } from '../ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/card'
import { ScrollArea } from '../ui/scroll-area'
import { MessageBubble } from './MessageBubble'
import { MessageInput } from './MessageInput'
import { useCopilot } from '../../contexts/CopilotContext'
import { useCharacterContext } from '../../contexts/CharacterContext'
import { cn } from '../../lib/utils'

export function FloatingWidget() {
  const {
    session,
    messages,
    isStreaming,
    isLoading,
    isWidgetOpen,
    toggleWidget,
    sendMessage,
    startSession,
  } = useCopilot()

  const { selectedCharacter } = useCharacterContext()
  const [isMinimized, setIsMinimized] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Get character portrait URL
  const characterPortrait = selectedCharacter
    ? `https://images.evetech.net/characters/${selectedCharacter.character_id}/portrait?size=64`
    : undefined

  // Get last 10 messages for widget display
  const displayMessages = messages.slice(-10)

  // Closed state - just the floating button
  if (!isWidgetOpen) {
    return (
      <Button
        onClick={toggleWidget}
        className={cn(
          'fixed bottom-6 right-6 z-50',
          'h-14 w-14 rounded-full shadow-lg',
          'hover:scale-105 transition-transform'
        )}
        size="icon"
      >
        <MessageCircle className="h-6 w-6" />
        <span className="sr-only">Open AI Copilot</span>
      </Button>
    )
  }

  // Open state - chat card
  return (
    <Card
      className={cn(
        'fixed bottom-6 right-6 z-50',
        'w-[400px] shadow-xl border-border',
        'flex flex-col',
        isMinimized ? 'h-auto' : 'h-[500px]'
      )}
    >
      {/* Header */}
      <CardHeader className="flex flex-row items-center justify-between p-4 border-b border-border space-y-0">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          AI Copilot
        </CardTitle>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setIsMinimized((prev) => !prev)}
          >
            {isMinimized ? (
              <Maximize2 className="h-4 w-4" />
            ) : (
              <Minimize2 className="h-4 w-4" />
            )}
            <span className="sr-only">
              {isMinimized ? 'Maximize' : 'Minimize'}
            </span>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={toggleWidget}
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </Button>
        </div>
      </CardHeader>

      {/* Content - hidden when minimized */}
      {!isMinimized && (
        <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
          {!session ? (
            // No session - show start session prompt
            <div className="flex-1 flex flex-col items-center justify-center gap-4 p-6 text-center">
              <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="h-8 w-8 text-primary" />
              </div>
              <div className="space-y-2">
                <h3 className="font-semibold">Start a Session</h3>
                <p className="text-sm text-muted-foreground">
                  Start a conversation with your AI Copilot to get help with EVE
                  Online tasks.
                </p>
              </div>
              <Button
                onClick={() => startSession()}
                disabled={isLoading || !selectedCharacter}
                className="gap-2"
              >
                <Play className="h-4 w-4" />
                Start Session
              </Button>
              {!selectedCharacter && (
                <p className="text-xs text-muted-foreground">
                  Select a character first
                </p>
              )}
            </div>
          ) : (
            // Active session - show messages and input
            <>
              {/* Messages area */}
              <ScrollArea className="flex-1" ref={scrollRef}>
                <div className="p-4 space-y-4">
                  {displayMessages.length === 0 ? (
                    <div className="text-center text-muted-foreground text-sm py-8">
                      Ask me anything about EVE Online!
                    </div>
                  ) : (
                    displayMessages.map((message) => (
                      <MessageBubble
                        key={message.id}
                        message={message}
                        characterPortrait={characterPortrait}
                      />
                    ))
                  )}
                </div>
              </ScrollArea>

              {/* Input area */}
              <MessageInput
                onSend={sendMessage}
                isLoading={isStreaming}
                disabled={!session}
                placeholder="Ask AI..."
              />
            </>
          )}
        </CardContent>
      )}
    </Card>
  )
}
