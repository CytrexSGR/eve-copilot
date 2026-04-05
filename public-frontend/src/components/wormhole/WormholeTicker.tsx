import { useState, useMemo } from 'react';
import { WORMHOLE_TICKER_TAGS } from '../../constants/wormhole';
import type { WormholeThreat, WormholeEviction } from '../../types/wormhole';

interface TickerItem {
  id: string;
  icon: string;
  tag: string;
  tagColor: string;
  tagBg: string;
  primary: string;
  secondary?: string;
}

interface WormholeTickerProps {
  threats: WormholeThreat[];
  evictions: WormholeEviction[];
}

function formatTimeAgo(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function WormholeTicker({ threats, evictions }: WormholeTickerProps) {
  const [isPaused, setIsPaused] = useState(false);

  const items = useMemo(() => {
    const tickerItems: TickerItem[] = [];

    // Add threats
    (threats || []).slice(0, 10).forEach((threat, i) => {
      const tag = threat.type === 'CAPITAL' ? WORMHOLE_TICKER_TAGS.KILL : WORMHOLE_TICKER_TAGS.SPIKE;
      tickerItems.push({
        id: `threat-${i}`,
        icon: tag.icon,
        tag: tag.label,
        tagColor: tag.color,
        tagBg: `${tag.color}22`,
        primary: threat.description,
        secondary: formatTimeAgo(threat.timestamp),
      });
    });

    // Add evictions
    (evictions || []).slice(0, 5).forEach((eviction, i) => {
      const tag = WORMHOLE_TICKER_TAGS.EVICTION;
      tickerItems.push({
        id: `eviction-${i}`,
        icon: tag.icon,
        tag: tag.label,
        tagColor: tag.color,
        tagBg: `${tag.color}22`,
        primary: `${eviction.system_name} - ${eviction.total_kills} kills`,
        secondary: `${(eviction.total_isk_destroyed / 1e9).toFixed(1)}B ISK`,
      });
    });

    return tickerItems;
  }, [threats, evictions]);

  if (items.length === 0) return null;

  const duplicatedItems = [...items, ...items];
  const duration = items.length * 8;

  return (
    <div style={{ marginTop: '0.75rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '1rem' }}>📊</span>
        <h3 style={{ fontSize: '0.8rem', fontWeight: 600, color: 'rgba(255,255,255,0.7)', margin: 0 }}>
          J-SPACE INTEL
        </h3>
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: '#00ff88',
            boxShadow: '0 0 6px #00ff88',
            animation: 'pulse 2s infinite',
          }}
        />
      </div>

      {/* Ticker Bar */}
      <div
        style={{
          position: 'relative',
          overflow: 'hidden',
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '6px',
          padding: '0.5rem 0',
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
            background: 'linear-gradient(to right, rgba(10,15,26,1), transparent)',
            zIndex: 1,
          }}
        />
        <div
          style={{
            position: 'absolute',
            right: 0,
            top: 0,
            bottom: 0,
            width: '40px',
            background: 'linear-gradient(to left, rgba(10,15,26,1), transparent)',
            zIndex: 1,
          }}
        />

        {/* Scrolling content */}
        <div
          style={{
            display: 'flex',
            gap: '2rem',
            animation: isPaused ? 'none' : `wormholeTicker ${duration}s linear infinite`,
          }}
        >
          {duplicatedItems.map((item, i) => (
            <div
              key={`${item.id}-${i}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                whiteSpace: 'nowrap',
              }}
            >
              <span style={{ fontSize: '0.9rem' }}>{item.icon}</span>
              <span
                style={{
                  fontSize: '0.65rem',
                  fontWeight: 600,
                  color: item.tagColor,
                  background: item.tagBg,
                  padding: '0.15rem 0.4rem',
                  borderRadius: '3px',
                }}
              >
                {item.tag}
              </span>
              <span style={{ fontSize: '0.8rem', color: '#fff' }}>{item.primary}</span>
              {item.secondary && (
                <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)' }}>
                  {item.secondary}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* CSS for ticker animation */}
      <style>{`
        @keyframes wormholeTicker {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
      `}</style>
    </div>
  );
}
