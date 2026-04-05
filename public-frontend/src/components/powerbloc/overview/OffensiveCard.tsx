/**
 * PowerBloc OffensiveCard - Compact Summary Card
 */

import { MiniChart } from '../../alliance/overview/MiniChart';

interface OffensiveCardProps {
  data: any;
}

export function OffensiveCard({ data }: OffensiveCardProps) {
  if (!data) return null;

  const { summary, kill_timeline } = data;
  const timeline = (kill_timeline || []).slice(-30);
  const timelineData = timeline.map((d: any) => d.kills || 0);

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
          • OFFENSIVE
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.4rem' }}>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>EFFICIENCY</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#3fb950', fontFamily: 'monospace' }}>
            {summary?.efficiency?.toFixed(1) || '0'} %
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>ISK DESTROYED</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#3fb950', fontFamily: 'monospace' }}>
            {((summary?.isk_destroyed || 0) / 1e12).toFixed(1)}T
          </div>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', alignItems: 'center', padding: '0 0.5rem' }}>
        <MiniChart data={timelineData} height={60} color="#3fb950" />
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.3rem' }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Top Target: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{data.top_victims?.[0]?.corporation_name || data.top_victims?.[0]?.alliance_name || 'N/A'}</span>
        </div>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Doctrine: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{data.doctrine_profile?.[0]?.ship_class || 'N/A'}</span>
        </div>
      </div>
    </div>
  );
}
