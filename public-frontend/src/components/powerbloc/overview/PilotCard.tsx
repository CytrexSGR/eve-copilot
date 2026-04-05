/**
 * PowerBloc PilotCard - Compact Summary Card
 * Uses details data passed from parent
 */

import { MiniChart } from '../../alliance/overview/MiniChart';

interface PilotCardProps {
  data: any;
}

export function PilotCard({ data }: PilotCardProps) {
  if (!data) return null;

  const alliances = data.alliance_heatmap || [];
  const totalAlliances = alliances.length;
  const totalActivity = alliances.reduce((sum: number, a: any) => sum + (a.hours?.reduce((s: number, v: number) => s + v, 0) || 0), 0);
  const avgActivity = totalActivity / Math.max(totalAlliances, 1);

  // Use participation trends for sparkline if available
  const daily = data.participation_trends?.daily || [];
  const timelineData = daily.length > 0
    ? daily.map((d: any) => d.active_pilots || 0)
    : Array(24).fill(0).map(() => Math.random() * avgActivity);

  // Get burnout status
  const burnoutStatus = data.burnout_index?.summary?.status || 'unknown';
  const statusColor = burnoutStatus === 'healthy' ? '#3fb950' : burnoutStatus === 'warning' ? '#ffcc00' : '#f85149';

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #a855f7',
      padding: '0.5rem',
      height: '180px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#a855f7', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          • PILOTS
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.4rem' }}>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>ALLIANCES</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#a855f7', fontFamily: 'monospace' }}>
            {totalAlliances}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>HEALTH</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: statusColor, fontFamily: 'monospace', textTransform: 'uppercase' }}>
            {burnoutStatus}
          </div>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', alignItems: 'center', padding: '0 0.5rem' }}>
        <MiniChart data={timelineData} height={60} color="#a855f7" />
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.3rem' }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Retention: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{data.attrition?.summary?.retention_rate?.toFixed(0) || '?'}%</span>
        </div>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Kills/Pilot: </span>
          <span style={{ color: '#a855f7', fontWeight: 600 }}>{data.burnout_index?.summary?.avg_kills_per_pilot?.toFixed(1) || '?'}</span>
        </div>
      </div>
    </div>
  );
}
