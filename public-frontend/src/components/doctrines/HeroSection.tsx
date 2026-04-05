import { memo } from 'react';
import { TimeFilter } from '../warfare/TimeFilter';

interface HeroSectionProps {
  stats: {
    activeDoctrines: number;
    fleetsDetected: number;
    alliancesTracked: number;
    hotRegions: number;
    dominantDoctrine: string;
  };
  timeFilter: number;
  onTimeFilterChange: (minutes: number) => void;
  quickIntel?: {
    hottestRegion: string;
    peakHour: number;
    avgFleetSize: number;
  };
}

export const HeroSection = memo(function HeroSection({
  stats,
  timeFilter,
  onTimeFilterChange,
  quickIntel
}: HeroSectionProps) {
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
          background: 'radial-gradient(circle at top right, rgba(88,166,255,0.15) 0%, transparent 70%)',
          pointerEvents: 'none'
        }} />

        {/* Single Row Layout */}
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          {/* Logo + Title + Live */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <img
              src="/doctrine-intel-logo.png"
              alt="Doctrine Intel"
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
              Doctrine Intel
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
              <span style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: '#00ff88',
                animation: 'pulse 2s infinite'
              }} />
              Live
            </span>
          </div>

          {/* Divider */}
          <div style={{ width: '1px', height: '32px', background: 'rgba(255,255,255,0.1)' }} />

          {/* Stats - Compact inline */}
          <div style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
            <StatBox value={stats.activeDoctrines.toString()} label="Doctrines" color="#ff4444" />
            <StatBox value={stats.fleetsDetected.toString()} label="Fleets" color="#ffcc00" />
            <StatBox value={stats.alliancesTracked.toString()} label="Alliances" color="#a855f7" />
            <StatBox value={stats.hotRegions.toString()} label="Hot Regions" color="#ff8800" />
            <StatBox value={stats.dominantDoctrine} label="Dominant" color="#00ff88" isText />
          </div>

          {/* Time Filter */}
          <TimeFilter value={timeFilter} onChange={onTimeFilterChange} />
        </div>

        {/* Quick Intel footer */}
        {quickIntel && (
          <div style={{
            display: 'flex',
            gap: '1.15rem',
            marginTop: '0.45rem',
            fontSize: '0.8rem',
            color: 'rgba(255,255,255,0.35)'
          }}>
            <span>
              🔥 Hottest: <span style={{ color: '#ff4444' }}>{quickIntel.hottestRegion}</span>
            </span>
            <span>
              ⏰ Peak: <span style={{ color: '#ffcc00' }}>{quickIntel.peakHour}:00</span>
            </span>
            <span>
              👥 Avg Fleet: <span style={{ color: '#00ff88' }}>{quickIntel.avgFleetSize}</span>
            </span>
          </div>
        )}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.2); }
        }
      `}</style>
    </>
  );
});

function StatBox({ value, label, color, isText = false }: {
  value: string;
  label: string;
  color: string;
  isText?: boolean;
}) {
  return (
    <div style={{ padding: '0 0.7rem', borderRight: '1px solid rgba(255,255,255,0.06)' }}>
      <span style={{
        fontSize: isText ? '1rem' : '1.25rem',
        fontWeight: 800,
        color,
        fontFamily: isText ? 'inherit' : 'monospace'
      }}>
        {value}
      </span>
      <span style={{
        fontSize: '0.7rem',
        color: 'rgba(255,255,255,0.35)',
        textTransform: 'uppercase',
        marginLeft: '5px'
      }}>
        {label}
      </span>
    </div>
  );
}
