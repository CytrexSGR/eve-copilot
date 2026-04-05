import { useState, useEffect } from 'react';
import { notificationApi } from '../../services/api/military';
import type { EsiNotification, NotificationType } from '../../types/military';

function formatRelativeTime(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function formatNotificationType(type: string): string {
  return type.replace(/([A-Z])/g, ' $1').trim();
}

function getTypeBadgeColor(type: string): string {
  if (
    type.startsWith('Structure') &&
    (type.includes('Attack') || type.includes('Lost') || type.includes('Destroyed'))
  ) {
    return '#f85149';
  }
  if (type.startsWith('Sov')) return '#ff8800';
  return '#00d4ff';
}

const SENDER_COLORS: Record<string, string> = {
  character: '#3fb950',
  corporation: '#d29922',
  alliance: '#a855f7',
  faction: '#f85149',
};

const selectStyle: React.CSSProperties = {
  background: 'var(--bg-primary)',
  color: 'var(--text-primary)',
  border: '1px solid var(--border-color)',
  borderRadius: '6px',
  padding: '5px 8px',
  fontSize: '0.85rem',
};

const cardBase: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-color)',
  borderRadius: '8px',
};

export function Notifications() {
  const [notifications, setNotifications] = useState<EsiNotification[]>([]);
  const [types, setTypes] = useState<NotificationType[]>([]);
  const [selectedType, setSelectedType] = useState<string>('');
  const [unprocessedOnly, setUnprocessedOnly] = useState(false);
  const [limit, setLimit] = useState(50);
  const [loading, setLoading] = useState(true);
  const [typeSummaryOpen, setTypeSummaryOpen] = useState(false);

  useEffect(() => {
    notificationApi.getTypes().then(res => setTypes(res.types || [])).catch(() => {});
  }, []);

  const fetchNotifications = () => {
    setLoading(true);
    notificationApi.getRecent({
      limit,
      notification_type: selectedType || undefined,
      unprocessed_only: unprocessedOnly || undefined,
    })
      .then(res => setNotifications(res.notifications || []))
      .catch(() => setNotifications([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchNotifications();
  }, [selectedType, unprocessedOnly, limit]);

  const handleMarkProcessed = (id: number) => {
    notificationApi.markProcessed(id).then(() => {
      setNotifications(prev =>
        prev.map(n => (n.notificationId === id ? { ...n, processed: true } : n))
      );
      setTypes(prev =>
        prev.map(t => {
          const match = notifications.find(n => n.notificationId === id);
          if (match && match.type === t.type) return { ...t, count: Math.max(0, t.count - 1) };
          return t;
        })
      );
    });
  };

  const sortedTypes = [...types].sort((a, b) => b.count - a.count);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* Filter Bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap',
        padding: '10px 14px', ...cardBase,
      }}>
        <select
          value={selectedType}
          onChange={e => setSelectedType(e.target.value)}
          style={{ ...selectStyle, minWidth: '200px' }}
        >
          <option value="">All Types</option>
          {sortedTypes.map(t => (
            <option key={t.type} value={t.type}>
              {formatNotificationType(t.type)} ({t.count})
            </option>
          ))}
        </select>

        <label style={{
          display: 'flex', alignItems: 'center', gap: '5px',
          fontSize: '0.85rem', color: 'var(--text-primary)',
          cursor: 'pointer', userSelect: 'none',
        }}>
          <input
            type="checkbox"
            checked={unprocessedOnly}
            onChange={e => setUnprocessedOnly(e.target.checked)}
            style={{ accentColor: '#00d4ff' }}
          />
          Unprocessed only
        </label>

        <select value={limit} onChange={e => setLimit(Number(e.target.value))} style={selectStyle}>
          {[25, 50, 100, 200].map(v => (
            <option key={v} value={v}>{v}</option>
          ))}
        </select>

        <button onClick={fetchNotifications} style={{
          background: 'transparent', color: '#00d4ff', border: '1px solid #00d4ff',
          borderRadius: '6px', padding: '5px 12px', fontSize: '0.85rem', cursor: 'pointer',
        }}>
          Refresh
        </button>
      </div>

      {/* Type Summary Panel (collapsible) */}
      {types.length > 0 && (
        <div style={{ ...cardBase, overflow: 'hidden' }}>
          <button
            onClick={() => setTypeSummaryOpen(prev => !prev)}
            style={{
              width: '100%', display: 'flex', alignItems: 'center',
              justifyContent: 'space-between', padding: '8px 14px',
              background: 'transparent', border: 'none',
              color: 'var(--text-primary)', cursor: 'pointer',
              fontSize: '0.85rem', fontWeight: 600,
            }}
          >
            <span>Type Summary ({types.length} types)</span>
            <span style={{ fontSize: '0.7rem', opacity: 0.6 }}>
              {typeSummaryOpen ? '\u25B2 Collapse' : '\u25BC Expand'}
            </span>
          </button>

          {typeSummaryOpen && (
            <div style={{ padding: '0 14px 10px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                <thead>
                  <tr style={{
                    borderBottom: '1px solid var(--border-color)',
                    color: 'rgba(255,255,255,0.5)',
                  }}>
                    <th style={{ textAlign: 'left', padding: '4px 8px', fontWeight: 500 }}>Type</th>
                    <th style={{ textAlign: 'right', padding: '4px 8px', fontWeight: 500 }}>Count</th>
                    <th style={{ textAlign: 'right', padding: '4px 8px', fontWeight: 500 }}>Latest</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedTypes.map(t => (
                    <tr key={t.type} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <td style={{ padding: '3px 8px' }}>
                        <span style={{
                          display: 'inline-block', padding: '1px 6px', borderRadius: '4px',
                          background: `${getTypeBadgeColor(t.type)}22`,
                          color: getTypeBadgeColor(t.type), fontSize: '0.75rem',
                        }}>
                          {formatNotificationType(t.type)}
                        </span>
                      </td>
                      <td style={{
                        textAlign: 'right', padding: '3px 8px', fontFamily: 'monospace',
                      }}>
                        {t.count}
                      </td>
                      <td style={{
                        textAlign: 'right', padding: '3px 8px', fontFamily: 'monospace',
                        fontSize: '0.7rem', opacity: 0.7,
                      }}>
                        {t.latest ? formatRelativeTime(t.latest) : '\u2014'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {[...Array(5)].map((_, i) => (
            <div key={i} style={{
              ...cardBase, height: '56px', opacity: 0.5 - i * 0.08,
              animation: 'notifPulse 1.5s ease-in-out infinite',
            }} />
          ))}
          <style>{`
            @keyframes notifPulse {
              0%, 100% { opacity: 0.3; }
              50% { opacity: 0.15; }
            }
          `}</style>
        </div>
      )}

      {/* Empty State */}
      {!loading && notifications.length === 0 && (
        <div style={{
          padding: '40px 20px', textAlign: 'center', ...cardBase,
          color: 'rgba(255,255,255,0.4)', fontSize: '0.9rem',
        }}>
          No notifications found
        </div>
      )}

      {/* Notification List */}
      {!loading && notifications.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {notifications.map(n => {
            const color = getTypeBadgeColor(n.type);
            const unprocessed = !n.processed;

            return (
              <div key={n.notificationId} style={{
                display: 'flex', alignItems: 'center', gap: '10px',
                padding: '10px 14px', minHeight: '48px',
                background: unprocessed ? 'rgba(255,255,255,0.04)' : 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                borderLeft: `3px solid ${color}`,
                borderRadius: '8px',
              }}>
                {/* Type Badge */}
                <span style={{
                  display: 'inline-block', padding: '2px 8px', borderRadius: '6px',
                  background: `${color}22`, color, fontSize: '0.75rem', fontWeight: 600,
                  whiteSpace: 'nowrap', flexShrink: 0,
                  maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis',
                }}>
                  {formatNotificationType(n.type)}
                </span>

                {/* Timestamp (relative + absolute on hover) */}
                <span
                  title={new Date(n.timestamp).toLocaleString()}
                  style={{
                    fontFamily: 'monospace', fontSize: '0.7rem',
                    color: 'rgba(255,255,255,0.5)', whiteSpace: 'nowrap', flexShrink: 0,
                  }}
                >
                  {formatRelativeTime(n.timestamp)}
                </span>

                {/* Sender Type Badge */}
                {n.senderType && (
                  <span style={{
                    display: 'inline-block', padding: '1px 6px', borderRadius: '4px',
                    background: `${SENDER_COLORS[n.senderType] || '#888'}22`,
                    color: SENDER_COLORS[n.senderType] || '#888',
                    fontSize: '0.7rem', whiteSpace: 'nowrap', flexShrink: 0,
                  }}>
                    {n.senderType}
                  </span>
                )}

                {/* Spacer */}
                <div style={{ flex: 1 }} />

                {/* Processed Status Indicator */}
                <span
                  style={{ fontSize: '0.85rem', flexShrink: 0 }}
                  title={n.processed ? 'Processed' : 'Unprocessed'}
                >
                  {n.processed
                    ? <span style={{ color: '#3fb950' }}>&#10003;</span>
                    : <span style={{ color: '#555' }}>&#9679;</span>
                  }
                </span>

                {/* Mark Processed Button (unprocessed only) */}
                {unprocessed && (
                  <button
                    onClick={() => handleMarkProcessed(n.notificationId)}
                    style={{
                      background: 'transparent', color: '#00d4ff',
                      border: '1px solid rgba(0,212,255,0.3)', borderRadius: '6px',
                      padding: '2px 8px', fontSize: '0.7rem', cursor: 'pointer',
                      whiteSpace: 'nowrap', flexShrink: 0,
                    }}
                  >
                    Mark Processed
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
