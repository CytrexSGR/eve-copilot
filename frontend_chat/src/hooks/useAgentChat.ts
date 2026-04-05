/**
 * Agent Chat Hook
 * React hook for Agent API with SSE streaming
 */

import { useState, useCallback, useRef } from 'react';
import { agentApi } from '../services/agentApi';
import type { SSEEvent } from '../services/agentApi';
import type { Message, ToolCall } from '../types';

interface UseAgentChatResult {
  messages: Message[];
  isStreaming: boolean;
  currentTool: string | null;
  error: string | null;
  sendMessage: (message: string) => Promise<void>;
  clearMessages: () => void;
}

export function useAgentChat(sessionId: string, characterId?: number): UseAgentChatResult {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentTool, setCurrentTool] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Track current streaming message for accumulation
  const streamingMessageRef = useRef<{
    id: string;
    content: string;
    toolCalls: ToolCall[];
  } | null>(null);

  const sendMessage = useCallback(
    async (message: string) => {
      if (!sessionId || isStreaming) return;

      setError(null);
      setIsStreaming(true);
      setCurrentTool(null);

      // Add user message immediately
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: message,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Initialize streaming message
      const assistantId = `assistant-${Date.now()}`;
      streamingMessageRef.current = {
        id: assistantId,
        content: '',
        toolCalls: [],
      };

      // Add placeholder for assistant message
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: 'assistant',
          content: '',
          tool_calls: [],
          timestamp: new Date(),
        },
      ]);

      try {
        // Stream the response
        for await (const event of agentApi.streamChat(
          sessionId,
          message,
          characterId || -1
        )) {
          handleSSEEvent(event);
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Unknown error';
        setError(errorMsg);

        // Update the streaming message with error
        if (streamingMessageRef.current) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === streamingMessageRef.current?.id
                ? { ...msg, content: `Error: ${errorMsg}` }
                : msg
            )
          );
        }
      } finally {
        setIsStreaming(false);
        setCurrentTool(null);
        streamingMessageRef.current = null;
      }
    },
    [sessionId, characterId, isStreaming]
  );

  const handleSSEEvent = useCallback((event: SSEEvent) => {
    if (!streamingMessageRef.current) return;

    const currentMessage = streamingMessageRef.current;

    switch (event.type) {
      case 'text':
        // Accumulate text content
        currentMessage.content += event.text || '';
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === currentMessage.id
              ? { ...msg, content: currentMessage.content }
              : msg
          )
        );
        break;

      case 'thinking':
        // Could show iteration indicator in UI
        break;

      case 'tool_call_started':
        // Show which tool is running
        setCurrentTool(event.tool || null);
        break;

      case 'tool_call_completed':
        // Add to tool calls list
        if (event.tool) {
          currentMessage.toolCalls.push({
            tool: event.tool,
            input: {}, // Input was shown in started event
            result: null, // Result not included in completed event
          });
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === currentMessage.id
                ? { ...msg, tool_calls: [...currentMessage.toolCalls] }
                : msg
            )
          );
        }
        setCurrentTool(null);
        break;

      case 'authorization_denied':
        // Show authorization denied in message
        currentMessage.content += `\n\n⚠️ Authorization denied for tool: ${event.tool}\nReason: ${event.reason}`;
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === currentMessage.id
              ? { ...msg, content: currentMessage.content }
              : msg
          )
        );
        break;

      case 'error':
        setError(event.error || 'Unknown error');
        break;

      case 'done':
        // Streaming complete
        setCurrentTool(null);
        break;
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isStreaming,
    currentTool,
    error,
    sendMessage,
    clearMessages,
  };
}
