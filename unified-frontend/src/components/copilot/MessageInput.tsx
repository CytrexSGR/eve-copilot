import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { Send, Loader2 } from 'lucide-react'
import { Input } from '../ui/input'
import { Button } from '../ui/button'

interface MessageInputProps {
  onSend: (message: string) => void
  isLoading?: boolean
  disabled?: boolean
  placeholder?: string
}

export function MessageInput({
  onSend,
  isLoading = false,
  disabled = false,
  placeholder = 'Type a message...',
}: MessageInputProps) {
  const [message, setMessage] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSend = () => {
    const trimmedMessage = message.trim()
    if (trimmedMessage && !isLoading && !disabled) {
      onSend(trimmedMessage)
      setMessage('')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    // Send on Enter, but not on Shift+Enter (allow multiline in future textarea version)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const canSend = message.trim().length > 0 && !isLoading && !disabled

  return (
    <div className="flex gap-2 p-4 border-t border-border bg-background">
      <Input
        ref={inputRef}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled || isLoading}
        className="flex-1"
      />
      <Button
        onClick={handleSend}
        disabled={!canSend}
        size="icon"
        className="flex-shrink-0"
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Send className="h-4 w-4" />
        )}
        <span className="sr-only">Send message</span>
      </Button>
    </div>
  )
}
