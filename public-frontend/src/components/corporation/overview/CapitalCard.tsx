/**
 * CapitalCard Component
 *
 * Displays capital warfare intelligence summary for Overview tab.
 */

import { useState, useEffect } from 'react';
import { corpApi } from '../../../services/corporationApi';
import type { CapitalSummary } from '../../../types/corporation';
import { TrendIndicator, MiniChart, StatCard, getEfficiencyColor } from './index';

interface CapitalCardProps {
  corpId: number;
  days: number;
}

export function CapitalCard({ corpId, days }: CapitalCardProps) {
  const [data, setData] = useState<CapitalSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    corpApi
      .getCapitalSummary(corpId, days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [corpId, days]);

  if (loading) {
    return (
      <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.75rem', borderLeft: '2px solid #ff0000' }}>
        <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e' }}>• CAPITALS</div>
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
        borderLeft: '2px solid #ff0000',
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
          • CAPITALS
        </div>
        <TrendIndicator trend={data.trend} size="small" />
      </div>

      {/* Stats Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '0.5rem',
        }}
      >
        <StatCard
          label="Kills"
          value={data.kills}
          color="#3fb950"
          size="small"
        />
        <StatCard
          label="Losses"
          value={data.losses}
          color="#f85149"
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

      {/* Chart - Stacked kills and losses */}
      <div style={{ marginTop: '0.25rem' }}>
        <MiniChart
          data={data.timeline.map((t) => t.kills + t.losses)}
          height={35}
          color="#ff0000"
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
          <span style={{ color: '#8b949e' }}>Top Type:</span>{' '}
          <span style={{ color: '#fff' }}>{data.top_capital_type}</span>
        </div>
        <div>
          <span style={{ color: '#8b949e' }}>Primary:</span>{' '}
          <span style={{ color: '#fff' }}>{data.primary_capital}</span>
        </div>
      </div>
    </div>
  );
}
