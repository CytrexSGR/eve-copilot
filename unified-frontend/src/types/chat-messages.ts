/**
 * Chat Message Types for AI Copilot
 * Defines types for chat messages and streaming
 */

/**
 * Role of the message sender
 */
export type MessageRole = 'user' | 'assistant' | 'system';

/**
 * Status of a tool call
 */
export type ToolCallStatus = 'pending' | 'running' | 'completed' | 'failed';

/**
 * Represents a tool call within a chat message
 */
export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: unknown;
  status: ToolCallStatus;
  error?: string;
}

/**
 * Represents a chat message in the conversation
 */
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  isStreaming?: boolean;
  toolCalls?: ToolCall[];
}

/**
 * Type of stream chunk
 */
export type StreamChunkType = 'text' | 'tool_call' | 'tool_result' | 'error' | 'done';

/**
 * Represents a chunk of streamed data from the server
 */
export interface StreamChunk {
  type: StreamChunkType;
  content?: string;
  tool_call?: {
    id: string;
    name: string;
    arguments: Record<string, unknown>;
  };
  tool_result?: {
    id: string;
    result: unknown;
    error?: string;
  };
  error?: string;
}
