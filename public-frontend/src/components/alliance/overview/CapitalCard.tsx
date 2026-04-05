/**
 * Alliance CapitalCard - Compact Summary Card
 */

import { useState, useEffect } from 'react';
import { getCapitalIntel } from '../../../services/allianceApi';
import type { AllianceCapitalIntel } from '../../../types/alliance';
import { MiniChart } from './MiniChart';

interface CapitalCardProps {
  allianceId: number;
  days: number;
}

export function CapitalCard({ allianceId, days }: CapitalCardProps) {
  const [data, setData] = useState<AllianceCapitalIntel | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getCapitalIntel(allianceId, days)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [allianceId, days]);

  if (loading) {
    return <div className="skeleton" style={{ height: '180px', borderRadius: '6px' }} />;
  }

  if (!data) return null;

  const { summary, capital_timeline } = data;
  const timeline = capital_timeline.slice(-30);
  const timelineData = timeline.map(d => (d.kills || 0) + (d.losses || 0));

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
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#ff0000', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          • CAPITALS
        </span>
        <span style={{ fontSize: '0.5rem', color: '#58a6ff', cursor: 'pointer' }}>ℹ️</span>
      </div>

      {/* Top Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.4rem', marginBottom: '0.4rem' }}>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>KILLS</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#3fb950', fontFamily: 'monospace' }}>
            {summary.capital_kills}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>LOSSES</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ff4444', fontFamily: 'monospace' }}>
            {summary.capital_losses}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>EFFICIENCY</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: summary.efficiency >= 70 ? '#3fb950' : '#ffcc00', fontFamily: 'monospace' }}>
            {summary.efficiency.toFixed(1)} %
          </div>
        </div>
      </div>

      {/* Chart */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', padding: '0 0.5rem' }}>
        <MiniChart data={timelineData} height={60} color="#ff0000" />
      </div>

      {/* Bottom Stats */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.3rem' }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Top Type: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{data.fleet_composition?.[0]?.capital_type || 'N/A'}</span>
        </div>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Primary: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{data.ship_details?.[0]?.ship_name?.split(' ')[0] || 'N/A'}</span>
        </div>
      </div>
    </div>
  );
}
