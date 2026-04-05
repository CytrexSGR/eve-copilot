import { RefreshIndicator } from '../RefreshIndicator';
import { formatISK } from '../../utils/format';
import type { AllianceWars } from '../../types/reports';
import type { StatusCounts } from './StatusFilterBar';

interface HeroSectionProps {
  lastUpdated: Date;
  autoRefreshSeconds: number;
  mapIskDestroyed?: number;
  allianceWars?: AllianceWars | null;
  statusCounts?: StatusCounts;
}

export function HeroSection({
  lastUpdated,
  autoRefreshSeconds,
  mapIskDestroyed = 0,
  allianceWars,
  statusCounts
}: HeroSectionProps) {
  // Calculate total battles from status counts
  const totalBattles = statusCounts
    ? statusCounts.gank + statusCounts.brawl + statusCounts.battle + statusCounts.hellcamp
    : 0;

  // Calculate threat level based on activity
  const threatLevel = totalBattles > 100 ? 'CRITICAL' : totalBattles > 50 ? 'HIGH' : totalBattles > 20 ? 'ELEVATED' : 'MODERATE';
  const threatColor = threatLevel === 'CRITICAL' ? '#ff4444' : threatLevel === 'HIGH' ? '#ff8800' : threatLevel === 'ELEVATED' ? '#ffcc00' : '#00ff88';
  const threatPercent = Math.min((totalBattles / 150) * 100, 100);

  return (
    <>
      <div style={{
        position: 'relative',
        background: 'linear-gradient(135deg, #0a0f1a 0%, #1a1f2e 50%, #0d1520 100%)',
        borderRadius: '8px',
        padding: '0.75rem 1rem',
        marginBottom: '0.75rem',
        border: '1px solid rgba(100, 150, 255, 0.2)',
        overflow: 'hidden'
      }}>
        {/* Glowing corner accent */}
        <div style={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: '200px',
          height: '200px',
          background: `radial-gradient(circle at top right, ${threatColor}15 0%, transparent 70%)`,
          pointerEvents: 'none'
        }} />

        {/* Single Row Layout */}
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          {/* Logo + Title + Live */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <img
              src="/combat-intel-logo.png"
              alt="Combat Intelligence"
              style={{ height: '42px', width: 'auto', objectFit: 'contain' }}
            />
            <h1 style={{
              margin: 0,
              fontSize: '1.5rem',
              fontWeight: 800,
              background: 'linear-gradient(135deg, #fff 0%, #a0c4ff 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              letterSpacing: '0.03em',
              textTransform: 'uppercase',
              whiteSpace: 'nowrap'
            }}>
              Combat Intel
            </h1>
            <span style={{
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
              padding: '2px 6px',
              background: 'rgba(0, 255, 136, 0.15)',
              border: '1px solid rgba(0, 255, 136, 0.3)',
              borderRadius: '999px',
              fontSize: '0.75rem',
              fontWeight: 700,
              color: '#00ff88',
              textTransform: 'uppercase'
            }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#00ff88', animation: 'pulse 2s infinite' }} />
              Live
            </span>
          </div>

          {/* Divider */}
          <div style={{ width: '1px', height: '32px', background: 'rgba(255,255,255,0.1)' }} />

          {/* Stats - Compact inline */}
          <div style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
            <StatBox value={String(totalBattles)} label="Battles" color="#ff4444" />
            <StatBox value={formatISK(mapIskDestroyed).replace(' ISK', '')} label="ISK" color="#ffcc00" />
            <StatBox value={String(allianceWars?.global.active_conflicts || 0)} label="Wars" color="#ff8800" />
            <StatBox value={String(allianceWars?.coalitions?.length || 0)} label="Blocs" color="#a855f7" />
            {statusCounts && (
              <StatBox value={String(statusCounts.hellcamp)} label="Hellcamps" color="#00ff88" />
            )}
          </div>

          {/* Threat Level - Compact inline */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', padding: '0.3rem 0.6rem', background: 'rgba(0,0,0,0.3)', borderRadius: '4px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Threat</span>
            <span style={{ fontSize: '0.9rem', fontWeight: 800, color: threatColor }}>{threatLevel}</span>
            <div style={{ width: '46px', height: '5px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{ width: `${threatPercent}%`, height: '100%', background: threatColor }} />
            </div>
          </div>

          {/* Refresh */}
          <RefreshIndicator lastUpdated={lastUpdated} autoRefreshSeconds={autoRefreshSeconds} />
        </div>
      </div>

      {/* CSS Animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.2); }
        }
      `}</style>
    </>
  );
}

function StatBox({ value, label, color }: { value: string; label: string; color: string }) {
  return (
    <div style={{ padding: '0 0.7rem', borderRight: '1px solid rgba(255,255,255,0.06)' }}>
      <span style={{ fontSize: '1.25rem', fontWeight: 800, color, fontFamily: 'monospace' }}>{value}</span>
      <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginLeft: '5px' }}>{label}</span>
    </div>
  );
}
