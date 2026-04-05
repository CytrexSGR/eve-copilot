/**
 * DefensiveCard Component
 *
 * Displays defensive intelligence summary for Overview tab.
 */

import { useState, useEffect } from 'react';
import { corpApi } from '../../../services/corporationApi';
import type { DefensiveOverview } from '../../../types/corporation';
import { TrendIndicator, MiniChart, StatCard, formatISK, getEfficiencyColor, getKDColor } from './index';

interface DefensiveCardProps {
  corpId: number;
  days: number;
}

export function DefensiveCard({ corpId, days }: DefensiveCardProps) {
  const [data, setData] = useState<DefensiveOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    corpApi
      .getDefensiveSummary(corpId, days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [corpId, days]);

  if (loading) {
    return (
      <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.75rem', borderLeft: '2px solid #f85149' }}>
        <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e' }}>• DEFENSIVE</div>
        <div style={{ marginTop: '0.5rem', color: '#8b949e', fontSize: '0.75rem' }}>Loading...</div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: '0.75rem',
        borderLeft: '2px solid #f85149',
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
          • DEFENSIVE
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
          label="K/D Ratio"
          value={data.kd_ratio.toFixed(2)}
          color={getKDColor(data.kd_ratio)}
          size="small"
        />
        <StatCard
          label="Efficiency"
          value={data.efficiency.toFixed(1)}
          suffix="%"
          color={getEfficiencyColor(data.efficiency)}
          size="small"
        />
      </div>

      {/* Chart */}
      <div style={{ marginTop: '0.25rem' }}>
        <MiniChart
          data={data.timeline.map((t) => t.deaths)}
          height={35}
          color="#f85149"
        />
      </div>

      {/* Bottom Stats */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '0.65rem',
          color: '#8b949e',
          marginTop: '0.25rem',
        }}
      >
        <div>
          <span style={{ color: '#8b949e' }}>Top Threat:</span>{' '}
          <span style={{ color: '#fff' }}>{data.top_threat.name}</span>
        </div>
        <div>
          <span style={{ color: '#8b949e' }}>Deaths:</span>{' '}
          <span style={{ color: '#f85149' }}>{data.deaths}</span>
        </div>
      </div>

      {/* ISK Trend */}
      <div
        style={{
          fontSize: '0.65rem',
          color: '#8b949e',
          textAlign: 'center',
        }}
      >
        ISK Lost: <span style={{ color: '#fff' }}>{formatISK(data.isk_lost)}</span> {data.isk_trend}
      </div>
    </div>
  );
}
