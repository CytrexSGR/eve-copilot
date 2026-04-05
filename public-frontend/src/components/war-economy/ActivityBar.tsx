import { ACTIVITY_THRESHOLDS, ACTIVITY_COLORS } from '../../constants/warEconomy';
import { formatISK } from '../../utils/format';

interface ActivityBarProps {
  killsPerHour: number;
  iskPerHour: number;
  regionsActive: number;
  avgKillsPerRegion: number;
}

function getActivityLevel(killsPerHour: number) {
  if (killsPerHour >= ACTIVITY_THRESHOLDS.active) return { level: 'HOT', color: ACTIVITY_COLORS.hot };
  if (killsPerHour >= ACTIVITY_THRESHOLDS.moderate) return { level: 'ACTIVE', color: ACTIVITY_COLORS.active };
  if (killsPerHour >= ACTIVITY_THRESHOLDS.quiet) return { level: 'MODERATE', color: ACTIVITY_COLORS.moderate };
  return { level: 'QUIET', color: ACTIVITY_COLORS.quiet };
}

export function ActivityBar({ killsPerHour, iskPerHour, regionsActive, avgKillsPerRegion }: ActivityBarProps) {
  const { level, color } = getActivityLevel(killsPerHour);
  const activityPercent = Math.min((killsPerHour / ACTIVITY_THRESHOLDS.maxScale) * 100, 100);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      padding: '1rem 1.25rem',
      marginBottom: '1.5rem',
      border: '1px solid rgba(255,255,255,0.05)'
    }}>
      {/* Header with level badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Combat Intensity
          </span>
          <span style={{
            padding: '0.2rem 0.5rem',
            background: `${color}22`,
            border: `1px solid ${color}55`,
            borderRadius: '4px',
            fontSize: '0.7rem',
            fontWeight: 800,
            color: color,
            textTransform: 'uppercase',
            letterSpacing: '0.05em'
          }}>
            {level}
          </span>
        </div>
        <span style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.6)', fontFamily: 'monospace' }}>
          <span style={{ color: color, fontWeight: 700 }}>{Math.round(killsPerHour)}</span> kills/hr
        </span>
      </div>

      {/* Progress bar with threshold markers */}
      <div style={{ position: 'relative', marginBottom: '0.5rem' }}>
        <div style={{
          height: '8px',
          background: 'rgba(255,255,255,0.1)',
          borderRadius: '4px',
          overflow: 'hidden'
        }}>
          <div style={{
            width: `${activityPercent}%`,
            height: '100%',
            background: `linear-gradient(90deg, ${color}88, ${color})`,
            borderRadius: '4px',
            boxShadow: `0 0 20px ${color}66`,
            transition: 'width 0.5s ease'
          }} />
        </div>
        {/* Threshold markers */}
        <div style={{ position: 'absolute', top: 0, left: `${(ACTIVITY_THRESHOLDS.quiet / ACTIVITY_THRESHOLDS.maxScale) * 100}%`, width: '1px', height: '8px', background: ACTIVITY_COLORS.quiet, opacity: 0.5 }} />
        <div style={{ position: 'absolute', top: 0, left: `${(ACTIVITY_THRESHOLDS.moderate / ACTIVITY_THRESHOLDS.maxScale) * 100}%`, width: '1px', height: '8px', background: ACTIVITY_COLORS.moderate, opacity: 0.5 }} />
        <div style={{ position: 'absolute', top: 0, left: `${(ACTIVITY_THRESHOLDS.active / ACTIVITY_THRESHOLDS.maxScale) * 100}%`, width: '1px', height: '8px', background: ACTIVITY_COLORS.hot, opacity: 0.5 }} />
      </div>

      {/* Scale labels with thresholds */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', marginBottom: '0.75rem' }}>
        <span style={{ color: ACTIVITY_COLORS.quiet }}>Quiet &lt;80</span>
        <span style={{ color: ACTIVITY_COLORS.moderate }}>Moderate 80-150</span>
        <span style={{ color: ACTIVITY_COLORS.active }}>Active 150-250</span>
        <span style={{ color: ACTIVITY_COLORS.hot }}>Hot 250+</span>
      </div>

      {/* Breakdown metrics */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '0.75rem',
        padding: '0.75rem',
        background: 'rgba(0,0,0,0.2)',
        borderRadius: '6px',
        fontSize: '0.75rem'
      }}>
        <div>
          <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem', textTransform: 'uppercase', marginBottom: '0.25rem' }}>ISK/Hour</div>
          <div style={{ color: '#ffcc00', fontFamily: 'monospace', fontWeight: 600 }}>{formatISK(iskPerHour)}</div>
        </div>
        <div>
          <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Active Regions</div>
          <div style={{ color: '#00d4ff', fontFamily: 'monospace', fontWeight: 600 }}>{regionsActive}</div>
        </div>
        <div>
          <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Avg Kills/Region</div>
          <div style={{ color: '#a855f7', fontFamily: 'monospace', fontWeight: 600 }}>{avgKillsPerRegion}</div>
        </div>
      </div>
    </div>
  );
}
