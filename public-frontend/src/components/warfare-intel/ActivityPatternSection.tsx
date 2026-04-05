// src/components/warfare-intel/ActivityPatternSection.tsx
import type { FastHourlyActivity } from '../../types/intelligence';

interface ActivityPatternSectionProps {
  activity: FastHourlyActivity | null;
  loading?: boolean;
}

function getTimezoneBreakdown(killsByHour: number[]): { eutz: number; ustz: number; autz: number } {
  const total = killsByHour.reduce((a, b) => a + b, 0);
  if (total === 0) return { eutz: 33, ustz: 33, autz: 34 };

  // EUTZ: 16:00-00:00 EVE (hours 16-23)
  const eutzKills = killsByHour.slice(16, 24).reduce((a, b) => a + b, 0);
  // USTZ: 00:00-08:00 EVE (hours 0-7)
  const ustzKills = killsByHour.slice(0, 8).reduce((a, b) => a + b, 0);
  // AUTZ: 08:00-16:00 EVE (hours 8-15)
  const autzKills = killsByHour.slice(8, 16).reduce((a, b) => a + b, 0);

  return {
    eutz: Math.round((eutzKills / total) * 100),
    ustz: Math.round((ustzKills / total) * 100),
    autz: Math.round((autzKills / total) * 100)
  };
}

export function ActivityPatternSection({ activity, loading }: ActivityPatternSectionProps) {
  const sectionStyle = {
    background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
    borderRadius: '12px',
    border: '1px solid rgba(100, 150, 255, 0.1)',
    padding: '1.5rem',
    marginBottom: '1.5rem'
  };

  if (loading || !activity) {
    return (
      <div style={sectionStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <span style={{ fontSize: '1.25rem' }}>🕐</span>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#00d4ff' }}>
            Activity Pattern
          </h3>
        </div>
        <div style={{ color: 'rgba(255,255,255,0.4)', padding: '2rem', textAlign: 'center' }}>
          Loading activity pattern...
        </div>
      </div>
    );
  }

  const maxKills = Math.max(...activity.kills_by_hour, 1);
  const timezone = getTimezoneBreakdown(activity.kills_by_hour);
  const dominantTz = timezone.eutz >= timezone.ustz && timezone.eutz >= timezone.autz ? 'EUTZ'
    : timezone.ustz >= timezone.autz ? 'USTZ' : 'AUTZ';
  const dominantPct = Math.max(timezone.eutz, timezone.ustz, timezone.autz);

  return (
    <div style={sectionStyle}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '1.25rem' }}>🕐</span>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#00d4ff' }}>
            Activity Pattern
          </h3>
        </div>
        <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)' }}>
          Last 24h (EVE Time)
        </span>
      </div>

      {/* Heatmap */}
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', gap: '2px', marginBottom: '0.5rem' }}>
          {activity.kills_by_hour.map((kills, hour) => {
            const intensity = kills / maxKills;
            const bg = intensity > 0.7 ? '#00d4ff' : intensity > 0.3 ? 'rgba(0, 212, 255, 0.5)' : 'rgba(255,255,255,0.1)';
            return (
              <div
                key={hour}
                style={{
                  flex: 1,
                  height: '24px',
                  background: bg,
                  borderRadius: '2px',
                  position: 'relative'
                }}
                title={`${hour}:00 - ${kills} kills`}
              />
            );
          })}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)' }}>
          <span>00</span>
          <span>04</span>
          <span>08</span>
          <span>12</span>
          <span>16</span>
          <span>20</span>
          <span>EVE</span>
        </div>
      </div>

      {/* Peak Times & Timezone */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        padding: '0.75rem 1rem',
        background: 'rgba(0,0,0,0.2)',
        borderRadius: '8px',
        fontSize: '0.85rem'
      }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.5)' }}>Peak: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>
            {String(activity.peak_danger_start).padStart(2, '0')}:00 - {String(activity.peak_danger_end).padStart(2, '0')}:00 EVE
          </span>
        </div>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.5)' }}>Timezone: </span>
          <span style={{ color: '#00d4ff', fontWeight: 600 }}>
            {dominantTz} dominant ({dominantPct}%)
          </span>
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.75rem', fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          <span style={{ width: '12px', height: '8px', background: '#00d4ff', borderRadius: '2px' }} />
          High
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          <span style={{ width: '12px', height: '8px', background: 'rgba(0, 212, 255, 0.5)', borderRadius: '2px' }} />
          Medium
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          <span style={{ width: '12px', height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px' }} />
          Low
        </div>
      </div>
    </div>
  );
}
