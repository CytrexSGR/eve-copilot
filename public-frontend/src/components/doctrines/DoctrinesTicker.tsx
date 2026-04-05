import { memo, useState } from 'react';

interface DoctrineAlert {
  id: string;
  type: 'detection' | 'counter' | 'trend';
  message: string;
  timestamp: Date;
}

interface DoctrinesTickerProps {
  alerts: DoctrineAlert[];
}

const TYPE_CONFIG: Record<DoctrineAlert['type'], { icon: string; label: string; color: string; bg: string }> = {
  detection: { icon: '🎯', label: 'DETECTED', color: '#ff4444', bg: 'rgba(255, 68, 68, 0.2)' },
  counter: { icon: '⚔️', label: 'COUNTER', color: '#00d4ff', bg: 'rgba(0, 212, 255, 0.2)' },
  trend: { icon: '📈', label: 'TREND', color: '#ffcc00', bg: 'rgba(255, 204, 0, 0.2)' },
};

export const DoctrinesTicker = memo(function DoctrinesTicker({ alerts }: DoctrinesTickerProps) {
  const [isPaused, setIsPaused] = useState(false);

  if (alerts.length === 0) {
    return (
      <div style={{ marginBottom: '1rem' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          marginBottom: '0.5rem',
        }}>
          <span style={{ fontSize: '1rem' }}>🛡️</span>
          <h3 style={{
            margin: 0,
            fontSize: '0.8rem',
            fontWeight: 700,
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}>
            Doctrine Intel
          </h3>
        </div>
        <div style={{
          height: '36px',
          background: 'var(--bg-elevated)',
          borderRadius: '4px',
          display: 'flex',
          alignItems: 'center',
          padding: '0 1rem',
          color: 'var(--text-tertiary)',
          fontSize: '0.75rem',
        }}>
          📭 No recent alerts
        </div>
      </div>
    );
  }

  // Duplicate for seamless loop
  const duplicatedAlerts = [...alerts, ...alerts];

  return (
    <div style={{ marginBottom: '1rem' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        marginBottom: '0.5rem',
      }}>
        <span style={{ fontSize: '1rem' }}>🛡️</span>
        <h3 style={{
          margin: 0,
          fontSize: '0.8rem',
          fontWeight: 700,
          color: 'var(--text-secondary)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}>
          Doctrine Intel
        </h3>
        <span style={{
          fontSize: '0.65rem',
          color: 'var(--text-tertiary)',
        }}>
          Detections | Counters | Trends
        </span>
        <span style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          background: '#00ff88',
          animation: 'doctrinePulse 2s infinite',
        }} />
      </div>

      <div
        style={{
          position: 'relative',
          overflow: 'hidden',
          background: 'var(--bg-elevated)',
          borderRadius: '4px',
          height: '36px',
        }}
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
      >
        {/* Gradient overlays */}
        <div style={{
          position: 'absolute',
          left: 0,
          top: 0,
          bottom: 0,
          width: '40px',
          background: 'linear-gradient(to right, var(--bg-elevated), transparent)',
          zIndex: 2,
          pointerEvents: 'none',
        }} />
        <div style={{
          position: 'absolute',
          right: 0,
          top: 0,
          bottom: 0,
          width: '40px',
          background: 'linear-gradient(to left, var(--bg-elevated), transparent)',
          zIndex: 2,
          pointerEvents: 'none',
        }} />

        {/* Ticker content */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          height: '100%',
          animation: isPaused ? 'none' : `doctrineTicker ${Math.max(alerts.length * 5, 15)}s linear infinite`,
          whiteSpace: 'nowrap',
        }}>
          {duplicatedAlerts.map((alert, index) => {
            const config = TYPE_CONFIG[alert.type];
            return (
              <div
                key={`${alert.id}-${index}`}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0 1.5rem',
                  borderRight: '1px solid var(--border-color)',
                  height: '100%',
                  transition: 'background 0.2s',
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.background = 'var(--bg-primary)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.background = 'transparent';
                }}
              >
                {/* Icon */}
                <span style={{ fontSize: '0.9rem' }}>{config.icon}</span>

                {/* Label */}
                <span style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  padding: '0.15rem 0.3rem',
                  borderRadius: '3px',
                  background: config.bg,
                  color: config.color,
                }}>
                  {config.label}
                </span>

                {/* Message */}
                <span style={{
                  fontWeight: 600,
                  fontSize: '0.8rem',
                  color: 'var(--text-primary)',
                }}>
                  {alert.message}
                </span>
              </div>
            );
          })}
        </div>

        {/* CSS Animation */}
        <style>{`
          @keyframes doctrineTicker {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
          }
          @keyframes doctrinePulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }
        `}</style>
      </div>
    </div>
  );
});
