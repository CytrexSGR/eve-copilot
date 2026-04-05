import { Link } from 'react-router-dom';
import type { Alert } from '../../types/alerts';
import { ALERT_COLORS } from '../../types/alerts';

export function AlertPanel({ alerts, onDismiss, onDismissAll, onClose }: {
  alerts: Alert[];
  onDismiss: (id: string) => void;
  onDismissAll: () => void;
  onClose: () => void;
}) {
  const visible = alerts.filter(a => !a.dismissed);

  return (
    <div style={{
      position: 'absolute', top: '100%', right: 0, marginTop: '8px',
      width: '320px', maxHeight: '400px', overflowY: 'auto',
      background: '#111827', border: '1px solid var(--border-color)',
      borderRadius: '8px', boxShadow: '0 8px 32px rgba(0,0,0,0.6)', zIndex: 1001,
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '0.5rem 0.65rem', borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase' }}>
          Alerts ({visible.length})
        </span>
        {visible.length > 0 && (
          <button
            onClick={onDismissAll}
            style={{
              background: 'none', border: 'none', color: 'rgba(255,255,255,0.3)',
              fontSize: '0.6rem', cursor: 'pointer',
            }}
          >
            Clear All
          </button>
        )}
      </div>
      {visible.length === 0 ? (
        <div style={{ padding: '1.5rem', textAlign: 'center', color: 'rgba(255,255,255,0.2)', fontSize: '0.75rem' }}>
          No active alerts
        </div>
      ) : visible.map(alert => (
        <div key={alert.id} style={{
          display: 'flex', gap: '0.4rem', padding: '0.5rem 0.65rem',
          borderBottom: '1px solid rgba(255,255,255,0.04)',
        }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%', marginTop: '4px', flexShrink: 0,
            background: ALERT_COLORS[alert.type],
          }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600 }}>{alert.title}</div>
            <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.35)' }}>{alert.message}</div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', alignItems: 'flex-end', flexShrink: 0 }}>
            {alert.actionUrl && (
              <Link to={alert.actionUrl} onClick={onClose} style={{
                fontSize: '0.6rem', color: '#00d4ff', textDecoration: 'none', fontWeight: 600,
              }}>Go</Link>
            )}
            <button onClick={() => onDismiss(alert.id)} style={{
              background: 'none', border: 'none', color: 'rgba(255,255,255,0.2)',
              fontSize: '0.55rem', cursor: 'pointer',
            }}>dismiss</button>
          </div>
        </div>
      ))}
    </div>
  );
}
