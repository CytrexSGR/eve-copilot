/**
 * PilotCard Component
 *
 * Displays pilot intelligence summary for Overview tab.
 */

import { useState, useEffect } from 'react';
import { corpApi } from '../../../services/corporationApi';
import type { PilotSummary } from '../../../types/corporation';
import { TrendIndicator, MiniChart, StatCard } from './index';

interface PilotCardProps {
  corpId: number;
  days: number;
}

export function PilotCard({ corpId, days }: PilotCardProps) {
  const [data, setData] = useState<PilotSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    corpApi
      .getPilotSummary(corpId, days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [corpId, days]);

  if (loading) {
    return (
      <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.75rem', borderLeft: '2px solid #a855f7' }}>
        <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e' }}>• PILOTS</div>
        <div style={{ marginTop: '0.5rem', color: '#8b949e', fontSize: '0.75rem' }}>Loading...</div>
      </div>
    );
  }

  if (!data) return null;

  // Morale color
  const getMoraleColor = (morale: number): string => {
    if (morale >= 70) return '#3fb950';
    if (morale >= 50) return '#ffcc00';
    return '#f85149';
  };

  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: '0.75rem',
        borderLeft: '2px solid #a855f7',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e', fontWeight: 600 }}>
          • PILOTS
        </div>
        <TrendIndicator trend={data.trend} size="small" />
      </div>

      {/* Stats Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '0.5rem',
        }}
      >
        <StatCard
          label="Total Pilots"
          value={data.total_pilots}
          color="#a855f7"
          size="small"
        />
        <StatCard
          label="Avg Morale"
          value={data.avg_morale.toFixed(1)}
          color={getMoraleColor(data.avg_morale)}
          size="small"
        />
      </div>

      {/* Chart */}
      <div style={{ marginTop: '0.25rem' }}>
        <MiniChart
          data={data.timeline.map((t) => t.active_pilots)}
          height={35}
          color="#a855f7"
        />
      </div>

      {/* Bottom Stats */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '0.5rem',
          fontSize: '0.65rem',
          color: '#8b949e',
          marginTop: '0.25rem',
        }}
      >
        <div>
          <span style={{ color: '#3fb950' }}>⬆️ Elite:</span>{' '}
          <span style={{ color: '#fff' }}>{data.elite_pilots}</span>
        </div>
        <div>
          <span style={{ color: '#f85149' }}>⬇️ Struggling:</span>{' '}
          <span style={{ color: '#fff' }}>{data.struggling_pilots}</span>
        </div>
      </div>

      {/* Top Pilot */}
      <div
        style={{
          fontSize: '0.65rem',
          color: '#8b949e',
          textAlign: 'center',
        }}
      >
        Top Pilot: <span style={{ color: '#fff' }}>{data.top_pilot}</span>
      </div>
    </div>
  );
}
