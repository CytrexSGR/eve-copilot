/**
 * PowerBloc HuntingCard - Compact Summary Card
 * Uses offensive data passed from parent
 */

import { MiniChart } from '../../alliance/overview/MiniChart';

interface HuntingCardProps {
  data: any;
  days: number;
}

export function HuntingCard({ data, days }: HuntingCardProps) {
  if (!data) return null;

  const { summary, kill_timeline, hunting_regions } = data;
  const regions = hunting_regions || data.hunting_grounds || [];

  const avgKillsPerDay = (summary?.total_kills || 0) / Math.max(days, 1);
  const threatLevel = avgKillsPerDay > 100 ? 'HIGH' : avgKillsPerDay > 50 ? 'MED' : 'LOW';
  const threatColor = threatLevel === 'HIGH' ? '#ff4444' : threatLevel === 'MED' ? '#ffcc00' : '#3fb950';

  const activeDays = (kill_timeline || []).filter((d: any) => (d.kills || 0) > 0).length;
  const opTempo = (summary?.total_kills || 0) / Math.max(activeDays, 1);

  const timeline = (kill_timeline || []).slice(-30);
  const timelineData = timeline.map((d: any) => d.kills || 0);

  const topRegion = regions.length > 0 ? regions[0] : null;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #ff8800',
      padding: '0.5rem',
      height: '180px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#ff8800', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          • HUNTING
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.4rem' }}>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>THREAT LEVEL</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: threatColor, fontFamily: 'monospace' }}>
            {threatLevel}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>OP TEMPO</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ff8800', fontFamily: 'monospace' }}>
            {opTempo.toFixed(0)}
          </div>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', alignItems: 'center', padding: '0 0.5rem' }}>
        <MiniChart data={timelineData} height={60} color="#ff8800" />
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.3rem' }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Most Hunted: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{topRegion?.region_name || 'N/A'}</span>
        </div>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Active: </span>
          <span style={{ color: '#ff8800', fontWeight: 600 }}>{activeDays}d</span>
        </div>
      </div>
    </div>
  );
}
