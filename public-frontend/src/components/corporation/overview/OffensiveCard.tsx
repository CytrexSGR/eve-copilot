/**
 * OffensiveCard Component
 *
 * Displays offensive intelligence summary for Overview tab.
 */

import { useState, useEffect } from 'react';
import { corpApi } from '../../../services/corporationApi';
import type { OffensiveOverview } from '../../../types/corporation';
import { TrendIndicator, MiniChart, StatCard, formatISK, getEfficiencyColor } from './index';

interface OffensiveCardProps {
  corpId: number;
  days: number;
}

export function OffensiveCard({ corpId, days }: OffensiveCardProps) {
  const [data, setData] = useState<OffensiveOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    corpApi
      .getOffensiveSummary(corpId, days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [corpId, days]);

  if (loading) {
    return (
      <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.75rem', borderLeft: '2px solid #3fb950' }}>
        <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e' }}>• OFFENSIVE</div>
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
        borderLeft: '2px solid #3fb950',
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
          • OFFENSIVE
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
          label="Efficiency"
          value={data.efficiency.toFixed(1)}
          suffix="%"
          color={getEfficiencyColor(data.efficiency)}
          size="small"
        />
        <StatCard
          label="ISK Destroyed"
          value={formatISK(data.isk_destroyed)}
          color="#3fb950"
          size="small"
        />
      </div>

      {/* Chart */}
      <div style={{ marginTop: '0.25rem' }}>
        <MiniChart
          data={data.timeline.map((t) => t.kills)}
          height={35}
          color="#3fb950"
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
          <span style={{ color: '#8b949e' }}>Top Target:</span>{' '}
          <span style={{ color: '#fff' }}>{data.top_target.name}</span>
        </div>
        <div>
          <span style={{ color: '#8b949e' }}>Doctrine:</span>{' '}
          <span style={{ color: '#fff' }}>{data.primary_doctrine}</span>
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
        ISK Trend: <span style={{ color: '#fff' }}>{data.isk_trend}</span>
      </div>
    </div>
  );
}
