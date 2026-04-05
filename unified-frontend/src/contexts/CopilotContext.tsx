import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
  useRef,
} from 'react'

// UUID generator that works in non-HTTPS contexts
function generateUUID(): string {
  // Use crypto.randomUUID if available (HTTPS only)
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  // Fallback for HTTP contexts
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}
import {
  agentApi,
  AgentSession,
  AutonomyLevel,
  Plan,
} from '../api/agent'
import type { ChatMessage } from '../types/chat-messages'
import type { AgentEvent } from '../types/agent-events'
import { useCharacterContext } from './CharacterContext'

// ============================================================================
// Types
// ============================================================================

const STORAGE_KEY = 'copilot_session'

interface StoredSession {
  session_id: string
  character_id: number
}

interface CopilotState {
  // Session
  session: AgentSession | null
  isConnected: boolean
  isLoading: boolean
  error: string | null

  // Chat
  messages: ChatMessage[]
  isStreaming: boolean

  // Plans
  plans: Plan[]
  selectedPlanId: number | null

  // Events
  events: AgentEvent[]

  // UI
  isEventPanelOpen: boolean
  isWidgetOpen: boolean
  isCommandPaletteOpen: boolean
}

interface CopilotContextValue extends CopilotState {
  // Session actions
  startSession: (autonomyLevel?: AutonomyLevel) => Promise<void>
  endSession: () => Promise<void>

  // Chat actions
  sendMessage: (message: string) => Promise<void>
  clearMessages: () => void

  // Plan actions
  selectPlan: (planId: number | null) => void
  refreshPlans: () => Promise<void>
  approvePlan: (planId: string) => Promise<void>
  rejectPlan: (planId: string, reason?: string) => Promise<void>

  // Event actions
  addEvent: (event: AgentEvent) => void
  clearEvents: () => void

  // UI actions
  toggleEventPanel: () => void
  toggleWidget: () => void
  toggleCommandPalette: () => void
  setCommandPaletteOpen: (open: boolean) => void
}

// ============================================================================
// Context
// ============================================================================

const CopilotContext = createContext<CopilotContextValue | undefined>(undefined)

// ============================================================================
// Provider
// ============================================================================

export function CopilotProvider({ children }: { children: ReactNode }) {
  const { selectedCharacter } = useCharacterContext()

  // Session state
  const [session, setSession] = useState<AgentSession | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)

  // Plans state
  const [plans, setPlans] = useState<Plan[]>([])
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null)

  // Events state
  const [events, setEvents] = useState<AgentEvent[]>([])

  // UI state
  const [isEventPanelOpen, setIsEventPanelOpen] = useState(false)
  const [isWidgetOpen, setIsWidgetOpen] = useState(false)
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)

  // Ref for cleanup function from streaming
  const streamCleanupRef = useRef<(() => void) | null>(null)

  // ============================================================================
  // Session Persistence
  // ============================================================================

  // Restore session on mount - or create new one if invalid
  useEffect(() => {
    const initSession = async () => {
      // TEMP: Copilot server disabled - skip all API calls
      return

      if (!selectedCharacter) return

      const stored = localStorage.getItem(STORAGE_KEY)

      // Try to restore existing session
      if (stored) {
        try {
          const { session_id, character_id }: StoredSession = JSON.parse(stored)

          // Validate stored data
          if (!session_id || session_id === 'undefined' || !character_id) {
            localStorage.removeItem(STORAGE_KEY)
          } else if (selectedCharacter.character_id !== character_id) {
            // Different character - clear old session
            localStorage.removeItem(STORAGE_KEY)
          } else {
            // Try to restore session from server
            setIsLoading(true)
            try {
              const restoredSession = await agentApi.getSession(session_id)
              setSession(restoredSession)
              setIsConnected(true)

              // Load chat history
              const history = await agentApi.getChatHistory(session_id)
              setMessages(history.messages)
              setIsLoading(false)
              return // Successfully restored
            } catch {
              // Session not found on server - will create new one below
              localStorage.removeItem(STORAGE_KEY)
            }
          }
        } catch {
          localStorage.removeItem(STORAGE_KEY)
        }
      }

      // No valid session - automatically create a new one
      setIsLoading(true)
      try {
        const newSession = await agentApi.createSession({
          character_id: selectedCharacter.character_id,
          autonomy_level: 'RECOMMENDATIONS',
        })

        if (newSession.session_id && newSession.session_id !== 'undefined') {
          setSession(newSession)
          setIsConnected(true)
          setMessages([])

          localStorage.setItem(STORAGE_KEY, JSON.stringify({
            session_id: newSession.session_id,
            character_id: selectedCharacter.character_id,
          }))
        }
      } catch (err) {
        console.error('Failed to create session:', err)
        setError('Failed to initialize copilot session')
      } finally {
        setIsLoading(false)
      }
    }

    initSession()
  }, [selectedCharacter])

  // Load plans when character changes
  useEffect(() => {
    // TEMP: Copilot server disabled - skip all API calls
    return

    if (selectedCharacter) {
      loadPlans(selectedCharacter.character_id)
    } else {
      setPlans([])
      setSelectedPlanId(null)
    }
  }, [selectedCharacter])

  // ============================================================================
  // Plans Loading
  // ============================================================================

  const loadPlans = async (characterId: number) => {
    try {
      const activePlans = await agentApi.getPlans(characterId, 'active')
      setPlans(activePlans)
    } catch (err) {
      console.error('Failed to load plans:', err)
    }
  }

  // ============================================================================
  // Session Actions
  // ============================================================================

  const startSession = useCallback(
    async (autonomyLevel: AutonomyLevel = 'RECOMMENDATIONS') => {
      // Always clear old session data first
      localStorage.removeItem(STORAGE_KEY)
      setSession(null)
      setMessages([])
      setIsConnected(false)

      if (!selectedCharacter) {
        setError('No character selected')
        return
      }

      setIsLoading(true)
      setError(null)

      try {
        const newSession = await agentApi.createSession({
          character_id: selectedCharacter.character_id,
          autonomy_level: autonomyLevel,
        })

        // Validate session has a valid ID before storing
        if (!newSession.session_id || newSession.session_id === 'undefined') {
          throw new Error('Server returned invalid session ID')
        }

        setSession(newSession)
        setIsConnected(true)
        setMessages([])

        // Persist session info
        const storedData: StoredSession = {
          session_id: newSession.session_id,
          character_id: selectedCharacter.character_id,
        }
        localStorage.setItem(STORAGE_KEY, JSON.stringify(storedData))
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to start session'
        setError(message)
        console.error('Failed to start copilot session:', err)
      } finally {
        setIsLoading(false)
      }
    },
    [selectedCharacter]
  )

  const endSession = useCallback(async () => {
    if (!session) return

    // Cancel any ongoing stream
    if (streamCleanupRef.current) {
      streamCleanupRef.current()
      streamCleanupRef.current = null
    }

    setIsLoading(true)

    try {
      await agentApi.deleteSession(session.session_id)
    } catch (err) {
      console.warn('Failed to delete session on server:', err)
    } finally {
      setSession(null)
      setIsConnected(false)
      setMessages([])
      setIsStreaming(false)
      setError(null)
      localStorage.removeItem(STORAGE_KEY)
      setIsLoading(false)
    }
  }, [session])

  // ============================================================================
  // Chat Actions
  // ============================================================================

  const sendMessage = useCallback(
    async (message: string) => {
      console.log('[sendMessage] session_id:', session?.session_id, 'character:', selectedCharacter?.character_id)

      if (!session) {
        setError('No active session')
        return
      }

      if (!selectedCharacter) {
        setError('No character selected')
        return
      }

      if (isStreaming) {
        return // Prevent sending while streaming
      }

      setError(null)

      // Add user message
      const userMessage: ChatMessage = {
        id: generateUUID(),
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMessage])

      // Create placeholder assistant message
      const assistantMessageId = generateUUID()
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        isStreaming: true,
      }
      setMessages((prev) => [...prev, assistantMessage])
      setIsStreaming(true)

      // Stream the response
      const cleanup = agentApi.streamChat(
        session.session_id,
        selectedCharacter.character_id,
        message,
        // onChunk
        (chunk: string) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: msg.content + chunk }
                : msg
            )
          )
        },
        // onError
        (err: Error) => {
          setError(err.message)
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId ? { ...msg, isStreaming: false } : msg
            )
          )
          setIsStreaming(false)
          streamCleanupRef.current = null
        },
        // onComplete
        () => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId ? { ...msg, isStreaming: false } : msg
            )
          )
          setIsStreaming(false)
          streamCleanupRef.current = null
        }
      )

      streamCleanupRef.current = cleanup
    },
    [session, selectedCharacter, isStreaming]
  )

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  // ============================================================================
  // Plan Actions
  // ============================================================================

  const selectPlan = useCallback((planId: number | null) => {
    setSelectedPlanId(planId)
  }, [])

  const refreshPlans = useCallback(async () => {
    if (selectedCharacter) {
      await loadPlans(selectedCharacter.character_id)
    }
  }, [selectedCharacter])

  const approvePlan = useCallback(
    async (planId: string) => {
      if (!session) {
        setError('No active session')
        return
      }

      try {
        await agentApi.executePlan(session.session_id, planId)
        await refreshPlans()
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to approve plan'
        setError(message)
        throw err
      }
    },
    [session, refreshPlans]
  )

  const rejectPlan = useCallback(
    async (planId: string, reason?: string) => {
      if (!session) {
        setError('No active session')
        return
      }

      try {
        await agentApi.rejectPlan(session.session_id, planId, reason)
        await refreshPlans()
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to reject plan'
        setError(message)
        throw err
      }
    },
    [session, refreshPlans]
  )

  // ============================================================================
  // Event Actions
  // ============================================================================

  const addEvent = useCallback((event: AgentEvent) => {
    setEvents((prev) => [...prev, event])
  }, [])

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  // ============================================================================
  // UI Actions
  // ============================================================================

  const toggleEventPanel = useCallback(() => {
    setIsEventPanelOpen((prev) => !prev)
  }, [])

  const toggleWidget = useCallback(() => {
    setIsWidgetOpen((prev) => !prev)
  }, [])

  const toggleCommandPalette = useCallback(() => {
    setIsCommandPaletteOpen((prev) => !prev)
  }, [])

  const setCommandPaletteOpen = useCallback((open: boolean) => {
    setIsCommandPaletteOpen(open)
  }, [])

  // ============================================================================
  // Context Value
  // ============================================================================

  const value: CopilotContextValue = {
    // State
    session,
    isConnected,
    isLoading,
    error,
    messages,
    isStreaming,
    plans,
    selectedPlanId,
    events,
    isEventPanelOpen,
    isWidgetOpen,
    isCommandPaletteOpen,

    // Actions
    startSession,
    endSession,
    sendMessage,
    clearMessages,
    selectPlan,
    refreshPlans,
    approvePlan,
    rejectPlan,
    addEvent,
    clearEvents,
    toggleEventPanel,
    toggleWidget,
    toggleCommandPalette,
    setCommandPaletteOpen,
  }

  return (
    <CopilotContext.Provider value={value}>{children}</CopilotContext.Provider>
  )
}

// ============================================================================
// Hook
// ============================================================================

export function useCopilot() {
  const context = useContext(CopilotContext)
  if (context === undefined) {
    throw new Error('useCopilot must be used within a CopilotProvider')
  }
  return context
}
