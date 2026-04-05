import { useRef, useEffect } from 'react'
import { MessageSquare } from 'lucide-react'
import { ScrollArea } from '../ui/scroll-area'
import { MessageBubble } from './MessageBubble'
import type { ChatMessage } from '../../types/chat-messages'

interface MessageListProps {
  messages: ChatMessage[]
  characterPortrait?: string
}

export function MessageList({ messages, characterPortrait }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Empty state
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center space-y-3">
          <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
            <MessageSquare className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h3 className="font-medium text-foreground">Welcome to AI Copilot</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Start a conversation to get help with your EVE Online activities.
              Ask about market analysis, production planning, or anything else.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <ScrollArea className="flex-1 p-4">
      <div className="space-y-4">
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            characterPortrait={characterPortrait}
          />
        ))}
        {/* Scroll anchor */}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  )
}
