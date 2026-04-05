import { useState, useEffect } from 'react';
import { Plus, MessageSquare, Trash2, Clock } from 'lucide-react';

export interface SessionInfo {
  sessionId: string;
  title: string;
  createdAt: Date;
  lastMessageAt: Date;
  messageCount: number;
}

interface SessionListProps {
  currentSessionId: string;
  onSessionSelect: (sessionId: string) => void;
  onNewSession: () => void;
}

const SESSION_STORAGE_KEY = 'eve-copilot-sessions';

function SessionList({ currentSessionId, onSessionSelect, onNewSession }: SessionListProps) {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [isExpanded, setIsExpanded] = useState(true);

  // Load sessions from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(SESSION_STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        // Convert date strings back to Date objects
        const sessionsWithDates = parsed.map((s: SessionInfo) => ({
          ...s,
          createdAt: new Date(s.createdAt),
          lastMessageAt: new Date(s.lastMessageAt),
        }));
        setSessions(sessionsWithDates);
      } catch (e) {
        console.error('Failed to parse stored sessions:', e);
      }
    }
  }, []);

  // Save sessions to localStorage when changed
  useEffect(() => {
    if (sessions.length > 0) {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessions));
    }
  }, [sessions]);

  // Add current session if not in list
  useEffect(() => {
    if (currentSessionId && !sessions.find(s => s.sessionId === currentSessionId)) {
      const newSession: SessionInfo = {
        sessionId: currentSessionId,
        title: `Chat ${new Date().toLocaleDateString()}`,
        createdAt: new Date(),
        lastMessageAt: new Date(),
        messageCount: 0,
      };
      setSessions(prev => [newSession, ...prev]);
    }
  }, [currentSessionId, sessions]);

  const handleDeleteSession = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    setSessions(prev => prev.filter(s => s.sessionId !== sessionId));
    // If deleting current session, create new one
    if (sessionId === currentSessionId) {
      onNewSession();
    }
  };

  const formatDate = (date: Date): string => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  // Group sessions by date
  const groupedSessions = sessions.reduce((groups, session) => {
    const dateKey = formatDate(session.lastMessageAt);
    if (!groups[dateKey]) {
      groups[dateKey] = [];
    }
    groups[dateKey].push(session);
    return groups;
  }, {} as Record<string, SessionInfo[]>);

  return (
    <div className={`session-list ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <div className="session-list-header">
        <h3 onClick={() => setIsExpanded(!isExpanded)}>
          <Clock size={16} />
          History
        </h3>
        <button
          className="new-session-btn"
          onClick={onNewSession}
          title="New chat"
        >
          <Plus size={16} />
        </button>
      </div>

      {isExpanded && (
        <div className="session-list-content">
          {Object.entries(groupedSessions).map(([dateKey, dateSessions]) => (
            <div key={dateKey} className="session-group">
              <div className="session-group-header">{dateKey}</div>
              {dateSessions.map(session => (
                <div
                  key={session.sessionId}
                  className={`session-item ${session.sessionId === currentSessionId ? 'active' : ''}`}
                  onClick={() => onSessionSelect(session.sessionId)}
                >
                  <MessageSquare size={14} />
                  <span className="session-title">{session.title}</span>
                  <button
                    className="session-delete-btn"
                    onClick={(e) => handleDeleteSession(e, session.sessionId)}
                    title="Delete chat"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
            </div>
          ))}

          {sessions.length === 0 && (
            <div className="no-sessions">
              <p>No previous chats</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Export function to update session info from outside
export function updateSessionInfo(
  sessionId: string,
  updates: Partial<Omit<SessionInfo, 'sessionId'>>
): void {
  const stored = localStorage.getItem(SESSION_STORAGE_KEY);
  if (stored) {
    try {
      const sessions: SessionInfo[] = JSON.parse(stored);
      const index = sessions.findIndex(s => s.sessionId === sessionId);
      if (index !== -1) {
        sessions[index] = { ...sessions[index], ...updates };
        localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessions));
      }
    } catch (e) {
      console.error('Failed to update session:', e);
    }
  }
}

export default SessionList;
