import { useState, useEffect, useRef, useCallback } from 'react';
import type { AgentEvent } from '../types/agent-events';

export interface UseAgentWebSocketOptions {
  sessionId: string;
  onEvent?: (event: AgentEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
}

export interface UseAgentWebSocketReturn {
  events: AgentEvent[];
  isConnected: boolean;
  error: string | null;
  clearEvents: () => void;
  reconnect: () => void;
}

// Use relative WebSocket URL to leverage Vite proxy for correct backend routing
const WS_URL = import.meta.env.VITE_WS_URL || (
  typeof window !== 'undefined'
    ? `ws://${window.location.host}`
    : 'ws://localhost:3000'
);

const MAX_RECONNECT_ATTEMPTS = 5;

export function useAgentWebSocket({
  sessionId,
  onEvent,
  onConnect,
  onDisconnect,
  onError,
  autoReconnect = true,
  reconnectInterval = 3000,
}: UseAgentWebSocketOptions): UseAgentWebSocketReturn {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const mountedRef = useRef(true);
  const pingIntervalRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);

  // Store callbacks in refs to avoid re-creating connect on every render
  const onEventRef = useRef(onEvent);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  const onErrorRef = useRef(onError);

  onEventRef.current = onEvent;
  onConnectRef.current = onConnect;
  onDisconnectRef.current = onDisconnect;
  onErrorRef.current = onError;

  const cleanupConnection = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror = null;
      wsRef.current.onclose = null;
      if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.close(1000, 'Cleanup');
      }
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    if (!sessionId || sessionId.trim() === '') {
      console.log('[AgentWS] Skipping connection - no session ID');
      return;
    }

    // Clean up any existing connection before creating a new one
    cleanupConnection();

    try {
      const ws = new WebSocket(`${WS_URL}/agent/stream/${sessionId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) {
          ws.close(1000, 'Component unmounted during connect');
          return;
        }
        console.log(`[AgentWS] Connected to session ${sessionId}`);
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        onConnectRef.current?.();

        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        if (event.data === 'pong') return;

        try {
          const agentEvent: AgentEvent = JSON.parse(event.data);
          setEvents((prev) => [...prev, agentEvent]);
          onEventRef.current?.(agentEvent);
        } catch (err) {
          console.error('[AgentWS] Failed to parse event:', err);
          setError('Failed to parse event data');
        }
      };

      ws.onerror = (event) => {
        if (!mountedRef.current) return;
        console.error('[AgentWS] WebSocket error:', event);
        setError('WebSocket connection error');

        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        onErrorRef.current?.(event);
      };

      ws.onclose = (event) => {
        if (!mountedRef.current) return;
        console.log(`[AgentWS] Disconnected: ${event.code} ${event.reason}`);
        setIsConnected(false);
        wsRef.current = null;

        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        onDisconnectRef.current?.();

        // Auto-reconnect if enabled and not a normal closure
        if (autoReconnect && event.code !== 1000 && mountedRef.current) {
          reconnectAttemptsRef.current++;

          if (reconnectAttemptsRef.current <= MAX_RECONNECT_ATTEMPTS) {
            console.log(`[AgentWS] Reconnecting in ${reconnectInterval}ms... (Attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`);
            reconnectTimeoutRef.current = setTimeout(() => {
              if (mountedRef.current) connect();
            }, reconnectInterval);
          } else {
            console.log(`[AgentWS] Max reconnect attempts (${MAX_RECONNECT_ATTEMPTS}) reached. Stopping.`);
            setError('WebSocket connection failed after multiple attempts');
          }
        }
      };
    } catch (err) {
      console.error('[AgentWS] Failed to connect:', err);
      wsRef.current = null;
      setError('Failed to establish WebSocket connection');

      if (autoReconnect && mountedRef.current) {
        reconnectAttemptsRef.current++;

        if (reconnectAttemptsRef.current <= MAX_RECONNECT_ATTEMPTS) {
          reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current) connect();
          }, reconnectInterval);
        } else {
          setError('WebSocket connection failed after multiple attempts');
        }
      }
    }
  }, [sessionId, autoReconnect, reconnectInterval, cleanupConnection]);

  useEffect(() => {
    mountedRef.current = true;
    reconnectAttemptsRef.current = 0;
    connect();

    return () => {
      mountedRef.current = false;
      cleanupConnection();
    };
  }, [connect, cleanupConnection]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    connect();
  }, [connect]);

  return {
    events,
    isConnected,
    error,
    clearEvents,
    reconnect,
  };
}
