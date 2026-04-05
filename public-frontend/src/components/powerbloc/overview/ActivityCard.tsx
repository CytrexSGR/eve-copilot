/**
 * PowerBloc ActivityCard - Compact Summary Card
 * Uses details data passed from parent
 */

import { MiniChart } from '../../alliance/overview/MiniChart';

interface ActivityCardProps {
  data: any;
  days: number;
}

export function ActivityCard({ data, days }: ActivityCardProps) {
  if (!data) return null;

  const alliances = data.alliance_heatmap || [];
  const totalActivity = alliances.reduce((sum: number, a: any) => sum + (a.hours?.reduce((s: number, v: number) => s + v, 0) || 0), 0);
  const avgPerDay = totalActivity / Math.max(days, 1);

  // Find peak hour from aggregated hourly data
  const hourlyTotals = Array(24).fill(0);
  alliances.forEach((a: any) => {
    (a.hours || []).forEach((count: number, hour: number) => {
      hourlyTotals[hour] += count;
    });
  });
  const peakHour = hourlyTotals.indexOf(Math.max(...hourlyTotals));

  // Use hourly data as sparkline
  const timelineData = hourlyTotals;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #3fb950',
      padding: '0.5rem',
      height: '180px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#3fb950', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          • ACTIVITY
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.4rem' }}>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>ALLIANCES</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#3fb950', fontFamily: 'monospace' }}>
            {alliances.length}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>AVG/DAY</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#3fb950', fontFamily: 'monospace' }}>
            {Math.round(avgPerDay)}
          </div>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', alignItems: 'center', padding: '0 0.5rem' }}>
        <MiniChart data={timelineData} height={60} color="#3fb950" />
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.3rem' }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Peak Activity: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{peakHour}:00 UTC</span>
        </div>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Total: </span>
          <span style={{ color: '#3fb950', fontWeight: 600 }}>{totalActivity.toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}
