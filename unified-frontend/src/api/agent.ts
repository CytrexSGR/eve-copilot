import axios from 'axios'
import type { ChatMessage, MessageRole } from '../types/chat-messages'

// Agent API uses a separate server (copilot server on port 8009)
// Direct connection to copilot server using same hostname as current page
const getAgentBaseURL = () => {
  if (import.meta.env.DEV) {
    // Development: use same hostname as current page but different port
    const hostname = typeof window !== 'undefined' ? window.location.hostname : 'localhost'
    return `http://${hostname}:8009/api/agent`
  }
  return '/api/agent'  // Production: proxied through nginx
}

const agentClient = axios.create({
  baseURL: getAgentBaseURL(),
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor for error handling
agentClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('Agent API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// ============================================================================
// Types
// ============================================================================

/**
 * Autonomy level for agent sessions
 * - READ_ONLY (0): Agent can only read data, no actions
 * - RECOMMENDATIONS (1): Agent provides recommendations, user executes
 * - ASSISTED (2): Agent executes low-risk actions, asks for approval on others
 * - SUPERVISED (3): Agent executes most actions, only asks for high-risk approval
 */
export type AutonomyLevel = 'READ_ONLY' | 'RECOMMENDATIONS' | 'ASSISTED' | 'SUPERVISED'

/**
 * Map autonomy level strings to integers for backend API
 */
const AUTONOMY_LEVEL_MAP: Record<AutonomyLevel, number> = {
  'READ_ONLY': 0,
  'RECOMMENDATIONS': 1,
  'ASSISTED': 2,
  'SUPERVISED': 3,
}

/**
 * Agent session state
 */
export interface AgentSession {
  session_id: string
  character_id: number
  autonomy_level: number | AutonomyLevel
  status: string
  created_at?: string
  updated_at?: string
  messages?: Array<{
    role: string
    content: string
    timestamp: string
  }>
}

/**
 * Request to create a new agent session
 */
export interface CreateSessionRequest {
  character_id: number
  autonomy_level?: AutonomyLevel
  initial_context?: Record<string, unknown>
}

/**
 * Request to send a chat message
 */
export interface ChatRequest {
  session_id: string
  message: string
  include_context?: boolean
}

/**
 * Response from chat history endpoint
 */
export interface ChatHistoryResponse {
  session_id: string
  messages: ChatMessage[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

/**
 * Milestone within a plan
 */
export interface Milestone {
  id: number
  plan_id: number
  title: string
  description?: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  order_index: number
  created_at: string
  completed_at?: string
}

/**
 * Plan for agent execution
 */
export interface Plan {
  id: number
  character_id: number
  title: string
  description?: string
  goal?: string
  status: 'draft' | 'active' | 'paused' | 'completed' | 'cancelled'
  priority: number
  created_at: string
  updated_at: string
  milestones?: Milestone[]
}

/**
 * Request to create a new plan
 */
export interface CreatePlanRequest {
  character_id: number
  title: string
  description?: string
  goal?: string
  priority?: number
}

/**
 * Request to create a new milestone
 */
export interface CreateMilestoneRequest {
  title: string
  description?: string
  order_index?: number
}

/**
 * Session restore summary
 */
export interface SessionRestoreSummary {
  session_id: string
  character_id: number
  last_activity: string
  message_count: number
  last_message_preview?: string
  context_summary?: Record<string, unknown>
}

// ============================================================================
// Agent API
// ============================================================================

export const agentApi = {
  // ==========================================================================
  // Session Management
  // ==========================================================================

  /**
   * Create a new agent session
   */
  createSession: async (data: CreateSessionRequest): Promise<AgentSession> => {
    // Convert autonomy level string to integer for backend
    const requestData = {
      character_id: data.character_id,
      autonomy_level: data.autonomy_level ? AUTONOMY_LEVEL_MAP[data.autonomy_level] : 1,
      initial_context: data.initial_context,
    }
    const response = await agentClient.post<AgentSession>('/session', requestData)
    // Server returns 'id' but frontend uses 'session_id' - map it
    return {
      ...response.data,
      session_id: response.data.session_id || (response.data as unknown as Record<string, unknown>).id as string,
    }
  },

  /**
   * Get an existing session by ID
   */
  getSession: async (sessionId: string): Promise<AgentSession> => {
    const response = await agentClient.get<AgentSession>(`/session/${sessionId}`)
    // Server returns 'id' but frontend uses 'session_id' - map it
    return {
      ...response.data,
      session_id: response.data.session_id || (response.data as unknown as Record<string, unknown>).id as string,
    }
  },

  /**
   * Delete a session
   */
  deleteSession: async (sessionId: string): Promise<void> => {
    await agentClient.delete(`/session/${sessionId}`)
  },

  // ==========================================================================
  // Chat
  // ==========================================================================

  /**
   * Send a chat message to the agent
   */
  chat: async (data: ChatRequest): Promise<ChatMessage> => {
    const response = await agentClient.post<ChatMessage>('/chat', data)
    return response.data
  },

  /**
   * Get chat history for a session
   */
  getChatHistory: async (
    sessionId: string,
    page?: number,
    pageSize?: number
  ): Promise<ChatHistoryResponse> => {
    const response = await agentClient.get<ChatHistoryResponse>(
      `/chat/history/${sessionId}`,
      {
        params: {
          page,
          page_size: pageSize,
        },
      }
    )
    // Map server's created_at to timestamp for frontend compatibility
    // Server may return created_at instead of timestamp, so we cast via unknown
    const mappedMessages = response.data.messages.map((msg) => {
      const serverMsg = msg as unknown as Record<string, unknown>
      return {
        id: serverMsg.id as string,
        role: serverMsg.role as MessageRole,
        content: serverMsg.content as string,
        timestamp: (serverMsg.timestamp || serverMsg.created_at || new Date().toISOString()) as string,
        isStreaming: false,
      }
    })
    return {
      ...response.data,
      messages: mappedMessages,
    }
  },

  /**
   * Stream chat response from the agent using Server-Sent Events
   * Returns a cleanup function to abort the stream
   */
  streamChat: (
    sessionId: string,
    characterId: number,
    message: string,
    onChunk: (chunk: string) => void,
    onError: (error: Error) => void,
    onComplete: () => void
  ): (() => void) => {
    console.log('[streamChat] Starting - sessionId:', sessionId, 'characterId:', characterId)

    // Validate session_id before making request
    if (!sessionId || sessionId === 'undefined') {
      console.error('[streamChat] Invalid sessionId:', sessionId)
      onError(new Error('Invalid session ID'))
      return () => {}
    }

    const abortController = new AbortController()

    // Use native fetch for SSE support (axios doesn't handle streaming well)
    const baseUrl = agentClient.defaults.baseURL || '/api/agent'
    const url = `${baseUrl}/chat/stream`
    console.log('[streamChat] Fetching:', url)

    const requestBody = {
      session_id: sessionId,
      character_id: characterId,
      message,
    }
    console.log('[streamChat] Request body:', JSON.stringify(requestBody))

    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(requestBody),
      signal: abortController.signal,
    })
      .then(async (response) => {
        console.log('[streamChat] Response status:', response.status)
        if (!response.ok) {
          const errorText = await response.text()
          console.error('[streamChat] Error response:', errorText)
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const reader = response.body?.getReader()
        if (!reader) {
          throw new Error('Response body is not readable')
        }
        console.log('[streamChat] Got reader, starting to read chunks...')

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()

          if (done) {
            onComplete()
            break
          }

          buffer += decoder.decode(value, { stream: true })

          // Process SSE events from buffer
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (let line of lines) {
            line = line.replace(/\r$/, '')

            if (line.startsWith('data: ')) {
              const data = line.slice(6)

              if (data === '[DONE]') {
                onComplete()
                return
              }

              try {
                const parsed = JSON.parse(data)
                console.log('[streamChat] Parsed SSE:', parsed.type, parsed.text?.substring(0, 30) || '')

                // Handle different response formats from copilot server
                if (parsed.type === 'text' && parsed.text) {
                  onChunk(parsed.text)
                } else if (parsed.content) {
                  onChunk(parsed.content)
                } else if (parsed.type === 'error' && parsed.error) {
                  onError(new Error(parsed.error))
                } else if (parsed.error) {
                  onError(new Error(parsed.error))
                }
                // Ignore "thinking" and "done" types - they don't contain text
              } catch {
                // If not JSON, treat as raw content
                console.log('[streamChat] Non-JSON data:', data.substring(0, 50))
                if (data.trim()) {
                  onChunk(data)
                }
              }
            }
          }
        }
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          console.error('[streamChat] Error:', error.message)
          onError(error)
        }
      })

    // Return cleanup function
    return () => {
      abortController.abort()
    }
  },

  // ==========================================================================
  // Plan Approval
  // ==========================================================================

  /**
   * Execute a pending plan
   */
  executePlan: async (
    sessionId: string,
    planId: string
  ): Promise<{ success: boolean; message: string }> => {
    const response = await agentClient.post<{ success: boolean; message: string }>(
      '/execute',
      { session_id: sessionId, plan_id: planId }
    )
    return response.data
  },

  /**
   * Reject a pending plan
   */
  rejectPlan: async (
    sessionId: string,
    planId: string,
    reason?: string
  ): Promise<{ success: boolean; message: string }> => {
    const response = await agentClient.post<{ success: boolean; message: string }>(
      '/reject',
      { session_id: sessionId, plan_id: planId, reason }
    )
    return response.data
  },

  // ==========================================================================
  // Plans API (Phase 1 backend)
  // ==========================================================================

  /**
   * Get plans for a character
   */
  getPlans: async (characterId: number, status?: string): Promise<Plan[]> => {
    const response = await agentClient.get<{ plans: Plan[] }>('/plans', {
      params: { character_id: characterId, status },
    })
    return response.data.plans
  },

  /**
   * Get a specific plan by ID
   */
  getPlan: async (planId: number): Promise<Plan> => {
    const response = await agentClient.get<Plan>(`/plans/${planId}`)
    return response.data
  },

  /**
   * Create a new plan
   */
  createPlan: async (data: CreatePlanRequest): Promise<Plan> => {
    const response = await agentClient.post<Plan>('/plans', data)
    return response.data
  },

  /**
   * Update an existing plan
   */
  updatePlan: async (planId: number, data: Partial<Plan>): Promise<Plan> => {
    const response = await agentClient.patch<Plan>(`/plans/${planId}`, data)
    return response.data
  },

  /**
   * Delete a plan
   */
  deletePlan: async (planId: number): Promise<void> => {
    await agentClient.delete(`/plans/${planId}`)
  },

  // ==========================================================================
  // Milestones
  // ==========================================================================

  /**
   * Add a milestone to a plan
   */
  addMilestone: async (
    planId: number,
    data: CreateMilestoneRequest
  ): Promise<Milestone> => {
    const response = await agentClient.post<Milestone>(
      `/plans/${planId}/milestones`,
      data
    )
    return response.data
  },

  /**
   * Update a milestone
   */
  updateMilestone: async (
    planId: number,
    milestoneId: number,
    data: Partial<Milestone>
  ): Promise<Milestone> => {
    const response = await agentClient.patch<Milestone>(
      `/plans/${planId}/milestones/${milestoneId}`,
      data
    )
    return response.data
  },

  // ==========================================================================
  // Context API
  // ==========================================================================

  /**
   * Get context for a character
   */
  getContext: async (characterId: number): Promise<Record<string, unknown>> => {
    const response = await agentClient.get<Record<string, unknown>>(
      `/context/${characterId}`
    )
    return response.data
  },

  /**
   * Set a context value for a character
   */
  setContext: async (
    characterId: number,
    key: string,
    value: unknown,
    source?: string
  ): Promise<{ success: boolean }> => {
    const response = await agentClient.post<{ success: boolean }>(
      `/context/${characterId}`,
      { key, value, source }
    )
    return response.data
  },

  // ==========================================================================
  // Session Restore
  // ==========================================================================

  /**
   * Get last session summary for a character
   * Returns null if no previous session exists
   */
  getLastSessionSummary: async (
    characterId: number
  ): Promise<SessionRestoreSummary | null> => {
    try {
      const response = await agentClient.get<SessionRestoreSummary>(
        `/session/restore/${characterId}`
      )
      return response.data
    } catch {
      // Return null if no session found or any error occurs
      return null
    }
  },
}
