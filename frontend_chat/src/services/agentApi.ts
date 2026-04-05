/**
 * Agent API Client
 * REST and SSE API communication for Phase 7 Agent Runtime
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export interface AgentSession {
  session_id: string;
  character_id?: number;
  autonomy_level: number;
  status: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  content_blocks?: ContentBlock[];
  created_at: string;
  token_usage?: TokenUsage;
}

export interface ContentBlock {
  type: string;
  text?: string;
  tool_calls?: ToolCallResult[];
}

export interface ToolCallResult {
  tool: string;
  result: unknown;
}

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
}

export interface ChatHistoryResponse {
  session_id: string;
  messages: ChatMessage[];
  message_count: number;
}

// SSE Event types
export type SSEEventType =
  | 'text'
  | 'thinking'
  | 'tool_call_started'
  | 'tool_call_completed'
  | 'authorization_denied'
  | 'error'
  | 'done';

export interface SSEEvent {
  type: SSEEventType;
  text?: string;
  iteration?: number;
  tool?: string;
  arguments?: Record<string, unknown>;
  reason?: string;
  error?: string;
  message_id?: string;
}

export const agentApi = {
  /**
   * Create a new agent session
   */
  async createSession(characterId?: number, autonomyLevel: number = 1): Promise<AgentSession> {
    const response = await fetch(`${API_BASE_URL}/agent/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        character_id: characterId,
        autonomy_level: autonomyLevel,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.status}`);
    }

    return response.json();
  },

  /**
   * Get session details
   */
  async getSession(sessionId: string): Promise<AgentSession> {
    const response = await fetch(`${API_BASE_URL}/agent/session/${sessionId}`);

    if (!response.ok) {
      throw new Error(`Failed to get session: ${response.status}`);
    }

    return response.json();
  },

  /**
   * Delete a session
   */
  async deleteSession(sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/agent/session/${sessionId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to delete session: ${response.status}`);
    }
  },

  /**
   * Get chat history for a session
   */
  async getChatHistory(sessionId: string, limit: number = 100): Promise<ChatHistoryResponse> {
    const response = await fetch(
      `${API_BASE_URL}/agent/chat/history/${sessionId}?limit=${limit}`
    );

    if (!response.ok) {
      throw new Error(`Failed to get chat history: ${response.status}`);
    }

    return response.json();
  },

  /**
   * Stream chat response via SSE
   * Returns an async generator that yields SSE events
   */
  async *streamChat(
    sessionId: string,
    message: string,
    characterId: number = -1
  ): AsyncGenerator<SSEEvent, void, unknown> {
    const response = await fetch(`${API_BASE_URL}/agent/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        message,
        character_id: characterId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to stream chat: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data.trim()) {
              try {
                const event = JSON.parse(data) as SSEEvent;
                yield event;

                // Stop on done or error
                if (event.type === 'done' || event.type === 'error') {
                  return;
                }
              } catch (e) {
                console.error('Failed to parse SSE event:', data, e);
              }
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  /**
   * Audio transcription (uses legacy endpoint)
   */
  async transcribeAudio(audioBlob: Blob): Promise<{ text: string }> {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');

    const response = await fetch(`${API_BASE_URL}/copilot/audio/transcribe`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Failed to transcribe audio');
    }

    return response.json();
  },

  /**
   * Text-to-speech synthesis (uses legacy endpoint)
   */
  async synthesizeSpeech(text: string, voice?: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/copilot/audio/synthesize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice }),
    });

    if (!response.ok) {
      throw new Error('Failed to synthesize speech');
    }

    const data = await response.json();
    // Convert hex string to blob
    const bytes = new Uint8Array(
      data.audio.match(/.{1,2}/g).map((byte: string) => parseInt(byte, 16))
    );
    return new Blob([bytes], { type: 'audio/mpeg' });
  },

  /**
   * Health check
   */
  async getHealth(): Promise<{ status: string; llm: string; mcp_tools: number }> {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.json();
  },
};
