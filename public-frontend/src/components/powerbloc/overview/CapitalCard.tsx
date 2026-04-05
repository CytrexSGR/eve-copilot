/**
 * PowerBloc CapitalCard - Compact Summary Card
 */

import { MiniChart } from '../../alliance/overview/MiniChart';

interface CapitalCardProps {
  data: any;
}

export function CapitalCard({ data }: CapitalCardProps) {
  if (!data) return null;

  const { summary, capital_timeline, fleet_composition } = data;
  const timeline = (capital_timeline || []).slice(-30);
  const timelineData = timeline.map((d: any) => (d.kills || 0) + (d.losses || 0));

  const kills = summary?.capital_kills || 0;
  const losses = summary?.capital_losses || 0;
  const efficiency = summary?.efficiency ?? (kills > 0 ? (kills / (kills + losses)) * 100 : 0);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #ff0000',
      padding: '0.5rem',
      height: '180px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#ff0000', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          • CAPITALS
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.4rem', marginBottom: '0.4rem' }}>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>KILLS</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#3fb950', fontFamily: 'monospace' }}>
            {kills}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>LOSSES</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ff4444', fontFamily: 'monospace' }}>
            {losses}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>EFFICIENCY</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: efficiency >= 70 ? '#3fb950' : '#ffcc00', fontFamily: 'monospace' }}>
            {efficiency.toFixed(1)} %
          </div>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', alignItems: 'center', padding: '0 0.5rem' }}>
        <MiniChart data={timelineData} height={60} color="#ff0000" />
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.3rem' }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Top Type: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{fleet_composition?.[0]?.capital_type || 'N/A'}</span>
        </div>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>K/D: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{summary?.kd_ratio?.toFixed(2) || 'N/A'}</span>
        </div>
      </div>
    </div>
  );
}
