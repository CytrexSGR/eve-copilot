/**
 * PowerBloc GeographyCard - Compact Summary Card
 * Uses offensive data passed from parent
 */

import { MiniChart } from '../../alliance/overview/MiniChart';

interface GeographyCardProps {
  data: any;
}

export function GeographyCard({ data }: GeographyCardProps) {
  if (!data) return null;

  const regions = (data.hunting_regions || data.hunting_grounds || []).slice(0, 10);
  const systems = regions.reduce((sum: number, r: any) => sum + (r.unique_systems || 0), 0);
  const totalRegions = regions.length;

  const timeline = (data.kill_timeline || []).slice(-30);
  const timelineData = timeline.map((d: any) => d.kills || 0);

  const topRegion = regions[0];

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #00bcd4',
      padding: '0.5rem',
      height: '180px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#00bcd4', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          • GEOGRAPHY
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.4rem' }}>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>SYSTEMS</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#00bcd4', fontFamily: 'monospace' }}>
            {systems}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>REGIONS</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#00bcd4', fontFamily: 'monospace' }}>
            {totalRegions}
          </div>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', alignItems: 'center', padding: '0 0.5rem' }}>
        <MiniChart data={timelineData} height={60} color="#00bcd4" />
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.3rem' }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Primary Region: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{topRegion?.region_name || 'N/A'}</span>
        </div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', marginTop: '0.15rem' }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Primary System: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{data.kill_heatmap?.[0]?.system_name || 'N/A'}</span>
        </div>
      </div>
    </div>
  );
}
