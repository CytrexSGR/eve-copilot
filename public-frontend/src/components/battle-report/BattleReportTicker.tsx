import { useState, useEffect } from 'react';
import { battleApi, type BattleEvent } from '../../services/api';

interface TickerItem {
  id: string;
  icon: string;
  label: string;
  labelColor: string;
  labelBg: string;
  primary: string;
  secondary?: string;
  value?: string;
  valueColor?: string;
  extra?: string;
}

const EVENT_ICONS: Record<string, string> = {
  titan_killed: '👑',
  supercarrier_killed: '🛸',
  capital_killed: '💥',
  dread_killed: '💥',
  carrier_killed: '🚀',
  fax_killed: '🏥',
  hot_zone_shift: '🔥',
  isk_spike: '💰',
  war_escalation: '⚔️',
  new_conflict: '⚔️',
  alliance_engagement: '🛡️',
  efficiency_change: '📊',
  regional_activity: '📍',
  last_titan: '👑',
  last_supercarrier: '🛸',
};

const SEVERITY_COLORS: Record<string, { color: string; bg: string }> = {
  critical: { color: '#ff4444', bg: 'rgba(255, 68, 68, 0.2)' },
  high: { color: '#ff8800', bg: 'rgba(255, 136, 0, 0.2)' },
  medium: { color: '#ffcc00', bg: 'rgba(255, 204, 0, 0.2)' },
  low: { color: '#00d4ff', bg: 'rgba(0, 212, 255, 0.2)' },
};

function eventToTickerItem(event: BattleEvent): TickerItem {
  const severityStyle = SEVERITY_COLORS[event.severity] || SEVERITY_COLORS.medium;
  const icon = EVENT_ICONS[event.event_type] || '📢';

  // Format label based on event type
  let label = event.severity.toUpperCase();
  if (event.event_type.includes('killed')) {
    label = event.event_type.replace('_killed', '').toUpperCase();
  } else if (event.event_type === 'hot_zone_shift') {
    label = 'HOT ZONE';
  } else if (event.event_type === 'isk_spike') {
    label = 'BIG KILL';
  } else if (event.event_type === 'last_titan') {
    label = 'TITAN';
  } else if (event.event_type === 'last_supercarrier') {
    label = 'SUPER';
  }

  return {
    id: `event-${event.id}`,
    icon,
    label,
    labelColor: severityStyle.color,
    labelBg: severityStyle.bg,
    primary: event.title,
    secondary: event.system_name ? `(${event.system_name})` : undefined,
    value: event.description || undefined,
    valueColor: 'var(--text-secondary)',
    extra: event.region_name || undefined,
  };
}

interface SupercapInfo {
  title: string;
  description: string;
  system_name: string;
  region_name: string;
}

export function BattleReportTicker() {
  const [events, setEvents] = useState<BattleEvent[]>([]);
  const [supercaps, setSupercaps] = useState<Record<string, SupercapInfo>>({});
  const [isPaused, setIsPaused] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [eventsData, supercapsData] = await Promise.all([
          battleApi.getBattleEvents(30),
          battleApi.getLastSupercaps(),
        ]);
        setEvents(eventsData.events || []);
        setSupercaps(supercapsData || {});
      } catch (err) {
        console.error('Failed to fetch battle events:', err);
        setEvents([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ height: '36px', background: 'var(--bg-elevated)', borderRadius: '4px' }} />
      </div>
    );
  }

  // Convert events to ticker items
  const eventItems = events.map(eventToTickerItem);

  // Add supercap info items
  const supercapItems: TickerItem[] = [];
  if (supercaps.last_titan) {
    supercapItems.push({
      id: 'last-titan',
      icon: '👑',
      label: 'TITAN',
      labelColor: '#ffcc00',
      labelBg: 'rgba(255, 204, 0, 0.2)',
      primary: supercaps.last_titan.title,
      secondary: supercaps.last_titan.system_name ? `(${supercaps.last_titan.system_name})` : undefined,
      value: supercaps.last_titan.description,
      valueColor: 'var(--text-secondary)',
      extra: supercaps.last_titan.region_name,
    });
  }
  if (supercaps.last_supercarrier) {
    supercapItems.push({
      id: 'last-super',
      icon: '🛸',
      label: 'SUPER',
      labelColor: '#a855f7',
      labelBg: 'rgba(168, 85, 247, 0.2)',
      primary: supercaps.last_supercarrier.title,
      secondary: supercaps.last_supercarrier.system_name ? `(${supercaps.last_supercarrier.system_name})` : undefined,
      value: supercaps.last_supercarrier.description,
      valueColor: 'var(--text-secondary)',
      extra: supercaps.last_supercarrier.region_name,
    });
  }

  // Combine: events first, then supercap info
  const items = [...eventItems, ...supercapItems];

  if (items.length === 0) {
    return (
      <div style={{ marginBottom: '1rem' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            marginBottom: '0.5rem',
          }}
        >
          <span style={{ fontSize: '1rem' }}>📊</span>
          <h3
            style={{
              margin: 0,
              fontSize: '0.8rem',
              fontWeight: 700,
              color: 'var(--text-secondary)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            Battle Intel
          </h3>
        </div>
        <div
          style={{
            height: '36px',
            background: 'var(--bg-elevated)',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            padding: '0 1rem',
            color: 'var(--text-tertiary)',
            fontSize: '0.75rem',
          }}
        >
          📭 No recent events
        </div>
      </div>
    );
  }

  // Duplicate for seamless loop
  const duplicatedItems = [...items, ...items];

  return (
    <div style={{ marginBottom: '1rem' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          marginBottom: '0.5rem',
        }}
      >
        <span style={{ fontSize: '1rem' }}>📊</span>
        <h3
          style={{
            margin: 0,
            fontSize: '0.8rem',
            fontWeight: 700,
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          Battle Intel
        </h3>
        <span
          style={{
            fontSize: '0.65rem',
            color: 'var(--text-tertiary)',
          }}
        >
          Live Events | Capitals | Hot Zones
        </span>
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: '#00ff88',
            animation: 'pulse 2s infinite',
          }}
        />
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
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: '40px',
            background: 'linear-gradient(to right, var(--bg-elevated), transparent)',
            zIndex: 2,
            pointerEvents: 'none',
          }}
        />
        <div
          style={{
            position: 'absolute',
            right: 0,
            top: 0,
            bottom: 0,
            width: '40px',
            background: 'linear-gradient(to left, var(--bg-elevated), transparent)',
            zIndex: 2,
            pointerEvents: 'none',
          }}
        />

        {/* Ticker content */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            height: '100%',
            animation: isPaused ? 'none' : `battleTicker ${Math.max(items.length * 4, 10)}s linear infinite`,
            whiteSpace: 'nowrap',
          }}
        >
          {duplicatedItems.map((item, index) => (
            <div
              key={`${item.id}-${index}`}
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
              <span style={{ fontSize: '0.9rem' }}>{item.icon}</span>

              {/* Label */}
              <span
                style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  padding: '0.15rem 0.3rem',
                  borderRadius: '3px',
                  background: item.labelBg,
                  color: item.labelColor,
                }}
              >
                {item.label}
              </span>

              {/* Primary */}
              <span
                style={{
                  fontWeight: 600,
                  fontSize: '0.8rem',
                  color: 'var(--text-primary)',
                }}
              >
                {item.primary}
              </span>

              {/* Secondary (e.g., system name) */}
              {item.secondary && (
                <span
                  style={{
                    fontSize: '0.7rem',
                    color: 'var(--text-tertiary)',
                  }}
                >
                  {item.secondary}
                </span>
              )}

              {/* Value */}
              {item.value && (
                <span
                  style={{
                    fontSize: '0.75rem',
                    color: item.valueColor || 'var(--text-secondary)',
                    fontFamily: 'monospace',
                  }}
                >
                  {item.value}
                </span>
              )}

              {/* Extra info */}
              {item.extra && (
                <span
                  style={{
                    fontSize: '0.65rem',
                    color: 'var(--text-tertiary)',
                  }}
                >
                  {item.extra}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* CSS Animation */}
        <style>{`
          @keyframes battleTicker {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
          }
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }
        `}</style>
      </div>
    </div>
  );
}
