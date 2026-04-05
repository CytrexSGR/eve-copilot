import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  TrendingUp,
  Factory,
  Globe,
  Wallet,
  Rocket,
  MessageSquare,
  ArrowRight,
} from 'lucide-react'
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
} from '../ui/command'
import { useCopilot } from '../../contexts/CopilotContext'

interface QuickCommand {
  icon: React.ReactNode
  label: string
  question: string
}

const quickCommands: QuickCommand[] = [
  {
    icon: <TrendingUp className="h-4 w-4" />,
    label: 'Market Analysis',
    question: 'What are the best market opportunities right now?',
  },
  {
    icon: <Factory className="h-4 w-4" />,
    label: 'Production Status',
    question: 'What is my current production status?',
  },
  {
    icon: <Globe className="h-4 w-4" />,
    label: 'PI Overview',
    question: 'Give me an overview of my PI colonies',
  },
  {
    icon: <Wallet className="h-4 w-4" />,
    label: 'Wallet Summary',
    question: 'What is my wallet balance?',
  },
  {
    icon: <Rocket className="h-4 w-4" />,
    label: 'Ship Mastery',
    question: 'What ships can I fly?',
  },
]

export function CommandPalette() {
  const navigate = useNavigate()
  const {
    session,
    isCommandPaletteOpen,
    setCommandPaletteOpen,
    sendMessage,
    startSession,
  } = useCopilot()

  const [inputValue, setInputValue] = useState('')

  // Register global Ctrl+K / Cmd+K listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setCommandPaletteOpen(!isCommandPaletteOpen)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isCommandPaletteOpen, setCommandPaletteOpen])

  // Clear input when dialog closes
  useEffect(() => {
    if (!isCommandPaletteOpen) {
      setInputValue('')
    }
  }, [isCommandPaletteOpen])

  // Execute a question by navigating to copilot and sending message
  const executeQuestion = async (question: string) => {
    setCommandPaletteOpen(false)
    navigate('/copilot')

    // If no session, start one first
    if (!session) {
      await startSession()
    }

    // Wait a bit for navigation and session to settle, then send message
    setTimeout(() => {
      sendMessage(question)
    }, 500)
  }

  // Handle navigation to copilot page
  const handleGoToCopilot = () => {
    setCommandPaletteOpen(false)
    navigate('/copilot')
  }

  // Handle custom question from input
  const handleCustomQuestion = () => {
    if (inputValue.trim()) {
      executeQuestion(inputValue.trim())
    }
  }

  return (
    <CommandDialog
      open={isCommandPaletteOpen}
      onOpenChange={setCommandPaletteOpen}
    >
      <CommandInput
        placeholder="Ask AI or search..."
        value={inputValue}
        onValueChange={setInputValue}
      />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        {/* Custom question from input */}
        {inputValue.trim() && (
          <CommandGroup heading="Ask AI">
            <CommandItem onSelect={handleCustomQuestion} className="gap-2">
              <MessageSquare className="h-4 w-4" />
              <span>Ask AI: {inputValue}</span>
            </CommandItem>
          </CommandGroup>
        )}

        {/* Quick Commands */}
        <CommandGroup heading="Quick Commands">
          {quickCommands.map((cmd) => (
            <CommandItem
              key={cmd.label}
              onSelect={() => executeQuestion(cmd.question)}
              className="gap-2"
            >
              {cmd.icon}
              <span>{cmd.label}</span>
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator />

        {/* Navigation */}
        <CommandGroup heading="Navigation">
          <CommandItem onSelect={handleGoToCopilot} className="gap-2">
            <ArrowRight className="h-4 w-4" />
            <span>Go to Copilot</span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
