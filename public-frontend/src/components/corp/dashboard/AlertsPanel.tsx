import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { srpApi } from '../../../services/api/srp';
import { applicationApi } from '../../../services/api/hr';
import { timerApi } from '../../../services/api/timers';
import { fontSize, color, spacing } from '../../../styles/theme';

interface Alert {
  message: string;
  link: string;
  color: string;
}

interface AlertsPanelProps {
  corpId: number;
}

export function AlertsPanel({ corpId }: AlertsPanelProps) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchAlerts() {
      setLoading(true);

      const results = await Promise.allSettled([
        srpApi.getRequests(corpId, { status: 'pending' }),
        applicationApi.getApplications({ status: 'pending' }),
        timerApi.getUpcoming({ hours: 24 }),
      ]);

      if (cancelled) return;

      const built: Alert[] = [];

      // Timers (RED) - check first for priority ordering
      if (results[2].status === 'fulfilled') {
        const timers = results[2].value.timers;
        if (timers.length > 0) {
          built.push({
            message: `${timers.length} structure timer${timers.length !== 1 ? 's' : ''} expiring within 24 hours`,
            link: '/corp/timers',
            color: '#f85149',
          });
        }
      }

      // SRP pending (YELLOW)
      if (results[0].status === 'fulfilled') {
        const pending = results[0].value;
        if (pending.length > 0) {
          built.push({
            message: `${pending.length} SRP request${pending.length !== 1 ? 's' : ''} pending review`,
            link: '/corp/srp',
            color: '#d29922',
          });
        }
      }

      // HR applications (YELLOW)
      if (results[1].status === 'fulfilled') {
        const { applications, count } = results[1].value;
        const total = count || applications.length;
        if (total > 0) {
          built.push({
            message: `${total} recruitment application${total !== 1 ? 's' : ''} awaiting review`,
            link: '/corp/hr',
            color: '#d29922',
          });
        }
      }

      setAlerts(built);
      setLoading(false);
    }

    fetchAlerts();
    return () => { cancelled = true; };
  }, [corpId]);

  // Loading skeleton
  if (loading) {
    return (
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: spacing.base,
      }}>
        <div style={{
          height: '1.2rem',
          width: '60%',
          background: 'rgba(255,255,255,0.05)',
          borderRadius: '4px',
          animation: 'pulse 1.5s ease-in-out infinite',
        }} />
        <style>{`
          @keyframes pulse {
            0%, 100% { opacity: 0.4; }
            50% { opacity: 0.8; }
          }
        `}</style>
      </div>
    );
  }

  // No alerts
  if (alerts.length === 0) {
    return (
      <div style={{ color: color.textSecondary, fontSize: fontSize.xs }}>
        No action items
      </div>
    );
  }

  // Alerts present
  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      padding: spacing.base,
      display: 'flex',
      flexDirection: 'column',
      gap: spacing.xs,
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: spacing.xs,
        marginBottom: spacing.xs,
      }}>
        <span style={{ fontSize: fontSize.xs, color: color.textPrimary, fontWeight: 600 }}>
          Action Items
        </span>
        <span style={{
          fontSize: fontSize.tiny,
          color: color.textWhite,
          background: 'rgba(255,255,255,0.15)',
          borderRadius: '9999px',
          padding: '0.1rem 0.4rem',
          fontWeight: 600,
          lineHeight: 1.4,
        }}>
          {alerts.length}
        </span>
      </div>

      {/* Alert items */}
      {alerts.map((alert, i) => (
        <div
          key={i}
          style={{
            background: 'rgba(0,0,0,0.2)',
            borderLeft: `3px solid ${alert.color}`,
            borderRadius: '4px',
            padding: '0.5rem 0.75rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span style={{ fontSize: fontSize.xs, color: color.textPrimary }}>
            {alert.message}
          </span>
          <Link
            to={alert.link}
            style={{
              color: alert.color,
              fontSize: fontSize.tiny,
              cursor: 'pointer',
              textDecoration: 'none',
              whiteSpace: 'nowrap',
              marginLeft: spacing.base,
            }}
          >
            View &rarr;
          </Link>
        </div>
      ))}
    </div>
  );
}
