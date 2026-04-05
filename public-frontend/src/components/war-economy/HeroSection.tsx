import { RefreshIndicator } from '../RefreshIndicator';
import { formatISK } from '../../utils/format';
import type { WarEconomy } from '../../types/reports';

interface HeroSectionProps {
  report: WarEconomy;
  lastUpdated: Date;
}

export function HeroSection({ report, lastUpdated }: HeroSectionProps) {
  const killsPerHour = report.global_summary.total_kills_24h / 24;

  // Activity level based on kills/hour
  const activityLevel = killsPerHour >= 250 ? 'HOT' : killsPerHour >= 150 ? 'ACTIVE' : killsPerHour >= 80 ? 'MODERATE' : 'QUIET';
  const activityColor = activityLevel === 'HOT' ? '#ff4444' : activityLevel === 'ACTIVE' ? '#ff8800' : activityLevel === 'MODERATE' ? '#ffcc00' : '#00ff88';
  const activityPercent = Math.min((killsPerHour / 300) * 100, 100);

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
          background: `radial-gradient(circle at top right, ${activityColor}15 0%, transparent 70%)`,
          pointerEvents: 'none'
        }} />

        {/* Single Row Layout */}
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          {/* Logo + Title + Live */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <img
              src="/war-economy-logo.png"
              alt="War Economy"
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
              War Economy
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

          {/* Spacer */}
          <div style={{ flex: 1 }} />

          {/* Activity Level - Compact inline */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', padding: '0.3rem 0.6rem', background: 'rgba(0,0,0,0.3)', borderRadius: '4px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Activity</span>
            <span style={{ fontSize: '0.9rem', fontWeight: 800, color: activityColor }}>{activityLevel}</span>
            <div style={{ width: '46px', height: '5px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{ width: `${activityPercent}%`, height: '100%', background: activityColor }} />
            </div>
          </div>

          {/* Refresh */}
          <RefreshIndicator lastUpdated={lastUpdated} autoRefreshSeconds={120} />
        </div>

        {/* Quick Intel - Small footer line */}
        <div style={{
          display: 'flex',
          gap: '1.15rem',
          marginTop: '0.45rem',
          fontSize: '0.8rem',
          color: 'rgba(255,255,255,0.35)'
        }}>
          {report.global_summary.hottest_region && (
            <span>🔥 <span style={{ color: '#ff4444' }}>{report.global_summary.hottest_region.region_name}</span> ({report.global_summary.hottest_region.kills} kills)</span>
          )}
          <span>⚡ <span style={{ color: '#ffcc00' }}>{Math.round(killsPerHour)}</span> kills/hr</span>
          <span>💰 <span style={{ color: '#00ff88' }}>{formatISK(report.global_summary.total_opportunity_value)}</span> demand</span>
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

