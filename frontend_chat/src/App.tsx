import { useState, useEffect, useCallback } from 'react';
import { agentApi } from './services/agentApi';
import './styles/app.css';
import './styles/sidebar.css';
import ChatWindow from './components/ChatWindow';
import ContextPanel from './components/ContextPanel';
import SessionList from './components/SessionList';
import type { ChatContext } from './types';

// Default region (Jita)
const DEFAULT_REGION_ID = 10000002;

function App() {
  const [context, setContext] = useState<ChatContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create a new session using Agent API
  const createNewSession = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const session = await agentApi.createSession(undefined, 1); // autonomy_level 1 (RECOMMENDATIONS)
      setContext({
        sessionId: session.session_id,
        regionId: DEFAULT_REGION_ID,
        characterId: session.character_id,
      });
    } catch (err) {
      setError('Failed to create session');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Handle session selection (for now, just create new - TODO: restore sessions)
  const handleSessionSelect = useCallback((sessionId: string) => {
    if (context?.sessionId !== sessionId) {
      // For now, we create a new session - full history restoration would require
      // backend support for loading conversation history
      setContext(prev => prev ? { ...prev, sessionId } : null);
    }
  }, [context?.sessionId]);

  // Initialize on mount
  useEffect(() => {
    createNewSession();
  }, [createNewSession]);

  if (loading && !context) {
    return (
      <div className="app-loading">
        <div className="spinner"></div>
        <p>Initializing EVE Co-Pilot...</p>
      </div>
    );
  }

  if (error && !context) {
    return (
      <div className="app-error">
        <h2>Connection Error</h2>
        <p>{error}</p>
        <button onClick={createNewSession}>Retry</button>
      </div>
    );
  }

  if (!context) {
    return null;
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>
          <span className="logo">⚡</span>
          EVE Co-Pilot AI
        </h1>
        <div className="header-actions">
          <span className="session-id">Session: {context.sessionId.slice(0, 8)}</span>
        </div>
      </header>

      <div className="app-main">
        <SessionList
          currentSessionId={context.sessionId}
          onSessionSelect={handleSessionSelect}
          onNewSession={createNewSession}
        />
        <ContextPanel context={context} onContextChange={setContext} />
        <ChatWindow context={context} />
      </div>
    </div>
  );
}

export default App;
