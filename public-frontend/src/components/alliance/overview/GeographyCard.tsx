/**
 * Alliance GeographyCard - Compact Summary Card
 */

import { useState, useEffect } from 'react';
import { getOffensiveStats } from '../../../services/allianceApi';
import type { AllianceOffensiveStats } from '../../../types/alliance';
import { MiniChart } from './MiniChart';

interface GeographyCardProps {
  allianceId: number;
  days: number;
}

export function GeographyCard({ allianceId, days }: GeographyCardProps) {
  const [data, setData] = useState<AllianceOffensiveStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getOffensiveStats(allianceId, days)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [allianceId, days]);

  if (loading) {
    return <div className="skeleton" style={{ height: '180px', borderRadius: '6px' }} />;
  }

  if (!data) return null;

  const regions = data.hunting_regions?.slice(0, 10) || [];
  const systems = regions.reduce((sum, r) => sum + (r.unique_systems || 0), 0);
  const totalRegions = regions.length;

  // Use kill timeline for geographic spread over time
  const timeline = data.kill_timeline.slice(-30);
  const timelineData = timeline.map(d => d.kills || 0);

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
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#00bcd4', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          • GEOGRAPHY
        </span>
        <span style={{ fontSize: '0.5rem', color: '#58a6ff', cursor: 'pointer' }}>ℹ️</span>
      </div>

      {/* Top Metrics */}
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

      {/* Chart */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', padding: '0 0.5rem' }}>
        <MiniChart data={timelineData} height={60} color="#00bcd4" />
      </div>

      {/* Bottom Stats */}
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
