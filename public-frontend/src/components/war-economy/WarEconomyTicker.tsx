import { useState } from 'react';
import type { WarEconomy } from '../../types/economy';
import type { WarRoomAlert } from '../../hooks/useWarRoomAlerts';
import { formatISK } from '../../utils/format';

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
}

interface WarEconomyTickerProps {
  report: WarEconomy;
  alerts?: WarRoomAlert[];
}

export function WarEconomyTicker({ report, alerts = [] }: WarEconomyTickerProps) {
  const [isPaused, setIsPaused] = useState(false);

  // Build ticker items from report data
  const items: TickerItem[] = [];

  // Add market alerts first (from WarRoomAlerts)
  alerts.forEach((alert, idx) => {
    const desc = alert.detail || alert.message || '';
    const isPrice = alert.type === 'manipulation' || desc.includes('price');
    const isVolume = desc.includes('volume');

    items.push({
      id: `alert-${idx}`,
      icon: alert.icon || (isPrice ? '📈' : isVolume ? '📊' : '⚠️'),
      label: isPrice ? 'PRICE' : isVolume ? 'VOLUME' : alert.type.toUpperCase(),
      labelColor: alert.priority === 'critical' ? '#ff4444' : alert.priority === 'high' ? '#ff8800' : '#ffcc00',
      labelBg: alert.priority === 'critical' ? 'rgba(255, 68, 68, 0.2)' : alert.priority === 'high' ? 'rgba(255, 136, 0, 0.2)' : 'rgba(255, 204, 0, 0.2)',
      primary: alert.message,
      secondary: alert.detail,
      value: '',
      valueColor: 'rgba(255,255,255,0.5)',
    });
  });

  // Add hottest region
  if (report.global_summary.hottest_region) {
    items.push({
      id: 'hottest-region',
      icon: '🔥',
      label: 'HOT ZONE',
      labelColor: '#ff4444',
      labelBg: 'rgba(255, 68, 68, 0.2)',
      primary: report.global_summary.hottest_region.region_name,
      value: `${report.global_summary.hottest_region.kills} kills`,
      valueColor: '#ff4444',
    });
  }

  // Add top opportunity regions from regional_demand
  report.regional_demand?.slice(0, 3).forEach((region) => {
    if (region.demand_score > 50) {
      items.push({
        id: `opportunity-${region.region_id}`,
        icon: '💰',
        label: 'OPPORTUNITY',
        labelColor: '#00ff88',
        labelBg: 'rgba(0, 255, 136, 0.2)',
        primary: region.region_name,
        value: `Score: ${region.demand_score.toFixed(0)}`,
        valueColor: '#00ff88',
      });
    }
  });

  // Add active fleet compositions
  report.fleet_compositions?.slice(0, 4).forEach((fc, idx) => {
    const mainDoctrine = fc.doctrine_hints?.[0];
    if (mainDoctrine) {
      items.push({
        id: `fleet-${idx}`,
        icon: '🚀',
        label: 'FLEET',
        labelColor: '#a855f7',
        labelBg: 'rgba(168, 85, 247, 0.2)',
        primary: mainDoctrine,
        secondary: fc.region_name,
        value: `${fc.total_ships_lost} ships`,
        valueColor: 'rgba(255,255,255,0.5)',
      });
    }
  });

  // Add hot items (high demand)
  report.hot_items?.slice(0, 3).forEach((item) => {
    items.push({
      id: `demand-${item.item_type_id}`,
      icon: '📦',
      label: 'DEMAND',
      labelColor: '#ffcc00',
      labelBg: 'rgba(255, 204, 0, 0.2)',
      primary: item.item_name,
      value: formatISK(item.market_price * item.quantity_destroyed),
      valueColor: '#ffcc00',
    });
  });

  // Global stats
  items.push({
    id: 'total-kills',
    icon: '💥',
    label: '24H',
    labelColor: '#ff4444',
    labelBg: 'rgba(255, 68, 68, 0.2)',
    primary: `${report.global_summary.total_kills_24h.toLocaleString()} Kills`,
    value: formatISK(report.global_summary.total_isk_destroyed),
    valueColor: '#ffcc00',
  });

  items.push({
    id: 'regions-active',
    icon: '🌐',
    label: 'ACTIVE',
    labelColor: '#00d4ff',
    labelBg: 'rgba(0, 212, 255, 0.2)',
    primary: `${report.global_summary.total_regions_active} Regions`,
    value: `${Math.round(report.global_summary.total_kills_24h / 24)}/hr`,
    valueColor: 'rgba(255,255,255,0.5)',
  });

  if (items.length === 0) {
    return (
      <div style={{ marginBottom: '1rem' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          marginBottom: '0.5rem',
        }}>
          <span style={{ fontSize: '1rem' }}>📊</span>
          <h3 style={{
            margin: 0,
            fontSize: '0.8rem',
            fontWeight: 700,
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}>
            Market Intel
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
          📭 No recent activity
        </div>
      </div>
    );
  }

  // Duplicate for seamless loop
  const duplicatedItems = [...items, ...items];

  return (
    <div style={{ marginBottom: '1rem' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        marginBottom: '0.5rem',
      }}>
        <span style={{ fontSize: '1rem' }}>📊</span>
        <h3 style={{
          margin: 0,
          fontSize: '0.8rem',
          fontWeight: 700,
          color: 'var(--text-secondary)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}>
          Market Intel
        </h3>
        <span style={{
          fontSize: '0.65rem',
          color: 'var(--text-tertiary)',
        }}>
          Price Alerts | Demand | Shortages | Fleets
        </span>
        <span style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          background: '#00ff88',
          animation: 'pulse 2s infinite',
        }} />
      </div>

      {/* Ticker Bar */}
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
          animation: isPaused ? 'none' : `marketTicker ${Math.max(items.length * 4, 10)}s linear infinite`,
          whiteSpace: 'nowrap',
        }}>
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
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '0.15rem 0.3rem',
                borderRadius: '3px',
                background: item.labelBg,
                color: item.labelColor,
              }}>
                {item.label}
              </span>

              {/* Primary */}
              <span style={{
                fontWeight: 600,
                fontSize: '0.8rem',
                color: 'var(--text-primary)',
              }}>
                {item.primary}
              </span>

              {/* Secondary */}
              {item.secondary && (
                <span style={{
                  fontSize: '0.7rem',
                  color: 'var(--text-tertiary)',
                }}>
                  ({item.secondary})
                </span>
              )}

              {/* Value */}
              {item.value && (
                <span style={{
                  fontSize: '0.75rem',
                  color: item.valueColor || 'var(--text-secondary)',
                  fontFamily: 'monospace',
                }}>
                  {item.value}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* CSS Animation */}
        <style>{`
          @keyframes marketTicker {
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
