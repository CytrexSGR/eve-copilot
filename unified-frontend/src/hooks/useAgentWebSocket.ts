import { useState, useEffect, useRef, useCallback } from 'react';
import { AgentEvent } from '../types/agent-events';

interface UseAgentWebSocketOptions {
  sessionId: string | null;
  onEvent?: (event: AgentEvent) => void;
  maxReconnectAttempts?: number;
}

interface UseAgentWebSocketReturn {
  events: AgentEvent[];
  isConnected: boolean;
  error: string | null;
  clearEvents: () => void;
  reconnect: () => void;
}

const DEFAULT_MAX_RECONNECT_ATTEMPTS = 5;
const MAX_RECONNECT_DELAY_MS = 30000;
const PING_INTERVAL_MS = 30000;

/**
 * Hook for managing WebSocket connection to the agent streaming endpoint.
 * Handles auto-reconnect with exponential backoff and ping/pong keep-alive.
 */
export function useAgentWebSocket(
  options: UseAgentWebSocketOptions
): UseAgentWebSocketReturn {
  const { sessionId, onEvent, maxReconnectAttempts = DEFAULT_MAX_RECONNECT_ATTEMPTS } = options;

  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const clearPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  const cleanup = useCallback(() => {
    clearReconnectTimeout();
    clearPingInterval();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, [clearReconnectTimeout, clearPingInterval]);

  const getWebSocketUrl = useCallback((sid: string): string => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const hostname = window.location.hostname;
    return `${protocol}//${hostname}:8002/agent/stream/${sid}`;
  }, []);

  const startPingPong = useCallback(() => {
    clearPingInterval();
    pingIntervalRef.current = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, PING_INTERVAL_MS);
  }, [clearPingInterval]);

  const connect = useCallback(() => {
    if (!sessionId) {
      return;
    }

    cleanup();
    setError(null);

    const url = getWebSocketUrl(sessionId);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
      reconnectAttemptsRef.current = 0;
      startPingPong();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Handle pong responses (ignore them)
        if (data.type === 'pong') {
          return;
        }

        // Parse as AgentEvent
        const agentEvent = data as AgentEvent;
        setEvents((prev) => [...prev, agentEvent]);

        if (onEvent) {
          onEvent(agentEvent);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      setError('WebSocket connection error');
    };

    ws.onclose = () => {
      setIsConnected(false);
      clearPingInterval();

      // Don't reconnect if we closed intentionally or session is null
      if (!sessionId) {
        return;
      }

      // Attempt reconnect if we haven't exceeded max attempts
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        const delay = Math.min(
          1000 * Math.pow(2, reconnectAttemptsRef.current),
          MAX_RECONNECT_DELAY_MS
        );

        reconnectAttemptsRef.current += 1;
        setError(`Connection lost. Reconnecting in ${delay / 1000}s... (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);

        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, delay);
      } else {
        setError(`Connection lost. Max reconnect attempts (${maxReconnectAttempts}) exceeded.`);
      }
    };
  }, [sessionId, onEvent, maxReconnectAttempts, cleanup, getWebSocketUrl, startPingPong, clearPingInterval]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    connect();
  }, [connect]);

  // Connect when sessionId changes
  useEffect(() => {
    if (sessionId) {
      connect();
    } else {
      cleanup();
      setIsConnected(false);
      setError(null);
    }

    return () => {
      cleanup();
    };
  }, [sessionId, connect, cleanup]);

  return {
    events,
    isConnected,
    error,
    clearEvents,
    reconnect,
  };
}

export default useAgentWebSocket;
