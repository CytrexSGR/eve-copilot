import { RefreshIndicator } from '../RefreshIndicator';
import { ACTIVITY_LEVEL_COLORS } from '../../constants/wormhole';
import type { WormholeSummary } from '../../types/wormhole';

interface WormholeHeroProps {
  summary: WormholeSummary | null;
  lastUpdated: Date;
  loading?: boolean;
}

function formatISK(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  return value.toLocaleString();
}

function StatBox({ value, label, color }: { value: string | number; label: string; color: string }) {
  return (
    <div style={{ textAlign: 'center', minWidth: '70px' }}>
      <div style={{ fontSize: '1.1rem', fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase' }}>{label}</div>
    </div>
  );
}

export function WormholeHero({ summary, lastUpdated, loading }: WormholeHeroProps) {
  const activityColor = summary ? ACTIVITY_LEVEL_COLORS[summary.activity_level] : '#888888';

  return (
    <div
      style={{
        background: 'linear-gradient(135deg, #0a0f1a 0%, #1a1f2e 50%, #0d1520 100%)',
        borderRadius: '8px',
        padding: '0.75rem 1rem',
        position: 'relative',
        overflow: 'hidden',
        border: '1px solid rgba(100, 150, 255, 0.2)',
      }}
    >
      {/* Glowing corner accent */}
      <div
        style={{
          position: 'absolute',
          top: '-50%',
          right: '-10%',
          width: '200px',
          height: '200px',
          background: `radial-gradient(circle, ${activityColor}15, transparent 70%)`,
          pointerEvents: 'none',
        }}
      />

      {/* Single Row Layout */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', position: 'relative' }}>
        {/* Logo + Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <img src="/wormhole-intel-logo.png" alt="" style={{ width: '42px', height: '42px', objectFit: 'contain' }} />
          <div>
            <h1 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', margin: 0 }}>
              WORMHOLE INTEL
            </h1>
            <p style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', margin: 0 }}>
              J-Space Activity & Threat Intelligence
            </p>
          </div>
        </div>

        {/* Divider */}
        <div style={{ width: '1px', height: '35px', background: 'rgba(255,255,255,0.1)' }} />

        {/* Stats */}
        {loading || !summary ? (
          <div style={{ color: 'rgba(255,255,255,0.5)' }}>Loading...</div>
        ) : (
          <>
            <StatBox value={summary.active_systems_30d ?? 0} label="Active Systems" color="#00d4ff" />
            <StatBox value={(summary.known_residents ?? 0).toLocaleString()} label="Residents" color="#00ff88" />
            <StatBox value={summary.kills_24h ?? 0} label="Kills 24h" color="#ff4444" />
            <StatBox value={formatISK(summary.isk_destroyed_24h ?? 0)} label="ISK Destroyed" color="#ffcc00" />
            <StatBox value={summary.evictions_7d ?? 0} label="Evictions (7d)" color="#ff8800" />
          </>
        )}

        {/* Divider */}
        <div style={{ width: '1px', height: '35px', background: 'rgba(255,255,255,0.1)' }} />

        {/* Activity Level */}
        {summary && (
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                fontSize: '0.85rem',
                fontWeight: 700,
                color: activityColor,
                textShadow: `0 0 10px ${activityColor}40`,
              }}
            >
              {summary.activity_level ?? 'N/A'}
            </div>
            <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>ACTIVITY</div>
          </div>
        )}

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Live Badge + Refresh */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#ff4444',
                boxShadow: '0 0 8px #ff4444',
                animation: 'pulse 2s infinite',
              }}
            />
            <span style={{ fontSize: '0.7rem', fontWeight: 600, color: '#ff4444' }}>LIVE</span>
          </div>
          <RefreshIndicator lastUpdated={lastUpdated} autoRefreshSeconds={60} />
        </div>
      </div>

      {/* CSS for pulse animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
