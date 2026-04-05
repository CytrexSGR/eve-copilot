import { Bot, User, Loader2 } from 'lucide-react'
import { Avatar, AvatarImage, AvatarFallback } from '../ui/avatar'
import { cn } from '../../lib/utils'
import type { ChatMessage } from '../../types/chat-messages'

interface MessageBubbleProps {
  message: ChatMessage
  characterPortrait?: string
}

export function MessageBubble({ message, characterPortrait }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const isStreaming = message.isStreaming
  const hasContent = message.content.length > 0

  // Format timestamp
  const timestamp = new Date(message.timestamp).toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div
      className={cn(
        'flex gap-3 max-w-[85%]',
        isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'
      )}
    >
      {/* Avatar */}
      <Avatar className="h-8 w-8 flex-shrink-0">
        {isUser ? (
          <>
            {characterPortrait ? (
              <AvatarImage src={characterPortrait} alt="Character" />
            ) : null}
            <AvatarFallback>
              <User className="h-4 w-4" />
            </AvatarFallback>
          </>
        ) : (
          <AvatarFallback className="bg-primary/10">
            <Bot className="h-4 w-4 text-primary" />
          </AvatarFallback>
        )}
      </Avatar>

      {/* Message content */}
      <div className={cn('flex flex-col gap-1', isUser ? 'items-end' : 'items-start')}>
        <div
          className={cn(
            'rounded-2xl px-4 py-2 text-sm',
            isUser
              ? 'bg-primary text-primary-foreground rounded-tr-sm'
              : 'bg-secondary text-secondary-foreground rounded-tl-sm'
          )}
        >
          {/* Loading state: show spinner when streaming with no content */}
          {isStreaming && !hasContent ? (
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-muted-foreground">Thinking...</span>
            </div>
          ) : (
            <div className="whitespace-pre-wrap break-words">
              {message.content}
              {/* Streaming indicator: blinking cursor when streaming with content */}
              {isStreaming && hasContent && (
                <span className="inline-block w-2 h-4 ml-0.5 bg-current animate-pulse" />
              )}
            </div>
          )}
        </div>

        {/* Timestamp */}
        <span className="text-xs text-muted-foreground px-1">{timestamp}</span>
      </div>
    </div>
  )
}
