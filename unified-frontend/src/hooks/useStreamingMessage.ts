import { useState, useRef, useCallback } from 'react';

interface UseStreamingMessageReturn {
  content: string;
  isStreaming: boolean;
  appendChunk: (chunk: string) => void;
  setContent: (content: string) => void;
  complete: () => void;
  reset: () => void;
}

/**
 * Hook for managing streaming message content.
 * Provides utilities to append chunks, complete streaming, and reset state.
 * Uses a ref to avoid stale closure issues in appendChunk callbacks.
 */
export function useStreamingMessage(): UseStreamingMessageReturn {
  const [content, setContentState] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);

  // Use ref to track current content and avoid stale closures
  const contentRef = useRef('');

  const appendChunk = useCallback((chunk: string) => {
    // Start streaming if not already
    setIsStreaming((prev) => {
      if (!prev) {
        return true;
      }
      return prev;
    });

    // Update ref and state
    contentRef.current += chunk;
    setContentState(contentRef.current);
  }, []);

  const setContent = useCallback((newContent: string) => {
    contentRef.current = newContent;
    setContentState(newContent);
  }, []);

  const complete = useCallback(() => {
    setIsStreaming(false);
  }, []);

  const reset = useCallback(() => {
    contentRef.current = '';
    setContentState('');
    setIsStreaming(false);
  }, []);

  return {
    content,
    isStreaming,
    appendChunk,
    setContent,
    complete,
    reset,
  };
}

export default useStreamingMessage;
